"""Klient za Riot API (Account-V1, Summoner-V4, Spectator-V5, Match-V5)."""

import time
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from app.riot.errors import RiotApiError, RiotAuthError, RiotNotFoundError, RiotUnavailableError
from app.riot.models import Account, ActiveGame, Match, Summoner
from app.riot.platforms import region_for

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 10.0


class RiotClient(Protocol):
    """Skupni vmesnik za način live in fixtures."""

    def get_account(self, game_name: str, tag_line: str, platform: str) -> Account: ...

    def get_summoner(self, puuid: str, platform: str) -> Summoner: ...

    def get_active_game(self, puuid: str, platform: str) -> ActiveGame | None: ...

    def get_match_ids(
        self, puuid: str, platform: str, *, count: int = 20, queue: int | None = None
    ) -> list[str]: ...

    def get_match(self, match_id: str, platform: str) -> Match: ...


class Limiter(Protocol):
    def acquire(self, routing: str) -> None: ...


def _segment(value: str) -> str:
    """Varno kodira del poti (npr. "../admin" ne more spremeniti poti)."""
    return quote(value, safe="")


class LiveRiotClient:
    def __init__(
        self,
        api_key: str,
        limiter: Limiter,
        *,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._limiter = limiter
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._sleep = sleep

    def __repr__(self) -> str:
        return "LiveRiotClient(api_key=***)"

    def get_account(self, game_name: str, tag_line: str, platform: str) -> Account:
        path = f"/riot/account/v1/accounts/by-riot-id/{_segment(game_name)}/{_segment(tag_line)}"
        return Account.model_validate(self._get(region_for(platform), path))

    def get_summoner(self, puuid: str, platform: str) -> Summoner:
        region_for(platform)  # preveri platformo
        path = f"/lol/summoner/v4/summoners/by-puuid/{_segment(puuid)}"
        return Summoner.model_validate(self._get(platform, path))

    def get_active_game(self, puuid: str, platform: str) -> ActiveGame | None:
        region_for(platform)
        path = f"/lol/spectator/v5/active-games/by-summoner/{_segment(puuid)}"
        try:
            return ActiveGame.model_validate(self._get(platform, path))
        except RiotNotFoundError:
            return None  # igralec trenutno ni v tekmi

    def get_match_ids(
        self, puuid: str, platform: str, *, count: int = 20, queue: int | None = None
    ) -> list[str]:
        params: dict[str, int] = {"count": count}
        if queue is not None:
            params["queue"] = queue
        path = f"/lol/match/v5/matches/by-puuid/{_segment(puuid)}/ids"
        return list(self._get(region_for(platform), path, params))

    def get_match(self, match_id: str, platform: str) -> Match:
        path = f"/lol/match/v5/matches/{_segment(match_id)}"
        return self._get(region_for(platform), path)

    def _get(self, routing: str, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"https://{routing}.api.riotgames.com{path}"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            last = attempt == MAX_ATTEMPTS
            self._limiter.acquire(routing)
            try:
                response = self._http.get(
                    url, params=params, headers={"X-Riot-Token": self._api_key}
                )
            except httpx.TransportError as exc:
                if last:
                    raise RiotUnavailableError(f"Riot API ni dosegljiv ({path})") from exc
                self._sleep(2 ** (attempt - 1))
                continue

            status = response.status_code
            if status == 200:
                return response.json()
            if status == 404:
                raise RiotNotFoundError(f"Ni najdeno: {path}")
            if status in (401, 403):
                raise RiotAuthError("Riot API ključ manjka, je neveljaven ali je potekel.")
            if status == 429 or status >= 500:
                if last:
                    raise RiotUnavailableError(f"Riot API je vrnil {status} ({path})")
                self._sleep(_retry_after(response, default=2 ** (attempt - 1)))
                continue
            raise RiotApiError(f"Riot API je vrnil {status} ({path})")
        raise AssertionError("nedosegljivo")


def _retry_after(response: httpx.Response, *, default: float) -> float:
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return float(default)
