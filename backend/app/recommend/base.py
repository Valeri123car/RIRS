"""Skupni vmesnik priporočil (ADR-0006).

Model in pravila vrneta enako obliko, zato frontend ne ve, kateri način je bil uporabljen;
razlikujeta se samo po polju "source" (in "model_id" pri modelu).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.models.champion import Champion
from app.models.item import Item
from app.recommend.champion_stats import BuildStats

RULES_LABEL = "Priporočilo na podlagi pravil"
MODEL_LABEL = "Priporočilo modela"

# Variante builda (ADR-0007) v vrstnem redu prikaza.
VARIANTS: tuple[tuple[str, str], ...] = (
    ("standard", "Standardna"),
    ("safe", "Varna"),
    ("aggressive", "Agresivna"),
)


@dataclass(frozen=True)
class RecommendationInput:
    """Vhod za priporočilo: igralčev šampion, profil nasprotne sestave in predmeti patcha."""

    champion: Champion
    enemy_comp: dict[str, Any]
    items: Sequence[Item]
    # Nasprotni šampioni iz baze znanja (model iz njih izračuna vektor sestave).
    enemy_champions: Sequence[Champion] = ()
    # Kaj šampion v zbranih tekemah res kupuje (None: premalo iger → pravila po oznakah).
    build_stats: BuildStats | None = None


class Recommender(Protocol):
    def recommend(self, data: RecommendationInput) -> dict[str, Any] | None:
        """Vrne priporočilo z variantami ali None, če ga ni mogoče sestaviti."""
        ...
