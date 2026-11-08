"""Nastavitve aplikacije, prebrane iz okoljskih spremenljivk (ali datoteke .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.riot.platforms import region_for


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

    # Prijava: brez privzete skrivnosti, preveri se ob prvem izdajanju žetona.
    jwt_secret: SecretStr | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    # V produkciji (HTTPS) mora biti True, da piškotek ne potuje po HTTP.
    cookie_secure: bool = False

    # Zbiralnik tekem (US-07): challenger igralci ene platforme, omejeno na zagon, da en
    # zagon z razvojnim ključem (100 klicev / 2 min) traja nekaj minut, ne ur.
    collector_platform: str = "euw1"
    collector_max_players: int = Field(20, ge=1, le=300)
    collector_matches_per_player: int = Field(20, ge=1, le=100)
    collector_max_new_matches: int = Field(100, ge=1, le=2000)
    # Časovnica podvoji število klicev, a da značilke zgodnje igre (CS@10, zlato @15 ...).
    collector_timelines: bool = True
    # Ura dnevnega zagona (Celery beat, UTC).
    collector_hour_utc: int = Field(3, ge=0, le=23)

    @field_validator("collector_platform")
    @classmethod
    def _known_platform(cls, value: str) -> str:
        region_for(value)  # sproži InvalidPlatformError (ValueError) za neznano platformo
        return value


@lru_cache
def get_settings() -> Settings:
    """Vrne nastavitve; zaradi predpomnjenja se .env prebere samo enkrat."""
    return Settings()
