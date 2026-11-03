from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from execution_sim.models import AgentObservation, Transition
from execution_sim.strategies import Strategy


def _finite(name: str, value: float) -> None:
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class QLearningConfig:
    alpha: float = 0.25
    gamma: float = 1.0
    epsilon_start: float = 0.25
    epsilon_min: float = 0.02
    epsilon_decay: float = 0.995
    action_multipliers: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0)
    spread_bins_bps: tuple[float, ...] = (0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 20.0)
    mid_deviation_bins_bps: tuple[float, ...] = (-100.0, -50.0, -20.0, -10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0)
    liquidity_ratio_bins: tuple[float, ...] = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
    remaining_ratio_bins: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (("alpha", self.alpha), ("gamma", self.gamma), ("epsilon_start", self.epsilon_start), ("epsilon_min", self.epsilon_min), ("epsilon_decay", self.epsilon_decay)):
            _finite(name, value)
        if not 0 < self.alpha <= 1:
            raise ValueError("alpha must lie in (0, 1]")
        if not 0 <= self.gamma <= 1:
            raise ValueError("gamma must lie in [0, 1]")
        if not 0 <= self.epsilon_min <= self.epsilon_start <= 1:
            raise ValueError("epsilon values must satisfy 0 <= min <= start <= 1")
        if not 0 < self.epsilon_decay <= 1:
            raise ValueError("epsilon_decay must lie in (0, 1]")
        self._validate_edges("action_multipliers", self.action_multipliers, lower=0.0)
        self._validate_edges("spread_bins_bps", self.spread_bins_bps, lower=0.0)
        self._validate_edges("mid_deviation_bins_bps", self.mid_deviation_bins_bps)
        self._validate_edges("liquidity_ratio_bins", self.liquidity_ratio_bins, lower=0.0)
        if self.remaining_ratio_bins:
            self._validate_edges("remaining_ratio_bins", self.remaining_ratio_bins, lower=0.0, upper=1.0)

    @staticmethod
    def _validate_edges(name: str, values: tuple[float, ...], lower: float | None = None, upper: float | None = None) -> None:
        if not values or tuple(sorted(set(values))) != values:
            raise ValueError(f"{name} must be nonempty, sorted and unique")
        for value in values:
            _finite(name, value)
            if lower is not None and value < lower:
                raise ValueError(f"{name} contains value below {lower}")
            if upper is not None and value > upper:
                raise ValueError(f"{name} contains value above {upper}")


class StateEncoder:
    """Encode time, own inventory, spread and observable mid-price deviation."""

    def __init__(self, config: QLearningConfig) -> None:
        self.config = config

    @staticmethod
    def _bin(value: float, edges: tuple[float, ...]) -> int:
        for index, edge in enumerate(edges):
            if value <= edge:
                return index
        return len(edges)

    def encode(self, observation: AgentObservation) -> tuple[int, int, int, int, int, int]:
        market = observation.market
        if observation.initial_mid_price <= 0 or not math.isfinite(observation.initial_mid_price):
            raise ValueError("observation initial mid price must be finite and positive")
        if not math.isfinite(market.mid_price) or not math.isfinite(market.full_spread_bps):
            raise ValueError("observation market values must be finite")
        mid_deviation_bps = (market.mid_price / observation.initial_mid_price - 1.0) * 10_000.0
        liquidity_ratio = market.liquidity_shares / observation.initial_order_shares if observation.initial_order_shares else 0.0
        remaining_state = int(observation.remaining_shares)
        if self.config.remaining_ratio_bins:
            remaining_ratio = observation.remaining_shares / max(1, observation.initial_order_shares)
            remaining_state = self._bin(remaining_ratio, self.config.remaining_ratio_bins)
        return (
            int(market.steps_remaining),
            remaining_state,
            self._bin(market.full_spread_bps, self.config.spread_bins_bps),
            self._bin(mid_deviation_bps, self.config.mid_deviation_bins_bps),
            self._bin(liquidity_ratio, self.config.liquidity_ratio_bins),
            int(market.max_trade_per_step),
        )


class TabularQLearningAgent(Strategy):
    name = "q_learning_round4"

    def __init__(self, config: QLearningConfig | None = None, seed: int = 0) -> None:
        self.config = config or QLearningConfig()
        self.encoder = StateEncoder(self.config)
        self.q_table: dict[tuple[int, int, int, int, int, int], list[float]] = {}
        self.visit_counts: dict[tuple[int, int, int, int, int, int], list[int]] = {}
        self.rng = random.Random(seed)
        self.epsilon = self.config.epsilon_start
        self.episodes_seen = 0
        self.frozen = False

    def _values(self, state: tuple[int, int, int, int, int, int], create: bool = True) -> list[float]:
        values = self.q_table.get(state)
        if values is None:
            if not create:
                return [0.0] * len(self.config.action_multipliers)
            values = [0.0] * len(self.config.action_multipliers)
            self.q_table[state] = values
        if len(values) != len(self.config.action_multipliers) or any(not math.isfinite(value) for value in values):
            raise ValueError("Q values must be finite and match the action count")
        return values

    def q_values(self, observation: AgentObservation) -> list[float]:
        return list(self._values(self.encoder.encode(observation), create=not self.frozen))

    def action_visit_counts(self, observation: AgentObservation) -> list[int]:
        state = self.encoder.encode(observation)
        return list(self.visit_counts.get(state, [0] * len(self.config.action_multipliers)))

    def state_visit_count(self, observation: AgentObservation) -> int:
        return sum(self.action_visit_counts(observation))

    def _filled_for_index(self, observation: AgentObservation, action_index: int) -> int:
        pace = observation.remaining_shares / max(1, observation.market.steps_remaining)
        requested = pace * self.config.action_multipliers[action_index]
        cap = min(observation.remaining_shares, observation.market.max_trade_per_step)
        required = max(0, int(observation.minimum_required_shares))
        if required > cap:
            raise ValueError("minimum required trade exceeds remaining-order or per-step cap")
        return min(max(math.floor(requested), required), cap)

    def valid_action_indices(self, observation: AgentObservation) -> list[int]:
        required = max(0, int(observation.minimum_required_shares))
        candidates: list[int] = []
        seen_fills: set[int] = set()
        for index in range(len(self.config.action_multipliers)):
            filled = self._filled_for_index(observation, index)
            if filled in seen_fills:
                continue
            if filled >= required:
                candidates.append(index)
                seen_fills.add(filled)
        if not candidates:
            maximum = max(range(len(self.config.action_multipliers)), key=lambda i: self._filled_for_index(observation, i))
            return [maximum]
        return candidates

    def select_action_index(self, observation: AgentObservation, explore: bool = True) -> int:
        valid = self.valid_action_indices(observation)
        values = self.q_values(observation)
        if explore and self.rng.random() < self.epsilon:
            return self.rng.choice(valid)
        best = max(values[index] for index in valid)
        return next(index for index in valid if values[index] == best)

    def action_shares(self, observation: AgentObservation, action_index: int) -> float:
        self._validate_action_index(action_index)
        if action_index not in self.valid_action_indices(observation):
            raise ValueError("action is masked because it aliases another quantity or violates completion feasibility")
        pace = observation.remaining_shares / max(1, observation.market.steps_remaining)
        return pace * self.config.action_multipliers[action_index]

    def act(self, observation: AgentObservation, explore: bool = True) -> float:
        return self.action_shares(observation, self.select_action_index(observation, explore=explore))

    def update(
        self,
        observation: AgentObservation,
        action_index: int,
        reward: float,
        next_observation: AgentObservation | None,
        done: bool,
    ) -> dict[str, object]:
        if self.frozen:
            raise RuntimeError("cannot update a frozen agent")
        self._validate_action_index(action_index)
        _finite("reward", reward)
        state = self.encoder.encode(observation)
        if action_index not in self.valid_action_indices(observation):
            raise ValueError("cannot update an aliased or infeasible action")
        values = self._values(state)
        counts = self.visit_counts.setdefault(state, [0] * len(self.config.action_multipliers))
        counts[action_index] += 1
        old_value = values[action_index]
        next_state = None if next_observation is None else self.encoder.encode(next_observation)
        if done:
            next_max = 0.0
        else:
            if next_observation is None:
                raise ValueError("nonterminal update requires next_observation")
            next_values = self._values(next_state)
            next_valid = self.valid_action_indices(next_observation)
            next_max = max(next_values[index] for index in next_valid)
        target = float(reward) + self.config.gamma * next_max
        _finite("target", target)
        new_value = old_value + self.config.alpha * (target - old_value)
        _finite("new_q", new_value)
        values[action_index] = new_value
        return {
            "state": list(state), "action_index": action_index,
            "action_multiplier": self.config.action_multipliers[action_index],
            "reward": float(reward), "next_state": None if next_state is None else list(next_state),
            "next_max_q": next_max, "old_q": old_value, "target": target,
            "new_q": new_value, "done": bool(done),
        }

    def _validate_action_index(self, action_index: int) -> None:
        if isinstance(action_index, bool) or not isinstance(action_index, int):
            raise TypeError("action_index must be an integer")
        if not 0 <= action_index < len(self.config.action_multipliers):
            raise IndexError(action_index)

    def end_episode(self) -> None:
        if self.frozen:
            raise RuntimeError("cannot advance a frozen agent")
        self.episodes_seen += 1
        self.epsilon = max(self.config.epsilon_min, self.epsilon * self.config.epsilon_decay)

    def learn(self, transition: Transition) -> None:
        raise NotImplementedError("use update(...) with the environment transition")

    def freeze(self) -> None:
        self.frozen = True
        self.epsilon = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "tabular_q_learning_round5_v1", "name": self.name,
            "config": {
                "alpha": self.config.alpha, "gamma": self.config.gamma,
                "epsilon_start": self.config.epsilon_start, "epsilon_min": self.config.epsilon_min,
                "epsilon_decay": self.config.epsilon_decay,
                "action_multipliers": list(self.config.action_multipliers),
                "spread_bins_bps": list(self.config.spread_bins_bps),
                "mid_deviation_bins_bps": list(self.config.mid_deviation_bins_bps),
                "liquidity_ratio_bins": list(self.config.liquidity_ratio_bins),
                "remaining_ratio_bins": list(self.config.remaining_ratio_bins),
            },
            "epsilon": self.epsilon, "episodes_seen": self.episodes_seen, "frozen": self.frozen,
            "q_table": {"|".join(map(str, key)): values for key, values in sorted(self.q_table.items())},
            "visit_counts": {"|".join(map(str, key)): values for key, values in sorted(self.visit_counts.items())},
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TabularQLearningAgent":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") != "tabular_q_learning_round5_v1":
            raise ValueError("unsupported Q-table format")
        raw = payload["config"]
        config = QLearningConfig(
            alpha=float(raw["alpha"]), gamma=float(raw["gamma"]),
            epsilon_start=float(raw["epsilon_start"]), epsilon_min=float(raw["epsilon_min"]),
            epsilon_decay=float(raw["epsilon_decay"]),
            action_multipliers=tuple(float(value) for value in raw["action_multipliers"]),
            spread_bins_bps=tuple(float(value) for value in raw["spread_bins_bps"]),
            mid_deviation_bins_bps=tuple(float(value) for value in raw["mid_deviation_bins_bps"]),
            liquidity_ratio_bins=tuple(float(value) for value in raw["liquidity_ratio_bins"]),
            remaining_ratio_bins=tuple(float(value) for value in raw.get("remaining_ratio_bins", ())),
        )
        agent = cls(config=config, seed=0)
        agent.epsilon = float(payload["epsilon"])
        _finite("saved epsilon", agent.epsilon)
        agent.episodes_seen = int(payload["episodes_seen"])
        agent.q_table = {}
        for key, values in payload["q_table"].items():
            state = tuple(int(value) for value in key.split("|"))
            if len(state) != 6 or len(values) != len(config.action_multipliers):
                raise ValueError("invalid saved Q-table shape")
            converted = [float(item) for item in values]
            if any(not math.isfinite(item) for item in converted):
                raise ValueError("saved Q-table contains non-finite value")
            agent.q_table[state] = converted
        agent.visit_counts = {}
        for key, counts in payload.get("visit_counts", {}).items():
            state = tuple(int(value) for value in key.split("|"))
            if len(state) != 6 or len(counts) != len(config.action_multipliers):
                raise ValueError("invalid saved visit-count shape")
            converted_counts = [int(item) for item in counts]
            if any(item < 0 for item in converted_counts):
                raise ValueError("saved visit counts must be nonnegative")
            agent.visit_counts[state] = converted_counts
        if bool(payload.get("frozen", False)):
            agent.freeze()
        return agent
