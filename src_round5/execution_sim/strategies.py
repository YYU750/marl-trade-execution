from __future__ import annotations

import math
from abc import ABC, abstractmethod

from execution_sim.models import AgentObservation, Transition


class Strategy(ABC):
    name: str

    @abstractmethod
    def act(self, observation: AgentObservation) -> float:
        """Return a continuous desired buy quantity in shares."""

    def learn(self, transition: Transition) -> None:
        """Future learning hook; no learning algorithm is implemented here."""
        del transition
        raise NotImplementedError("learning is outside the first-stage prototype")


class TWAPStrategy(Strategy):
    name = "twap"

    def act(self, observation: AgentObservation) -> float:
        if observation.market.steps_remaining == 1:
            return float(observation.remaining_shares)
        return observation.initial_order_shares / observation.market.horizon_steps


class FrontLoadedStrategy(Strategy):
    name = "front_loaded"

    def act(self, observation: AgentObservation) -> float:
        market = observation.market
        if market.steps_remaining == 1:
            return float(observation.remaining_shares)
        front_steps = max(1, math.ceil(market.horizon_steps / 2) - market.step)
        return observation.remaining_shares / min(market.steps_remaining, front_steps)


class BackLoadedStrategy(Strategy):
    name = "back_loaded"

    def act(self, observation: AgentObservation) -> float:
        market = observation.market
        if market.steps_remaining == 1:
            return float(observation.remaining_shares)
        start_step = market.horizon_steps // 2
        if market.step < start_step:
            return 0.0
        return observation.remaining_shares / market.steps_remaining


class SpreadUrgencyStrategy(Strategy):
    name = "spread_urgency"

    def __init__(self, spread_scale_bps: float = 6.0, urgency_strength: float = 2.0) -> None:
        if spread_scale_bps <= 0 or urgency_strength < 0:
            raise ValueError("spread_scale_bps must be positive and urgency_strength nonnegative")
        self.spread_scale_bps = spread_scale_bps
        self.urgency_strength = urgency_strength

    def act(self, observation: AgentObservation) -> float:
        market = observation.market
        remaining = observation.remaining_shares
        if market.steps_remaining == 1:
            return float(remaining)
        pace = remaining / market.steps_remaining
        elapsed_fraction = market.step / market.horizon_steps
        urgency = 1.0 + self.urgency_strength * elapsed_fraction
        spread_fraction = market.full_spread_bps / self.spread_scale_bps
        spread_adjustment = 1.0 / (1.0 + spread_fraction)
        return min(float(remaining), pace * urgency * spread_adjustment)


STRATEGY_FACTORIES = {
    TWAPStrategy.name: TWAPStrategy,
    FrontLoadedStrategy.name: FrontLoadedStrategy,
    BackLoadedStrategy.name: BackLoadedStrategy,
    SpreadUrgencyStrategy.name: SpreadUrgencyStrategy,
}


def make_strategy(name: str) -> Strategy:
    try:
        return STRATEGY_FACTORIES[name]()
    except KeyError as exc:
        raise ValueError(f"unknown strategy: {name}") from exc
