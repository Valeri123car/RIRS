import pytest

from app.matchup.abilities import dangerous_abilities
from app.matchup.card import build_matchup_card
from app.matchup.power import LEVELS, phase_strength_from_counts, power_curve, stat_at
from app.matchup.roles import POSITIONS, SMITE_ID, assign_roles
from app.models.champion import Champion, DamageProfile

STATS = {
    "hp": 600,
    "hpperlevel": 100,
    "armor": 30,
    "armorperlevel": 4.5,
    "spellblock": 30,
    "spellblockperlevel": 1.5,
    "attackdamage": 60,
    "attackdamageperlevel": 3,
    "attackspeed": 0.65,
    "attackspeedperlevel": 2.5,
    "attackrange": 175,
}


def spell(key, name, description, cooldown=(10, 9, 8, 7, 6)):
    return {"key": key, "name": name, "description": description, "cooldown": list(cooldown)}


SPELLS = [
    spell("Q", "Strike", "Deals physical damage to an enemy."),
    spell("W", "Guard", "Gains a shield."),
    spell("E", "Leap", "Dashes to a target and Stuns it for 1 second."),
    spell("R", "Finale", "Knocks Up all nearby enemies.", cooldown=(120, 100, 80)),
]


def champ(cid=1, name="A", classes=("Fighter",), stats=None, spells=None, **ratings):
    return Champion(
        id=cid,
        slug=name,
        name=name,
        classes=list(classes),
        damage_profile=ratings.pop("damage_profile", DamageProfile.PHYSICAL),
        stats=dict(STATS if stats is None else stats),
        spells=list(SPELLS if spells is None else spells),
        cc=ratings.get("cc", 1),
        healing=ratings.get("healing", 0),
        engage=ratings.get("engage", 1),
        burst=ratings.get("burst", 1),
        tank=ratings.get("tank", 1),
        poke=ratings.get("poke", 0),
    )


# --- moč po levelu --------------------------------------------------------------------------


def test_statistika_po_riotovi_formuli_rasti():
    assert stat_at(600, 100, 1) == 600
    assert stat_at(600, 100, 18) == pytest.approx(600 + 100 * 17 * (0.7025 + 0.0175 * 17))


def test_enaka_sampiona_sta_izenacena_na_vseh_levelih():
    curve = power_curve(champ(1), champ(2))

    assert [p["level"] for p in curve] == list(LEVELS)
    assert all(p["state"] == "even" and p["you"] == pytest.approx(50) for p in curve)


def test_sampion_z_vecjo_rastjo_je_mocnejsi_pozno():
    scaler = champ(1, stats=STATS | {"hpperlevel": 160, "attackdamageperlevel": 6})
    early = champ(2, stats=STATS | {"hp": 680, "attackdamage": 68, "hpperlevel": 70})

    curve = power_curve(scaler, early)

    assert curve[0]["state"] == "disadvantage"
    assert curve[-1]["state"] == "advantage"
    assert curve[-1]["you"] + curve[-1]["enemy"] == pytest.approx(100)


def test_podatki_o_fazah_igre_premaknejo_moc():
    phases = {1: {"early": 0.56, "late": 0.44}, 2: {"early": 0.5, "late": 0.5}}

    curve = power_curve(champ(1), champ(2), phases)

    assert curve[0]["state"] == "advantage"
    assert curve[-1]["state"] == "disadvantage"


def test_faza_igre_skrci_redke_sampione_proti_polovici():
    phases = phase_strength_from_counts({7: (6, 2, 7, 7), 8: (300, 100, 300, 200)})

    assert 0.5 < phases[7]["late"] < 0.56  # 7 od 7 dolgih iger, a malo podatkov
    assert phases[8]["early"] < 0.4 and phases[8]["late"] > 0.6


def test_brez_statistik_ni_krivulje():
    assert power_curve(champ(1, stats={}), champ(2)) == []


# --- nevarne sposobnosti ----------------------------------------------------------------------


def test_nevarne_sposobnosti_so_cc_in_skoki_z_razlogom():
    result = dangerous_abilities(champ())

    assert len(result) >= 2
    keys = [a["key"] for a in result]
    assert "E" in keys and "R" in keys and "W" not in keys
    leap = next(a for a in result if a["key"] == "E")
    assert "omami" in leap["reason"] and "skok" in leap["reason"]
    assert leap["cooldown"] == 10


def test_ce_ni_cc_vzame_vsaj_dve_sposobnosti_z_r():
    plain = [spell(k, k, "Deals damage.") for k in "QWER"]

    result = dangerous_abilities(champ(spells=plain))

    assert len(result) == 2 and result[0]["key"] == "R"


# --- linije ----------------------------------------------------------------------------------


def _dist(*rows):
    return {cid: dict(zip(POSITIONS, probs, strict=True)) for cid, probs in rows}


DIST = _dist(
    (1, (0.9, 0.0, 0.1, 0.0, 0.0)),  # top
    (2, (0.1, 0.6, 0.3, 0.0, 0.0)),  # jungle/mid
    (3, (0.0, 0.0, 0.9, 0.1, 0.0)),  # mid
    (4, (0.0, 0.0, 0.0, 0.95, 0.05)),  # bot
    (5, (0.0, 0.0, 0.1, 0.0, 0.9)),  # support
)


def test_vloge_po_porazdelitvi_in_smite_pomeni_jungle():
    team = [(1, False), (2, True), (3, False), (4, False), (5, False)]

    roles = assign_roles(team, DIST)

    assert {cid: r["role"] for cid, r in roles.items()} == {
        1: "TOP",
        2: "JUNGLE",
        3: "MIDDLE",
        4: "BOTTOM",
        5: "UTILITY",
    }
    assert roles[3]["confidence"] > 0.8


def test_neznan_sampion_brez_podatkov_ima_nizko_zaupanje():
    team = [(1, False), (2, True), (98, False), (99, False), (5, False)]

    roles = assign_roles(team, DIST)

    assert roles[98]["confidence"] < 0.6 and roles[2]["role"] == "JUNGLE"


# --- kartica ---------------------------------------------------------------------------------


def _participants(enemy_ids=(11, 12, 13, 14, 15)):
    ours = [
        (1, 100, True, 4),
        (2, 100, False, SMITE_ID),
        (3, 100, False, 4),
        (4, 100, False, 4),
        (5, 100, False, 4),
    ]
    theirs = [(e, 200, False, SMITE_ID if i == 1 else 4) for i, e in enumerate(enemy_ids)]
    return [
        {"champion_id": c, "team_id": t, "is_target": target, "spell1_id": 14, "spell2_id": s}
        for c, t, target, s in ours + theirs
    ]


def _champions():
    ours = {i: champ(i, f"N{i}") for i in range(1, 6)}
    theirs = {10 + i: champ(10 + i, f"E{i}") for i in range(1, 6)}
    return ours | theirs


def test_kartica_doloci_nasprotnika_v_isti_liniji():
    dist = DIST | {10 + k: v for k, v in DIST.items()}

    card = build_matchup_card(_participants(), _champions(), dist)

    assert card["role"] == "TOP"
    assert card["opponent"] == {"id": 11, "name": "E1"} and card["opponent_source"] == "auto"
    assert len(card["candidates"]) == 5
    assert len(card["levels"]) == 18
    assert len(card["dangerous_abilities"]) >= 2
    assert 2 <= len(card["tips"]) <= 3


def test_kartica_brez_zanesljivega_nasprotnika_ponudi_izbiro():
    card = build_matchup_card(_participants(), _champions(), DIST)  # nasprotniki brez podatkov

    assert card["opponent"] is None
    assert card["levels"] == [] and card["tips"] == []
    assert [c["id"] for c in card["candidates"]] == [11, 12, 13, 14, 15]


def test_kartica_z_izbranim_nasprotnikom():
    card = build_matchup_card(_participants(), _champions(), DIST, opponent_id=13)

    assert card["opponent"] == {"id": 13, "name": "E3"} and card["opponent_source"] == "choice"
    assert len(card["levels"]) == 18


def test_izbran_nasprotnik_mora_biti_v_nasprotni_ekipi():
    with pytest.raises(ValueError):
        build_matchup_card(_participants(), _champions(), DIST, opponent_id=2)
