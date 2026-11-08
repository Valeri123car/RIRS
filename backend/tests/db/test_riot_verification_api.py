from datetime import UTC, datetime, timedelta

from app.api.deps import get_riot_client
from app.models.riot_account import RiotAccount
from app.riot.errors import RiotUnavailableError
from app.riot.fixture_client import FixtureRiotClient
from tests.db.conftest import auth_headers

URL = "/riot-accounts/verifications"


def start(api, headers, riot_id="Luka#EUNE", platform="eun1"):
    return api.post(URL, json={"riot_id": riot_id, "platform": platform}, headers=headers)


def test_zacetek_verifikacije_vrne_nakljucno_privzeto_ikono_in_rok_10_minut(api):
    headers = auth_headers(api)

    response = start(api, headers)

    assert response.status_code == 201
    body = response.json()
    current_icon = FixtureRiotClient().get_summoner(body["puuid"], "eun1").profile_icon_id
    assert 0 <= body["icon_id"] <= 28
    assert body["icon_id"] != current_icon
    assert (body["game_name"], body["tag_line"], body["platform"]) == ("Luka", "EUNE", "eun1")
    expires = datetime.fromisoformat(body["expires_at"])
    assert timedelta(minutes=9) < expires - datetime.now(UTC) <= timedelta(minutes=10)


def test_riot_id_ni_v_izbrani_regiji(api):
    headers = auth_headers(api)

    response = start(api, headers, riot_id="Sara#EUW", platform="eun1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Igralca s tem Riot ID ni v regiji EUNE"


def test_neobstojec_riot_id(api):
    response = start(api, auth_headers(api), riot_id="Nihce#0000", platform="euw1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Igralca s tem Riot ID ni v regiji EUW"


def test_neveljaven_vnos_je_zavrnjen(api):
    headers = auth_headers(api)

    assert start(api, headers, riot_id="brez-oznake").status_code == 422
    assert start(api, headers, riot_id="a#EUNE").status_code == 422
    assert start(api, headers, riot_id="Luka#predolgaoznaka").status_code == 422
    assert start(api, headers, platform="xx9").status_code == 422


def test_racuna_verificiranega_pri_drugem_uporabniku_ni_mogoce_povezati(api, db):
    puuid = FixtureRiotClient().get_account("Luka", "EUNE", "eun1").puuid
    other = auth_headers(api, "drugi@example.com")
    other_id = api.get("/auth/me", headers=other).json()["id"]
    # merge: zapis za igralca že lahko obstaja (npr. iz tekem), samo brez lastnika.
    db.merge(
        RiotAccount(
            puuid=puuid,
            game_name="Luka",
            tag_line="EUNE",
            platform="eun1",
            user_id=other_id,
            verified_at=datetime.now(UTC),
        )
    )
    db.flush()

    response = start(api, auth_headers(api))

    assert response.status_code == 409
    assert response.json()["detail"] == "Ta Riot račun je že povezan z drugim uporabnikom."


def test_verifikacija_zahteva_prijavo(api):
    assert start(api, headers={}).status_code == 401


class UnavailableRiot(FixtureRiotClient):
    def get_account(self, game_name, tag_line, platform):
        raise RiotUnavailableError("Riot API je vrnil 503")


def test_nedosegljiv_riot_api_vrne_503(api):
    api.app.dependency_overrides[get_riot_client] = UnavailableRiot

    response = start(api, auth_headers(api))

    assert response.status_code == 503
    assert response.json()["detail"] == "Riot API trenutno ni dosegljiv, poskusi kasneje."
