from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Rune(TimestampMixin, Base):
    """Rune in drevesa run iz Data Dragon (runesReforged.json); preslikava ID → ime."""

    __tablename__ = "runes"

    # Riot ID: drevo (npr. 8000 Precision) ali runa (npr. 8010 Conqueror).
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(64))
    # Drevo, ki mu runa pripada; pri drevesih samem ni vrednosti.
    tree_id: Mapped[int | None] = mapped_column(default=None)
    # 0 = ključna runa, 1–3 = vrstice manjših run; pri drevesih ni vrednosti.
    slot: Mapped[int | None] = mapped_column(SmallInteger, default=None)
