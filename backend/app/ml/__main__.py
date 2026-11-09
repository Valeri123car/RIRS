"""Učenje modela buildov iz zbranih tekem: uv run python -m app.ml [--activate]."""

import argparse
import sys

from app.db.session import get_session_factory
from app.ml.build_data import load_training_rows
from app.ml.build_ranker import (
    ActivationRefusedError,
    NotEnoughDataError,
    activate_build_ranker,
    save_build_ranker,
    train_build_ranker,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Učenje modela LightGBM za ocenjevanje buildov.")
    parser.add_argument(
        "--activate",
        action="store_true",
        help="takoj aktiviraj, če je prispevek sestave večji od odklona med delitvami",
    )
    args = parser.parse_args(argv)

    with get_session_factory()() as session:
        rows, patch = load_training_rows(session)
        try:
            trained = train_build_ranker(rows, patch or "neznan")
        except NotEnoughDataError as exc:
            print(f"Model ni naučen: {exc}", file=sys.stderr)
            return 1
        model = save_build_ranker(session, trained)
        session.commit()
        metrics = trained.metrics
        print(
            f"Model build_ranker v{model.version} (id {model.id}, patch {model.patch}): "
            f"AUC {metrics['auc']} ± {metrics['auc_std']}, izhodišče brez sestave "
            f"{metrics['baseline_auc']} ± {metrics['baseline_auc_std']}, prispevek sestave "
            f"{metrics['contribution']} (odklon {metrics['contribution_std']}), "
            f"log loss {metrics['log_loss']}, tekem {metrics['matches']}, "
            f"predmetov {metrics['items']}"
        )
        if not args.activate:
            return 0
        try:
            activate_build_ranker(session, model)
        except ActivationRefusedError as exc:
            print(f"Ni aktiviran: {exc}", file=sys.stderr)
            return 2
        session.commit()
        print("Model je aktiven in se uporablja za priporočila.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
