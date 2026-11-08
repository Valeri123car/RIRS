"""SSE tok napredka analize (GET /analyses/{id}/events)."""

import json
import uuid

from app.analysis.progress import ProgressWaiter
from app.api.deps import get_progress_waiter_factory
from app.models.live_analysis import AnalysisStatus, LiveAnalysis


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def test_koncana_analiza_poslje_en_dogodek_in_zapre_tok(api):
    analysis_id = api.post("/analyses", json={"riot_id": "Luka#EUNE", "platform": "eun1"}).json()[
        "id"
    ]

    response = api.get(f"/analyses/{analysis_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [(name, data["status"]) for name, data in events] == [("progress", "completed")]
    assert len(events[0][1]["participants"]) == 10


class StepWaiter(ProgressWaiter):
    """Namesto delavca: ob vsakem čakanju premakne analizo za en korak naprej."""

    def __init__(self, db, analysis_id, steps):
        self.db, self.analysis_id, self.steps = db, analysis_id, list(steps)
        self.closed = False

    def wait(self, timeout):
        analysis = self.db.get(LiveAnalysis, self.analysis_id)
        analysis.status = self.steps.pop(0)
        self.db.commit()

    def close(self):
        self.closed = True


def test_tok_poslje_vsak_korak_do_koncnega_stanja(api, db):
    analysis = LiveAnalysis(game_name="Luka", tag_line="EUNE", platform="eun1")
    db.add(analysis)
    db.commit()
    waiter = StepWaiter(
        db,
        analysis.id,
        # dvakrat "capturing": nespremenjeno stanje se ne pošlje ponovno
        [AnalysisStatus.CAPTURING, AnalysisStatus.CAPTURING, AnalysisStatus.COMPLETED],
    )
    api.app.dependency_overrides[get_progress_waiter_factory] = lambda: lambda _id: waiter

    events = parse_sse(api.get(f"/analyses/{analysis.id}/events").text)

    assert [data["status"] for _, data in events] == ["pending", "capturing", "completed"]
    assert waiter.steps == []
    assert waiter.closed


def test_tok_neobstojece_analize(api):
    assert api.get(f"/analyses/{uuid.uuid4()}/events").status_code == 404
