from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.profiling.baselines import compute_baselines, load_baselines, store_baselines
from app.profiling.indicators import INDICATORS
from app.profiling.style import build_style_profile
from app.riot.fixture_client import FixtureRiotClient

ROK = "fx-rok-d83bbdc2bfce918cfdde5b798972fda2c0076c52da34f22a4c6cc4f89815e655d83bbdc"
BASELINES = {pos: dict.fromkeys(INDICATORS, 2.0) for pos in ("TOP", "JUNGLE", "MIDDLE")}


def test_profil_prenese_manjkajoce_tekme_in_oznaci_nizko_zaupanje(db: Session):
    profile = build_style_profile(db, FixtureRiotClient(), ROK, "eun1", BASELINES)

    assert db.scalar(select(func.count()).select_from(Match)) >= 1
    assert profile["matches"] >= 1
    assert profile["low_confidence"] is True
    assert set(profile["indicators"]) == set(INDICATORS)
    assert profile["role"] in BASELINES


def test_brez_prenosa_uporabi_samo_tekme_v_bazi(db: Session):
    profile = build_style_profile(db, None, ROK, "eun1", BASELINES, download=False)

    assert profile == {"matches": 0, "low_confidence": True, "role": None, "indicators": {}}


def test_mediane_se_shranijo_in_preberejo(db: Session):
    build_style_profile(db, FixtureRiotClient(), ROK, "eun1", BASELINES)

    medians, sizes = compute_baselines(db)
    # Fixture tekme so kratke (< 15 min) ali ne; shranjeno mora biti vsaj to, kar je izračunano.
    store_baselines(db, medians, sizes)

    assert load_baselines(db) == medians
