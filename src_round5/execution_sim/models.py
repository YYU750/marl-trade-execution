from __future__ import annotations

import math
from dataclasses import dataclass


def _finite_nonnegative(name: str, value: float) -> None:
    if not math.isfinite(float(value)) or float(value) < 0:
        raise ValueError(f"{name} must be finite and nonnegative")


@dataclass(frozen=True)
class SimulationConfig:
    horizon_steps: int = 30
    initial_order_shares: int = 100_000
    initial_mid_price: float = 100.0
    full_spread_bps: float = 6.0
    liquidity_shares: int = 20_000
    volatility_bps: float = 2.0
    temporary_impact_bps_per_liquidity_unit: float = 2.0
    permanent_impact_bps_per_liquidity_unit: float = 0.6
    max_trade_per_step: int = 10_000
    fee_bps: float = 0.3
    terminal_penalty_per_share: float = 0.25
    enforce_completion: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.horizon_steps, bool) or not isinstance(self.horizon_steps, int):
            raise ValueError("horizon_steps must be an integer")
        if isinstance(self.initial_order_shares, bool) or not isinstance(self.initial_order_shares, int):
            raise ValueError("initial_order_shares must be an integer")
        if isinstance(self.liquidity_shares, bool) or not isinstance(self.liquidity_shares, int):
            raise ValueError("liquidity_shares must be an integer")
        if isinstance(self.max_trade_per_step, bool) or not isinstance(self.max_trade_per_step, int):
            raise ValueError("max_trade_per_step must be an integer")
        if self.horizon_steps < 1:
            raise ValueError("horizon_steps must be positive")
        if self.initial_order_shares < 0:
            raise ValueError("initial_order_shares cannot be negative")
        if not math.isfinite(float(self.initial_mid_price)) or self.initial_mid_price <= 0:
            raise ValueError("initial_mid_price must be positive")
        if self.liquidity_shares <= 0:
            raise ValueError("liquidity_shares must be positive")
        if self.max_trade_per_step < 1:
            raise ValueError("max_trade_per_step must be positive")
        for name in (
            "full_spread_bps",
            "volatility_bps",
            "temporary_impact_bps_per_liquidity_unit",
            "permanent_impact_bps_per_liquidity_unit",
            "fee_bps",
            "terminal_penalty_per_share",
        ):
            _finite_nonnegative(name, getattr(self, name))
        if not isinstance(self.enforce_completion, bool):
            raise ValueError("enforce_completion must be bool")
        if self.enforce_completion and self.initial_order_shares > self.horizon_steps * self.max_trade_per_step:
            raise ValueError("order cannot be completed within horizon and per-step cap")


@dataclass(frozen=True)
class MarketSnapshot:
    step: int
    mid_price: float
    full_spread_bps: float
    liquidity_shares: int
    steps_remaining: int
    horizon_steps: int
    max_trade_per_step: int = 10_000


@dataclass(frozen=True)
class AgentObservation:
    agent_id: str
    market: MarketSnapshot
    initial_order_shares: int
    remaining_shares: int
    initial_mid_price: float = 100.0
    minimum_required_shares: int = 0


@dataclass(frozen=True)
class Transition:
    """Reserved transition shape for a future learning agent."""

    observation: AgentObservation
    action_shares: float
    reward: float
    next_observation: AgentObservation | None
    done: bool


@dataclass(frozen=True)
class DiscreteActionSpace:
    """Future learner action contract: fraction of remaining order per step."""

    fractions: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)

    def __post_init__(self) -> None:
        if not self.fractions or any(value < 0 or value > 1 for value in self.fractions):
            raise ValueError("fractions must be nonempty and lie in [0, 1]")
        if tuple(sorted(set(self.fractions))) != self.fractions:
            raise ValueError("fractions must be sorted and unique")
