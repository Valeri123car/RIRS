"""Zbiralnik rangiranih tekem (US-07, F07).

Vir je samo uradni Riot API (ADR-0001): League-V4 challenger liga na platformi -> puuidi ->
Match-V5 ID-ji rangiranih solo tekem -> tekma (+ časovnica). Tekme se shranijo trajno
(ADR-0005); tekme, ki so že v bazi, se ne prenašajo znova. Klici gredo skozi Riot klient,
ki jih omejuje prek Redis (razvojni ključ: 100 klicev / 2 min).

Vsak zagon je zapisan v collector_runs (čas, število novih tekem, izid). Tekme se potrdijo
sproti, zato napaka sredi zagona ne izgubi že prenesenih tekem.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.collector.parse import MatchParseError, ParsedMatch, parse_match, timeline_features
from app.core.config import Settings
from app.models.collector_run import CollectorRun, CollectorStatus
from app.models.match import Match, MatchParticipant
from app.models.riot_account import RiotAccount
from app.riot.client import RiotClient
from app.riot.errors import RiotApiError, RiotNotFoundError

logger = logging.getLogger(__name__)

RANKED_SOLO_QUEUE_ID = 420


@dataclass(frozen=True)
class CollectorConfig:
    platform: str = "euw1"
    max_players: int = 20
    matches_per_player: int = 20
    max_new_matches: int = 100
    timelines: bool = True

    @classmethod
    def from_settings(cls, settings: Settings, **overrides: Any) -> "CollectorConfig":
        values = {
            "platform": settings.collector_platform,
            "max_players": settings.collector_max_players,
            "matches_per_player": settings.collector_matches_per_player,
            "max_new_matches": settings.collector_max_new_matches,
            "timelines": settings.collector_timelines,
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)


def collect_matches(session: Session, riot: RiotClient, config: CollectorConfig) -> CollectorRun:
    """Izvede en zagon zbiralnika in vrne njegov zapis (status success ali error)."""
    run = CollectorRun(
        platform=config.platform,
        status=CollectorStatus.RUNNING,
        started_at=datetime.now(UTC),
        players=0,
        new_matches=0,
    )
    session.add(run)
    session.commit()

    try:
        _collect(session, riot, config, run)
    except Exception as exc:
        session.rollback()  # zavrže samo nepotrjeno tekmo; prejšnje so že potrjene
        logger.exception("Zbiralnik tekem ni uspel")
        run.status = CollectorStatus.ERROR
        run.error = _describe(exc)
    else:
        run.status = CollectorStatus.SUCCESS
    run.finished_at = datetime.now(UTC)
    session.commit()
    session.refresh(run)  # po rollback so atributi potekli; zapis naj bo berljiv tudi po seji
    return run


def _collect(
    session: Session, riot: RiotClient, config: CollectorConfig, run: CollectorRun
) -> None:
    league = riot.get_challenger_league(config.platform)
    # Najvišje uvrščeni najprej; vrstni red je stabilen, zato so zagoni ponovljivi.
    entries = sorted(league.entries, key=lambda e: (-e.league_points, e.puuid))
    seen: set[str] = set()

    for entry in entries[: config.max_players]:
        if run.new_matches >= config.max_new_matches:
            break
        match_ids = riot.get_match_ids(
            entry.puuid,
            config.platform,
            count=config.matches_per_player,
            queue=RANKED_SOLO_QUEUE_ID,
        )
        run.players += 1
        # Tekmo igra 10 igralcev, zato se ista tekma pogosto pojavi pri več challengerjih.
        candidates = [match_id for match_id in dict.fromkeys(match_ids) if match_id not in seen]
        seen.update(candidates)
        stored = set(session.scalars(select(Match.match_id).where(Match.match_id.in_(candidates))))

        for match_id in candidates:
            if run.new_matches >= config.max_new_matches:
                break
            if match_id in stored:
                continue
            if _download_and_store(session, riot, config, match_id):
                run.new_matches += 1
            session.commit()
        session.commit()  # števec igralcev tudi, ko igralec nima novih tekem


def _download_and_store(
    session: Session, riot: RiotClient, config: CollectorConfig, match_id: str
) -> bool:
    try:
        raw = riot.get_match(match_id, config.platform)
        parsed = parse_match(raw, match_id)
    except (RiotNotFoundError, MatchParseError) as exc:
        logger.warning("Tekma %s preskočena: %s", match_id, exc)
        return False
    if parsed.queue_id != RANKED_SOLO_QUEUE_ID:
        logger.warning("Tekma %s ni rangirana solo tekma, preskočena", match_id)
        return False

    features: dict[str, dict[str, int]] = {}
    if config.timelines:
        try:
            features = timeline_features(riot.get_match_timeline(match_id, config.platform))
        except RiotNotFoundError:
            logger.warning("Tekma %s nima časovnice, shranjena brez značilk", match_id)
    return store_match(session, parsed, raw, features)


def store_match(
    session: Session,
    parsed: ParsedMatch,
    raw: dict[str, Any],
    features: dict[str, dict[str, int]] | None = None,
) -> bool:
    """Shrani tekmo z udeleženci; vrne False, če je tekma že v bazi (npr. vzporedni zagon)."""
    features = features or {}
    inserted = session.scalar(
        insert(Match)
        .values(
            match_id=parsed.match_id,
            platform=parsed.platform,
            queue_id=parsed.queue_id,
            patch=parsed.patch,
            game_start=parsed.game_start,
            duration_s=parsed.duration_s,
            winning_team=parsed.winning_team,
            raw=raw,
        )
        .on_conflict_do_nothing(index_elements=[Match.match_id])
        .returning(Match.match_id)
    )
    if inserted is None:
        return False

    # Igralci iz tekem so v riot_accounts brez uporabnika; obstoječih računov ne spreminjamo.
    session.execute(
        insert(RiotAccount)
        .values(
            [
                {
                    "puuid": p.puuid,
                    "game_name": p.game_name,
                    "tag_line": p.tag_line,
                    "platform": parsed.platform,
                }
                for p in parsed.participants
            ]
        )
        .on_conflict_do_nothing(index_elements=[RiotAccount.puuid])
    )
    session.execute(
        insert(MatchParticipant).values(
            [
                {
                    "match_id": parsed.match_id,
                    "puuid": p.puuid,
                    "team_id": p.team_id,
                    "champion_id": p.champion_id,
                    "position": p.position,
                    "kills": p.kills,
                    "deaths": p.deaths,
                    "assists": p.assists,
                    "items": p.items,
                    "win": p.win,
                    "features": features.get(p.puuid) or None,
                }
                for p in parsed.participants
            ]
        )
    )
    return True


def _describe(exc: Exception) -> str:
    """Sporočilo za collector_runs. Napake Riot prehoda ne vsebujejo ključa; pri ostalih
    zapišemo samo vrsto napake (podrobnosti so v dnevniku), da v bazo ne pride kaj občutljivega.
    """
    if isinstance(exc, RiotApiError):
        message = str(exc)
    else:
        message = f"Nepričakovana napaka ({type(exc).__name__})"
    return message[:500]
