"""Nastavitve aplikacije, prebrane iz okoljskih spremenljivk (ali datoteke .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RIFT_HELP API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Brez privzete vrednosti, da v kodi ni gesel; preveri se šele ob prvi uporabi baze.
    database_url: str | None = None
    redis_url: SecretStr | None = None  # vsebuje geslo

    # fixtures = sintetični odgovori brez ključa, live = pravi Riot API
    riot_api_mode: Literal["live", "fixtures"] = "fixtures"
    riot_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Vrne nastavitve; zaradi predpomnjenja se .env prebere samo enkrat."""
    return Settings()
