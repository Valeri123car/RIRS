from dataclasses import replace

from app.ddragon.importer import import_static_data
from app.ddragon.parse import ChampionData, ItemData
from app.models.champion import Champion, DamageProfile
from app.models.item import Item

# Visoki ID-ji, da se testi ne prekrivajo z morebiti že uvoženimi podatki.
RATINGS = {"cc": 1, "healing": 3, "engage": 0, "burst": 1, "tank": 0, "poke": 0}
SORAKA = ChampionData(9016, "TestSoraka", "Soraka", DamageProfile.MAGIC, RATINGS)
REMINDER = ItemData(9033, "Mortal Reminder", 3000, ["anti_heal", "armor_pen"])


def test_prvi_uvoz_ustvari_zapise_z_atributi(db):
    result = import_static_data(db, [SORAKA], [REMINDER])

    assert (result.champions.created, result.items.created) == (1, 1)
    champion = db.get(Champion, 9016)
    assert champion.slug == "TestSoraka"
    assert champion.damage_profile == DamageProfile.MAGIC
    assert (champion.healing, champion.cc) == (3, 1)
    item = db.get(Item, 9033)
    assert (item.name, item.cost, item.tags) == (
        "Mortal Reminder",
        3000,
        ["anti_heal", "armor_pen"],
    )


def test_ponovni_uvoz_istih_podatkov_nic_ne_spremeni(db):
    import_static_data(db, [SORAKA], [REMINDER])

    result = import_static_data(db, [SORAKA], [REMINDER])

    assert result.champions.unchanged == result.items.unchanged == 1
    assert result.champions.created == result.champions.updated == 0


def test_nov_patch_posodobi_ime_in_ceno(db):
    import_static_data(db, [SORAKA], [REMINDER])

    result = import_static_data(
        db, [replace(SORAKA, name="Soraka 2")], [replace(REMINDER, cost=3100)]
    )

    assert (result.champions.updated, result.items.updated) == (1, 1)
    assert db.get(Champion, 9016).name == "Soraka 2"
    assert db.get(Item, 9033).cost == 3100


def test_uvoz_ne_povozi_rocno_urejenih_ocen_in_oznak(db):
    import_static_data(db, [SORAKA], [REMINDER])
    db.get(Champion, 9016).healing = 2
    db.get(Item, 9033).tags = ["anti_heal"]
    db.flush()

    result = import_static_data(db, [SORAKA], [REMINDER])

    assert result.champions.unchanged == result.items.unchanged == 1
    assert db.get(Champion, 9016).healing == 2
    assert db.get(Item, 9033).tags == ["anti_heal"]
