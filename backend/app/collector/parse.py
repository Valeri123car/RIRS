"""Pretvorba odgovorov Match-V5 (tekma in časovnica) v vrstice za bazo.

Odgovori pridejo od zunaj, zato jih preverimo: tekma brez 10 igralcev, zmagovalca ali z
napačnim ID-jem se ne shrani (MatchParseError), da učni podatki ostanejo čisti.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

TEAMS = (100, 200)
ITEM_SLOTS = tuple(f"item{i}" for i in range(7))
# Minute, ob katerih iz časovnice vzamemo stanje igralca (docs/03: CS@10, zlato @15 ...).
CS_MINUTE = 10
GOLD_MINUTE = 15
EARLY_DEATHS_MINUTE = 14


class MatchParseError(ValueError):
    """Odgovor Match-V5 nima pričakovane oblike."""


@dataclass(frozen=True)
class ParsedParticipant:
    puuid: str
    game_name: str
    tag_line: str
    participant_id: int
    team_id: int
    champion_id: int
    position: str
    kills: int
    deaths: int
    assists: int
    items: list[int]
    win: bool


@dataclass(frozen=True)
class ParsedMatch:
    match_id: str
    platform: str
    queue_id: int
    patch: str
    game_start: datetime
    duration_s: int
    winning_team: int
    participants: list[ParsedParticipant] = field(default_factory=list)


def parse_match(raw: dict[str, Any], expected_id: str) -> ParsedMatch:
    try:
        metadata, info = raw["metadata"], raw["info"]
        match_id = str(metadata["matchId"])
        if match_id != expected_id:
            raise MatchParseError(f"Riot je vrnil tekmo {match_id} namesto {expected_id}")
        participants = [_parse_participant(p, i) for i, p in enumerate(info["participants"])]
        winners = [t["teamId"] for t in info["teams"] if t.get("win") is True]
        start_ms = info.get("gameStartTimestamp") or info["gameCreation"]
        parsed = ParsedMatch(
            match_id=match_id,
            platform=str(info["platformId"]).lower()[:8],
            queue_id=int(info["queueId"]),
            patch=_patch(str(info["gameVersion"])),
            game_start=datetime.fromtimestamp(int(start_ms) / 1000, tz=UTC),
            duration_s=int(info["gameDuration"]),
            winning_team=winners[0] if len(winners) == 1 else 0,
            participants=participants,
        )
    except MatchParseError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise MatchParseError(f"Nepopolna tekma {expected_id}: {exc!r}") from exc

    if len(parsed.participants) != 10 or len({p.puuid for p in parsed.participants}) != 10:
        raise MatchParseError(f"Tekma {match_id} nima 10 različnih igralcev")
    if parsed.winning_team not in TEAMS:
        raise MatchParseError(f"Tekma {match_id} nima zmagovalne ekipe")
    return parsed


def _parse_participant(p: dict[str, Any], index: int) -> ParsedParticipant:
    team_id = int(p["teamId"])
    if team_id not in TEAMS:
        raise MatchParseError(f"Neznana ekipa {team_id}")
    puuid = str(p["puuid"])
    if not puuid or len(puuid) > 78:
        raise MatchParseError("Neveljaven puuid")
    return ParsedParticipant(
        puuid=puuid,
        # Riot ID je lahko prazen (stari računi); dolžina kot v riot_accounts.
        game_name=str(p.get("riotIdGameName") or "")[:32],
        tag_line=str(p.get("riotIdTagline") or "")[:8],
        participant_id=int(p.get("participantId") or index + 1),
        team_id=team_id,
        champion_id=int(p["championId"]),
        position=str(p.get("teamPosition") or "")[:16],
        kills=int(p["kills"]),
        deaths=int(p["deaths"]),
        assists=int(p["assists"]),
        items=[int(p[slot]) for slot in ITEM_SLOTS if p.get(slot)],
        win=bool(p["win"]),
    )


def _patch(game_version: str) -> str:
    """ "16.22.734.5678" -> "16.22"."""
    parts = game_version.split(".")
    if len(parts) < 2 or not all(part.isdigit() for part in parts[:2]):
        raise MatchParseError(f"Neznana verzija igre {game_version!r}")
    return ".".join(parts[:2])


def timeline_features(timeline: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Značilke zgodnje igre po igralcih (puuid -> značilke) iz časovnice Match-V5.

    Kratka tekma (npr. predaja pred 15. minuto) nima vseh okvirjev; manjkajoča značilka
    se izpusti. Nepopolna časovnica vrne prazen slovar (tekma se shrani brez značilk).
    """
    try:
        info = timeline["info"]
        puuids = {int(p["participantId"]): str(p["puuid"]) for p in info["participants"]}
        frames = info["frames"]
        features: dict[str, dict[str, int]] = {puuid: {} for puuid in puuids.values()}

        for name, minute, value in (
            ("cs_at_10", CS_MINUTE, _cs),
            ("xp_at_10", CS_MINUTE, lambda f: int(f["xp"])),
            ("gold_at_15", GOLD_MINUTE, lambda f: int(f["totalGold"])),
        ):
            frame = _frame_at(frames, minute)
            if frame is None:
                continue
            for pid, puuid in puuids.items():
                state = frame["participantFrames"].get(str(pid))
                if state is not None:
                    features[puuid][name] = value(state)

        deaths = dict.fromkeys(puuids.values(), 0)
        for frame in frames:
            for event in frame.get("events", []):
                if (
                    event.get("type") == "CHAMPION_KILL"
                    and int(event["timestamp"]) < EARLY_DEATHS_MINUTE * 60_000
                    and int(event.get("victimId", 0)) in puuids
                ):
                    deaths[puuids[int(event["victimId"])]] += 1
        for puuid, count in deaths.items():
            features[puuid]["deaths_before_14"] = count
        return features
    except (KeyError, TypeError, ValueError):
        return {}


def _frame_at(frames: list[dict[str, Any]], minute: int) -> dict[str, Any] | None:
    """Prvi okvir ob ali po dani minuti (Riot okvirje zapiše vsakih ~60 s)."""
    for frame in frames:
        if int(frame["timestamp"]) >= minute * 60_000:
            return frame
    return None


def _cs(state: dict[str, Any]) -> int:
    return int(state["minionsKilled"]) + int(state["jungleMinionsKilled"])
