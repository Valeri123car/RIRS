"""Uvoz patcha iz Data Dragon: uv run python -m app.ddragon [--version 16.22.1]."""

import argparse
import sys

from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.ddragon.client import DataDragonClient, DataDragonError
from app.ddragon.importer import ImportResult, import_static_data
from app.ddragon.parse import parse_champions, parse_items


def run_import(
    session: Session, client: DataDragonClient, version: str | None = None
) -> tuple[str, ImportResult]:
    """Prenese in uvozi podatke; brez verzije vzame zadnjo. Ne potrdi transakcije."""
    version = version or client.latest_version()
    champions = parse_champions(client.champions(version))
    items = parse_items(client.items(version))
    return version, import_static_data(session, champions, items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uvoz šampionov in predmetov iz Data Dragon.")
    parser.add_argument("--version", help="verzija patcha, npr. 16.22.1 (privzeto zadnja)")
    args = parser.parse_args(argv)

    with get_session_factory()() as session:
        try:
            version, result = run_import(session, DataDragonClient(), args.version)
        except (DataDragonError, ValueError) as exc:
            print(f"Uvoz ni uspel: {exc}", file=sys.stderr)
            return 1
        session.commit()

    for label, counts in (("Šampioni", result.champions), ("Predmeti", result.items)):
        print(
            f"{label}: novih {counts.created}, spremenjenih {counts.updated}, "
            f"nespremenjenih {counts.unchanged}"
        )
    print(f"Uvožen patch {version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
