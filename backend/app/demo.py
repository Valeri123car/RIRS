"""Testni (demo) podatki za predstavitev: python -m app.demo <e-pošta>.

Za obstoječega uporabnika ustvari povezan (preverjen) demo Riot račun in tri končane analize
aktivne tekme, da je mogoče predstaviti aplikacijo brez igralca, ki je trenutno v tekmi.
Analize niso ponarejene: profil sestave, priporočilo, matchup in profil sloga izračunajo
pravi moduli iz podatkov v bazi; izmišljena sta samo sestava ekip in imena igralcev
(»Nasprotnik N#DEMO«). Profil sloga vsakega nasprotnika je od pravega igralca iz zbranih
tekem, a brez njegovega Riot ID-ja. Ponovni zagon zamenja prejšnje demo analize.
"""

import sys
from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.analysis.pipeline import (
    build_matchup,
    default_recommender,
    profile_enemy_styles,
    profile_enemy_team,
    recommend_build,
)
from app.db.session import get_session_factory
from app.models.champion import Champion
from app.models.live_analysis import AnalysisStatus, LiveAnalysis
from app.models.riot_account import RiotAccount
from app.models.user import User

DEMO_TAG = "DEMO"
DEMO_PLATFORM = "euw1"
MIN_STYLE_MATCHES = 20

# Čarovnije: Flash, Ignite, Smite, Teleport, Heal, Exhaust.
FLASH, IGNITE, SMITE, TELEPORT, HEAL, EXHAUST = 4, 14, 11, 12, 7, 3

# (naslov, naša ekipa (prvi je igralec), nasprotniki); vsak vnos: (šampion, čarovnije)
SCENARIOS = [
    (
        "Pyke",
        [
            ("Pyke", (FLASH, IGNITE)),
            ("Jinx", (FLASH, HEAL)),
            ("Ahri", (FLASH, IGNITE)),
            ("Lee Sin", (FLASH, SMITE)),
            ("Ornn", (FLASH, TELEPORT)),
        ],
        [
            ("Leona", (FLASH, IGNITE)),
            ("Ezreal", (FLASH, HEAL)),
            ("Lissandra", (FLASH, IGNITE)),
            ("Vi", (FLASH, SMITE)),
            ("Garen", (FLASH, TELEPORT)),
        ],
    ),
    (
        "Jinx",
        [
            ("Jinx", (FLASH, HEAL)),
            ("Lulu", (FLASH, EXHAUST)),
            ("Syndra", (FLASH, IGNITE)),
            ("Hecarim", (FLASH, SMITE)),
            ("Ornn", (FLASH, TELEPORT)),
        ],
        [
            ("Caitlyn", (FLASH, HEAL)),
            ("Soraka", (FLASH, IGNITE)),
            ("Zed", (FLASH, IGNITE)),
            ("Sejuani", (FLASH, SMITE)),
            ("Aatrox", (FLASH, TELEPORT)),
        ],
    ),
    (
        "Ambessa",
        [
            ("Ambessa", (FLASH, TELEPORT)),
            ("Kai'Sa", (FLASH, HEAL)),
            ("Orianna", (FLASH, IGNITE)),
            ("Viego", (FLASH, SMITE)),
            ("Nautilus", (FLASH, EXHAUST)),
        ],
        [
            ("Malphite", (FLASH, TELEPORT)),
            ("Jhin", (FLASH, HEAL)),
            ("Ahri", (FLASH, IGNITE)),
            ("Amumu", (FLASH, SMITE)),
            ("Janna", (FLASH, EXHAUST)),
        ],
    ),
]


# Vloga nasprotnika: profil sloga je od pravega igralca, ki to vlogo večinoma igra.
ENEMY_ROLES = {
    "Garen": "TOP",
    "Malphite": "TOP",
    "Aatrox": "TOP",
    "Vi": "JUNGLE",
    "Sejuani": "JUNGLE",
    "Amumu": "JUNGLE",
    "Lissandra": "MIDDLE",
    "Zed": "MIDDLE",
    "Ahri": "MIDDLE",
    "Ezreal": "BOTTOM",
    "Caitlyn": "BOTTOM",
    "Jhin": "BOTTOM",
    "Leona": "UTILITY",
    "Soraka": "UTILITY",
    "Janna": "UTILITY",
}
DOMINANT_SHARE = 0.7


class DemoError(RuntimeError):
    """Demo podatkov ni mogoče pripraviti (npr. uporabnik ali podatki ne obstajajo)."""


def seed_demo(session: Session, email: str) -> list[LiveAnalysis]:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        raise DemoError(f"Uporabnik {email} ne obstaja (najprej se registriraj).")
    champions = {c.name: c for c in session.scalars(select(Champion))}
    missing = {n for _, ours, theirs in SCENARIOS for n, _ in ours + theirs} - champions.keys()
    if missing:
        raise DemoError(f"Šampioni niso v bazi (python -m app.ddragon): {sorted(missing)}")

    account = _demo_account(session, user)
    session.execute(
        delete(LiveAnalysis).where(
            LiveAnalysis.user_id == user.id, LiveAnalysis.tag_line == DEMO_TAG
        )
    )
    pools = _style_puuids(session, len(SCENARIOS))

    analyses = []
    for index, (title, ours, theirs) in enumerate(SCENARIOS):
        analysis = LiveAnalysis(
            user_id=user.id,
            game_name=f"Demo {title}",
            tag_line=DEMO_TAG,
            platform=DEMO_PLATFORM,
            puuid=account.puuid,
            game_id=9_000_000_000 + index,
            status=AnalysisStatus.COMPLETED,
            participants=_participants(
                champions,
                ours,
                theirs,
                account.puuid,
                [pools[ENEMY_ROLES[name]][index] for name, _ in theirs],
            ),
        )
        session.add(analysis)
        session.flush()
        analysis.enemy_comp = profile_enemy_team(session, analysis)
        analysis.style = profile_enemy_styles(session, None, analysis)
        analysis.recommendation = recommend_build(session, analysis, default_recommender(session))
        analysis.matchup = build_matchup(session, analysis)
        analyses.append(analysis)
    session.commit()
    return analyses


def _demo_account(session: Session, user: User) -> RiotAccount:
    puuid = f"demo-puuid-{user.id}"
    account = session.get(RiotAccount, puuid)
    if account is None:
        account = RiotAccount(
            puuid=puuid,
            game_name="DemoIgralec",
            tag_line=DEMO_TAG,
            platform=DEMO_PLATFORM,
            user_id=user.id,
            verified_at=datetime.now(UTC),
        )
        session.add(account)
        session.flush()
    return account


def _style_puuids(session: Session, per_role: int) -> dict[str, list[str]]:
    """Pravi igralci iz zbranih tekem po vlogi: vsaj 20 tekem, večino v tej vlogi."""
    pools: dict[str, list[str]] = {}
    for role in sorted(set(ENEMY_ROLES.values())):
        rows = session.execute(
            text(
                "SELECT puuid FROM ("
                " SELECT puuid, count(*) AS total,"
                "  count(*) FILTER (WHERE position = :role) AS in_role"
                " FROM match_participants GROUP BY puuid) t"
                " WHERE total >= :min AND in_role >= :share * total"
                " ORDER BY md5(puuid) LIMIT :n"
            ),
            {"role": role, "min": MIN_STYLE_MATCHES, "share": DOMINANT_SHARE, "n": per_role},
        ).scalars()
        pools[role] = list(rows)
        if len(pools[role]) < per_role:
            raise DemoError(f"V bazi je premalo igralcev z vlogo {role} za demo.")
    return pools


def _participants(champions, ours, theirs, target_puuid, enemy_puuids) -> list[dict]:
    result = []
    for index, (name, spells) in enumerate(ours):
        puuid = target_puuid if index == 0 else f"demo-ally-{name}"
        result.append(_entry(champions[name], spells, puuid, 100, f"Zaveznik {index}", index == 0))
    for index, ((name, spells), puuid) in enumerate(zip(theirs, enemy_puuids, strict=True), 1):
        result.append(_entry(champions[name], spells, puuid, 200, f"Nasprotnik {index}", False))
    return result


def _entry(champion, spells, puuid, team_id, label, is_target) -> dict:
    return {
        "puuid": puuid,
        "riot_id": "DemoIgralec#DEMO" if is_target else f"{label}#{DEMO_TAG}",
        "team_id": team_id,
        "champion_id": champion.id,
        "champion_name": champion.name,
        "champion_slug": champion.slug,
        "spell1_id": spells[0],
        "spell2_id": spells[1],
        "is_target": is_target,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Uporaba: python -m app.demo <e-pošta>", file=sys.stderr)
        return 2
    with get_session_factory()() as session:
        try:
            analyses = seed_demo(session, args[0].strip().lower())
        except DemoError as exc:
            print(exc, file=sys.stderr)
            return 1
        for analysis in analyses:
            print(f"{analysis.game_name}: /analiza/{analysis.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
