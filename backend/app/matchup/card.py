"""Matchup kartica za linijo (US-05): nasprotnik, časovnica moči, nevarne sposobnosti, nasveti."""

from typing import Any

from app.matchup.abilities import dangerous_abilities
from app.matchup.power import PhaseStrength, power_curve, power_windows
from app.matchup.roles import SMITE_ID, RoleDistribution, assign_roles
from app.models.champion import Champion

# Najmanjše zaupanje v linijo igralca in nasprotnika, da nasprotnika določimo samodejno.
MIN_CONFIDENCE = 0.6
RANGE_GAP = 150
MAX_TIPS = 3


def build_matchup_card(
    participants: list[dict[str, Any]],
    champions: dict[int, Champion],
    dist: RoleDistribution,
    opponent_id: int | None = None,
    phases: PhaseStrength | None = None,
) -> dict[str, Any]:
    """Kartica za igralca (is_target). Brez zanesljivega nasprotnika je opponent None in
    igralec izbere enega izmed kandidatov (opponent_id)."""
    target = next(p for p in participants if p["is_target"])
    team = [p for p in participants if p["team_id"] == target["team_id"]]
    enemies = [p for p in participants if p["team_id"] != target["team_id"]]
    candidates = [{"id": p["champion_id"], "name": _name(p, champions)} for p in enemies]

    own_roles = assign_roles([_slot(p) for p in team], dist)
    own = own_roles.get(target["champion_id"], {"role": None, "confidence": 0.0})
    card: dict[str, Any] = {
        "champion": {"id": target["champion_id"], "name": _name(target, champions)},
        "role": own["role"],
        "opponent": None,
        "opponent_source": None,
        "confidence": None,
        "candidates": candidates,
        "levels": [],
        "windows": [],
        "dangerous_abilities": [],
        "tips": [],
    }

    if opponent_id is not None:
        if opponent_id not in {c["id"] for c in candidates}:
            raise ValueError("Nasprotnik mora biti eden izmed petih nasprotnih šampionov.")
        card["opponent_source"] = "choice"
    else:
        enemy_roles = assign_roles([_slot(p) for p in enemies], dist)
        match = next((cid for cid, r in enemy_roles.items() if r["role"] == own["role"]), None)
        confidence = min(own["confidence"], enemy_roles[match]["confidence"]) if match else 0.0
        card["confidence"] = round(confidence, 3)
        if match is None or confidence < MIN_CONFIDENCE:
            return card
        opponent_id = match
        card["opponent_source"] = "auto"

    card["opponent"] = next(c for c in candidates if c["id"] == opponent_id)
    me, opponent = champions.get(target["champion_id"]), champions.get(opponent_id)
    if me is None or opponent is None:
        return card
    card["levels"] = power_curve(me, opponent, phases)
    card["windows"] = power_windows(card["levels"])
    card["dangerous_abilities"] = dangerous_abilities(opponent)
    card["tips"] = lane_tips(me, opponent, card["windows"], card["dangerous_abilities"])
    return card


def _slot(participant: dict[str, Any]) -> tuple[int, bool]:
    spells = {participant.get("spell1_id"), participant.get("spell2_id")}
    return participant["champion_id"], SMITE_ID in spells


def _name(participant: dict[str, Any], champions: dict[int, Champion]) -> str:
    champion = champions.get(participant["champion_id"])
    if champion is not None:
        return champion.name
    return participant.get("champion_name") or f"Šampion {participant['champion_id']}"


def _levels(window: dict[str, Any]) -> str:
    if window["from"] == window["to"]:
        return f"levelu {window['from']}"
    return f"levelih {window['from']}–{window['to']}"


def lane_tips(
    me: Champion,
    opponent: Champion,
    windows: list[dict[str, Any]],
    abilities: list[dict[str, Any]],
) -> list[str]:
    """2–3 nasveti za linijsko fazo (do levela 11) iz oken moči, sposobnosti in dosega."""
    tips: list[str] = []
    lane = [w for w in windows if w["from"] <= 11]
    danger = next((w for w in lane if w["state"] == "disadvantage"), None)
    chance = next((w for w in lane if w["state"] == "advantage"), None)
    if danger:
        tips.append(
            f"{opponent.name} ima prednost na {_levels(danger)} ({danger['reason']}): ne sprejemaj "
            "daljših menjav, farmaj varno in drži val bližje svojemu stolpu."
        )
    if chance:
        tips.append(
            f"Na {_levels(chance)} imaš prednost ({chance['reason']}): išči menjave in pritiskaj "
            "val, ko je nasprotnik brez ključne sposobnosti."
        )

    cc = next((a for a in abilities if "(" in a["reason"]), None)
    if cc:
        cooldown = f" (obnova ~{cc['cooldown']} s)" if cc.get("cooldown") else ""
        tips.append(
            f"Pazi na {cc['key']} – {cc['name']}: {cc['reason']}. Ko ga porabi{cooldown}, "
            "imaš varno okno za napad."
        )

    my_range = me.stats.get("attackrange", 0)
    their_range = opponent.stats.get("attackrange", 0)
    if their_range - my_range >= RANGE_GAP:
        tips.append(
            f"{opponent.name} ima večji doseg napada ({their_range:.0f} proti {my_range:.0f}): "
            "minione pobiraj, ko nasprotnik napada val, sicer te bo obstreljeval."
        )
    elif my_range - their_range >= RANGE_GAP:
        tips.append(
            f"Imaš večji doseg ({my_range:.0f} proti {their_range:.0f}): ob vsakem zadnjem "
            "udarcu nasprotnika ustreli in mu znižaj zdravje."
        )
    if opponent.healing >= 2:
        tips.append(
            f"{opponent.name} ima močno zdravljenje: zgodaj kupi predmet z Grievous Wounds."
        )
    if len(tips) < 2:
        tips.append(
            "Spremljaj razliko v levelih: en level prednosti v linijski fazi pogosto "
            "odloči menjavo."
        )
    return tips[:MAX_TIPS]
