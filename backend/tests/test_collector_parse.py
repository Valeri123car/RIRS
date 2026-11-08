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
