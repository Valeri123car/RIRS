"""Časovnica moči dveh šampionov od levela 1 do 18 (US-05, F05).

Moč je hevristika iz osnovnih statistik Data Dragon (brez podatkov o konkretni tekmi):
- obramba = zdravje × (1 + odpornost / 100), odpornost glede na vrsto škode nasprotnika,
- napad = osnovni napadi (AD × hitrost) in sposobnosti (točke v sposobnostih, R šteje več),
  utežena po glavnem razredu šampiona (strelec se zanaša na napade, čarovnik na sposobnosti),
- moč = √(napad × obramba); primerjava je delež moči (50 = izenačeno),
- faza igre iz zbranih tekem: win rate šampiona v kratkih (< 25 min) in dolgih (≥ 32 min)
  tekmah, skrčen proti 50 % (Bayes, PRIOR_GAMES). Zgodaj šteje kratki, pozno dolgi; tako se
  pokaže skaliranje sposobnosti (Kayle, Kog'Maw), ki ga osnovne statistike ne zajamejo.
Statistike rastejo po Riotovi formuli: osnova + rast × (L − 1) × (0,7025 + 0,0175 × (L − 1)).
"""

import math
from typing import Any

from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session

from app.models.champion import Champion, DamageProfile
from app.models.match import Match, MatchParticipant

LEVELS = range(1, 19)
R_LEVELS = (6, 11, 16)
# Delež moči, nad katerim je šampion v prednosti (pod 100 − prag v zaostanku).
ADVANTAGE_SHARE = 52.5
# (utež osnovnih napadov, utež sposobnosti) po glavnem razredu.
CLASS_WEIGHTS: dict[str, tuple[float, float]] = {
    "Marksman": (1.0, 0.45),
    "Mage": (0.3, 1.0),
    "Assassin": (0.5, 1.0),
    "Fighter": (0.75, 0.7),
    "Tank": (0.5, 0.5),
    "Support": (0.3, 0.6),
}
DEFAULT_WEIGHTS = CLASS_WEIGHTS["Fighter"]
# Škoda sposobnosti na vloženo točko; točka v R šteje kot R_POINT_VALUE osnovnih.
SPELL_DAMAGE_PER_POINT = 18.0
R_POINT_VALUE = 3.0
SPELL_SCALING_PER_LEVEL = 0.04
RATING_BONUS = 0.05
SHORT_GAME_S = 25 * 60
LONG_GAME_S = 32 * 60
MIN_GAME_S = 15 * 60
PRIOR_GAMES = 60
# Vpliv faze: 5 odstotnih točk win ratea spremeni moč za PHASE_WEIGHT × 5 %.
PHASE_WEIGHT = 3.0

PhaseStrength = dict[int, dict[str, float]]


def phase_strength_from_counts(counts: dict[int, tuple[int, int, int, int]]) -> PhaseStrength:
    """counts: {champion_id: (iger kratkih, zmag kratkih, iger dolgih, zmag dolgih)}."""
    prior = PRIOR_GAMES / 2
    return {
        cid: {
            "early": (wins_short + prior) / (short + PRIOR_GAMES),
            "late": (wins_long + prior) / (long + PRIOR_GAMES),
        }
        for cid, (short, wins_short, long, wins_long) in counts.items()
    }


def phase_strength(session: Session) -> PhaseStrength:
    """Moč šampionov v kratkih in dolgih tekmah iz zbranih tekem."""
    short = Match.duration_s < SHORT_GAME_S
    long = Match.duration_s >= LONG_GAME_S
    win = MatchParticipant.win.cast(Integer)
    rows = session.execute(
        select(
            MatchParticipant.champion_id,
            func.count().filter(short),
            func.coalesce(func.sum(case((short, win), else_=0)), 0),
            func.count().filter(long),
            func.coalesce(func.sum(case((long, win), else_=0)), 0),
        )
        .join(Match, Match.match_id == MatchParticipant.match_id)
        .where(Match.duration_s >= MIN_GAME_S)
        .group_by(MatchParticipant.champion_id)
    )
    return phase_strength_from_counts({row[0]: tuple(int(v) for v in row[1:]) for row in rows})


def _phase_factor(phases: PhaseStrength | None, champion: Champion, level: int) -> float:
    phase = (phases or {}).get(champion.id)
    if phase is None:
        return 1.0
    late = (level - 1) / (len(LEVELS) - 1)
    edge = (1 - late) * (phase["early"] - 0.5) + late * (phase["late"] - 0.5)
    return 1 + PHASE_WEIGHT * edge


def stat_at(base: float, growth: float, level: int) -> float:
    steps = level - 1
    return base + growth * steps * (0.7025 + 0.0175 * steps)


def r_rank(level: int) -> int:
    return sum(level >= r for r in R_LEVELS)


def _attack_speed(stats: dict[str, float], level: int) -> float:
    bonus = stat_at(0, stats.get("attackspeedperlevel", 0) / 100, level)
    return stats.get("attackspeed", 0.625) * (1 + bonus)


def _offense(champion: Champion, level: int) -> float:
    stats = champion.stats
    auto_weight, spell_weight = CLASS_WEIGHTS.get(
        (champion.classes or ["Fighter"])[0], DEFAULT_WEIGHTS
    )
    autos = stat_at(stats["attackdamage"], stats.get("attackdamageperlevel", 0), level)
    autos *= _attack_speed(stats, level)
    points = (level - r_rank(level)) + R_POINT_VALUE * r_rank(level)
    spells = SPELL_DAMAGE_PER_POINT * points * (1 + SPELL_SCALING_PER_LEVEL * (level - 1))
    return (auto_weight * autos + spell_weight * spells) * (1 + RATING_BONUS * champion.burst)


def _defense(champion: Champion, level: int, against: DamageProfile) -> float:
    stats = champion.stats
    hp = stat_at(stats["hp"], stats.get("hpperlevel", 0), level)
    armor = stat_at(stats.get("armor", 0), stats.get("armorperlevel", 0), level)
    resist = stat_at(stats.get("spellblock", 0), stats.get("spellblockperlevel", 0), level)
    if against == DamageProfile.PHYSICAL:
        mitigation = armor
    elif against == DamageProfile.MAGIC:
        mitigation = resist
    else:
        mitigation = (armor + resist) / 2
    return hp * (1 + mitigation / 100) * (1 + RATING_BONUS * champion.tank)


def _power(
    champion: Champion, opponent: Champion, level: int, phases: PhaseStrength | None
) -> float:
    base = math.sqrt(_offense(champion, level) * _defense(champion, level, opponent.damage_profile))
    return base * _phase_factor(phases, champion, level)


def _has_stats(champion: Champion) -> bool:
    return all(key in (champion.stats or {}) for key in ("hp", "attackdamage"))


def power_curve(
    champion: Champion, opponent: Champion, phases: PhaseStrength | None = None
) -> list[dict[str, Any]]:
    """Delež moči obeh šampionov po levelih; prazno, če manjkajo statistike."""
    if not _has_stats(champion) or not _has_stats(opponent):
        return []
    curve = []
    for level in LEVELS:
        mine = _power(champion, opponent, level, phases)
        theirs = _power(opponent, champion, level, phases)
        share = 100 * mine / (mine + theirs)
        if share >= ADVANTAGE_SHARE:
            state = "advantage"
        elif share <= 100 - ADVANTAGE_SHARE:
            state = "disadvantage"
        else:
            state = "even"
        curve.append(
            {"level": level, "you": round(share, 1), "enemy": round(100 - share, 1), "state": state}
        )
    return curve


def power_windows(curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Zaporedni leveli prednosti ali zaostanka združeni v okna z razlogom."""
    windows: list[dict[str, Any]] = []
    for point in curve:
        if point["state"] == "even":
            continue
        last = windows[-1] if windows else None
        if last and last["state"] == point["state"] and last["to"] == point["level"] - 1:
            last["to"] = point["level"]
        else:
            windows.append({"from": point["level"], "to": point["level"], "state": point["state"]})
    for window in windows:
        window["reason"] = _reason(window)
    return windows


def _reason(window: dict[str, Any]) -> str:
    start, end = window["from"], window["to"]
    if end - start >= 9:
        return "večino igre – boljše osnovne statistike in razmerje moči"
    if start <= 3:
        return "zgodnja igra – osnovne statistike in prve sposobnosti"
    if start <= 6 <= end and end - start <= 4:
        return "level 6 – ultimat (R)"
    if start >= 11 or end == LEVELS[-1]:
        return "pozna igra – skaliranje"
    return "rast statistik po levelih"
