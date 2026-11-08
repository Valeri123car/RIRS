"""Omejevalnik klicev Riot API, skupen vsem procesom (API in delavci) prek Redis.

Riot omejuje klice po oknih za vsako regijo posebej (razvojni ključ: 20 klicev / 1 s in
100 klicev / 2 min). Okno se začne ob prvem klicu, zato števec dobi rok trajanja ob prvem
povečanju. Preverjanje in povečanje vseh oken je ena Lua skripta, torej atomarno.
"""

import time
from collections.abc import Callable, Sequence
from typing import NamedTuple

from redis import Redis


class RateLimit(NamedTuple):
    calls: int
    seconds: int


DEV_KEY_LIMITS: tuple[RateLimit, ...] = (RateLimit(20, 1), RateLimit(100, 120))

# Naše okno se začne malo pred Riotovim (čas potovanja zahteve), zato ga podaljšamo.
WINDOW_PADDING_MS = 250

# KEYS = ključi oken, ARGV = pari (omejitev, trajanje okna v ms).
# Vrne 0, če je klic dovoljen (in ga prešteje), sicer število ms do sprostitve.
_ACQUIRE_SCRIPT = """
local wait = 0
for i, key in ipairs(KEYS) do
  local limit = tonumber(ARGV[2 * i - 1])
  local count = tonumber(redis.call('GET', key) or '0')
  if count >= limit then
    local ttl = redis.call('PTTL', key)
    if ttl < 0 then ttl = tonumber(ARGV[2 * i]) end
    if ttl > wait then wait = ttl end
  end
end
if wait > 0 then return wait end
for i, key in ipairs(KEYS) do
  if redis.call('INCR', key) == 1 then
    redis.call('PEXPIRE', key, ARGV[2 * i])
  end
end
return 0
"""


class RedisRateLimiter:
    def __init__(
        self,
        redis: Redis,
        limits: Sequence[RateLimit] = DEV_KEY_LIMITS,
        *,
        prefix: str = "riot:rl",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._limits = tuple(limits)
        self._prefix = prefix
        self._sleep = sleep
        self._script = redis.register_script(_ACQUIRE_SCRIPT)

    def try_acquire(self, routing: str) -> float:
        """Poskusi porabiti en klic; vrne 0 ali število sekund do naslednjega poskusa."""
        keys = [f"{self._prefix}:{routing}:{limit.seconds}" for limit in self._limits]
        args: list[int] = []
        for limit in self._limits:
            args += [limit.calls, limit.seconds * 1000 + WINDOW_PADDING_MS]
        return int(self._script(keys=keys, args=args)) / 1000

    def acquire(self, routing: str) -> None:
        """Počaka, dokler klic na dani regiji ni dovoljen, in ga prešteje."""
        while (wait := self.try_acquire(routing)) > 0:
            self._sleep(wait)
