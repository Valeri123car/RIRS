"""Priporočilo iz pravih buildov šampiona (#82): Pyke ne sme dobiti enchanter predmetov."""

import pytest

from app.analysis.enemy_comp import build_enemy_comp
from app.recommend.base import RecommendationInput
from app.recommend.champion_stats import BuildStats
from app.recommend.rules import MIN_PICK_RATE, RuleBasedRecommender
from tests.test_rules_recommender import HEALERS, ITEMS, champ

PYKE = champ("Pyke", classes=["Support", "Assassin"])
SUPPORT_ITEMS = {3107, 6617, 3190}  # Redemption, Moonstone Renewer, Locket
# Pykeovi pravi nakupi: Black Cleaver, Death's Dance, Lord Dominik's, Infinity Edge;
# enchanter predmeti so redki (pod pragom).
STATS = BuildStats(
    games=100,
    position="UTILITY",
    items={
        3071: (70, 36),
        6333: (50, 26),
        3036: (40, 20),
        3031: (30, 15),
        3107: (2, 1),
        6617: (1, 0),
        3190: (1, 0),
    },
)


def recommend(stats, enemies=HEALERS):
    data = RecommendationInput(
        champion=PYKE,
        enemy_comp=build_enemy_comp(enemies),
        items=ITEMS,
        build_stats=stats,
    )
    return RuleBasedRecommender().recommend(data)


def test_support_s_smrtonosnim_buildom_ne_dobi_enchanter_predmetov():
    result = recommend(STATS)

    for variant in result["variants"]:
        ids = {i["id"] for i in variant["items"]}
        assert not ids & SUPPORT_ITEMS


def test_vsi_predlagani_predmeti_so_med_pogostimi_nakupi_sampiona():
    result = recommend(STATS)

    for variant in result["variants"]:
        for entry in variant["items"]:
            assert STATS.pick_rate(entry["id"]) >= MIN_PICK_RATE


def test_najpogostejsi_predmet_je_v_standardni_varianti():
    standard = recommend(STATS)["variants"][0]

    assert 3071 in {i["id"] for i in standard["items"]}


def test_rune_in_sposobnosti_izhajajo_iz_builda_ne_iz_razreda_support():
    variant = recommend(STATS)["variants"][0]

    assert variant["runes"]["keystone"] != "Summon Aery"
    assert variant["skill_order"]["priority"] != ["E", "Q", "W"]


def test_razlog_za_pogost_predmet_navede_pogostost_in_zmage():
    reasons = [i["reason"] for v in recommend(STATS, enemies=[])["variants"] for i in v["items"]]

    assert any("Pogost predmet tega šampiona" in r and "% iger" in r for r in reasons)


def test_brez_statistike_ostane_rezerva_po_oznakah():
    # Brez dovolj iger (build_stats=None) se uporabijo oznake predmetov kot prej.
    result = recommend(None)

    assert result["source"] == "rules"
    assert len(result["variants"]) >= 1


def test_premalo_kandidatov_iz_statistike_pade_na_oznake():
    sparse = BuildStats(games=100, position="UTILITY", items={3071: (60, 30)})

    result = recommend(sparse)

    assert result is not None
    assert "Pogost predmet" not in " ".join(
        i["reason"] for v in result["variants"] for i in v["items"]
    )


@pytest.mark.parametrize("games,pick", [(100, 0.7), (50, 0.4)])
def test_pogostost_je_delez_iger(games, pick):
    stats = BuildStats(games=games, position="TOP", items={1: (int(games * pick), 0)})

    assert stats.pick_rate(1) == pytest.approx(pick)
    assert stats.pick_rate(999) == 0.0
