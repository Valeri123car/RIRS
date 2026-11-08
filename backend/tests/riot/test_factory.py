import fakeredis
import pytest

from app.core.config import Settings
from app.riot.client import LiveRiotClient
from app.riot.errors import RiotConfigError
from app.riot.factory import build_riot_client
from app.riot.fixture_client import FixtureRiotClient


def settings(**values) -> Settings:
    # _env_file=None: test ne sme brati lokalne .env datoteke.
    return Settings(_env_file=None, **values)


def test_privzeto_je_nacin_fixtures():
    assert isinstance(build_riot_client(settings()), FixtureRiotClient)


def test_nacin_live_brez_kljuca_je_napaka():
    with pytest.raises(RiotConfigError, match="RIOT_API_KEY"):
        build_riot_client(settings(riot_api_mode="live", redis_url="redis://x"))


def test_nacin_live_brez_redis_je_napaka():
    with pytest.raises(RiotConfigError, match="REDIS_URL"):
        build_riot_client(settings(riot_api_mode="live", riot_api_key="RGAPI-x"))


def test_nacin_live_s_kljucem_in_redis_vrne_pravi_klient():
    client = build_riot_client(
        settings(riot_api_mode="live", riot_api_key="RGAPI-x", redis_url="redis://x"),
        redis=fakeredis.FakeRedis(),
    )

    assert isinstance(client, LiveRiotClient)


def test_neznan_nacin_je_zavrnjen_ob_branju_nastavitev():
    with pytest.raises(ValueError):
        settings(riot_api_mode="mock")


def test_kljuc_se_ne_izpise_v_nastavitvah():
    assert "RGAPI-skrivnost" not in repr(settings(riot_api_key="RGAPI-skrivnost"))
