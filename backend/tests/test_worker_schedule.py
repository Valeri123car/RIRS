import pytest
from pydantic import ValidationError

from app.collector.service import CollectorConfig
from app.core.config import Settings, get_settings
from app.worker import celery_app


def test_zbiralnik_je_v_urniku_enkrat_na_dan():
    entry = celery_app.conf.beat_schedule["zbiralnik-tekem-dnevno"]

    assert entry["task"] == "collector.run"
    schedule = entry["schedule"]
    assert schedule.hour == {get_settings().collector_hour_utc}
    assert schedule.minute == {0}
    assert schedule.day_of_week == set(range(7))
    assert "collector.run" in celery_app.tasks


def test_zbiralnik_ni_acks_late():
    # Dolg zagon se po poteku vidnosti v Redis ne sme dostaviti znova.
    assert celery_app.tasks["collector.run"].acks_late is False


def test_nastavitve_zbiralnika_iz_okolja(monkeypatch):
    monkeypatch.setenv("COLLECTOR_PLATFORM", "eun1")
    monkeypatch.setenv("COLLECTOR_MAX_PLAYERS", "2")
    monkeypatch.setenv("COLLECTOR_MAX_NEW_MATCHES", "5")
    monkeypatch.setenv("COLLECTOR_TIMELINES", "false")

    config = CollectorConfig.from_settings(Settings(_env_file=None), max_new_matches=3)

    assert config == CollectorConfig(
        platform="eun1", max_players=2, matches_per_player=20, max_new_matches=3, timelines=False
    )


@pytest.mark.parametrize(
    "values",
    [
        {"collector_platform": "xx9"},
        {"collector_max_players": 0},
        {"collector_matches_per_player": 101},
        {"collector_hour_utc": 24},
    ],
)
def test_neveljavne_nastavitve_zbiralnika_so_zavrnjene(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
