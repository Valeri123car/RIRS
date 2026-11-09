import pytest

from app.riot.demo_client import PUUID_PREFIX, DemoRiotClient, is_demo_riot_id
from app.riot.errors import RiotNotFoundError
from app.riot.fixture_client import FixtureRiotClient


@pytest.fixture
def client():
    return DemoRiotClient(FixtureRiotClient(), delay_s=0)


@pytest.mark.parametrize(
    ("name", "tag", "expected"),
    [
        ("DemoPyke", "DEMO", True),
        ("demojinx", "demo", True),
        ("DemoAmbessa", "DEMO", True),
        ("DemoPyke", "EUW", False),  # pravi igralec z drugo oznako
        ("Luka", "DEMO", False),
        ("DemoNeznan", "DEMO", False),
    ],
)
def test_prepoznava_samo_tri_demo_riot_id(name, tag, expected):
    assert is_demo_riot_id(name, tag) is expected


def test_demo_racun_in_klicatelj_ne_porabita_riot_api(client):
    account = client.get_account("DemoPyke", "DEMO", "euw1")

    assert account.puuid == f"{PUUID_PREFIX}demopyke"
    assert client.get_summoner(account.puuid, "euw1").puuid == account.puuid


def test_pravi_igralci_gredo_skozi_ovit_klient(client):
    account = client.get_account("Luka", "EUNE", "eun1")

    assert account.game_name == "Luka"
    assert client.get_active_game(account.puuid, "eun1") is not None


def test_neznan_pravi_igralec_ostane_not_found(client):
    with pytest.raises(RiotNotFoundError):
        client.get_account("Neznan", "XXXX", "eun1")
