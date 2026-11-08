import pytest

from app.riot.client import RiotClient
from app.riot.errors import InvalidPlatformError, RiotNotFoundError
from app.riot.fixture_client import FixtureRiotClient


@pytest.fixture
def client() -> RiotClient:
    return FixtureRiotClient()


def test_poisce_racun_ne_glede_na_velike_crke(client):
    account = client.get_account("luka", "eune", "eun1")

    assert account.game_name == "Luka"
    assert account.tag_line == "EUNE"


def test_neobstojec_racun_sprozi_not_found(client):
    with pytest.raises(RiotNotFoundError):
        client.get_account("Nihce", "0000", "eun1")


def test_summoner_obstaja_samo_na_platformi_racuna(client):
    puuid = client.get_account("Luka", "EUNE", "eun1").puuid

    assert client.get_summoner(puuid, "eun1").puuid == puuid
    with pytest.raises(RiotNotFoundError):
        client.get_summoner(puuid, "euw1")


def test_aktivna_tekma_ima_deset_igralcev_z_obeh_ekip(client):
    puuid = client.get_account("Luka", "EUNE", "eun1").puuid

    game = client.get_active_game(puuid, "eun1")

    assert game is not None
    assert len(game.participants) == 10
    assert {p.team_id for p in game.participants} == {100, 200}
    assert puuid in {p.puuid for p in game.participants}


def test_igralec_brez_tekme_nima_aktivne_tekme(client):
    puuid = client.get_account("Miha", "EUNE", "eun1").puuid

    assert client.get_active_game(puuid, "eun1") is None


def test_zadnje_tekme_igralca_se_dajo_prenesti(client):
    puuid = client.get_account("Luka", "EUNE", "eun1").puuid

    match_ids = client.get_match_ids(puuid, "eun1", count=1)

    assert len(match_ids) == 1
    match = client.get_match(match_ids[0], "eun1")
    assert match["metadata"]["matchId"] == match_ids[0]
    assert puuid in match["metadata"]["participants"]


def test_neznana_tekma_sprozi_not_found(client):
    with pytest.raises(RiotNotFoundError):
        client.get_match("EUN1_0", "eun1")


def test_neznana_platforma_je_zavrnjena(client):
    with pytest.raises(InvalidPlatformError):
        client.get_account("Luka", "EUNE", "xx9")


def test_challenger_liga_euw_vsebuje_igralce_s_tekmami(client):
    league = client.get_challenger_league("euw1")

    assert league.tier == "CHALLENGER"
    assert len(league.entries) >= 2
    sara = client.get_account("Sara", "EUW", "euw1").puuid
    assert sara in {e.puuid for e in league.entries}
    assert client.get_match_ids(sara, "euw1", queue=420)


def test_platforma_brez_challenger_igralcev_vrne_prazno_ligo(client):
    assert client.get_challenger_league("kr").entries == []


def test_casovnica_tekme_ima_okvirje_in_udelezence(client):
    match_id = client.get_match_ids(client.get_account("Sara", "EUW", "euw1").puuid, "euw1")[0]

    timeline = client.get_match_timeline(match_id, "euw1")

    assert timeline["metadata"]["matchId"] == match_id
    assert len(timeline["info"]["participants"]) == 10
    assert len(timeline["info"]["frames"]) > 15


def test_neznana_casovnica_sprozi_not_found(client):
    with pytest.raises(RiotNotFoundError):
        client.get_match_timeline("EUW1_0", "euw1")
