import enum
from typing import Any

from sqlalchemy import Enum, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class ModelKind(enum.StrEnum):
    BUILD_RANKER = "build_ranker"  # LightGBM ocena buildov (US-04)
    PLAYSTYLE_CLUSTERS = "playstyle_clusters"  # Gaussian Mixture arhetipi (US-06)


class ModelStatus(enum.StrEnum):
    TRAINED = "trained"  # naučen, še ne v uporabi
    ACTIVE = "active"  # uporablja se za priporočila
    RETIRED = "retired"  # zamenjala ga je novejša aktivna verzija


class MlModel(TimestampMixin, Base):
    """Verzija naučenega modela (ADR-0006). Vsako priporočilo modela hrani njen id.

    Naučen model je shranjen kot besedilo (LightGBM model_to_string), da ga API in delavec
    preberejo iz baze; datotečni sistem kontejnerjev je samo za branje.
    """

    __tablename__ = "ml_models"
    __table_args__ = (
        # Za vsak tip modela je aktivna največ ena verzija.
        Index(
            "uq_ml_models_active_kind",
            "kind",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ModelKind] = mapped_column(
        Enum(ModelKind, name="model_kind", values_callable=enum_values)
    )
    # Zaporedna verzija znotraj tipa, npr. "build_ranker-3".
    version: Mapped[int]
    # Patch učnih podatkov (najnovejši v učni množici), npr. "16.22".
    patch: Mapped[str] = mapped_column(String(16))
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, name="model_status", values_callable=enum_values),
        default=ModelStatus.TRAINED,
        server_default=ModelStatus.TRAINED.value,
    )
    # Metrike na testnih tekmah (auc, log_loss, baseline_auc, train/test velikost).
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    # Opis značilk (seznam stolpcev, predmeti, šampioni), da se vhod ob napovedi ujema z učenjem.
    feature_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    artifact: Mapped[str] = mapped_column(Text)
