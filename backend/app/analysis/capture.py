"""Zajem aktivne tekme: Riot ID → puuid → Spectator-V5 → 10 udeležencev (US-02)."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.progress import ProgressNotifier, no_notify
from app.models.champion import Champion
from app.models.live_analysis import AnalysisStatus, LiveAnalysis
from app.riot.client import RiotClient
from app.riot.errors import RiotApiError, RiotNotFoundError
from app.riot.models import ActiveGame
from app.riot.platforms import PLATFORM_LABELS

NOT_IN_GAME = "Igralec trenutno ni v tekmi"
RIOT_UNAVAILABLE = "Riot API trenutno ni dosegljiv, poskusi kasneje."


def capture_active_game(
    session: Session,
    riot: RiotClient,
    analysis_id: uuid.UUID,
    notify: ProgressNotifier = no_notify,
) -> None:
    """Izpolni analizo z udeleženci aktivne tekme ali jo označi z razlogom neuspeha.

    Po vsaki spremembi stanja pokliče notify, da SSE tok (GET /analyses/{id}/events) takoj
    pošlje napredek.
    """
    analysis = session.get(LiveAnalysis, analysis_id)
    if analysis is None:
        return

    def set_status(status: AnalysisStatus, error: str | None = None) -> None:
        analysis.status = status
        analysis.error = error
        session.commit()
        notify(analysis.id)

    set_status(AnalysisStatus.CAPTURING)

    try:
        account = riot.get_account(analysis.game_name, analysis.tag_line, analysis.platform)
        analysis.puuid = account.puuid
        # Account-V1 je regionalen; Summoner-V4 potrdi, da igralec igra na izbrani platformi.
        riot.get_summoner(account.puuid, analysis.platform)
        game = riot.get_active_game(account.puuid, analysis.platform)
    except RiotNotFoundError:
        label = PLATFORM_LABELS.get(analysis.platform, analysis.platform)
        set_status(AnalysisStatus.FAILED, f"Igralca s tem Riot ID ni v regiji {label}")
        return
    except RiotApiError:
        set_status(AnalysisStatus.FAILED, RIOT_UNAVAILABLE)
        return

    if game is None:
        set_status(AnalysisStatus.NOT_IN_GAME, NOT_IN_GAME)
        return

    analysis.game_id = game.game_id
    analysis.participants = _participants(session, game, account.puuid)
    set_status(AnalysisStatus.COMPLETED)


def _participants(session: Session, game: ActiveGame, target_puuid: str) -> list[dict[str, Any]]:
    champion_ids = {p.champion_id for p in game.participants}
    champions = {
        c.id: c for c in session.scalars(select(Champion).where(Champion.id.in_(champion_ids)))
    }
    result = []
    for p in game.participants:
        champion = champions.get(p.champion_id)
        result.append(
            {
                "puuid": p.puuid,
                "riot_id": p.riot_id,
                "team_id": p.team_id,
                "champion_id": p.champion_id,
                # None, če Data Dragon še ni uvožen (python -m app.ddragon).
                "champion_name": champion.name if champion else None,
                "champion_slug": champion.slug if champion else None,
                "spell1_id": p.spell1_id,
                "spell2_id": p.spell2_id,
                "is_target": p.puuid == target_puuid,
            }
        )
    return result
