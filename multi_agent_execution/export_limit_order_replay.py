#!/usr/bin/env python3
"""Export frozen limit-order replays for both volatility scenarios."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from export_self_play_trace import agent_from_payload
from run_advanced_self_play import ACTION_NAMES, DEFAULT_OUT, LOB_CONFIG, SCENARIOS, episode
from run_standard_benchmark import ACTIONS, Config
from schedule_aware_q import LimitOrderAwareQLearningAgent


AGENTS = ("A", "B")
ORDER_FIELDS = {
    "open_before": "open_order_remaining_before",
    "open_after": "open_order_remaining_after",
    "queue_ahead_before": "queue_ahead_before",
    "queue_ahead_after": "queue_ahead_after",
    "maker_filled": "maker_filled_qty",
    "taker_filled": "taker_filled_qty",
    "replaced": "replaced_order_cancelled_qty",
    "expired": "expired_order_cancelled_qty",
    "ioc_cancelled": "ioc_remainder_cancelled_qty",
    "deadline_cancelled": "deadline_cancelled_qty",
}


def policy_hash(agent: LimitOrderAwareQLearningAgent) -> str:
    states = sorted(set(agent.q) | set(agent.action_visits))
    values = [(key, agent.q.get(key), agent.action_visits.get(key)) for key in states]
    return sha256(json.dumps(values, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def serialize_agent(row: dict, agent: LimitOrderAwareQLearningAgent, config: Config) -> dict:
    state = tuple(map(int, row["state_key"].split("|")))
    chosen = ACTION_NAMES.index(row["action"])
    values = agent.q.get(state, [0.0] * len(ACTIONS))
    visits = agent.action_visits.get(state, [0] * len(ACTIONS))
    tried = [index for index, count in enumerate(visits) if count > 0]
    ties = sum(abs(values[index] - values[chosen]) < 1e-12 for index in tried)
    if (tried and (chosen not in tried or max(values[i] for i in tried) - values[chosen] >= 1e-12)
            or not tried and chosen != 2):
        raise ValueError("Replay action does not match its frozen checkpoint")
    remaining = row["remaining_before_shares"]
    steps_left = config.horizon - row["step"] + 1
    costs = {key: row[f"{key}_cost_bps"] for key in ("price_drift", "quote_offset", "temporary_impact", "fee")}
    if not isclose(sum(costs.values()), -row["weighted_step_reward"], abs_tol=1e-8):
        raise ValueError("Per-step cost components do not reconcile")
    return {
        "observation": {
            "own_remaining_shares": remaining,
            "seconds_remaining": steps_left * config.step_seconds,
            "price_deviation_bps": (row["mid_before"] / config.initial_price - 1) * 10_000,
            "pace_ratio_vs_remaining_twap": remaining / (config.base_slice * steps_left),
            "opponent_previous_quantity": row["opponent_previous_qty"],
            "state_key": state,
        },
        "decision": {
            "mode": ("greedy_q_over_tried_feasible_actions" if tried
                     else "twap_fallback_no_tried_feasible_action"),
            "selected_action": row["action"],
            "selected_quantity_shares": row["submitted_qty"],
            "selected_q_value": values[chosen] if tried else None,
            "greedy_tie_count": ties,
            "all_action_q_values": values,
            "all_action_visit_counts": visits,
            "feasible_actions": [
                {"index": index, "quantity_shares": min(remaining, config.base_slice * multiple),
                 "twap_multiple": multiple}
                for index, multiple in enumerate(ACTIONS)
            ],
        },
        "execution": {
            "fill_price_including_fee": row["fill_price_including_fee"],
            "weighted_step_shortfall_bps": -row["weighted_step_reward"],
            "cost_components_bps_of_parent_order": costs,
            "actual_filled_quantity_shares": row["actual_filled_qty"],
            "forced_completion_quantity_shares": row["forced_completion_qty"],
            "limit_order": {
                "type": row["order_type"],
                "limit_price": row["limit_price"],
                **{name: row[source] for name, source in ORDER_FIELDS.items()},
            },
        },
    }


def build_replay(checkpoint: dict, args: argparse.Namespace, scenario: str, multiplier: float) -> dict:
    config = Config(inventory_risk_weight=0.0)
    policies = {name: agent_from_payload(config, checkpoint[name]) for name in AGENTS}
    before = {name: policy_hash(agent) for name, agent in policies.items()}
    rows: list[dict] = []
    result = episode(policies["A"], policies["B"], config, args.seed, args.fee_bps,
                     multiplier, epsilon=0.0, training=False, trace_rows=rows, completion_mode=args.completion_mode)
    after = {name: policy_hash(agent) for name, agent in policies.items()}
    if before != after or len(rows) != config.horizon * len(AGENTS):
        raise ValueError("Invalid frozen replay")

    steps = []
    for step in range(config.horizon):
        pair = rows[step * 2:step * 2 + 2]
        a = pair[0]
        agents = {row["agent"]: serialize_agent(row, policies[row["agent"]], config) for row in pair}
        market = {key: a[key] for key in (
            "mid_before", "mid_after", "external_shock_bps", "permanent_impact_bps",
            "temporary_impact_bps", "half_spread_bps", "one_way_fee_bps",
        )}
        market["joint_submitted_quantity_shares"] = sum(row["submitted_qty"] for row in pair)
        market["joint_actual_filled_quantity_shares"] = a["joint_actual_filled_qty"]
        steps.append({"step": step + 1, "elapsed_seconds": a["elapsed_seconds"],
                      "agents": agents, "market_transition": market})

    summary: dict = {"cost_reconciliation": {}}
    for name in AGENTS:
        traded_cost = sum(step["agents"][name]["execution"]["weighted_step_shortfall_bps"] for step in steps)
        unfilled = result[f"unfilled_{name}"]
        opportunity = (unfilled / config.order_size
                       * (steps[-1]["market_transition"]["mid_after"] / config.initial_price - 1) * 10_000)
        cost = result[f"cost_{name}_bps"]
        if not isclose(traded_cost + opportunity, cost, abs_tol=1e-8):
            raise ValueError(f"Episode costs for {name} do not reconcile")
        summary.update({
            f"{name}_cost_bps": cost,
            f"{name}_completion_rate": result[f"completion_{name}"],
            f"{name}_unfilled_shares": unfilled,
            f"{name}_forced_completion_shares": result[f"forced_completion_{name}"],
            f"{name}_forced_completion_cost_bps": result[f"forced_completion_cost_contribution_{name}_bps"],
            f"{name}_action_counts": json.loads(result[f"actions_{name}"]),
        })
        summary["cost_reconciliation"][name] = {
            "sum_of_step_shortfalls_bps": traded_cost,
            "reported_total_cost_bps": cost,
            "residual_opportunity_cost_bps": opportunity,
        }
    return {
        "schema_version": "2.0",
        "demo_type": "frozen_limit_order_replay",
        "completion_mode": args.completion_mode,
        "source_ref": args.source_ref,
        "checkpoint_episode": args.checkpoint,
        "seed": args.seed,
        "scenario": scenario,
        "training_updates_applied": False,
        "epsilon": 0,
        "policy_table_sha256_before": before,
        "policy_table_sha256_after": after,
        "config": {
            "asset_symbol": "SIM-ASSET-01",
            "side": "BUY",
            "window_minutes": config.window_minutes,
            "step_seconds": config.step_seconds,
            "horizon_steps": config.horizon,
            "order_size_per_agent_shares": config.order_size,
            "initial_mid_price": config.initial_price,
            "one_way_fee_bps": args.fee_bps,
            "quote_ttl_steps": LOB_CONFIG.quote_ttl_steps,
        },
        "steps": steps,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-file", type=Path)
    parser.add_argument("--completion-mode", choices=("autonomous", "none"), default="autonomous")
    parser.add_argument("--checkpoint", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261105)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--source-ref", default="limit-order-self-play")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.fee_bps < 0:
        parser.error("--fee-bps must be nonnegative")
    output = DEFAULT_OUT if args.completion_mode == "autonomous" else DEFAULT_OUT.with_name("advanced_self_play_no_completion")
    checkpoint_file = args.checkpoint_file or output / "checkpoint_qtables_run1.json"
    checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))[str(args.checkpoint)]
    if any(checkpoint[name].get("state_encoding") != LimitOrderAwareQLearningAgent.state_encoding for name in AGENTS):
        parser.error("expected a limit-order checkpoint")
    replays = [(name, build_replay(checkpoint, args, name, multiplier)) for name, multiplier in SCENARIOS]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, replay in replays:
        path = args.output_dir / f"limit_replay_{name}.json"
        path.write_text(json.dumps(replay, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
                        encoding="utf-8")
        print(f"{path}: {len(replay['steps'])} steps, frozen hashes unchanged")


if __name__ == "__main__":
    main()
