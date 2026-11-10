"""Predizračun pravih buildov šampionov (rune, čas nakupa predmetov, začetni nakupi).

`python -m app.recommend.precompute` prebere zbrane tekme (matches.raw → perks,
match_participants.features → purchases) in za vsakega šampiona v njegovi glavni vlogi shrani
vrstico v champion_build_stats. Priporočilo nato bere samo to vrstico (ne 900 MB surovih tekem).
Zažene se po zbiranju tekem, skupaj z `app.profiling.baselines`.
"""

import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models.champion_build_stat import ChampionBuildStat
from app.models.item import Item
from app.recommend.champion_stats import MIN_GAMES

MIN_PAGE_GAMES = 20
MIN_PAGE_RATE = 0.05
MAX_PAGES = 3
# Nakupi v prvih sekundah so začetni predmeti (trgovina ob začetku tekme).
START_WINDOW_S = 35
MIN_TIMING_SAMPLE = 10

RunePage = tuple[int, int, int]  # (primarno drevo, ključna runa, sekundarno drevo)


def parse_perks(perks: dict[str, Any] | None) -> dict[str, Any] | None:
    """Iz Riotovih perks izlušči stran run; None, če so podatki nepopolni."""
    if not perks:
        return None
    styles = {s.get("description"): s for s in perks.get("styles", [])}
    primary, secondary = styles.get("primaryStyle"), styles.get("subStyle")
    if not primary or not secondary:
        return None
    main = [s["perk"] for s in primary.get("selections", [])]
    sub = [s["perk"] for s in secondary.get("selections", [])]
    if len(main) < 4 or len(sub) < 2:
        return None
    stat = perks.get("statPerks", {})
    return {
        "primary_style": primary["style"],
        "secondary_style": secondary["style"],
        "primary": main[:4],
        "secondary": sub[:2],
        "shards": [stat.get("offense"), stat.get("flex"), stat.get("defense")],
    }


def _new_entry() -> dict[str, Any]:
    return {
        "games": 0,
        "wins": 0,
        "main": [Counter() for _ in range(3)],
        "sub": Counter(),
        "shards": [Counter() for _ in range(3)],
    }


def build_rune_pages(rows: Iterable[tuple[bool, dict[str, Any]]], games: int) -> list[dict]:
    """Najpogostejše strani (drevo, ključna runa, sekundarno drevo) z modalnimi manjšimi runami."""
    pages: dict[RunePage, dict[str, Any]] = {}
    for win, page in rows:
        key = (page["primary_style"], page["primary"][0], page["secondary_style"])
        entry = pages.setdefault(key, _new_entry())
        entry["games"] += 1
        entry["wins"] += int(win)
        for slot, perk in enumerate(page["primary"][1:4]):
            entry["main"][slot][perk] += 1
        entry["sub"].update(page["secondary"])
        for slot, shard in enumerate(page["shards"]):
            entry["shards"][slot][shard] += 1

    result = []
    ranked = sorted(pages.items(), key=lambda kv: (-kv[1]["games"], kv[0]))
    for (primary_style, keystone, secondary_style), entry in ranked:
        if entry["games"] < MIN_PAGE_GAMES or entry["games"] / games < MIN_PAGE_RATE:
            continue
        result.append(
            {
                "primary_style": primary_style,
                "keystone": keystone,
                "secondary_style": secondary_style,
                "games": entry["games"],
                "wins": entry["wins"],
                "primary_perks": [keystone] + [c.most_common(1)[0][0] for c in entry["main"]],
                "secondary_perks": [perk for perk, _ in entry["sub"].most_common(2)],
                "shards": [c.most_common(1)[0][0] for c in entry["shards"]],
            }
        )
    return result[:MAX_PAGES]


def build_item_timing(
    players: Iterable[tuple[list[int], list[list[int]]]], completed: set[int]
) -> dict[str, dict[str, float]]:
    """Mediana časa prvega nakupa vsakega dokončanega predmeta, ki ga igralec ima ob koncu."""
    times: dict[int, list[int]] = defaultdict(list)
    for final_items, purchases in players:
        owned = set(final_items) & completed
        first: dict[int, int] = {}
        for item_id, second in purchases:
            if item_id in owned and (item_id not in first or second < first[item_id]):
                first[item_id] = second
        for item_id, second in first.items():
            times[item_id].append(second)
    return {
        str(item_id): {"median_s": statistics.median(values), "n": len(values)}
        for item_id, values in times.items()
        if len(values) >= MIN_TIMING_SAMPLE
    }


def build_start_items(players: Iterable[tuple[bool, list[list[int]]]]) -> dict[str, Any] | None:
    counts: Counter[tuple[int, ...]] = Counter()
    wins: Counter[tuple[int, ...]] = Counter()
    for win, purchases in players:
        start = tuple(sorted(item for item, second in purchases if second <= START_WINDOW_S))
        if start:
            counts[start] += 1
            wins[start] += int(win)
    if not counts:
        return None
    best, games = counts.most_common(1)[0]
    return {"items": list(best), "games": games, "wins": wins[best]}


def main_positions(session: Session) -> dict[int, tuple[str, int]]:
    rows = session.execute(
        text(
            "SELECT DISTINCT ON (champion_id) champion_id, position, n FROM ("
            " SELECT champion_id, position, count(*) AS n FROM match_participants"
            " WHERE position <> '' GROUP BY champion_id, position) t"
            " ORDER BY champion_id, n DESC"
        )
    )
    return {r[0]: (r[1], r[2]) for r in rows if r[2] >= MIN_GAMES}


def recompute(session: Session) -> int:
    """Pregleda vse tekme in zamenja champion_build_stats; vrne število šampionov."""
    positions = main_positions(session)
    completed = set(session.scalars(select(Item.id).where(Item.completed)))

    pages: dict[int, list[tuple[bool, dict]]] = defaultdict(list)
    runes = session.execute(
        text(
            "SELECT (p->>'championId')::int, p->>'teamPosition', (p->>'win')::bool, p->'perks' "
            "FROM matches m "
            "CROSS JOIN LATERAL jsonb_array_elements(m.raw->'info'->'participants') p"
        ).execution_options(stream_results=True)
    )
    for champion_id, position, win, perks in runes:
        if champion_id in positions and positions[champion_id][0] == position:
            page = parse_perks(perks)
            if page:
                pages[champion_id].append((win, page))

    timing: dict[int, list] = defaultdict(list)
    start: dict[int, list] = defaultdict(list)
    purchases = session.execute(
        text(
            "SELECT champion_id, position, win, items, features->'purchases' "
            "FROM match_participants WHERE features ? 'purchases'"
        ).execution_options(stream_results=True)
    )
    for champion_id, position, win, items, bought in purchases:
        if champion_id in positions and positions[champion_id][0] == position and bought:
            timing[champion_id].append((items, bought))
            start[champion_id].append((win, bought))

    session.execute(delete(ChampionBuildStat))
    for champion_id, (position, games) in positions.items():
        session.add(
            ChampionBuildStat(
                champion_id=champion_id,
                position=position,
                games=games,
                rune_pages=build_rune_pages(pages[champion_id], max(len(pages[champion_id]), 1)),
                item_timing=build_item_timing(timing[champion_id], completed),
                start_items=build_start_items(start[champion_id]),
            )
        )
    session.flush()
    return len(positions)


def main() -> int:
    with get_session_factory()() as session:
        count = recompute(session)
        session.commit()
    print(f"Predizračunani buildi za {count} šampionov.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
