"""Testi na pravi PostgreSQL bazi.

Zaženejo se samo, če je nastavljen TEST_DATABASE_URL (baza mora biti migrirana:
alembic upgrade head). Vsak test teče v transakciji, ki se na koncu razveljavi,
zato v bazi ne ostanejo podatki.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
