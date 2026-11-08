"""Učni podatki za model buildov iz zbranih tekem (matches, match_participants)."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.build_features import TrainingRow, comp_vector
from app.models.champion import Champion
from app.models.item import Item
from app.models.match import Match, MatchParticipant

# Krajše tekme so remake ali zgodnja predaja: buildi v njih niso dokončani.
MIN_DURATION_S = 15 * 60


def load_training_rows(session: Session) -> tuple[list[TrainingRow], str | None]:
    """Vrstice za učenje in najnovejši patch med uporabljenimi tekmami."""
    champions = {c.id: c for c in session.scalars(select(Champion))}
    completed = set(session.scalars(select(Item.id).where(Item.completed)))

    result = session.execute(
        select(
            MatchParticipant.match_id,
            MatchParticipant.team_id,
            MatchParticipant.champion_id,
            MatchParticipant.position,
            MatchParticipant.items,
            MatchParticipant.win,
            Match.patch,
        )
        .join(Match, Match.match_id == MatchParticipant.match_id)
        .where(Match.duration_s >= MIN_DURATION_S)
        .order_by(MatchParticipant.match_id)
    )
    by_match: dict[str, list] = defaultdict(list)
    patches: set[str] = set()
    for row in result:
        by_match[row.match_id].append(row)
        patches.add(row.patch)

    rows: list[TrainingRow] = []
    for match_id, participants in by_match.items():
        for player in participants:
            enemies = [
                champions[p.champion_id]
                for p in participants
                if p.team_id != player.team_id and p.champion_id in champions
            ]
            rows.append(
                TrainingRow(
                    match_id=match_id,
                    champion_id=player.champion_id,
                    position=player.position or "",
                    comp=comp_vector(enemies),
                    items=tuple(i for i in player.items if i in completed),
                    win=player.win,
                )
            )
    latest = max(patches, key=_patch_key) if patches else None
    return rows, latest


def _patch_key(patch: str) -> tuple[int, ...]:
    return tuple(int(part) for part in patch.split(".") if part.isdigit())
