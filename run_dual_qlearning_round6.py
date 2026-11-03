from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.dual_qexperiment import run_dual_experiment  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a bounded Independent Q-learning self-play study.")
    parser.add_argument("--baseline-q", type=Path, default=ROOT / "results_round5_standard" / "q_table_selected.json")
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "round6" / "dual_iql_20261103")
    parser.add_argument("--train-episodes", type=int, default=300)
    parser.add_argument("--test-episodes", type=int, default=100)
    parser.add_argument("--train-seed-start", type=int, default=20263103)
    parser.add_argument("--test-seed-start", type=int, default=20263403)
    args = parser.parse_args()
    if not args.baseline_q.is_file():
        raise SystemExit(f"Round 5 baseline Q table not found: {args.baseline_q}")
    run_dual_experiment(
        args.output, args.baseline_q, args.train_episodes, args.test_episodes,
        args.train_seed_start, args.test_seed_start,
    )
    print(f"ROUND6_COMPLETE output={args.output.resolve()}")


if __name__ == "__main__":
    main()
