from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collector.service import CollectorConfig, collect_matches
from app.models.collector_run import CollectorRun, CollectorStatus
from app.models.match import Match, MatchParticipant
from app.models.riot_account import RiotAccount
from app.models.user import User
from app.riot.errors import RiotAuthError
from app.riot.fixture_client import FixtureRiotClient

# Fixtures: challenger liga euw1 ima 4 igralce, ki skupaj igrajo 3 različne tekme.
FIXTURE_MATCHES = {"EUW1_7100000001", "EUW1_7100000002", "EUW1_7100000003"}
CONFIG = CollectorConfig(platform="euw1", max_players=10, matches_per_player=20)


class CountingClient(FixtureRiotClient):
    """Fixture klient, ki šteje klice (preverjanje, da se tekme ne prenašajo znova)."""

    def __init__(self, fail_on_match: str | None = None) -> None:
        self.calls: list[str] = []
        self._fail_on_match = fail_on_match

    def get_match(self, match_id, platform):
        self.calls.append(f"match:{match_id}")
        if match_id == self._fail_on_match:
            raise RiotAuthError("Riot API ključ manjka, je neveljaven ali je potekel.")
        return super().get_match(match_id, platform)

    def get_match_timeline(self, match_id, platform):
        self.calls.append(f"timeline:{match_id}")
        return super().get_match_timeline(match_id, platform)


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_zagon_prenese_tekme_in_zapise_izid(db: Session):
    run = collect_matches(db, FixtureRiotClient(), CONFIG)

    assert run.status is CollectorStatus.SUCCESS
    assert run.new_matches == 3
    assert run.players == 4
    assert run.error is None
    assert run.started_at <= run.finished_at <= datetime.now(UTC)
    assert set(db.scalars(select(Match.match_id))) == FIXTURE_MATCHES
    assert _count(db, MatchParticipant) == 30

    match = db.get(Match, "EUW1_7100000002")
    assert (match.platform, match.queue_id, match.patch, match.winning_team) == (
        "euw1",
        420,
        "16.22",
        200,
    )
    assert match.raw["metadata"]["matchId"] == "EUW1_7100000002"
    participant = db.scalars(
        select(MatchParticipant).where(MatchParticipant.match_id == "EUW1_7100000002")
    ).first()
    assert set(participant.features) == {"cs_at_10", "xp_at_10", "gold_at_15", "deaths_before_14"}


def test_igralci_iz_tekem_so_racuni_brez_uporabnika(db: Session):
    collect_matches(db, FixtureRiotClient(), CONFIG)

    accounts = db.scalars(select(RiotAccount)).all()
    assert len(accounts) == 15 + 1  # 15 sintetičnih igralcev + Sara
    assert all(a.user_id is None and a.platform == "euw1" for a in accounts)


def test_povezan_racun_uporabnika_ostane_nespremenjen(db: Session):
    sara = FixtureRiotClient().get_account("Sara", "EUW", "euw1")
    user = User(email="sara@example.com", password_hash="x")
    db.add(user)
    db.flush()
    db.add(
        RiotAccount(
            puuid=sara.puuid,
            game_name="SaraNova",
            tag_line="1234",
            platform="euw1",
            user_id=user.id,
            verified_at=datetime.now(UTC),
        )
    )
    db.commit()

    collect_matches(db, FixtureRiotClient(), CONFIG)

    account = db.get(RiotAccount, sara.puuid)
    db.refresh(account)
    assert (account.game_name, account.user_id) == ("SaraNova", user.id)


def test_ponovni_zagon_ne_prenese_obstojecih_tekem(db: Session):
    collect_matches(db, FixtureRiotClient(), CONFIG)
    client = CountingClient()

    run = collect_matches(db, client, CONFIG)

    assert run.status is CollectorStatus.SUCCESS
    assert run.new_matches == 0
    assert client.calls == []
    assert _count(db, Match) == 3


def test_skupna_tekma_vec_igralcev_se_prenese_enkrat(db: Session):
    client = CountingClient()

    collect_matches(db, client, CONFIG)

    match_calls = [c for c in client.calls if c.startswith("match:")]
    assert sorted(match_calls) == sorted(f"match:{m}" for m in FIXTURE_MATCHES)


def test_omejitev_novih_tekem_na_zagon(db: Session):
    config = CollectorConfig(platform="euw1", max_players=10, max_new_matches=2)

    first = collect_matches(db, FixtureRiotClient(), config)
    second = collect_matches(db, FixtureRiotClient(), config)

    assert (first.new_matches, second.new_matches) == (2, 1)
    assert _count(db, Match) == 3


def test_omejitev_igralcev_vzame_najvisje_uvrscene(db: Session):
    # Najvišje LP ima Petra, ki je igrala samo tekmo ...003.
    run = collect_matches(db, FixtureRiotClient(), CollectorConfig(max_players=1))

    assert run.players == 1
    assert set(db.scalars(select(Match.match_id))) == {"EUW1_7100000003"}


def test_brez_casovnic_tekme_nimajo_znacilk(db: Session):
    client = CountingClient()

    collect_matches(db, client, CollectorConfig(timelines=False))

    assert not [c for c in client.calls if c.startswith("timeline:")]
    assert db.scalars(select(MatchParticipant.features)).all() == [None] * 30


def test_napaka_riot_api_zapise_izid_in_ohrani_prenesene_tekme(db: Session):
    # Petra (...003) se obdela prva, nato Marko (...002 in ...001).
    run = collect_matches(db, CountingClient(fail_on_match="EUW1_7100000002"), CONFIG)

    assert run.status is CollectorStatus.ERROR
    assert run.error == "Riot API ključ manjka, je neveljaven ali je potekel."
    assert run.finished_at is not None
    assert run.new_matches == 1
    assert set(db.scalars(select(Match.match_id))) == {"EUW1_7100000003"}
    stored = db.get(CollectorRun, run.id)
    assert stored.status is CollectorStatus.ERROR


def test_nepricakovana_napaka_ne_zapise_podrobnosti(db: Session):
    class Broken(FixtureRiotClient):
        def get_challenger_league(self, platform, queue="RANKED_SOLO_5x5"):
            raise RuntimeError("postgresql://uporabnik:skrivnost@baza")

    run = collect_matches(db, Broken(), CONFIG)

    assert run.status is CollectorStatus.ERROR
    assert run.error == "Nepričakovana napaka (RuntimeError)"
    assert run.new_matches == 0


def test_prekinjen_zagon_se_ob_naslednjem_oznaci_kot_napaka(db: Session):
    stale = CollectorRun(
        platform="euw1",
        status=CollectorStatus.RUNNING,
        started_at=datetime.now(UTC) - timedelta(hours=7),
    )
    recent = CollectorRun(platform="euw1", status=CollectorStatus.RUNNING)
    db.add_all([stale, recent])
    db.commit()

    collect_matches(db, FixtureRiotClient(), CONFIG)

    db.refresh(stale)
    db.refresh(recent)
    assert (stale.status, stale.error) == (CollectorStatus.ERROR, "Zagon je bil prekinjen.")
    assert stale.finished_at is not None
    assert recent.status is CollectorStatus.RUNNING
