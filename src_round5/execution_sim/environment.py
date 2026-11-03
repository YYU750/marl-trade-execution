from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Mapping

from execution_sim.models import AgentObservation, MarketSnapshot, SimulationConfig


@dataclass(frozen=True)
class AgentStepResult:
    agent_id: str
    action_requested_shares: float
    completion_constraint_shares: int
    minimum_required_shares: int
    filled_shares: int
    remaining_shares: int
    fill_price: float
    realized_fill_shortfall: float
    spread_cost_component: float
    temporary_impact_cost_component: float
    unfilled_opportunity_cost: float
    fee: float
    terminal_penalty: float
    total_objective: float
    reward: float


@dataclass(frozen=True)
class MarketStepResult:
    snapshot: MarketSnapshot
    mid_price_after: float
    terminal_reference_price: float | None
    joint_filled_shares: int
    exogenous_shock_bps: float
    temporary_impact_bps: float
    permanent_impact_bps: float
    agents: Mapping[str, AgentStepResult]


class MarketEnvironment:
    """Synchronous, full-fill market simulator with explicit objective components."""

    AGENTS = ("A", "B")

    def __init__(self, config: SimulationConfig, seed: int) -> None:
        self.config = config
        self.seed = seed
        self._rng = random.Random(seed)
        self.initial_mid_price = config.initial_mid_price
        self.mid_price = config.initial_mid_price
        self.step_index = 0
        self.remaining = {agent_id: config.initial_order_shares for agent_id in self.AGENTS}
        self._snapshot: MarketSnapshot | None = None
        self._reset_totals()

    def _reset_totals(self) -> None:
        self._totals = {
            agent_id: {
                "realized_fill_shortfall": 0.0,
                "unfilled_opportunity_cost": 0.0,
                "fees": 0.0,
                "terminal_penalty": 0.0,
                "total_objective": 0.0,
                "filled_shares": 0,
            }
            for agent_id in self.AGENTS
        }

    @property
    def done(self) -> bool:
        return self.step_index >= self.config.horizon_steps

    def reset(self, seed: int | None = None) -> MarketSnapshot:
        if seed is not None:
            self.seed = seed
        self._rng = random.Random(self.seed)
        self.mid_price = self.initial_mid_price
        self.step_index = 0
        self.remaining = {agent_id: self.config.initial_order_shares for agent_id in self.AGENTS}
        self._snapshot = None
        self._reset_totals()
        return self.observe_market()

    def _minimum_required(self, agent_id: str, steps_remaining: int) -> int:
        if not self.config.enforce_completion:
            return 0
        return max(0, self.remaining[agent_id] - (steps_remaining - 1) * self.config.max_trade_per_step)

    def observe(self, agent_id: str) -> AgentObservation:
        if agent_id not in self.AGENTS:
            raise KeyError(agent_id)
        market = self.observe_market()
        return AgentObservation(
            agent_id=agent_id,
            market=market,
            initial_order_shares=self.config.initial_order_shares,
            remaining_shares=self.remaining[agent_id],
            initial_mid_price=self.initial_mid_price,
            minimum_required_shares=self._minimum_required(agent_id, market.steps_remaining),
        )

    def observe_market(self) -> MarketSnapshot:
        if self.done:
            raise RuntimeError("cannot observe after the episode has ended")
        if self._snapshot is None:
            self._snapshot = MarketSnapshot(
                step=self.step_index,
                mid_price=self.mid_price,
                full_spread_bps=self.config.full_spread_bps,
                liquidity_shares=self.config.liquidity_shares,
                steps_remaining=self.config.horizon_steps - self.step_index,
                horizon_steps=self.config.horizon_steps,
                max_trade_per_step=self.config.max_trade_per_step,
            )
        return self._snapshot

    def step(self, actions: Mapping[str, float], snapshot: MarketSnapshot | None = None) -> MarketStepResult:
        if self.done:
            raise RuntimeError("episode has ended")
        snapshot = self.observe_market() if snapshot is None else snapshot
        if snapshot is not self._snapshot:
            raise ValueError("both actions must use the current shared market snapshot")
        if set(actions) != set(self.AGENTS):
            raise ValueError("actions must contain exactly agents A and B")

        quantities: dict[str, int] = {}
        required: dict[str, int] = {}
        constrained: dict[str, int] = {}
        for agent_id in self.AGENTS:
            requested = float(actions[agent_id])
            if not math.isfinite(requested) or requested < 0:
                raise ValueError("requested quantities must be finite and nonnegative")
            clipped = min(math.floor(requested), self.remaining[agent_id], self.config.max_trade_per_step)
            minimum = self._minimum_required(agent_id, snapshot.steps_remaining)
            if minimum > self.config.max_trade_per_step:
                raise RuntimeError("completion constraint is infeasible at this step")
            filled = max(clipped, minimum)
            quantities[agent_id] = filled
            required[agent_id] = minimum
            constrained[agent_id] = filled - clipped

        joint_qty = sum(quantities.values())
        impact_scale = joint_qty / self.config.liquidity_shares
        temporary_bps = self.config.temporary_impact_bps_per_liquidity_unit * impact_scale
        permanent_bps = self.config.permanent_impact_bps_per_liquidity_unit * impact_scale
        half_spread_bps = self.config.full_spread_bps / 2.0
        fill_price = snapshot.mid_price * (1.0 + (half_spread_bps + temporary_bps) / 10_000.0)
        shock_bps = self._rng.gauss(0.0, self.config.volatility_bps)
        next_mid = snapshot.mid_price * math.exp((shock_bps + permanent_bps) / 10_000.0)
        terminal = snapshot.steps_remaining == 1
        terminal_reference = next_mid if terminal else None

        agent_results: dict[str, AgentStepResult] = {}
        for agent_id in self.AGENTS:
            quantity = quantities[agent_id]
            self.remaining[agent_id] -= quantity
            remaining_after = self.remaining[agent_id]
            realized = quantity * (fill_price - self.initial_mid_price)
            fee = quantity * fill_price * self.config.fee_bps / 10_000.0
            opportunity = remaining_after * (next_mid - self.initial_mid_price) if terminal else 0.0
            penalty = remaining_after * self.config.terminal_penalty_per_share if terminal else 0.0
            objective = realized + opportunity + fee + penalty
            reward = -objective
            spread_component = quantity * snapshot.mid_price * half_spread_bps / 10_000.0
            temporary_component = quantity * snapshot.mid_price * temporary_bps / 10_000.0
            totals = self._totals[agent_id]
            totals["realized_fill_shortfall"] += realized
            totals["unfilled_opportunity_cost"] += opportunity
            totals["fees"] += fee
            totals["terminal_penalty"] += penalty
            totals["total_objective"] += objective
            totals["filled_shares"] += quantity
            agent_results[agent_id] = AgentStepResult(
                agent_id=agent_id,
                action_requested_shares=float(actions[agent_id]),
                completion_constraint_shares=constrained[agent_id],
                minimum_required_shares=required[agent_id],
                filled_shares=quantity,
                remaining_shares=remaining_after,
                fill_price=fill_price,
                realized_fill_shortfall=realized,
                spread_cost_component=spread_component,
                temporary_impact_cost_component=temporary_component,
                unfilled_opportunity_cost=opportunity,
                fee=fee,
                terminal_penalty=penalty,
                total_objective=objective,
                reward=reward,
            )

        self.mid_price = next_mid
        self.step_index += 1
        self._snapshot = None
        return MarketStepResult(
            snapshot=snapshot,
            mid_price_after=next_mid,
            terminal_reference_price=terminal_reference,
            joint_filled_shares=joint_qty,
            exogenous_shock_bps=shock_bps,
            temporary_impact_bps=temporary_bps,
            permanent_impact_bps=permanent_bps,
            agents=agent_results,
        )

    def final_metrics(self, agent_id: str) -> dict[str, float | int | None]:
        if agent_id not in self.AGENTS:
            raise KeyError(agent_id)
        if not self.done:
            raise RuntimeError("final metrics are available only after the horizon")
        totals = self._totals[agent_id]
        filled = int(totals["filled_shares"])
        remaining = self.remaining[agent_id]
        initial_qty = self.config.initial_order_shares
        initial_notional = initial_qty * self.initial_mid_price
        return {
            "agent_id": agent_id,
            "filled_shares": filled,
            "unfilled_shares": remaining,
            "fill_ratio": filled / initial_qty if initial_qty else 1.0,
            "realized_fill_shortfall": float(totals["realized_fill_shortfall"]),
            "unfilled_opportunity_cost": float(totals["unfilled_opportunity_cost"]),
            "fees": float(totals["fees"]),
            "terminal_penalty": float(totals["terminal_penalty"]),
            "total_objective": float(totals["total_objective"]),
            "total_objective_bps_of_initial_notional": float(totals["total_objective"]) / initial_notional * 10_000.0 if initial_notional else 0.0,
            "average_fill_price": None if filled == 0 else self._average_fill_price(agent_id),
        }

    def _average_fill_price(self, agent_id: str) -> float:
        totals = self._totals[agent_id]
        filled = int(totals["filled_shares"])
        return self.initial_mid_price + float(totals["realized_fill_shortfall"]) / filled
