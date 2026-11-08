from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Match(TimestampMixin, Base):
    """Odigrana rangirana tekma (Match-V5). Končana tekma se ne spreminja (ADR-0005)."""

    __tablename__ = "matches"

    # Riotov ID, npr. "EUW1_7100000001".
    match_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    platform: Mapped[str] = mapped_column(String(8))
    queue_id: Mapped[int] = mapped_column(Integer)
    # "16.22" iz gameVersion "16.22.734.5678"; po njem se učni podatki delijo po patchih.
    patch: Mapped[str] = mapped_column(String(16), index=True)
    game_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int] = mapped_column(Integer)
    winning_team: Mapped[int] = mapped_column(SmallInteger)
    # Celoten odgovor Match-V5 (brez časovnice), da se značilke lahko kasneje izračunajo znova.
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)


class MatchParticipant(Base):
    """Igralec v tekmi: statistika in značilke (učni podatki za modele)."""

    __tablename__ = "match_participants"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.match_id", ondelete="CASCADE"), primary_key=True
    )
    # Indeks za iskanje zadnjih tekem igralca (profil sloga, US-06).
    puuid: Mapped[str] = mapped_column(
        ForeignKey("riot_accounts.puuid"), primary_key=True, index=True
    )
    team_id: Mapped[int] = mapped_column(SmallInteger)
    champion_id: Mapped[int] = mapped_column(Integer, index=True)
    # TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY (prazno, če Riot vloge ne določi).
    position: Mapped[str] = mapped_column(String(16))
    kills: Mapped[int] = mapped_column(SmallInteger)
    deaths: Mapped[int] = mapped_column(SmallInteger)
    assists: Mapped[int] = mapped_column(SmallInteger)
    # ID-ji predmetov item0–item6 (brez praznih mest); brez tujega ključa, glej docs/03.
    items: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    win: Mapped[bool]
    # Značilke iz časovnice (cs_at_10, gold_at_15, xp_at_10, deaths_before_14); None brez nje.
    features: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
