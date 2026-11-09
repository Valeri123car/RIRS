"""Kaj šampion v zbranih tekemah res kupuje: pogostost in zmage po dokončanih predmetih.

Pravila po oznakah predmetov ne poznajo šampionov, ki odstopajo od svojega razreda (Pyke je
»Support«, a gradi smrtonosnost). Zato so kandidati za priporočilo predmeti, ki jih igralci
tega šampiona v svoji najpogostejši vlogi res imajo ob koncu tekme (docs/ugotovitve.md,
poskus 8: build je odvisen predvsem od šampiona).
"""

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

# Pod tem številom iger šampiona v njegovi glavni vlogi se podatkom ne zaupa (rezerva: oznake).
MIN_GAMES = 30


@dataclass(frozen=True)
class BuildStats:
    games: int
    position: str
    # predmet -> (število iger z njim, zmage)
    items: dict[int, tuple[int, int]] = field(default_factory=dict)

    def pick_rate(self, item_id: int) -> float:
        return self.items.get(item_id, (0, 0))[0] / self.games if self.games else 0.0

    def win_rate(self, item_id: int, prior_games: int = 20) -> float:
        """Delež zmag z Bayesovim krčenjem k 50 %, da redek predmet ne izstopa po naključju."""
        count, wins = self.items.get(item_id, (0, 0))
        return (wins + prior_games / 2) / (count + prior_games)


def load_build_stats(session: Session, champion_id: int) -> BuildStats | None:
    """Statistika predmetov šampiona v njegovi najpogostejši vlogi; None brez dovolj iger."""
    row = session.execute(
        text(
            "SELECT position, count(*) FROM match_participants "
            "WHERE champion_id = :c AND position <> '' GROUP BY position "
            "ORDER BY count(*) DESC LIMIT 1"
        ),
        {"c": champion_id},
    ).first()
    if row is None or row[1] < MIN_GAMES:
        return None
    position, games = row
    items = session.execute(
        text(
            "SELECT it, count(*), sum(p.win::int) "
            "FROM match_participants p CROSS JOIN LATERAL unnest(p.items) AS it "
            "JOIN items i ON i.id = it AND i.completed "
            "WHERE p.champion_id = :c AND p.position = :pos GROUP BY it"
        ),
        {"c": champion_id, "pos": position},
    )
    return BuildStats(
        games=games, position=position, items={r[0]: (r[1], int(r[2])) for r in items}
    )
