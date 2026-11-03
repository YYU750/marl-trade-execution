from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.qexperiment import run_qlearning_experiment  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-run the frozen Round 4 Q-learning protocol with behavior diagnostics.")
    parser.add_argument("--train-seeds", type=int, default=300)
    parser.add_argument("--validation-seeds", type=int, default=60)
    parser.add_argument("--test-seeds", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=20261103)
    parser.add_argument("--output", type=Path, default=ROOT / "results_round5_standard")
    args = parser.parse_args()
    if min(args.train_seeds, args.validation_seeds, args.test_seeds) < 2:
        raise SystemExit("each seed split must contain at least 2 seeds")
    for key, path in run_qlearning_experiment(
        args.output,
        train_count=args.train_seeds,
        validation_count=args.validation_seeds,
        test_count=args.test_seeds,
        seed_start=args.seed_start,
    ).items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
