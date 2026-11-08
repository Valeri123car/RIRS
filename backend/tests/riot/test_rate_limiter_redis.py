"""Omejevalnik na pravem Redisu; izvede se samo, če je nastavljen TEST_REDIS_URL."""

import os
import uuid

import pytest
from redis import Redis

from app.riot.rate_limiter import RateLimit, RedisRateLimiter

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")

pytestmark = pytest.mark.skipif(not TEST_REDIS_URL, reason="TEST_REDIS_URL ni nastavljen")


@pytest.fixture
def redis():
    client = Redis.from_url(TEST_REDIS_URL)
    prefix = f"test:rl:{uuid.uuid4().hex}"
    yield client, prefix
    for key in client.scan_iter(f"{prefix}:*"):
        client.delete(key)
    client.close()


def test_lua_skripta_na_pravem_redisu(redis):
    client, prefix = redis
    limiter = RedisRateLimiter(client, [RateLimit(2, 1), RateLimit(5, 120)], prefix=prefix)

    assert limiter.try_acquire("europe") == 0
    assert limiter.try_acquire("europe") == 0
    wait = limiter.try_acquire("europe")

    assert 0 < wait <= 1.25
    assert int(client.get(f"{prefix}:europe:120")) == 2
    assert 120_000 < client.pttl(f"{prefix}:europe:120") <= 120_250
