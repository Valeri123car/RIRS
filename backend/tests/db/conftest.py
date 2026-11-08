"""Testi na pravi PostgreSQL bazi.

Zaženejo se samo, če je nastavljen TEST_DATABASE_URL (baza mora biti migrirana:
alembic upgrade head). Vsak test teče v transakciji, ki se na koncu razveljavi,
zato v bazi ne ostanejo podatki.
"""

import os
from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analysis.guest_limit import RedisGuestLimiter
from app.analysis.pipeline import run_analysis
from app.api.deps import (
    get_analysis_queue,
    get_guest_limiter,
    get_ip_limiter,
    get_riot_client,
)
from app.core.config import Settings, get_settings
from app.core.ip_limit import IpRateLimiter
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
    # Namesto Celery vrste se zajem izvede takoj, v testni seji.
    app.dependency_overrides[get_analysis_queue] = lambda: (
        lambda analysis_id: run_analysis(db, FixtureRiotClient(), analysis_id)
    )
    # Vsak test ima svoj (prazen) števec analiz gostov.
    limiter = RedisGuestLimiter(fakeredis.FakeRedis())
    app.dependency_overrides[get_guest_limiter] = lambda: limiter
    ip_limiter = IpRateLimiter(fakeredis.FakeRedis())
    app.dependency_overrides[get_ip_limiter] = lambda: ip_limiter
    with TestClient(app) as client:
        yield client


def auth_headers(api: TestClient, email: str = "igralec@example.com") -> dict[str, str]:
    """Registrira in prijavi uporabnika; vrne glavo z dostopnim žetonom."""
    credentials = {"email": email, "password": "dolgo-geslo-123"}
    api.post("/auth/register", json=credentials)
    token = api.post("/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
