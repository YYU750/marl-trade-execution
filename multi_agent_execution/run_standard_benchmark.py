#!/usr/bin/env python3
"""Reproducible multi-agent execution simulator (standard-library only).

This is a research simulator, not a live trading system. It runs one learning
agent against a fixed-policy counterparty in a stylized market, then evaluates
incremental value from feedback, learning, and opponent information.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import time
import traceback
from collections import Counter
from dataclasses import asdict, dataclass, replace
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
FEE_TIERS_BPS = (10.0, 30.0, 50.0)


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
    market_impact_multiplier: float = 1.0
    opponent_impact_multiplier: float = 1.0
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
    open_order_qty: float = 0.0
    queue_ahead: float = 0.0
    limit_price: float = 0.0
    order_age_steps: int = 0


def feasible_action_floor(obs: Observation, config: Config) -> tuple[float, int]:
    """Return the minimum executable shares and action index needed to finish."""
    steps_after_this = max(0, config.horizon - obs.t - 1)
    required_now = max(
        0.0,
        obs.remaining - steps_after_this * ACTIONS[-1] * config.base_slice,
    )
    min_action_index = min(
        len(ACTIONS) - 1,
        max(0, math.ceil(required_now / config.base_slice * 2 - 1e-12)),
    )
    return required_now, min_action_index


@dataclass
class EpisodeResult:
    policy: str
    opponent: str
    fee_bps: float
    scenario: str
    seed: int
    cost_bps: float
    gross_cost_bps: float
    fee_cost_bps: float
    opportunity_cost_bps: float
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
        self.frozen = False

    def freeze(self) -> None:
        """Make policy queries read-only and reject subsequent learning updates."""
        self.frozen = True

    def values(self, obs: Observation) -> list[float]:
        state = discretize_state(obs, self.opponent_aware)
        if self.frozen:
            return self.q.get(state, [0.0] * len(ACTIONS))
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
        if self.frozen:
            raise RuntimeError("Cannot update a frozen Q-learning policy")
        state = discretize_state(obs, self.opponent_aware)
        self.visited.add(state)
        current = self.q.setdefault(state, [0.0] * len(ACTIONS))
        visits = self.action_visits.setdefault(state, [0] * len(ACTIONS))
        visits[action] += 1
        if next_obs is None:
            future = 0.0
        else:
            next_values = self.values(next_obs)
            _, min_feasible_index = feasible_action_floor(next_obs, self.config)
            future = max(next_values[min_feasible_index:])
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
        desired = min(remaining, c.base_slice * multiple)
        if self.name == "randomized":
            # Keep the stochastic policy's chosen pace where feasible, but
            # enforce the same 2x maximum-child-order completion constraint
            # used by A so B cannot become an unintended unfilled-order case.
            steps_after_this = max(0, c.horizon - t - 1)
            required_now = max(0.0, remaining - steps_after_this * ACTIONS[-1] * c.base_slice)
            desired = min(remaining, max(desired, required_now))
        return desired


def make_observation(t: int, remaining: float, mid: float, initial: float,
                     opponent_previous_qty: float, config: Config,
                     volatility_multiplier: float = 1.0,
                     open_order_qty: float = 0.0,
                     queue_ahead: float = 0.0,
                     limit_price: float = 0.0,
                     order_age_steps: int = 0) -> Observation:
    return Observation(t, remaining, mid, initial, opponent_previous_qty,
                       config.base_slice, config.horizon,
                       config.step_volatility_bps * volatility_multiplier,
                       open_order_qty, queue_ahead, limit_price, order_age_steps)


def run_episode(policy: str, opponent_name: str, fee_bps: float, seed: int,
                config: Config, q_agent: QLearningAgent | None = None,
                training_epsilon: float = 0.0, trace_enabled: bool = False,
                scenario_name: str = "normal", volatility_multiplier: float = 1.0) -> EpisodeResult:
    # Keep policy randomness, randomized-opponent choices, and market shocks
    # on separate streams so one policy cannot change the opponent's path by
    # consuming a different number of random draws.
    agent_rng = random.Random(seed ^ 0x13579BDF)
    opponent_rng = random.Random(seed ^ 0x2468ACE0)
    market_rng = random.Random(seed ^ 0x5DEECE66D)
    opponent = OpponentAgent(opponent_name, config, opponent_rng)
    mid = config.initial_price
    remaining_a = remaining_b = config.order_size
    initial_mid = mid
    last_b_qty = 0.0
    cash_a = cash_b = 0.0
    gross_cash_a = 0.0
    fee_cash_a = 0.0
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
        required_now, min_action_index = feasible_action_floor(obs, config)
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
            elif (config.temporary_impact_bps_per_slice * config.market_impact_multiplier *
                  config.step_minutes) > 0.15 and deficit < 0.98:
                # When ahead of schedule, slow down under high impact instead
                # of continuing to accelerate the parent order.
                action_idx = 1
            else:
                action_idx = 2
        elif policy in ("G2_Q_learning", "G3_opponent_aware_Q"):
            if q_agent is None:
                raise ValueError(f"Missing trained Q agent for {policy}")
            action_idx = q_agent.select(obs, agent_rng, training_epsilon, min_action_index)
            q_values_before = q_agent.values(obs).copy()
        else:
            raise ValueError(f"Unknown A policy: {policy}")

        action_idx = max(action_idx, min_action_index)
        qty_a = min(remaining_a, config.base_slice * ACTIONS[action_idx])
        qty_b = opponent.desired_qty(t, remaining_b)
        # A and B decide from the same pre-trade snapshot. Their combined flow
        # affects both the execution price and the next market state.
        price_impact_volume = qty_a + config.opponent_impact_multiplier * qty_b
        pooled_temp_impact = (config.temporary_impact_bps_per_slice * config.market_impact_multiplier *
                              config.step_minutes * price_impact_volume / config.base_slice)
        gross_fill_price_a = mid * (1 + (config.half_spread_bps + pooled_temp_impact) / 10_000)
        fee_per_share_a = mid * fee_bps / 10_000
        fill_price_a = gross_fill_price_a + fee_per_share_a
        fill_price_b = mid * (1 + (config.half_spread_bps + fee_bps + pooled_temp_impact) / 10_000)
        cash_a += qty_a * fill_price_a
        gross_cash_a += qty_a * gross_fill_price_a
        fee_cash_a += qty_a * fee_per_share_a
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
        permanent_impact = (config.permanent_impact_bps_per_slice * config.market_impact_multiplier *
                            config.step_minutes * price_impact_volume / config.base_slice)
        next_mid = mid * (1 + (shocks[t] + permanent_impact) / 10_000)
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
                decision_reason = "动态规则结合当前价格偏离、剩余订单进度及冲击条件调整下单速度。"
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
                "A_fill_price": fill_price_a, "A_gross_fill_price": gross_fill_price_a,
                "A_fee_per_share": fee_per_share_a,
                "opponent_impact_multiplier": config.opponent_impact_multiplier,
                "market_impact_multiplier": config.market_impact_multiplier,
                "permanent_impact_bps": permanent_impact,
                "step_reward": step_reward,
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
    parent_notional = config.order_size * initial_mid
    gross_cost_bps = ((gross_cash_a - fill_a * initial_mid) / parent_notional * 10_000)
    fee_cost_bps = fee_cash_a / parent_notional * 10_000
    opportunity_cost_bps = remaining_a * (mid - initial_mid) / parent_notional * 10_000
    cost_bps = gross_cost_bps + fee_cost_bps + opportunity_cost_bps
    max_shock = max(abs(x) for x in shocks) / math.sqrt(config.step_minutes)
    review, reason = RiskReviewAgent().review(completion, cost_bps, max_shock)
    return EpisodeResult(
        policy=policy, opponent=opponent_name, fee_bps=fee_bps, scenario=scenario_name,
        seed=seed, cost_bps=cost_bps, gross_cost_bps=gross_cost_bps,
        fee_cost_bps=fee_cost_bps, opportunity_cost_bps=opportunity_cost_bps,
        completion_rate=completion, unfilled_shares=unfilled, reward=episode_reward,
        action_counts=dict(action_counts), review_required=review, review_reason=reason,
        trace=trace,
    )


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
            "mean_gross_execution_shortfall_bps": statistics.mean(x.gross_cost_bps for x in group),
            "mean_fee_cost_bps": statistics.mean(x.fee_cost_bps for x in group),
            "mean_opportunity_cost_bps": statistics.mean(x.opportunity_cost_bps for x in group),
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


def paired_comparisons(results: list[EpisodeResult], scenario_names: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    indexed = {(r.fee_bps, r.scenario, r.opponent, r.seed, r.policy): r for r in results}
    contrasts = (("G1_dynamic_rule", "G0_TWAP", "H1 dynamic feedback vs fixed TWAP"),
                 ("G2_Q_learning", "G1_dynamic_rule", "H2 Q-learning vs dynamic rule"),
                 ("G3_opponent_aware_Q", "G2_Q_learning", "H3 opponent information vs none"))
    rows = []
    fees = sorted(set(r.fee_bps for r in results))
    scenarios = scenario_names or tuple(name for name, _vol_multiplier in SCENARIOS)
    for fee in fees:
        for scenario in scenarios:
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
            "gross_execution_shortfall_bps": r.gross_cost_bps,
            "fee_cost_bps": r.fee_cost_bps,
            "opportunity_cost_bps": r.opportunity_cost_bps,
            "completion_rate": r.completion_rate, "unfilled_shares": r.unfilled_shares,
            "episode_reward": r.reward,
            "wait_action_share": r.action_counts.get("wait", 0) / total,
            "half_action_share": r.action_counts.get("half", 0) / total,
            "base_action_share": r.action_counts.get("base", 0) / total,
            "large_action_share": r.action_counts.get("large", 0) / total,
            "review_required": r.review_required, "review_reason": r.review_reason,
        })
    return rows


def candidate_set_regret_rows(results: list[EpisodeResult]) -> list[dict[str, Any]]:
    """Regret relative to the best policy in the tested G0-G3 candidate set."""
    grouped: dict[tuple[float, str, str, int], list[EpisodeResult]] = {}
    for result in results:
        grouped.setdefault((result.fee_bps, result.scenario, result.opponent, result.seed), []).append(result)
    rows = []
    for (fee, scenario, opponent, seed), group in sorted(grouped.items()):
        best = min(group, key=lambda x: x.cost_bps)
        for result in group:
            rows.append({
                "fee_bps": fee, "scenario": scenario, "B_opponent": opponent, "seed": seed,
                "A_policy": result.policy, "candidate_best_policy": best.policy,
                "candidate_best_cost_bps": best.cost_bps,
                "policy_cost_bps": result.cost_bps,
                "candidate_set_regret_bps": result.cost_bps - best.cost_bps,
                "completion_rate": result.completion_rate,
            })
    return rows


def summarize_candidate_regret(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[float, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["fee_bps"], row["scenario"], row["B_opponent"], row["A_policy"])
        groups.setdefault(key, []).append(row)
    summary = []
    for (fee, scenario, opponent, policy), group in sorted(groups.items()):
        regret = [float(x["candidate_set_regret_bps"]) for x in group]
        best_share = sum(x["candidate_best_policy"] == policy for x in group) / len(group)
        summary.append({
            "fee_bps": fee, "scenario": scenario, "B_opponent": opponent, "A_policy": policy,
            "runs": len(group), "mean_candidate_set_regret_bps": statistics.mean(regret),
            "sd_candidate_set_regret_bps": statistics.stdev(regret) if len(regret) > 1 else 0.0,
            "best_response_share_in_candidate_set": best_share,
            "mean_completion_rate": statistics.mean(float(x["completion_rate"]) for x in group),
        })
    return summary


def interaction_ablation_rows(on_results: list[EpisodeResult], off_results: list[EpisodeResult]) -> list[dict[str, Any]]:
    rows = []
    for condition, results, multiplier in (
        ("opponent_impact_on", on_results, 1.0),
        ("opponent_impact_off", off_results, 0.0),
    ):
        for row in raw_evaluation_rows(results):
            row["interaction_condition"] = condition
            row["opponent_impact_multiplier"] = multiplier
            rows.append(row)
    return rows


def summarize_interaction_ablation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, float, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["interaction_condition"], row["fee_bps"], row["B_opponent"], row["A_policy"])
        groups.setdefault(key, []).append(row)
    summary = []
    for (condition, fee, opponent, policy), group in sorted(groups.items()):
        costs = [float(x["implementation_shortfall_bps"]) for x in group]
        summary.append({
            "interaction_condition": condition, "opponent_impact_multiplier": group[0]["opponent_impact_multiplier"],
            "fee_bps": fee, "B_opponent": opponent, "A_policy": policy, "runs": len(group),
            "mean_total_implementation_shortfall_bps": statistics.mean(costs),
            "sd_total_implementation_shortfall_bps": statistics.stdev(costs) if len(costs) > 1 else 0.0,
            "mean_gross_execution_shortfall_bps": statistics.mean(float(x["gross_execution_shortfall_bps"]) for x in group),
            "mean_fee_cost_bps": statistics.mean(float(x["fee_cost_bps"]) for x in group),
            "mean_opportunity_cost_bps": statistics.mean(float(x["opportunity_cost_bps"]) for x in group),
            "mean_completion_rate": statistics.mean(float(x["completion_rate"]) for x in group),
            "wait_action_share": statistics.mean(float(x["wait_action_share"]) for x in group),
            "half_action_share": statistics.mean(float(x["half_action_share"]) for x in group),
            "base_action_share": statistics.mean(float(x["base_action_share"]) for x in group),
            "large_action_share": statistics.mean(float(x["large_action_share"]) for x in group),
        })
    return summary


def interaction_ablation_comparisons(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {(r["interaction_condition"], float(r["fee_bps"]), r["B_opponent"], int(r["seed"]), r["A_policy"]): r
               for r in rows}
    comparisons = []
    for fee in sorted(set(float(r["fee_bps"]) for r in rows)):
        for opponent in TEST_OPPONENTS:
            seeds = sorted(set(int(r["seed"]) for r in rows
                               if float(r["fee_bps"]) == fee and r["B_opponent"] == opponent))
            mode_deltas: dict[str, list[float]] = {}
            for condition in ("opponent_impact_on", "opponent_impact_off"):
                deltas = [
                    float(indexed[(condition, fee, opponent, seed, "G3_opponent_aware_Q")]["implementation_shortfall_bps"])
                    - float(indexed[(condition, fee, opponent, seed, "G2_Q_learning")]["implementation_shortfall_bps"])
                    for seed in seeds
                ]
                mode_deltas[condition] = deltas
                mean = statistics.mean(deltas) if deltas else 0.0
                sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
                half = 1.96 * sd / math.sqrt(len(deltas)) if deltas else 0.0
                comparisons.append({
                    "fee_bps": fee, "B_opponent": opponent, "interaction_condition": condition,
                    "paired_runs": len(deltas), "mean_G3_minus_G2_bps": mean,
                    "approx_95pct_ci_low_bps": mean - half, "approx_95pct_ci_high_bps": mean + half,
                })
            did = [off - on for off, on in zip(mode_deltas["opponent_impact_off"], mode_deltas["opponent_impact_on"])]
            did_mean = statistics.mean(did) if did else 0.0
            did_sd = statistics.stdev(did) if len(did) > 1 else 0.0
            did_half = 1.96 * did_sd / math.sqrt(len(did)) if did else 0.0
            comparisons.append({
                "fee_bps": fee, "B_opponent": opponent, "interaction_condition": "difference_in_differences",
                "paired_runs": len(did), "mean_G3_minus_G2_bps": did_mean,
                "approx_95pct_ci_low_bps": did_mean - did_half,
                "approx_95pct_ci_high_bps": did_mean + did_half,
            })
    return comparisons


def run_uniform_optimality_control(episodes: int, seeds: int, seed: int,
                                   config: Config) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Check the simulator in a zero-drift convex temporary-impact market."""
    control_config = replace(
        config, half_spread_bps=0.0, volatility_bps=0.0,
        permanent_impact_bps_per_slice=0.0, inventory_risk_weight=0.0,
        opponent_impact_multiplier=0.0, market_impact_multiplier=1.0,
    )
    learner, diagnostics = train_agent(0.0, False, episodes, seed + 80_000_000, control_config)
    rows = []
    for run_idx in range(seeds):
        common_seed = seed + 81_000_000 + run_idx * 101
        for policy in ("G0_TWAP", "G2_Q_learning"):
            result = run_episode(
                policy, "twap", 0.0, common_seed, control_config,
                learner if policy == "G2_Q_learning" else None,
                scenario_name="uniform_optimality_control",
            )
            rows.append({
                "policy": policy, "seed": common_seed,
                "total_implementation_shortfall_bps": result.cost_bps,
                "gross_execution_shortfall_bps": result.gross_cost_bps,
                "fee_cost_bps": result.fee_cost_bps,
                "opportunity_cost_bps": result.opportunity_cost_bps,
                "completion_rate": result.completion_rate,
                "unfilled_shares": result.unfilled_shares,
                "theoretical_uniform_cost_bps": (
                    control_config.temporary_impact_bps_per_slice *
                    control_config.market_impact_multiplier * control_config.step_minutes
                ),
            })
    by_seed = {}
    for row in rows:
        by_seed.setdefault(row["seed"], {})[row["policy"]] = row
    deltas = [v["G2_Q_learning"]["total_implementation_shortfall_bps"] -
              v["G0_TWAP"]["total_implementation_shortfall_bps"] for v in by_seed.values()]
    summary = {
        "episodes": episodes, "evaluation_seeds": seeds,
        "market": "zero drift, zero spread, zero fee, zero permanent impact, opponent impact off",
        "own_temporary_impact_bps_per_slice": control_config.temporary_impact_bps_per_slice,
        "theoretical_uniform_cost_bps": control_config.temporary_impact_bps_per_slice * control_config.step_minutes,
        "mean_G0_TWAP_cost_bps": statistics.mean(v["G0_TWAP"]["total_implementation_shortfall_bps"] for v in by_seed.values()),
        "mean_G2_cost_bps": statistics.mean(v["G2_Q_learning"]["total_implementation_shortfall_bps"] for v in by_seed.values()),
        "mean_G2_minus_G0_bps": statistics.mean(deltas) if deltas else 0.0,
        "sd_G2_minus_G0_bps": statistics.stdev(deltas) if len(deltas) > 1 else 0.0,
        "mean_G0_completion_rate": statistics.mean(v["G0_TWAP"]["completion_rate"] for v in by_seed.values()),
        "mean_G2_completion_rate": statistics.mean(v["G2_Q_learning"]["completion_rate"] for v in by_seed.values()),
    }
    return rows, summary, diagnostics


def build_findings(rows: list[dict[str, Any]], comparisons: list[dict[str, Any]],
                   diagnostics: list[dict[str, Any]], config: Config,
                   episodes: int, seeds: int,
                   regret_summary: list[dict[str, Any]],
                   ablation_comparisons: list[dict[str, Any]],
                   impact_summary: list[dict[str, Any]],
                   impact_comparisons: list[dict[str, Any]],
                   control_summary: dict[str, Any]) -> str:
    def pooled_stats(group: list[dict[str, Any]], mean_key: str,
                     low_key: str, high_key: str) -> tuple[float, float, float, int]:
        total_n = sum(int(row["paired_runs"]) for row in group)
        if total_n == 0:
            return 0.0, 0.0, 0.0, 0
        mean = sum(float(row[mean_key]) * int(row["paired_runs"]) for row in group) / total_n
        within_ss = 0.0
        for row in group:
            n = int(row["paired_runs"])
            half = (float(row[high_key]) - float(row[low_key])) / 2.0
            sd = half * math.sqrt(n) / 1.96 if n > 1 else 0.0
            within_ss += max(0, n - 1) * sd * sd
            within_ss += n * (float(row[mean_key]) - mean) ** 2
        pooled_sd = math.sqrt(within_ss / max(total_n - 1, 1))
        half_width = 1.96 * pooled_sd / math.sqrt(total_n)
        return mean, mean - half_width, mean + half_width, total_n

    hypothesis_defs = (
        ("H1：G1 − G0", "G1_dynamic_rule", "G0_TWAP"),
        ("H2：G2 − G1", "G2_Q_learning", "G1_dynamic_rule"),
        ("H3：G3 − G2", "G3_opponent_aware_Q", "G2_Q_learning"),
    )
    pooled_hypotheses = []
    for label, strategy, _baseline in hypothesis_defs:
        subset = [row for row in comparisons if row["strategy"] == strategy]
        pooled_hypotheses.append((label, *pooled_stats(
            subset, "mean_cost_difference_bps_strategy_minus_baseline",
            "approx_95pct_ci_low_bps", "approx_95pct_ci_high_bps")))
    ablation_stats = {
        condition: pooled_stats(
            [row for row in ablation_comparisons if row["interaction_condition"] == condition],
            "mean_G3_minus_G2_bps", "approx_95pct_ci_low_bps", "approx_95pct_ci_high_bps")
        for condition in ("opponent_impact_on", "opponent_impact_off", "difference_in_differences")
    }
    lines = [
        "# 多智能体交易执行系统：实验结果与研究假设核验", "",
        f"运行时间（UTC）：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"主实验环境：每方母单 {config.order_size:,.0f} 股，执行窗口 {config.window_minutes} 分钟、每 {config.step_seconds} 秒一步（共 {config.horizon} 步）。",
        f"训练预算：每个手续费档、每种学习器 {episodes} 回合；主评估：每个策略×对手×手续费×波动场景 {seeds} 个配对种子。", "",
        "## 研究问题与对照逻辑", "",
        "本研究不把固定 TWAP 称为‘非 Agent’。比较的是逐层增加的策略能力：G0 固定 TWAP → G1 反馈型动态规则 → G2 Q-learning → G3 加入对手历史行动的 Q-learning。",
        "H1 比较 G1−G0，检验动态反馈相对固定计划的增量；H2 比较 G2−G1，检验学习型策略相对动态规则的增量；H3 比较 G3−G2，并结合关闭 B 对价格影响的消融，检验对手信息是否带来增量。双边同时学习暂列扩展实验，不作为本轮主要结论。", "",
        "## 成本口径与公平性", "",
        "总实施缺口按初始中间价为基准，分为成交部分的毛执行缺口、显式手续费和未成交订单按期末中间价计量的机会成本。训练奖励还包含库存风险项及未完成惩罚，因此奖励和实际成本不可互换。报告同时给出完成率和未成交股数，防止策略通过少成交伪装低成本。",
        "所有策略共享母单、期限、离散动作集合和可行性约束。配对运行共享外生市场冲击及对手随机流；Agent 行为改变后产生的价格路径差异是市场内生反馈。置信区间是配对差值的正态近似 95% 区间。", "",
        "## 本次运行的总体观察", "",
        "下表把不同费用、波动场景和对手下的配对差值合并作描述性汇总；推断时仍应查看后面的分层结果。区间为近似值，未调整多重比较。", "",
        "| 假设对照 | 策略−基线成本差 bp | 近似 95% 区间 | 配对数 |", "|---|---:|---:|---:|"]
    for label, mean, low, high, n in pooled_hypotheses:
        lines.append(f"| {label} | {mean:.3f} | [{low:.3f}, {high:.3f}] | {n} |")
    on_mean, on_low, on_high, on_n = ablation_stats["opponent_impact_on"]
    off_mean, off_low, off_high, off_n = ablation_stats["opponent_impact_off"]
    did_mean, did_low, did_high, did_n = ablation_stats["difference_in_differences"]
    lines.extend([
        "",
        f"本轮完成率范围为 {min(float(r['mean_completion_rate']) for r in rows):.3f}–{max(float(r['mean_completion_rate']) for r in rows):.3f}，主实验未成交股数为 0。对手冲击开启时 G3−G2 为 {on_mean:.3f} bp [{on_low:.3f}, {on_high:.3f}]（n={on_n}）；关闭时为 {off_mean:.3f} bp [{off_low:.3f}, {off_high:.3f}]（n={off_n}）；差上差（关闭−开启）为 {did_mean:.3f} bp [{did_low:.3f}, {did_high:.3f}]（n={did_n}）。这些结果只说明当前模拟设定下的表现差异。",
        f"TWAP 反向检验中理论与实测 TWAP 成本为 {control_summary['theoretical_uniform_cost_bps']:.3f} / {control_summary['mean_G0_TWAP_cost_bps']:.3f} bp，Q-learning 为 {control_summary['mean_G2_cost_bps']:.3f} bp；Q-learning 没有系统性击败均匀执行基准，符合该控制设定的预期。", "",
        "## 主实验：各手续费档的汇总", "",
        "以下结果按策略、手续费和波动场景汇总，并对五类固定规则对手取平均。逐对手统计见 evaluation_summary.csv。", "",
        "| 手续费 | 场景 | A 策略 | 总缺口 bp | 毛执行缺口 bp | 手续费 bp | 机会成本 bp | 完成率 | 未成交股数 |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    fees = sorted(set(float(r["fee_bps"]) for r in rows))
    for fee in fees:
        for scenario, _ in SCENARIOS:
            for policy in POLICIES:
                subset = [r for r in rows if float(r["fee_bps"]) == fee and r["scenario"] == scenario and r["A_policy"] == policy]
                if not subset:
                    continue
                avg = lambda key: statistics.mean(float(r[key]) for r in subset)
                lines.append(f"| {fee/100:.1f}% | {scenario} | {policy} | {avg('mean_implementation_shortfall_bps'):.2f} | {avg('mean_gross_execution_shortfall_bps'):.2f} | {avg('mean_fee_cost_bps'):.2f} | {avg('mean_opportunity_cost_bps'):.2f} | {avg('mean_completion_rate'):.3f} | {avg('mean_unfilled_shares'):.1f} |")
    lines.extend(["", "## 主要假设的配对检验", "",
                  "成本差定义为策略成本减基线成本；负值有利于被比较策略。结果须结合区间、完成率和多重场景一致性解释，不能只挑选有利场景。", "",
                  "| 手续费 | 场景 | B 对手 | 检验 | 成本差 bp | 配对近似 95% 区间 | 完成率差 |",
                  "|---:|---|---|---|---:|---:|---:|"])
    for c in comparisons:
        lines.append(f"| {c['fee_bps']/100:.1f}% | {c['scenario']} | {c['B_opponent']} | {c['research_question']} | {c['mean_cost_difference_bps_strategy_minus_baseline']:.2f} | [{c['approx_95pct_ci_low_bps']:.2f}, {c['approx_95pct_ci_high_bps']:.2f}] | {c['mean_completion_rate_difference']:.3f} |")
    lines.extend(["", "## 对手影响消融：G3 相对 G2", "",
                  "差值为 G3 成本减 G2 成本；差上差为 (关闭对手影响时的 G3−G2)−(开启时的 G3−G2)。若结果未支持预期，需如实报告；关闭 B 冲击会同时改变环境中的竞争反馈。", "",
                  "| 手续费 | B 对手 | 条件 | G3−G2 bp | 近似 95% 区间 |",
                  "|---:|---|---|---:|---:|"])
    for c in ablation_comparisons:
        lines.append(f"| {c['fee_bps']/100:.1f}% | {c['B_opponent']} | {c['interaction_condition']} | {c['mean_G3_minus_G2_bps']:.2f} | [{c['approx_95pct_ci_low_bps']:.2f}, {c['approx_95pct_ci_high_bps']:.2f}] |")
    lines.extend(["", "## 市场冲击压力测试", "",
                  "该组将自身和对手交易冲击系数同时提高到基准的 2 倍，使用固定基准环境训练出的策略进行迁移测试。", "",
                  "| A 策略 | 平均总缺口 bp | 完成率 | 平均毛执行缺口 bp | 平均手续费 bp |", "|---|---:|---:|---:|---:|"])
    for policy in POLICIES:
        subset = [r for r in impact_summary if r["A_policy"] == policy]
        if subset:
            mean = lambda key: statistics.mean(float(r[key]) for r in subset)
            lines.append(f"| {policy} | {mean('mean_implementation_shortfall_bps'):.2f} | {mean('mean_completion_rate'):.3f} | {mean('mean_gross_execution_shortfall_bps'):.2f} | {mean('mean_fee_cost_bps'):.2f} |")
    lines.extend(["", "## 候选策略集内的后悔值", "",
                  "后悔值按同手续费、场景、固定对手和随机种子下 G0–G3 的最低实测成本计算，只代表相对本次候选集合的差距；它不是全局最优值，也不意味着达到纳什均衡。", "",
                  "| 策略 | 平均候选集后悔值 bp | 成为候选最佳策略的比例 | 平均完成率 |", "|---|---:|---:|---:|"])
    for policy in POLICIES:
        subset = [r for r in regret_summary if r["A_policy"] == policy]
        if subset:
            lines.append(f"| {policy} | {statistics.mean(float(r['mean_candidate_set_regret_bps']) for r in subset):.2f} | {statistics.mean(float(r['best_response_share_in_candidate_set']) for r in subset):.3f} | {statistics.mean(float(r['mean_completion_rate']) for r in subset):.3f} |")
    lines.extend(["", "## TWAP 最优性反向检验", "",
                  f"控制环境设为零价差、零波动、零永久冲击、零手续费和零对手冲击，仅保留凸性临时冲击。均匀 TWAP 理论成本为 {control_summary['theoretical_uniform_cost_bps']:.4f} bp；实测 TWAP 均值 {control_summary['mean_G0_TWAP_cost_bps']:.4f} bp，Q-learning 均值 {control_summary['mean_G2_cost_bps']:.4f} bp，Q−TWAP 配对差 {control_summary['mean_G2_minus_G0_bps']:.4f} bp。若 Q-learning 系统性优于理论基准，应先检查环境实现、动作限制和成本口径。", "",
                  "## 训练诊断", "", "| 手续费 | 学习器 | 训练回合 | 最近 100 回合奖励 | 前 100 回合奖励 | 初始状态 max Q | 访问状态数 |", "|---:|---|---:|---:|---:|---:|---:|"])
    for d in diagnostics:
        prev = "NA" if d["rolling_return_previous_100"] is None else f"{d['rolling_return_previous_100']:.2f}"
        lines.append(f"| {d['fee_bps']/100:.1f}% | {d['agent']} | {d['episodes']} | {d['rolling_return_last_100']:.2f} | {prev} | {d['initial_state_max_q']:.2f} | {d['visited_state_count']} |")
    lines.extend([
        "", "## 结果边界", "",
        "- 本项目是可复现的教学模拟器，并非历史行情回测：单一资产、单一时间步长、简化冲击方程和规则化对手。没有真实订单簿、排队撮合、隐藏流动性、市场制度、外部数据或实盘下单。",
        "- 当前核心架构是一个学习型执行机构 A 与一个固定规则机构 B 交互。G3 是对手感知策略，不等于 B 也在学习；双方同步 Q-learning 作为后续扩展。",
        "- G2/G3 在 TWAP、前置、后置规则对手中训练；bursty 与 randomized 只用于冻结策略的未见对手测试，测的是泛化而非在线适应。",
        "- 手续费作为显式成交成本计入。若所有订单必须完成且费率为常数，费率上升本身不会改变最优交易节奏；动态节奏主要由价格反馈和冲击环境驱动。",
        "- 结果不预设 Q-learning 或对手感知一定胜出。训练回报、Q 值和测试成本必须分别解释；没有通过收敛性检查的结果只能视为探索性。",
        "- RiskReviewAgent 只标记需要人工复核的模拟结果，不下真实订单。运行使用本地 Python 和固定随机流，不调用生成式模型 API。", "",
        "## 主要产物", "",
        "- evaluation_summary.csv、evaluation_raw.csv、paired_comparisons.csv：主实验汇总、逐种子结果和 H1–H3 配对比较。",
        "- opponent_impact_ablation_*.csv：对手冲击开关消融及 G3−G2 差上差。",
        "- market_impact_stress_*.csv：冲击系数翻倍压力测试与迁移评估。",
        "- candidate_set_regret*.csv：相对 G0–G3 候选集合的后悔值。",
        "- uniform_optimality_control*.csv：TWAP 最优性反向检验。",
        "- training_diagnostics.csv、qtable_*.json：训练诊断与可复用 Q 表。",
        "- sample_episode_trace.csv：30 秒一个决策步的逐步输入、判断、成交、反馈和业务解释。",
        "- run_manifest.json：完整参数、随机种子、数据规模与运行时间。", "",
    ])
    return "\n".join(lines)


def run_experiment(episodes: int, seeds: int, seed: int, config: Config) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    all_eval: list[EpisodeResult] = []
    diagnostics: list[dict[str, Any]] = []
    trained: dict[tuple[float, str], QLearningAgent] = {}
    fee_tiers = FEE_TIERS_BPS

    # Core design: for each fee tier train G2 and G3 against fixed scripted
    # opponents, then freeze both tables for a paired G0-G3 strategy matrix.
    for fee_index, fee in enumerate(fee_tiers):
        for learner_index, opponent_aware in enumerate((False, True)):
            learner_name = "G3_opponent_aware_Q" if opponent_aware else "G2_Q_learning"
            print(f"[训练] fee={fee/100:.1f}% agent={learner_name} episodes={episodes}", flush=True)
            agent, diag = train_agent(fee, opponent_aware, episodes,
                                      seed + fee_index * 100_000,
                                      config)
            diagnostics.append(diag)
            trained[(fee, learner_name)] = agent
            q_path = OUT / f"qtable_{learner_name}_{int(fee)}bps.json"
            q_path.write_text(json.dumps(serialize_q(agent), ensure_ascii=False, indent=2), encoding="utf-8")
            agent.freeze()

        for policy in POLICIES:
            q_agent = None if policy.startswith(("G0", "G1")) else trained[(fee, policy)]
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

    # Market-impact transfer test: retain policies trained at base impact and
    # double both temporary and permanent impact coefficients at evaluation.
    impact_config = replace(config, market_impact_multiplier=2.0)
    impact_stress_eval: list[EpisodeResult] = []
    for fee_index, fee in enumerate(fee_tiers):
        for policy in POLICIES:
            q_agent = None if policy.startswith(("G0", "G1")) else trained[(fee, policy)]
            for opponent_name in TEST_OPPONENTS:
                for run_idx in range(seeds):
                    common_seed = seed + 2_000_000 + fee_index * 1_000_000 + run_idx * 101
                    impact_stress_eval.append(run_episode(
                        policy, opponent_name, fee, common_seed, impact_config, q_agent,
                        scenario_name="high_market_impact", volatility_multiplier=1.0,
                    ))

    # Ablate B's contribution to price impact. G2 and G3 are trained and tested
    # separately in the no-opponent-impact world, matching their on-condition
    # training budgets; B's script and exogenous market seeds remain paired.
    interaction_on = [r for r in all_eval if r.scenario == "normal" and r.policy in
                      ("G2_Q_learning", "G3_opponent_aware_Q")]
    interaction_off_config = replace(config, opponent_impact_multiplier=0.0)
    interaction_off: list[EpisodeResult] = []
    interaction_off_diagnostics: list[dict[str, Any]] = []
    for fee_index, fee in enumerate(fee_tiers):
        for learner_index, opponent_aware in enumerate((False, True)):
            policy = "G3_opponent_aware_Q" if opponent_aware else "G2_Q_learning"
            print(f"[消融训练] opponent impact off fee={fee/100:.1f}% agent={policy}", flush=True)
            agent, diag = train_agent(
                fee, opponent_aware, episodes,
                seed + fee_index * 100_000,
                interaction_off_config,
            )
            diag["interaction_condition"] = "opponent_impact_off"
            interaction_off_diagnostics.append(diag)
            off_path = OUT / f"qtable_{policy}_{int(fee)}bps_opponent_impact_off.json"
            off_path.write_text(json.dumps(serialize_q(agent), ensure_ascii=False, indent=2), encoding="utf-8")
            for opponent_name in TEST_OPPONENTS:
                for run_idx in range(seeds):
                    common_seed = seed + 2_000_000 + fee_index * 1_000_000 + run_idx * 101
                    interaction_off.append(run_episode(
                        policy, opponent_name, fee, common_seed, interaction_off_config, agent,
                        scenario_name="normal", volatility_multiplier=1.0,
                    ))

    ablation_raw = interaction_ablation_rows(interaction_on, interaction_off)
    ablation_summary = summarize_interaction_ablation(ablation_raw)
    ablation_comparisons = interaction_ablation_comparisons(ablation_raw)

    # Theoretical negative control: with no drift, spread, fee, permanent
    # impact, or opponent impact, own temporary impact is convex in slice size.
    control_rows, control_summary, control_diagnostics = run_uniform_optimality_control(
        episodes, seeds, seed, config
    )

    summary_rows = aggregate(all_eval)
    comparison_rows = paired_comparisons(all_eval)
    regret_rows = candidate_set_regret_rows(all_eval)
    regret_summary = summarize_candidate_regret(regret_rows)
    impact_summary = aggregate(impact_stress_eval)
    impact_comparisons = paired_comparisons(impact_stress_eval, ("high_market_impact",))
    write_csv(OUT / "evaluation_summary.csv", summary_rows)
    write_csv(OUT / "paired_comparisons.csv", comparison_rows)
    write_csv(OUT / "evaluation_raw.csv", raw_evaluation_rows(all_eval))
    write_csv(OUT / "training_diagnostics.csv", diagnostics)
    write_csv(OUT / "candidate_set_regret.csv", regret_rows)
    write_csv(OUT / "candidate_set_regret_summary.csv", regret_summary)
    write_csv(OUT / "market_impact_stress_raw.csv", raw_evaluation_rows(impact_stress_eval))
    write_csv(OUT / "market_impact_stress_summary.csv", impact_summary)
    write_csv(OUT / "market_impact_stress_comparisons.csv", impact_comparisons)
    write_csv(OUT / "opponent_impact_ablation_raw.csv", ablation_raw)
    write_csv(OUT / "opponent_impact_ablation_summary.csv", ablation_summary)
    write_csv(OUT / "opponent_impact_ablation_comparisons.csv", ablation_comparisons)
    write_csv(OUT / "opponent_impact_off_training_diagnostics.csv", interaction_off_diagnostics)
    write_csv(OUT / "uniform_optimality_control.csv", control_rows)
    write_csv(OUT / "uniform_optimality_control_summary.csv", [control_summary])
    write_csv(OUT / "uniform_optimality_training_diagnostics.csv", [control_diagnostics])

    trace_fee = 50.0
    trace_agent = trained[(trace_fee, "G3_opponent_aware_Q")]
    sample = run_episode("G3_opponent_aware_Q", "bursty", trace_fee,
                         seed + 9_999_991, config, trace_agent, trace_enabled=True,
                         scenario_name="high_volatility", volatility_multiplier=2.0)
    write_csv(OUT / "sample_episode_trace.csv", sample.trace)

    total_eval_count = (len(all_eval) + len(impact_stress_eval) + len(interaction_off) + len(control_rows))
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
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
        "training_episode_count_primary": len(fee_tiers) * 2 * episodes,
        "training_episode_count_opponent_impact_ablation": len(fee_tiers) * 2 * episodes,
        "training_episode_count_uniform_control": episodes,
        "training_episode_count_total": len(fee_tiers) * 4 * episodes + episodes,
        "evaluation_seeds_per_policy_opponent_fee_scenario": seeds,
        "master_seed": seed,
        "primary_evaluation_episode_count": len(all_eval),
        "market_impact_stress_episode_count": len(impact_stress_eval),
        "opponent_impact_off_evaluation_episode_count": len(interaction_off),
        "uniform_control_evaluation_episode_count": len(control_rows),
        "total_evaluation_rows_across_experiments": total_eval_count,
        "market_impact_stress_multiplier": impact_config.market_impact_multiplier,
        "market_impact_stress_training": "policies are frozen from base-impact training",
        "opponent_impact_ablation_levels": [1.0, 0.0],
        "opponent_impact_ablation_training": "G2 and G3 are separately trained at each level using identical training seed schedules",
        "paired_random_streams": {"agent": "seed xor 0x13579BDF", "opponent": "seed xor 0x2468ACE0", "market": "seed xor 0x5DEECE66D"},
        "candidate_regret_scope": "relative to G0-G3 candidate policy set; not a global optimum or Nash equilibrium",
        "total_cost_definition": "gross fill shortfall + explicit fee cost + terminal opportunity cost on unfilled shares",
        "elapsed_seconds": round(time.time() - started, 3),
        "sample_trace_review_required": sample.review_required,
        "sample_trace_review_reason": sample.review_reason,
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "findings.md").write_text(
        build_findings(summary_rows, comparison_rows, diagnostics, config, episodes, seeds,
                       regret_summary, ablation_comparisons, impact_summary,
                       impact_comparisons, control_summary),
        encoding="utf-8",
    )
    print(f"[完成] {total_eval_count} 条评估记录；用时 {manifest['elapsed_seconds']} 秒。", flush=True)
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
