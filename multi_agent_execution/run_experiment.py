#!/usr/bin/env python3
"""Reproducible multi-agent execution simulator (standard-library only).

This is a research simulator, not a live trading system. It runs two agents
simultaneously in a stylized market and writes all experiment outputs locally.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
import traceback
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
ACTIONS = (0.0, 0.5, 1.0, 1.5, 2.0)  # multiples of the common TWAP slice
TRAIN_OPPONENTS = ("twap", "frontloaded", "backloaded")
TEST_OPPONENTS = TRAIN_OPPONENTS + ("bursty", "randomized")
POLICIES = ("G0_TWAP", "G1_dynamic_rule", "G2_Q_learning", "G3_opponent_aware_Q")
SCENARIOS = (("normal", 1.0), ("high_volatility", 2.0))


@dataclass(frozen=True)
class Config:
    window_minutes: int = 30
    step_seconds: int = 30
    order_size: float = 100_000.0
    initial_price: float = 100.0
    half_spread_bps: float = 2.0
    volatility_bps: float = 2.5
    temporary_impact_bps_per_slice: float = 0.35
    permanent_impact_bps_per_slice: float = 0.20
    inventory_risk_weight: float = 0.025
    terminal_unfilled_penalty_bps: float = 1_000.0
    learning_rate: float = 0.15
    discount: float = 0.98
    epsilon_start: float = 0.35
    epsilon_end: float = 0.05

    @property
    def horizon(self) -> int:
        return self.window_minutes * 60 // self.step_seconds

    @property
    def step_minutes(self) -> float:
        return self.step_seconds / 60.0

    @property
    def step_volatility_bps(self) -> float:
        # volatility_bps is the one-minute standard deviation.
        return self.volatility_bps * math.sqrt(self.step_minutes)

    @property
    def base_slice(self) -> float:
        return self.order_size / self.horizon


@dataclass(frozen=True)
class Observation:
    t: int
    remaining: float
    mid: float
    initial_mid: float
    opponent_previous_qty: float
    base_slice: float
    horizon: int
    volatility_bps: float


@dataclass
class EpisodeResult:
    policy: str
    opponent: str
    fee_bps: float
    scenario: str
    seed: int
    cost_bps: float
    completion_rate: float
    unfilled_shares: float
    reward: float
    action_counts: dict[str, int]
    review_required: bool
    review_reason: str
    trace: list[dict[str, Any]]


def discretize_state(obs: Observation, opponent_aware: bool) -> tuple[int, ...]:
    # Keep the exact decision step so delayed terminal penalties can propagate
    # backward through Q updates instead of collapsing many minutes together.
    time_bin = obs.t
    remaining_fraction = obs.remaining / max(obs.base_slice * obs.horizon, 1.0)
    inventory_bin = min(10, max(0, int(remaining_fraction * 10)))
    deviation_bps = (obs.mid / obs.initial_mid - 1.0) * 10_000.0
    price_bin = 0 if deviation_bps < -4 else 1 if deviation_bps < -1 else 2 if deviation_bps < 1 else 3 if deviation_bps < 4 else 4
    state: tuple[int, ...] = (time_bin, inventory_bin, price_bin)
    if opponent_aware:
        opponent_ratio = obs.opponent_previous_qty / max(obs.base_slice, 1.0)
        opponent_bin = 0 if opponent_ratio < 0.25 else 1 if opponent_ratio < 1.25 else 2
        state += (opponent_bin,)
    return state


class QLearningAgent:
    """A tabular execution agent; G3 adds the opponent's previous action."""

    def __init__(self, config: Config, opponent_aware: bool, q_table: dict[tuple[int, ...], list[float]] | None = None):
        self.config = config
        self.opponent_aware = opponent_aware
        self.q: dict[tuple[int, ...], list[float]] = q_table if q_table is not None else {}
        self.action_visits: dict[tuple[int, ...], list[int]] = {}
        self.visited: set[tuple[int, ...]] = set()

    def values(self, obs: Observation) -> list[float]:
        state = discretize_state(obs, self.opponent_aware)
        self.visited.add(state)
        return self.q.setdefault(state, [0.0] * len(ACTIONS))

    def select(self, obs: Observation, rng: random.Random, epsilon: float = 0.0,
               allowed_min_index: int = 0) -> int:
        values = self.values(obs)
        state = discretize_state(obs, self.opponent_aware)
        allowed = list(range(allowed_min_index, len(ACTIONS)))
        if epsilon > 0 and rng.random() < epsilon:
            return rng.choice(allowed)
        # In a cost-minimization problem all learned Q values are usually
        # negative. Treating unvisited zero-initialized actions as the best
        # action creates an optimistic-initialization bug at evaluation time.
        # Use the common TWAP slice as the explicit fallback until an action has
        # actually been tried in this state, then compare only tried actions.
        visits = self.action_visits.get(state, [0] * len(ACTIONS))
        tried = [i for i, count in enumerate(visits) if count > 0 and i in allowed]
        if not tried:
            return 2 if 2 in allowed else allowed[0]
        best = max(values[i] for i in tried)
        tied = [i for i in tried if abs(values[i] - best) < 1e-12]
        return rng.choice(tied)

    def update(self, obs: Observation, action: int, reward: float, next_obs: Observation | None) -> None:
        state = discretize_state(obs, self.opponent_aware)
        self.visited.add(state)
        current = self.q.setdefault(state, [0.0] * len(ACTIONS))
        visits = self.action_visits.setdefault(state, [0] * len(ACTIONS))
        visits[action] += 1
        future = 0.0 if next_obs is None else max(self.values(next_obs))
        target = reward + self.config.discount * future
        current[action] += self.config.learning_rate * (target - current[action])

    def initial_state_max_q(self) -> float:
        initial = Observation(0, self.config.order_size, self.config.initial_price,
                              self.config.initial_price, 0.0, self.config.base_slice,
                              self.config.horizon, self.config.step_volatility_bps)
        return max(self.q.get(discretize_state(initial, self.opponent_aware), [0.0] * len(ACTIONS)))


class RiskReviewAgent:
    """Independent rule-based review gate; it never submits real orders."""

    def review(self, completion_rate: float, cost_bps: float, max_abs_shock_bps: float) -> tuple[bool, str]:
        reasons = []
        if completion_rate < 0.98:
            reasons.append("completion_below_98_percent")
        if cost_bps > 200:
            reasons.append("execution_cost_above_200bp")
        if max_abs_shock_bps > 10:
            reasons.append("extreme_market_shock_above_10bp")
        return bool(reasons), ";".join(reasons)


class OpponentAgent:
    """Transparent scripted B agents used as controlled counter-strategies."""

    def __init__(self, name: str, config: Config, rng: random.Random):
        self.name, self.config, self.rng = name, config, rng

    def desired_qty(self, t: int, remaining: float) -> float:
        c = self.config
        x = t / c.horizon
        if self.name == "twap":
            multiple = 1.0
        elif self.name == "frontloaded":
            multiple = 1.6 if x < 0.30 else 0.743
        elif self.name == "backloaded":
            multiple = 0.70 if x < 0.70 else 1.70
        elif self.name == "bursty":
            # Two consecutive high-volume bursts followed by two quiet steps;
            # average size remains one TWAP slice over each four-step cycle.
            multiple = 2.0 if t % 4 in (1, 2) else 0.0
        elif self.name == "randomized":
            multiple = self.rng.choice((0.5, 1.5))
        else:
            raise ValueError(f"Unknown opponent: {self.name}")
        return min(remaining, c.base_slice * multiple)


def make_observation(t: int, remaining: float, mid: float, initial: float,
                     opponent_previous_qty: float, config: Config,
                     volatility_multiplier: float = 1.0) -> Observation:
    return Observation(t, remaining, mid, initial, opponent_previous_qty,
                       config.base_slice, config.horizon,
                       config.step_volatility_bps * volatility_multiplier)


def run_episode(policy: str, opponent_name: str, fee_bps: float, seed: int,
                config: Config, q_agent: QLearningAgent | None = None,
                training_epsilon: float = 0.0, trace_enabled: bool = False,
                scenario_name: str = "normal", volatility_multiplier: float = 1.0) -> EpisodeResult:
    rng = random.Random(seed)
    market_rng = random.Random(seed ^ 0x5DEECE66D)
    opponent = OpponentAgent(opponent_name, config, rng)
    mid = config.initial_price
    remaining_a = remaining_b = config.order_size
    initial_mid = mid
    last_b_qty = 0.0
    cash_a = cash_b = 0.0
    fill_a = fill_b = 0.0
    episode_reward = 0.0
    action_counts: Counter[str] = Counter()
    trace: list[dict[str, Any]] = []
    shocks = [market_rng.gauss(0, config.step_volatility_bps * volatility_multiplier)
              for _ in range(config.horizon)]

    terminal_penalty = 0.0
    for t in range(config.horizon):
        obs = make_observation(t, remaining_a, mid, initial_mid, last_b_qty, config,
                               volatility_multiplier)
        q_values_before: list[float] | None = None
        # Shared hard feasibility constraint: never choose an action that makes
        # completion impossible under the common 2x maximum child-order size.
        future_capacity = (config.horizon - t - 1) * ACTIONS[-1] * config.base_slice
        required_now = max(0.0, remaining_a - future_capacity)
        min_action_index = min(len(ACTIONS) - 1,
                               max(0, math.ceil(required_now / config.base_slice * 2 - 1e-12)))
        if policy == "G0_TWAP":
            action_idx = 2  # the common base slice
        elif policy == "G1_dynamic_rule":
            deficit = remaining_a / max(config.base_slice * (config.horizon - t), 1.0)
            price_deviation = (mid / initial_mid - 1.0) * 10_000.0
            if t == config.horizon - 1 or deficit > 1.25:
                action_idx = 4
            elif price_deviation < -1.0:
                action_idx = 3
            elif price_deviation > 2.0 and deficit < 1.05:
                action_idx = 1
            else:
                action_idx = 2
        elif policy in ("G2_Q_learning", "G3_opponent_aware_Q"):
            if q_agent is None:
                raise ValueError(f"Missing trained Q agent for {policy}")
            action_idx = q_agent.select(obs, rng, training_epsilon, min_action_index)
            q_values_before = q_agent.values(obs).copy()
        else:
            raise ValueError(f"Unknown A policy: {policy}")

        action_idx = max(action_idx, min_action_index)
        qty_a = min(remaining_a, config.base_slice * ACTIONS[action_idx])
        qty_b = opponent.desired_qty(t, remaining_b)
        # A and B decide from the same pre-trade snapshot. Their combined flow
        # affects both the execution price and the next market state.
        pooled_temp_impact = (config.temporary_impact_bps_per_slice * config.step_minutes *
                              (qty_a + qty_b) / config.base_slice)
        fill_price_a = mid * (1 + (config.half_spread_bps + fee_bps + pooled_temp_impact) / 10_000)
        fill_price_b = mid * (1 + (config.half_spread_bps + fee_bps + pooled_temp_impact) / 10_000)
        cash_a += qty_a * fill_price_a
        cash_b += qty_b * fill_price_b
        fill_a += qty_a
        fill_b += qty_b
        remaining_a -= qty_a
        remaining_b -= qty_b
        shortfall_a = (fill_price_a / initial_mid - 1.0) * 10_000.0
        step_reward = -(qty_a / config.order_size) * shortfall_a
        step_reward -= (config.inventory_risk_weight * (remaining_a / config.order_size) *
                        (config.volatility_bps * volatility_multiplier / 2.5) * config.step_minutes)
        episode_reward += step_reward
        action_counts["wait"] += int(action_idx == 0)
        action_counts["half"] += int(action_idx == 1)
        action_counts["base"] += int(action_idx == 2)
        action_counts["large"] += int(action_idx >= 3)

        old_obs = obs
        next_mid = mid * (1 + (shocks[t] + config.permanent_impact_bps_per_slice * config.step_minutes *
                               (qty_a + qty_b) / config.base_slice) / 10_000)
        last_b_qty = qty_b
        if trace_enabled:
            seconds_left_before = (config.horizon - t) * config.step_seconds
            simulated_time = datetime(2000, 1, 1, 15, 0) - timedelta(seconds=seconds_left_before)
            if required_now > 0:
                decision_reason = "订单进度已接近可行性边界，按共享的最小可行下单量约束执行。"
            elif policy.startswith("G2") or policy.startswith("G3"):
                decision_reason = "根据当前时间、剩余订单、价格偏离和可用的对手历史信息，选择 Q 值最高的已尝试动作。"
            elif policy == "G0_TWAP":
                decision_reason = "按固定 TWAP 节奏执行基准份额。"
            else:
                decision_reason = "动态规则结合当前价格偏离与剩余订单进度调整下单速度。"
            trace.append({
                "t": t + 1, "elapsed_seconds": (t + 1) * config.step_seconds,
                "simulated_market_time": simulated_time.strftime("%H:%M:%S"),
                "time_left_seconds": seconds_left_before,
                "scenario": scenario_name, "fee_bps": fee_bps,
                "half_spread_bps": config.half_spread_bps,
                "B_previous_qty": obs.opponent_previous_qty,
                "q_values_before": json.dumps(q_values_before) if q_values_before is not None else "",
                "decision_reason": decision_reason,
                "mid_before": mid,
                "price_deviation_bps": (mid / initial_mid - 1) * 10_000,
                "A_remaining_before": remaining_a + qty_a, "A_action_multiple": ACTIONS[action_idx],
                "A_min_feasible_qty": required_now,
                "A_qty": qty_a, "B_strategy": opponent_name, "B_qty": qty_b,
                "pooled_temporary_impact_bps": pooled_temp_impact,
                "A_fill_price": fill_price_a, "step_reward": step_reward,
                "A_remaining_after": remaining_a, "mid_after": next_mid,
                "business_explanation": "本步成交和合并订单冲击更新了市场状态；动作是当前模拟假设下的策略选择，不是对真实价格的预测。",
            })
        mid = next_mid
        is_terminal = t == config.horizon - 1
        if is_terminal:
            terminal_penalty = (remaining_a / config.order_size) * config.terminal_unfilled_penalty_bps
        learning_reward = step_reward - terminal_penalty if is_terminal else step_reward
        next_obs = None if is_terminal else make_observation(
            t + 1, remaining_a, mid, initial_mid, last_b_qty, config,
            volatility_multiplier)
        if q_agent is not None and training_epsilon > 0:
            q_agent.update(old_obs, action_idx, learning_reward, next_obs)

    unfilled = max(0.0, remaining_a)
    if unfilled < max(1e-9, config.order_size * 1e-12):
        unfilled = 0.0
    completion = 1.0 if unfilled == 0.0 else min(1.0, fill_a / config.order_size)
    episode_reward -= terminal_penalty
    cost_bps = ((cash_a / max(fill_a, 1.0)) / initial_mid - 1) * 10_000 if fill_a else 0.0
    max_shock = max(abs(x) for x in shocks) / math.sqrt(config.step_minutes)
    review, reason = RiskReviewAgent().review(completion, cost_bps, max_shock)
    return EpisodeResult(policy, opponent_name, fee_bps, scenario_name, seed, cost_bps, completion,
                         unfilled, episode_reward, dict(action_counts), review, reason, trace)


def train_agent(fee_bps: float, opponent_aware: bool, episodes: int,
                seed: int, config: Config) -> tuple[QLearningAgent, dict[str, Any]]:
    agent = QLearningAgent(config, opponent_aware)
    rng = random.Random(seed)
    returns: list[float] = []
    for ep in range(episodes):
        epsilon = config.epsilon_start + (config.epsilon_end - config.epsilon_start) * ep / max(episodes - 1, 1)
        opponent_name = rng.choice(TRAIN_OPPONENTS)
        result = run_episode("G3_opponent_aware_Q" if opponent_aware else "G2_Q_learning",
                             opponent_name, fee_bps, seed + ep * 37 + 11,
                             config, agent, epsilon)
        returns.append(result.reward)
    recent = returns[-min(100, len(returns)):]
    # The Q table stores tuples internally; serialize with explicit state keys.
    diagnostics = {
        "fee_bps": fee_bps,
        "agent": "G3_opponent_aware_Q" if opponent_aware else "G2_Q_learning",
        "episodes": episodes,
        "rolling_return_last_100": statistics.mean(recent) if recent else 0.0,
        "rolling_return_previous_100": statistics.mean(returns[-200:-100]) if len(returns) > 100 else None,
        "initial_state_max_q": agent.initial_state_max_q(),
        "mean_max_q_over_visited_states": statistics.mean(max(agent.q[s]) for s in agent.visited) if agent.visited else 0.0,
        "visited_state_count": len(agent.visited),
    }
    return agent, diagnostics


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def serialize_q(agent: QLearningAgent) -> dict[str, Any]:
    return {"opponent_aware": agent.opponent_aware,
            "actions_as_base_slice_multiples": list(ACTIONS),
            "q_table": [{"state": list(state), "values": values,
                         "action_visits": agent.action_visits.get(state, [0] * len(ACTIONS))}
                        for state, values in sorted(agent.q.items())]}


def load_q_table(path: Path, config: Config) -> QLearningAgent:
    """Load a saved Q table for later evaluation or an extended experiment."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    agent = QLearningAgent(config, bool(payload["opponent_aware"]))
    for row in payload["q_table"]:
        state = tuple(int(x) for x in row["state"])
        agent.q[state] = [float(x) for x in row["values"]]
        agent.action_visits[state] = [int(x) for x in row.get("action_visits", [0] * len(ACTIONS))]
        agent.visited.add(state)
    return agent


def aggregate(results: list[EpisodeResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float, str], list[EpisodeResult]] = {}
    for result in results:
        grouped.setdefault((result.policy, result.opponent, result.fee_bps, result.scenario), []).append(result)
    rows = []
    for (policy, opponent, fee, scenario), group in sorted(grouped.items()):
        counts = Counter()
        for item in group:
            counts.update(item.action_counts)
        denominators = max(1, sum(counts.values()))
        rows.append({
            "fee_percent": fee / 100.0,
            "fee_bps": fee,
            "scenario": scenario,
            "A_policy": policy,
            "B_opponent": opponent,
            "runs": len(group),
            "mean_implementation_shortfall_bps": statistics.mean(x.cost_bps for x in group),
            "sd_implementation_shortfall_bps": statistics.stdev(x.cost_bps for x in group) if len(group) > 1 else 0.0,
            "mean_completion_rate": statistics.mean(x.completion_rate for x in group),
            "mean_unfilled_shares": statistics.mean(x.unfilled_shares for x in group),
            "mean_episode_reward": statistics.mean(x.reward for x in group),
            "wait_action_share": counts["wait"] / denominators,
            "half_action_share": counts["half"] / denominators,
            "base_action_share": counts["base"] / denominators,
            "large_action_share": counts["large"] / denominators,
            "human_review_rate": sum(x.review_required for x in group) / len(group),
        })
    return rows


def paired_comparisons(results: list[EpisodeResult]) -> list[dict[str, Any]]:
    indexed = {(r.fee_bps, r.scenario, r.opponent, r.seed, r.policy): r for r in results}
    contrasts = (("G1_dynamic_rule", "G0_TWAP", "H1 dynamic feedback vs fixed TWAP"),
                 ("G2_Q_learning", "G1_dynamic_rule", "H2 Q-learning vs dynamic rule"),
                 ("G3_opponent_aware_Q", "G2_Q_learning", "H3 opponent information vs none"))
    rows = []
    fees = sorted(set(r.fee_bps for r in results))
    for fee in fees:
        for scenario, _vol_multiplier in SCENARIOS:
            for opponent in TEST_OPPONENTS:
                seeds = sorted(set(r.seed for r in results if r.fee_bps == fee and r.scenario == scenario and r.opponent == opponent))
                for policy, baseline, question in contrasts:
                    deltas, completion_deltas = [], []
                    for seed in seeds:
                        a = indexed[(fee, scenario, opponent, seed, policy)]
                        b = indexed[(fee, scenario, opponent, seed, baseline)]
                        deltas.append(a.cost_bps - b.cost_bps)
                        completion_deltas.append(a.completion_rate - b.completion_rate)
                    mean_delta = statistics.mean(deltas)
                    sd_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
                    half_width = 1.96 * sd_delta / math.sqrt(len(deltas)) if deltas else 0.0
                    rows.append({
                        "fee_bps": fee, "scenario": scenario, "B_opponent": opponent,
                        "research_question": question, "strategy": policy, "baseline": baseline,
                        "paired_runs": len(deltas),
                        "mean_cost_difference_bps_strategy_minus_baseline": mean_delta,
                        "approx_95pct_ci_low_bps": mean_delta - half_width,
                        "approx_95pct_ci_high_bps": mean_delta + half_width,
                        "mean_completion_rate_difference": statistics.mean(completion_deltas),
                    })
    return rows


def raw_evaluation_rows(results: list[EpisodeResult]) -> list[dict[str, Any]]:
    rows = []
    for r in results:
        total = max(1, sum(r.action_counts.values()))
        rows.append({
            "fee_bps": r.fee_bps, "scenario": r.scenario,
            "B_opponent": r.opponent, "A_policy": r.policy,
            "seed": r.seed, "implementation_shortfall_bps": r.cost_bps,
            "completion_rate": r.completion_rate, "unfilled_shares": r.unfilled_shares,
            "episode_reward": r.reward,
            "wait_action_share": r.action_counts.get("wait", 0) / total,
            "half_action_share": r.action_counts.get("half", 0) / total,
            "base_action_share": r.action_counts.get("base", 0) / total,
            "large_action_share": r.action_counts.get("large", 0) / total,
            "review_required": r.review_required, "review_reason": r.review_reason,
        })
    return rows


def build_findings(rows: list[dict[str, Any]], comparisons: list[dict[str, Any]],
                   diagnostics: list[dict[str, Any]], config: Config,
                   episodes: int, seeds: int) -> str:
    lines = [
        "# 多智能体最优执行模拟：本次运行记录", "",
        f"运行时间（UTC）：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"模拟设置：每方母单 {config.order_size:,.0f} 股，执行窗口 {config.window_minutes} 分钟、每 {config.step_seconds} 秒一步（共 {config.horizon} 步）；A/B 同时决策。",
        f"训练：每个手续费档、每种 Q 策略 {episodes} 回合；评估：每个手续费×波动场景×策略×对手组合 {seeds} 个配对随机种子。", "",
        "## 怎样解读", "",
        "以下结果由本地模拟器实际生成。价格、冲击、价差和对手规则均为明确的教学模拟设定，不是历史市场估计。成本与奖励口径不同：执行缺口按成交均价对初始参考价计算，训练奖励另包含库存风险和未完成惩罚。Q 值受奖励刻度、训练轮数和随机种子影响，不能单独作为策略优劣结论。", "",
        "## 按成本档的平均结果", "",
        "表中对每种 A 策略在全部五类 B 对手上的评估均值再取平均；详细的逐对手结果见 `evaluation_summary.csv`。", "",
        "| 手续费 | 波动场景 | A 策略 | 平均执行缺口 (bp) | 完成率 | 平均奖励 | 等待动作占比 | 人工复核率 |", "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    fees = sorted(set(float(r["fee_bps"]) for r in rows))
    for fee in fees:
        for scenario, _ in SCENARIOS:
            for policy in POLICIES:
                subset = [r for r in rows if float(r["fee_bps"]) == fee and r["scenario"] == scenario and r["A_policy"] == policy]
                if not subset:
                    continue
                avg = lambda key: statistics.mean(float(r[key]) for r in subset)
                lines.append(f"| {fee/100:.1f}% | {scenario} | {policy} | {avg('mean_implementation_shortfall_bps'):.2f} | {avg('mean_completion_rate'):.3f} | {avg('mean_episode_reward'):.2f} | {avg('wait_action_share'):.3f} | {avg('human_review_rate'):.3f} |")
    lines.extend(["", "## 同种子配对差异", "",
                  "正的成本差表示策略比基线成本高，负值表示低。区间为正态近似 95% 区间；逐种子原始结果在 `evaluation_raw.csv`，完整比较在 `paired_comparisons.csv`。", "",
                  "| 手续费 | 波动场景 | B 对手 | 假设对照 | 成本差 bp (策略−基线) | 近似 95% 区间 | 完成率差 |",
                  "|---:|---|---|---|---:|---:|---:|"])
    for c in comparisons:
        lines.append(f"| {c['fee_bps']/100:.1f}% | {c['scenario']} | {c['B_opponent']} | {c['research_question']} | {c['mean_cost_difference_bps_strategy_minus_baseline']:.2f} | [{c['approx_95pct_ci_low_bps']:.2f}, {c['approx_95pct_ci_high_bps']:.2f}] | {c['mean_completion_rate_difference']:.3f} |")
    lines.extend(["", "## 学习诊断", "", "| 手续费 | 学习器 | 训练回合 | 最近 100 回合平均奖励 | 前 100 回合平均奖励 | 初始状态 max Q | 已访问状态数 |", "|---:|---|---:|---:|---:|---:|---:|"])
    for d in diagnostics:
        prev = "NA" if d["rolling_return_previous_100"] is None else f"{d['rolling_return_previous_100']:.2f}"
        lines.append(f"| {d['fee_bps']/100:.1f}% | {d['agent']} | {d['episodes']} | {d['rolling_return_last_100']:.2f} | {prev} | {d['initial_state_max_q']:.2f} | {d['visited_state_count']} |")
    lines.extend([
        "", "## 实验限制与下一步", "",
        "- 这是单一资产、单一离散时间步长的模拟，不包含真实订单簿撮合、队列优先级、隐藏流动性、市场制度或历史逐笔行情。",
        "- G2/G3 以多个规则对手混合训练；`bursty` 与 `randomized` 留作未见测试对手。冻结策略后的换对手测试衡量泛化，不代表在线适应。",
        "- 每个策略与对手组合共享相同外生随机种子；策略引发的价格路径差异是市场内生反馈。策略必须满足相同母单、期限和单步动作集合。所有 A 策略共享可行性约束：若继续等待会导致在剩余时段最大下单量下也无法完成，则屏蔽过小动作。",
        "- 结果不保证 Q-learning 胜出。若结果不稳定，应增加训练轮数、检查状态覆盖，或重新设计离散状态；不能把未收敛结果包装为有效结论。",
        "- RiskReviewAgent 只触发模拟结果复核标记，不执行真实交易。该系统没有券商接口或真实下单功能。",
        "- 本次未调用生成式模型服务，因此没有模型 API 阻塞；仿真和 Q-learning 使用可重现的本地随机种子。", "",
        "## 产物", "",
        "- `evaluation_summary.csv`：成本、完成率、奖励、动作分布和复核率。",
        "- `paired_comparisons.csv`：同随机种子配对的策略差异与近似 95% 区间。",
        "- `evaluation_raw.csv`：逐回合种子结果，可复核或重新统计。",
        "- `training_diagnostics.csv`：训练奖励、初始状态 Q 值及状态访问情况。",
        "- `sample_episode_trace.csv`：0.5% 手续费、高波动下 G3 对 bursty 对手的一回合逐步记录，含状态、Q 值、判断、动作、反馈和解释。",
        "- `qtable_*.json`：每个成本档训练后的 Q 表。",
        "- `run_manifest.json`：参数、种子和运行配置。", "",
    ])
    return "\n".join(lines)


def run_experiment(episodes: int, seeds: int, seed: int, config: Config) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    all_eval: list[EpisodeResult] = []
    diagnostics: list[dict[str, Any]] = []
    trained: dict[tuple[float, str], QLearningAgent] = {}
    fee_tiers = (10.0, 30.0, 50.0)  # 0.1%, 0.3%, 0.5%

    for fee_index, fee in enumerate(fee_tiers):
        for learner_index, opponent_aware in enumerate((False, True)):
            learner_name = "G3_opponent_aware_Q" if opponent_aware else "G2_Q_learning"
            print(f"[训练] fee={fee/100:.1f}% agent={learner_name} episodes={episodes}", flush=True)
            agent, diag = train_agent(fee, opponent_aware, episodes,
                                      seed + fee_index * 100_000 + learner_index * 10_000,
                                      config)
            diagnostics.append(diag)
            trained[(fee, learner_name)] = agent
            q_path = OUT / f"qtable_{learner_name}_{int(fee)}bps.json"
            q_path.write_text(json.dumps(serialize_q(agent), ensure_ascii=False, indent=2), encoding="utf-8")

        for policy in POLICIES:
            q_agent = None if policy.startswith("G0") or policy.startswith("G1") else trained[(fee, policy)]
            for scenario_name, volatility_multiplier in SCENARIOS:
                for opponent_name in TEST_OPPONENTS:
                    for run_idx in range(seeds):
                        common_seed = seed + 2_000_000 + fee_index * 1_000_000 + run_idx * 101
                        result = run_episode(policy, opponent_name, fee, common_seed,
                                             config, q_agent, trace_enabled=False,
                                             scenario_name=scenario_name,
                                             volatility_multiplier=volatility_multiplier)
                        all_eval.append(result)
            print(f"[评估] fee={fee/100:.1f}% 完成 {policy}", flush=True)

    summary_rows = aggregate(all_eval)
    comparison_rows = paired_comparisons(all_eval)
    write_csv(OUT / "evaluation_summary.csv", summary_rows)
    write_csv(OUT / "paired_comparisons.csv", comparison_rows)
    write_csv(OUT / "evaluation_raw.csv", raw_evaluation_rows(all_eval))
    write_csv(OUT / "training_diagnostics.csv", diagnostics)

    trace_fee = 50.0
    trace_agent = trained[(trace_fee, "G3_opponent_aware_Q")]
    sample = run_episode("G3_opponent_aware_Q", "bursty", trace_fee,
                         seed + 9_999_991, config, trace_agent, trace_enabled=True,
                         scenario_name="high_volatility", volatility_multiplier=2.0)
    write_csv(OUT / "sample_episode_trace.csv", sample.trace)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "config": {**asdict(config), "horizon_steps": config.horizon,
                   "base_slice_shares": config.base_slice,
                   "step_volatility_bps": config.step_volatility_bps},
        "fee_tiers_bps": list(fee_tiers),
        "evaluation_scenarios": [{"name": name, "volatility_multiplier": multiplier}
                                  for name, multiplier in SCENARIOS],
        "training_opponents": list(TRAIN_OPPONENTS),
        "test_opponents": list(TEST_OPPONENTS),
        "policies": list(POLICIES),
        "training_episodes_per_learner_per_fee": episodes,
        "evaluation_seeds_per_policy_opponent_fee_scenario": seeds,
        "master_seed": seed,
        "evaluation_episode_count": len(all_eval),
        "elapsed_seconds": round(time.time() - started, 3),
        "sample_trace_review_required": sample.review_required,
        "sample_trace_review_reason": sample.review_reason,
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "findings.md").write_text(build_findings(summary_rows, comparison_rows, diagnostics, config, episodes, seeds), encoding="utf-8")
    print(f"[完成] {len(all_eval)} 个评估回合；用时 {manifest['elapsed_seconds']} 秒。", flush=True)
    print(f"结果目录：{OUT}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=1200, help="每种 Q 学习器、每个手续费档的训练回合数")
    parser.add_argument("--seeds", type=int, default=30, help="每个策略×对手×手续费组合的评估随机种子数")
    parser.add_argument("--seed", type=int, default=20261102, help="主随机种子")
    args = parser.parse_args()
    if args.episodes < 1 or args.seeds < 1:
        parser.error("episodes and seeds must both be positive")
    try:
        run_experiment(args.episodes, args.seeds, args.seed, Config())
    except Exception:
        print("[运行失败] 捕获到异常，完整诊断如下：", file=sys.stderr)
        traceback.print_exc()
        print("可用相同 --seed 重试；必要时减少 --episodes 定位问题。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
