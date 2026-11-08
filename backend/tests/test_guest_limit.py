"""Dnevna omejitev analiz za goste."""

from datetime import UTC, datetime

import fakeredis

from app.analysis.guest_limit import RedisGuestLimiter


def test_stirje_poskusi_istega_ip():
    limiter = RedisGuestLimiter(fakeredis.FakeRedis())
    now = datetime(2026, 11, 8, 23, 0, tzinfo=UTC)

    results = [limiter.hit("203.0.113.5", now) for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[-1].retry_after == 3600  # do polnoči


def test_razlicni_ip_imata_loceno_omejitev():
    limiter = RedisGuestLimiter(fakeredis.FakeRedis())
    now = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
    for _ in range(3):
        limiter.hit("203.0.113.5", now)

    assert limiter.hit("203.0.113.6", now).allowed


def test_naslednji_dan_se_stevec_ponastavi():
    limiter = RedisGuestLimiter(fakeredis.FakeRedis())
    for _ in range(3):
        limiter.hit("203.0.113.5", datetime(2026, 11, 8, 22, 0, tzinfo=UTC))

    assert limiter.hit("203.0.113.5", datetime(2026, 11, 9, 0, 5, tzinfo=UTC)).allowed


def test_ip_ni_shranjen_v_berljivi_obliki():
    redis = fakeredis.FakeRedis()
    RedisGuestLimiter(redis).hit("203.0.113.5", datetime(2026, 11, 8, 12, 0, tzinfo=UTC))

    keys = [k.decode() for k in redis.keys("*")]
    assert len(keys) == 1
    assert "203.0.113.5" not in keys[0]
    assert redis.ttl(keys[0]) > 0
