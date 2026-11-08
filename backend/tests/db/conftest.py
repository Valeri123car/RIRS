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

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app

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
    with TestClient(app) as client:
        yield client
