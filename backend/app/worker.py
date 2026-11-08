"""Celery delavci (ADR-0004): klici Riot API in dolgotrajno delo analiz.

Zagon: uv run celery -A app.worker worker --loglevel=info
"""

import uuid

from celery import Celery
from redis import Redis

from app.analysis.capture import capture_active_game
from app.analysis.progress import ProgressNotifier, RedisProgressNotifier, no_notify
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.riot.factory import build_riot_client


def _broker_url() -> str | None:
    redis_url = get_settings().redis_url
    return redis_url.get_secret_value() if redis_url else None


celery_app = Celery("rift_help", broker=_broker_url())
celery_app.conf.update(
    task_ignore_result=True,  # rezultat je v bazi (live_analyses), ne v Celery
    task_acks_late=True,  # ob padcu delavca se naloga ponovi
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

_riot_client = None


def _riot():
    global _riot_client
    if _riot_client is None:
        _riot_client = build_riot_client(get_settings())
    return _riot_client


_notifier: ProgressNotifier | None = None


def _notify() -> ProgressNotifier:
    global _notifier
    if _notifier is None:
        url = _broker_url()
        _notifier = RedisProgressNotifier(Redis.from_url(url)) if url else no_notify
    return _notifier


@celery_app.task(name="analysis.run")
def run_analysis(analysis_id: str) -> None:
    with get_session_factory()() as session:
        capture_active_game(session, _riot(), uuid.UUID(analysis_id), _notify())
