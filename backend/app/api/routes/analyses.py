"""Analiza aktivne tekme (US-02): zagon in stanje."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession, OptionalUser, Queue
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


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: uuid.UUID, db: DbSession) -> LiveAnalysis:
    analysis = db.get(LiveAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analiza ne obstaja.")
    return analysis
