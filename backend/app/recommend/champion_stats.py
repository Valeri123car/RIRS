"""Kaj šampion v zbranih tekemah res kupuje: pogostost in zmage po dokončanih predmetih.

Pravila po oznakah predmetov ne poznajo šampionov, ki odstopajo od svojega razreda (Pyke je
»Support«, a gradi smrtonosnost). Zato so kandidati za priporočilo predmeti, ki jih igralci
tega šampiona v svoji najpogostejši vlogi res imajo ob koncu tekme (docs/ugotovitve.md,
poskus 8: build je odvisen predvsem od šampiona).
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.champion_build_stat import ChampionBuildStat
from app.models.item import Item
from app.models.rune import Rune

# Pod tem številom iger šampiona v njegovi glavni vlogi se podatkom ne zaupa (rezerva: oznake).
MIN_GAMES = 30


@dataclass(frozen=True)
class BuildStats:
    games: int
    position: str
    # predmet -> (število iger z njim, zmage)
    items: dict[int, tuple[int, int]] = field(default_factory=dict)
    # Strani run z razrešenimi imeni (padajoče po pogostosti); prazno brez predizračuna.
    rune_pages: tuple[dict[str, Any], ...] = ()
    # Predmet -> mediana minute prvega nakupa (dokončani predmeti).
    item_minutes: dict[int, float] = field(default_factory=dict)
    # Začetni nakupi: {"items": [{"id", "name"}], "games", "wins"} ali None.
    start_items: dict[str, Any] | None = None

    def pick_rate(self, item_id: int) -> float:
        return self.items.get(item_id, (0, 0))[0] / self.games if self.games else 0.0

    def win_rate(self, item_id: int, prior_games: int = 20) -> float:
        """Delež zmag z Bayesovim krčenjem k 50 %, da redek predmet ne izstopa po naključju."""
        count, wins = self.items.get(item_id, (0, 0))
        return (wins + prior_games / 2) / (count + prior_games)


def load_build_stats(session: Session, champion_id: int) -> BuildStats | None:
    """Statistika predmetov šampiona v njegovi najpogostejši vlogi; None brez dovolj iger."""
    row = session.execute(
        text(
            "SELECT position, count(*) FROM match_participants "
            "WHERE champion_id = :c AND position <> '' GROUP BY position "
            "ORDER BY count(*) DESC LIMIT 1"
        ),
        {"c": champion_id},
    ).first()
    if row is None or row[1] < MIN_GAMES:
        return None
    position, games = row
    items = session.execute(
        text(
            "SELECT it, count(*), sum(p.win::int) "
            "FROM match_participants p CROSS JOIN LATERAL unnest(p.items) AS it "
            "JOIN items i ON i.id = it AND i.completed "
            "WHERE p.champion_id = :c AND p.position = :pos GROUP BY it"
        ),
        {"c": champion_id, "pos": position},
    )
    stats = BuildStats(
        games=games, position=position, items={r[0]: (r[1], int(r[2])) for r in items}
    )
    return _with_precomputed(session, champion_id, stats)


# Statistične rune (shards) niso v runesReforged.json.
SHARD_NAMES = {
    5001: "Rast zdravja",
    5002: "Oklep",
    5003: "Magični odpor",
    5005: "Hitrost napadanja",
    5007: "Pospešek sposobnosti",
    5008: "Prilagodljiva moč",
    5010: "Hitrost gibanja",
    5011: "Zdravje",
    5013: "Žilavost in odpornost proti upočasnitvi",
}


def _with_precomputed(session: Session, champion_id: int, stats: BuildStats) -> BuildStats:
    """Doda rune, čase nakupov in začetne predmete iz champion_build_stats (če so)."""
    row = session.get(ChampionBuildStat, champion_id)
    if row is None or row.position != stats.position:
        return stats
    perk_ids: set[int] = set()
    for page in row.rune_pages:
        perk_ids |= {page["primary_style"], page["secondary_style"]}
        perk_ids |= set(page["primary_perks"]) | set(page["secondary_perks"])
    names = {r.id: r.name for r in session.scalars(select(Rune).where(Rune.id.in_(perk_ids)))}
    pages = []
    for page in row.rune_pages:
        try:
            pages.append(
                {
                    "primary_tree": names[page["primary_style"]],
                    "keystone": names[page["keystone"]],
                    "secondary_tree": names[page["secondary_style"]],
                    "primary_perks": [names[i] for i in page["primary_perks"]],
                    "secondary_perks": [names[i] for i in page["secondary_perks"]],
                    "shards": [SHARD_NAMES.get(i, str(i)) for i in page["shards"]],
                    "games": page["games"],
                    "wins": page["wins"],
                }
            )
        except KeyError:
            continue  # runa še ni uvožena (stara baza): stran se preskoči
    start = None
    if row.start_items:
        ids = row.start_items["items"]
        item_names = {i.id: i.name for i in session.scalars(select(Item).where(Item.id.in_(ids)))}
        start = {
            "items": [{"id": i, "name": item_names.get(i, str(i))} for i in ids],
            "games": row.start_items["games"],
            "wins": row.start_items["wins"],
        }
    minutes = {int(k): v["median_s"] / 60 for k, v in row.item_timing.items()}
    return BuildStats(
        games=stats.games,
        position=stats.position,
        items=stats.items,
        rune_pages=tuple(pages),
        item_minutes=minutes,
        start_items=start,
    )
