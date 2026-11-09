"""Potek analize aktivne tekme (ADR-0004): zajem → profiliranje → priporočila."""

import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.capture import capture_active_game
from app.analysis.enemy_comp import build_enemy_comp
from app.analysis.progress import ProgressNotifier, no_notify
from app.matchup.card import build_matchup_card
from app.matchup.power import phase_strength
from app.matchup.roles import role_distribution
from app.ml.build_ranker import load_active_build_ranker
from app.models.champion import Champion
from app.models.item import Item
from app.models.live_analysis import AnalysisStatus, LiveAnalysis
from app.profiling.archetypes import classify, load_active_archetypes
from app.profiling.baselines import load_baselines
from app.profiling.style import build_style_profile
from app.recommend.base import RecommendationInput, Recommender
from app.recommend.champion_stats import load_build_stats
from app.recommend.model import ModelRecommender
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
    analysis.style = profile_enemy_styles(session, riot, analysis)
    _set_status(session, analysis, AnalysisStatus.RECOMMENDING, notify)
    analysis.recommendation = recommend_build(
        session, analysis, recommender or default_recommender(session)
    )
    analysis.matchup = build_matchup(session, analysis)
    _set_status(session, analysis, AnalysisStatus.COMPLETED, notify)


def build_matchup(session: Session, analysis: LiveAnalysis, opponent_id: int | None = None) -> dict:
    """Matchup kartica za igralca; opponent_id je nasprotnik, ki ga je izbral igralec.

    ValueError, če izbrani šampion ni v nasprotni ekipi.
    """
    ids = [p["champion_id"] for p in analysis.participants]
    champions = {c.id: c for c in session.scalars(select(Champion).where(Champion.id.in_(ids)))}
    return build_matchup_card(
        analysis.participants,
        champions,
        role_distribution(session),
        opponent_id=opponent_id,
        phases=phase_strength(session),
    )


def profile_enemy_team(session: Session, analysis: LiveAnalysis) -> dict:
    """Profil nasprotne ekipe glede na igralca, ki se analizira."""
    champions, enemy_ids = _enemy_champions(session, analysis)
    return build_enemy_comp(champions, missing=len(enemy_ids) - len(champions))


def profile_enemy_styles(session: Session, riot: RiotClient, analysis: LiveAnalysis) -> dict:
    """Profil sloga vsakega nasprotnika (po puuid); {} brez mediane vlog v bazi."""
    baselines = load_baselines(session)
    if not baselines:
        return {}
    target_team = next((p["team_id"] for p in analysis.participants if p["is_target"]), None)
    spec = load_active_archetypes(session)
    profiles = {}
    for p in analysis.participants:
        if p["team_id"] == target_team or not p.get("puuid"):
            continue
        profile = build_style_profile(session, riot, p["puuid"], analysis.platform, baselines)
        if spec is not None and profile["matches"]:
            vs_median = {n: v["vs_median"] for n, v in profile["indicators"].items()}
            profile["archetype"] = asdict(classify(spec, vs_median))
        profiles[p["puuid"]] = profile
    return profiles


def _enemy_champions(session: Session, analysis: LiveAnalysis) -> tuple[list[Champion], list[int]]:
    """Nasprotni šampioni iz baze znanja in vsi ID-ji nasprotnikov."""
    target_team = next((p["team_id"] for p in analysis.participants if p["is_target"]), None)
    enemy_ids = [p["champion_id"] for p in analysis.participants if p["team_id"] != target_team]
    found = {c.id: c for c in session.scalars(select(Champion).where(Champion.id.in_(enemy_ids)))}
    return [found[i] for i in enemy_ids if i in found], enemy_ids


def default_recommender(session: Session) -> Recommender:
    """Aktivni model LightGBM s pravili kot rezervo (ADR-0006)."""
    return ModelRecommender(load_active_build_ranker(session), fallback=RuleBasedRecommender())


def recommend_build(
    session: Session, analysis: LiveAnalysis, recommender: Recommender
) -> dict | None:
    """Build za igralčevega šampiona; None, če šampiona ni v bazi znanja."""
    champion_id = next((p["champion_id"] for p in analysis.participants if p["is_target"]), None)
    champion = session.get(Champion, champion_id) if champion_id is not None else None
    if champion is None or analysis.enemy_comp is None:
        return None
    items = session.scalars(select(Item).where(Item.completed)).all()
    enemies, _ = _enemy_champions(session, analysis)
    return recommender.recommend(
        RecommendationInput(
            champion=champion,
            enemy_comp=analysis.enemy_comp,
            items=items,
            enemy_champions=enemies,
            build_stats=load_build_stats(session, champion.id),
        )
    )


def _set_status(
    session: Session, analysis: LiveAnalysis, status: AnalysisStatus, notify: ProgressNotifier
) -> None:
    analysis.status = status
    session.commit()
    notify(analysis.id)
