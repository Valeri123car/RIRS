"""Povezava Riot računa z verifikacijo profilne ikone (US-01, F01)."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import CurrentUser, DbSession, Riot
from app.models.riot_account import RiotAccount
from app.models.riot_verification import RiotVerification
from app.riot.errors import RiotApiError, RiotNotFoundError
from app.riot.platforms import PLATFORM_LABELS

router = APIRouter(prefix="/riot-accounts", tags=["riot-accounts"])

VERIFICATION_TIME = timedelta(minutes=10)
# Privzete profilne ikone, ki jih ima vsak račun (ID 0–28).
DEFAULT_ICON_IDS = range(29)

# Riot: ime 3–16 znakov, oznaka 3–5 znakov.
GAME_NAME_LENGTH = (3, 16)
TAG_LINE_LENGTH = (3, 5)

Platform = Literal["eun1", "euw1", "tr1", "ru", "na1", "br1", "la1", "la2", "kr", "jp1"]


class VerificationStart(BaseModel):
    riot_id: str = Field(max_length=32, examples=["Luka#EUNE"])
    platform: Platform

    @field_validator("riot_id")
    @classmethod
    def validate_riot_id(cls, value: str) -> str:
        game_name, separator, tag_line = value.strip().rpartition("#")
        game_name, tag_line = game_name.strip(), tag_line.strip()
        if not separator:
            raise ValueError("Riot ID mora biti v obliki ime#oznaka.")
        if not GAME_NAME_LENGTH[0] <= len(game_name) <= GAME_NAME_LENGTH[1]:
            raise ValueError("Ime mora imeti 3–16 znakov.")
        if not (TAG_LINE_LENGTH[0] <= len(tag_line) <= TAG_LINE_LENGTH[1] and tag_line.isalnum()):
            raise ValueError("Oznaka mora imeti 3–5 črk ali številk.")
        return f"{game_name}#{tag_line}"


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    puuid: str
    game_name: str
    tag_line: str
    platform: str
    icon_id: int
    expires_at: datetime


def riot_unavailable() -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Riot API trenutno ni dosegljiv, poskusi kasneje."
    )


@router.post("/verifications", response_model=VerificationOut, status_code=status.HTTP_201_CREATED)
def start_verification(
    body: VerificationStart, user: CurrentUser, db: DbSession, riot: Riot
) -> RiotVerification:
    game_name, tag_line = body.riot_id.rsplit("#", 1)
    not_in_region = HTTPException(
        status.HTTP_404_NOT_FOUND,
        f"Igralca s tem Riot ID ni v regiji {PLATFORM_LABELS[body.platform]}",
    )
    try:
        account = riot.get_account(game_name, tag_line, body.platform)
        # Account-V1 je regionalen; Summoner-V4 potrdi, da račun igra na izbrani platformi.
        summoner = riot.get_summoner(account.puuid, body.platform)
    except RiotNotFoundError:
        raise not_in_region from None
    except RiotApiError:
        raise riot_unavailable() from None

    existing = db.get(RiotAccount, account.puuid)
    if existing is not None and existing.verified_at is not None:
        if existing.user_id == user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ta Riot račun je že povezan s tabo.")
        if existing.user_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ta Riot račun je že povezan z drugim uporabnikom."
            )

    # Ikona mora biti drugačna od trenutne, sicer bi bil račun "verificiran" brez dokaza.
    icon_id = secrets.choice([i for i in DEFAULT_ICON_IDS if i != summoner.profile_icon_id])
    verification = RiotVerification(
        user_id=user.id,
        puuid=account.puuid,
        game_name=account.game_name,
        tag_line=account.tag_line,
        platform=body.platform,
        icon_id=icon_id,
        expires_at=datetime.now(UTC) + VERIFICATION_TIME,
    )
    db.add(verification)
    db.commit()
    return verification
