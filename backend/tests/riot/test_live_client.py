import httpx
import pytest

from app.riot.client import LiveRiotClient
from app.riot.errors import (
    InvalidPlatformError,
    RiotAuthError,
    RiotNotFoundError,
    RiotUnavailableError,
)

API_KEY = "RGAPI-test-kljuc"

ACCOUNT = {"puuid": "p-luka", "gameName": "Luka", "tagLine": "EUNE"}


class RecordingLimiter:
    def __init__(self) -> None:
        self.routings: list[str] = []

    def acquire(self, routing: str) -> None:
        self.routings.append(routing)


def make_client(handler, limiter=None, sleeps=None) -> LiveRiotClient:
    return LiveRiotClient(
        API_KEY,
        limiter or RecordingLimiter(),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=(sleeps.append if sleeps is not None else lambda _: None),
    )


def test_account_klic_gre_na_regionalni_streznik_s_kljucem_v_glavi():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=ACCOUNT)

    limiter = RecordingLimiter()
    account = make_client(handler, limiter).get_account("Luka Novak", "EUNE", "eun1")

    assert account.puuid == "p-luka"
    assert account.game_name == "Luka"
    url = requests[0].url
    assert url.host == "europe.api.riotgames.com"
    assert url.raw_path == b"/riot/account/v1/accounts/by-riot-id/Luka%20Novak/EUNE"
    assert requests[0].headers["X-Riot-Token"] == API_KEY
    assert limiter.routings == ["europe"]


def test_posebni_znaki_v_riot_id_ne_spremenijo_poti():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=ACCOUNT)

    make_client(handler).get_account("../admin", "a/b", "eun1")

    assert requests[0].url.raw_path == (b"/riot/account/v1/accounts/by-riot-id/..%2Fadmin/a%2Fb")


def test_summoner_klic_gre_na_streznik_platforme():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "eun1.api.riotgames.com"
        assert request.url.path == "/lol/summoner/v4/summoners/by-puuid/p-luka"
        return httpx.Response(
            200, json={"puuid": "p-luka", "profileIconId": 29, "summonerLevel": 312}
        )

    summoner = make_client(handler).get_summoner("p-luka", "eun1")

    assert summoner.profile_icon_id == 29


def test_aktivna_tekma_vrne_none_ce_igralec_ni_v_tekmi():
    client = make_client(lambda _: httpx.Response(404, json={"status": {"status_code": 404}}))

    assert client.get_active_game("p-luka", "eun1") is None


def test_neobstojec_racun_sprozi_not_found():
    client = make_client(lambda _: httpx.Response(404))

    with pytest.raises(RiotNotFoundError):
        client.get_account("Nihce", "EUNE", "eun1")


def test_match_ids_uporabijo_regijo_in_parametre():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "europe.api.riotgames.com"
        assert request.url.path == "/lol/match/v5/matches/by-puuid/p-luka/ids"
        assert request.url.params["count"] == "5"
        assert request.url.params["queue"] == "420"
        return httpx.Response(200, json=["EUN1_1", "EUN1_2"])

    ids = make_client(handler).get_match_ids("p-luka", "eun1", count=5, queue=420)

    assert ids == ["EUN1_1", "EUN1_2"]


def test_ob_429_pocaka_retry_after_in_ponovi():
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": "3"}), httpx.Response(200, json=ACCOUNT)]
    )
    sleeps: list[float] = []

    account = make_client(lambda _: next(responses), sleeps=sleeps).get_account(
        "Luka", "EUNE", "eun1"
    )

    assert account.puuid == "p-luka"
    assert sleeps == [3.0]


def test_ponavljajoce_napake_streznika_sprozijo_unavailable():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(RiotUnavailableError):
        make_client(handler).get_account("Luka", "EUNE", "eun1")

    assert len(calls) == 3


def test_napaka_omrezja_se_ponovi():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        if len(attempts) == 1:
            raise httpx.ConnectTimeout("timeout", request=request)
        return httpx.Response(200, json=ACCOUNT)

    assert make_client(handler).get_account("Luka", "EUNE", "eun1").puuid == "p-luka"
    assert len(attempts) == 2


def test_neveljaven_kljuc_se_ne_ponavlja_in_ne_razkrije_kljuca():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(403)

    with pytest.raises(RiotAuthError) as exc_info:
        make_client(handler).get_account("Luka", "EUNE", "eun1")

    assert len(calls) == 1
    assert API_KEY not in str(exc_info.value)
    assert API_KEY not in repr(make_client(handler))


def test_neznana_platforma_je_zavrnjena_brez_klica():
    with pytest.raises(InvalidPlatformError):
        make_client(lambda _: pytest.fail("ne sme klicati")).get_account("Luka", "EUNE", "xx9")
