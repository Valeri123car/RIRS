import enum
import uuid
from typing import Any

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class AnalysisStatus(enum.StrEnum):
    PENDING = "pending"
    CAPTURING = "capturing"
    PROFILING = "profiling"
    RECOMMENDING = "recommending"
    COMPLETED = "completed"
    NOT_IN_GAME = "not_in_game"
    FAILED = "failed"


class LiveAnalysis(TimestampMixin, Base):
    """Analiza aktivne tekme (US-02). ID je UUID, ker si gost analizo ogleda brez prijave."""

    __tablename__ = "live_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Vnos uporabnika; puuid in game_id izpolni delavec.
    game_name: Mapped[str] = mapped_column(String(32))
    tag_line: Mapped[str] = mapped_column(String(8))
    platform: Mapped[str] = mapped_column(String(8))
    puuid: Mapped[str | None] = mapped_column(String(78))
    game_id: Mapped[int | None] = mapped_column(BigInteger)

    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status", values_callable=enum_values),
        default=AnalysisStatus.PENDING,
        server_default=AnalysisStatus.PENDING.value,
    )
    # Sporočilo za uporabnika, kadar analiza ne uspe (npr. "Igralec trenutno ni v tekmi").
    error: Mapped[str | None] = mapped_column(String(200))
    # 10 udeležencev: puuid, riot_id, team_id, champion_id/name/slug, spelli, is_target.
    participants: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    # Profil nasprotne sestave (US-03).
    enemy_comp: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Priporočilo builda (US-04): vir (model/pravila), variante z runami, predmeti in razlogi.
    recommendation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
