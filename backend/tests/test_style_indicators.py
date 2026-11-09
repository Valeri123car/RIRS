import pytest

from app.profiling.indicators import (
    AGGRESSION,
    EARLY_DEATHS,
    FARMING,
    INDICATORS,
    ROAMING,
    VISION,
    compute_indicators,
    slim_participant,
)
from app.profiling.style import relative_to_median

PARTICIPANT = {
    "totalMinionsKilled": 240,
    "neutralMinionsKilled": 0,
    "deaths": 7,
    "teamPosition": "MIDDLE",
    "challenges": {
        "soloKills": 3,
        "takedownsFirstXMinutes": 2,
        "killsOnOtherLanesEarlyJungleAsLaner": 1,
        "teleportTakedowns": 2,
        "visionScorePerMinute": 0.9,
    },
}


def test_kazalniki_iz_tekme():
    result = compute_indicators(PARTICIPANT, duration_s=1800, deaths_before_14=1)

    assert set(result) == set(INDICATORS)
    assert result[AGGRESSION] == 5
    assert result[ROAMING] == 3
    assert result[FARMING] == pytest.approx(8.0)
    assert result[EARLY_DEATHS] == 1
    assert result[VISION] == pytest.approx(0.9)


def test_zgodnje_smrti_brez_casovnice_so_ocena_iz_smrti_na_minuto():
    result = compute_indicators(PARTICIPANT, duration_s=1800, deaths_before_14=None)

    assert result[EARLY_DEATHS] == pytest.approx(7 / 30 * 14)


def test_manjkajoca_polja_so_nic():
    result = compute_indicators({}, duration_s=1200)

    assert result[AGGRESSION] == result[ROAMING] == result[FARMING] == result[VISION] == 0


def test_slim_participant_obdrzi_samo_potrebna_polja():
    slim = slim_participant(
        {**PARTICIPANT, "goldEarned": 1, "challenges": {"soloKills": 1, "x": 2}}
    )

    assert "goldEarned" not in slim
    assert slim["challenges"]["soloKills"] == 1
    assert "x" not in slim["challenges"]


def test_odstopanje_od_mediane():
    assert relative_to_median(12, 8) == pytest.approx(0.5)
    # Mediana 0 (roaming): imenovalec je 1, ne deljenje z nič.
    assert relative_to_median(3, 0) == 3
