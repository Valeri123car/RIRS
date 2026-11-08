"""Profil nasprotne sestave (US-03)."""

from app.analysis.enemy_comp import MAX_THREATS, build_enemy_comp
from app.models.champion import Champion, DamageProfile

P, M, X = DamageProfile.PHYSICAL, DamageProfile.MAGIC, DamageProfile.MIXED


def champ(name, profile=X, **ratings):
    values = dict.fromkeys(("cc", "healing", "engage", "burst", "tank", "poke"), 0)
    values.update(ratings)
    return Champion(id=hash(name) % 10_000, slug=name, name=name, damage_profile=profile, **values)


TEAM = [
    champ("Aatrox", P, healing=3, burst=1, tank=1),
    champ("Sejuani", X, cc=3, engage=3, tank=3),
    champ("Syndra", M, burst=3, poke=2, cc=1),
    champ("Caitlyn", P, poke=2),
    champ("Soraka", M, healing=3, cc=1),
]


def test_delez_skode_je_skupaj_100():
    damage = build_enemy_comp(TEAM)["damage"]

    # 2 fizična + 2 magična + 1 mešan = 50/50
    assert damage == {"physical": 50, "magic": 50}


def test_delez_skode_zaokrozen_na_cela_stevila():
    damage = build_enemy_comp([champ("A", P), champ("B", P), champ("C", M)])["damage"]

    assert damage == {"physical": 67, "magic": 33}
    assert damage["physical"] + damage["magic"] == 100


def test_grozjne_razvrscene_po_moci_s_povzrocitelji():
    threats = build_enemy_comp(TEAM)["threats"]

    scores = [t["score"] for t in threats]
    assert scores == sorted(scores, reverse=True)
    healing = next(t for t in threats if t["key"] == "healing")
    assert healing["label"] == "Zdravljenje"
    assert healing["champions"] == ["Aatrox", "Soraka"]
    assert healing["score"] == 6
    assert healing["level"] == "high"


def test_najvec_5_grozenj_in_samo_tiste_s_povzrocitelji():
    strong = [champ(f"S{i}", cc=3, healing=3, engage=3, burst=3, tank=3, poke=3) for i in range(5)]

    assert len(build_enemy_comp(strong)["threats"]) == MAX_THREATS
    assert build_enemy_comp([champ("Nihce", P, burst=1)])["threats"] == []


def test_sampion_z_nizko_oceno_ni_med_povzrocitelji():
    threats = build_enemy_comp(TEAM)["threats"]

    cc = next(t for t in threats if t["key"] == "cc")
    assert cc["champions"] == ["Sejuani"]  # Syndra in Soraka imata CC 1


def test_manjkajoci_sampioni_so_zabelezeni():
    comp = build_enemy_comp(TEAM[:3], missing=2)

    assert (comp["champion_count"], comp["missing_champions"]) == (3, 2)


def test_brez_znanih_sampionov():
    comp = build_enemy_comp([], missing=5)

    assert comp["damage"] == {"physical": 50, "magic": 50}
    assert comp["threats"] == []
