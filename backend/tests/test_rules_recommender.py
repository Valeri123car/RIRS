"""Priporočilo builda na podlagi pravil (US-04, #19)."""

import itertools
import re

import pytest

from app.analysis.enemy_comp import build_enemy_comp
from app.models.champion import Champion, DamageProfile
from app.models.item import Item
from app.recommend.base import RULES_LABEL, RecommendationInput
from app.recommend.rules import RuleBasedRecommender

P, M, X = DamageProfile.PHYSICAL, DamageProfile.MAGIC, DamageProfile.MIXED


def champ(name, profile=X, classes=(), **ratings):
    values = dict.fromkeys(("cc", "healing", "engage", "burst", "tank", "poke"), 0)
    values.update(ratings)
    return Champion(
        id=hash(name) % 10_000,
        slug=name,
        name=name,
        damage_profile=profile,
        classes=list(classes),
        **values,
    )


def item(item_id, name, *tags, completed=True, cost=3000):
    return Item(id=item_id, name=name, cost=cost, tags=list(tags), completed=completed)


# Izsek dokončanih predmetov iz patcha 16.22.1 (oznake kot jih da uvoz Data Dragon).
ITEMS = [
    item(3031, "Infinity Edge", "critical_strike", "damage"),
    item(3089, "Rabadon's Deathcap", "spell_damage"),
    item(3072, "Bloodthirster", "damage", "life_steal"),
    item(3036, "Lord Dominik's Regards", "armor_pen", "critical_strike", "damage"),
    item(3033, "Mortal Reminder", "anti_heal", "armor_pen", "critical_strike", "damage"),
    item(3046, "Phantom Dancer", "attack_speed", "critical_strike", "nonboots_movement"),
    item(3032, "Yun Tal Wildarrows", "attack_speed", "critical_strike", "damage"),
    item(6673, "Immortal Shieldbow", "critical_strike", "damage"),
    item(3139, "Mercurial Scimitar", "damage", "life_steal", "spell_block", "tenacity"),
    item(3026, "Guardian Angel", "armor", "damage"),
    item(3157, "Zhonya's Hourglass", "active", "armor", "spell_damage"),
    item(3165, "Morellonomicon", "ability_haste", "anti_heal", "health", "spell_damage"),
    item(3135, "Void Staff", "magic_pen", "spell_damage"),
    item(3102, "Banshee's Veil", "spell_block", "spell_damage"),
    item(6655, "Luden's Echo", "ability_haste", "mana", "spell_damage"),
    item(4645, "Shadowflame", "magic_pen", "spell_damage"),
    item(3071, "Black Cleaver", "ability_haste", "armor_pen", "damage", "health"),
    item(3053, "Sterak's Gage", "damage", "health", "tenacity"),
    item(6333, "Death's Dance", "ability_haste", "armor", "damage"),
    item(3075, "Thornmail", "anti_heal", "armor", "health", cost=2450),
    item(3065, "Spirit Visage", "ability_haste", "health", "health_regen", "spell_block"),
    item(6665, "Jak'Sho, The Protean", "armor", "health", "magic_resist", "spell_block"),
    item(3742, "Dead Man's Plate", "armor", "health", "slow"),
    item(2504, "Kaenic Rookern", "health", "health_regen", "spell_block"),
    item(3083, "Warmog's Armor", "health", "health_regen"),
    item(3107, "Redemption", "ability_haste", "mana_regen", "spell_damage", cost=2300),
    item(
        6617,
        "Moonstone Renewer",
        "ability_haste",
        "health",
        "mana_regen",
        "spell_damage",
        cost=2200,
    ),
    item(
        3190,
        "Locket of the Iron Solari",
        "ability_haste",
        "armor",
        "aura",
        "spell_block",
        cost=2200,
    ),
    item(1037, "Pickaxe", "damage", completed=False, cost=875),
]

HEALERS = [
    champ("Aatrox", P, ["Fighter", "Tank"], healing=3, burst=1, tank=1),
    champ("Soraka", M, ["Support", "Mage"], healing=3, cc=1),
    champ("Sejuani", X, ["Tank", "Fighter"], cc=3, engage=3, tank=3),
    champ("Syndra", M, ["Mage"], burst=3, poke=2, cc=1),
    champ("Caitlyn", P, ["Marksman"], poke=2),
]
MAGES = [
    champ("Syndra", M, ["Mage"], burst=3, poke=2, cc=1),
    champ("Lux", M, ["Mage", "Support"], burst=2, poke=3, cc=2),
    champ("Ahri", M, ["Mage", "Assassin"], burst=3, cc=1),
    champ("Malphite", M, ["Tank", "Fighter"], tank=3, engage=3, cc=2),
    champ("Lillia", M, ["Fighter", "Mage"], cc=2),
]

JINX = champ("Jinx", P, ["Marksman"])
LUX = champ("Lux", M, ["Mage", "Support"])
ORNN = champ("Ornn", X, ["Tank", "Fighter"])


def recommend(champion, enemies=HEALERS, items=ITEMS):
    data = RecommendationInput(champion=champion, enemy_comp=build_enemy_comp(enemies), items=items)
    return RuleBasedRecommender().recommend(data)


@pytest.mark.parametrize("champion", [JINX, LUX, ORNN])
def test_priporocilo_je_oznaceno_kot_na_podlagi_pravil(champion):
    result = recommend(champion)

    assert result["source"] == "rules"
    assert result["label"] == RULES_LABEL == "Priporočilo na podlagi pravil"
    assert result["model_id"] is None


@pytest.mark.parametrize("champion", [JINX, LUX, ORNN])
def test_tri_variante_standardna_varna_agresivna(champion):
    variants = recommend(champion)["variants"]

    assert [v["key"] for v in variants] == ["standard", "safe", "aggressive"]
    assert [v["label"] for v in variants] == ["Standardna", "Varna", "Agresivna"]


@pytest.mark.parametrize("champion", [JINX, LUX, ORNN])
@pytest.mark.parametrize("enemies", [HEALERS, MAGES])
def test_variante_se_razlikujejo_v_vsaj_enem_dokoncanem_predmetu(champion, enemies):
    variants = recommend(champion, enemies)["variants"]

    for first, second in itertools.combinations(variants, 2):
        assert {i["id"] for i in first["items"]} != {i["id"] for i in second["items"]}


@pytest.mark.parametrize("champion", [JINX, LUX, ORNN])
def test_varianta_ima_rune_vsaj_3_dokoncane_predmete_in_sposobnosti(champion):
    completed = {i.id for i in ITEMS if i.completed}

    for variant in recommend(champion)["variants"]:
        runes = variant["runes"]
        assert runes["keystone"] and runes["primary_tree"] and runes["secondary_tree"]
        assert runes["primary_tree"] != runes["secondary_tree"]
        assert len(variant["items"]) >= 3
        assert all(i["id"] in completed for i in variant["items"])
        assert len({i["id"] for i in variant["items"]}) == len(variant["items"])
        levels = variant["skill_order"]["levels"]
        assert len(levels) == 18
        assert [lvl for lvl, skill in enumerate(levels, start=1) if skill == "R"] == [6, 11, 16]
        assert all(levels.count(skill) == 5 for skill in "QWE")


@pytest.mark.parametrize("champion", [JINX, LUX, ORNN])
@pytest.mark.parametrize("enemies", [HEALERS, MAGES])
def test_vsak_predmet_ima_razlog_s_konkretno_lastnostjo_sestave(champion, enemies):
    names = {c.name for c in enemies}
    concrete = re.compile(r"\d+ %|" + "|".join(names))

    for variant in recommend(champion, enemies)["variants"]:
        for chosen in variant["items"]:
            reason = chosen["reason"]
            assert reason.endswith(".") and reason.count(".") == 1, reason
            assert concrete.search(reason), reason


def test_proti_zdravljenju_standardna_varianta_kupi_anti_heal():
    standard = recommend(JINX)["variants"][0]

    [anti_heal] = [i for i in standard["items"] if i["name"] == "Mortal Reminder"]
    assert "Soraka" in anti_heal["reason"] and "Aatrox" in anti_heal["reason"]


def test_fizicni_strelec_ne_dobi_predmetov_z_magijo():
    magic_only = {i.id for i in ITEMS if "spell_damage" in i.tags and "damage" not in i.tags}

    for variant in recommend(JINX, MAGES)["variants"]:
        assert not magic_only & {i["id"] for i in variant["items"]}


def test_varna_varianta_proti_magom_vsebuje_magicni_odpor():
    safe = recommend(JINX, MAGES)["variants"][1]
    resist = {i.id for i in ITEMS if {"spell_block", "magic_resist"} & set(i.tags)}

    chosen = [i for i in safe["items"] if i["id"] in resist]
    assert chosen
    assert "100 % magične" in chosen[0]["reason"]


def test_podporne_predmete_dobi_samo_podpora():
    support_items = {3107, 6617, 3190}

    for variant in recommend(ORNN)["variants"]:
        assert not support_items & {i["id"] for i in variant["items"]}
    soraka = champ("Soraka", M, ["Support", "Mage"])
    standard = recommend(soraka, MAGES)["variants"][0]
    assert support_items & {i["id"] for i in standard["items"]}


def test_brez_dovolj_predmetov_ni_priporocila():
    assert recommend(JINX, items=ITEMS[:2]) is None
