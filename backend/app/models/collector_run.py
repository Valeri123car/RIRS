import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_values


class CollectorStatus(enum.StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class CollectorRun(Base):
    """En zagon zbiralnika tekem (US-07): čas, število novih tekem in izid."""

    __tablename__ = "collector_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[CollectorStatus] = mapped_column(
        Enum(CollectorStatus, name="collector_status", values_callable=enum_values),
        default=CollectorStatus.RUNNING,
        server_default=CollectorStatus.RUNNING.value,
    )
    platform: Mapped[str] = mapped_column(String(8))
    players: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    new_matches: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Sporočilo napake (brez API ključa – napake Riot prehoda ga ne vsebujejo).
    error: Mapped[str | None] = mapped_column(String(500))
