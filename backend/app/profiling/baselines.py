"""Mediane kazalnikov po vlogah iz vseh zbranih tekem (US-06).

Izračun je počasen (preleti celoten JSON vseh tekem), zato se zažene ročno in se shrani v
style_baselines: `python -m app.profiling.baselines`. Pri analizi se samo prebere.
"""

import logging
import statistics
from collections import defaultdict

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.style_baseline import StyleBaseline
from app.profiling.indicators import (
    CHALLENGE_FIELDS,
    INDICATORS,
    MIN_GAME_S,
    PARTICIPANT_FIELDS,
    compute_indicators,
)

logger = logging.getLogger(__name__)
POSITIONS = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")

Baselines = dict[str, dict[str, float]]

# Iz JSON-a vzamemo samo potrebna polja; zgodnje smrti so v match_participants.features.
_SQL = text(
    """
    SELECT x.puuid, p AS participant, m.duration_s, m.game_start,
           (mp.features->>'deaths_before_14')::int AS deaths14
    FROM matches m
    CROSS JOIN LATERAL (
        SELECT jsonb_build_object(
            {fields},
            'challenges', jsonb_build_object({challenges})
        ) AS p, e->>'puuid' AS puuid
        FROM jsonb_array_elements(m.raw->'info'->'participants') e
    ) x
    LEFT JOIN match_participants mp ON mp.match_id = m.match_id AND mp.puuid = x.puuid
    WHERE m.duration_s >= :min_s
    """.format(
        fields=", ".join(f"'{k}', e->'{k}'" for k in PARTICIPANT_FIELDS),
        challenges=", ".join(f"'{k}', e->'challenges'->'{k}'" for k in CHALLENGE_FIELDS),
    )
)


def iter_participants(session: Session):
    """(puuid, zmanjšan udeleženec, trajanje, začetek, zgodnje smrti) za vse tekme v bazi."""
    yield from session.execute(_SQL, {"min_s": MIN_GAME_S}).yield_per(2000)


def compute_baselines(session: Session) -> tuple[Baselines, dict[str, int]]:
    """({vloga: {kazalnik: mediana}}, {vloga: število igralcev}) iz vseh tekem v bazi."""
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for _puuid, participant, duration_s, _start, deaths14 in iter_participants(session):
        position = participant.get("teamPosition")
        if position not in POSITIONS:
            continue
        for name, value in compute_indicators(participant, duration_s, deaths14).items():
            values[position][name].append(value)
    medians = {
        pos: {name: statistics.median(v) for name, v in by_name.items()}
        for pos, by_name in values.items()
    }
    sizes = {pos: len(by_name[INDICATORS[0]]) for pos, by_name in values.items()}
    return medians, sizes


def store_baselines(session: Session, medians: Baselines, sizes: dict[str, int]) -> None:
    rows = [
        {"position": pos, "indicator": name, "median": value, "sample": sizes[pos]}
        for pos, by_name in medians.items()
        for name, value in by_name.items()
    ]
    if not rows:
        return
    stmt = insert(StyleBaseline).values(rows)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["position", "indicator"],
            set_={"median": stmt.excluded.median, "sample": stmt.excluded.sample},
        )
    )
    session.commit()


def load_baselines(session: Session) -> Baselines:
    out: Baselines = defaultdict(dict)
    for row in session.scalars(select(StyleBaseline)):
        out[row.position][row.indicator] = row.median
    return dict(out)


def main() -> None:
    from app.db.session import get_session_factory

    logging.basicConfig(level=logging.INFO)
    with get_session_factory()() as session:
        medians, sizes = compute_baselines(session)
        store_baselines(session, medians, sizes)
    for pos in POSITIONS:
        logger.info("%s (n=%s): %s", pos, sizes.get(pos), medians.get(pos))


if __name__ == "__main__":
    main()
