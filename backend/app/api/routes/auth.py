"""Registracija, prijava, osvežitev žetona in odjava (US-01, F01)."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AppSettings, CurrentUser, DbSession, limit_by_ip, unauthorized
from app.core.config import Settings
from app.core.ip_limit import IpLimitRule
from app.core.security import (
    InvalidTokenError,
    create_token,
    decode_token_with_version,
    hash_password,
    token_lifetime,
    verify_password,
)
from app.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"
LOGIN_FAILED = "Napačna e-pošta ali geslo."

# Omejitev poskusov po IP (#43): ugibanje gesel in preverjanje, katere e-pošte obstajajo.
LOGIN_LIMIT = IpLimitRule("auth-login", limit=10, window_seconds=15 * 60)
REGISTER_LIMIT = IpLimitRule("auth-register", limit=5, window_seconds=60 * 60)
TOO_MANY = {429: {"description": "Preveč poskusov z istega IP naslova."}}

# Zgostitev naključnega gesla: pri neznanem uporabniku vseeno preverimo geslo,
# da se po času odgovora ne da ugotoviti, katere e-pošte so registrirane.
_DUMMY_HASH = hash_password("neobstojec-uporabnik")


class Credentials(BaseModel):
    email: EmailStr
    # Argon2 sprejme dolga gesla, zgornja meja prepreči zlorabo z ogromnimi vnosi.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(Credentials):
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def _issue_tokens(response: Response, user: User, settings: Settings) -> TokenOut:
    refresh = create_token(user.id, "refresh", settings, version=user.token_version)
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=int(token_lifetime("refresh", settings).total_seconds()),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return TokenOut(
        access_token=create_token(user.id, "access", settings),
        expires_in=int(token_lifetime("access", settings).total_seconds()),
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses=TOO_MANY,
    dependencies=[Depends(limit_by_ip(REGISTER_LIMIT, "Preveč registracij z istega naslova."))],
)
def register(body: Credentials, db: DbSession) -> User:
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Uporabnik s to e-pošto že obstaja.")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # hkratna registracija z isto e-pošto
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Uporabnik s to e-pošto že obstaja."
        ) from None
    return user


@router.post(
    "/login",
    response_model=TokenOut,
    responses=TOO_MANY,
    dependencies=[Depends(limit_by_ip(LOGIN_LIMIT, "Preveč poskusov prijave."))],
)
def login(body: LoginRequest, response: Response, db: DbSession, settings: AppSettings) -> TokenOut:
    user = db.scalars(select(User).where(User.email == body.email)).one_or_none()
    password_ok = verify_password(user.password_hash if user else _DUMMY_HASH, body.password)
    if user is None or not password_ok:
        raise unauthorized(LOGIN_FAILED)
    return _issue_tokens(response, user, settings)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenOut:
    if not refresh_token:
        raise unauthorized()
    user = _user_from_refresh_token(db, refresh_token, settings)
    if user is None:
        raise unauthorized("Seja je potekla, prijavi se znova.")
    return _issue_tokens(response, user, settings)


def _user_from_refresh_token(db: Session, token: str, settings: Settings) -> User | None:
    """Uporabnik iz veljavnega osvežilnega žetona, ki ni bil preklican z odjavo."""
    try:
        user_id, version = decode_token_with_version(token, "refresh", settings)
    except InvalidTokenError:
        return None
    user = db.get(User, user_id)
    if user is None or user.token_version != version:
        return None
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    # Prekliče vse osvežilne žetone uporabnika (tudi morebiti ukradene kopije piškotka).
    user = _user_from_refresh_token(db, refresh_token, settings) if refresh_token else None
    if user is not None:
        user.token_version += 1
        db.commit()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
