"""Priporočilo builda z modelom LightGBM in rezerva s pravili (US-04, #20)."""

import itertools
import re

import pytest

from app.analysis.enemy_comp import build_enemy_comp
from app.ml.build_ranker import LoadedRanker, train_build_ranker
from app.models.champion import Champion, DamageProfile
from app.models.item import Item
from app.recommend.base import MODEL_LABEL, RULES_LABEL, RecommendationInput
from app.recommend.model import ModelRecommender
from tests.ml_synthetic import ANTI_HEAL, synthetic_rows

P, M = DamageProfile.PHYSICAL, DamageProfile.MAGIC


def champ(champion_id, name, profile=P, classes=("Fighter",), **ratings):
    values = dict.fromkeys(("cc", "healing", "engage", "burst", "tank", "poke"), 0)
    values.update(ratings)
    return Champion(
        id=champion_id,
        slug=name,
        name=name,
        damage_profile=profile,
        classes=list(classes),
        **values,
    )


ITEMS = [
    Item(id=101, name="Chempunk", cost=3000, tags=["anti_heal", "damage"], completed=True),
    Item(id=102, name="Cleaver", cost=3000, tags=["armor_pen", "damage", "health"], completed=True),
    Item(id=103, name="Trinity", cost=3300, tags=["damage", "attack_speed"], completed=True),
    Item(id=104, name="Death's Dance", cost=3300, tags=["armor", "damage"], completed=True),
    Item(id=105, name="Sterak", cost=3200, tags=["damage", "health"], completed=True),
    Item(id=106, name="Eclipse", cost=2900, tags=["damage"], completed=True),
]
ME = champ(1, "Darius")
HEALERS = [
    champ(11, "Soraka", M, ["Support"], healing=3),
    champ(12, "Aatrox", P, healing=3),
    champ(13, "Vladimir", M, ["Mage"], healing=3),
    champ(14, "Lux", M, ["Mage"]),
    champ(15, "Jinx", P, ["Marksman"]),
]


@pytest.fixture(scope="module")
def ranker():
    trained = train_build_ranker(synthetic_rows(), patch="16.22")
    return LoadedRanker(model_id=7, booster=trained.booster, spec=trained.spec)


def recommend(ranker, champion=ME, enemies=HEALERS):
    data = RecommendationInput(
        champion=champion,
        enemy_comp=build_enemy_comp(enemies),
        items=ITEMS,
        enemy_champions=enemies,
    )
    return ModelRecommender(ranker).recommend(data)


def test_priporocilo_modela_je_sledljivo_do_verzije(ranker):
    result = recommend(ranker)

    assert (result["source"], result["label"], result["model_id"]) == ("model", MODEL_LABEL, 7)


def test_variante_modela_so_razlicne_in_popolne(ranker):
    variants = recommend(ranker)["variants"]

    assert 2 <= len(variants) <= 3
    assert variants[0]["key"] == "standard"
    for first, second in itertools.combinations(variants, 2):
        assert {i["id"] for i in first["items"]} != {i["id"] for i in second["items"]}
    for variant in variants:
        assert len(variant["items"]) >= 3
        assert variant["runes"]["keystone"]
        assert len(variant["skill_order"]["levels"]) == 18


def test_razlog_za_predmet_omenja_lastnost_sestave(ranker):
    concrete = re.compile(r"\d+ %|\d+ od 15|" + "|".join(c.name for c in HEALERS))

    for variant in recommend(ranker)["variants"]:
        for item in variant["items"]:
            assert item["reason"].endswith(".") and item["reason"].count(".") == 1
            assert concrete.search(item["reason"]), item["reason"]


def test_model_proti_zdravljenju_izbere_anti_heal_z_razlogom_iz_shap(ranker):
    standard = recommend(ranker)["variants"][0]

    [anti_heal] = [i for i in standard["items"] if i["id"] == ANTI_HEAL]
    assert "zdravljenju" in anti_heal["reason"]
    assert "Soraka" in anti_heal["reason"]


def test_za_neznanega_sampiona_se_uporabijo_pravila(ranker):
    unknown = champ(99, "Neznan")

    result = recommend(ranker, champion=unknown)

    assert (result["source"], result["label"], result["model_id"]) == ("rules", RULES_LABEL, None)


def test_brez_aktivnega_modela_se_uporabijo_pravila():
    assert recommend(None)["source"] == "rules"
