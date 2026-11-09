"""Arhetipi igralnega sloga z mešanico Gaussovih porazdelitev (US-06, ADR-0006).

Učni podatki so profili igralcev (povprečno odstopanje od mediane vloge, glej style.py) iz
tekem v bazi. Kazalniki se standardizirajo (StandardScaler), število komponent določi BIC.
Gruče nimajo vnaprejšnjih imen: poimenujemo jih po kazalnikih, ki najbolj odstopajo od
povprečja. Model se shrani kot JSON (brez pickle), napoved pa izračuna numpy.
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.ml_model import MlModel, ModelKind, ModelStatus
from app.profiling.baselines import Baselines, iter_participants, load_baselines
from app.profiling.indicators import INDICATORS, compute_indicators
from app.profiling.style import MAX_MATCHES, relative_to_median

logger = logging.getLogger(__name__)

MIN_PLAYER_MATCHES = 5
MIN_PLAYERS = 50
COMPONENTS = range(2, 9)
SEED = 7
# Odstopanje (v standardnih odklonih), od katerega kazalnik poimenuje gručo.
NAME_THRESHOLD = 0.4
SECOND_THRESHOLD = 0.7

LABELS = {
    ("aggression", 1): "Agresiven v linijski fazi",
    ("aggression", -1): "Pasiven v linijski fazi",
    ("roaming", 1): "Roamer",
    ("roaming", -1): "Ostaja v svoji liniji",
    ("farming", 1): "Močan farmer",
    ("farming", -1): "Šibek farmer",
    ("early_deaths", 1): "Tvegan (zgodnje smrti)",
    ("early_deaths", -1): "Previden (malo zgodnjih smrti)",
    ("vision", 1): "Vizijski igralec",
    ("vision", -1): "Malo vizije",
}
BALANCED = "Uravnotežen"


class NotEnoughPlayersError(ValueError):
    """Premalo igralcev z dovolj tekem za učenje."""


@dataclass
class Archetype:
    name: str
    probability: float


def player_vectors(session: Session, baselines: Baselines) -> np.ndarray:
    """Povprečno odstopanje od mediane vloge (zadnjih 20 tekem) za igralce z dovolj tekem."""
    per_player: dict[str, list[tuple[Any, list[float]]]] = defaultdict(list)
    for puuid, participant, duration_s, start, deaths14 in iter_participants(session):
        medians = baselines.get(participant.get("teamPosition") or "")
        if medians is None:
            continue
        values = compute_indicators(participant, duration_s, deaths14)
        per_player[puuid].append(
            (start, [relative_to_median(values[n], medians[n]) for n in INDICATORS])
        )
    vectors = []
    for matches in per_player.values():
        if len(matches) < MIN_PLAYER_MATCHES:
            continue
        recent = sorted(matches, key=lambda m: m[0], reverse=True)[:MAX_MATCHES]
        vectors.append(np.mean([m[1] for m in recent], axis=0))
    return np.array(vectors)


def name_component(z_means: np.ndarray) -> str:
    """Ime gruče iz najizrazitejših kazalnikov (z-vrednosti povprečja gruče)."""
    order = np.argsort(-np.abs(z_means))
    parts = []
    for rank, idx in enumerate(order[:2]):
        z = z_means[idx]
        if abs(z) < (NAME_THRESHOLD if rank == 0 else SECOND_THRESHOLD):
            break
        parts.append(LABELS[(INDICATORS[idx], 1 if z > 0 else -1)])
    return " + ".join(parts) if parts else BALANCED


def train_archetypes(vectors: np.ndarray, patch: str) -> dict[str, Any]:
    """Nauči GMM (diagonalne kovariance), število komponent izbere z BIC; vrne JSON model."""
    if len(vectors) < MIN_PLAYERS:
        raise NotEnoughPlayersError(f"{len(vectors)} igralcev, potrebnih {MIN_PLAYERS}")
    scaler = StandardScaler().fit(vectors)
    scaled = scaler.transform(vectors)
    fits = {
        k: GaussianMixture(k, covariance_type="diag", n_init=5, random_state=SEED).fit(scaled)
        for k in COMPONENTS
    }
    bic = {k: float(m.bic(scaled)) for k, m in fits.items()}
    best = min(bic, key=bic.__getitem__)
    gmm = fits[best]
    labels = gmm.predict(scaled)
    names = [name_component(mean) for mean in gmm.means_]
    return {
        "metrics": {
            "players": len(vectors),
            "components": best,
            "bic": bic,
            "cluster_sizes": [int((labels == i).sum()) for i in range(best)],
            "names": names,
        },
        "spec": {
            "indicators": list(INDICATORS),
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(),
            "weights": gmm.weights_.tolist(),
            "means": gmm.means_.tolist(),
            "variances": gmm.covariances_.tolist(),
            "names": names,
        },
        "patch": patch,
    }


def classify(spec: dict[str, Any], vs_median: dict[str, float]) -> Archetype:
    """Arhetip z največjo verjetnostjo za profil (kazalnik → odstopanje od mediane)."""
    raw = np.array([vs_median[n] for n in spec["indicators"]])
    x = (raw - spec["scaler_mean"]) / spec["scaler_scale"]
    means, var = np.array(spec["means"]), np.array(spec["variances"])
    log_p = np.log(spec["weights"]) - 0.5 * np.sum(
        np.log(2 * np.pi * var) + (x - means) ** 2 / var, axis=1
    )
    p = np.exp(log_p - log_p.max())
    p /= p.sum()
    best = int(p.argmax())
    return Archetype(name=spec["names"][best], probability=round(float(p[best]), 2))


def save_archetypes(session: Session, trained: dict[str, Any]) -> MlModel:
    """Shrani verzijo in jo aktivira (nenadzorovan, brez izhodiščnega AUC); brez commit."""
    latest = session.scalar(
        select(func.max(MlModel.version)).where(MlModel.kind == ModelKind.PLAYSTYLE_CLUSTERS)
    )
    session.execute(
        update(MlModel)
        .where(MlModel.kind == ModelKind.PLAYSTYLE_CLUSTERS, MlModel.status == ModelStatus.ACTIVE)
        .values(status=ModelStatus.RETIRED)
    )
    model = MlModel(
        kind=ModelKind.PLAYSTYLE_CLUSTERS,
        version=(latest or 0) + 1,
        patch=trained["patch"],
        status=ModelStatus.ACTIVE,
        metrics=trained["metrics"],
        feature_spec=trained["spec"],
        artifact=json.dumps(trained["spec"]),
    )
    session.add(model)
    session.flush()
    return model


def load_active_archetypes(session: Session) -> dict[str, Any] | None:
    model = session.scalar(
        select(MlModel).where(
            MlModel.kind == ModelKind.PLAYSTYLE_CLUSTERS, MlModel.status == ModelStatus.ACTIVE
        )
    )
    return model.feature_spec if model is not None else None


def main() -> None:
    from app.db.session import get_session_factory
    from app.models.match import Match

    logging.basicConfig(level=logging.INFO)
    with get_session_factory()() as session:
        vectors = player_vectors(session, load_baselines(session))
        patch = session.scalar(select(func.max(Match.patch))) or ""
        trained = train_archetypes(vectors, patch)
        model = save_archetypes(session, trained)
        session.commit()
    logger.info("model %s: %s", model.id, trained["metrics"])


if __name__ == "__main__":
    main()
