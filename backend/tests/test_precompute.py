"""Predizračun pravih buildov (#101): rune, čas nakupa in začetni predmeti iz tekem."""

from app.recommend.base import RecommendationInput
from app.recommend.champion_stats import BuildStats
from app.recommend.precompute import (
    build_item_timing,
    build_rune_pages,
    build_start_items,
    parse_perks,
)
from app.recommend.rules import RuleBasedRecommender
from tests.test_rules_from_builds import PYKE, STATS
from tests.test_rules_recommender import HEALERS, ITEMS


def perks(keystone=8010, secondary=8300, sub=(8304, 8347)):
    return {
        "styles": [
            {
                "description": "primaryStyle",
                "style": 8000,
                "selections": [{"perk": p} for p in (keystone, 9111, 9104, 8299)],
            },
            {
                "description": "subStyle",
                "style": secondary,
                "selections": [{"perk": p} for p in sub],
            },
        ],
        "statPerks": {"offense": 5008, "flex": 5008, "defense": 5011},
    }


def test_parse_perks_izlusci_stran_run():
    page = parse_perks(perks())

    assert page == {
        "primary_style": 8000,
        "secondary_style": 8300,
        "primary": [8010, 9111, 9104, 8299],
        "secondary": [8304, 8347],
        "shards": [5008, 5008, 5011],
    }


def test_parse_perks_zavrne_nepopolne_podatke():
    assert parse_perks(None) is None
    assert parse_perks({"styles": []}) is None
    assert parse_perks({"styles": [{"description": "primaryStyle", "selections": []}]}) is None


def test_strani_run_so_urejene_po_pogostosti_in_redke_izpuscene():
    rows = [(True, parse_perks(perks()))] * 30 + [(False, parse_perks(perks(keystone=8005)))] * 25
    rows += [(True, parse_perks(perks(keystone=8021)))] * 2  # pod pragom iger

    pages = build_rune_pages(rows, games=len(rows))

    assert [p["keystone"] for p in pages] == [8010, 8005]
    assert (pages[0]["games"], pages[0]["wins"]) == (30, 30)
    assert pages[0]["primary_perks"] == [8010, 9111, 9104, 8299]
    assert pages[0]["secondary_perks"] == [8304, 8347]


def test_cas_nakupa_je_mediana_prvega_nakupa_samo_za_dokoncane_predmete_ob_koncu():
    players = [([3071, 3031], [[3071, 600 + i * 10], [3071, 900], [1001, 100]]) for i in range(10)]

    timing = build_item_timing(players, completed={3071, 3031})

    assert set(timing) == {"3071"}  # 3031 ni bil kupljen; 1001 ni dokončan
    assert timing["3071"]["median_s"] == 645
    assert timing["3071"]["n"] == 10


def test_premalo_vzorcev_za_cas_nakupa():
    assert build_item_timing([([3071], [[3071, 600]])], completed={3071}) == {}


def test_zacetni_predmeti_so_najpogostejsi_nakupi_v_prvih_sekundah():
    players = [(True, [[2003, 6], [3364, 7], [3071, 700]])] * 3 + [(False, [[1055, 5]])]

    start = build_start_items(players)

    assert start == {"items": [2003, 3364], "games": 3, "wins": 3}


def test_priporocilo_uporabi_rune_cas_nakupa_in_zacetne_predmete():
    page = {
        "primary_tree": "Domination",
        "keystone": "Hail of Blades",
        "secondary_tree": "Resolve",
        "primary_perks": ["Hail of Blades", "Sudden Impact", "Deep Ward", "Relentless Hunter"],
        "secondary_perks": ["Unflinching", "Bone Plating"],
        "shards": ["Prilagodljiva moč", "Prilagodljiva moč", "Zdravje"],
        "games": 40,
        "wins": 18,
    }
    stats = BuildStats(
        games=STATS.games,
        position=STATS.position,
        items=STATS.items,
        rune_pages=(page,),
        item_minutes={3071: 14.0, 6333: 17.0, 3036: 21.0, 3031: 11.0},
        start_items={"items": [{"id": 2003, "name": "Health Potion"}], "games": 50, "wins": 25},
    )
    data = RecommendationInput(champion=PYKE, enemy_comp=_comp(), items=ITEMS, build_stats=stats)

    result = RuleBasedRecommender().recommend(data)

    for variant in result["variants"]:
        runes = variant["runes"]
        assert runes["keystone"] == "Hail of Blades"
        assert (runes["pick_rate"], runes["win_rate"]) == (40, 45)
        assert variant["start_items"]["items"][0]["name"] == "Health Potion"
        minutes = [i.get("typical_minute") for i in variant["items"] if "typical_minute" in i]
        assert minutes == sorted(minutes) and len(minutes) >= 3


def test_brez_predizracuna_ostanejo_rune_iz_profila_razreda():
    data = RecommendationInput(champion=PYKE, enemy_comp=_comp(), items=ITEMS, build_stats=STATS)

    for variant in RuleBasedRecommender().recommend(data)["variants"]:
        assert "primary_perks" not in variant["runes"]
        assert variant["runes"]["keystone"]
        assert variant["start_items"] is None


def _comp():
    from app.analysis.enemy_comp import build_enemy_comp

    return build_enemy_comp(HEALERS)
