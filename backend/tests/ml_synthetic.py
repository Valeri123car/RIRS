"""Sintetične tekme za teste modela buildov.

Šampion 1 kupuje predmete 101–106. Predmet 101 (anti-heal) poveča možnost zmage samo proti
ekipam z veliko zdravljenja, predmet 104 (oklep) samo proti fizični škodi; ostalo je šum.
Model mora te povezave najti, izhodiščni model brez sestave pa ne.
"""

import random

from app.ml.build_features import COMP_FEATURES, TrainingRow

ANTI_HEAL, ARMOR = 101, 104
CHAMPION_ITEMS = (101, 102, 103, 104, 105, 106)


def synthetic_rows(matches: int = 400, seed: int = 3) -> list[TrainingRow]:
    rng = random.Random(seed)
    rows: list[TrainingRow] = []
    for m in range(matches):
        for _team in (0, 1):
            healing = rng.choice((0.0, 2.0, 9.0))
            physical = rng.choice((0.2, 0.5, 0.9))
            comp = dict.fromkeys(COMP_FEATURES, 1.0)
            comp.update({"enemy_healing": healing, "enemy_physical": physical})
            for slot in range(5):
                items = tuple(sorted(rng.sample(CHAMPION_ITEMS, 3)))
                logit = 0.0
                if ANTI_HEAL in items:
                    logit += 2.5 if healing >= 9 else -1.0
                if ARMOR in items:
                    logit += 2.0 if physical >= 0.9 else -0.8
                win = rng.random() < 1 / (1 + 2.718**-logit)
                rows.append(
                    TrainingRow(
                        match_id=f"M{m}",
                        champion_id=1 if slot == 0 else 2 + slot,
                        position="TOP" if slot == 0 else "",
                        comp=comp,
                        items=items,
                        win=win,
                    )
                )
    return rows
