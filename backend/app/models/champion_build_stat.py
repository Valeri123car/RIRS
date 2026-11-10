from typing import Any

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChampionBuildStat(TimestampMixin, Base):
    """Predizračunani pravi buildi šampiona v glavni vlogi: rune, vrstni red nakupov, začetek.

    Izračun iz matches.raw (perks) in features.purchases je počasen, zato se izvede ob osvežitvi
    podatkov (`python -m app.recommend.precompute`), priporočilo pa prebere samo to vrstico.
    """

    __tablename__ = "champion_build_stats"

    champion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    position: Mapped[str] = mapped_column(String(16))
    games: Mapped[int] = mapped_column(Integer)
    # Najpogostejše strani run: [{primary_style, keystone, secondary_style, games, wins,
    # primary_perks, secondary_perks, shards}], padajoče po pogostosti.
    rune_pages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    # {item_id: {"median_s": ..., "n": ...}} za dokončane predmete.
    item_timing: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Najpogostejši začetni nakupi: {"items": [ids], "games": n, "wins": n}.
    start_items: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
