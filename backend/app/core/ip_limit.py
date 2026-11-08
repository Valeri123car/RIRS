"""Omejevanje števila zahtev po IP naslovu (fiksno časovno okno v Redis).

Uporablja se za prijavo in registracijo (#43): prepreči ugibanje gesel in množično preverjanje,
katere e-pošte so registrirane. Namesto IP naslova hranimo samo njegov SHA-256 odtis.
"""

import hashlib
import time
from dataclasses import dataclass

from redis import Redis


@dataclass(frozen=True)
class IpLimitResult:
    allowed: bool
    # Sekunde do konca okna (za glavo Retry-After).
    retry_after: int


@dataclass(frozen=True)
class IpLimitRule:
    name: str
    limit: int
    window_seconds: int


class IpRateLimiter:
    def __init__(self, redis: Redis, prefix: str = "iplimit") -> None:
        self._redis = redis
        self._prefix = prefix

    def hit(self, rule: IpLimitRule, ip: str, now: float | None = None) -> IpLimitResult:
        now = time.time() if now is None else now
        window = int(now // rule.window_seconds)
        retry_after = max(1, int((window + 1) * rule.window_seconds - now))
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()
        key = f"{self._prefix}:{rule.name}:{window}:{ip_hash}"
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, retry_after)
        count, _ = pipe.execute()
        return IpLimitResult(allowed=count <= rule.limit, retry_after=retry_after)
