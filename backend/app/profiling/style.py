"""Profil sloga igralca iz njegovih zadnjih rangiranih tekem (US-06, F06).

Tekme, ki so že v bazi, se ne prenašajo znova; manjkajoče se prenesejo prek Riot klienta
(Match-V5) in shranijo z zbiralnikovim store_match, a brez časovnic (preveč klicev pri
omejitvi 100 klicev / 2 min). Zato je število prenosov na igralca omejeno.
"""

import logging
import statistics
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collector.parse import MatchParseError, parse_match
from app.collector.service import RANKED_SOLO_QUEUE_ID, store_match
from app.models.match import Match, MatchParticipant
from app.profiling.baselines import Baselines
from app.profiling.indicators import INDICATORS, MIN_GAME_S, compute_indicators
from app.riot.client import RiotClient
from app.riot.errors import RiotApiError, RiotNotFoundError

logger = logging.getLogger(__name__)

MAX_MATCHES = 20
# Pod tem številom tekem je profil označen kot "nizko zaupanje".
LOW_CONFIDENCE_BELOW = 5
# Največ novih tekem na igralca: 5 nasprotnikov x (1 + 8) klicev ostane pod omejitvijo ključa.
MAX_DOWNLOADS_PER_PLAYER = 8


def _own_matches(session: Session, puuid: str) -> list[tuple[dict, int, int | None]]:
    """(udeleženec iz JSON-a, trajanje, zgodnje smrti) za zadnje tekme igralca v bazi."""
    rows = session.execute(
        select(Match.raw, Match.duration_s, MatchParticipant.features)
        .join(MatchParticipant, MatchParticipant.match_id == Match.match_id)
        .where(MatchParticipant.puuid == puuid, Match.duration_s >= MIN_GAME_S)
        .order_by(Match.game_start.desc())
        .limit(MAX_MATCHES)
    )
    out = []
    for raw, duration_s, features in rows:
        participant = next(
            (p for p in raw["info"]["participants"] if p.get("puuid") == puuid), None
        )
        if participant is not None:
            deaths14 = (features or {}).get("deaths_before_14")
            out.append((participant, duration_s, deaths14))
    return out


def _download_missing(session: Session, riot: RiotClient, puuid: str, platform: str) -> None:
    try:
        ids = riot.get_match_ids(puuid, platform, count=MAX_MATCHES, queue=RANKED_SOLO_QUEUE_ID)
    except RiotApiError as exc:
        logger.warning("Zgodovine igralca ni bilo mogoče prenesti: %s", exc)
        return
    known = set(session.scalars(select(Match.match_id).where(Match.match_id.in_(ids))))
    for match_id in [i for i in ids if i not in known][:MAX_DOWNLOADS_PER_PLAYER]:
        try:
            raw = riot.get_match(match_id, platform)
            parsed = parse_match(raw, match_id)
        except (RiotNotFoundError, MatchParseError) as exc:
            logger.warning("Tekma %s preskočena: %s", match_id, exc)
            continue
        except RiotApiError as exc:
            logger.warning("Prenos tekme %s ni uspel: %s", match_id, exc)
            return
        if parsed.queue_id == RANKED_SOLO_QUEUE_ID:
            store_match(session, parsed, raw)
    session.commit()


def relative_to_median(value: float, median: float) -> float:
    """Odstopanje od mediane vloge (0 = povprečen, 0,5 = 50 % nad mediano).

    Imenovalec je vsaj 1, ker je mediana nekaterih kazalnikov (roaming) 0.
    """
    return (value - median) / max(abs(median), 1.0)


def build_style_profile(
    session: Session,
    riot: RiotClient | None,
    puuid: str,
    platform: str,
    baselines: Baselines,
    *,
    download: bool = True,
) -> dict[str, Any]:
    """Kazalniki igralca (povprečje zadnjih tekem) in odstopanje od mediane vloge."""
    matches = _own_matches(session, puuid)
    if download and riot is not None and len(matches) < MAX_MATCHES:
        _download_missing(session, riot, puuid, platform)
        matches = _own_matches(session, puuid)

    values: dict[str, list[float]] = {name: [] for name in INDICATORS}
    relative: dict[str, list[float]] = {name: [] for name in INDICATORS}
    positions: list[str] = []
    for participant, duration_s, deaths14 in matches:
        position = participant.get("teamPosition") or ""
        medians = baselines.get(position)
        if medians is None:
            continue
        positions.append(position)
        for name, value in compute_indicators(participant, duration_s, deaths14).items():
            values[name].append(value)
            relative[name].append(relative_to_median(value, medians[name]))

    n = len(positions)
    return {
        "matches": n,
        "low_confidence": n < LOW_CONFIDENCE_BELOW,
        "role": statistics.mode(positions) if positions else None,
        "indicators": {
            name: {
                "value": round(statistics.fmean(values[name]), 2),
                "vs_median": round(statistics.fmean(relative[name]), 2),
            }
            for name in INDICATORS
            if n
        },
    }
