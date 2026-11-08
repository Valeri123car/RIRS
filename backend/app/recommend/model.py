"""Priporočilo builda z modelom LightGBM (US-04, ADR-0006, ADR-0007).

Kandidatni buildi so pogosta jedra (prvi 3 dokončani predmeti) šampiona iz zbranih tekem in
jedra variant iz pravil. Model vsakega oceni glede na šampiona, vlogo in nasprotno sestavo;
standardna varianta je najbolje ocenjena, varna in agresivna sta med najboljšimi tista z
največ oziroma najmanj obrambe. Razlog za predmet izhaja iz njegovega SHAP prispevka
(LightGBM pred_contrib): lastnost sestave, ki prispevek predmeta najbolj poveča, je navedena
v razlogu. Če model ni aktiven ali ima šampion premalo tekem, se uporabijo pravila.
"""

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from app.ml.build_features import COMP_FEATURES, FeatureSpec, comp_vector
from app.ml.build_ranker import LoadedRanker
from app.models.champion import Champion
from app.models.item import Item
from app.recommend.base import MODEL_LABEL, VARIANTS, RecommendationInput, Recommender
from app.recommend.rules import RuleBasedRecommender, profile_for, skill_levels

# Najmanj tekem šampiona v učnih podatkih, da modelu zaupamo (sicer pravila).
MIN_CHAMPION_GAMES = 20
MIN_CANDIDATES = 2
# Varna in agresivna varianta se izbereta med toliko najbolje ocenjenimi kandidati.
TOP_CANDIDATES = 10
DEFENSIVE_TAGS = frozenset({"armor", "spell_block", "magic_resist", "health"})
CONTRIBUTOR_MIN_RATING = 2
MAX_NAMED_CHAMPIONS = 3

# Lastnosti sestave za razloge: (imenovalnik, rodilnik za "malo ...").
COMP_PHRASES = {
    "enemy_healing": ("zdravljenje", "zdravljenja"),
    "enemy_cc": ("nadzor (CC)", "nadzora (CC)"),
    "enemy_engage": ("engage", "engagea"),
    "enemy_burst": ("burst", "bursta"),
    "enemy_tank": ("tankovskost", "tankovskosti"),
    "enemy_poke": ("poke", "pokea"),
}
# Manjši vpliv (v odstotnih točkah) se prikaže kot 0,0 in ne šteje kot priporočilo.
MIN_SHOWN_POINTS = 0.05
RATING_SUM_MAX = 15


class ModelRecommender:
    def __init__(self, ranker: LoadedRanker | None, fallback: Recommender | None = None):
        self.ranker = ranker
        self.fallback = fallback or RuleBasedRecommender()

    def recommend(self, data: RecommendationInput) -> dict[str, Any] | None:
        result = self._recommend(data) if self.ranker is not None else None
        return result if result is not None else self.fallback.recommend(data)

    def _recommend(self, data: RecommendationInput) -> dict[str, Any] | None:
        assert self.ranker is not None
        spec = self.ranker.spec
        champion = data.champion
        if spec.champion_games.get(champion.id, 0) < MIN_CHAMPION_GAMES:
            return None
        if not data.enemy_champions:
            return None

        items = {i.id: i for i in data.items if i.completed and i.id in set(spec.item_ids)}
        candidates = self._candidates(data, spec, items)
        if len(candidates) < MIN_CANDIDATES:
            return None

        comp = comp_vector(data.enemy_champions)
        position = spec.champion_position.get(champion.id, "")
        matrix = np.vstack([spec.encode(champion.id, position, comp, c) for c in candidates])
        scores = self.ranker.booster.predict(matrix)
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda cs: -cs[1])

        explainer = _Explainer(self.ranker, champion, position, comp, data)
        profile = profile_for(champion)
        variants = []
        for key, (build, score) in _choose_variants(ranked, items):
            label = dict(VARIANTS)[key]
            primary_tree, keystone, secondary_tree = profile.runes[key]
            variants.append(
                {
                    "key": key,
                    "label": label,
                    "score": round(float(score), 3),
                    "runes": {
                        "primary_tree": primary_tree,
                        "keystone": keystone,
                        "secondary_tree": secondary_tree,
                    },
                    "items": [
                        {"id": item_id, "name": items[item_id].name, "reason": reason}
                        for item_id, reason in explainer.reasons(build)
                    ],
                    "skill_order": {
                        "priority": list(profile.skill_priority),
                        "levels": skill_levels(profile.skill_priority),
                    },
                }
            )
        return {
            "source": "model",
            "label": MODEL_LABEL,
            "model_id": self.ranker.model_id,
            "champion": {"id": champion.id, "name": champion.name},
            "variants": variants,
        }

    def _candidates(
        self, data: RecommendationInput, spec: FeatureSpec, items: dict[int, Item]
    ) -> list[tuple[int, ...]]:
        popularity = {
            item: i for i, item in enumerate(spec.champion_items.get(data.champion.id, []))
        }
        cores = [list(build) for build in spec.champion_builds.get(data.champion.id, [])]
        rules = (
            self.fallback.recommend(data)
            if isinstance(self.fallback, RuleBasedRecommender)
            else None
        )
        for variant in (rules or {}).get("variants", []):
            cores.append([i["id"] for i in variant["items"] if i["id"] in items][:3])

        unique: dict[frozenset[int], tuple[int, ...]] = {}
        for core in cores:
            if len(core) < 3 or not all(i in items for i in core):
                continue
            ordered = tuple(sorted(core, key=lambda i: popularity.get(i, len(popularity))))
            unique.setdefault(frozenset(ordered), ordered)
        return list(unique.values())


def _defense(build: Sequence[int], items: dict[int, Item]) -> int:
    return sum(len(DEFENSIVE_TAGS.intersection(items[i].tags)) for i in build)


def _choose_variants(
    ranked: list[tuple[tuple[int, ...], float]], items: dict[int, Item]
) -> list[tuple[str, tuple[tuple[int, ...], float]]]:
    """Standardna = najboljša ocena; varna/agresivna = največ/najmanj obrambe med najboljšimi."""
    chosen = [("standard", ranked[0])]
    pool = ranked[1:TOP_CANDIDATES]
    if pool:
        safe = max(pool, key=lambda cs: (_defense(cs[0], items), cs[1]))
        chosen.append(("safe", safe))
        rest = [cs for cs in pool if cs is not safe]
        if rest:
            aggressive = min(rest, key=lambda cs: (_defense(cs[0], items), -cs[1]))
            chosen.append(("aggressive", aggressive))
    order = [key for key, _ in VARIANTS]
    return sorted(chosen, key=lambda kc: order.index(kc[0]))


class _Explainer:
    """Razlogi iz SHAP prispevkov predmetov in vpliva sestave nanje."""

    def __init__(
        self,
        ranker: LoadedRanker,
        champion: Champion,
        position: str,
        comp: dict[str, float],
        data: RecommendationInput,
    ):
        self.ranker = ranker
        self.champion = champion
        self.position = position
        self.comp = comp
        self.data = data

    def reasons(self, build: tuple[int, ...]) -> list[tuple[int, str]]:
        spec = self.ranker.spec
        # Vrstica z dejansko sestavo + po ena vrstica za vsako lastnost sestave na povprečju.
        rows = [spec.encode(self.champion.id, self.position, self.comp, build)]
        for name in COMP_FEATURES:
            neutral = dict(self.comp)
            neutral[name] = spec.comp_mean.get(name, self.comp[name])
            rows.append(spec.encode(self.champion.id, self.position, neutral, build))
        contributions = self.ranker.booster.predict(np.vstack(rows), pred_contrib=True)
        actual = contributions[0]
        probability = 1 / (1 + math.exp(-float(actual.sum())))
        columns = spec.columns

        result = []
        for item_id in build:
            column = columns.index(f"item_{item_id}")
            shap = float(actual[column])
            influence = {
                name: shap - float(contributions[i + 1][column])
                for i, name in enumerate(COMP_FEATURES)
            }
            feature = max(influence, key=lambda name: (influence[name], name))
            points = shap * probability * (1 - probability) * 100
            result.append((item_id, self._reason(feature, influence[feature] > 0, points)))
        return result

    def _reason(self, feature: str, helps: bool, points: float) -> str:
        """En stavek: "priporoča" samo, če predmet pomaga in to pomoč poveča sestava."""
        effect = "0,0" if abs(points) < MIN_SHOWN_POINTS else f"{points:+.1f}".replace(".", ",")
        prop = self._property(feature)
        if helps and points >= MIN_SHOWN_POINTS:
            return (
                f"Model ga priporoča zaradi sestave nasprotnikov: {prop} "
                f"(vpliv na oceno {effect} %)."
            )
        return (
            f"Pogost predmet tega šampiona; tudi {prop} nanj skoraj ne vpliva "
            f"(vpliv na oceno {effect} %)."
        )

    def _property(self, feature: str) -> str:
        """Konkretna lastnost sestave, npr. "zdravljenje (Soraka)" ali "60 % fizične škode"."""
        if feature == "enemy_physical":
            shares = self.data.enemy_comp.get("damage", {})
            if self.comp[feature] >= self.ranker.spec.comp_mean.get(feature, 0.5):
                return f"{shares.get('physical', 50)} % fizične škode"
            return f"{shares.get('magic', 50)} % magične škode"
        attribute = feature.removeprefix("enemy_")
        noun, of = COMP_PHRASES[feature]
        if self.comp[feature] >= self.ranker.spec.comp_mean.get(feature, 0.0):
            return f"{noun} ({self._names(attribute)})"
        total = round(self.comp[feature])
        return f"malo {of} ({total} od {RATING_SUM_MAX})"

    def _names(self, attribute: str) -> str:
        enemies = sorted(self.data.enemy_champions, key=lambda c: (-getattr(c, attribute), c.name))
        strong = [c.name for c in enemies if getattr(c, attribute) >= CONTRIBUTOR_MIN_RATING]
        return ", ".join((strong or [enemies[0].name])[:MAX_NAMED_CHAMPIONS])
