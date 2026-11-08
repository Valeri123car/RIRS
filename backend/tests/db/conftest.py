"""Testi na pravi PostgreSQL bazi.

Zaženejo se samo, če je nastavljen TEST_DATABASE_URL (baza mora biti migrirana:
alembic upgrade head). Vsak test teče v transakciji, ki se na koncu razveljavi,
zato v bazi ne ostanejo podatki.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_riot_client
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.riot.fixture_client import FixtureRiotClient

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def db() -> Iterator[Session]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL ni nastavljen")

    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as connection:
        transaction = connection.begin()
        # join_transaction_mode: commit/rollback v testu ostaneta znotraj zunanje transakcije.
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
    engine.dispose()


TEST_JWT_SECRET = "testna-skrivnost-ki-je-dovolj-dolga-za-hs256"


@pytest.fixture
def api(db: Session) -> Iterator[TestClient]:
    """Odjemalec API, ki uporablja testno sejo (transakcija se razveljavi) in testno skrivnost."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret=TEST_JWT_SECRET
    )
    app.dependency_overrides[get_riot_client] = FixtureRiotClient
    with TestClient(app) as client:
        yield client


def auth_headers(api: TestClient, email: str = "igralec@example.com") -> dict[str, str]:
    """Registrira in prijavi uporabnika; vrne glavo z dostopnim žetonom."""
    credentials = {"email": email, "password": "dolgo-geslo-123"}
    api.post("/auth/register", json=credentials)
    token = api.post("/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
