from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RiotVerification(TimestampMixin, Base):
    """Izziv za povezavo Riot računa (US-01): igralec mora do expires_at nastaviti icon_id."""

    __tablename__ = "riot_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    puuid: Mapped[str] = mapped_column(String(78))
    game_name: Mapped[str] = mapped_column(String(32))
    tag_line: Mapped[str] = mapped_column(String(8))
    platform: Mapped[str] = mapped_column(String(8))
    icon_id: Mapped[int] = mapped_column(SmallInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
