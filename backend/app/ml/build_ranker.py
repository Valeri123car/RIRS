"""Učenje, shranjevanje in nalaganje modela LightGBM za ocenjevanje buildov (US-04, ADR-0006).

Model se uči na igralcih iz zbranih tekem (cilj: zmaga). Tekme se med učno in testno množico
delijo v celoti, da isti dogodek ni na obeh straneh. Za potrditev (ADR-0006) se nauči še
izhodiščni model brez značilk sestave; aktivirati je mogoče samo model z višjim AUC.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ml.build_features import (
    CATEGORICAL_FEATURES,
    COMP_FEATURES,
    FeatureSpec,
    TrainingRow,
    build_spec,
    encode_rows,
)
from app.models.ml_model import MlModel, ModelKind, ModelStatus

MIN_TRAINING_ROWS = 200
CV_FOLDS = 5
SEED = 7
NUM_ROUNDS = 200
PARAMS: dict[str, Any] = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.9,
    "lambda_l2": 1.0,
    "seed": SEED,
    "deterministic": True,
    "num_threads": 1,
    "verbose": -1,
}


class NotEnoughDataError(ValueError):
    """Premalo tekem za učenje modela."""


class ActivationRefusedError(ValueError):
    """Model ni boljši od izhodiščnega, zato ga ni mogoče aktivirati (ADR-0006)."""


@dataclass
class TrainedRanker:
    booster: lgb.Booster
    spec: FeatureSpec
    metrics: dict[str, Any]
    patch: str


@dataclass
class LoadedRanker:
    model_id: int
    booster: lgb.Booster
    spec: FeatureSpec


def train_build_ranker(rows: Sequence[TrainingRow], patch: str) -> TrainedRanker:
    if len(rows) < MIN_TRAINING_ROWS:
        raise NotEnoughDataError(
            f"Za učenje je potrebnih vsaj {MIN_TRAINING_ROWS} igralcev, na voljo {len(rows)}."
        )
    spec = build_spec(rows)
    features, labels = encode_rows(spec, rows)
    groups = [row.match_id for row in rows]
    columns = spec.columns
    comp_columns = {columns.index(name) for name in COMP_FEATURES}
    keep = [i for i in range(len(columns)) if i not in comp_columns]
    keep_columns = [columns[i] for i in keep]

    # Ena delitev je šumna (poskusi 4–5: odklon ±0,01–0,02), zato metrike povprečimo čez
    # GroupKFold; cele tekme so v isti skupini, da isti dogodek ni na obeh straneh.
    aucs, baseline_aucs, losses = [], [], []
    for train_idx, test_idx in GroupKFold(n_splits=CV_FOLDS).split(features, labels, groups):
        test_labels = labels[test_idx]
        model = _fit(features[train_idx], labels[train_idx], columns)
        predicted = model.predict(features[test_idx])
        baseline = _fit(features[train_idx][:, keep], labels[train_idx], keep_columns)
        baseline_predicted = baseline.predict(features[test_idx][:, keep])
        aucs.append(roc_auc_score(test_labels, predicted))
        baseline_aucs.append(roc_auc_score(test_labels, baseline_predicted))
        losses.append(log_loss(test_labels, predicted))
    gains = np.array(aucs) - np.array(baseline_aucs)

    # Končni model se nauči na vseh podatkih; metrike zgoraj ocenjujejo ta postopek.
    booster = _fit(features, labels, columns)
    metrics = {
        "auc": round(float(np.mean(aucs)), 4),
        "auc_std": round(float(np.std(aucs)), 4),
        "baseline_auc": round(float(np.mean(baseline_aucs)), 4),
        "baseline_auc_std": round(float(np.std(baseline_aucs)), 4),
        # Prispevek značilk sestave po delitvah in njegov odklon: pogoj aktivacije.
        "contribution": round(float(gains.mean()), 4),
        "contribution_std": round(float(gains.std()), 4),
        "log_loss": round(float(np.mean(losses)), 4),
        "folds": CV_FOLDS,
        "rows": len(rows),
        "matches": len(set(groups)),
        "items": len(spec.item_ids),
    }
    return TrainedRanker(booster=booster, spec=spec, metrics=metrics, patch=patch)


def _fit(features: np.ndarray, labels: np.ndarray, columns: list[str]) -> lgb.Booster:
    categorical = [name for name in CATEGORICAL_FEATURES if name in columns]
    dataset = lgb.Dataset(
        features, labels, feature_name=columns, categorical_feature=categorical, free_raw_data=False
    )
    return lgb.train(PARAMS, dataset, num_boost_round=NUM_ROUNDS)


def save_build_ranker(session: Session, trained: TrainedRanker, activate: bool = False) -> MlModel:
    """Shrani verzijo (status "trained"); z activate=True jo takoj aktivira (flush, brez commit)."""
    latest = session.scalar(
        select(func.max(MlModel.version)).where(MlModel.kind == ModelKind.BUILD_RANKER)
    )
    model = MlModel(
        kind=ModelKind.BUILD_RANKER,
        version=(latest or 0) + 1,
        patch=trained.patch,
        status=ModelStatus.TRAINED,
        metrics=trained.metrics,
        feature_spec=trained.spec.to_json(),
        artifact=trained.booster.model_to_string(),
    )
    session.add(model)
    session.flush()
    if activate:
        activate_build_ranker(session, model)
    return model


def activate_build_ranker(session: Session, model: MlModel) -> None:
    """Aktivira verzijo, če sestava dokazljivo pomaga; prejšnja aktivna je umaknjena (ADR-0006).

    Pogoj: povprečni prispevek značilk sestave čez delitve je večji od njegovega odklona
    (drugače je razlika šum). Starejše verzije brez CV metrik: AUC višji od izhodiščnega.
    """
    metrics = model.metrics
    if "contribution" in metrics:
        if metrics["contribution"] <= metrics.get("contribution_std", 0):
            raise ActivationRefusedError(
                f"Prispevek sestave {metrics['contribution']} ni večji od odklona "
                f"{metrics.get('contribution_std')}; model ostane neaktiven."
            )
    elif metrics.get("auc", 0) <= metrics.get("baseline_auc", 1):
        raise ActivationRefusedError(
            f"AUC {metrics.get('auc')} ni višji od izhodiščnega "
            f"{metrics.get('baseline_auc')}; model ostane neaktiven."
        )
    session.execute(
        update(MlModel)
        .where(MlModel.kind == ModelKind.BUILD_RANKER, MlModel.status == ModelStatus.ACTIVE)
        .values(status=ModelStatus.RETIRED)
    )
    model.status = ModelStatus.ACTIVE
    session.flush()


# Naložen model po id: besedilo modela se ne spreminja, zato ga je varno hraniti v pomnilniku.
_BOOSTERS: dict[int, lgb.Booster] = {}


def load_active_build_ranker(session: Session) -> LoadedRanker | None:
    model = session.scalar(
        select(MlModel).where(
            MlModel.kind == ModelKind.BUILD_RANKER, MlModel.status == ModelStatus.ACTIVE
        )
    )
    if model is None:
        return None
    booster = _BOOSTERS.get(model.id)
    if booster is None:
        booster = lgb.Booster(model_str=model.artifact)
        _BOOSTERS[model.id] = booster
    return LoadedRanker(
        model_id=model.id, booster=booster, spec=FeatureSpec.from_json(model.feature_spec)
    )
