"""Skupne FastAPI odvisnosti (prijavljen uporabnik ...)."""

import uuid
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from app.analysis.guest_limit import GuestLimiter, NoGuestLimit, RedisGuestLimiter
from app.analysis.progress import PollingProgressWaiter, ProgressWaiter, RedisProgressWaiter
from app.core.config import Settings, get_settings
from app.core.ip_limit import IpLimitRule, IpRateLimiter
from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.riot.client import RiotClient
from app.riot.factory import build_riot_client

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

_bearer = HTTPBearer(auto_error=False)


def unauthorized(detail: str = "Prijava je potrebna.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_token(credentials.credentials, "access", settings)
    except InvalidTokenError:
        raise unauthorized("Seja je potekla ali ni veljavna.") from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized("Seja je potekla ali ni veljavna.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_admin_user(user: CurrentUser) -> User:
    """Prijavljen administrator; navaden uporabnik dobi 403."""
    if user.role is not UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Potrebna je vloga administrator.")
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]


@lru_cache
def _shared_riot_client() -> RiotClient:
    # En klient na proces: ponovno uporabi HTTP in Redis povezave.
    return build_riot_client(get_settings())


def get_riot_client() -> RiotClient:
    return _shared_riot_client()


Riot = Annotated[RiotClient, Depends(get_riot_client)]


def get_optional_user(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """Prijavljen uporabnik ali None za gosta (npr. analiza je na voljo tudi gostom)."""
    if credentials is None:
        return None
    return get_current_user(db, settings, credentials)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]

AnalysisQueue = Callable[[uuid.UUID], None]


def get_analysis_queue() -> AnalysisQueue:
    """Pošlje analizo v Celery vrsto (v testih se zamenja s takojšnjim izvajanjem)."""
    from app.worker import run_analysis  # uvoz šele ob uporabi: API ne potrebuje brokerja ob zagonu

    return lambda analysis_id: run_analysis.delay(str(analysis_id))


Queue = Annotated[AnalysisQueue, Depends(get_analysis_queue)]


ProgressWaiterFactory = Callable[[uuid.UUID], ProgressWaiter]


@lru_cache
def _shared_redis() -> Redis | None:
    url = get_settings().redis_url
    return Redis.from_url(url.get_secret_value()) if url else None


def get_progress_waiter_factory() -> ProgressWaiterFactory:
    """Čakanje na napredek analize: prek Redis obvestil ali (brez Redis) s periodičnim branjem."""
    redis = _shared_redis()
    if redis is None:
        return lambda analysis_id: PollingProgressWaiter()
    return lambda analysis_id: RedisProgressWaiter(redis, analysis_id)


WaiterFactory = Annotated[ProgressWaiterFactory, Depends(get_progress_waiter_factory)]


def get_guest_limiter() -> GuestLimiter:
    """Dnevna omejitev analiz za goste (v testih se zamenja z omejevalnikom na fakeredis)."""
    redis = _shared_redis()
    return RedisGuestLimiter(redis) if redis is not None else NoGuestLimit()


GuestLimit = Annotated[GuestLimiter, Depends(get_guest_limiter)]


def get_ip_limiter() -> IpRateLimiter | None:
    """Omejevalnik zahtev po IP (None brez Redis, npr. lokalni razvoj brez REDIS_URL)."""
    redis = _shared_redis()
    return IpRateLimiter(redis) if redis is not None else None


def client_ip(request: Request) -> str:
    # IP neposredno iz povezave; glavi X-Forwarded-For ne zaupamo (odjemalec bi jo ponaredil).
    return request.client.host if request.client else "unknown"


def limit_by_ip(rule: IpLimitRule, message: str) -> Callable[..., None]:
    """Odvisnost, ki po preseženi meji za ta IP vrne 429 z glavo Retry-After."""

    def dependency(
        request: Request,
        limiter: Annotated[IpRateLimiter | None, Depends(get_ip_limiter)],
    ) -> None:
        if limiter is None:
            return
        result = limiter.hit(rule, client_ip(request))
        if not result.allowed:
            minutes = max(1, -(-result.retry_after // 60))
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"{message} Poskusi znova čez {minutes} min.",
                headers={"Retry-After": str(result.retry_after)},
            )

    return dependency
