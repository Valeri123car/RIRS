import fakeredis
import pytest

from app.riot.rate_limiter import RateLimit, RedisRateLimiter


class FakeSleep:
    """Namesto čakanja zabeleži čas in "pretečejo" vsa okna (izbriše ključe)."""

    def __init__(self, redis: fakeredis.FakeRedis) -> None:
        self.redis = redis
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.redis.flushall()


@pytest.fixture
def redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


def make_limiter(redis, limits) -> tuple[RedisRateLimiter, FakeSleep]:
    sleep = FakeSleep(redis)
    return RedisRateLimiter(redis, limits, sleep=sleep), sleep


def test_klici_do_omejitve_ne_cakajo(redis):
    limiter, sleep = make_limiter(redis, [RateLimit(calls=3, seconds=1)])

    for _ in range(3):
        limiter.acquire("europe")

    assert sleep.calls == []


def test_klic_nad_omejitvijo_pocaka_do_konca_okna(redis):
    limiter, sleep = make_limiter(redis, [RateLimit(calls=2, seconds=1)])

    for _ in range(3):
        limiter.acquire("europe")

    assert len(sleep.calls) == 1
    assert 0 < sleep.calls[0] <= 1.5


def test_upostevano_je_tudi_daljse_okno(redis):
    limiter, sleep = make_limiter(redis, [RateLimit(calls=5, seconds=1), RateLimit(3, 120)])

    for _ in range(4):
        limiter.acquire("eun1")

    assert len(sleep.calls) == 1
    assert 100 < sleep.calls[0] <= 121


def test_omejitve_veljajo_loceno_za_vsako_regijo(redis):
    limiter, sleep = make_limiter(redis, [RateLimit(calls=1, seconds=1)])

    limiter.acquire("europe")
    limiter.acquire("eun1")

    assert sleep.calls == []


def test_zavrnjen_klic_ne_porabi_kvote(redis):
    limiter, _ = make_limiter(redis, [RateLimit(calls=10, seconds=1), RateLimit(2, 120)])

    limiter.acquire("europe")
    limiter.acquire("europe")
    # Daljše okno je polno: kratko okno ne sme šteti zavrnjenih poskusov.
    assert limiter.try_acquire("europe") > 0
    assert limiter.try_acquire("europe") > 0

    assert int(redis.get("riot:rl:europe:1")) == 2
