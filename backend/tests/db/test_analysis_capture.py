from sqlalchemy import delete

from app.analysis.capture import capture_active_game
from app.analysis.pipeline import run_analysis
from app.models.champion import Champion
from app.models.item import Item
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
        AnalysisStatus.RECOMMENDING,
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
    assert analysis.recommendation is None


def add_marksman_items(db):
    # Visoki ID-ji, da se ne prekrivajo z uvoženimi predmeti Data Dragon.
    for item_id, name, tags in [
        (9031, "Test Infinity Edge", ["critical_strike", "damage"]),
        (9072, "Test Bloodthirster", ["damage", "life_steal"]),
        (9046, "Test Phantom Dancer", ["attack_speed", "critical_strike"]),
        (9036, "Test Lord Dominik's", ["armor_pen", "critical_strike", "damage"]),
        (9139, "Test Mercurial", ["damage", "spell_block", "tenacity"]),
        (9026, "Test Guardian Angel", ["armor", "damage"]),
    ]:
        db.merge(Item(id=item_id, name=name, cost=3000, tags=tags, completed=True))


def test_analiza_priporoci_build_po_pravilih(db):
    db.merge(Champion(id=222, slug="Jinx", name="Jinx", classes=["Marksman"]))
    add_marksman_items(db)
    analysis = new_analysis(db)

    run_analysis(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    recommendation = analysis.recommendation
    assert recommendation["source"] == "rules"
    assert recommendation["label"] == "Priporočilo na podlagi pravil"
    assert recommendation["champion"] == {"id": 222, "name": "Jinx"}
    assert 2 <= len(recommendation["variants"]) <= 3


def test_brez_sampiona_v_bazi_znanja_analiza_konca_brez_priporocila(db):
    db.execute(delete(Champion).where(Champion.id == 222))
    analysis = new_analysis(db)

    run_analysis(db, FixtureRiotClient(), analysis.id)

    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.recommendation is None
