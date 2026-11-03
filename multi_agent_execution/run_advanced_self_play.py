#!/usr/bin/env python3
"""Primary two-sided Q-learning self-play model for execution simulation.

This is the primary local, stylized research simulation. A and B learn
simultaneously. The fixed-opponent benchmark remains available separately as
run_standard_benchmark.py. Only Python's standard library is required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_standard_benchmark import (
    ACTIONS,
    Config,
    QLearningAgent,
    discretize_state,
    feasible_action_floor,
    make_observation,
)
from schedule_aware_q import ScheduleAwareQLearningAgent


DEFAULT_OUT = Path(__file__).resolve().parent / "outputs" / "advanced_self_play"
SCENARIOS = (("normal", 1.0), ("high_volatility", 2.0))
ACTION_NAMES = ("wait", "half", "base", "one_and_half", "double")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train two Q-learning execution agents simultaneously and evaluate frozen cross-play."
    )
    parser.add_argument("--episodes", type=int, default=500, help="training episodes per run")
    parser.add_argument("--training-runs", type=int, default=5, help="independent training seeds")
    parser.add_argument("--eval-seeds", type=int, default=30, help="paired evaluation seeds per cell")
    parser.add_argument("--checkpoint-interval", type=int, default=100)
    parser.add_argument("--fee-bps", type=float, default=30.0, help="one-way fee in basis points; 30bp = 0.3%%")
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.episodes < 1 or args.training_runs < 1 or args.eval_seeds < 1:
        parser.error("episodes, training-runs, and eval-seeds must be positive")
    if args.checkpoint_interval < 1:
        parser.error("checkpoint-interval must be positive")
    if args.fee_bps < 0:
        parser.error("fee-bps cannot be negative")
    return args


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def qtable_to_json(agent: QLearningAgent) -> dict[str, Any]:
    return {
        "opponent_aware": agent.opponent_aware,
        "state_encoding": getattr(agent, "state_encoding", "exact_time_inventory_price_opponent_v0"),
        "q": {"|".join(map(str, state)): values for state, values in agent.q.items()},
        "action_visits": {
            "|".join(map(str, state)): counts for state, counts in agent.action_visits.items()
        },
    }


def snapshot_to_json(snap: dict[str, Any]) -> dict[str, Any]:
    return {
        "state_encoding": ScheduleAwareQLearningAgent.state_encoding,
        "visited_state_count": snap["visited_state_count"],
        "q": {"|".join(map(str, state)): values for state, values in snap["q"].items()},
        "action_visits": {
            "|".join(map(str, state)): counts for state, counts in snap["visits"].items()
        },
    }


def snapshot(agent: QLearningAgent) -> dict[str, Any]:
    return {
        "q": {state: values[:] for state, values in agent.q.items()},
        "visits": {state: counts[:] for state, counts in agent.action_visits.items()},
        "visited_state_count": len(agent.visited),
    }


def frozen_action(agent: QLearningAgent, obs: Any, rng: random.Random) -> int:
    """Read a learned policy without mutating its Q table during evaluation."""
    state = (agent.state_key(obs) if hasattr(agent, "state_key")
             else discretize_state(obs, agent.opponent_aware))
    values = agent.q.get(state, [0.0] * len(ACTIONS))
    visits = agent.action_visits.get(state, [0] * len(ACTIONS))
    _, min_idx = feasible_action_floor(obs, agent.config)
    allowed = [idx for idx in range(min_idx, len(ACTIONS)) if visits[idx] > 0]
    if not allowed:
        return 2 if 2 >= min_idx else min_idx
    best_value = max(values[idx] for idx in allowed)
    tied = [idx for idx in allowed if abs(values[idx] - best_value) < 1e-12]
    return rng.choice(tied)


def episode(agent_a: QLearningAgent, agent_b: QLearningAgent, config: Config,
            seed: int, fee_bps: float, volatility_multiplier: float,
            epsilon: float = 0.0, training: bool = False) -> dict[str, Any]:
    """Run one synchronized episode; both agents act before either is updated."""
    rng_a = random.Random(seed ^ 0x13579BDF)
    rng_b = random.Random(seed ^ 0x2468ACE0)
    market_rng = random.Random(seed ^ 0x5DEECE66D)
    shocks = [market_rng.gauss(0, config.step_volatility_bps * volatility_multiplier)
              for _ in range(config.horizon)]
    initial_mid = config.initial_price
    mid = initial_mid
    remaining = {"A": config.order_size, "B": config.order_size}
    fills = {"A": 0.0, "B": 0.0}
    gross_cash = {"A": 0.0, "B": 0.0}
    fee_cash = {"A": 0.0, "B": 0.0}
    prev_qty = {"A": 0.0, "B": 0.0}
    total_reward = {"A": 0.0, "B": 0.0}
    action_counts = {"A": Counter(), "B": Counter()}
    agents = {"A": agent_a, "B": agent_b}
    rngs = {"A": rng_a, "B": rng_b}

    for t in range(config.horizon):
        # Both observations use the same pre-trade mid and only prior-step
        # opponent activity, so neither policy sees the other's current order.
        observations = {
            name: make_observation(t, remaining[name], mid, initial_mid,
                                  prev_qty["B" if name == "A" else "A"],
                                  config, volatility_multiplier)
            for name in ("A", "B")
        }
        action_idx: dict[str, int] = {}
        qty: dict[str, float] = {}
        for name in ("A", "B"):
            _, min_idx = feasible_action_floor(observations[name], config)
            if training:
                action_idx[name] = agents[name].select(
                    observations[name], rngs[name], epsilon, min_idx
                )
            else:
                action_idx[name] = frozen_action(agents[name], observations[name], rngs[name])
            action_idx[name] = max(action_idx[name], min_idx)
            qty[name] = min(remaining[name], config.base_slice * ACTIONS[action_idx[name]])

        pooled_volume = qty["A"] + config.opponent_impact_multiplier * qty["B"]
        temp_impact = (config.temporary_impact_bps_per_slice *
                       config.market_impact_multiplier * config.step_minutes *
                       pooled_volume / config.base_slice)
        fee_per_share = mid * fee_bps / 10_000.0
        fill_prices = {
            name: mid * (1 + (config.half_spread_bps + temp_impact) / 10_000.0)
            + fee_per_share
            for name in ("A", "B")
        }
        rewards: dict[str, float] = {}
        for name in ("A", "B"):
            gross_cash[name] += qty[name] * (fill_prices[name] - fee_per_share)
            fee_cash[name] += qty[name] * fee_per_share
            fills[name] += qty[name]
            remaining[name] = max(0.0, remaining[name] - qty[name])
            shortfall_bps = (fill_prices[name] / initial_mid - 1) * 10_000.0
            # Align the TD objective with reported implementation shortfall.
            # Unfilled shares still receive the terminal completion penalty.
            reward = -(qty[name] / config.order_size) * shortfall_bps
            rewards[name] = reward
            action_counts[name][ACTION_NAMES[action_idx[name]]] += 1

        permanent_impact = (config.permanent_impact_bps_per_slice *
                            config.market_impact_multiplier * config.step_minutes *
                            pooled_volume / config.base_slice)
        next_mid = mid * (1 + (shocks[t] + permanent_impact) / 10_000.0)
        next_prev_qty = {"A": qty["A"], "B": qty["B"]}
        terminal = t == config.horizon - 1
        next_observations = {
            name: None if terminal else make_observation(
                t + 1, remaining[name], next_mid, initial_mid,
                next_prev_qty["B" if name == "A" else "A"], config,
                volatility_multiplier)
            for name in ("A", "B")
        }
        for name in ("A", "B"):
            learning_reward = rewards[name]
            if terminal:
                learning_reward -= (remaining[name] / config.order_size) * config.terminal_unfilled_penalty_bps
            total_reward[name] += learning_reward
        if training:
            # Updates occur only after both current actions and the shared
            # market transition have been computed (simultaneous learning).
            for name in ("A", "B"):
                agents[name].update(observations[name], action_idx[name],
                                   learning_reward_for(rewards[name], remaining[name], config, terminal),
                                   next_observations[name])
        prev_qty = next_prev_qty
        mid = next_mid

    cost: dict[str, float] = {}
    completion: dict[str, float] = {}
    unfilled: dict[str, float] = {}
    for name in ("A", "B"):
        unfilled[name] = max(0.0, config.order_size - fills[name])
        if unfilled[name] < max(1e-9, config.order_size * 1e-12):
            unfilled[name] = 0.0
        completion[name] = min(1.0, fills[name] / config.order_size)
        opportunity = unfilled[name] * (mid - initial_mid) / (config.order_size * initial_mid) * 10_000.0
        gross_bps = ((gross_cash[name] - fills[name] * initial_mid) /
                     (config.order_size * initial_mid) * 10_000.0)
        fee_bps_cost = fee_cash[name] / (config.order_size * initial_mid) * 10_000.0
        cost[name] = gross_bps + fee_bps_cost + opportunity
    return {
        "seed": seed,
        "cost_A_bps": cost["A"], "cost_B_bps": cost["B"],
        "completion_A": completion["A"], "completion_B": completion["B"],
        "unfilled_A": unfilled["A"], "unfilled_B": unfilled["B"],
        "reward_A": total_reward["A"], "reward_B": total_reward["B"],
        "actions_A": json.dumps(dict(action_counts["A"]), ensure_ascii=False, sort_keys=True),
        "actions_B": json.dumps(dict(action_counts["B"]), ensure_ascii=False, sort_keys=True),
    }


def learning_reward_for(step_reward: float, remaining: float, config: Config, terminal: bool) -> float:
    if terminal:
        return step_reward - (remaining / config.order_size) * config.terminal_unfilled_penalty_bps
    return step_reward


def train_run(run_id: int, args: argparse.Namespace, config: Config) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], QLearningAgent, QLearningAgent]:
    run_seed = args.seed + run_id * 1_000_003
    agent_a = ScheduleAwareQLearningAgent(config, opponent_aware=True)
    agent_b = ScheduleAwareQLearningAgent(config, opponent_aware=True)
    snapshots: dict[int, dict[str, Any]] = {
        0: {"A": snapshot(agent_a), "B": snapshot(agent_b)}
    }
    episodes_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    rewards_a: list[float] = []
    rewards_b: list[float] = []
    costs_a: list[float] = []
    costs_b: list[float] = []
    checkpoints = {args.episodes}
    checkpoints.update(range(args.checkpoint_interval, args.episodes + 1, args.checkpoint_interval))
    for ep in range(1, args.episodes + 1):
        epsilon = config.epsilon_start + (config.epsilon_end - config.epsilon_start) * (ep - 1) / max(args.episodes - 1, 1)
        result = episode(agent_a, agent_b, config, run_seed + ep * 37 + 11,
                         args.fee_bps, 1.0, epsilon=epsilon, training=True)
        rewards_a.append(result["reward_A"])
        rewards_b.append(result["reward_B"])
        costs_a.append(result["cost_A_bps"])
        costs_b.append(result["cost_B_bps"])
        episodes_rows.append({
            "training_run": run_id, "episode": ep, "epsilon": epsilon,
            "A_reward": result["reward_A"], "B_reward": result["reward_B"],
            "A_cost_bps": result["cost_A_bps"], "B_cost_bps": result["cost_B_bps"],
            "A_completion_rate": result["completion_A"], "B_completion_rate": result["completion_B"],
            "A_unfilled_shares": result["unfilled_A"], "B_unfilled_shares": result["unfilled_B"],
            "A_actions": result["actions_A"], "B_actions": result["actions_B"],
        })
        if ep in checkpoints:
            window = min(100, ep)
            diagnostics.extend([
                {"training_run": run_id, "checkpoint_episode": ep, "agent": name,
                 "rolling_window_episodes": window,
                 "rolling_reward_mean": statistics.fmean(rewards[-window:]),
                 "rolling_cost_mean_bps": statistics.fmean(costs[-window:]),
                 "rolling_cost_sd_bps": statistics.pstdev(costs[-window:]) if window > 1 else 0.0,
                 "visited_state_count": len(agent.visited), "q_state_count": len(agent.q),
                 "initial_state_max_q": agent.initial_state_max_q(), "epsilon": epsilon}
                for name, agent, rewards, costs in (
                    ("A", agent_a, rewards_a, costs_a), ("B", agent_b, rewards_b, costs_b))
            ])
            snapshots[ep] = {"A": snapshot(agent_a), "B": snapshot(agent_b)}
    return snapshots, episodes_rows, diagnostics, agent_a, agent_b


def instantiate_snapshot(config: Config, snap: dict[str, Any]) -> QLearningAgent:
    agent = ScheduleAwareQLearningAgent(config, opponent_aware=True)
    agent.q = {state: values[:] for state, values in snap["q"].items()}
    agent.action_visits = {state: counts[:] for state, counts in snap["visits"].items()}
    agent.freeze()
    return agent


def mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.fmean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def evaluate_cross_play(run_id: int, snapshots: dict[int, dict[str, Any]],
                        args: argparse.Namespace, config: Config) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    checkpoints = sorted(snapshots)
    for a_cp in checkpoints:
        for b_cp in checkpoints:
            for scenario, volatility_multiplier in SCENARIOS:
                for eval_idx in range(args.eval_seeds):
                    seed = args.seed + run_id * 1_000_003 + 500_000_000 + eval_idx * 101 + (0 if scenario == "normal" else 50_000)
                    # Independent frozen copies ensure evaluation cannot alter training snapshots.
                    a = instantiate_snapshot(config, snapshots[a_cp]["A"])
                    b = instantiate_snapshot(config, snapshots[b_cp]["B"])
                    result = episode(a, b, config, seed, args.fee_bps,
                                     volatility_multiplier, training=False)
                    rows.append({
                        "training_run": run_id, "A_checkpoint": a_cp, "B_checkpoint": b_cp,
                        "scenario": scenario, "seed": seed,
                        "cost_A_bps": result["cost_A_bps"], "cost_B_bps": result["cost_B_bps"],
                        "completion_A": result["completion_A"], "completion_B": result["completion_B"],
                        "unfilled_A": result["unfilled_A"], "unfilled_B": result["unfilled_B"],
                        "reward_A": result["reward_A"], "reward_B": result["reward_B"],
                        "actions_A": result["actions_A"], "actions_B": result["actions_B"],
                        "fee_bps": args.fee_bps,
                    })
    return rows


def summarize_cross_play(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in raw_rows:
        key = (row["training_run"], row["A_checkpoint"], row["B_checkpoint"], row["scenario"])
        groups.setdefault(key, []).append(row)
    summaries = []
    for (run_id, a_cp, b_cp, scenario), group in sorted(groups.items()):
        costs_a = [r["cost_A_bps"] for r in group]
        costs_b = [r["cost_B_bps"] for r in group]
        summaries.append({
            "training_run": run_id, "A_checkpoint": a_cp, "B_checkpoint": b_cp,
            "scenario": scenario, "evaluation_seeds": len(group),
            "A_cost_mean_bps": statistics.fmean(costs_a),
            "A_cost_sd_bps": statistics.stdev(costs_a) if len(costs_a) > 1 else 0.0,
            "B_cost_mean_bps": statistics.fmean(costs_b),
            "B_cost_sd_bps": statistics.stdev(costs_b) if len(costs_b) > 1 else 0.0,
            "A_completion_mean": statistics.fmean(r["completion_A"] for r in group),
            "B_completion_mean": statistics.fmean(r["completion_B"] for r in group),
            "A_unfilled_mean": statistics.fmean(r["unfilled_A"] for r in group),
            "B_unfilled_mean": statistics.fmean(r["unfilled_B"] for r in group),
            "A_reward_mean": statistics.fmean(r["reward_A"] for r in group),
            "B_reward_mean": statistics.fmean(r["reward_B"] for r in group),
        })
    return summaries


def build_stability(summaries: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in summaries:
        if row["A_checkpoint"] != row["B_checkpoint"]:
            continue
        rows.append({
            "training_run": row["training_run"], "checkpoint_episode": row["A_checkpoint"],
            "scenario": row["scenario"], "evaluation_seeds": row["evaluation_seeds"],
            "A_diagonal_cost_mean_bps": row["A_cost_mean_bps"],
            "A_diagonal_cost_sd_bps": row["A_cost_sd_bps"],
            "B_diagonal_cost_mean_bps": row["B_cost_mean_bps"],
            "B_diagonal_cost_sd_bps": row["B_cost_sd_bps"],
            "A_completion_mean": row["A_completion_mean"],
            "B_completion_mean": row["B_completion_mean"],
            "A_reward_mean": row["A_reward_mean"],
            "B_reward_mean": row["B_reward_mean"],
        })
    # Attach training diagnostics to separate rows so performance stability
    # and training signals can be inspected without conflating their units.
    for d in diagnostics:
        rows.append({
            "training_run": d["training_run"], "checkpoint_episode": d["checkpoint_episode"],
            "scenario": "training_diagnostic", "agent": d["agent"],
            "rolling_reward_mean": d["rolling_reward_mean"],
            "rolling_cost_mean_bps": d["rolling_cost_mean_bps"],
            "rolling_cost_sd_bps": d["rolling_cost_sd_bps"],
            "visited_state_count": d["visited_state_count"], "q_state_count": d["q_state_count"],
            "initial_state_max_q": d["initial_state_max_q"], "epsilon": d["epsilon"],
        })
    return rows


def build_candidate_best_response(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    group_keys = sorted({(r["training_run"], r["scenario"]) for r in summaries})
    for run_id, scenario in group_keys:
        group = [r for r in summaries if r["training_run"] == run_id and r["scenario"] == scenario]
        checkpoints = sorted({r["A_checkpoint"] for r in group})
        for fixed_b_cp in checkpoints:
            candidates = [r for r in group if r["B_checkpoint"] == fixed_b_cp]
            incumbent = next(r for r in candidates if r["A_checkpoint"] == fixed_b_cp)
            best = min(candidates, key=lambda r: r["A_cost_mean_bps"])
            rows.append({
                "training_run": run_id, "scenario": scenario, "responding_agent": "A",
                "fixed_opponent_checkpoint": fixed_b_cp,
                "incumbent_own_checkpoint": fixed_b_cp,
                "candidate_best_response_checkpoint": best["A_checkpoint"],
                "incumbent_cost_bps": incumbent["A_cost_mean_bps"],
                "best_response_cost_bps": best["A_cost_mean_bps"],
                "candidate_set_regret_bps": incumbent["A_cost_mean_bps"] - best["A_cost_mean_bps"],
                "candidate_policy_count": len(candidates), "evaluation_seeds": best["evaluation_seeds"],
            })
        for fixed_a_cp in checkpoints:
            candidates = [r for r in group if r["A_checkpoint"] == fixed_a_cp]
            incumbent = next(r for r in candidates if r["B_checkpoint"] == fixed_a_cp)
            best = min(candidates, key=lambda r: r["B_cost_mean_bps"])
            rows.append({
                "training_run": run_id, "scenario": scenario, "responding_agent": "B",
                "fixed_opponent_checkpoint": fixed_a_cp,
                "incumbent_own_checkpoint": fixed_a_cp,
                "candidate_best_response_checkpoint": best["B_checkpoint"],
                "incumbent_cost_bps": incumbent["B_cost_mean_bps"],
                "best_response_cost_bps": best["B_cost_mean_bps"],
                "candidate_set_regret_bps": incumbent["B_cost_mean_bps"] - best["B_cost_mean_bps"],
                "candidate_policy_count": len(candidates), "evaluation_seeds": best["evaluation_seeds"],
            })
    return rows


def findings_text(args: argparse.Namespace, summaries: list[dict[str, Any]],
                  best_response: list[dict[str, Any]],
                  diagnostics: list[dict[str, Any]]) -> str:
    final_episode = args.episodes
    lines = [
        "# 双边同步 Q-learning：本轮运行记录", "",
        f"- 训练：{args.training_runs} 个独立种子，每个 {args.episodes} 回合；每回合 {Config().horizon} 个 30 秒时间步。",
        f"- 冻结交叉评估：每个训练运行 {len({r['A_checkpoint'] for r in summaries})} 个检查点，{args.eval_seeds} 个配对随机种子；单边手续费 {args.fee_bps:g} bp。",
        "- 训练在正常波动环境进行；训练检查点分别冻结后，在正常与 2 倍波动场景做交叉对局。",
        "- 本文件的数字仅是本次命令参数下的模拟结果，不自动代表收敛或现实市场效果。", "",
        "## 最终检查点的交叉对局", "",
        "下表按训练运行和场景汇总 A/B 均采用最终检查点的对局。成本越低越好；完成率和未完成量应同时检查。", "",
        "| 训练运行 | 场景 | A 成本均值 (bp) | A 成本标准差 | A 完成率 | B 成本均值 (bp) | B 成本标准差 | B 完成率 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for run_id in sorted({r["training_run"] for r in summaries}):
        for scenario, _ in SCENARIOS:
            row = next(r for r in summaries if r["training_run"] == run_id and r["A_checkpoint"] == final_episode and r["B_checkpoint"] == final_episode and r["scenario"] == scenario)
            lines.append(f"| {run_id} | {scenario} | {row['A_cost_mean_bps']:.3f} | {row['A_cost_sd_bps']:.3f} | {row['A_completion_mean']:.3f} | {row['B_cost_mean_bps']:.3f} | {row['B_cost_sd_bps']:.3f} | {row['B_completion_mean']:.3f} |")
    lines += ["", "## 跨训练种子汇总与学习诊断", "",
              "下表先在每个训练运行内对评估种子取均值，再汇总不同训练运行；± 后为训练运行均值的标准差。该值描述随机训练种子间的差异，不是每个评估回合的标准误。", "",
              "| 场景 | A 最终成本均值 ± 训练种子标准差 (bp) | B 最终成本均值 ± 训练种子标准差 (bp) |",
              "|---|---:|---:|"]
    for scenario, _ in SCENARIOS:
        scenario_rows = [r for r in summaries if r["A_checkpoint"] == final_episode and
                         r["B_checkpoint"] == final_episode and r["scenario"] == scenario]
        a_mean, a_sd = mean_sd([r["A_cost_mean_bps"] for r in scenario_rows])
        b_mean, b_sd = mean_sd([r["B_cost_mean_bps"] for r in scenario_rows])
        lines.append(f"| {scenario} | {a_mean:.3f} ± {a_sd:.3f} | {b_mean:.3f} ± {b_sd:.3f} |")
    lines += ["", "各检查点训练诊断的跨种子均值如下。训练回报和成本并非单调改善，当前数据不足以声称双边策略已收敛。", "",
              "| 检查点 | Agent | 滚动回报均值 | 滚动成本均值 (bp) | 已访问状态均值 |",
              "|---:|---|---:|---:|---:|"]
    for cp in sorted({d["checkpoint_episode"] for d in diagnostics}):
        for agent_name in ("A", "B"):
            rows = [d for d in diagnostics if d["checkpoint_episode"] == cp and d["agent"] == agent_name]
            lines.append(f"| {cp} | {agent_name} | {statistics.fmean(d['rolling_reward_mean'] for d in rows):.3f} | {statistics.fmean(d['rolling_cost_mean_bps'] for d in rows):.3f} | {statistics.fmean(d['visited_state_count'] for d in rows):.1f} |")
    regrets = [r["candidate_set_regret_bps"] for r in best_response if r["incumbent_own_checkpoint"] == final_episode]
    lines += ["", "## 候选集最佳反应", "",
              f"最终检查点对照同一训练运行中保存的冻结检查点集合，候选集后悔值均值为 {statistics.fmean(regrets):.4f} bp（共 {len(regrets)} 个方向/场景/运行观测）。",
              "该量只表示相对有限检查点候选集的成本差，不是全局最优策略，也不构成纳什均衡证明。", "",
              "## 解释边界", "",
              "- A、B 在每步基于同一交易前价格和各自库存同时选动作；两者的当前下单量共同影响暂时冲击与下一步价格。",
              "- 双方均为带执行进度状态聚合的表格 Q-learning：状态包含 6 档时间阶段、订单执行进度、价格偏离和对手上一期成交量。TD 奖励与实施缺口口径对齐；下一状态仅从已尝试且可行的动作中自举，避免未尝试动作的零初始化高估。训练中两边策略都在变化，因此环境对任一单方而言是非平稳的。",
              "- 检查点交叉对局把已保存的策略冻结后进行组合评估，避免评估过程继续改写 Q 表；配对种子共享外生价格冲击。",
              "- 稳定性要结合多训练种子的滚动奖励、成本波动、状态覆盖与检查点交叉结果判断。单一训练曲线变平不足以证明收敛。",
              "- 本主模型运行结果写入 outputs/advanced_self_play；规则策略配对比较另由 run_matched_rule_q_comparison.py 生成。",
              "- 该环境是教学用简化撮合模型，没有真实行情、订单簿或实盘接口。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    started = time.time()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    config = Config(inventory_risk_weight=0.0)
    all_training: list[dict[str, Any]] = []
    all_diagnostics: list[dict[str, Any]] = []
    all_raw: list[dict[str, Any]] = []
    checkpoint_count = math.ceil(args.episodes / args.checkpoint_interval) + 1
    print(f"Advanced self-play: {args.training_runs} runs × {args.episodes} episodes; checkpoints about {checkpoint_count} per run.", flush=True)
    for run_id in range(1, args.training_runs + 1):
        print(f"Training run {run_id}/{args.training_runs} ...", flush=True)
        snapshots, training_rows, diagnostics, final_a, final_b = train_run(run_id, args, config)
        all_training.extend(training_rows)
        all_diagnostics.extend(diagnostics)
        for side, agent in (("A", final_a), ("B", final_b)):
            (out / f"qtable_run{run_id}_{side}.json").write_text(
                json.dumps(qtable_to_json(agent), ensure_ascii=False, indent=2), encoding="utf-8")
        checkpoint_payload = {
            str(cp): {side: snapshot_to_json(snap[side]) for side in ("A", "B")}
            for cp, snap in snapshots.items()
        }
        (out / f"checkpoint_qtables_run{run_id}.json").write_text(
            json.dumps(checkpoint_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"Evaluating frozen checkpoint cross-play for run {run_id} ...", flush=True)
        all_raw.extend(evaluate_cross_play(run_id, snapshots, args, config))
    summaries = summarize_cross_play(all_raw)
    stability = build_stability(summaries, all_diagnostics)
    best_response = build_candidate_best_response(summaries)
    write_csv(out / "training_episodes.csv", all_training)
    write_csv(out / "checkpoint_training_diagnostics.csv", all_diagnostics)
    write_csv(out / "cross_play_raw.csv", all_raw)
    write_csv(out / "cross_play_summary.csv", summaries)
    write_csv(out / "self_play_stability.csv", stability)
    write_csv(out / "candidate_best_response.csv", best_response)
    (out / "findings.md").write_text(findings_text(args, summaries, best_response, all_diagnostics), encoding="utf-8")
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    core_path = Path(__file__).with_name("run_standard_benchmark.py")
    try:
        output_dir_record = out.resolve().relative_to(Path(__file__).resolve().parent).as_posix()
    except ValueError:
        output_dir_record = str(out.resolve())
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "script": Path(__file__).name, "script_sha256": script_hash,
        "shared_qlearning_core_sha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
        "schedule_aware_q_sha256": hashlib.sha256(
            Path(__file__).with_name("schedule_aware_q.py").read_bytes()
        ).hexdigest(),
        "parameters": {"episodes": args.episodes, "training_runs": args.training_runs,
                       "eval_seeds": args.eval_seeds, "checkpoint_interval": args.checkpoint_interval,
                       "fee_bps": args.fee_bps, "seed": args.seed,
                       "output_dir": output_dir_record},
        "config": {**asdict(config), "horizon_steps": config.horizon,
                   "training_scenarios": ["normal"],
                   "evaluation_scenarios": {name: mult for name, mult in SCENARIOS}},
        "method": {
            "agent_A": "opponent-aware tabular Q-learning with schedule-aware state aggregation",
            "agent_B": "opponent-aware tabular Q-learning with schedule-aware state aggregation",
            "state_encoding": ScheduleAwareQLearningAgent.state_encoding,
            "reward_alignment": "implementation shortfall plus terminal unfilled-order penalty; no extra inventory-risk shaping",
            "untried_action_bootstrap": "only tried feasible actions are included in the next-state maximum",
            "simultaneous_action_and_update": True,
            "checkpoint_evaluation": "frozen cross-play on paired seeds",
            "candidate_best_response": "minimum own cost among saved checkpoints against fixed opponent checkpoint",
            "claim_boundary": "candidate-set responses are not global optima or Nash equilibria",
        },
        "counts": {"training_episode_rows": len(all_training), "cross_play_rows": len(all_raw),
                   "cross_play_summary_rows": len(summaries), "checkpoint_count_per_run": len(snapshots)},
        "elapsed_seconds": round(time.time() - started, 3),
    }
    # snapshots is loop-local; derive the actual checkpoint count from the summaries.
    manifest["counts"]["checkpoint_count_per_run"] = len({r["A_checkpoint"] for r in summaries})
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Complete. Outputs written to {out.resolve()}", flush=True)


if __name__ == "__main__":
    main()
