from sqlalchemy import select

from app.models.user import User

EMAIL = "luka@example.com"
PASSWORD = "dolgo-geslo-123"


def register(api, email=EMAIL, password=PASSWORD):
    return api.post("/auth/register", json={"email": email, "password": password})


def login(api, email=EMAIL, password=PASSWORD):
    return api.post("/auth/login", json={"email": email, "password": password})


def test_registracija_ustvari_igralca_z_zgosceno_geslom(api, db):
    response = register(api, email="Luka@Example.com")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert body["role"] == "player"
    assert "password" not in str(body)
    user = db.scalars(select(User).where(User.email == EMAIL)).one()
    assert user.password_hash.startswith("$argon2id$")


def test_e_posta_je_lahko_registrirana_samo_enkrat(api):
    register(api)

    response = register(api, email="LUKA@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "Uporabnik s to e-pošto že obstaja."


def test_prekratko_geslo_in_neveljavna_e_posta_sta_zavrnjena(api):
    assert register(api, password="kratko").status_code == 422
    assert register(api, email="ni-e-posta").status_code == 422


def test_prijava_vrne_dostopni_zeton_in_osvezilni_piskotek(api):
    register(api)

    response = login(api, email="LUKA@example.com")

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("refresh_token=")
    assert "HttpOnly" in cookie
    assert "Path=/auth" in cookie
    assert "SameSite=lax" in cookie


def test_napacno_geslo_in_neznan_uporabnik_dobita_isto_sporocilo(api):
    register(api)

    wrong_password = login(api, password="napacno-geslo")
    unknown_user = login(api, email="nihce@example.com")

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_me_vrne_prijavljenega_uporabnika(api):
    register(api)
    token = login(api).json()["access_token"]

    response = api.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_me_brez_ali_z_neveljavnim_zetonom_vrne_401(api):
    assert api.get("/auth/me").status_code == 401
    bad = api.get("/auth/me", headers={"Authorization": "Bearer neveljaven"})
    assert bad.status_code == 401


def test_osvezilni_piskotek_da_nov_dostopni_zeton(api):
    register(api)
    login(api)  # TestClient shrani piškotek

    response = api.post("/auth/refresh")

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert api.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_osvezitev_brez_piskotka_vrne_401(api):
    assert api.post("/auth/refresh").status_code == 401


def test_osvezilni_zeton_ni_uporaben_kot_dostopni(api):
    register(api)
    refresh_token = login(api).cookies["refresh_token"]

    response = api.get("/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})

    assert response.status_code == 401


def test_odjava_izbrise_piskotek(api):
    register(api)
    login(api)

    response = api.post("/auth/logout")

    assert response.status_code == 204
    assert api.post("/auth/refresh").status_code == 401


def test_odjava_preklice_prej_izdan_osvezilni_zeton(api):
    register(api)
    stolen = login(api).cookies["refresh_token"]
    api.post("/auth/logout")

    api.cookies.set("refresh_token", stolen, path="/auth")
    response = api.post("/auth/refresh")

    assert response.status_code == 401


def test_enajsti_poskus_prijave_v_15_minutah_je_zavrnjen(api):
    register(api)
    for _ in range(10):
        assert login(api, password="napacno-geslo").status_code == 401

    # Omejitev velja tudi za pravilno geslo: napadalec ne izve, ali je uganil.
    response = login(api)

    assert response.status_code == 429
    assert response.json()["detail"].startswith("Preveč poskusov prijave.")
    assert 0 < int(response.headers["Retry-After"]) <= 15 * 60


def test_sesta_registracija_v_uri_je_zavrnjena(api):
    for n in range(5):
        assert register(api, email=f"igralec{n}@example.com").status_code == 201

    response = register(api, email="igralec9@example.com")

    assert response.status_code == 429
    assert response.json()["detail"].startswith("Preveč registracij")
