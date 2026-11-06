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
    make_observation,
)
from limit_order_book import (
    ChildOrder,
    Fill,
    SyntheticLOBConfig,
    deadline_urgency,
    make_market_tape,
    match_marketable_orders,
    match_passive_orders,
    queue_ahead_for_new_order,
    quote_for_action,
    terminal_completion_price,
)
from schedule_aware_q import LimitOrderAwareQLearningAgent


DEFAULT_OUT = Path(__file__).resolve().parent / "outputs" / "advanced_self_play_autonomous_completion"
SCENARIOS = (("normal", 1.0), ("high_volatility", 2.0))
ACTION_NAMES = (
    "hold_or_wait", "passive_half_deep", "passive_base_best_bid",
    "passive_1_5_inside_spread", "marketable_2x_limit_ioc",
)
LOB_CONFIG = SyntheticLOBConfig()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train two Q-learning execution agents simultaneously and evaluate frozen cross-play."
    )
    parser.add_argument("--episodes", type=int, default=500, help="training episodes per run")
    parser.add_argument("--training-runs", type=int, default=5, help="independent training seeds")
    parser.add_argument("--eval-seeds", type=int, default=30, help="paired evaluation seeds per cell")
    parser.add_argument("--checkpoint-interval", type=int, default=100)
    parser.add_argument("--fee-bps", type=float, default=30.0, help="one-way fee in basis points; 30bp = 0.3%%")
    parser.add_argument(
        "--schedule-deficit-penalty-bps", type=float, default=10.0,
        help="per-step learning penalty coefficient for falling behind the even-fill schedule",
    )
    parser.add_argument(
        "--terminal-unfilled-penalty-bps", type=float, default=1_000.0,
        help="terminal learning penalty per full-order fraction left unfilled or sent to the backstop",
    )
    parser.add_argument(
        "--deadline-c-mode", choices=("none", "stochastic", "learned"), default="none",
        help="none=ordinary Q actions; stochastic=randomized C; learned=Q agent learns C timing and measure",
    )
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument(
        "--completion-mode", choices=("autonomous", "none"), default="autonomous",
        help=("autonomous keeps every intraday action under Q-learning and uses a terminal "
              "completion backstop; none disables the backstop and does not guarantee completion"),
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    if args.episodes < 1 or args.training_runs < 1 or args.eval_seeds < 1:
        parser.error("episodes, training-runs, and eval-seeds must be positive")
    if args.checkpoint_interval < 1:
        parser.error("checkpoint-interval must be positive")
    if args.fee_bps < 0:
        parser.error("fee-bps cannot be negative")
    if args.schedule_deficit_penalty_bps < 0 or args.terminal_unfilled_penalty_bps < 0:
        parser.error("completion penalty coefficients cannot be negative")
    if args.output_dir is None:
        if args.completion_mode == "autonomous":
            suffix = ("autonomous_learned_c" if args.deadline_c_mode == "learned" else
                      "autonomous_stochastic_c" if args.deadline_c_mode == "stochastic" else
                      "autonomous_completion")
        else:
            suffix = ("no_completion_learned_c" if args.deadline_c_mode == "learned" else
                      "no_completion_stochastic_c" if args.deadline_c_mode == "stochastic" else
                      "no_completion")
        args.output_dir = Path(__file__).resolve().parent / "outputs" / f"advanced_self_play_{suffix}"
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
    payload = {
        "opponent_aware": agent.opponent_aware,
        "state_encoding": getattr(agent, "state_encoding", "exact_time_inventory_price_opponent_v0"),
        "q": {"|".join(map(str, state)): values for state, values in agent.q.items()},
        "action_visits": {
            "|".join(map(str, state)): counts for state, counts in agent.action_visits.items()
        },
    }
    if hasattr(agent, "scheme_c"):
        payload["scheme_c_policy"] = {
            "state_encoding": agent.scheme_c.state_encoding,
            "q": {"|".join(map(str, state)): values
                  for state, values in agent.scheme_c.q.items()},
            "action_visits": {"|".join(map(str, state)): counts
                              for state, counts in agent.scheme_c.action_visits.items()},
        }
    return payload


def snapshot_to_json(snap: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "state_encoding": snap["state_encoding"],
        "visited_state_count": snap["visited_state_count"],
        "q": {"|".join(map(str, state)): values for state, values in snap["q"].items()},
        "action_visits": {
            "|".join(map(str, state)): counts for state, counts in snap["visits"].items()
        },
    }
    if "scheme_c" in snap:
        payload["scheme_c_policy"] = {
            "state_encoding": snap["scheme_c"]["state_encoding"],
            "q": {"|".join(map(str, state)): values
                  for state, values in snap["scheme_c"]["q"].items()},
            "action_visits": {"|".join(map(str, state)): counts
                              for state, counts in snap["scheme_c"]["visits"].items()},
        }
    return payload


def snapshot(agent: QLearningAgent) -> dict[str, Any]:
    payload = {
        "state_encoding": getattr(agent, "state_encoding", "unknown"),
        "q": {state: values[:] for state, values in agent.q.items()},
        "visits": {state: counts[:] for state, counts in agent.action_visits.items()},
        "visited_state_count": len(agent.visited),
    }
    if hasattr(agent, "scheme_c"):
        payload["scheme_c"] = {
            "state_encoding": agent.scheme_c.state_encoding,
            "q": {state: values[:] for state, values in agent.scheme_c.q.items()},
            "visits": {state: counts[:] for state, counts in agent.scheme_c.action_visits.items()},
        }
    return payload


def frozen_action(agent: QLearningAgent, obs: Any, rng: random.Random) -> int:
    """Read a learned policy without mutating its Q table during evaluation."""
    state = (agent.state_key(obs) if hasattr(agent, "state_key")
             else discretize_state(obs, agent.opponent_aware))
    values = agent.q.get(state, [0.0] * len(ACTIONS))
    visits = agent.action_visits.get(state, [0] * len(ACTIONS))
    # The parent schedule cannot guarantee that a limit order fills. Keep all
    # actions available at evaluation rather than applying a false completion
    # floor derived from submitted quantity.
    allowed = [idx for idx in range(len(ACTIONS)) if visits[idx] > 0]
    if not allowed:
        return 2
    best_value = max(values[idx] for idx in allowed)
    tied = [idx for idx in allowed if abs(values[idx] - best_value) < 1e-12]
    return rng.choice(tied)


def _weighted_choice(draw: float, values: tuple[int, ...], weights: tuple[float, ...]) -> int:
    threshold = min(max(draw, 0.0), 1.0 - 1e-15)
    cumulative = 0.0
    for value, weight in zip(values, weights):
        cumulative += weight
        if threshold < cumulative:
            return value
    return values[-1]


def stochastic_c_decision(stage: str, remaining: float, step: int,
                          config: Config, draws: tuple[float, float, float, float]
                          ) -> tuple[int, int, float, bool, float]:
    """Sample a risk-conditioned C intervention for the current Q decision.

    C only enters after the linear schedule is missed. Its intervention chance,
    action floor, price escalation, and catch-up fraction all vary stochastically
    by deadline stage, with stronger pressure closer to the close.
    """
    # Randomized intervention becomes more likely and more aggressive as the
    # close approaches, but early interventions favor passive quotes to limit
    # taker fees and price impact. Each stage tuple is:
    # base probability, action floors/weights, quote ticks/weights, catch-up range.
    stages = {
        "early_autonomous_window": (
            0.12, (1, 2, 3), (0.10, 0.55, 0.35),
            (0, 1), (0.85, 0.15), (0.10, 0.30),
        ),
        "urgency_window": (
            0.32, (2, 3, 4), (0.12, 0.55, 0.33),
            (0, 1, 2), (0.62, 0.30, 0.08), (0.25, 0.55),
        ),
        "high_urgency_window": (
            0.60, (3, 4), (0.38, 0.62),
            (0, 1, 2, 3), (0.52, 0.28, 0.15, 0.05), (0.40, 0.80),
        ),
        "final_sweep_window": (
            0.88, (3, 4), (0.10, 0.90),
            (0, 1, 2, 3, 4, 5, 6), (0.24, 0.22, 0.18, 0.14, 0.10, 0.07, 0.05),
            (0.70, 1.00),
        ),
    }
    if stage not in stages:
        return 0, 0, 0.0, False, 0.0

    (base_probability, floor_values, floor_weights, tick_values, tick_weights,
     quantity_range) = stages[stage]
    schedule_remaining = config.order_size * max(config.horizon - step - 1, 0) / config.horizon
    deficit_slices = max(0.0, remaining - schedule_remaining) / max(config.base_slice, 1.0)
    probability = min(0.98, base_probability + min(0.20, deficit_slices * 0.03))
    gate_draw, floor_draw, tick_draw, quantity_draw = draws
    if gate_draw >= probability:
        return 0, 0, 0.0, False, probability

    floor = _weighted_choice(floor_draw, floor_values, floor_weights)
    ticks = _weighted_choice(tick_draw, tick_values, tick_weights)
    low, high = quantity_range
    catch_up_fraction = low + (high - low) * quantity_draw
    return floor, ticks, catch_up_fraction, True, probability


def episode(agent_a: QLearningAgent, agent_b: QLearningAgent, config: Config,
            seed: int, fee_bps: float, volatility_multiplier: float,
            epsilon: float = 0.0, training: bool = False,
            trace_rows: list[dict[str, Any]] | None = None,
            completion_mode: str = "autonomous",
            deadline_c_mode: str = "none") -> dict[str, Any]:
    """Run one synchronous episode with event-based limit-order execution."""
    if completion_mode not in {"autonomous", "none"}:
        raise ValueError("completion_mode must be 'autonomous' or 'none'")
    if deadline_c_mode not in {"none", "deterministic", "stochastic", "learned"}:
        raise ValueError("deadline_c_mode must be 'none', 'deterministic', 'stochastic', or 'learned'")
    if deadline_c_mode == "deterministic" and training:
        raise ValueError("Deterministic C is evaluation-only; use stochastic C to train the integrated policy")
    rng_a = random.Random(seed ^ 0x13579BDF)
    rng_b = random.Random(seed ^ 0x2468ACE0)
    tape = make_market_tape(
        seed, config.horizon, config.base_slice,
        config.step_volatility_bps * volatility_multiplier, LOB_CONFIG,
    )
    initial_mid = config.initial_price
    mid = initial_mid
    remaining = {"A": config.order_size, "B": config.order_size}
    fills = {"A": 0.0, "B": 0.0}
    submitted = {"A": 0.0, "B": 0.0}
    cancelled = {"A": 0.0, "B": 0.0}
    maker_fills = {"A": 0.0, "B": 0.0}
    taker_fills = {"A": 0.0, "B": 0.0}
    forced_fills = {"A": 0.0, "B": 0.0}
    forced_cost_contribution_bps = {"A": 0.0, "B": 0.0}
    schedule_deficit_penalty_total = {"A": 0.0, "B": 0.0}
    terminal_residual_penalty_total = {"A": 0.0, "B": 0.0}
    deadline_urgency_steps = {"A": 0, "B": 0}
    deadline_action_overrides = {"A": 0, "B": 0}
    deadline_c_interventions = {"A": 0, "B": 0}
    deadline_c_action_counts = {"A": Counter(), "B": Counter()}
    gross_cash = {"A": 0.0, "B": 0.0}
    fee_cash = {"A": 0.0, "B": 0.0}
    prev_qty = {"A": 0.0, "B": 0.0}
    total_reward = {"A": 0.0, "B": 0.0}
    action_counts = {"A": Counter(), "B": Counter()}
    orders: dict[str, ChildOrder | None] = {"A": None, "B": None}
    agents = {"A": agent_a, "B": agent_b}
    rngs = {"A": rng_a, "B": rng_b}
    c_rngs = {
        "A": random.Random(seed ^ 0x57C011A1),
        "B": random.Random(seed ^ 0x57C022B2),
    }
    c_meta_rngs = {
        "A": random.Random(seed ^ 0x57C033C3),
        "B": random.Random(seed ^ 0x57C044D4),
    }
    c_random_draws = {
        name: [tuple(c_rngs[name].random() for _ in range(4))
               for _ in range(config.horizon)]
        for name in ("A", "B")
    }

    for t in range(config.horizon):
        event = tape[t]
        tie_order = list(event["tie_order"])
        expired_qty = {"A": 0.0, "B": 0.0}
        for name in ("A", "B"):
            order = orders[name]
            if order is not None and t - order.created_step >= LOB_CONFIG.quote_ttl_steps:
                expired_qty[name] = order.remaining_qty
                cancelled[name] += order.remaining_qty
                orders[name] = None
            elif order is not None:
                best_ask = mid * (1.0 + config.half_spread_bps / 10_000.0)
                if not order.marketable and order.limit_price >= best_ask - 1e-10:
                    order.marketable = True
                    order.queue_ahead = 0.0
                    order.order_type = "resting_limit_became_marketable"

        mid_before = mid
        remaining_before = remaining.copy()
        prev_qty_before = prev_qty.copy()
        order_before = {
            name: None if orders[name] is None else {
                "remaining_qty": orders[name].remaining_qty,
                "limit_price": orders[name].limit_price,
                "queue_ahead": orders[name].queue_ahead,
                "age": t - orders[name].created_step,
                "order_type": orders[name].order_type,
            }
            for name in ("A", "B")
        }
        # Both observations use the same pre-trade mid and only prior-step
        # opponent activity. Each agent sees only its own current child order.
        observations = {
            name: make_observation(t, remaining[name], mid, initial_mid,
                                  prev_qty["B" if name == "A" else "A"],
                                  config, volatility_multiplier,
                                  open_order_qty=(orders[name].remaining_qty
                                                  if orders[name] else 0.0),
                                  queue_ahead=(orders[name].queue_ahead
                                               if orders[name] else 0.0),
                                  limit_price=(orders[name].limit_price
                                               if orders[name] else 0.0),
                                  order_age_steps=(t - orders[name].created_step
                                                   if orders[name] else 0))
            for name in ("A", "B")
        }
        action_idx: dict[str, int] = {}
        proposed_action_idx: dict[str, int] = {}
        action_floor: dict[str, int] = {"A": 0, "B": 0}
        urgency_ticks: dict[str, int] = {"A": 0, "B": 0}
        urgency_stage: dict[str, str] = {"A": "disabled", "B": "disabled"}
        c_intervened: dict[str, bool] = {"A": False, "B": False}
        c_probability: dict[str, float] = {"A": 0.0, "B": 0.0}
        c_quantity_fraction: dict[str, float] = {"A": 0.0, "B": 0.0}
        c_decision_idx: dict[str, int] = {"A": 0, "B": 0}
        for name in ("A", "B"):
            if training:
                proposed_action_idx[name] = agents[name].select(
                    observations[name], rngs[name], epsilon, 0
                )
            else:
                proposed_action_idx[name] = frozen_action(agents[name], observations[name], rngs[name])
            if deadline_c_mode == "learned":
                stage, _, behind = agents[name].scheme_c.stage_and_actions(observations[name])
                urgency_stage[name] = stage
                if behind:
                    deadline_urgency_steps[name] += 1
                c_decision_idx[name] = agents[name].scheme_c.select(
                    observations[name], c_meta_rngs[name], epsilon, training,
                )
                if c_decision_idx[name] > 0:
                    action_floor[name] = 4
                    urgency_ticks[name] = agents[name].scheme_c.quote_ticks[c_decision_idx[name]]
                    c_intervened[name] = True
            elif deadline_c_mode != "none":
                rule_floor, rule_ticks, urgency_stage[name] = deadline_urgency(
                    t, config.horizon, remaining[name], config.order_size,
                )
                if urgency_stage[name] != "on_schedule":
                    if deadline_c_mode == "deterministic":
                        if urgency_stage[name] != "early_autonomous_window":
                            deadline_urgency_steps[name] += 1
                            action_floor[name], urgency_ticks[name] = rule_floor, rule_ticks
                            c_intervened[name] = True
                            c_probability[name] = 1.0
                            c_quantity_fraction[name] = 1.0
                    else:
                        deadline_urgency_steps[name] += 1
                        (action_floor[name], urgency_ticks[name], c_quantity_fraction[name],
                         c_intervened[name], c_probability[name]) = stochastic_c_decision(
                            urgency_stage[name], remaining[name], t, config,
                            c_random_draws[name][t],
                        )
                elif deadline_c_mode == "stochastic":
                    c_probability[name] = 0.0
            else:
                urgency_stage[name] = "agent_autonomous"
            action_idx[name] = max(proposed_action_idx[name], action_floor[name])
            if action_idx[name] != proposed_action_idx[name]:
                deadline_action_overrides[name] += 1
            if c_intervened[name]:
                deadline_c_interventions[name] += 1
            c_action_label = (
                "on_schedule" if deadline_c_mode == "learned" and urgency_stage[name] == "on_schedule" else
                agents[name].scheme_c.action_names[c_decision_idx[name]]
                if deadline_c_mode == "learned" else
                "random_c" if c_intervened[name] and deadline_c_mode == "stochastic" else
                "deterministic_c" if c_intervened[name] and deadline_c_mode == "deterministic" else
                "no_c"
            )
            deadline_c_action_counts[name][c_action_label] += 1

        submitted_this_step = {"A": 0.0, "B": 0.0}
        policy_action_qty = {"A": 0.0, "B": 0.0}
        deadline_catch_up_qty = {"A": 0.0, "B": 0.0}
        replaced_qty = {"A": 0.0, "B": 0.0}
        order_type_this_step = {"A": "hold_or_wait", "B": "hold_or_wait"}
        limit_price_this_step: dict[str, float | None] = {"A": None, "B": None}
        # A and B choose from the same pre-trade snapshot. A deterministic
        # random tie order from the shared tape resolves equal-time queues.
        external_depths = event["bid_queue_depths"]
        for name in tie_order:
            idx = action_idx[name]
            if idx == 0:
                continue
            old = orders[name]
            if old is not None:
                replaced_qty[name] = old.remaining_qty
                cancelled[name] += old.remaining_qty
                orders[name] = None
            policy_action_qty[name] = min(remaining[name], config.base_slice * ACTIONS[idx])
            order_qty = policy_action_qty[name]
            if c_intervened[name] and idx > 0:
                steps_left = max(1, config.horizon - t)
                catch_up_qty = remaining[name] / steps_left
                order_qty = min(
                    remaining[name],
                    order_qty + c_quantity_fraction[name] * max(0.0, catch_up_qty - order_qty),
                )
                deadline_catch_up_qty[name] = max(0.0, order_qty - policy_action_qty[name])
            submitted_this_step[name] = order_qty
            submitted[name] += order_qty
            if order_qty <= 1e-9:
                continue
            limit_price, marketable, tier, order_type = quote_for_action(
                idx, mid, config.half_spread_bps, LOB_CONFIG.tick_bps,
                urgency_ticks[name],
            )
            limit_price_this_step[name] = limit_price
            order_type_this_step[name] = order_type
            queue_ahead = 0.0
            if not marketable:
                queue_ahead = queue_ahead_for_new_order(
                    limit_price, tier, mid, config.half_spread_bps,
                    LOB_CONFIG.tick_bps, external_depths,
                    [existing for existing in orders.values() if existing is not None],
                )
            orders[name] = ChildOrder(
                agent=name, limit_price=limit_price, remaining_qty=order_qty,
                queue_ahead=queue_ahead, created_step=t,
                priority=tie_order.index(name), action_index=idx,
                order_type=order_type, marketable=marketable,
            )

        marketable_orders = [order for order in orders.values()
                             if order is not None and order.marketable]
        taker_events = match_marketable_orders(
            marketable_orders, mid, config.half_spread_bps,
            LOB_CONFIG.tick_bps, event["ask_depths"], tie_order,
        )
        # Index 4 is IOC: any unfilled residual is cancelled immediately.
        ioc_cancelled = {"A": 0.0, "B": 0.0}
        for name in ("A", "B"):
            order = orders[name]
            if order is not None and order.marketable:
                if order.order_type.endswith("_ioc"):
                    ioc_cancelled[name] = order.remaining_qty
                    cancelled[name] += order.remaining_qty
                    orders[name] = None
                else:
                    # A previously resting GTC limit that becomes marketable
                    # may rest at its limit after visible asks are exhausted.
                    order.marketable = False
                    order.queue_ahead = 0.0
                    order.order_type = "resting_limit_after_crossing"

        maker_events = match_passive_orders(
            [order for order in orders.values() if order is not None],
            float(event["sell_flow"]), tie_order,
        )
        fill_events = taker_events + maker_events
        terminal = t == config.horizon - 1
        forced_completion_qty = {"A": 0.0, "B": 0.0}
        forced_completion_price: float | None = None
        forced_completion_impact_bps = 0.0
        if completion_mode == "autonomous" and terminal:
            regular_fills = {
                name: sum(fill.quantity for fill in fill_events if fill.agent == name)
                for name in ("A", "B")
            }
            forced_total = sum(
                max(0.0, remaining[name] - regular_fills[name])
                for name in ("A", "B")
            )
            if forced_total > 1e-9:
                forced_completion_price, forced_completion_impact_bps = terminal_completion_price(
                    mid, config.half_spread_bps, LOB_CONFIG.tick_bps, forced_total,
                    config.base_slice, config.temporary_impact_bps_per_slice,
                    config.market_impact_multiplier, config.step_minutes,
                )
                for name in ("A", "B"):
                    forced_completion_qty[name] = max(
                        0.0, remaining[name] - regular_fills[name]
                    )
                    if forced_completion_qty[name] > 1e-9:
                        forced_cost_contribution_bps[name] += (
                            forced_completion_qty[name]
                            * (forced_completion_price * (1 + fee_bps / 10_000.0) - initial_mid)
                            / (config.order_size * initial_mid) * 10_000.0
                        )
                        # Synthetic market-on-close backstop: residual shares are
                        # filled at one shared, impact-stressed terminal price.
                        fill_events.append(Fill(
                            name, forced_completion_qty[name],
                            forced_completion_price, "forced",
                        ))
                        submitted[name] += forced_completion_qty[name]
        aggressive_volume = sum(fill.quantity for fill in taker_events)
        temp_impact_bps = (
            config.temporary_impact_bps_per_slice
            * config.market_impact_multiplier * config.step_minutes
            * aggressive_volume / max(config.base_slice, 1.0)
        )
        rewards: dict[str, float] = {}
        actual_fill_this_step = {"A": 0.0, "B": 0.0}
        weighted_fill_cash = {"A": 0.0, "B": 0.0}
        for fill in fill_events:
            impact_adjustment = (temp_impact_bps if fill.liquidity == "taker" else 0.0)
            execution_price = fill.price * (1.0 + impact_adjustment / 10_000.0)
            fee_per_share = execution_price * fee_bps / 10_000.0
            actual_fill_this_step[fill.agent] += fill.quantity
            weighted_fill_cash[fill.agent] += fill.quantity * (execution_price + fee_per_share)
            gross_cash[fill.agent] += fill.quantity * execution_price
            fee_cash[fill.agent] += fill.quantity * fee_per_share
            if fill.liquidity == "maker":
                maker_fills[fill.agent] += fill.quantity
            elif fill.liquidity == "taker":
                taker_fills[fill.agent] += fill.quantity
            else:
                forced_fills[fill.agent] += fill.quantity

        for name in ("A", "B"):
            fills[name] += actual_fill_this_step[name]
            remaining[name] = max(0.0, remaining[name] - actual_fill_this_step[name])
            if remaining[name] <= max(1e-9, config.order_size * 1e-12):
                remaining[name] = 0.0
                if orders[name] is not None:
                    cancelled[name] += orders[name].remaining_qty
                    orders[name] = None
            elif orders[name] is not None and orders[name].remaining_qty <= 1e-9:
                orders[name] = None
            if actual_fill_this_step[name] > 0:
                avg_price_including_fee = weighted_fill_cash[name] / actual_fill_this_step[name]
                shortfall_bps = (avg_price_including_fee / initial_mid - 1) * 10_000.0
            else:
                shortfall_bps = 0.0
            # Economic execution reward is based on actual fills. The schedule
            # and terminal residual penalties are added to the learning reward.
            reward = -(actual_fill_this_step[name] / config.order_size) * shortfall_bps
            rewards[name] = reward
            action_counts[name][ACTION_NAMES[action_idx[name]]] += 1

        total_executed = actual_fill_this_step["A"] + actual_fill_this_step["B"]
        permanent_impact = (config.permanent_impact_bps_per_slice *
                            config.market_impact_multiplier * config.step_minutes *
                            total_executed / config.base_slice)
        shock_bps = float(event["shock_bps"])
        next_mid = mid * (1 + (shock_bps + permanent_impact) / 10_000.0)
        next_prev_qty = actual_fill_this_step.copy()
        deadline_cancelled = {"A": 0.0, "B": 0.0}
        if terminal:
            for name in ("A", "B"):
                if orders[name] is not None:
                    deadline_cancelled[name] = orders[name].remaining_qty
                    cancelled[name] += orders[name].remaining_qty
                    orders[name] = None
        next_observations = {
            name: None if terminal else make_observation(
                t + 1, remaining[name], next_mid, initial_mid,
                next_prev_qty["B" if name == "A" else "A"], config,
                volatility_multiplier,
                open_order_qty=(orders[name].remaining_qty if orders[name] else 0.0),
                queue_ahead=(orders[name].queue_ahead if orders[name] else 0.0),
                limit_price=(orders[name].limit_price if orders[name] else 0.0),
                order_age_steps=(t + 1 - orders[name].created_step if orders[name] else 0))
            for name in ("A", "B")
        }
        learning_rewards: dict[str, float] = {}
        reward_components: dict[str, dict[str, float]] = {}
        for name in ("A", "B"):
            terminal_residual_qty = (
                forced_completion_qty[name]
                if completion_mode == "autonomous" else remaining[name]
            ) if terminal else 0.0
            components = learning_reward_components(
                rewards[name], remaining[name], config, terminal, next_mid,
                initial_mid, t, terminal_residual_qty,
            )
            reward_components[name] = components
            learning_reward = components["learning_reward"]
            learning_rewards[name] = learning_reward
            total_reward[name] += learning_reward
            schedule_deficit_penalty_total[name] += components["schedule_deficit_penalty_bps"]
            terminal_residual_penalty_total[name] += components["terminal_residual_penalty_bps"]
        update_diagnostics: dict[str, dict[str, Any]] = {}
        if training:
            # Updates occur only after both current actions and the shared
            # market transition have been computed (simultaneous learning).
            for name in ("A", "B"):
                update_diagnostics[name] = agents[name].update(
                    observations[name], action_idx[name], learning_rewards[name],
                    next_observations[name]) or {}
                if deadline_c_mode == "learned":
                    _, c_allowed, _ = agents[name].scheme_c.stage_and_actions(observations[name])
                    if len(c_allowed) > 1:
                        agents[name].scheme_c.update(
                            observations[name], c_decision_idx[name], learning_rewards[name],
                            next_observations[name],
                        )
        if trace_rows is not None:
            for name in ("A", "B"):
                opponent_name = "B" if name == "A" else "A"
                components = reward_components[name]
                td_reward = components["learning_reward"]
                update = update_diagnostics.get(name, {})
                state = (agents[name].state_key(observations[name])
                         if hasattr(agents[name], "state_key")
                         else discretize_state(observations[name], agents[name].opponent_aware))
                trace_rows.append({
                    "trace_scope": "illustrative_post_checkpoint_online_update_not_aggregate_evaluation",
                    "seed": seed,
                    "scenario_multiplier": volatility_multiplier,
                    "step": t + 1,
                    "elapsed_seconds": t * config.step_seconds,
                    "agent": name,
                    "state_key": update.get("state_key", "|".join(map(str, state))),
                    "remaining_before_shares": remaining_before[name],
                    "opponent_previous_qty": prev_qty_before[opponent_name],
                    "mid_before": mid_before,
                    "proposed_action": ACTION_NAMES[proposed_action_idx[name]],
                    "action": ACTION_NAMES[action_idx[name]],
                    "action_multiplier": ACTIONS[action_idx[name]],
                    "deadline_c_mode": deadline_c_mode,
                    "deadline_c_decision": c_action_label,
                    "deadline_c_decision_available": (
                        deadline_c_mode == "learned" and urgency_stage[name] != "on_schedule"
                    ),
                    "deadline_c_state_key": (
                        "|".join(map(str, agents[name].scheme_c.state_key(observations[name])))
                        if deadline_c_mode == "learned" else None
                    ),
                    "deadline_c_q_values": (
                        json.dumps(agents[name].scheme_c.q.get(
                            agents[name].scheme_c.state_key(observations[name]),
                            [0.0] * len(agents[name].scheme_c.action_names),
                        )) if deadline_c_mode == "learned" else None
                    ),
                    "deadline_c_intervened": c_intervened[name],
                    "deadline_c_probability": c_probability[name],
                    "deadline_catch_up_fraction": c_quantity_fraction[name],
                    "deadline_action_floor": action_floor[name],
                    "deadline_urgency_ticks": urgency_ticks[name],
                    "deadline_urgency_stage": urgency_stage[name],
                    "policy_action_qty": policy_action_qty[name],
                    "deadline_catch_up_qty": deadline_catch_up_qty[name],
                    "order_type": order_type_this_step[name],
                    "limit_price": limit_price_this_step[name],
                    "submitted_qty": submitted_this_step[name],
                    "replaced_order_cancelled_qty": replaced_qty[name],
                    "expired_order_cancelled_qty": expired_qty[name],
                    "ioc_remainder_cancelled_qty": ioc_cancelled[name],
                    "deadline_cancelled_qty": deadline_cancelled[name],
                    "open_order_remaining_before": (order_before[name]["remaining_qty"]
                                                     if order_before[name] else 0.0),
                    "open_order_type_before": (order_before[name]["order_type"]
                                                if order_before[name] else None),
                    "queue_ahead_before": (order_before[name]["queue_ahead"]
                                            if order_before[name] else 0.0),
                    "order_age_before": (order_before[name]["age"]
                                         if order_before[name] else 0),
                    "sell_market_event_count": event["sell_event_count"],
                    "sell_market_flow_qty": event["sell_flow"],
                    "visible_ask_depth_level_1": event["ask_depths"][0],
                    "visible_ask_depth_level_2": event["ask_depths"][1],
                    "visible_ask_depth_level_3": event["ask_depths"][2],
                    "visible_ask_depth_level_4": event["ask_depths"][3],
                    "visible_ask_depth_level_5": event["ask_depths"][4],
                    "visible_ask_depth_level_6": event["ask_depths"][5],
                    "visible_ask_depth_level_7": event["ask_depths"][6],
                    "actual_filled_qty": actual_fill_this_step[name],
                    "joint_actual_filled_qty": total_executed,
                    "maker_filled_qty": sum(f.quantity for f in maker_events if f.agent == name),
                    "taker_filled_qty": sum(f.quantity for f in taker_events if f.agent == name),
                    "forced_completion_qty": forced_completion_qty[name],
                    "forced_completion_price": forced_completion_price,
                    "forced_completion_impact_bps": forced_completion_impact_bps,
                    "open_order_remaining_after": (orders[name].remaining_qty
                                                    if orders[name] else 0.0),
                    "queue_ahead_after": (orders[name].queue_ahead if orders[name] else 0.0),
                    "order_age_after": (t + 1 - orders[name].created_step
                                         if orders[name] else 0),
                    "temporary_impact_bps": temp_impact_bps,
                    "half_spread_bps": config.half_spread_bps,
                    "one_way_fee_bps": fee_bps,
                    "fill_price_including_fee": (weighted_fill_cash[name] /
                                                  actual_fill_this_step[name]
                                                  if actual_fill_this_step[name] else None),
                    "weighted_step_reward": rewards[name],
                    "schedule_deficit_penalty_bps": components["schedule_deficit_penalty_bps"],
                    "terminal_residual_penalty_bps": components["terminal_residual_penalty_bps"],
                    "terminal_opportunity_cost_adjustment_bps": components["terminal_opportunity_cost_bps"],
                    "learning_reward_adjustment": td_reward - rewards[name],
                    "td_reward": td_reward,
                    "gamma": config.discount,
                    "td_future_value": update.get("future_value"),
                    "td_target": update.get("td_target"),
                    "q_value_before": update.get("q_before"),
                    "q_value_after": update.get("q_after"),
                    "next_state_key": update.get("next_state_key"),
                    "external_shock_bps": shock_bps,
                    "permanent_impact_bps": permanent_impact,
                    "mid_after": next_mid,
                })
        prev_qty = next_prev_qty
        mid = next_mid

    cost: dict[str, float] = {}
    completion: dict[str, float] = {}
    unfilled: dict[str, float] = {}
    for name in ("A", "B"):
        unfilled[name] = max(0.0, config.order_size - fills[name])
        if unfilled[name] < max(1e-9, config.order_size * 1e-12):
            unfilled[name] = 0.0
        completion[name] = (1.0 if unfilled[name] == 0.0
                            else min(1.0, fills[name] / config.order_size))
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
        "submitted_A": submitted["A"], "submitted_B": submitted["B"],
        "filled_A": fills["A"], "filled_B": fills["B"],
        "maker_fills_A": maker_fills["A"], "maker_fills_B": maker_fills["B"],
        "taker_fills_A": taker_fills["A"], "taker_fills_B": taker_fills["B"],
        "forced_completion_A": forced_fills["A"],
        "forced_completion_B": forced_fills["B"],
        "forced_completion_cost_contribution_A_bps": forced_cost_contribution_bps["A"],
        "forced_completion_cost_contribution_B_bps": forced_cost_contribution_bps["B"],
        "deadline_urgency_steps_A": deadline_urgency_steps["A"],
        "deadline_urgency_steps_B": deadline_urgency_steps["B"],
        "deadline_action_overrides_A": deadline_action_overrides["A"],
        "deadline_action_overrides_B": deadline_action_overrides["B"],
        "deadline_c_interventions_A": deadline_c_interventions["A"],
        "deadline_c_interventions_B": deadline_c_interventions["B"],
        "deadline_c_actions_A": json.dumps(dict(deadline_c_action_counts["A"]), ensure_ascii=False, sort_keys=True),
        "deadline_c_actions_B": json.dumps(dict(deadline_c_action_counts["B"]), ensure_ascii=False, sort_keys=True),
        "schedule_deficit_penalty_A_bps": schedule_deficit_penalty_total["A"],
        "schedule_deficit_penalty_B_bps": schedule_deficit_penalty_total["B"],
        "terminal_residual_penalty_A_bps": terminal_residual_penalty_total["A"],
        "terminal_residual_penalty_B_bps": terminal_residual_penalty_total["B"],
        "cancelled_A": cancelled["A"], "cancelled_B": cancelled["B"],
        "reward_A": total_reward["A"], "reward_B": total_reward["B"],
        "actions_A": json.dumps(dict(action_counts["A"]), ensure_ascii=False, sort_keys=True),
        "actions_B": json.dumps(dict(action_counts["B"]), ensure_ascii=False, sort_keys=True),
    }


def learning_reward_components(step_reward: float, remaining: float, config: Config,
                               terminal: bool, terminal_mid: float,
                               initial_mid: float, step_index: int,
                               terminal_residual_qty: float = 0.0) -> dict[str, float]:
    """Add schedule-risk feedback and a terminal residual penalty to the fill reward.

    Before the last step, the schedule term penalizes shares left above the
    even-fill target for the remaining steps. At termination, the residual is
    the quantity that remains unfilled in ``none`` mode or is sent to the
    synthetic backstop in ``autonomous`` mode.
    """
    schedule_penalty_bps = 0.0
    terminal_penalty_bps = 0.0
    opportunity_cost_bps = 0.0
    if terminal:
        residual_fraction = max(0.0, terminal_residual_qty) / config.order_size
        terminal_penalty_bps = residual_fraction * config.terminal_unfilled_penalty_bps
        unfilled_fraction = max(0.0, remaining) / config.order_size
        opportunity_cost_bps = ((terminal_mid / initial_mid - 1.0)
                                * 10_000.0 * unfilled_fraction)
    else:
        steps_after = max(0, config.horizon - step_index - 1)
        schedule_remaining = config.base_slice * steps_after
        schedule_deficit = max(0.0, remaining - schedule_remaining)
        schedule_penalty_bps = (
            config.schedule_deficit_penalty_bps
            * schedule_deficit / config.order_size
        )
    learning_reward = (
        step_reward - schedule_penalty_bps - terminal_penalty_bps
        - opportunity_cost_bps
    )
    return {
        "learning_reward": learning_reward,
        "schedule_deficit_penalty_bps": schedule_penalty_bps,
        "terminal_residual_penalty_bps": terminal_penalty_bps,
        "terminal_opportunity_cost_bps": opportunity_cost_bps,
    }


def train_run(run_id: int, args: argparse.Namespace, config: Config) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], QLearningAgent, QLearningAgent]:
    run_seed = args.seed + run_id * 1_000_003
    agent_a = LimitOrderAwareQLearningAgent(config, opponent_aware=True)
    agent_b = LimitOrderAwareQLearningAgent(config, opponent_aware=True)
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
                         args.fee_bps, 1.0, epsilon=epsilon, training=True,
                         completion_mode=args.completion_mode,
                         deadline_c_mode=args.deadline_c_mode)
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
            "A_submitted_shares": result["submitted_A"], "B_submitted_shares": result["submitted_B"],
            "A_filled_shares": result["filled_A"], "B_filled_shares": result["filled_B"],
            "A_maker_filled_shares": result["maker_fills_A"], "B_maker_filled_shares": result["maker_fills_B"],
            "A_taker_filled_shares": result["taker_fills_A"], "B_taker_filled_shares": result["taker_fills_B"],
            "A_forced_completion_shares": result["forced_completion_A"],
            "B_forced_completion_shares": result["forced_completion_B"],
            "A_forced_completion_cost_contribution_bps": result["forced_completion_cost_contribution_A_bps"],
            "B_forced_completion_cost_contribution_bps": result["forced_completion_cost_contribution_B_bps"],
            "A_deadline_c_interventions": result["deadline_c_interventions_A"],
            "B_deadline_c_interventions": result["deadline_c_interventions_B"],
            "A_deadline_c_actions": result["deadline_c_actions_A"],
            "B_deadline_c_actions": result["deadline_c_actions_B"],
            "A_schedule_deficit_penalty_bps": result["schedule_deficit_penalty_A_bps"],
            "B_schedule_deficit_penalty_bps": result["schedule_deficit_penalty_B_bps"],
            "A_terminal_residual_penalty_bps": result["terminal_residual_penalty_A_bps"],
            "B_terminal_residual_penalty_bps": result["terminal_residual_penalty_B_bps"],
            "A_cancelled_shares": result["cancelled_A"], "B_cancelled_shares": result["cancelled_B"],
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
    agent = LimitOrderAwareQLearningAgent(config, opponent_aware=True)
    agent.q = {state: values[:] for state, values in snap["q"].items()}
    agent.action_visits = {state: counts[:] for state, counts in snap["visits"].items()}
    c_snap = snap.get("scheme_c")
    if c_snap is not None:
        agent.scheme_c.q = {state: values[:] for state, values in c_snap["q"].items()}
        agent.scheme_c.action_visits = {
            state: counts[:] for state, counts in c_snap["visits"].items()
        }
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
                                     volatility_multiplier, training=False,
                                     completion_mode=args.completion_mode,
                                     deadline_c_mode=args.deadline_c_mode)
                    rows.append({
                        "training_run": run_id, "A_checkpoint": a_cp, "B_checkpoint": b_cp,
                        "scenario": scenario, "seed": seed,
                        "cost_A_bps": result["cost_A_bps"], "cost_B_bps": result["cost_B_bps"],
                        "completion_A": result["completion_A"], "completion_B": result["completion_B"],
                        "unfilled_A": result["unfilled_A"], "unfilled_B": result["unfilled_B"],
                        "submitted_A": result["submitted_A"], "submitted_B": result["submitted_B"],
                        "filled_A": result["filled_A"], "filled_B": result["filled_B"],
                        "maker_fills_A": result["maker_fills_A"], "maker_fills_B": result["maker_fills_B"],
                        "taker_fills_A": result["taker_fills_A"], "taker_fills_B": result["taker_fills_B"],
                        "forced_completion_A": result["forced_completion_A"],
                        "forced_completion_B": result["forced_completion_B"],
                        "forced_completion_cost_contribution_A_bps": result["forced_completion_cost_contribution_A_bps"],
                        "forced_completion_cost_contribution_B_bps": result["forced_completion_cost_contribution_B_bps"],
                        "schedule_deficit_penalty_A_bps": result["schedule_deficit_penalty_A_bps"],
                        "schedule_deficit_penalty_B_bps": result["schedule_deficit_penalty_B_bps"],
                        "terminal_residual_penalty_A_bps": result["terminal_residual_penalty_A_bps"],
                        "terminal_residual_penalty_B_bps": result["terminal_residual_penalty_B_bps"],
                        "deadline_c_mode": args.deadline_c_mode,
                        "deadline_c_interventions_A": result["deadline_c_interventions_A"],
                        "deadline_c_interventions_B": result["deadline_c_interventions_B"],
                        "deadline_c_actions_A": result["deadline_c_actions_A"],
                        "deadline_c_actions_B": result["deadline_c_actions_B"],
                        "cancelled_A": result["cancelled_A"], "cancelled_B": result["cancelled_B"],
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
            "A_submitted_mean": statistics.fmean(r["submitted_A"] for r in group),
            "B_submitted_mean": statistics.fmean(r["submitted_B"] for r in group),
            "A_filled_mean": statistics.fmean(r["filled_A"] for r in group),
            "B_filled_mean": statistics.fmean(r["filled_B"] for r in group),
            "A_maker_fills_mean": statistics.fmean(r["maker_fills_A"] for r in group),
            "B_maker_fills_mean": statistics.fmean(r["maker_fills_B"] for r in group),
            "A_taker_fills_mean": statistics.fmean(r["taker_fills_A"] for r in group),
            "B_taker_fills_mean": statistics.fmean(r["taker_fills_B"] for r in group),
            "A_forced_completion_mean": statistics.fmean(r["forced_completion_A"] for r in group),
            "B_forced_completion_mean": statistics.fmean(r["forced_completion_B"] for r in group),
            "A_c_interventions_mean": statistics.fmean(r["deadline_c_interventions_A"] for r in group),
            "B_c_interventions_mean": statistics.fmean(r["deadline_c_interventions_B"] for r in group),
            "A_forced_completion_cost_contribution_mean_bps": statistics.fmean(r["forced_completion_cost_contribution_A_bps"] for r in group),
            "B_forced_completion_cost_contribution_mean_bps": statistics.fmean(r["forced_completion_cost_contribution_B_bps"] for r in group),
            "A_schedule_deficit_penalty_mean_bps": statistics.fmean(r["schedule_deficit_penalty_A_bps"] for r in group),
            "B_schedule_deficit_penalty_mean_bps": statistics.fmean(r["schedule_deficit_penalty_B_bps"] for r in group),
            "A_terminal_residual_penalty_mean_bps": statistics.fmean(r["terminal_residual_penalty_A_bps"] for r in group),
            "B_terminal_residual_penalty_mean_bps": statistics.fmean(r["terminal_residual_penalty_B_bps"] for r in group),
            "A_cancelled_mean": statistics.fmean(r["cancelled_A"] for r in group),
            "B_cancelled_mean": statistics.fmean(r["cancelled_B"] for r in group),
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
    if args.completion_mode == "autonomous":
        if args.deadline_c_mode == "learned":
            mode_note = (
                "- 盘中策略：Q-learning Agent 与独立 C 决策头共同学习。每个时间步若落后线性进度，C 决策头按精确时间、缺口、价格、挂单和对手近期成交状态选择暂不加急、IOC+1、IOC+3 或 IOC+6；"
                "42、51、57 步（约 20 分 30 秒、25 分钟、28 分钟）只是分析参照，Agent 可在任一落后时间点启动或等待。普通撮合后，终端兜底仅处理剩余母单。"
            )
            mode_label = "双边 Q-learning + 学习型 C 决策 + 终端完单兜底"
            output_path = "outputs/advanced_self_play_autonomous_learned_c"
        elif args.deadline_c_mode == "stochastic":
            mode_note = (
                "- 盘中策略：Q-learning Agent 先自主选动作；当进度落后时，随机 C 决策按阶段概率抽取动作下限、报价加价档和追赶数量比例；"
                "Q 表按最终实际执行的动作更新。收盘兜底只负责剩余未成交量，兜底量和成本单独报告。"
            )
            mode_label = "Q-learning + 随机 C 决策 + 终端完单兜底"
            output_path = "outputs/advanced_self_play_autonomous_stochastic_c"
        else:
            mode_note = (
                "- 完单方式：全程由 Q-learning Agent 自主选择 60 个时间步的动作、报价和常规子单数量；"
                "不按进度覆盖动作。第 60 步普通撮合后，环境只对剩余母单执行合成收盘兜底，因此模拟器内完成率为 100%；"
                "兜底成交量和成本单独报告，不能算作 Agent 自主成交。"
            )
            mode_label = "自主决策 + 终端完单兜底"
            output_path = "outputs/advanced_self_play_autonomous_completion"
    else:
        mode_note = (
            "- 完单方式：未启用终端完单兜底；所有盘中动作由 Q-learning 自主选择，订单可能无法按时完成。"
        )
        mode_label = "Agent 自主决策、无完单兜底"
        output_path = "outputs/advanced_self_play_no_completion"
    lines = [
        "# 双边同步 Q-learning：本轮运行记录", "",
        f"- 训练：{args.training_runs} 个独立种子，每个 {args.episodes} 回合；每回合 {Config().horizon} 个 30 秒时间步。",
        f"- 冻结交叉评估：每个训练运行 {len({r['A_checkpoint'] for r in summaries})} 个检查点，{args.eval_seeds} 个配对随机种子；单边手续费 {args.fee_bps:g} bp。",
        "- 训练在正常波动环境进行；训练检查点分别冻结后，在正常与 2 倍波动场景做交叉对局。",
        f"- 本结果属于路线 A（A/B 双边同步 Independent Q-learning）；路线 B 的规则引导 Double Q 对固定规则对手实验须单独报告。",
        f"- 当前单边费率为 {args.fee_bps:g} bp（{args.fee_bps / 100:g}%）；按初始价 {Config().initial_price:g}、每方母单 {Config().order_size:,.0f} 股估算，单家满额手续费约 {Config().initial_price * Config().order_size * args.fee_bps / 10_000:,.0f}。",
        f"- 完成惩罚：每步对落后均匀进度的数量按 {args.schedule_deficit_penalty_bps:g} bp 系数惩罚；终局对未完成量或送入收盘兜底的数量按 {args.terminal_unfilled_penalty_bps:g} bp 系数惩罚。该项属于学习奖励，不计入经济交易成本。",
        f"- 完单配置：{mode_label}。",
        mode_note,
        "- 普通执行仍是教学用事件驱动限价单：成交量由队列、可见卖盘和随机订单流决定；IOC 只触达其限价范围内的卖盘；终端兜底使用显式合成深层流动性价格曲线，并单独记录强制成交股数。",
        "- 本文件的数字仅是本次命令参数下的模拟结果，不自动代表收敛或现实市场效果。", "",
        "## 最终检查点的交叉对局", "",
              f"下表按训练运行和场景汇总 A/B 均采用最终检查点的对局。成本越低越好；当前完单模式为“{mode_label}”，并同时列出终端强制成交股数与其成本贡献。", "",
        "| 训练运行 | 场景 | A 成本 (bp) | A 完成率 | A 强制股数 | A 进度惩罚 (bp) | A 残余惩罚 (bp) | A 强制成本贡献 (bp) | B 成本 (bp) | B 完成率 | B 强制股数 | B 进度惩罚 (bp) | B 残余惩罚 (bp) | B 强制成本贡献 (bp) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run_id in sorted({r["training_run"] for r in summaries}):
        for scenario, _ in SCENARIOS:
            row = next(r for r in summaries if r["training_run"] == run_id and r["A_checkpoint"] == final_episode and r["B_checkpoint"] == final_episode and r["scenario"] == scenario)
            lines.append(
                f"| {run_id} | {scenario} | {row['A_cost_mean_bps']:.3f} | "
                f"{row['A_completion_mean']:.3f} | {row['A_forced_completion_mean']:.0f} | "
                f"{row['A_schedule_deficit_penalty_mean_bps']:.3f} | "
                f"{row['A_terminal_residual_penalty_mean_bps']:.3f} | "
                f"{row['A_forced_completion_cost_contribution_mean_bps']:.3f} | "
                f"{row['B_cost_mean_bps']:.3f} | {row['B_completion_mean']:.3f} | "
                f"{row['B_forced_completion_mean']:.0f} | "
                f"{row['B_schedule_deficit_penalty_mean_bps']:.3f} | "
                f"{row['B_terminal_residual_penalty_mean_bps']:.3f} | "
                f"{row['B_forced_completion_cost_contribution_mean_bps']:.3f} |"
            )
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
              "- A、B 在每步基于同一交易前快照同步决策，各自只能观察自身库存、上期对手成交量和自己的当前挂单；市场之后统一处理可成交限价单和卖方主动订单流。终端兜底数量不是 Agent 自主成交量。",
              "- 动作 0 保留已有报价或等待；动作 1–3 分别挂深档买单、最佳买价和价差内报价，动作 4 提交价格上限为卖一价上方一档的可成交限价 IOC。被动订单可部分成交并保留，队列在 4 个时间步（2 分钟）后过期；IOC 未成交余量立即撤销。",
              "- Q 状态包含时间阶段、执行进度、价格偏离、对手上期成交量、当前报价档位、挂单余量、队列前方数量和订单年龄。学习奖励按实际成交成本、每步进度缺口惩罚及终局残余惩罚计算；自主模式终局惩罚按收盘兜底前余量计算。纯 Q 模式下盘中实际动作等于 Agent 提出的动作；随机 C 模式下 Q 动作作为候选，最终执行动作可能经 C 抽样调整，Q 表按最终动作更新。下一状态只从已尝试动作中自举。训练中双方策略都变化，环境对单方而言仍是非平稳的。",
              "- 买方被动成交由卖方主动订单流穿过队列触发；IOC 限价单按各自报价上限消耗合成卖盘。手续费只按实际成交名义金额计算。",
              "- 检查点交叉对局把已保存的策略冻结后进行组合评估，避免评估过程继续改写 Q 表；配对种子共享外生价格冲击。",
              "- 稳定性要结合多训练种子的滚动奖励、成本波动、状态覆盖与检查点交叉结果判断。单一训练曲线变平不足以证明收敛。",
              "- 历史资料若使用 0.3 bp 或 30 个时间步，未按当前手续费和 60 步配置重跑前不得与本结果并表。",
              "- 可用 export_self_play_trace.py 从保存的最终检查点生成一条额外的 A/B 同步动作、市场反馈和 Q 更新样例；说明性轨迹不进入本次交叉评估统计。",
              f"- 本次模式结果写入 {output_path}；无兜底模式和硬完单模式的完成约束不同，不能仅按成本高低直接排序。规则策略配对比较仍由 run_matched_rule_q_comparison.py 单独生成，并须使用相同限价簿和完成约束重新评估。",
              "- 该环境是未用真实行情校准的合成订单簿，不含完整撮合交易所规则、隐藏流动性或实盘接口；队列深度、订单流和收盘深层流动性兜底均为显式模拟假设。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    started = time.time()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    config = Config(
        inventory_risk_weight=0.0,
        schedule_deficit_penalty_bps=args.schedule_deficit_penalty_bps,
        terminal_unfilled_penalty_bps=args.terminal_unfilled_penalty_bps,
    )
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
    lob_path = Path(__file__).with_name("limit_order_book.py")
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
        "limit_order_book_sha256": hashlib.sha256(lob_path.read_bytes()).hexdigest(),
        "parameters": {"episodes": args.episodes, "training_runs": args.training_runs,
                       "eval_seeds": args.eval_seeds, "checkpoint_interval": args.checkpoint_interval,
                       "fee_bps": args.fee_bps,
                       "schedule_deficit_penalty_bps": args.schedule_deficit_penalty_bps,
                       "terminal_unfilled_penalty_bps": args.terminal_unfilled_penalty_bps,
                       "deadline_c_mode": args.deadline_c_mode,
                       "seed": args.seed,
                       "output_dir": output_dir_record},
        "config": {**asdict(config), "horizon_steps": config.horizon,
                   "training_scenarios": ["normal"],
                   "evaluation_scenarios": {name: mult for name, mult in SCENARIOS}},
        "method": {
            "research_route": "Route A: simultaneous two-sided Independent Q-learning; rule-guided Double Q against fixed opponents is a separately reported Route B extension",
            "agent_A": "opponent-aware tabular Q-learning with schedule-aware state aggregation",
            "agent_B": "opponent-aware tabular Q-learning with schedule-aware state aggregation",
            "state_encoding": LimitOrderAwareQLearningAgent.state_encoding,
            "reward_alignment": "implementation shortfall on actual fills; per-step penalty for schedule deficit; terminal residual penalty applies to unfilled shares in none mode or backstop shares in autonomous mode; the terminal penalty is a learning signal, not economic cost",
            "untried_action_bootstrap": "only tried actions are included in next-state bootstrap; learned Scheme C maintains a separate Q table and action visitation counts",
            "simultaneous_action_and_update": True,
            "execution_model": "synthetic event-driven limit-order book with partial fills, persistent passive orders, queue ahead, seven displayed ask levels, sell-market order flow, TTL expiry, IOC cancellation, and an optional impact-priced market-on-close backstop",
            "submission_vs_execution": "submitted child quantity is not treated as filled; parent inventory falls only by matched execution quantity",
            "completion_mode": args.completion_mode,
            "deadline_c_mode": args.deadline_c_mode,
            "deadline_c_integration": (
                "a separate exact-time tabular Q head learns no-C, IOC+1, IOC+3, or IOC+6 at any lagging decision step; the regular Q agent learns order placement simultaneously using the resulting shared execution reward"
                if args.deadline_c_mode == "learned" else
                "stochastic C perturbations participate in the Q behavior policy; the Q update uses the final action index executed"
                if args.deadline_c_mode == "stochastic" else
                "disabled; Q-learning actions are used directly"
            ),
            "deadline_c_policy": ({
                "decision_owner": "learned SchemeCDecisionPolicy Q head; not a fixed calendar trigger",
                "activation": "available at every time step only when remaining inventory exceeds the linear remaining-time target including the current step",
                "state": "exact time step, remaining-inventory-to-schedule ratio bin, price-deviation bin, own resting-order state, and previous opponent fill bin",
                "actions": {
                    "0": "no C intervention; ordinary Q-selected action executes",
                    "1": "raise action floor to IOC and add 1 tick above the ordinary IOC quote",
                    "2": "raise action floor to IOC and add 3 ticks above the ordinary IOC quote",
                    "3": "raise action floor to IOC and add 6 ticks above the ordinary IOC quote",
                },
                "reference_elapsed_time_nodes": {
                    "step_42": "20m30s; analysis marker only",
                    "step_51": "25m00s; analysis marker only",
                    "step_57": "28m00s; analysis marker only",
                },
                "learning": "the separate C-Q head is updated from the same realized per-step execution reward as the order-placement Q head; exploration uses the run epsilon",
                "c_head_state_encoding": LimitOrderAwareQLearningAgent.state_encoding + "+scheme_c_meta_exact_time_v1",
                "terminal_completion": "the learned C policy reduces residual through ordinary order-book executions but does not guarantee completion; autonomous mode still uses a separately counted terminal backstop",
            } if args.deadline_c_mode == "learned" else {
                "activation": "only when behind the post-decision linear schedule",
                "base_probability_by_stage": {
                    "early_autonomous_window": 0.12,
                    "urgency_window": 0.32,
                    "high_urgency_window": 0.60,
                    "final_sweep_window": 0.88,
                },
                "deficit_probability_increment_per_base_slice": 0.03,
                "deficit_increment_cap": 0.20,
                "probability_cap": 0.98,
                "action_floor_distributions": {
                    "early_autonomous_window": {"1": 0.10, "2": 0.55, "3": 0.35},
                    "urgency_window": {"2": 0.12, "3": 0.55, "4": 0.33},
                    "high_urgency_window": {"3": 0.38, "4": 0.62},
                    "final_sweep_window": {"3": 0.10, "4": 0.90},
                },
                "quote_tick_distributions": {
                    "early_autonomous_window": {"0": 0.85, "1": 0.15},
                    "urgency_window": {"0": 0.62, "1": 0.30, "2": 0.08},
                    "high_urgency_window": {"0": 0.52, "1": 0.28, "2": 0.15, "3": 0.05},
                    "final_sweep_window": {"0": 0.24, "1": 0.22, "2": 0.18, "3": 0.14, "4": 0.10, "5": 0.07, "6": 0.05},
                },
                "catch_up_fraction_uniform_range_by_stage": {
                    "early_autonomous_window": [0.10, 0.30],
                    "urgency_window": [0.25, 0.55],
                    "high_urgency_window": [0.40, 0.80],
                    "final_sweep_window": [0.70, 1.00],
                },
                "q_update_uses_final_action_index": True,
            } if args.deadline_c_mode == "stochastic" else None),
            "completion_constraint": (
                "hard completion by a synthetic market-on-close backstop; Q-learning controls all intraday actions and residual quantity is filled at an impact-stressed average price"
                if args.completion_mode == "autonomous" else
                "none; actual completion rate is an outcome and terminal unfilled shares incur opportunity cost plus penalty"
            ),
            "terminal_backstop_price": "half-spread + tick_bps*sqrt(forced_qty/base_slice) + temporary_impact_bps_per_slice*market_impact_multiplier*step_minutes*(forced_qty/base_slice)" if args.completion_mode == "autonomous" else None,
            "limit_order_parameters": asdict(LOB_CONFIG),
            "fee_economic_interpretation": f"{args.fee_bps:g} bp one-way = {args.fee_bps / 100:g}% of traded notional",
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
