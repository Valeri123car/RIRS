from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StyleBaseline(TimestampMixin, Base):
    """Mediana kazalnika sloga za vlogo (iz vseh zbranih tekem); primerjalna osnova (US-06)."""

    __tablename__ = "style_baselines"

    # TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY.
    position: Mapped[str] = mapped_column(String(16), primary_key=True)
    indicator: Mapped[str] = mapped_column(String(32), primary_key=True)
    median: Mapped[float] = mapped_column(Float)
    # Število igralcev (tekem), iz katerih je mediana izračunana.
    sample: Mapped[int] = mapped_column(Integer)
