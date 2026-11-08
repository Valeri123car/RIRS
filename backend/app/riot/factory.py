"""Izbira Riot klienta glede na nastavitev RIOT_API_MODE."""

from redis import Redis

from app.core.config import Settings
from app.riot.client import LiveRiotClient, RiotClient
from app.riot.errors import RiotConfigError
from app.riot.fixture_client import FixtureRiotClient
from app.riot.rate_limiter import RedisRateLimiter


def build_riot_client(settings: Settings, *, redis: Redis | None = None) -> RiotClient:
    if settings.riot_api_mode == "fixtures":
        return FixtureRiotClient()

    if not settings.riot_api_key or not settings.riot_api_key.get_secret_value():
        raise RiotConfigError("RIOT_API_MODE=live zahteva RIOT_API_KEY (glej .env.example).")
    if redis is None:
        if settings.redis_url is None:
            raise RiotConfigError("RIOT_API_MODE=live zahteva REDIS_URL za omejevanje klicev.")
        redis = Redis.from_url(settings.redis_url.get_secret_value())
    return LiveRiotClient(settings.riot_api_key.get_secret_value(), RedisRateLimiter(redis))
