"""Povezava s PostgreSQL in seja za posamezno zahtevo."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


class DatabaseNotConfiguredError(RuntimeError):
    pass


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise DatabaseNotConfiguredError("DATABASE_URL ni nastavljen (glej .env.example).")
    # pool_pre_ping prepreči napake ob prekinjenih povezavah (npr. po ponovnem zagonu baze).
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI odvisnost: odpre sejo za zahtevo in jo na koncu vedno zapre."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
