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
# Stanje igralca in ekipe za model buildov: samo podatki, znani do te minute (brez izida).
STATE_MINUTE = 15
TIMELINE_VERSION = 2
MONSTER_COUNTERS = {
    "DRAGON": "dragons",
    "HORDE": "grubs",
    "RIFTHERALD": "heralds",
    "BARON_NASHOR": "barons",
}
TEAM_COUNTERS = ("deaths", "dragons", "grubs", "heralds", "barons", "towers", "plates")


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


def timeline_features(timeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Značilke zgodnje igre po igralcih (puuid -> značilke) iz časovnice Match-V5.

    Kratka tekma (npr. predaja pred 15. minuto) nima vseh okvirjev; manjkajoča značilka
    se izpusti. Nepopolna časovnica vrne prazen slovar (tekma se shrani brez značilk).
    Različica 2 doda stanje igralca in ekipe ob STATE_MINUTE ter nakupe s časom.
    """
    try:
        info = timeline["info"]
        puuids = {int(p["participantId"]): str(p["puuid"]) for p in info["participants"]}
        frames = info["frames"]
        features: dict[str, dict[str, Any]] = {
            puuid: {"timeline_v": TIMELINE_VERSION} for puuid in puuids.values()
        }

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

        for pid, purchases in _purchases(frames, puuids).items():
            features[puuids[pid]]["purchases"] = purchases
        state_frame = _frame_at(frames, STATE_MINUTE)
        if state_frame is not None:
            for pid, values in _state_at(state_frame, frames, puuids).items():
                features[puuids[pid]].update(values)
        return features
    except (KeyError, TypeError, ValueError):
        return {}


def _team(participant_id: int) -> int:
    """Match-V5: igralci 1–5 so v ekipi 100, 6–10 v ekipi 200."""
    return TEAMS[0] if participant_id <= 5 else TEAMS[1]


def _events_before(frames: list[dict[str, Any]], minute: int):
    limit = minute * 60_000
    for frame in frames:
        for event in frame.get("events", []):
            if int(event["timestamp"]) < limit:
                yield event


def _purchases(frames: list[dict[str, Any]], puuids: dict[int, str]) -> dict[int, list[list[int]]]:
    """Nakupi po igralcih kot [predmet, sekunda]; ITEM_UNDO odstrani zadnji nakup predmeta."""
    bought: dict[int, list[list[int]]] = {pid: [] for pid in puuids}
    for frame in frames:
        for event in frame.get("events", []):
            pid = int(event.get("participantId", 0))
            if pid not in bought:
                continue
            if event["type"] == "ITEM_PURCHASED":
                bought[pid].append([int(event["itemId"]), int(event["timestamp"]) // 1000])
            elif event["type"] == "ITEM_UNDO":
                undone = int(event.get("beforeId", 0))
                for i in range(len(bought[pid]) - 1, -1, -1):
                    if bought[pid][i][0] == undone:
                        del bought[pid][i]
                        break
    return bought


def _state_at(
    frame: dict[str, Any], frames: list[dict[str, Any]], puuids: dict[int, str]
) -> dict[int, dict[str, int]]:
    """Stanje igralca in ekipe ob STATE_MINUTE (okvir) in dogodki pred to minuto."""
    states = frame["participantFrames"]
    player: dict[int, dict[str, int]] = {}
    for pid in puuids:
        state = states[str(pid)]
        values = {
            "gold_15": int(state["totalGold"]),
            "xp_15": int(state["xp"]),
            "level_15": int(state["level"]),
            "cs_15": _cs(state),
        }
        damage = state.get("damageStats") or {}
        if "totalDamageDoneToChampions" in damage:
            values["dmg_champ_15"] = int(damage["totalDamageDoneToChampions"])
        if "totalDamageTaken" in damage:
            values["dmg_taken_15"] = int(damage["totalDamageTaken"])
        values.update(
            kills_15=0, deaths_15=0, assists_15=0, shutdown_gold_15=0, shutdowns_given_15=0
        )
        player[pid] = values

    team_gold = dict.fromkeys(TEAMS, 0)
    team_xp = dict.fromkeys(TEAMS, 0)
    for pid, values in player.items():
        team_gold[_team(pid)] += values["gold_15"]
        team_xp[_team(pid)] += values["xp_15"]

    team: dict[int, dict[str, int]] = {t: dict.fromkeys(TEAM_COUNTERS, 0) for t in TEAMS}
    first_blood: int | None = None
    for event in _events_before(frames, STATE_MINUTE):
        kind = event["type"]
        if kind == "CHAMPION_KILL":
            killer, victim = int(event.get("killerId", 0)), int(event.get("victimId", 0))
            if killer in player:
                player[killer]["kills_15"] += 1
                player[killer]["shutdown_gold_15"] += int(event.get("shutdownBounty", 0))
            if victim in player:
                player[victim]["deaths_15"] += 1
                if int(event.get("shutdownBounty", 0)) > 0:
                    player[victim]["shutdowns_given_15"] += 1
                team[_team(victim)]["deaths"] += 1
                if first_blood is None:
                    first_blood = TEAMS[1] if _team(victim) == TEAMS[0] else TEAMS[0]
            for assistant in event.get("assistingParticipantIds") or []:
                if int(assistant) in player:
                    player[int(assistant)]["assists_15"] += 1
        elif kind == "ELITE_MONSTER_KILL":
            counter = MONSTER_COUNTERS.get(str(event.get("monsterType")))
            if counter and int(event.get("killerTeamId", 0)) in team:
                team[int(event["killerTeamId"])][counter] += 1
        elif kind in ("BUILDING_KILL", "TURRET_PLATE_DESTROYED"):
            if kind == "BUILDING_KILL" and event.get("buildingType") != "TOWER_BUILDING":
                continue
            owner = int(event.get("teamId", 0))  # teamId je ekipa, ki je stavbo izgubila
            if owner in team:
                taker = TEAMS[1] if owner == TEAMS[0] else TEAMS[0]
                team[taker]["towers" if kind == "BUILDING_KILL" else "plates"] += 1

    result: dict[int, dict[str, int]] = {}
    for pid, values in player.items():
        own = _team(pid)
        enemy = TEAMS[1] if own == TEAMS[0] else TEAMS[0]
        values["team_gold_diff_15"] = team_gold[own] - team_gold[enemy]
        values["team_xp_diff_15"] = team_xp[own] - team_xp[enemy]
        values["team_kills_15"] = team[enemy]["deaths"]
        values["enemy_kills_15"] = team[own]["deaths"]
        for counter in TEAM_COUNTERS:
            if counter == "deaths":
                continue
            values[f"team_{counter}_15"] = team[own][counter]
            values[f"enemy_{counter}_15"] = team[enemy][counter]
        values["first_blood_team"] = int(first_blood == own)
        result[pid] = values
    return result


def _frame_at(frames: list[dict[str, Any]], minute: int) -> dict[str, Any] | None:
    """Prvi okvir ob ali po dani minuti (Riot okvirje zapiše vsakih ~60 s)."""
    for frame in frames:
        if int(frame["timestamp"]) >= minute * 60_000:
            return frame
    return None


def _cs(state: dict[str, Any]) -> int:
    return int(state["minionsKilled"]) + int(state["jungleMinionsKilled"])
