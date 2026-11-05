#!/usr/bin/env python3
"""Export a verified frozen A/B Q-learning episode for the course front end."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_advanced_self_play import (
    ACTION_NAMES,
    DEFAULT_OUT,
    SCENARIOS,
    episode,
    frozen_action,
)
from run_standard_benchmark import (
    ACTIONS,
    Config,
    feasible_action_floor,
    make_observation,
)
from schedule_aware_q import ScheduleAwareQLearningAgent

ROOT = Path(__file__).resolve().parent
DEMO_DIR = DEFAULT_OUT / "demo_frozen"
ACTION_LABELS = {
    "wait": "等待",
    "half": "半份 TWAP",
    "base": "基准 TWAP",
    "one_and_half": "1.5 倍 TWAP",
    "double": "2 倍 TWAP",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-file", type=Path,
                        default=DEFAULT_OUT / "checkpoint_qtables_run1.json")
    parser.add_argument("--checkpoint", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261105)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--scenario", choices=[name for name, _ in SCENARIOS],
                        default="normal")
    parser.add_argument("--output", type=Path,
                        default=DEMO_DIR / "demo_frozen_episode.json")
    parser.add_argument("--config-output", type=Path, default=None,
                        help="Optional path for the replay configuration receipt")
    parser.add_argument("--source-ref", default="wuxinhan-1@79dab6f")
    return parser.parse_args()


def sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def agent_from_payload(config: Config, payload: dict[str, Any]) -> ScheduleAwareQLearningAgent:
    agent = ScheduleAwareQLearningAgent(config, opponent_aware=True)
    agent.q = {
        tuple(int(value) for value in state.split("|")): [float(q) for q in values]
        for state, values in payload["q"].items()
    }
    agent.action_visits = {
        tuple(int(value) for value in state.split("|")): [int(n) for n in counts]
        for state, counts in payload["action_visits"].items()
    }
    agent.freeze()
    return agent


def table_digest(agent: ScheduleAwareQLearningAgent) -> str:
    payload = {
        "q": {"|".join(map(str, state)): values
              for state, values in sorted(agent.q.items())},
        "action_visits": {"|".join(map(str, state)): counts
                          for state, counts in sorted(agent.action_visits.items())},
    }
    return sha256_json(payload)


def explain_agent_step(row: dict[str, Any], agent: ScheduleAwareQLearningAgent,
                       config: Config, volatility_multiplier: float) -> dict[str, Any]:
    t = int(row["step"]) - 1
    remaining = float(row["remaining_before_shares"])
    mid = float(row["mid_before"])
    opponent_previous_qty = float(row["opponent_previous_qty"])
    obs = make_observation(t, remaining, mid, config.initial_price,
                           opponent_previous_qty, config, volatility_multiplier)
    state = agent.state_key(obs)
    q_values = agent.q.get(state, [0.0] * len(ACTIONS))
    visits = agent.action_visits.get(state, [0] * len(ACTIONS))
    required_now, min_index = feasible_action_floor(obs, config)
    feasible_indices = list(range(min_index, len(ACTIONS)))
    tried_feasible = [i for i in feasible_indices if visits[i] > 0]
    selected = ACTION_NAMES.index(str(row["action"]))
    if selected not in feasible_indices:
        raise AssertionError(f"infeasible selected action at step={t + 1}, agent={row['agent']}")
    selected_qty = float(row["submitted_qty"])
    if selected_qty + 1e-9 < required_now or selected_qty > remaining + 1e-9:
        raise AssertionError(f"selected quantity violates feasibility at step={t + 1}, agent={row['agent']}")
    expected_qty = min(remaining, config.base_slice * ACTIONS[selected])
    if abs(selected_qty - expected_qty) > 1e-9:
        raise AssertionError(f"selected action quantity mismatch at step={t + 1}, agent={row['agent']}")

    if tried_feasible:
        best_q = max(q_values[i] for i in tried_feasible)
        best_indices = [i for i in tried_feasible if abs(q_values[i] - best_q) < 1e-12]
        if selected not in best_indices:
            raise AssertionError(f"frozen greedy action mismatch at step={t + 1}, agent={row['agent']}")
        mode = "greedy_q_over_tried_feasible_actions"
        explanation = "在已尝试且可行的动作中选择估计 Q 值最高者；并列时由冻结评估随机流打破平局。"
        tie_count = len(best_indices)
    else:
        fallback = 2 if 2 >= min_index else min_index
        if selected != fallback:
            raise AssertionError(f"frozen fallback mismatch at step={t + 1}, agent={row['agent']}")
        best_q = None
        best_indices = [fallback]
        mode = "twap_fallback_no_tried_feasible_action"
        explanation = "该状态没有已尝试的可行动作，回退到基准 TWAP；若 TWAP 不可行则取最低可行动作。"
        tie_count = 1

    pace_ratio = remaining / max(obs.base_slice * max(obs.horizon - t, 1), 1.0)
    price_deviation_bps = (mid / config.initial_price - 1.0) * 10_000.0
    opponent_ratio = opponent_previous_qty / max(obs.base_slice, 1.0)
    all_actions = [{
        "index": i,
        "name": ACTION_NAMES[i],
        "label": ACTION_LABELS[ACTION_NAMES[i]],
        "twap_multiple": ACTIONS[i],
        "quantity_shares": min(remaining, config.base_slice * ACTIONS[i]),
        "q_value": q_values[i],
        "visit_count": visits[i],
        "tried_before": visits[i] > 0,
        "feasible": i in feasible_indices,
    } for i in range(len(ACTIONS))]
    feasible_actions = [action for action in all_actions if action["feasible"]]

    quantity_weight = float(row["submitted_qty"]) / config.order_size
    mid_scale = mid / config.initial_price
    components = {
        "price_drift": (mid_scale - 1.0) * 10_000.0 * quantity_weight,
        "half_spread": mid_scale * config.half_spread_bps * quantity_weight,
        "temporary_impact": mid_scale * float(row["temporary_impact_bps"]) * quantity_weight,
        "fee": mid_scale * float(row["fee_bps"]) * quantity_weight,
    }
    weighted_step_shortfall = -float(row["weighted_step_reward"])
    if abs(sum(components.values()) - weighted_step_shortfall) > 1e-6:
        raise AssertionError(f"cost components do not reconcile at step={t + 1}, agent={row['agent']}")

    return {
        "agent": row["agent"],
        "observation": {
            "time_step": t + 1,
            "elapsed_seconds": int(row["elapsed_seconds"]),
            "seconds_remaining": (config.horizon - t) * config.step_seconds,
            "mid_price": mid,
            "initial_mid_price": config.initial_price,
            "price_deviation_bps": price_deviation_bps,
            "own_remaining_shares": remaining,
            "pace_ratio_vs_remaining_twap": pace_ratio,
            "opponent_previous_quantity": opponent_previous_qty,
            "opponent_previous_quantity_in_twap_slices": opponent_ratio,
            "state_key": list(state),
            "state_bins": {
                "time_phase_0_to_5": state[0],
                "execution_pace_bin_0_to_4": state[1],
                "price_deviation_bin_0_to_6": state[2],
                "opponent_previous_flow_bin_0_to_2": state[3],
            },
        },
        "decision": {
            "mode": mode,
            "explanation": explanation,
            "selected_action_index": selected,
            "selected_action": ACTION_NAMES[selected],
            "selected_action_label": ACTION_LABELS[ACTION_NAMES[selected]],
            "selected_twap_multiple": ACTIONS[selected],
            "selected_quantity_shares": float(row["submitted_qty"]),
            "selected_q_value": q_values[selected] if visits[selected] > 0 else None,
            "best_q_among_tried_feasible_actions": best_q,
            "greedy_tie_count": tie_count,
            "minimum_feasible_quantity_shares": required_now,
            "minimum_feasible_action_index": min_index,
            "feasibility_floor_active": min_index > 0,
            "selected_action_is_at_feasibility_floor": selected == min_index and min_index > 0,
            "epsilon": 0.0,
            "q_table_updated": False,
            "feasible_actions": feasible_actions,
            "all_actions": all_actions,
            "all_action_q_values": q_values,
            "all_action_visit_counts": visits,
        },
        "execution": {
            "submitted_quantity_shares": float(row["submitted_qty"]),
            "joint_submitted_quantity_shares": float(row["joint_submitted_qty"]),
            "fill_price_including_fee": float(row["fill_price_including_fee"]),
            "weighted_step_shortfall_bps": weighted_step_shortfall,
            "cost_components_bps_of_parent_order": components,
        },
    }


def traced_episode(agent_a: ScheduleAwareQLearningAgent, agent_b: ScheduleAwareQLearningAgent,
                   config: Config, seed: int, fee_bps: float,
                   volatility_multiplier: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Trace-only mirror of the existing frozen episode; parity checked against episode()."""
    rngs = {"A": random.Random(seed ^ 0x13579BDF),
            "B": random.Random(seed ^ 0x2468ACE0)}
    market_rng = random.Random(seed ^ 0x5DEECE66D)
    shocks = [market_rng.gauss(0, config.step_volatility_bps * volatility_multiplier)
              for _ in range(config.horizon)]
    initial_mid = config.initial_price
    mid = initial_mid
    remaining = {"A": config.order_size, "B": config.order_size}
    fills = {"A": 0.0, "B": 0.0}
    gross_cash = {"A": 0.0, "B": 0.0}
    fee_cash = {"A": 0.0, "B": 0.0}
    previous_qty = {"A": 0.0, "B": 0.0}
    rewards_total = {"A": 0.0, "B": 0.0}
    action_counts = {"A": {}, "B": {}}
    agents = {"A": agent_a, "B": agent_b}
    trace: list[dict[str, Any]] = []

    for t in range(config.horizon):
        observations = {
            name: make_observation(t, remaining[name], mid, initial_mid,
                                   previous_qty["B" if name == "A" else "A"],
                                   config, volatility_multiplier)
            for name in ("A", "B")
        }
        indices = {}
        quantities = {}
        for name in ("A", "B"):
            _, min_index = feasible_action_floor(observations[name], config)
            indices[name] = max(frozen_action(agents[name], observations[name], rngs[name]), min_index)
            quantities[name] = min(remaining[name], config.base_slice * ACTIONS[indices[name]])

        joint = quantities["A"] + config.opponent_impact_multiplier * quantities["B"]
        temp = (config.temporary_impact_bps_per_slice * config.market_impact_multiplier
                * config.step_minutes * joint / config.base_slice)
        fee_per_share = mid * fee_bps / 10_000.0
        fills_price = {
            name: mid * (1.0 + (config.half_spread_bps + temp) / 10_000.0) + fee_per_share
            for name in ("A", "B")
        }
        reward = {}
        for name in ("A", "B"):
            gross_cash[name] += quantities[name] * (fills_price[name] - fee_per_share)
            fee_cash[name] += quantities[name] * fee_per_share
            fills[name] += quantities[name]
            remaining[name] = max(0.0, remaining[name] - quantities[name])
            shortfall = (fills_price[name] / initial_mid - 1.0) * 10_000.0
            reward[name] = -(quantities[name] / config.order_size) * shortfall
            rewards_total[name] += reward[name]
            action_name = ACTION_NAMES[indices[name]]
            action_counts[name][action_name] = action_counts[name].get(action_name, 0) + 1

        permanent = (config.permanent_impact_bps_per_slice * config.market_impact_multiplier
                     * config.step_minutes * joint / config.base_slice)
        next_mid = mid * (1.0 + (shocks[t] + permanent) / 10_000.0)
        for name in ("A", "B"):
            trace.append({
                "step": t + 1,
                "elapsed_seconds": (t + 1) * config.step_seconds,
                "mid_before": mid,
                "mid_after": next_mid,
                "external_shock_bps": shocks[t],
                "permanent_impact_bps": permanent,
                "temporary_impact_bps": temp,
                "joint_submitted_qty": joint,
                "half_spread_bps": config.half_spread_bps,
                "fee_bps": fee_bps,
                "agent": name,
                "remaining_before_shares": remaining[name] + quantities[name],
                "opponent_previous_qty": previous_qty["B" if name == "A" else "A"],
                "action": ACTION_NAMES[indices[name]],
                "submitted_qty": quantities[name],
                "fill_price_including_fee": fills_price[name],
                "weighted_step_reward": reward[name],
            })
        previous_qty = {"A": quantities["A"], "B": quantities["B"]}
        mid = next_mid

    result: dict[str, Any] = {"seed": seed}
    for name in ("A", "B"):
        unfilled = max(0.0, config.order_size - fills[name])
        if unfilled < max(1e-9, config.order_size * 1e-12):
            unfilled = 0.0
        completion = min(1.0, fills[name] / config.order_size)
        opportunity = unfilled * (mid - initial_mid) / (config.order_size * initial_mid) * 10_000.0
        gross = ((gross_cash[name] - fills[name] * initial_mid)
                 / (config.order_size * initial_mid) * 10_000.0)
        fee_cost = fee_cash[name] / (config.order_size * initial_mid) * 10_000.0
        result.update({f"cost_{name}_bps": gross + fee_cost + opportunity,
                       f"completion_{name}": completion,
                       f"unfilled_{name}": unfilled,
                       f"reward_{name}": rewards_total[name],
                       f"actions_{name}": json.dumps(action_counts[name], ensure_ascii=False,
                                                     sort_keys=True)})
    return result, trace


def assert_episode_parity(actual: dict[str, Any], traced: dict[str, Any]) -> None:
    for key in ("seed", "actions_A", "actions_B"):
        if actual[key] != traced[key]:
            raise AssertionError(f"traced/export episode mismatch in {key}: {actual[key]} != {traced[key]}")
    for key in ("cost_A_bps", "cost_B_bps", "completion_A", "completion_B",
                "unfilled_A", "unfilled_B", "reward_A", "reward_B"):
        if abs(float(actual[key]) - float(traced[key])) > 1e-10:
            raise AssertionError(f"traced/export episode mismatch in {key}")


def main() -> None:
    args = parse_args()
    if args.fee_bps < 0:
        raise SystemExit("--fee-bps cannot be negative")
    checkpoint_path = args.checkpoint_file.resolve()
    if not checkpoint_path.is_file():
        raise SystemExit(f"Checkpoint file not found: {checkpoint_path}")
    manifest_path = checkpoint_path.with_name("run_manifest.json")
    if not manifest_path.is_file():
        raise SystemExit(f"Checkpoint run manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    all_checkpoints = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint_key = str(args.checkpoint)
    if checkpoint_key not in all_checkpoints:
        raise SystemExit(f"Checkpoint {args.checkpoint} is absent from {checkpoint_path}")

    config = Config(inventory_risk_weight=0.0)
    checkpoint = all_checkpoints[checkpoint_key]
    agents = {name: agent_from_payload(config, checkpoint[name]) for name in ("A", "B")}
    before = {name: table_digest(agent) for name, agent in agents.items()}
    volatility = dict(SCENARIOS)[args.scenario]

    # Compare the traceable export path to the project's actual frozen episode.
    actual = episode(agents["A"], agents["B"], config, args.seed, args.fee_bps,
                     volatility, epsilon=0.0, training=False)
    traced, raw_rows = traced_episode(agents["A"], agents["B"], config, args.seed,
                                      args.fee_bps, volatility)
    assert_episode_parity(actual, traced)
    after = {name: table_digest(agent) for name, agent in agents.items()}
    if before != after:
        raise AssertionError("Frozen replay modified a Q table or action visit counter")
    if len(raw_rows) != config.horizon * 2:
        raise AssertionError(f"expected {config.horizon * 2} agent-step rows; got {len(raw_rows)}")

    grouped: dict[int, dict[str, Any]] = {}
    for row in raw_rows:
        step = int(row["step"])
        item = grouped.setdefault(step, {
            "step": step,
            "elapsed_seconds": int(row["elapsed_seconds"]),
            "market_transition": {
                "mid_before": float(row["mid_before"]),
                "mid_after": float(row["mid_after"]),
                "external_shock_bps": float(row["external_shock_bps"]),
                "permanent_impact_bps": float(row["permanent_impact_bps"]),
                "temporary_impact_bps": float(row["temporary_impact_bps"]),
                "joint_submitted_quantity_shares": float(row["joint_submitted_qty"]),
                "half_spread_bps": float(row["half_spread_bps"]),
                "one_way_fee_bps": float(row["fee_bps"]),
            },
            "agents": {},
        })
        item["agents"][row["agent"]] = explain_agent_step(
            row, agents[row["agent"]], config, volatility,
        )

    steps = [grouped[k] for k in sorted(grouped)]
    for item in steps:
        if set(item["agents"]) != {"A", "B"}:
            raise AssertionError(f"step {item['step']} does not contain both agents")
        a_record, b_record = item["agents"]["A"], item["agents"]["B"]
        if abs(a_record["observation"]["mid_price"] - b_record["observation"]["mid_price"]) > 1e-12:
            raise AssertionError(f"A/B do not share the pre-trade price at step {item['step']}")
        submitted = sum(item["agents"][name]["execution"]["submitted_quantity_shares"]
                        for name in ("A", "B"))
        if abs(submitted - item["market_transition"]["joint_submitted_quantity_shares"]) > 1e-7:
            raise AssertionError(f"joint submitted quantity mismatch at step {item['step']}")

    reconciliation = {}
    for name in ("A", "B"):
        step_sum = sum(s["agents"][name]["execution"]["weighted_step_shortfall_bps"] for s in steps)
        total = float(actual[f"cost_{name}_bps"])
        residual = total - step_sum
        reconciliation[name] = {
            "sum_of_step_shortfalls_bps": step_sum,
            "reported_total_cost_bps": total,
            "residual_opportunity_cost_bps": residual,
        }
        if float(actual[f"completion_{name}"]) >= 1.0 - 1e-12 and abs(residual) > 1e-6:
            raise AssertionError(f"completed Agent {name} costs do not reconcile")

    payload = {
        "schema_version": "1.0",
        "demo_type": "frozen_simultaneous_ab_q_learning_replay",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_ref": args.source_ref,
        "replay_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_checkpoint_file": str(checkpoint_path.relative_to(ROOT.parent)),
        "source_checkpoint_sha256": file_sha256(checkpoint_path),
        "source_run_manifest_file": str(manifest_path.relative_to(ROOT.parent)),
        "source_run_manifest_sha256": file_sha256(manifest_path),
        "checkpoint_training_source_hashes": {
            key: manifest.get(key)
            for key in ("script_sha256", "shared_qlearning_core_sha256", "schedule_aware_q_sha256")
        },
        "checkpoint_episode": args.checkpoint,
        "seed": args.seed,
        "scenario": args.scenario,
        "policy_mode": "frozen_greedy_no_learning_updates",
        "training_updates_applied": False,
        "epsilon": 0.0,
        "config": {
            "window_minutes": config.window_minutes,
            "step_seconds": config.step_seconds,
            "horizon_steps": config.horizon,
            "order_size_per_agent_shares": config.order_size,
            "initial_mid_price": config.initial_price,
            "one_way_fee_bps": args.fee_bps,
            "one_way_fee_percent": args.fee_bps / 100.0,
            "half_spread_bps": config.half_spread_bps,
            "volatility_bps_per_minute": config.volatility_bps,
            "volatility_multiplier": volatility,
            "temporary_impact_bps_per_slice": config.temporary_impact_bps_per_slice,
            "permanent_impact_bps_per_slice": config.permanent_impact_bps_per_slice,
            "opponent_impact_multiplier": config.opponent_impact_multiplier,
        },
        "policy_table_sha256_before": before,
        "policy_table_sha256_after": after,
        "source_episode_parity": {
            key: {"source": actual[key], "trace_export": traced[key]}
            for key in ("cost_A_bps", "cost_B_bps", "completion_A", "completion_B",
                        "unfilled_A", "unfilled_B", "actions_A", "actions_B")
        },
        "summary": {
            "A_cost_bps": float(actual["cost_A_bps"]),
            "B_cost_bps": float(actual["cost_B_bps"]),
            "A_completion_rate": float(actual["completion_A"]),
            "B_completion_rate": float(actual["completion_B"]),
            "A_unfilled_shares": float(actual["unfilled_A"]),
            "B_unfilled_shares": float(actual["unfilled_B"]),
            "A_action_counts": json.loads(actual["actions_A"]),
            "B_action_counts": json.loads(actual["actions_B"]),
            "cost_reconciliation": reconciliation,
        },
        "steps": steps,
        "interpretation_limits": [
            "这是冻结 Q 表的策略回放，不进行在线学习；Q 表及访问计数哈希前后保持一致。",
            "A、B 使用同一交易前市场快照同步选择动作，双方当前动作不会互相可见。",
            "Q 值和访问次数是表格型策略的数值诊断，不是自然语言推理过程。",
            "永久冲击通过下一时点中间价影响后续成本，不应作为当前成交费用重复相加。",
            "环境采用批次撮合和提交即成交假设，不包含真实订单簿排队、拒单或部分成交。",
            "100% 完成率由最低可行动作约束和模拟成交假设共同保证，不代表真实市场保证成交。",
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    config_path = (args.config_output.resolve() if args.config_output is not None
                   else output_path.parent / "run_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_payload = {
        "schema_version": "1.0",
        "purpose": "frozen A/B demo replay configuration and provenance",
        "source_ref": args.source_ref,
        "replay_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "checkpoint_episode": args.checkpoint,
        "checkpoint_file": str(checkpoint_path.relative_to(ROOT.parent)),
        "checkpoint_sha256": payload["source_checkpoint_sha256"],
        "checkpoint_run_manifest_file": str(manifest_path.relative_to(ROOT.parent)),
        "checkpoint_run_manifest_sha256": payload["source_run_manifest_sha256"],
        "checkpoint_training_source_hashes": payload["checkpoint_training_source_hashes"],
        "seed": args.seed,
        "scenario": args.scenario,
        "fee_bps": args.fee_bps,
        "epsilon": 0.0,
        "training_updates_applied": False,
        "output_file": str(output_path.relative_to(ROOT.parent)),
        "runner_files": {
            name: {"path": str((ROOT / name).relative_to(ROOT.parent)),
                   "sha256": file_sha256(ROOT / name)}
            for name in ("export_agent_demo.py", "run_advanced_self_play.py",
                         "run_standard_benchmark.py", "schedule_aware_q.py")
        },
        "python_version": sys.version,
    }
    config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Demo JSON written: {output_path}")
    print(f"Run config written: {config_path}")
    print(f"checkpoint_sha256={payload['source_checkpoint_sha256']}")
    print(f"steps={len(steps)} agent_step_rows={len(raw_rows)} source_episode_parity=PASS")
    print(f"q_table_unchanged={before == after}")
    print(f"A_cost_bps={actual['cost_A_bps']:.10f} B_cost_bps={actual['cost_B_bps']:.10f}")


if __name__ == "__main__":
    main()
