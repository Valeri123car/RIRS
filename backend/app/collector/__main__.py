"""Ročni zagon zbiralnika: uv run python -m app.collector [--players 2 --matches 5].

Ponoven prenos časovnic obstoječih tekem (nove značilke):
uv run python -m app.collector --platform euw1 --backfill-timelines --matches 500
"""

import argparse
import logging
import sys

from app.collector.service import CollectorConfig, backfill_timelines, collect_matches
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.collector_run import CollectorStatus
from app.riot.errors import RiotConfigError
from app.riot.factory import build_riot_client
from app.riot.platforms import PLATFORM_TO_REGION


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("mora biti vsaj 1")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prenos novih rangiranih tekem (Riot API).")
    parser.add_argument("--platform", choices=sorted(PLATFORM_TO_REGION), help="npr. euw1")
    parser.add_argument("--players", type=_positive, help="največ challenger igralcev")
    parser.add_argument("--per-player", type=_positive, help="ID-jev tekem na igralca (1–100)")
    parser.add_argument("--matches", type=_positive, help="največ novih tekem v zagonu")
    parser.add_argument("--no-timelines", action="store_true", help="brez časovnic")
    parser.add_argument(
        "--backfill-timelines",
        action="store_true",
        help="namesto zajema dopolni značilke časovnic obstoječih tekem (največ --matches)",
    )
    args = parser.parse_args(argv)
    if args.per_player is not None and args.per_player > 100:
        parser.error("--per-player je lahko največ 100")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    config = CollectorConfig.from_settings(
        settings,
        platform=args.platform,
        max_players=args.players,
        matches_per_player=args.per_player,
        max_new_matches=args.matches,
        timelines=False if args.no_timelines else None,
    )

    try:
        riot = build_riot_client(settings)
    except RiotConfigError as exc:
        print(f"Zbiralnik ni zagnan: {exc}", file=sys.stderr)
        return 1
    if args.backfill_timelines:
        with get_session_factory()() as session:
            updated = backfill_timelines(
                session, riot, platform=config.platform, limit=config.max_new_matches
            )
        print(f"Dopolnjene časovnice ({config.platform}): {updated} tekem")
        return 0

    with get_session_factory()() as session:
        run = collect_matches(session, riot, config)

    duration = (run.finished_at - run.started_at).total_seconds() if run.finished_at else 0
    print(
        f"Zagon #{run.id} ({run.platform}): {run.status.value}, igralcev {run.players}, "
        f"novih tekem {run.new_matches}, trajanje {duration:.0f} s"
    )
    if run.status is CollectorStatus.ERROR:
        print(f"Napaka: {run.error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
