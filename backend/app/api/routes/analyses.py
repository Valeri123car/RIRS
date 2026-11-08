"""Analiza aktivne tekme (US-02): zagon in stanje."""

import time
import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession, OptionalUser, Queue, WaiterFactory
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
    created_at: datetime


@router.post("", response_model=AnalysisOut, status_code=status.HTTP_202_ACCEPTED)
def start_analysis(
    body: RiotIdInput, user: OptionalUser, db: DbSession, queue: Queue
) -> LiveAnalysis:
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


def _existing_analysis(analysis_id: uuid.UUID, db: DbSession) -> uuid.UUID:
    if db.get(LiveAnalysis, analysis_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analiza ne obstaja.")
    return analysis_id


ExistingAnalysisId = Annotated[uuid.UUID, Depends(_existing_analysis)]


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: ExistingAnalysisId, db: DbSession) -> LiveAnalysis:
    return db.get_one(LiveAnalysis, analysis_id)


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
