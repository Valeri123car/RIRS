from sqlalchemy import select, update

from app.models.ml_model import MlModel, ModelKind, ModelStatus
from app.models.user import User, UserRole
from tests.db.conftest import auth_headers


def _admin(api, db, email="admin@example.com"):
    headers = auth_headers(api, email)
    db.execute(update(User).where(User.email == email).values(role=UserRole.ADMIN))
    db.flush()
    return headers


def _model(db, kind=ModelKind.BUILD_RANKER, version=1, status=ModelStatus.TRAINED, **metrics):
    model = MlModel(
        kind=kind, version=version, patch="16.22", status=status, metrics=metrics, artifact="x"
    )
    db.add(model)
    db.flush()
    return model


def test_brez_prijave_je_401_in_navaden_uporabnik_403(api, db):
    model = _model(db)

    assert api.get("/admin/models").status_code == 401
    assert api.post(f"/admin/models/{model.id}/activate").status_code == 401
    player = auth_headers(api)
    assert api.get("/admin/models", headers=player).status_code == 403
    assert api.post(f"/admin/models/{model.id}/activate", headers=player).status_code == 403
    db.refresh(model)
    assert model.status is ModelStatus.TRAINED


def test_admin_vidi_verzije_z_metrikami(api, db):
    model = _model(db, version=1, auc=0.6, baseline_auc=0.55)

    response = api.get("/admin/models", headers=_admin(api, db))

    assert response.status_code == 200
    row = next(r for r in response.json() if r["id"] == model.id)
    assert row["metrics"] == {"auc": 0.6, "baseline_auc": 0.55}
    assert row["status"] == "trained"
    assert row["kind"] == "build_ranker"


def test_aktivacija_umakne_prejsnjo_verzijo(api, db):
    old = _model(db, version=1, status=ModelStatus.ACTIVE, auc=0.6, baseline_auc=0.5)
    new = _model(db, version=2, auc=0.62, baseline_auc=0.5)

    response = api.post(f"/admin/models/{new.id}/activate", headers=_admin(api, db))

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    db.refresh(old)
    assert (old.status, new.status) == (ModelStatus.RETIRED, ModelStatus.ACTIVE)


def test_slabsega_od_izhodisca_ni_mogoce_aktivirati(api, db):
    new = _model(db, version=2, auc=0.5, baseline_auc=0.55)

    response = api.post(f"/admin/models/{new.id}/activate", headers=_admin(api, db))

    assert response.status_code == 409
    db.refresh(new)
    assert new.status is ModelStatus.TRAINED


def test_ze_aktivna_in_neobstojeca_verzija(api, db):
    active = _model(db, status=ModelStatus.ACTIVE, auc=0.6, baseline_auc=0.5)
    headers = _admin(api, db)

    assert api.post(f"/admin/models/{active.id}/activate", headers=headers).status_code == 409
    assert api.post("/admin/models/999999/activate", headers=headers).status_code == 404


def test_arhetipi_se_aktivirajo_brez_izhodiscnega_auc(api, db):
    kind = ModelKind.PLAYSTYLE_CLUSTERS
    old = _model(db, kind, 1, ModelStatus.ACTIVE)
    new = _model(db, kind, 2)

    response = api.post(f"/admin/models/{new.id}/activate", headers=_admin(api, db))

    assert response.status_code == 200
    db.refresh(old)
    assert (old.status, new.status) == (ModelStatus.RETIRED, ModelStatus.ACTIVE)
    active = db.scalars(
        select(MlModel).where(MlModel.kind == kind, MlModel.status == ModelStatus.ACTIVE)
    ).all()
    assert len(active) == 1
