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


def test_cetrta_analiza_gosta_v_dnevu_je_zavrnjena(api):
    for _ in range(3):
        assert start(api).status_code == 202

    response = start(api)

    assert response.status_code == 429
    assert "največ 3 analize" in response.json()["detail"]
    assert "Registriraj se" in response.json()["detail"]
    assert int(response.headers["Retry-After"]) > 0


def test_prijavljen_uporabnik_nima_omejitve_gostov(api):
    headers = auth_headers(api)
    for _ in range(5):
        assert start(api, headers=headers).status_code == 202


def test_neveljaven_vnos_ne_porabi_analize(api):
    for _ in range(3):
        start(api, riot_id="brez-oznake")

    assert start(api).status_code == 202


def test_matchup_z_izbranim_nasprotnikom(api, db):
    from app.models.champion import Champion

    stats = {"hp": 600, "hpperlevel": 100, "attackdamage": 60, "attackrange": 525}
    db.merge(Champion(id=222, slug="Jinx", name="Jinx", classes=["Marksman"], stats=stats))
    db.merge(Champion(id=51, slug="Caitlyn", name="Caitlyn", classes=["Marksman"], stats=stats))
    analysis_id = start(api).json()["id"]

    response = api.get(f"/analyses/{analysis_id}/matchup", params={"opponent": 51})

    assert response.status_code == 200
    card = response.json()
    assert card["opponent"] == {"id": 51, "name": "Caitlyn"}
    assert card["opponent_source"] == "choice"
    assert [p["level"] for p in card["levels"]] == list(range(1, 19))


def test_matchup_nasprotnik_mora_biti_v_nasprotni_ekipi(api):
    analysis_id = start(api).json()["id"]

    response = api.get(f"/analyses/{analysis_id}/matchup", params={"opponent": 222})

    assert response.status_code == 422


def test_matchup_analize_brez_tekme_ni_mogoc(api):
    analysis_id = start(api, "Miha#EUNE").json()["id"]

    response = api.get(f"/analyses/{analysis_id}/matchup", params={"opponent": 51})

    assert response.status_code == 409


def test_seznam_analiz_vrne_samo_analize_prijavljenega_uporabnika(api):
    mine = auth_headers(api, "moja@example.com")
    other = auth_headers(api, "tvoja@example.com")
    my_id = start(api, headers=mine).json()["id"]
    start(api, headers=other)
    start(api)  # gost

    result = api.get("/analyses", headers=mine)

    assert result.status_code == 200
    items = result.json()
    assert [item["id"] for item in items] == [my_id]
    assert (items[0]["game_name"], items[0]["status"]) == ("Luka", "completed")
    # Testna baza nima uvoženih šampionov (imena so None), zato seznam nasprotnikov ni poln.
    assert "champion_name" in items[0] and isinstance(items[0]["enemy_champions"], list)


def test_seznam_analiz_zahteva_prijavo(api):
    assert api.get("/analyses").status_code == 401


def test_uporabnik_izbrise_svojo_analizo(api, db):
    headers = auth_headers(api, "brisi@example.com")
    analysis_id = start(api, headers=headers).json()["id"]

    assert api.delete(f"/analyses/{analysis_id}", headers=headers).status_code == 204

    assert db.get(LiveAnalysis, uuid.UUID(analysis_id)) is None
    assert api.get("/analyses", headers=headers).json() == []


def test_tuje_analize_ni_mogoce_izbrisati(api, db):
    mine = auth_headers(api, "moja2@example.com")
    other = auth_headers(api, "tvoja2@example.com")
    analysis_id = start(api, headers=mine).json()["id"]

    assert api.delete(f"/analyses/{analysis_id}", headers=other).status_code == 404

    assert db.get(LiveAnalysis, uuid.UUID(analysis_id)) is not None


def test_brisanje_zahteva_prijavo_in_analiza_gosta_ni_brisljiva(api):
    analysis_id = start(api).json()["id"]

    assert api.delete(f"/analyses/{analysis_id}").status_code == 401
    assert api.delete(f"/analyses/{analysis_id}", headers=auth_headers(api)).status_code == 404


def test_priporocilo_z_neveljavnim_stanjem_igre_je_zavrnjeno(api):
    analysis_id = start(api).json()["id"]

    response = api.get(f"/analyses/{analysis_id}/recommendation", params={"state": "winning"})

    assert response.status_code == 422


def test_priporocilo_analize_brez_tekme_ni_mogoce(api):
    analysis_id = start(api, "Miha#EUNE").json()["id"]

    response = api.get(f"/analyses/{analysis_id}/recommendation", params={"state": "ahead"})

    assert response.status_code == 409


def test_priporocilo_po_stanju_igre(api, db):
    from app.models.champion import Champion
    from app.models.item import Item

    db.merge(Champion(id=222, slug="Jinx", name="Jinx", classes=["Marksman"]))
    for item_id, tags in enumerate(
        (["damage", "critical_strike"], ["damage", "armor_pen"], ["armor", "health"], ["damage"]),
        start=3000,
    ):
        db.merge(Item(id=item_id, name=f"Predmet {item_id}", cost=3000, tags=tags, completed=True))
    analysis_id = start(api).json()["id"]

    response = api.get(f"/analyses/{analysis_id}/recommendation", params={"state": "behind"})

    assert response.status_code == 200
    body = response.json()
    assert body["game_state"] == "behind" and body["source"] == "rules"
    assert api.get(f"/analyses/{analysis_id}/recommendation").json()["game_state"] == "even"
