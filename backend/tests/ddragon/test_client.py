import httpx
import pytest

from app.ddragon.client import DataDragonClient, DataDragonError


def make_client(handler) -> DataDragonClient:
    return DataDragonClient(http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_zadnja_verzija_je_prva_v_seznamu():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://ddragon.leagueoflegends.com/api/versions.json"
        return httpx.Response(200, json=["16.22.1", "16.21.1"])

    assert make_client(handler).latest_version() == "16.22.1"


def test_sampioni_in_predmeti_za_dano_verzijo():
    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.path.rsplit("/", 1)[-1]
        assert request.url.path.startswith("/cdn/16.22.1/data/en_US/")
        return httpx.Response(200, json={"type": name, "data": {"x": {}}})

    client = make_client(handler)

    assert client.champions("16.22.1") == {"x": {}}
    assert client.items("16.22.1") == {"x": {}}


@pytest.mark.parametrize("version", ["../../evil", "16.22", "latest", "16.22.1/x"])
def test_neveljavna_verzija_je_zavrnjena_brez_klica(version):
    client = make_client(lambda _: pytest.fail("ne sme klicati"))

    with pytest.raises(ValueError):
        client.champions(version)


def test_napaka_streznika_sprozi_data_dragon_error():
    with pytest.raises(DataDragonError):
        make_client(lambda _: httpx.Response(503)).latest_version()


def test_napaka_omrezja_sprozi_data_dragon_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("ni povezave", request=request)

    with pytest.raises(DataDragonError):
        make_client(handler).items("16.22.1")
