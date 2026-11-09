"""Administracija modelov: seznam verzij in aktivacija (US-07, F07)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update

from app.api.deps import AdminUser, DbSession
from app.ml.build_ranker import ActivationRefusedError, activate_build_ranker
from app.models.ml_model import MlModel, ModelKind, ModelStatus

router = APIRouter(prefix="/admin", tags=["admin"])


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ModelKind
    version: int
    patch: str
    status: ModelStatus
    metrics: dict[str, Any]
    created_at: datetime


@router.get("/models")
def list_models(_admin: AdminUser, db: DbSession) -> list[ModelOut]:
    """Vse verzije modelov, najnovejše najprej."""
    models = db.scalars(select(MlModel).order_by(MlModel.created_at.desc(), MlModel.id.desc()))
    return [ModelOut.model_validate(m) for m in models]


@router.post("/models/{model_id}/activate")
def activate_model(model_id: int, _admin: AdminUser, db: DbSession) -> ModelOut:
    """Aktivira verzijo; prejšnja aktivna istega tipa dobi status "umaknjen".

    Model buildov, ki ni boljši od izhodiščnega, se ne aktivira (409, ADR-0006).
    """
    model = db.get(MlModel, model_id)
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verzija modela ne obstaja.")
    if model.status is ModelStatus.ACTIVE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ta verzija je že aktivna.")
    if model.kind is ModelKind.BUILD_RANKER:
        try:
            activate_build_ranker(db, model)
        except ActivationRefusedError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    else:
        # Nenadzorovani modeli (arhetipi) nimajo izhodiščnega AUC: samo zamenjava verzije.
        db.execute(
            update(MlModel)
            .where(MlModel.kind == model.kind, MlModel.status == ModelStatus.ACTIVE)
            .values(status=ModelStatus.RETIRED)
        )
        model.status = ModelStatus.ACTIVE
        db.flush()
    db.commit()
    return ModelOut.model_validate(model)
