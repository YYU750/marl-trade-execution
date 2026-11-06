"""Small event-driven limit-order matching model for the bilateral simulator.

This is a transparent synthetic order book for coursework experiments, not a
calibrated exchange simulator. It represents displayed queue ahead, partial
fills, price priority, order persistence, marketable limit orders, and random
order-flow events using only the Python standard library.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SyntheticLOBConfig:
    tick_bps: float = 1.0
    quote_ttl_steps: int = 4
    # Displayed external bid depth, from the inside quote outwards, in base
    # TWAP slices. Each new child order joins behind the cumulative depth.
    passive_queue_mean_base_slices: tuple[float, ...] = (0.12, 0.65, 1.10)
    sell_market_events_per_step: float = 1.5
    sell_order_mean_base_slices: float = 0.70
    sell_order_log_sigma: float = 0.55
    # The first two levels support ordinary capped IOC orders. Deeper synthetic
    # Deeper levels are reachable only when a strategy or optional legacy
    # deadline overlay submits a sufficiently high limit price.
    ask_depth_mean_base_slices: tuple[float, ...] = (
        0.80, 0.55, 0.40, 0.30, 0.22, 0.16, 0.12,
    )
    ask_depth_log_sigma: float = 0.35


@dataclass
class ChildOrder:
    agent: str
    limit_price: float
    remaining_qty: float
    queue_ahead: float
    created_step: int
    priority: int
    action_index: int
    order_type: str
    marketable: bool = False


@dataclass(frozen=True)
class Fill:
    agent: str
    quantity: float
    price: float
    liquidity: str


def _poisson(rng: random.Random, mean: float) -> int:
    """Knuth sampler; suitable for the small per-step event rate here."""
    if mean <= 0:
        return 0
    threshold = math.exp(-mean)
    product = 1.0
    count = 0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


def make_market_tape(seed: int, horizon: int, base_slice: float,
                     step_volatility_bps: float,
                     lob: SyntheticLOBConfig) -> list[dict[str, object]]:
    """Pre-generate common exogenous events for paired strategy evaluation."""
    rng = random.Random(seed ^ 0x5DEECE66D)
    tape: list[dict[str, object]] = []
    for _ in range(horizon):
        event_count = _poisson(rng, lob.sell_market_events_per_step)
        sell_sizes = [
            base_slice * rng.lognormvariate(
                math.log(lob.sell_order_mean_base_slices)
                - 0.5 * lob.sell_order_log_sigma**2,
                lob.sell_order_log_sigma,
            )
            for _ in range(event_count)
        ]
        queue_depths = [
            base_slice * rng.lognormvariate(
                math.log(mean) - 0.5 * lob.ask_depth_log_sigma**2,
                lob.ask_depth_log_sigma,
            )
            for mean in lob.passive_queue_mean_base_slices
        ]
        ask_depths = [
            base_slice * rng.lognormvariate(
                math.log(mean) - 0.5 * lob.ask_depth_log_sigma**2,
                lob.ask_depth_log_sigma,
            )
            for mean in lob.ask_depth_mean_base_slices
        ]
        tape.append({
            "shock_bps": rng.gauss(0.0, step_volatility_bps),
            "sell_event_count": event_count,
            "sell_event_sizes": sell_sizes,
            "sell_flow": sum(sell_sizes),
            "bid_queue_depths": queue_depths,
            "ask_depths": ask_depths,
            "tie_order": rng.sample(("A", "B"), 2),
        })
    return tape


def quote_for_action(action_index: int, mid: float, half_spread_bps: float,
                     tick_bps: float,
                     urgency_ticks: int = 0) -> tuple[float, bool, int, str]:
    """Map the five Q actions to hold/wait, passive quotes, or a capped IOC.

    Action 0 is handled by the caller. Indices 1-3 place passive limits at a
    deep bid, the best bid, or one tick inside the spread. Index 4 submits a
    marketable limit capped one tick above the best ask. When the deadline
    guard is active, quotes move upward by ``urgency_ticks``; a passive quote
    that crosses the ask becomes an IOC. Execution is capped by visible ask
    levels priced within the limit; any unfilled IOC remainder is cancelled.
    """
    urgency_ticks = max(0, int(urgency_ticks))
    tick = mid * tick_bps / 10_000.0
    best_bid = mid * (1.0 - half_spread_bps / 10_000.0)
    best_ask = mid * (1.0 + half_spread_bps / 10_000.0)
    if action_index == 1:
        price, tier, order_type = best_bid - tick, 2, "passive_deep_limit"
    elif action_index == 2:
        price, tier, order_type = best_bid, 1, "passive_best_bid_limit"
    elif action_index == 3:
        price, tier, order_type = best_bid + tick, 0, "passive_inside_spread_limit"
    elif action_index == 4:
        price = best_ask + (1 + urgency_ticks) * tick
        return price, True, -1, "marketable_limit_ioc"
    else:
        raise ValueError(f"Action index {action_index} does not place a quote")

    price += urgency_ticks * tick
    if price >= best_ask - 1e-10:
        return price, True, -1, "deadline_marketable_limit_ioc"
    if price >= best_bid + tick - 1e-10:
        tier = 0
    elif price >= best_bid - 1e-10:
        tier = 1
    else:
        tier = 2
    return price, False, tier, order_type


def deadline_urgency(step: int, horizon: int, remaining: float,
                     order_size: float) -> tuple[int, int, str]:
    """Return a minimum action, quote-price escalation and stage for a late order.

    The guard only overrides the learned action when the agent is behind a
    linear completion schedule. It leaves early decisions to the Q policy,
    then submits progressively less restrictive capped IOC limits at 70%,
    85%, and 95% of the horizon.
    """
    if horizon <= 0 or order_size <= 0:
        raise ValueError("horizon and order_size must be positive")
    steps_after_this = max(0, horizon - step - 1)
    schedule_remaining = order_size * steps_after_this / horizon
    behind_schedule = remaining > schedule_remaining + max(1e-9, order_size * 1e-12)
    if not behind_schedule:
        return 0, 0, "on_schedule"

    progress = (step + 1) / horizon
    if progress >= 0.95:
        return 4, 6, "final_sweep_window"
    if progress >= 0.85:
        return 4, 3, "high_urgency_window"
    if progress >= 0.70:
        # Start with a shallow marketable limit so the first deadline stage
        # changes execution probability, not just the passive queue tier.
        return 4, 1, "urgency_window"
    return 0, 0, "early_autonomous_window"


def terminal_completion_price(mid: float, half_spread_bps: float,
                              tick_bps: float, forced_qty: float,
                              base_slice: float,
                              temporary_impact_bps_per_slice: float,
                              market_impact_multiplier: float,
                              step_minutes: float) -> tuple[float, float]:
    """Price a synthetic market-on-close backstop for any residual parent order.

    The backstop uses a transparent synthetic deep-liquidity curve because the
    displayed two-level ask book may be smaller than the compulsory residual.
    Its concession combines square-root tick walking with linear temporary
    impact. It is an explicit modelling assumption, not a real-exchange fill.
    Returns (average execution price, impact concession in basis points).
    """
    if mid <= 0 or base_slice <= 0 or forced_qty < 0:
        raise ValueError("mid/base_slice must be positive and forced_qty non-negative")
    slices = forced_qty / base_slice
    impact_bps = (tick_bps * math.sqrt(slices)
                  + temporary_impact_bps_per_slice
                  * market_impact_multiplier * step_minutes * slices)
    price = mid * (1.0 + (half_spread_bps + impact_bps) / 10_000.0)
    return price, impact_bps


def queue_ahead_for_new_order(price: float, tier: int, mid: float,
                              half_spread_bps: float, tick_bps: float,
                              external_depths: Iterable[float],
                              earlier_orders: Iterable[ChildOrder]) -> float:
    """Estimate displayed volume ahead using cumulative depth and priority."""
    depths = list(external_depths)
    external_ahead = sum(depths[:tier + 1])
    own_ahead = sum(
        order.remaining_qty for order in earlier_orders
        if order.remaining_qty > 0 and order.limit_price >= price - 1e-10
    )
    return external_ahead + own_ahead


def match_marketable_orders(orders: Iterable[ChildOrder], mid: float,
                            half_spread_bps: float, tick_bps: float,
                            ask_depths: Iterable[float], tie_order: Iterable[str]) -> list[Fill]:
    """Sweep visible ask levels by price/time priority; partial fills allowed."""
    tick = mid * tick_bps / 10_000.0
    best_ask = mid * (1.0 + half_spread_bps / 10_000.0)
    asks = [(best_ask + level * tick, depth)
            for level, depth in enumerate(ask_depths)]
    available = [depth for _, depth in asks]
    side_priority = {name: index for index, name in enumerate(tie_order)}
    marketable = sorted(
        (order for order in orders if order.marketable and order.remaining_qty > 0),
        key=lambda order: (-order.limit_price, order.created_step,
                           side_priority.get(order.agent, order.priority)),
    )
    fills: list[Fill] = []
    for order in marketable:
        for level, (ask_price, _) in enumerate(asks):
            if order.remaining_qty <= 1e-9 or ask_price > order.limit_price + 1e-10:
                continue
            quantity = min(order.remaining_qty, available[level])
            if quantity <= 1e-9:
                continue
            fills.append(Fill(order.agent, quantity, ask_price, "taker"))
            order.remaining_qty -= quantity
            available[level] -= quantity
    return fills


def match_passive_orders(orders: Iterable[ChildOrder], sell_flow: float,
                         tie_order: Iterable[str]) -> list[Fill]:
    """Consume one shared sell-market flow through resting bids and their queues."""
    side_priority = {name: index for index, name in enumerate(tie_order)}
    resting = sorted(
        (order for order in orders
         if not order.marketable and order.remaining_qty > 1e-9),
        key=lambda order: (-order.limit_price, order.created_step,
                           side_priority.get(order.agent, order.priority)),
    )
    initial_flow = max(0.0, sell_flow)
    flow_left = initial_flow
    fills: list[Fill] = []
    for order in resting:
        consumed_before = initial_flow - flow_left
        ahead_now = max(0.0, order.queue_ahead - consumed_before)
        queue_consumed = min(flow_left, ahead_now)
        flow_left -= queue_consumed
        consumed_total = initial_flow - flow_left
        order.queue_ahead = max(0.0, order.queue_ahead - consumed_total)
        if flow_left <= 1e-9:
            continue
        quantity = min(order.remaining_qty, flow_left)
        if quantity <= 1e-9:
            continue
        fills.append(Fill(order.agent, quantity, order.limit_price, "maker"))
        order.remaining_qty -= quantity
        flow_left -= quantity
    return fills
