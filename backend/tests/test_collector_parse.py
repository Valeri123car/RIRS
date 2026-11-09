import copy
from datetime import UTC, datetime

import pytest

from app.collector.parse import MatchParseError, parse_match, timeline_features
from app.riot.fixture_client import FixtureRiotClient

MATCH_ID = "EUW1_7100000001"


@pytest.fixture
def raw() -> dict:
    return FixtureRiotClient().get_match(MATCH_ID, "euw1")


@pytest.fixture
def timeline() -> dict:
    return FixtureRiotClient().get_match_timeline(MATCH_ID, "euw1")


def test_tekma_se_pretvori_v_vrstice(raw):
    match = parse_match(raw, MATCH_ID)

    assert match.match_id == MATCH_ID
    assert match.platform == "euw1"
    assert match.queue_id == 420
    assert match.patch == "16.22"
    assert match.game_start == datetime.fromtimestamp(raw["info"]["gameStartTimestamp"] / 1000, UTC)
    assert match.winning_team == 100
    assert len(match.participants) == 10
    sara = match.participants[0]
    assert (sara.game_name, sara.tag_line, sara.team_id, sara.win) == ("Sara", "EUW", 100, True)
    assert 0 not in sara.items and sara.items


def test_tekma_z_drugim_id_je_zavrnjena(raw):
    with pytest.raises(MatchParseError):
        parse_match(raw, "EUW1_1")


@pytest.mark.parametrize(
    "pokvari",
    [
        lambda m: m["info"]["participants"].pop(),
        lambda m: m["info"].pop("teams"),
        lambda m: m["info"].update(teams=[{"teamId": 100, "win": False}]),
        lambda m: m["info"].update(gameVersion="neznano"),
        lambda m: m["info"]["participants"][0].update(teamId=300),
        lambda m: m["info"]["participants"][0].update(kills="veliko"),
        lambda m: m["info"]["participants"][1].update(puuid=m["info"]["participants"][0]["puuid"]),
    ],
)
def test_nepopolna_tekma_je_zavrnjena(raw, pokvari):
    broken = copy.deepcopy(raw)
    pokvari(broken)

    with pytest.raises(MatchParseError):
        parse_match(broken, MATCH_ID)


def test_znacilke_iz_casovnice(timeline):
    features = timeline_features(timeline)

    assert len(features) == 10
    puuid = timeline["info"]["participants"][0]["puuid"]
    frame_10 = timeline["info"]["frames"][10]["participantFrames"]["1"]
    frame_15 = timeline["info"]["frames"][15]["participantFrames"]["1"]
    assert features[puuid]["cs_at_10"] == (
        frame_10["minionsKilled"] + frame_10["jungleMinionsKilled"]
    )
    assert features[puuid]["xp_at_10"] == frame_10["xp"]
    assert features[puuid]["gold_at_15"] == frame_15["totalGold"]
    assert all("deaths_before_14" in f for f in features.values())


def test_smrti_pred_14_minuto_stejejo_samo_zgodnje_uboje(timeline):
    victim = timeline["info"]["participants"][3]["puuid"]
    for frame in timeline["info"]["frames"]:
        frame["events"] = []
    timeline["info"]["frames"][5]["events"] = [
        {"type": "CHAMPION_KILL", "timestamp": 4 * 60_000, "victimId": 4, "killerId": 1},
        {"type": "WARD_PLACED", "timestamp": 4 * 60_000, "creatorId": 4},
    ]
    timeline["info"]["frames"][15]["events"] = [
        {"type": "CHAMPION_KILL", "timestamp": 14 * 60_000 + 1, "victimId": 4, "killerId": 1}
    ]

    assert timeline_features(timeline)[victim]["deaths_before_14"] == 1


def test_kratka_tekma_nima_znacilk_po_koncu(timeline):
    timeline["info"]["frames"] = timeline["info"]["frames"][:12]  # konec v 12. minuti

    features = timeline_features(timeline)

    puuid = timeline["info"]["participants"][0]["puuid"]
    assert "cs_at_10" in features[puuid]
    assert "gold_at_15" not in features[puuid]


def test_pokvarjena_casovnica_vrne_prazne_znacilke():
    assert timeline_features({"info": {"frames": "ne"}}) == {}


# --- stanje ob 15. minuti in nakupi (timeline_v 2) ---------------------------------------


def _min(minutes: float) -> int:
    return int(minutes * 60_000)


def _puuid(timeline: dict, participant_id: int) -> str:
    return timeline["info"]["participants"][participant_id - 1]["puuid"]


@pytest.fixture
def events_timeline(timeline) -> dict:
    """Časovnica z znanimi dogodki: ekipa 100 = igralci 1–5, ekipa 200 = 6–10."""
    for frame in timeline["info"]["frames"]:
        frame["events"] = []
    events = [
        {"type": "ITEM_PURCHASED", "timestamp": 5_000, "participantId": 1, "itemId": 1055},
        {"type": "ITEM_PURCHASED", "timestamp": 5_000, "participantId": 0, "itemId": 3865},
        {
            "type": "CHAMPION_KILL",
            "timestamp": _min(3),
            "killerId": 1,
            "victimId": 6,
            "assistingParticipantIds": [2],
            "shutdownBounty": 0,
        },
        {"type": "ITEM_PURCHASED", "timestamp": _min(5), "participantId": 1, "itemId": 1001},
        {
            "type": "ITEM_UNDO",
            "timestamp": _min(5) + 2_000,
            "participantId": 1,
            "beforeId": 1001,
            "afterId": 0,
            "goldGain": 300,
        },
        {
            "type": "ELITE_MONSTER_KILL",
            "timestamp": _min(6),
            "killerTeamId": 100,
            "monsterType": "DRAGON",
        },
        {
            "type": "ELITE_MONSTER_KILL",
            "timestamp": _min(7),
            "killerTeamId": 100,
            "monsterType": "HORDE",
        },
        {
            "type": "ELITE_MONSTER_KILL",
            "timestamp": _min(8),
            "killerTeamId": 200,
            "monsterType": "HORDE",
        },
        {"type": "TURRET_PLATE_DESTROYED", "timestamp": _min(9), "teamId": 200, "killerId": 1},
        {"type": "TURRET_PLATE_DESTROYED", "timestamp": _min(9.5), "teamId": 200, "killerId": 2},
        {
            "type": "CHAMPION_KILL",
            "timestamp": _min(10),
            "killerId": 7,
            "victimId": 1,
            "assistingParticipantIds": [],
            "shutdownBounty": 300,
        },
        {
            "type": "BUILDING_KILL",
            "timestamp": _min(12),
            "teamId": 200,
            "killerId": 1,
            "buildingType": "TOWER_BUILDING",
        },
        {
            "type": "ELITE_MONSTER_KILL",
            "timestamp": _min(14.5),
            "killerTeamId": 200,
            "monsterType": "RIFTHERALD",
        },
        # po 15. minuti: ne šteje v stanje, nakup pa ostane v seznamu nakupov
        {
            "type": "CHAMPION_KILL",
            "timestamp": _min(15.5),
            "killerId": 6,
            "victimId": 2,
            "assistingParticipantIds": [],
            "shutdownBounty": 0,
        },
        {
            "type": "ELITE_MONSTER_KILL",
            "timestamp": _min(16),
            "killerTeamId": 200,
            "monsterType": "DRAGON",
        },
        {"type": "ITEM_PURCHASED", "timestamp": _min(20), "participantId": 1, "itemId": 3006},
    ]
    for event in events:
        index = min(event["timestamp"] // 60_000 + 1, len(timeline["info"]["frames"]) - 1)
        timeline["info"]["frames"][index]["events"].append(event)
    return timeline


def test_casovnica_dobi_razlicico_znacilk(timeline):
    features = timeline_features(timeline)

    assert all(f["timeline_v"] == 3 for f in features.values())


def test_stanje_igralca_ob_15_minuti(timeline):
    state = timeline["info"]["frames"][15]["participantFrames"]["1"]
    state["damageStats"] = {"totalDamageDoneToChampions": 4200, "totalDamageTaken": 5100}

    features = timeline_features(timeline)[_puuid(timeline, 1)]

    assert features["gold_15"] == state["totalGold"]
    assert features["xp_15"] == state["xp"]
    assert features["level_15"] == state["level"]
    assert features["cs_15"] == state["minionsKilled"] + state["jungleMinionsKilled"]
    assert features["dmg_champ_15"] == 4200
    assert features["dmg_taken_15"] == 5100


def test_prednost_ekipe_v_zlatu_in_xp_ob_15(timeline):
    frame = timeline["info"]["frames"][15]["participantFrames"]
    gold = {pid: frame[str(pid)]["totalGold"] for pid in range(1, 11)}
    xp = {pid: frame[str(pid)]["xp"] for pid in range(1, 11)}
    lead = sum(gold[p] for p in range(1, 6)) - sum(gold[p] for p in range(6, 11))
    xp_lead = sum(xp[p] for p in range(1, 6)) - sum(xp[p] for p in range(6, 11))

    features = timeline_features(timeline)

    assert features[_puuid(timeline, 1)]["team_gold_diff_15"] == lead
    assert features[_puuid(timeline, 6)]["team_gold_diff_15"] == -lead
    assert features[_puuid(timeline, 3)]["team_xp_diff_15"] == xp_lead


def test_kili_smrti_asistence_in_shutdowni_do_15(events_timeline):
    features = timeline_features(events_timeline)
    p1, p2, p6, p7 = (features[_puuid(events_timeline, i)] for i in (1, 2, 6, 7))

    assert (p1["kills_15"], p1["deaths_15"], p1["assists_15"]) == (1, 1, 0)
    assert (p2["kills_15"], p2["deaths_15"], p2["assists_15"]) == (0, 0, 1)  # smrt v 15:30
    assert p7["shutdown_gold_15"] == 300 and p1["shutdown_gold_15"] == 0
    assert p1["shutdowns_given_15"] == 1 and p6["shutdowns_given_15"] == 0
    assert p1["first_blood_team"] == 1 and p6["first_blood_team"] == 0
    assert p1["team_kills_15"] == 1 and p1["enemy_kills_15"] == 1


def test_cilji_ekipe_do_15(events_timeline):
    features = timeline_features(events_timeline)
    blue, red = features[_puuid(events_timeline, 4)], features[_puuid(events_timeline, 9)]

    assert (blue["team_dragons_15"], blue["enemy_dragons_15"]) == (1, 0)  # zmaj v 16. ne šteje
    assert (blue["team_grubs_15"], blue["enemy_grubs_15"]) == (1, 1)
    assert (blue["team_heralds_15"], blue["enemy_heralds_15"]) == (0, 1)
    assert (blue["team_towers_15"], blue["enemy_towers_15"]) == (1, 0)
    assert (blue["team_plates_15"], blue["enemy_plates_15"]) == (2, 0)
    assert (red["team_dragons_15"], red["enemy_towers_15"], red["enemy_plates_15"]) == (0, 1, 2)


def test_nakupi_s_casom_in_razveljavitvijo(events_timeline):
    features = timeline_features(events_timeline)

    assert features[_puuid(events_timeline, 1)]["purchases"] == [[1055, 5], [3006, 1200]]
    assert features[_puuid(events_timeline, 2)]["purchases"] == []


def test_kratka_tekma_nima_stanja_ob_15(timeline):
    timeline["info"]["frames"] = timeline["info"]["frames"][:12]

    features = timeline_features(timeline)[_puuid(timeline, 1)]

    assert "gold_15" not in features and "team_gold_diff_15" not in features
    assert "kills_15" not in features and "team_dragons_15" not in features
    assert features["purchases"] == []


def _extended(timeline: dict, minutes: int) -> dict:
    """Časovnica z okvirji vsako minuto do `minutes` (zadnji okvir se kopira, zlato raste)."""
    frames = timeline["info"]["frames"]
    while len(frames) <= minutes:
        frame = copy.deepcopy(frames[-1])
        frame["timestamp"] = len(frames) * 60_000
        frame["events"] = []
        for state in frame["participantFrames"].values():
            state["totalGold"] += 100
        frames.append(frame)
    return timeline


@pytest.mark.parametrize("minute", [10, 15, 20, 25, 30, 40])
def test_stanje_ob_vseh_minutah(timeline, minute):
    timeline = _extended(timeline, 41)
    state = timeline["info"]["frames"][minute]["participantFrames"]["1"]

    features = timeline_features(timeline)[_puuid(timeline, 1)]

    assert features[f"gold_{minute}"] == state["totalGold"]
    assert f"team_gold_diff_{minute}" in features and f"enemy_towers_{minute}" in features


def test_tekma_do_22_minute_nima_stanja_ob_25_in_40(timeline):
    timeline = _extended(timeline, 22)
    timeline["info"]["frames"] = timeline["info"]["frames"][:23]

    features = timeline_features(timeline)[_puuid(timeline, 1)]

    assert "gold_20" in features
    assert "gold_25" not in features and "gold_40" not in features
