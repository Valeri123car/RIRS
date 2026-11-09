"""Določitev linije šampionov v ekipi (US-05).

Spectator-V5 ne pove linij. Za vsakega šampiona vzamemo porazdelitev položajev iz zbranih
tekem (match_participants), Smite pomeni jungle, nato pregledamo vseh 120 razporeditev ekipe in
izračunamo verjetnost, da je šampion na posamezni liniji (zaupanje).
"""

import itertools
import math
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.match import MatchParticipant

POSITIONS = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")
SMITE_ID = 11
# Glajenje: šampion lahko zaigra tudi na nenavadni liniji.
SMOOTHING = 0.02
SMITE_JUNGLE = 0.97
NO_SMITE_JUNGLE_FACTOR = 0.05

RoleDistribution = dict[int, dict[str, float]]


def role_distribution(session: Session) -> RoleDistribution:
    """Delež iger šampiona na posamezni liniji v zbranih tekmah."""
    rows = session.execute(
        select(MatchParticipant.champion_id, MatchParticipant.position, func.count())
        .where(MatchParticipant.position.in_(POSITIONS))
        .group_by(MatchParticipant.champion_id, MatchParticipant.position)
    )
    counts: dict[int, dict[str, int]] = defaultdict(dict)
    for champion_id, position, count in rows:
        counts[champion_id][position] = count
    return {
        champion_id: {p: by_pos.get(p, 0) / sum(by_pos.values()) for p in POSITIONS}
        for champion_id, by_pos in counts.items()
    }


def _role_probs(champion_id: int, has_smite: bool, dist: RoleDistribution) -> dict[str, float]:
    base = dist.get(champion_id) or dict.fromkeys(POSITIONS, 1 / len(POSITIONS))
    probs = {p: (1 - 5 * SMOOTHING) * base.get(p, 0) + SMOOTHING for p in POSITIONS}
    if has_smite:
        rest = (1 - SMITE_JUNGLE) / (len(POSITIONS) - 1)
        return {p: SMITE_JUNGLE if p == "JUNGLE" else rest for p in POSITIONS}
    probs["JUNGLE"] *= NO_SMITE_JUNGLE_FACTOR
    return probs


def assign_roles(
    team: Sequence[tuple[int, bool]], dist: RoleDistribution
) -> dict[int, dict[str, Any]]:
    """team: (champion_id, ima_smite). Vrne {champion_id: {"role", "confidence"}}."""
    probs = [_role_probs(cid, smite, dist) for cid, smite in team]
    if len(team) != len(POSITIONS):
        return {
            cid: {"role": max(p, key=p.get), "confidence": round(max(p.values()), 3)}
            for (cid, _), p in zip(team, probs, strict=True)
        }

    marginal = [dict.fromkeys(POSITIONS, 0.0) for _ in team]
    best, best_weight, total = None, -1.0, 0.0
    for perm in itertools.permutations(POSITIONS):
        weight = math.prod(p[role] for p, role in zip(probs, perm, strict=True))
        total += weight
        for i, role in enumerate(perm):
            marginal[i][role] += weight
        if weight > best_weight:
            best, best_weight = perm, weight
    assert best is not None
    return {
        cid: {"role": role, "confidence": round(marginal[i][role] / total, 3)}
        for i, ((cid, _), role) in enumerate(zip(team, best, strict=True))
    }
