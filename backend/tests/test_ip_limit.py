"""Omejevanje zahtev po IP (fiksno okno v Redis)."""

import fakeredis

from app.core.ip_limit import IpLimitRule, IpRateLimiter

RULE = IpLimitRule("test", limit=3, window_seconds=600)


def test_po_meji_je_zahteva_zavrnjena_do_konca_okna():
    limiter = IpRateLimiter(fakeredis.FakeRedis())

    results = [limiter.hit(RULE, "203.0.113.5", now=1000.0) for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[-1].retry_after == 200  # okno 600–1200 s


def test_novo_okno_ponastavi_stevec():
    limiter = IpRateLimiter(fakeredis.FakeRedis())
    for _ in range(3):
        limiter.hit(RULE, "203.0.113.5", now=1000.0)

    assert limiter.hit(RULE, "203.0.113.5", now=1200.0).allowed


def test_ip_in_pravila_so_loceni():
    limiter = IpRateLimiter(fakeredis.FakeRedis())
    other = IpLimitRule("drugo", limit=3, window_seconds=600)
    for _ in range(3):
        limiter.hit(RULE, "203.0.113.5", now=1000.0)

    assert limiter.hit(RULE, "203.0.113.6", now=1000.0).allowed
    assert limiter.hit(other, "203.0.113.5", now=1000.0).allowed


def test_ip_ni_shranjen_v_berljivi_obliki():
    redis = fakeredis.FakeRedis()
    IpRateLimiter(redis).hit(RULE, "203.0.113.5", now=1000.0)

    keys = [k.decode() for k in redis.keys("*")]
    assert len(keys) == 1
    assert "203.0.113.5" not in keys[0]
    assert redis.ttl(keys[0]) > 0
