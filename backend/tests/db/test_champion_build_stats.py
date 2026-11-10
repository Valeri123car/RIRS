from app.models.champion_build_stat import ChampionBuildStat
from app.models.item import Item
from app.models.rune import Rune
from app.recommend.champion_stats import BuildStats, _with_precomputed

CHAMPION = 9777


def test_predizracunani_podatki_se_razresijo_v_imena(db):
    for rune_id, name in ((9801, "Drevo A"), (9802, "Drevo B"), (9803, "Ključna"), (9804, "Mala")):
        db.merge(Rune(id=rune_id, name=name))
    db.merge(Item(id=9901, name="Testni napoj", cost=50, tags=[], completed=False))
    db.add(
        ChampionBuildStat(
            champion_id=CHAMPION,
            position="TOP",
            games=100,
            rune_pages=[
                {
                    "primary_style": 9801,
                    "keystone": 9803,
                    "secondary_style": 9802,
                    "games": 40,
                    "wins": 20,
                    "primary_perks": [9803, 9804, 9804, 9804],
                    "secondary_perks": [9804, 9804],
                    "shards": [5008, 5008, 5011],
                }
            ],
            item_timing={"3071": {"median_s": 840, "n": 30}},
            start_items={"items": [9901], "games": 60, "wins": 31},
        )
    )
    db.flush()

    stats = _with_precomputed(db, CHAMPION, BuildStats(games=100, position="TOP"))

    page = stats.rune_pages[0]
    assert (page["primary_tree"], page["keystone"], page["secondary_tree"]) == (
        "Drevo A",
        "Ključna",
        "Drevo B",
    )
    assert page["shards"] == ["Prilagodljiva moč", "Prilagodljiva moč", "Zdravje"]
    assert stats.item_minutes == {3071: 14.0}
    assert stats.start_items["items"] == [{"id": 9901, "name": "Testni napoj"}]


def test_brez_vrstice_ali_druge_vloge_ostane_statistika_nespremenjena(db):
    base = BuildStats(games=100, position="TOP")

    assert _with_precomputed(db, 9778, base) is base
