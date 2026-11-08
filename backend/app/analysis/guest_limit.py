"""Dnevna omejitev analiz za goste (US-02): največ GUEST_DAILY_LIMIT analiz na IP naslov na dan.

Števec je v Redis (skupen vsem procesom API) in poteče ob polnoči (UTC). Namesto IP naslova
hranimo samo njegov SHA-256 odtis, da v Redis ni osebnih podatkov v berljivi obliki.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from redis import Redis

GUEST_DAILY_LIMIT = 3


@dataclass(frozen=True)
class LimitResult:
    allowed: bool
    # Sekunde do ponastavitve števca (za glavo Retry-After).
    retry_after: int


class GuestLimiter(Protocol):
    def hit(self, ip: str) -> LimitResult: ...


def _seconds_until_midnight(now: datetime) -> int:
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((midnight - now).total_seconds()))


class RedisGuestLimiter:
    def __init__(
        self, redis: Redis, limit: int = GUEST_DAILY_LIMIT, prefix: str = "guest:analyses"
    ):
        self._redis = redis
        self._limit = limit
        self._prefix = prefix

    def hit(self, ip: str, now: datetime | None = None) -> LimitResult:
        now = now or datetime.now(UTC)
        ttl = _seconds_until_midnight(now)
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()
        key = f"{self._prefix}:{now:%Y-%m-%d}:{ip_hash}"
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        count, _ = pipe.execute()
        return LimitResult(allowed=count <= self._limit, retry_after=ttl)


class NoGuestLimit:
    """Brez Redis (lokalni razvoj brez REDIS_URL): omejitve ni."""

    def hit(self, ip: str) -> LimitResult:
        return LimitResult(allowed=True, retry_after=0)
