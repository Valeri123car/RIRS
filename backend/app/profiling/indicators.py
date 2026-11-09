"""Kazalniki igralnega sloga iz ene tekme (Match-V5 udeleženec).

Vsi kazalniki so "več = bolj izrazito" in izraženi na tekmo oziroma na minuto, da dolžina
tekme ne popači primerjave. Ker so vrednosti odvisne od vloge, se primerjajo z mediano
iste vloge (glej baselines.py).
"""

from typing import Any

# Tekme, krajše od tega, so remake ali predaja v prvih minutah (nekoristne za slog).
MIN_GAME_S = 900
EARLY_DEATHS_MINUTE = 14

AGGRESSION = "aggression"
ROAMING = "roaming"
FARMING = "farming"
EARLY_DEATHS = "early_deaths"
VISION = "vision"
INDICATORS = (AGGRESSION, ROAMING, FARMING, EARLY_DEATHS, VISION)

# Polja udeleženca, ki jih kazalniki potrebujejo (SQL za mediane izbere samo ta).
CHALLENGE_FIELDS = (
    "soloKills",
    "takedownsFirstXMinutes",
    "killsOnOtherLanesEarlyJungleAsLaner",
    "killsOnLanersEarlyJungleAsJungler",
    "getTakedownsInAllLanesEarlyJungleAsLaner",
    "teleportTakedowns",
    "visionScorePerMinute",
)
PARTICIPANT_FIELDS = ("totalMinionsKilled", "neutralMinionsKilled", "deaths", "teamPosition")


def slim_participant(p: dict[str, Any]) -> dict[str, Any]:
    """Zmanjšan udeleženec (brez ostalih ~100 polj), primeren za shranjevanje in SQL."""
    challenges = p.get("challenges") or {}
    return {
        **{k: p.get(k) for k in PARTICIPANT_FIELDS},
        "challenges": {k: challenges.get(k) for k in CHALLENGE_FIELDS},
    }


def _num(value: Any) -> float:
    return float(value) if isinstance(value, int | float) else 0.0


def compute_indicators(
    p: dict[str, Any], duration_s: int, deaths_before_14: int | None = None
) -> dict[str, float]:
    """Pet kazalnikov za enega udeleženca.

    - aggression: samostojni kili + zgodnji "takedowns" (do ~12. min) na tekmo;
    - roaming: kili/takedowni v drugih linijah, ko je igralec v liniji ali džungli, in
      takedowni po teleportu;
    - farming: CS na minuto (vojaki + džungelski);
    - early_deaths: smrti pred 14. min (iz časovnice); če je ni, ocena iz smrti na minuto;
    - vision: vision score na minuto.
    """
    minutes = max(duration_s, 1) / 60
    c = p.get("challenges") or {}
    deaths = deaths_before_14
    if deaths is None:
        deaths = _num(p.get("deaths")) / minutes * EARLY_DEATHS_MINUTE
    return {
        AGGRESSION: _num(c.get("soloKills")) + _num(c.get("takedownsFirstXMinutes")),
        ROAMING: _num(c.get("killsOnOtherLanesEarlyJungleAsLaner"))
        + _num(c.get("killsOnLanersEarlyJungleAsJungler"))
        + _num(c.get("getTakedownsInAllLanesEarlyJungleAsLaner"))
        + _num(c.get("teleportTakedowns")),
        FARMING: (_num(p.get("totalMinionsKilled")) + _num(p.get("neutralMinionsKilled")))
        / minutes,
        EARLY_DEATHS: float(deaths),
        VISION: _num(c.get("visionScorePerMinute")),
    }
