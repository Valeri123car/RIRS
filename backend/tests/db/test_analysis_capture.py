from app.analysis.capture import capture_active_game
from app.analysis.pipeline import run_analysis
from app.models.champion import Champion
from app.models.live_analysis import AnalysisStatus, LiveAnalysis
from app.riot.errors import RiotUnavailableError
from app.riot.fixture_client import FixtureRiotClient


def new_analysis(db, riot_id="Luka#EUNE", platform="eun1") -> LiveAnalysis:
    game_name, tag_line = riot_id.split("#")
    analysis = LiveAnalysis(game_name=game_name, tag_line=tag_line, platform=platform)
    db.add(analysis)
    db.flush()
    return analysis


def test_zajem_shrani_vseh_10_udelezencev_s_sampioni(db):
    db.merge(Champion(id=222, slug="Jinx", name="Jinx"))
    analysis = new_analysis(db)

    run_analysis(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.game_id is not None
    assert len(analysis.participants) == 10
    target = [p for p in analysis.participants if p["is_target"]]
    assert len(target) == 1
    assert target[0]["puuid"] == analysis.puuid
    assert (target[0]["champion_id"], target[0]["champion_name"]) == (222, "Jinx")
    assert {p["team_id"] for p in analysis.participants} == {100, 200}


def test_igralec_ni_v_tekmi(db):
    analysis = new_analysis(db, "Miha#EUNE")

    capture_active_game(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.NOT_IN_GAME
    assert analysis.error == "Igralec trenutno ni v tekmi"
    assert analysis.participants == []


def test_igralca_ni_v_regiji(db):
    analysis = new_analysis(db, "Sara#EUW", "eun1")

    capture_active_game(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.FAILED
    assert analysis.error == "Igralca s tem Riot ID ni v regiji EUNE"


def test_nedosegljiv_riot_api(db):
    class Unavailable(FixtureRiotClient):
        def get_active_game(self, puuid, platform):
            raise RiotUnavailableError("503")

    analysis = new_analysis(db)

    capture_active_game(db, Unavailable(), analysis.id)

    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.FAILED
    assert analysis.error == "Riot API trenutno ni dosegljiv, poskusi kasneje."


def test_analiza_obvesti_o_vsakem_koraku(db):
    analysis = new_analysis(db)
    statuses = []

    run_analysis(
        db, FixtureRiotClient(), analysis.id, notify=lambda _id: statuses.append(analysis.status)
    )

    assert statuses == [
        AnalysisStatus.CAPTURING,
        AnalysisStatus.PROFILING,
        AnalysisStatus.COMPLETED,
    ]


def test_neuspeh_zajema_obvesti_s_koncnim_stanjem(db):
    analysis = new_analysis(db, "Miha#EUNE")
    statuses = []

    capture_active_game(
        db, FixtureRiotClient(), analysis.id, notify=lambda _id: statuses.append(analysis.status)
    )

    assert statuses == [AnalysisStatus.CAPTURING, AnalysisStatus.NOT_IN_GAME]


def test_analiza_izracuna_profil_nasprotne_ekipe(db):
    analysis = new_analysis(db)

    run_analysis(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    comp = analysis.enemy_comp
    assert comp is not None
    assert comp["damage"]["physical"] + comp["damage"]["magic"] == 100
    assert comp["champion_count"] + comp["missing_champions"] == 5
    assert len(comp["threats"]) <= 5


def test_neuspel_zajem_nima_profila(db):
    analysis = new_analysis(db, "Miha#EUNE")

    run_analysis(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.NOT_IN_GAME
    assert analysis.enemy_comp is None
