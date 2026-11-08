import enum
from typing import Any

from sqlalchemy import CheckConstraint, Enum, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values

# Ocene atributov šampionov so omejene na 0–3 (US-14).
RATING_MIN = 0
RATING_MAX = 3
RATED_ATTRIBUTES = ("cc", "healing", "engage", "burst", "tank", "poke")


class DamageProfile(enum.StrEnum):
    PHYSICAL = "physical"
    MAGIC = "magic"
    MIXED = "mixed"


def _rating_column() -> Mapped[int]:
    return mapped_column(SmallInteger, default=0, server_default="0")


class Champion(TimestampMixin, Base):
    """Baza znanja o šampionu: statični podatki iz Data Dragon in ročno urejene ocene."""

    __tablename__ = "champions"
    __table_args__ = tuple(
        CheckConstraint(f"{name} BETWEEN {RATING_MIN} AND {RATING_MAX}", name=f"{name}_range")
        for name in RATED_ATTRIBUTES
    )

    # Riot številčni ID (Data Dragon "key"), npr. 266 za Aatrox.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    # Data Dragon ime brez presledkov, npr. "MonkeyKing"; uporablja se za slike.
    slug: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    damage_profile: Mapped[DamageProfile] = mapped_column(
        Enum(DamageProfile, name="damage_profile", values_callable=enum_values),
        default=DamageProfile.MIXED,
        server_default=DamageProfile.MIXED.value,
    )
    # Riotovi razredi po pomembnosti, npr. ["Tank", "Fighter"]; osnova za pravila builda.
    classes: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list, server_default="{}")

    cc: Mapped[int] = _rating_column()
    healing: Mapped[int] = _rating_column()
    engage: Mapped[int] = _rating_column()
    burst: Mapped[int] = _rating_column()
    tank: Mapped[int] = _rating_column()
    poke: Mapped[int] = _rating_column()

    # Seznam oken moči, npr. [{"level": 6, "reason": "R"}].
    power_spikes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
