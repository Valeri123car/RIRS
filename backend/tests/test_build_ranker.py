"""Značilke in učenje modela buildov (US-04, #20)."""

import pytest

from app.ml.build_features import (
    COMP_FEATURES,
    CORE_SIZE,
    FeatureSpec,
    TrainingRow,
    build_spec,
    comp_vector,
)
from app.ml.build_ranker import NotEnoughDataError, train_build_ranker
from app.models.champion import Champion, DamageProfile
from tests.ml_synthetic import ANTI_HEAL, synthetic_rows


def champ(profile, **ratings):
    values = dict.fromkeys(("cc", "healing", "engage", "burst", "tank", "poke"), 0)
    values.update(ratings)
    return Champion(id=1, slug="X", name="X", damage_profile=profile, **values)


def test_vektor_sestave_ima_delez_fizicne_skode_in_vsote_ocen():
    enemies = [
        champ(DamageProfile.PHYSICAL, healing=3),
        champ(DamageProfile.MAGIC, healing=2, cc=1),
    ]

    vector = comp_vector(enemies)

    assert set(vector) == set(COMP_FEATURES)
    assert vector["enemy_physical"] == 0.5
    assert (vector["enemy_healing"], vector["enemy_cc"]) == (5.0, 1.0)


def test_specifikacija_vsebuje_pogoste_predmete_in_jedra_buildov():
    spec = build_spec(synthetic_rows(matches=60))

    assert ANTI_HEAL in spec.item_ids
    assert spec.champion_games[1] == 120
    assert spec.champion_position[1] == "TOP"
    builds = spec.champion_builds[1]
    assert builds and all(len(b) == CORE_SIZE for b in builds)
    assert set(spec.comp_mean) == set(COMP_FEATURES)


def test_specifikacija_prezivi_pretvorbo_v_json():
    spec = build_spec(synthetic_rows(matches=60))

    again = FeatureSpec.from_json(spec.to_json())

    assert again.columns == spec.columns
    assert again.champion_builds[1] == spec.champion_builds[1]


def test_model_z_znacilkami_sestave_premaga_izhodisce():
    trained = train_build_ranker(synthetic_rows(), patch="16.22")

    metrics = trained.metrics
    assert set(metrics) >= {
        "auc",
        "log_loss",
        "baseline_auc",
        "contribution",
        "contribution_std",
        "train_matches",
        "test_matches",
    }
    assert metrics["auc"] > metrics["baseline_auc"]
    # Prispevek sestave mora biti večji od odklona med delitvami (pogoj aktivacije).
    assert metrics["contribution"] > metrics["contribution_std"] >= 0
    assert (metrics["folds"], metrics["rows"]) == (5, 4000)


def test_ucenje_je_ponovljivo():
    first = train_build_ranker(synthetic_rows(), patch="16.22").metrics
    second = train_build_ranker(synthetic_rows(), patch="16.22").metrics

    assert first == second


def test_premalo_podatkov_za_ucenje():
    rows = [TrainingRow("M1", 1, "TOP", {}, (101,), True)]

    with pytest.raises(NotEnoughDataError):
        train_build_ranker(rows, patch="16.22")
