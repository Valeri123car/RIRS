from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class RiotAccount(TimestampMixin, Base):
    """Riot račun: naš uporabnik (user_id) ali igralec, ki se pojavi v tekmah (user_id je NULL).

    Ker je puuid primarni ključ in ima račun en sam user_id, je lahko račun
    povezan z največ enim uporabnikom (pogoj iz US-01).
    """

    __tablename__ = "riot_accounts"

    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    game_name: Mapped[str] = mapped_column(String(32))
    tag_line: Mapped[str] = mapped_column(String(8))
    # Riot platforma, npr. "eun1" ali "euw1".
    platform: Mapped[str] = mapped_column(String(8))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    profile_public: Mapped[bool] = mapped_column(default=True, server_default="true")

    user: Mapped[User | None] = relationship(back_populates="riot_accounts")
