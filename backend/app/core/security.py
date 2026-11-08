"""Gesla (Argon2id) in JWT žetoni (kratkoživ dostopni + osvežilni)."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings

TokenKind = Literal["access", "refresh"]

ALGORITHM = "HS256"
MIN_SECRET_LENGTH = 32

# Privzete nastavitve argon2-cffi so Argon2id s priporočenimi parametri (RFC 9106).
_hasher = PasswordHasher()


class AuthConfigError(RuntimeError):
    pass


class InvalidTokenError(Exception):
    """Žeton je neveljaven, potekel ali napačne vrste."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _secret(settings: Settings) -> str:
    secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else ""
    if len(secret) < MIN_SECRET_LENGTH:
        raise AuthConfigError(
            f"JWT_SECRET mora biti nastavljen in imeti vsaj {MIN_SECRET_LENGTH} znakov."
        )
    return secret


def token_lifetime(kind: TokenKind, settings: Settings) -> timedelta:
    if kind == "access":
        return timedelta(minutes=settings.access_token_minutes)
    return timedelta(days=settings.refresh_token_days)


def create_token(
    user_id: int, kind: TokenKind, settings: Settings, *, now: datetime | None = None
) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": kind,
        "iat": issued,
        "exp": issued + token_lifetime(kind, settings),
    }
    return jwt.encode(payload, _secret(settings), algorithm=ALGORITHM)


def decode_token(token: str, kind: TokenKind, settings: Settings) -> int:
    """Vrne ID uporabnika ali sproži InvalidTokenError."""
    try:
        # algorithms=[ALGORITHM] zavrne nepodpisane žetone ("none") in zamenjavo algoritma.
        payload = jwt.decode(
            token, _secret(settings), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]}
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Neveljaven žeton") from exc
    if payload.get("type") != kind:
        raise InvalidTokenError("Napačna vrsta žetona")
    try:
        return int(payload["sub"])
    except ValueError as exc:
        raise InvalidTokenError("Neveljaven žeton") from exc
