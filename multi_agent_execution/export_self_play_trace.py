#!/usr/bin/env python3
"""Export one synchronized A/B learning episode from a saved self-play checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_advanced_self_play import DEFAULT_OUT, SCENARIOS, episode, write_csv
from run_standard_benchmark import Config
from schedule_aware_q import LimitOrderAwareQLearningAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a step-by-step simultaneous A/B Q-learning trace."
    )
    parser.add_argument("--checkpoint-file", type=Path,
                        default=DEFAULT_OUT / "checkpoint_qtables_run1.json")
    parser.add_argument("--checkpoint", type=int, default=500,
                        help="saved training checkpoint episode")
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--schedule-deficit-penalty-bps", type=float, default=10.0)
    parser.add_argument("--terminal-unfilled-penalty-bps", type=float, default=1_000.0)
    parser.add_argument("--scenario", choices=[name for name, _ in SCENARIOS], default="normal")
    parser.add_argument("--output", type=Path,
                        default=DEFAULT_OUT / "sample_simultaneous_learning_trace.csv")
    return parser.parse_args()


def agent_from_payload(config: Config, payload: dict[str, Any]) -> LimitOrderAwareQLearningAgent:
    if payload.get("state_encoding") not in (
        None, LimitOrderAwareQLearningAgent.state_encoding,
    ):
        raise ValueError(
            "Checkpoint uses a different state encoding; provide a checkpoint "
            "from outputs/advanced_self_play_limit_orders."
        )
    agent = LimitOrderAwareQLearningAgent(config, opponent_aware=True)
    agent.q = {
        tuple(int(value) for value in state.split("|")): [float(q) for q in values]
        for state, values in payload["q"].items()
    }
    agent.action_visits = {
        tuple(int(value) for value in state.split("|")): [int(count) for count in counts]
        for state, counts in payload["action_visits"].items()
    }
    return agent


def main() -> None:
    args = parse_args()
    if args.fee_bps < 0:
        raise SystemExit("--fee-bps cannot be negative")
    if args.schedule_deficit_penalty_bps < 0 or args.terminal_unfilled_penalty_bps < 0:
        raise SystemExit("completion penalty coefficients cannot be negative")
    if not args.checkpoint_file.is_file():
        raise SystemExit(
            f"Checkpoint file not found: {args.checkpoint_file}. Run run_experiment.py first."
        )

    all_checkpoints = json.loads(args.checkpoint_file.read_text(encoding="utf-8"))
    checkpoint_key = str(args.checkpoint)
    if checkpoint_key not in all_checkpoints:
        raise SystemExit(f"Checkpoint {args.checkpoint} is absent from {args.checkpoint_file}")

    config = Config(
        inventory_risk_weight=0.0,
        schedule_deficit_penalty_bps=args.schedule_deficit_penalty_bps,
        terminal_unfilled_penalty_bps=args.terminal_unfilled_penalty_bps,
    )
    checkpoint = all_checkpoints[checkpoint_key]
    agent_a = agent_from_payload(config, checkpoint["A"])
    agent_b = agent_from_payload(config, checkpoint["B"])
    volatility_multiplier = dict(SCENARIOS)[args.scenario]
    trace_rows: list[dict[str, Any]] = []
    episode_result = episode(
        agent_a, agent_b, config, args.seed, args.fee_bps, volatility_multiplier,
        epsilon=0.0, training=True, trace_rows=trace_rows,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, trace_rows)
    try:
        checkpoint_label = args.checkpoint_file.resolve().relative_to(
            Path(__file__).resolve().parent
        ).as_posix()
    except ValueError:
        checkpoint_label = args.checkpoint_file.name
    summary = {
        "trace_type": "illustrative simultaneous A/B learning trajectory",
        "not_part_of_aggregate_evaluation": True,
        "source_checkpoint_file": checkpoint_label,
        "checkpoint_episode": args.checkpoint,
        "seed": args.seed,
        "scenario": args.scenario,
        "fee_bps_one_way": args.fee_bps,
        "schedule_deficit_penalty_coefficient_bps": args.schedule_deficit_penalty_bps,
        "terminal_residual_penalty_coefficient_bps": args.terminal_unfilled_penalty_bps,
        "window_minutes": config.window_minutes,
        "step_seconds": config.step_seconds,
        "steps": config.horizon,
        "order_size_per_agent_shares": config.order_size,
        "A_cost_bps": episode_result["cost_A_bps"],
        "B_cost_bps": episode_result["cost_B_bps"],
        "A_completion": episode_result["completion_A"],
        "B_completion": episode_result["completion_B"],
        "A_filled_shares": episode_result["filled_A"],
        "B_filled_shares": episode_result["filled_B"],
        "A_unfilled_shares": episode_result["unfilled_A"],
        "B_unfilled_shares": episode_result["unfilled_B"],
        "completion_mode": "autonomous",
        "A_forced_completion_shares": episode_result["forced_completion_A"],
        "B_forced_completion_shares": episode_result["forced_completion_B"],
        "A_schedule_deficit_penalty_bps": episode_result["schedule_deficit_penalty_A_bps"],
        "B_schedule_deficit_penalty_bps": episode_result["schedule_deficit_penalty_B_bps"],
        "A_terminal_residual_penalty_bps": episode_result["terminal_residual_penalty_A_bps"],
        "B_terminal_residual_penalty_bps": episode_result["terminal_residual_penalty_B_bps"],
        "A_forced_completion_cost_contribution_bps": episode_result[
            "forced_completion_cost_contribution_A_bps"
        ],
        "B_forced_completion_cost_contribution_bps": episode_result[
            "forced_completion_cost_contribution_B_bps"
        ],
        "note": (
            "Both actions are selected from the same pre-trade snapshot. The saved checkpoint is "
            "loaded into temporary mutable copies; these 60 steps demonstrate online Q updates "
            "with queue-dependent partial fills and agent-controlled intraday actions. The "
            "synthetic terminal backstop, not the Q policy alone, guarantees completion; this "
            "illustration is excluded from the main cross-play statistics."
        ),
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Trace written to {args.output.resolve()}")
    print(f"Summary written to {summary_path.resolve()}")


if __name__ == "__main__":
    main()
