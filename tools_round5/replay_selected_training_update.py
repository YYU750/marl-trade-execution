from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.models import SimulationConfig  # noqa: E402
from execution_sim.qexperiment import _episode  # noqa: E402
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the recorded first terminal update from the selected candidate.")
    parser.add_argument("--output", type=Path, default=ROOT / "audit_round5" / "selected_training_update_full.json")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite: {args.output}")
    agent = TabularQLearningAgent(
        QLearningConfig(alpha=0.30, epsilon_decay=0.99),
        seed=20261103 + 10_000 + 2,
    )
    _, trace, extra = _episode(
        agent,
        SimulationConfig(enforce_completion=True),
        seed=20261103,
        train=True,
        episode=1,
    )
    recorded = json.loads((ROOT / "results_round5_standard" / "selected_training_update.json").read_text(encoding="utf-8"))
    update = extra["first_update"]
    final_step = trace[-1]
    update_matches = update == recorded["update"]
    payload = {
        "status": "passed" if update_matches else "failed",
        "replay": {"candidate_id": 2, "alpha": 0.30, "epsilon_decay": 0.99, "agent_seed": 20271105,
                   "episode_seed": 20261103, "episode": 1, "step_count": len(trace)},
        "recorded_update_matches_replay": update_matches,
        "terminal_step": final_step,
        "interpretation": "At the final step with 10,000 remaining shares, the 0.0x action requests zero; enforce_completion fills the 10,000-share minimum. The recorded reward is generated from this actual environment transition.",
    }
    if not update_matches:
        raise AssertionError("replayed update differs from the standard result receipt")
    if final_step["action_multiplier"] != 0.0 or final_step["completion_constraint_shares"] != 10_000 or final_step["filled_shares"] != 10_000:
        raise AssertionError("terminal forced-fill trace did not match the expected environment constraint")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"REPLAY_OK update_matches={update_matches} forced_fill={final_step['completion_constraint_shares']} output={args.output.resolve()}")


if __name__ == "__main__":
    main()
