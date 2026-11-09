"""Analiza aktivne tekme (US-02): zagon in stanje."""

import time
import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.analysis.guest_limit import GUEST_DAILY_LIMIT
from app.analysis.pipeline import build_matchup
from app.api.deps import (
    CurrentUser,
    DbSession,
    GuestLimit,
    OptionalUser,
    Queue,
    WaiterFactory,
    client_ip,
)
from app.api.schemas import RiotIdInput
from app.models.live_analysis import AnalysisStatus, LiveAnalysis

router = APIRouter(prefix="/analyses", tags=["analyses"])


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: AnalysisStatus
    error: str | None
    game_name: str
    tag_line: str
    platform: str
    participants: list[dict[str, Any]]
    # Profil nasprotne sestave (US-03); None, dokler korak profiliranja ni končan.
    enemy_comp: dict[str, Any] | None
    # Priporočilo builda (US-04); None, dokler korak ni končan ali če šampiona ni v bazi.
    recommendation: dict[str, Any] | None
    # Matchup kartica (US-05); opponent je None, če linijskega nasprotnika ni bilo mogoče določiti.
    matchup: dict[str, Any] | None
    # Profil sloga nasprotnikov (US-06) po puuid; None, dokler korak profiliranja ni končan.
    style: dict[str, Any] | None
    created_at: datetime


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    status: AnalysisStatus
    game_name: str
    tag_line: str
    platform: str
    # Šampion igralca (is_target) in nasprotna ekipa za hiter pregled seznama.
    champion_name: str | None
    enemy_champions: list[str]
    created_at: datetime


MAX_LISTED_ANALYSES = 50


GUEST_LIMIT_MESSAGE = (
    f"Kot gost lahko na dan zaženeš največ {GUEST_DAILY_LIMIT} analize. "
    "Registriraj se brezplačno in analiziraj brez omejitve."
)


@router.post(
    "",
    response_model=AnalysisOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses={429: {"description": GUEST_LIMIT_MESSAGE}},
)
def start_analysis(
    body: RiotIdInput,
    request: Request,
    user: OptionalUser,
    db: DbSession,
    queue: Queue,
    guest_limit: GuestLimit,
) -> LiveAnalysis:
    if user is None:
        limit = guest_limit.hit(client_ip(request))
        if not limit.allowed:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                GUEST_LIMIT_MESSAGE,
                headers={"Retry-After": str(limit.retry_after)},
            )
    analysis = LiveAnalysis(
        user_id=user.id if user else None,
        game_name=body.game_name,
        tag_line=body.tag_line,
        platform=body.platform,
    )
    db.add(analysis)
    db.commit()
    # Riot API kliče samo delavec (ADR-0004); API takoj vrne ID.
    queue(analysis.id)
    db.refresh(analysis)
    return analysis


@router.get("", response_model=list[AnalysisSummary])
def list_my_analyses(user: CurrentUser, db: DbSession) -> list[AnalysisSummary]:
    """Analize prijavljenega uporabnika, najnovejše najprej."""
    rows = db.scalars(
        select(LiveAnalysis)
        .where(LiveAnalysis.user_id == user.id)
        .order_by(LiveAnalysis.created_at.desc())
        .limit(MAX_LISTED_ANALYSES)
    )
    summaries = []
    for analysis in rows:
        target = next((p for p in analysis.participants if p["is_target"]), None)
        enemies = [
            p["champion_name"]
            for p in analysis.participants
            if target is not None and p["team_id"] != target["team_id"] and p["champion_name"]
        ]
        summaries.append(
            AnalysisSummary(
                id=analysis.id,
                status=analysis.status,
                game_name=analysis.game_name,
                tag_line=analysis.tag_line,
                platform=analysis.platform,
                champion_name=target["champion_name"] if target else None,
                enemy_champions=enemies,
                created_at=analysis.created_at,
            )
        )
    return summaries


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_analysis(analysis_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Izbriše analizo, ki pripada prijavljenemu uporabniku (tuja ali neobstoječa: 404)."""
    analysis = db.get(LiveAnalysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analiza ne obstaja.")
    db.delete(analysis)
    db.commit()


def _existing_analysis(analysis_id: uuid.UUID, db: DbSession) -> uuid.UUID:
    if db.get(LiveAnalysis, analysis_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analiza ne obstaja.")
    return analysis_id


ExistingAnalysisId = Annotated[uuid.UUID, Depends(_existing_analysis)]


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: ExistingAnalysisId, db: DbSession) -> LiveAnalysis:
    return db.get_one(LiveAnalysis, analysis_id)


@router.get("/{analysis_id}/matchup")
def get_matchup(
    analysis_id: ExistingAnalysisId,
    db: DbSession,
    opponent: Annotated[int, Query(ge=1, le=100_000, description="ID nasprotnega šampiona")],
) -> dict[str, Any]:
    """Matchup kartica proti izbranemu nasprotniku (eden izmed petih nasprotnih šampionov)."""
    analysis = db.get_one(LiveAnalysis, analysis_id)
    if analysis.status != AnalysisStatus.COMPLETED or not analysis.participants:
        raise HTTPException(status.HTTP_409_CONFLICT, "Analiza še ni končana ali nima tekme.")
    try:
        return build_matchup(db, analysis, opponent_id=opponent)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


# Končna stanja: po njih se tok zapre.
FINAL_STATUSES = {AnalysisStatus.COMPLETED, AnalysisStatus.NOT_IN_GAME, AnalysisStatus.FAILED}
# Najdaljše čakanje na obvestilo, preden stanje vseeno ponovno preberemo iz baze.
POLL_INTERVAL = 1.0
# Najdaljše trajanje enega toka; brskalnik (EventSource) se nato sam ponovno poveže.
STREAM_TIMEOUT = 60.0


@router.get("/{analysis_id}/events", response_class=EventSourceResponse)
def analysis_events(
    analysis_id: ExistingAnalysisId, db: DbSession, waiters: WaiterFactory
) -> Iterator[ServerSentEvent]:
    """SSE tok napredka: dogodek "progress" ob vsaki spremembi stanja, do končnega stanja.

    Vsak dogodek vsebuje celotno analizo (enako kot GET /analyses/{id}).
    """
    waiter = waiters(analysis_id)  # naročilo pred prvim branjem: sprememba vmes se ne izgubi
    deadline = time.monotonic() + STREAM_TIMEOUT
    last_status: AnalysisStatus | None = None
    try:
        while True:
            db.expire_all()
            analysis = db.get_one(LiveAnalysis, analysis_id)
            current = analysis.status
            payload = AnalysisOut.model_validate(analysis).model_dump(mode="json")
            db.rollback()  # med čakanjem ne držimo odprte transakcije
            if current != last_status:
                last_status = current
                yield ServerSentEvent(event="progress", data=payload, retry=2000)
            if current in FINAL_STATUSES or time.monotonic() >= deadline:
                return
            waiter.wait(POLL_INTERVAL)
    finally:
        waiter.close()
