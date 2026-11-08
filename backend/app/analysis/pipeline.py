"""Potek analize aktivne tekme (ADR-0004): zajem → profiliranje → priporočila."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.capture import capture_active_game
from app.analysis.enemy_comp import build_enemy_comp
from app.analysis.progress import ProgressNotifier, no_notify
from app.models.champion import Champion
from app.models.item import Item
from app.models.live_analysis import AnalysisStatus, LiveAnalysis
from app.recommend.base import RecommendationInput, Recommender
from app.recommend.rules import RuleBasedRecommender
from app.riot.client import RiotClient


def run_analysis(
    session: Session,
    riot: RiotClient,
    analysis_id: uuid.UUID,
    notify: ProgressNotifier = no_notify,
    recommender: Recommender | None = None,
) -> None:
    if not capture_active_game(session, riot, analysis_id, notify):
        return

    analysis = session.get_one(LiveAnalysis, analysis_id)
    _set_status(session, analysis, AnalysisStatus.PROFILING, notify)
    analysis.enemy_comp = profile_enemy_team(session, analysis)
    _set_status(session, analysis, AnalysisStatus.RECOMMENDING, notify)
    analysis.recommendation = recommend_build(
        session, analysis, recommender or RuleBasedRecommender()
    )
    _set_status(session, analysis, AnalysisStatus.COMPLETED, notify)


def profile_enemy_team(session: Session, analysis: LiveAnalysis) -> dict:
    """Profil nasprotne ekipe glede na igralca, ki se analizira."""
    target_team = next((p["team_id"] for p in analysis.participants if p["is_target"]), None)
    enemy_ids = [p["champion_id"] for p in analysis.participants if p["team_id"] != target_team]
    found = {c.id: c for c in session.scalars(select(Champion).where(Champion.id.in_(enemy_ids)))}
    champions = [found[i] for i in enemy_ids if i in found]
    return build_enemy_comp(champions, missing=len(enemy_ids) - len(champions))


def recommend_build(
    session: Session, analysis: LiveAnalysis, recommender: Recommender
) -> dict | None:
    """Build za igralčevega šampiona; None, če šampiona ni v bazi znanja."""
    champion_id = next((p["champion_id"] for p in analysis.participants if p["is_target"]), None)
    champion = session.get(Champion, champion_id) if champion_id is not None else None
    if champion is None or analysis.enemy_comp is None:
        return None
    items = session.scalars(select(Item).where(Item.completed)).all()
    return recommender.recommend(
        RecommendationInput(champion=champion, enemy_comp=analysis.enemy_comp, items=items)
    )


def _set_status(
    session: Session, analysis: LiveAnalysis, status: AnalysisStatus, notify: ProgressNotifier
) -> None:
    analysis.status = status
    session.commit()
    notify(analysis.id)
