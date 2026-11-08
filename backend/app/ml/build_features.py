"""Značilke za model ocenjevanja buildov (US-04, F04).

Vrstica = igralec v tekmi: njegov šampion in vloga, sestava nasprotne ekipe (isti atributi kot
profil sestave F03) in dokončani predmeti (0/1 za vsak predmet). Cilj je zmaga. Model se nato
uporabi za razvrščanje kandidatnih buildov, ne kot obljubljena verjetnost zmage (ADR-0006).
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.analysis.enemy_comp import PHYSICAL_SHARE
from app.models.champion import RATED_ATTRIBUTES, Champion

# Sestava nasprotnikov: delež fizične škode (0–1) in vsota ocen 0–3 petih šampionov.
COMP_FEATURES: tuple[str, ...] = ("enemy_physical", *(f"enemy_{a}" for a in RATED_ATTRIBUTES))
BASE_FEATURES: tuple[str, ...] = ("champion", "position", "completed_count")
CATEGORICAL_FEATURES: tuple[str, ...] = ("champion", "position")
POSITIONS: tuple[str, ...] = ("", "TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")

# Predmet mora biti v učnih podatkih vsaj tolikokrat, da dobi svoj stolpec.
MIN_ITEM_COUNT = 5
# Kandidatni buildi: prvi 3 dokončani predmeti (po priljubljenosti pri šampionu).
CORE_SIZE = 3
MAX_CANDIDATES_PER_CHAMPION = 30


def comp_vector(enemies: Sequence[Champion]) -> dict[str, float]:
    """Vektor nasprotne sestave iz šampionov v bazi znanja."""
    physical = (
        sum(PHYSICAL_SHARE[c.damage_profile] for c in enemies) / len(enemies) if enemies else 0.5
    )
    vector = {"enemy_physical": physical}
    for attribute in RATED_ATTRIBUTES:
        vector[f"enemy_{attribute}"] = float(sum(getattr(c, attribute) for c in enemies))
    return vector


@dataclass(frozen=True)
class TrainingRow:
    match_id: str
    champion_id: int
    position: str
    comp: dict[str, float]
    items: tuple[int, ...]  # samo dokončani predmeti
    win: bool


@dataclass
class FeatureSpec:
    """Kateri stolpci so v modelu in podatki za sestavo kandidatov ob napovedi (JSON)."""

    item_ids: list[int]
    champion_games: dict[int, int] = field(default_factory=dict)
    champion_position: dict[int, str] = field(default_factory=dict)
    # Predmeti šampiona po priljubljenosti in pogosta jedra buildov (CORE_SIZE predmetov).
    champion_items: dict[int, list[int]] = field(default_factory=dict)
    champion_builds: dict[int, list[list[int]]] = field(default_factory=dict)
    # Povprečna sestava v učnih podatkih: izhodišče za razlago vpliva sestave na predmet.
    comp_mean: dict[str, float] = field(default_factory=dict)

    @property
    def columns(self) -> list[str]:
        return [*BASE_FEATURES, *COMP_FEATURES, *(f"item_{i}" for i in self.item_ids)]

    def to_json(self) -> dict[str, Any]:
        return {
            "columns": self.columns,
            "item_ids": self.item_ids,
            "champion_games": {str(k): v for k, v in self.champion_games.items()},
            "champion_position": {str(k): v for k, v in self.champion_position.items()},
            "champion_items": {str(k): v for k, v in self.champion_items.items()},
            "champion_builds": {str(k): v for k, v in self.champion_builds.items()},
            "comp_mean": self.comp_mean,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "FeatureSpec":
        def ints(mapping: dict[str, Any]) -> dict[int, Any]:
            return {int(k): v for k, v in mapping.items()}

        return cls(
            item_ids=list(data["item_ids"]),
            champion_games=ints(data.get("champion_games", {})),
            champion_position=ints(data.get("champion_position", {})),
            champion_items=ints(data.get("champion_items", {})),
            champion_builds=ints(data.get("champion_builds", {})),
            comp_mean=dict(data.get("comp_mean", {})),
        )

    def encode(self, champion_id: int, position: str, comp: dict[str, float], items: Iterable[int]):
        """Ena vrstica značilk (numpy) v vrstnem redu self.columns."""
        item_set = set(items)
        values = [
            float(champion_id),
            float(POSITIONS.index(position) if position in POSITIONS else 0),
            float(len(item_set)),
            *(comp.get(name, 0.0) for name in COMP_FEATURES),
            *(1.0 if i in item_set else 0.0 for i in self.item_ids),
        ]
        return np.asarray(values, dtype=np.float64)


def build_spec(rows: Sequence[TrainingRow]) -> FeatureSpec:
    item_counts = Counter(i for row in rows for i in row.items)
    item_ids = sorted(i for i, n in item_counts.items() if n >= MIN_ITEM_COUNT)

    spec = FeatureSpec(item_ids=item_ids)
    by_champion: dict[int, list[TrainingRow]] = {}
    for row in rows:
        by_champion.setdefault(row.champion_id, []).append(row)

    allowed = set(item_ids)
    for champion_id, champion_rows in by_champion.items():
        spec.champion_games[champion_id] = len(champion_rows)
        positions = Counter(r.position for r in champion_rows if r.position)
        spec.champion_position[champion_id] = positions.most_common(1)[0][0] if positions else ""
        popularity = Counter(i for r in champion_rows for i in r.items if i in allowed)
        ranked = [i for i, _ in popularity.most_common()]
        spec.champion_items[champion_id] = ranked
        order = {item: index for index, item in enumerate(ranked)}
        cores = Counter(
            tuple(sorted((i for i in r.items if i in order), key=order.__getitem__)[:CORE_SIZE])
            for r in champion_rows
        )
        spec.champion_builds[champion_id] = [
            list(core)
            for core, _ in cores.most_common(MAX_CANDIDATES_PER_CHAMPION)
            if len(core) == CORE_SIZE
        ]

    if rows:
        spec.comp_mean = {
            name: float(np.mean([row.comp.get(name, 0.0) for row in rows]))
            for name in COMP_FEATURES
        }
    return spec


def encode_rows(spec: FeatureSpec, rows: Sequence[TrainingRow]) -> tuple[np.ndarray, np.ndarray]:
    features = np.vstack([spec.encode(r.champion_id, r.position, r.comp, r.items) for r in rows])
    labels = np.asarray([1 if r.win else 0 for r in rows], dtype=np.int8)
    return features, labels
