"""Napredek analiz (ADR-0004): delavec ob vsakem koraku objavi obvestilo v Redis, API ga prek SSE
posreduje brskalniku.

Vir resnice je stanje v bazi (live_analyses.status). Obvestilo v Redis vsebuje samo ID analize
in API le zbudi, da stanje ponovno prebere. Če se obvestilo izgubi (npr. API se je naročil
prepozno), API stanje vseeno prebere ob naslednjem izteku čakanja.
"""

import time
import uuid
from collections.abc import Callable

from redis import Redis

CHANNEL_PREFIX = "analysis:"

# Obvesti naročnike, da se je stanje analize spremenilo.
ProgressNotifier = Callable[[uuid.UUID], None]


def channel(analysis_id: uuid.UUID) -> str:
    return f"{CHANNEL_PREFIX}{analysis_id}"


def no_notify(analysis_id: uuid.UUID) -> None:
    """Brez obveščanja (testi, zagon brez Redis); SSE stanje vseeno bere iz baze."""


class RedisProgressNotifier:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def __call__(self, analysis_id: uuid.UUID) -> None:
        self._redis.publish(channel(analysis_id), "changed")


class ProgressWaiter:
    """Čaka na obvestilo za eno analizo (ali na iztek časa). Uporablja ga SSE tok."""

    def wait(self, timeout: float) -> None:  # pragma: no cover - vmesnik
        raise NotImplementedError

    def close(self) -> None:
        pass


class RedisProgressWaiter(ProgressWaiter):
    def __init__(self, redis: Redis, analysis_id: uuid.UUID) -> None:
        self._pubsub = redis.pubsub(ignore_subscribe_messages=True)
        # Naročimo se PRED prvim branjem stanja iz baze, da ne zgrešimo spremembe vmes.
        self._pubsub.subscribe(channel(analysis_id))

    def wait(self, timeout: float) -> None:
        self._pubsub.get_message(timeout=timeout)

    def close(self) -> None:
        self._pubsub.close()


class PollingProgressWaiter(ProgressWaiter):
    """Brez Redis: samo počaka in SSE stanje ponovno prebere iz baze."""

    def wait(self, timeout: float) -> None:
        time.sleep(timeout)
