from datetime import UTC, datetime, timedelta

import pytest

from app.api.deps import get_riot_client
from app.models.riot_account import RiotAccount
from app.models.riot_verification import RiotVerification
from app.riot import fixture_client
from app.riot.fixture_client import FixtureRiotClient
from tests.db.conftest import auth_headers

URL = "/riot-accounts/verifications"


@pytest.fixture(autouse=True)
def reset_fixture_icons():
    yield
    fixture_client.reset_profile_icons()


def start(api, headers, riot_id="Luka#EUNE"):
    response = api.post(URL, json={"riot_id": riot_id, "platform": "eun1"}, headers=headers)
    assert response.status_code == 201
    return response.json()


def check(api, headers, verification_id):
    return api.post(f"{URL}/{verification_id}/check", headers=headers)


def test_ikona_se_ni_zamenjana(api):
    headers = auth_headers(api)
    verification = start(api, headers)

    response = check(api, headers, verification["id"])

    assert response.status_code == 400
    assert response.json()["detail"] == "Ikona na računu še ni zamenjana"
    # Ponovni poskus je mogoč, dokler čas ne poteče.
    assert check(api, headers, verification["id"]).status_code == 400


def test_pravilna_ikona_verificira_racun_in_ga_prikaze_v_profilu(api, db):
    headers = auth_headers(api)
    verification = start(api, headers)
    assert verification["simulation_available"] is True
    simulated = api.post(f"{URL}/{verification['id']}/simulate-icon", headers=headers)
    assert simulated.status_code == 204

    response = check(api, headers, verification["id"])

    assert response.status_code == 200
    body = response.json()
    assert (body["game_name"], body["tag_line"], body["platform"]) == ("Luka", "EUNE", "eun1")
    assert body["verified_at"] is not None
    accounts = api.get("/riot-accounts", headers=headers).json()
    assert [a["puuid"] for a in accounts] == [verification["puuid"]]
    assert db.get(RiotVerification, verification["id"]) is None


def test_po_izteku_roka_preverjanje_ni_mogoce(api, db):
    headers = auth_headers(api)
    verification = start(api, headers)
    db.get(RiotVerification, verification["id"]).expires_at = datetime.now(UTC) - timedelta(
        seconds=1
    )
    db.flush()

    response = check(api, headers, verification["id"])

    assert response.status_code == 410
    assert response.json()["detail"] == "Čas za verifikacijo je potekel, začni znova."


def test_tuje_verifikacije_ni_mogoce_preveriti(api):
    verification = start(api, auth_headers(api, "prvi@example.com"))
    other = auth_headers(api, "drugi@example.com")

    assert check(api, other, verification["id"]).status_code == 404
    assert api.post(f"{URL}/{verification['id']}/simulate-icon", headers=other).status_code == 404


def test_racun_verificiran_pri_drugem_medtem_ko_je_tekla_verifikacija(api, db):
    headers = auth_headers(api)
    verification = start(api, headers)
    api.post(f"{URL}/{verification['id']}/simulate-icon", headers=headers)
    other_id = api.get("/auth/me", headers=auth_headers(api, "drugi@example.com")).json()["id"]
    db.add(
        RiotAccount(
            puuid=verification["puuid"],
            game_name="Luka",
            tag_line="EUNE",
            platform="eun1",
            user_id=other_id,
            verified_at=datetime.now(UTC),
        )
    )
    db.flush()

    assert check(api, headers, verification["id"]).status_code == 409


def test_simulacija_ikone_ni_na_voljo_s_pravim_riot_api(api):
    headers = auth_headers(api)
    verification = start(api, headers)

    class LiveLike:
        get_summoner = FixtureRiotClient.get_summoner

    api.app.dependency_overrides[get_riot_client] = LiveLike
    response = api.post(f"{URL}/{verification['id']}/simulate-icon", headers=headers)

    assert response.status_code == 404


def test_seznam_racunov_zahteva_prijavo(api):
    assert api.get("/riot-accounts").status_code == 401
