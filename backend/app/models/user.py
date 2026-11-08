from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_values

if TYPE_CHECKING:
    from app.models.riot_account import RiotAccount


class UserRole(enum.StrEnum):
    PLAYER = "player"
    COACH = "coach"
    ADMIN = "admin"


class ExplanationLevel(enum.StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # E-pošta se pred shranjevanjem normalizira v male črke (v servisu za registracijo).
    email: Mapped[str] = mapped_column(String(320), unique=True)
    # Samo Argon2id zgostitev, nikoli gesla v čistopisu.
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        default=UserRole.PLAYER,
        server_default=UserRole.PLAYER.value,
    )
    explanation_level: Mapped[ExplanationLevel] = mapped_column(
        Enum(ExplanationLevel, name="explanation_level", values_callable=enum_values),
        default=ExplanationLevel.INTERMEDIATE,
        server_default=ExplanationLevel.INTERMEDIATE.value,
    )

    # Povečanje (ob odjavi) prekliče vse prej izdane osvežilne žetone uporabnika.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")

    riot_accounts: Mapped[list[RiotAccount]] = relationship(back_populates="user")
