from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Item(TimestampMixin, Base):
    """Predmet iz Data Dragon z oznakami, ki jih uporablja logika priporočil."""

    __tablename__ = "items"
    __table_args__ = (CheckConstraint("cost >= 0", name="cost_non_negative"),)

    # Riot ID predmeta, npr. 3033 za Mortal Reminder.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(64))
    cost: Mapped[int] = mapped_column(default=0, server_default="0")
    # Oznake, npr. ["anti_heal", "armor_pen"].
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list, server_default="{}")
