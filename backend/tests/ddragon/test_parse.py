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


def test_sampion_ohrani_riotove_razrede_po_vrsti():
    [malphite] = parse_champions(
        {"Malphite": champion("Malphite", "54", tags=("Tank", "Fighter"))}, overrides={}
    )

    assert malphite.classes == ["Tank", "Fighter"]


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


def test_predmet_iz_sestavin_brez_nadgradnje_je_dokoncan():
    [parsed] = parse_items({"3033": item(**{"from": ["3035", "1037"]})})

    assert parsed.completed is True


@pytest.mark.parametrize(
    "raw",
    [
        item("Long Sword", total=350),
        item("Last Whisper", total=1450, **{"from": ["1036"], "into": ["3033"]}),
        item("Berserker's Greaves", tags=("Boots",), **{"from": ["1001"]}),
        item("Elixir of Iron", tags=("Consumable",)),
        item("Bloodsong", total=400, **{"from": ["3867"]}),
    ],
)
def test_sestavine_cevlji_in_potrosni_predmeti_niso_dokoncani(raw):
    [parsed] = parse_items({"3001": raw})

    assert parsed.completed is False


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


STATS = {
    "hp": 650,
    "hpperlevel": 114,
    "mp": 0,
    "mpperlevel": 0,
    "movespeed": 345,
    "armor": 38,
    "armorperlevel": 4.8,
    "spellblock": 32,
    "spellblockperlevel": 2.05,
    "attackrange": 175,
    "hpregen": 3,
    "hpregenperlevel": 0.5,
    "attackdamage": 60,
    "attackdamageperlevel": 5,
    "attackspeedperlevel": 2.5,
    "attackspeed": 0.651,
}


def spell(spell_id, name, description, cooldown=(10, 9, 8, 7, 6)):
    return {"id": spell_id, "name": name, "description": description, "cooldown": list(cooldown)}


def test_sampion_dobi_osnovne_statistike_za_izracun_po_levelu():
    raw = champion() | {"stats": STATS}

    [aatrox] = parse_champions({"Aatrox": raw}, overrides={})

    assert aatrox.stats["hp"] == 650 and aatrox.stats["hpperlevel"] == 114
    assert aatrox.stats["attackspeed"] == 0.651
    assert "movespeed" in aatrox.stats and "mp" not in aatrox.stats


def test_sposobnosti_dobijo_tipko_ime_opis_brez_html_in_cas_obnove():
    raw = champion() | {
        "spells": [
            spell("AatroxQ", "The Darkin Blade", "Aatrox <status>Knocks Up</status> enemies."),
            spell("AatroxW", "Infernal Chains", "Pulls enemies.<br>Slows them."),
            spell("AatroxE", "Umbral Dash", "Dashes."),
            spell("AatroxR", "World Ender", "Transforms.", cooldown=(120, 100, 80)),
        ]
    }

    [aatrox] = parse_champions({"Aatrox": raw}, overrides={})

    assert [s["key"] for s in aatrox.spells] == ["Q", "W", "E", "R"]
    assert aatrox.spells[0] == {
        "key": "Q",
        "name": "The Darkin Blade",
        "description": "Aatrox Knocks Up enemies.",
        "cooldown": [10, 9, 8, 7, 6],
    }
    assert aatrox.spells[1]["description"] == "Pulls enemies. Slows them."
    assert aatrox.spells[3]["cooldown"] == [120, 100, 80]


def test_sampion_brez_statistik_in_sposobnosti_ima_prazne_vrednosti():
    [aatrox] = parse_champions({"Aatrox": champion()}, overrides={})

    assert aatrox.stats == {} and aatrox.spells == []
