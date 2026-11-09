import numpy as np
import pytest

from app.profiling.archetypes import (
    BALANCED,
    MIN_PLAYERS,
    NotEnoughPlayersError,
    classify,
    name_component,
    train_archetypes,
)
from app.profiling.indicators import INDICATORS


def _blobs(seed: int = 1) -> np.ndarray:
    """Tri jasno ločene skupine igralcev: agresivni, roamerji, farmerji."""
    rng = np.random.default_rng(seed)
    centers = {
        "aggression": [1.0, 0, 0, 0, 0],
        "roaming": [0, 1.5, 0, 0, 0],
        "farming": [0, 0, 0.6, 0, 0],
    }
    return np.vstack([rng.normal(c, 0.1, size=(80, len(INDICATORS))) for c in centers.values()])


def test_ime_gruce_po_najizrazitejsem_kazalniku():
    assert name_component(np.array([1.2, 0.0, 0.0, 0.0, 0.0])) == "Agresiven v linijski fazi"
    assert name_component(np.array([0.0, -1.0, 0.0, 0.0, 0.0])) == "Ostaja v svoji liniji"


def test_ime_gruce_doda_drugi_kazalnik_samo_ce_je_dovolj_izrazit():
    assert name_component(np.array([1.2, 0.9, 0.0, 0.0, 0.0])) == (
        "Agresiven v linijski fazi + Roamer"
    )
    assert name_component(np.array([1.2, 0.3, 0.0, 0.0, 0.0])) == "Agresiven v linijski fazi"


def test_povprecen_igralec_je_uravnotezen():
    assert name_component(np.zeros(len(INDICATORS))) == BALANCED


def test_model_loci_skupine_in_klasificira_profil():
    trained = train_archetypes(_blobs(), "16.22")
    spec = trained["spec"]

    assert trained["metrics"]["components"] >= 3
    assert sum(trained["metrics"]["cluster_sizes"]) == 240
    result = classify(spec, dict(zip(INDICATORS, [0.0, 1.5, 0.0, 0.0, 0.0], strict=True)))
    assert "Roamer" in result.name
    assert 0.5 < result.probability <= 1.0


def test_ucenje_je_ponovljivo():
    a = train_archetypes(_blobs(), "16.22")["metrics"]
    b = train_archetypes(_blobs(), "16.22")["metrics"]

    assert a == b


def test_premalo_igralcev():
    with pytest.raises(NotEnoughPlayersError):
        train_archetypes(np.zeros((MIN_PLAYERS - 1, len(INDICATORS))), "16.22")
