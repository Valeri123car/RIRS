import uuid

from app.models.live_analysis import LiveAnalysis
from tests.db.conftest import auth_headers


def start(api, riot_id="Luka#EUNE", platform="eun1", headers=None):
    return api.post(
        "/analyses", json={"riot_id": riot_id, "platform": platform}, headers=headers or {}
    )


def test_gost_zazene_analizo_in_dobi_10_udelezencev(api):
    response = start(api)

    assert response.status_code == 202
    analysis_id = response.json()["id"]
    result = api.get(f"/analyses/{analysis_id}").json()
    assert result["status"] == "completed"
    assert len(result["participants"]) == 10
    assert (result["game_name"], result["tag_line"], result["platform"]) == ("Luka", "EUNE", "eun1")


def test_igralec_ni_v_tekmi(api):
    analysis_id = start(api, "Miha#EUNE").json()["id"]

    result = api.get(f"/analyses/{analysis_id}").json()

    assert result["status"] == "not_in_game"
    assert result["error"] == "Igralec trenutno ni v tekmi"


def test_analiza_prijavljenega_uporabnika_se_shrani_k_njemu(api, db):
    headers = auth_headers(api)
    user_id = api.get("/auth/me", headers=headers).json()["id"]

    analysis_id = start(api, headers=headers).json()["id"]

    assert db.get(LiveAnalysis, uuid.UUID(analysis_id)).user_id == user_id


def test_neveljaven_vnos_je_zavrnjen(api):
    assert start(api, riot_id="brez-oznake").status_code == 422
    assert start(api, platform="xx9").status_code == 422


def test_neobstojeca_analiza(api):
    assert api.get(f"/analyses/{uuid.uuid4()}").status_code == 404
    assert api.get("/analyses/ni-uuid").status_code == 422
