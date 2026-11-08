"""Profil nasprotne sestave (US-03, F03): delež fizične/magične škode in glavne grožnje.

Izračun temelji na bazi znanja o šampionih (tabela champions): profil škode in ocene 0–3 za
zdravljenje, CC, engage, burst, poke in tankovskost.
"""

from collections.abc import Sequence
from typing import Any

from app.models.champion import Champion, DamageProfile

MAX_THREATS = 5
# Šampion prispeva h grožnji, če ima oceno vsaj toliko (0–3).
CONTRIBUTOR_MIN_RATING = 2

# Vrstni red določa razvrstitev pri enaki moči (prej nevarnejše za build).
THREATS: tuple[tuple[str, str], ...] = (
    ("healing", "Zdravljenje"),
    ("engage", "Engage"),
    ("burst", "Burst"),
    ("cc", "Nadzor (CC)"),
    ("poke", "Poke"),
    ("tank", "Tankovskost"),
)

# Delež fizične škode po profilu šampiona (ostalo je magična škoda).
PHYSICAL_SHARE = {DamageProfile.PHYSICAL: 1.0, DamageProfile.MAGIC: 0.0, DamageProfile.MIXED: 0.5}


def threat_level(score: int) -> str:
    """Stopnja grožnje iz vsote ocen ekipe (5 šampionov × 0–3)."""
    if score >= 8:
        return "very_high"
    if score >= 5:
        return "high"
    return "medium"


def build_enemy_comp(champions: Sequence[Champion], missing: int = 0) -> dict[str, Any]:
    """Profil sestave za podane šampione nasprotne ekipe.

    missing = število nasprotnikov, katerih šampiona ni v bazi znanja (niso upoštevani).
    """
    physical = round(
        100 * sum(PHYSICAL_SHARE[c.damage_profile] for c in champions) / len(champions)
        if champions
        else 50
    )

    threats = []
    for order, (attribute, label) in enumerate(THREATS):
        contributors = sorted(
            (c for c in champions if getattr(c, attribute) >= CONTRIBUTOR_MIN_RATING),
            key=lambda c: (-getattr(c, attribute), c.name),
        )
        if not contributors:
            continue
        score = sum(getattr(c, attribute) for c in champions)
        threats.append(
            {
                "key": attribute,
                "label": label,
                "score": score,
                "level": threat_level(score),
                "champions": [c.name for c in contributors],
                "_order": order,
            }
        )
    threats.sort(key=lambda t: (-t["score"], t["_order"]))
    for threat in threats:
        del threat["_order"]

    return {
        "damage": {"physical": physical, "magic": 100 - physical},
        "threats": threats[:MAX_THREATS],
        "champion_count": len(champions),
        "missing_champions": missing,
    }
