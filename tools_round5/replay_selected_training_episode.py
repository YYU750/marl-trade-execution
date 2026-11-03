from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.models import SimulationConfig  # noqa: E402
from execution_sim.qexperiment import _episode  # noqa: E402
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay one full recorded Q-learning training episode.")
    parser.add_argument("--output", type=Path, default=ROOT / "audit_round5" / "selected_training_episode_trace.csv")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")

    agent = TabularQLearningAgent(QLearningConfig(alpha=0.30, epsilon_decay=0.99), seed=20271105)
    _, trace, extra = _episode(agent, SimulationConfig(enforce_completion=True), 20261103, train=True, episode=1)
    recorded = json.loads((ROOT / "results_round5_standard" / "selected_training_update.json").read_text(encoding="utf-8"))
    if extra["first_update"] != recorded["update"]:
        raise AssertionError("replayed training episode does not match the selected training receipt")
    if len(trace) != 30 or any(not row["q_update"] for row in trace):
        raise AssertionError("expected 30 actual Q updates in the training episode")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trace[0]))
        writer.writeheader()
        writer.writerows(trace)
    print(f"EPISODE_REPLAY_OK steps={len(trace)} updates={sum(bool(row['q_update']) for row in trace)} first_update_matches=True output={output}")


if __name__ == "__main__":
    main()
