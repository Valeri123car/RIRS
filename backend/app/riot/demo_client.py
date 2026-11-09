"""Demo igra za predstavitev: Riot ID DemoPyke#DEMO, DemoJinx#DEMO, DemoAmbessa#DEMO.

Ovije pravi Riot klient. Za tri demo Riot ID-je vrne izmišljeno aktivno tekmo (sestava ekip iz
app.demo), vse ostalo (pravi igralci, tekme, lige) gre skozi ovit klient. Analiza nato
poteka kot pri pravi tekmi (zajem → profiliranje → priporočila prek SSE); izmišljena je samo
sestava in imena. Profile sloga nasprotnikov dajo pravi igralci iz zbranih tekem po vlogi.
Klicev Riot API demo ne porabi.
"""

import time

from sqlalchemy import select

from app.db.session import get_session_factory
from app.demo import DEMO_TAG, ENEMY_ROLES, SCENARIOS, _style_puuids
from app.models.champion import Champion
from app.riot.client import RiotClient
from app.riot.errors import RiotNotFoundError
from app.riot.models import (
    Account,
    ActiveGame,
    ActiveGameParticipant,
    LeagueList,
    Match,
    MatchTimeline,
    Summoner,
)

PUUID_PREFIX = "demo-live-"
# Kratek premor, da je v spletni strani viden korak »Zajem tekme«.
CAPTURE_DELAY_S = 1.5
DEMO_ICON_ID = 29
DEMO_LEVEL = 120
RIOT_ID_TO_SCENARIO = {
    f"demo{title.lower()}": index for index, (title, _, _) in enumerate(SCENARIOS)
}


def is_demo_riot_id(game_name: str, tag_line: str) -> bool:
    return tag_line.upper() == DEMO_TAG and game_name.lower() in RIOT_ID_TO_SCENARIO


class DemoRiotClient:
    def __init__(self, inner: RiotClient, *, delay_s: float = CAPTURE_DELAY_S) -> None:
        self._inner = inner
        self._delay_s = delay_s

    def get_account(self, game_name: str, tag_line: str, platform: str) -> Account:
        if is_demo_riot_id(game_name, tag_line):
            return Account(
                puuid=f"{PUUID_PREFIX}{game_name.lower()}", game_name=game_name, tag_line=tag_line
            )
        return self._inner.get_account(game_name, tag_line, platform)

    def get_summoner(self, puuid: str, platform: str) -> Summoner:
        if puuid.startswith(PUUID_PREFIX):
            return Summoner(puuid=puuid, profile_icon_id=DEMO_ICON_ID, summoner_level=DEMO_LEVEL)
        return self._inner.get_summoner(puuid, platform)

    def get_active_game(self, puuid: str, platform: str) -> ActiveGame | None:
        if not puuid.startswith(PUUID_PREFIX):
            return self._inner.get_active_game(puuid, platform)
        index = RIOT_ID_TO_SCENARIO.get(puuid.removeprefix(PUUID_PREFIX))
        if index is None:
            raise RiotNotFoundError("Neznan demo igralec")
        time.sleep(self._delay_s)
        return self._build_game(index, puuid, platform)

    def get_match_ids(
        self, puuid: str, platform: str, *, count: int = 20, queue: int | None = None
    ) -> list[str]:
        return self._inner.get_match_ids(puuid, platform, count=count, queue=queue)

    def get_match(self, match_id: str, platform: str) -> Match:
        return self._inner.get_match(match_id, platform)

    def get_match_timeline(self, match_id: str, platform: str) -> MatchTimeline:
        return self._inner.get_match_timeline(match_id, platform)

    def get_challenger_league(self, platform: str, queue: str = "RANKED_SOLO_5x5") -> LeagueList:
        return self._inner.get_challenger_league(platform, queue)

    @staticmethod
    def _build_game(index: int, target_puuid: str, platform: str) -> ActiveGame:
        title, ours, theirs = SCENARIOS[index]
        with get_session_factory()() as session:
            champions = {c.name: c.id for c in session.scalars(select(Champion))}
            enemy_puuids = _style_puuids(session, 1)
        participants = []
        for i, (name, spells) in enumerate(ours):
            participants.append(
                ActiveGameParticipant(
                    puuid=target_puuid if i == 0 else f"demo-ally-{name}",
                    riot_id=f"Demo{title}#{DEMO_TAG}" if i == 0 else f"Zaveznik {i}#{DEMO_TAG}",
                    champion_id=champions[name],
                    team_id=100,
                    spell1_id=spells[0],
                    spell2_id=spells[1],
                )
            )
        for i, (name, spells) in enumerate(theirs, 1):
            participants.append(
                ActiveGameParticipant(
                    puuid=enemy_puuids[ENEMY_ROLES[name]][0],
                    riot_id=f"Nasprotnik {i}#{DEMO_TAG}",
                    champion_id=champions[name],
                    team_id=200,
                    spell1_id=spells[0],
                    spell2_id=spells[1],
                )
            )
        return ActiveGame(
            game_id=9_100_000_000 + index,
            platform_id=platform.upper(),
            game_queue_config_id=420,
            game_start_time=int(time.time() * 1000),
            participants=participants,
        )
