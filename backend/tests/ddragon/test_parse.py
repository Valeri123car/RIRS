import pytest

from app.ddragon.parse import load_overrides, parse_champions, parse_items
from app.models.champion import DamageProfile


def champion(slug="Aatrox", key="266", attack=8, magic=3, tags=("Fighter",)):
    return {
        "id": slug,
        "key": key,
        "name": slug,
        "info": {"attack": attack, "defense": 4, "magic": magic, "difficulty": 4},
        "tags": list(tags),
    }


def item(name="Mortal Reminder", total=3000, description="", tags=(), **extra):
    return {
        "name": name,
        "description": description,
        "gold": {"base": 150, "purchasable": True, "total": total, "sell": 2100},
        "tags": list(tags),
        "maps": {"11": True, "12": True},
        **extra,
    }


def test_sampion_dobi_stevilcni_id_iz_kljuca():
    [aatrox] = parse_champions({"Aatrox": champion()}, overrides={})

    assert (aatrox.id, aatrox.slug, aatrox.name) == (266, "Aatrox", "Aatrox")


@pytest.mark.parametrize(
    ("attack", "magic", "expected"),
    [(8, 3, DamageProfile.PHYSICAL), (2, 9, DamageProfile.MAGIC), (6, 6, DamageProfile.MIXED)],
)
def test_vrsta_skode_iz_razmerja_napad_magija(attack, magic, expected):
    [parsed] = parse_champions({"X": champion("X", attack=attack, magic=magic)}, overrides={})

    assert parsed.damage_profile == expected


def test_glavna_oznaka_tank_da_visjo_oceno_kot_stranska():
    parsed = parse_champions(
        {
            "Malphite": champion("Malphite", "54", tags=("Tank", "Fighter")),
            "Darius": champion("Darius", "122", tags=("Fighter", "Tank")),
        },
        overrides={},
    )
    tank = {c.slug: c.ratings["tank"] for c in parsed}

    assert tank == {"Malphite": 3, "Darius": 2}


def test_atentator_ima_visok_burst():
    [zed] = parse_champions({"Zed": champion("Zed", "238", tags=("Assassin",))}, overrides={})

    assert zed.ratings["burst"] == 3


def test_vse_ocene_so_med_0_in_3():
    tags = ("Tank", "Support", "Mage", "Assassin", "Fighter", "Marksman")
    [parsed] = parse_champions({"X": champion("X", tags=tags)}, overrides={})

    assert set(parsed.ratings) == {"cc", "healing", "engage", "burst", "tank", "poke"}
    assert all(0 <= value <= 3 for value in parsed.ratings.values())


def test_rocni_popravki_prevladajo_nad_hevristiko():
    [soraka] = parse_champions(
        {"Soraka": champion("Soraka", "16", tags=("Support", "Mage"))},
        overrides={"Soraka": {"healing": 3}},
    )

    assert soraka.ratings["healing"] == 3


def test_neveljaven_rocni_popravek_je_zavrnjen():
    with pytest.raises(ValueError, match="Soraka"):
        parse_champions({"Soraka": champion("Soraka", "16")}, overrides={"Soraka": {"healing": 5}})


def test_datoteka_rocnih_popravkov_je_veljavna():
    overrides = load_overrides()
    champions = {slug: champion(slug, str(n)) for n, slug in enumerate(overrides, start=1)}

    parsed = parse_champions(champions)

    assert len(parsed) == len(overrides) > 0


def test_predmet_dobi_ceno_in_oznake_v_snake_case():
    [parsed] = parse_items({"3033": item(tags=("Damage", "ArmorPenetration", "LifeSteal"))})

    assert (parsed.id, parsed.name, parsed.cost) == (3033, "Mortal Reminder", 3000)
    assert parsed.tags == ["armor_pen", "damage", "life_steal"]


def test_grievous_wounds_v_opisu_pomeni_anti_heal():
    description = "<passive>Grievous Wounds</passive> applies <keyword>40% Wounds</keyword>"
    [parsed] = parse_items({"3075": item("Thornmail", description=description)})

    assert "anti_heal" in parsed.tags


@pytest.mark.parametrize(
    ("item_id", "raw"),
    [
        ("3001", item(maps={"11": False, "12": True})),
        ("3002", item(gold={"total": 0, "purchasable": False})),
        ("3003", item(requiredChampion="Kalista")),
        ("3004", item(inStore=False)),
        ("3005", item(hideFromAll=True)),
        ("323075", item("Thornmail")),
    ],
)
def test_predmeti_izven_summoners_rift_so_izpusceni(item_id, raw):
    assert parse_items({item_id: raw}) == []
