"""Način RIOT_API_MODE=fixtures: odgovori iz datotek v app/riot/fixtures/ (brez ključa).

Podatki so sintetični, a v enaki obliki kot odgovori Riot API, zato gredo skozi iste
modele kot pravi odgovori. Polje "platform" v accounts.json ni Riotovo – pove, na kateri
platformi račun obstaja (za preverjanje "igralca ni v regiji").
"""

import copy
import json
from functools import cache
from pathlib import Path
from typing import Any

from app.riot.client import check_match_count, check_ranked_queue
from app.riot.errors import RiotNotFoundError
from app.riot.models import Account, ActiveGame, LeagueList, Match, MatchTimeline, Summoner
from app.riot.platforms import region_for

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Ikone, "nastavljene" med razvojem (simulacija zamenjave ikone pri verifikaciji, US-01).
# Na ravni modula, ker FastAPI odvisnost lahko ustvari več primerkov klienta.
_profile_icons: dict[str, int] = {}


def reset_profile_icons() -> None:
    _profile_icons.clear()


@cache
def _load(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class FixtureRiotClient:
    def get_account(self, game_name: str, tag_line: str, platform: str) -> Account:
        region = region_for(platform)
        for account in _load("accounts.json"):
            same_id = (account["gameName"].casefold(), account["tagLine"].casefold()) == (
                game_name.casefold(),
                tag_line.casefold(),
            )
            # Account-V1 je regionalen: račun najdemo v celotni regiji, ne le na platformi.
            if same_id and region_for(account["platform"]) == region:
                return Account.model_validate(account)
        raise RiotNotFoundError(f"Ni računa {game_name}#{tag_line}")

    def get_summoner(self, puuid: str, platform: str) -> Summoner:
        region_for(platform)
        if self._platform_of(puuid) != platform:
            raise RiotNotFoundError("Igralca ni na tej platformi")
        summoner = Summoner.model_validate(_load("summoners.json")[puuid])
        if puuid in _profile_icons:
            summoner = summoner.model_copy(update={"profile_icon_id": _profile_icons[puuid]})
        return summoner

    def set_profile_icon(self, puuid: str, icon_id: int) -> None:
        """Samo za način fixtures: simulira, da je igralec v odjemalcu zamenjal ikono."""
        if self._platform_of(puuid) is None:
            raise RiotNotFoundError("Ni igralca")
        _profile_icons[puuid] = icon_id

    def get_active_game(self, puuid: str, platform: str) -> ActiveGame | None:
        region_for(platform)
        for game in _load("active_games.json"):
            in_game = any(p.get("puuid") == puuid for p in game["participants"])
            if in_game and game["platformId"].lower() == platform:
                return ActiveGame.model_validate(game)
        return None

    def get_match_ids(
        self, puuid: str, platform: str, *, count: int = 20, queue: int | None = None
    ) -> list[str]:
        region_for(platform)
        check_match_count(count)
        matches = [_load(f"matches/{path.name}") for path in self._match_files()]
        matches = [
            m
            for m in matches
            if puuid in m["metadata"]["participants"]
            and m["info"]["platformId"].lower() == platform
            and (queue is None or m["info"]["queueId"] == queue)
        ]
        # Kot Riot: najnovejše tekme najprej.
        matches.sort(key=lambda m: m["info"]["gameCreation"], reverse=True)
        return [m["metadata"]["matchId"] for m in matches[:count]]

    def get_match(self, match_id: str, platform: str) -> Match:
        region_for(platform)
        files = {path.stem: path.name for path in self._match_files()}
        if match_id not in files:
            raise RiotNotFoundError(f"Ni tekme {match_id}")
        # Kopija, da klicatelj ne more spremeniti predpomnjenih podatkov.
        return copy.deepcopy(_load(f"matches/{files[match_id]}"))

    def get_match_timeline(self, match_id: str, platform: str) -> MatchTimeline:
        region_for(platform)
        files = {path.stem: path.name for path in (FIXTURES_DIR / "timelines").glob("*.json")}
        if match_id not in files:
            raise RiotNotFoundError(f"Ni časovnice tekme {match_id}")
        return copy.deepcopy(_load(f"timelines/{files[match_id]}"))

    def get_challenger_league(self, platform: str, queue: str = "RANKED_SOLO_5x5") -> LeagueList:
        region_for(platform)
        check_ranked_queue(queue)
        league = _load("challenger_leagues.json").get(platform)
        if league is None or league["queue"] != queue:
            # Riot za platformo brez igralcev vrne prazen seznam.
            return LeagueList(tier="CHALLENGER", queue=queue, entries=[])
        return LeagueList.model_validate(league)

    @staticmethod
    def _match_files() -> list[Path]:
        return sorted((FIXTURES_DIR / "matches").glob("*.json"))

    @staticmethod
    def _platform_of(puuid: str) -> str | None:
        for account in _load("accounts.json"):
            if account["puuid"] == puuid:
                return account["platform"]
        return None
