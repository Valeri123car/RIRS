"""Odgovori Riot API, ki jih uporablja aplikacija (ostala polja se ignorirajo).

Riot vrača camelCase; modeli jih preslikajo v snake_case. Tekme (Match-V5) so obsežne in
se shranijo kot JSONB, zato jih klient vrača kot slovar.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Match = dict[str, Any]
MatchTimeline = dict[str, Any]


class RiotModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class Account(RiotModel):
    puuid: str
    game_name: str
    tag_line: str


class Summoner(RiotModel):
    puuid: str
    profile_icon_id: int
    summoner_level: int


class Perks(RiotModel):
    perk_ids: list[int] = Field(default_factory=list)
    perk_style: int
    perk_sub_style: int


class ActiveGameParticipant(RiotModel):
    puuid: str | None = None  # None za igralce v načinu "streamer"
    riot_id: str | None = None
    champion_id: int
    team_id: int
    spell1_id: int
    spell2_id: int
    perks: Perks | None = None


class ActiveGame(RiotModel):
    game_id: int
    platform_id: str
    game_queue_config_id: int | None = None
    game_start_time: int
    participants: list[ActiveGameParticipant]


class LeagueEntry(RiotModel):
    puuid: str
    league_points: int
    wins: int = 0
    losses: int = 0


class LeagueList(RiotModel):
    """League-V4: liga (npr. challenger) z vsemi igralci v njej."""

    tier: str
    queue: str
    entries: list[LeagueEntry] = Field(default_factory=list)
