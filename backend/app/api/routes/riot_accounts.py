"""Povezava Riot računa z verifikacijo profilne ikone (US-01, F01)."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, Riot
from app.models.riot_account import RiotAccount
from app.models.riot_verification import RiotVerification
from app.models.user import User
from app.riot.client import RiotClient
from app.riot.errors import RiotApiError, RiotNotFoundError
from app.riot.fixture_client import FixtureRiotClient
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
    # True v načinu fixtures: zamenjavo ikone je mogoče simulirati (razvoj brez ključa).
    simulation_available: bool = False


class RiotAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    puuid: str
    game_name: str
    tag_line: str
    platform: str
    verified_at: datetime | None


def riot_unavailable() -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Riot API trenutno ni dosegljiv, poskusi kasneje."
    )


@router.post("/verifications", response_model=VerificationOut, status_code=status.HTTP_201_CREATED)
def start_verification(
    body: VerificationStart, user: CurrentUser, db: DbSession, riot: Riot
) -> VerificationOut:
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

    _ensure_linkable(db.get(RiotAccount, account.puuid), user)

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
    return _verification_out(verification, riot)


@router.post("/verifications/{verification_id}/check", response_model=RiotAccountOut)
def check_verification(
    verification_id: int, user: CurrentUser, db: DbSession, riot: Riot
) -> RiotAccount:
    verification = _own_verification(db, verification_id, user)
    if verification.expires_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_410_GONE, "Čas za verifikacijo je potekel, začni znova.")
    try:
        summoner = riot.get_summoner(verification.puuid, verification.platform)
    except RiotApiError:
        raise riot_unavailable() from None
    if summoner.profile_icon_id != verification.icon_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ikona na računu še ni zamenjana")

    # Pogoj ponovno preverimo: račun je lahko medtem verificiral nekdo drug.
    account = db.get(RiotAccount, verification.puuid, with_for_update=True)
    _ensure_linkable(account, user)
    if account is None:
        account = RiotAccount(puuid=verification.puuid)
        db.add(account)
    account.game_name = verification.game_name
    account.tag_line = verification.tag_line
    account.platform = verification.platform
    account.user_id = user.id
    account.verified_at = datetime.now(UTC)
    db.execute(delete(RiotVerification).where(RiotVerification.puuid == verification.puuid))
    db.commit()
    return account


@router.post(
    "/verifications/{verification_id}/simulate-icon", status_code=status.HTTP_204_NO_CONTENT
)
def simulate_icon_change(
    verification_id: int, user: CurrentUser, db: DbSession, riot: Riot
) -> Response:
    """Samo v načinu fixtures: "nastavi" zahtevano ikono, da je verifikacijo mogoče preizkusiti."""
    verification = _own_verification(db, verification_id, user)
    if not isinstance(riot, FixtureRiotClient):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Simulacija ni na voljo.")
    riot.set_profile_icon(verification.puuid, verification.icon_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[RiotAccountOut])
def my_accounts(user: CurrentUser, db: DbSession) -> list[RiotAccount]:
    """Verificirani Riot računi prijavljenega uporabnika (prikaz v profilu)."""
    query = (
        select(RiotAccount)
        .where(RiotAccount.user_id == user.id, RiotAccount.verified_at.is_not(None))
        .order_by(RiotAccount.verified_at)
    )
    return list(db.scalars(query))


def _ensure_linkable(account: RiotAccount | None, user: User) -> None:
    if account is None or account.verified_at is None or account.user_id is None:
        return
    if account.user_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ta Riot račun je že povezan s tabo.")
    raise HTTPException(
        status.HTTP_409_CONFLICT, "Ta Riot račun je že povezan z drugim uporabnikom."
    )


def _own_verification(db: Session, verification_id: int, user: User) -> RiotVerification:
    verification = db.get(RiotVerification, verification_id)
    # Tuja verifikacija je za uporabnika enaka neobstoječi (ne razkrijemo, da obstaja).
    if verification is None or verification.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verifikacija ne obstaja.")
    return verification


def _verification_out(verification: RiotVerification, riot: RiotClient) -> VerificationOut:
    out = VerificationOut.model_validate(verification)
    out.simulation_available = isinstance(riot, FixtureRiotClient)
    return out
