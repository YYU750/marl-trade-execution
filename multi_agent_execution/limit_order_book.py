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
    ask_depth_mean_base_slices: tuple[float, ...] = (0.80, 0.55)
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
                     tick_bps: float) -> tuple[float, bool, int, str]:
    """Map the five Q actions to hold/wait, passive quotes, or a capped IOC.

    Action 0 is handled by the caller. Indices 1-3 place passive limits at a
    deep bid, the best bid, or one tick inside the spread. Index 4 submits a
    marketable limit capped one tick above the best ask; any amount that cannot
    execute against the two visible ask levels is cancelled (IOC remainder).
    """
    tick = mid * tick_bps / 10_000.0
    best_bid = mid * (1.0 - half_spread_bps / 10_000.0)
    best_ask = mid * (1.0 + half_spread_bps / 10_000.0)
    if action_index == 1:
        return best_bid - tick, False, 2, "passive_deep_limit"
    if action_index == 2:
        return best_bid, False, 1, "passive_best_bid_limit"
    if action_index == 3:
        return best_bid + tick, False, 0, "passive_inside_spread_limit"
    if action_index == 4:
        return best_ask + tick, True, -1, "marketable_limit_ioc"
    raise ValueError(f"Action index {action_index} does not place a quote")


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
