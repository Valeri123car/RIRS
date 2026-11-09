"""Nevarne sposobnosti nasprotnika iz opisov Data Dragon (US-05).

Opisi so v angleščini, zato ključne besede (stun, knock up, dash ...) preslikamo v slovenske
razloge. Nadzor (CC) je najnevarnejši, sledijo skoki (engage) in eksekucije; R ima prednost.
"""

import re
from typing import Any

from app.models.champion import Champion

# (vzorec, razlog, teža)
PATTERNS: tuple[tuple[re.Pattern[str], str, float], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), reason, weight)
    for pattern, reason, weight in (
        (r"\bstun", "omami (stun)", 3),
        (r"knock(s|ed|ing)? (up|back|aside)|airborne", "dvigne ali odbije (knock-up)", 3),
        (r"\broot|\bsnare|immobiliz", "ukoreni (root)", 3),
        (r"\bcharm", "očara (charm)", 3),
        (r"\btaunt", "izzove (taunt)", 3),
        (r"\bfear|\bflee|terrif", "prestraši (fear)", 3),
        (r"suppress", "zatre (suppression)", 3),
        (r"\bsleep|drows", "uspava (sleep)", 3),
        (r"\bsilence", "utiša (silence)", 2),
        (r"\bpull", "potegne k sebi", 2),
        (r"polymorph", "spremeni v žival (polymorph)", 3),
        (r"\bslow", "upočasni", 1),
        (
            r"\bdash|\bleap|\blunge|\bjump|\bblink|teleport|charges? (forward|toward)",
            "skok (engage)",
            2,
        ),
        (r"execut|missing health", "eksekucija pri nizkem zdravju", 2),
    )
)
R_BONUS = 1.5
MIN_ABILITIES = 2
MAX_ABILITIES = 3


def dangerous_abilities(champion: Champion) -> list[dict[str, Any]]:
    """2–3 najnevarnejše sposobnosti s slovenskim razlogom in časom obnove na rangu 1."""
    scored = []
    for spell in champion.spells or []:
        reasons = []
        score = 0.0
        for pattern, reason, weight in PATTERNS:
            if pattern.search(spell.get("description", "")) and reason not in reasons:
                reasons.append(reason)
                score += weight
        if spell["key"] == "R":
            score += R_BONUS
        scored.append((score, bool(reasons), spell, reasons))

    chosen = [s for s in scored if s[1]]
    chosen.sort(key=lambda s: -s[0])
    chosen = chosen[:MAX_ABILITIES]
    for extra in sorted((s for s in scored if not s[1]), key=lambda s: -s[0]):
        if len(chosen) >= MIN_ABILITIES:
            break
        chosen.append(extra)
    return [_describe(spell, reasons) for _, _, spell, reasons in chosen]


def _describe(spell: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    if not reasons:
        reasons = ["ultimat – največji vpliv v boju" if spell["key"] == "R" else "glavna škoda"]
    cooldown = (spell.get("cooldown") or [None])[0]
    if isinstance(cooldown, float) and cooldown.is_integer():
        cooldown = int(cooldown)
    return {
        "key": spell["key"],
        "name": spell["name"],
        "reason": ", ".join(reasons),
        "cooldown": cooldown,
    }
