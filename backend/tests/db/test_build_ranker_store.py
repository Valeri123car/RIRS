"""Shranjevanje, aktivacija in nalaganje verzij modela buildov (US-04, #20)."""

from dataclasses import replace

import pytest
from sqlalchemy import update

from app.ml.build_ranker import (
    ActivationRefusedError,
    activate_build_ranker,
    load_active_build_ranker,
    save_build_ranker,
    train_build_ranker,
)
from app.models.ml_model import MlModel, ModelStatus
from tests.ml_synthetic import synthetic_rows


@pytest.fixture(scope="module")
def trained():
    return train_build_ranker(synthetic_rows(matches=150), patch="16.22")


@pytest.fixture(autouse=True)
def no_active_models(db):
    # Testna baza je lahko že imela aktiven model; v transakciji testa ga umaknemo.
    db.execute(
        update(MlModel)
        .where(MlModel.status == ModelStatus.ACTIVE)
        .values(status=ModelStatus.RETIRED)
    )


def test_nova_verzija_je_shranjena_kot_naucena(db, trained):
    first = save_build_ranker(db, trained)
    second = save_build_ranker(db, trained)

    assert second.version == first.version + 1
    assert first.status == ModelStatus.TRAINED
    assert first.metrics["auc"] == trained.metrics["auc"]
    assert first.feature_spec["columns"] == trained.spec.columns
    assert load_active_build_ranker(db) is None


def test_aktivacija_umakne_prejsnjo_verzijo_in_model_se_nalozi(db, trained):
    first = save_build_ranker(db, trained, activate=True)
    second = save_build_ranker(db, trained, activate=True)

    db.refresh(first)
    assert (first.status, second.status) == (ModelStatus.RETIRED, ModelStatus.ACTIVE)
    loaded = load_active_build_ranker(db)
    assert loaded.model_id == second.id
    assert loaded.spec.columns == trained.spec.columns


def test_model_slabsi_od_izhodisca_ni_mogoce_aktivirati(db, trained):
    worse = replace(
        trained,
        metrics={**trained.metrics, "auc": 0.5, "baseline_auc": 0.55, "contribution": -0.05},
    )
    model = save_build_ranker(db, worse)

    with pytest.raises(ActivationRefusedError):
        activate_build_ranker(db, model)
    assert model.status == ModelStatus.TRAINED


def test_prispevek_sestave_znotraj_odklona_ni_dovolj_za_aktivacijo(db, trained):
    noisy = replace(
        trained,
        metrics={**trained.metrics, "contribution": 0.004, "contribution_std": 0.01},
    )
    model = save_build_ranker(db, noisy)

    with pytest.raises(ActivationRefusedError, match="odklon"):
        activate_build_ranker(db, model)
    assert model.status == ModelStatus.TRAINED


def test_starejsa_verzija_brez_cv_metrik_se_presoja_po_auc(db, trained):
    legacy_metrics = {"auc": 0.6, "baseline_auc": 0.55}
    model = save_build_ranker(db, replace(trained, metrics=legacy_metrics), activate=True)

    assert model.status == ModelStatus.ACTIVE
