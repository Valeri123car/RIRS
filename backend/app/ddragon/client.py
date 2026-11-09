"""Branje javnega Riot Data Dragon CDN (brez API ključa)."""

import re
from typing import Any

import httpx

BASE_URL = "https://ddragon.leagueoflegends.com"
LOCALE = "en_US"
TIMEOUT_SECONDS = 30.0

# Verzija gre v pot URL, zato dovolimo samo obliko "16.22.1".
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class DataDragonError(Exception):
    """Data Dragon ni dosegljiv ali je vrnil napako."""


class DataDragonClient:
    def __init__(self, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)

    def latest_version(self) -> str:
        return self._get("/api/versions.json")[0]

    def champions(self, version: str) -> dict[str, dict[str, Any]]:
        # championFull ima poleg povzetka še statistike po levelu in sposobnosti (US-05).
        return self._get(self._data_path(version, "championFull.json"))["data"]

    def items(self, version: str) -> dict[str, dict[str, Any]]:
        return self._get(self._data_path(version, "item.json"))["data"]

    @staticmethod
    def _data_path(version: str, name: str) -> str:
        if not VERSION_PATTERN.fullmatch(version):
            raise ValueError(f"Neveljavna verzija Data Dragon: {version!r}")
        return f"/cdn/{version}/data/{LOCALE}/{name}"

    def _get(self, path: str) -> Any:
        try:
            response = self._http.get(BASE_URL + path)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise DataDragonError(f"Data Dragon napaka ({path}): {exc}") from exc
