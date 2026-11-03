"""Compact schedule-aware Q-learning agent shared by training and evaluation."""
from __future__ import annotations

import random

from run_standard_benchmark import (
    ACTIONS,
    Config,
    Observation,
    QLearningAgent,
    feasible_action_floor,
)


class ScheduleAwareQLearningAgent(QLearningAgent):
    """Q-learning with fewer, schedule-relevant state bins.

    The reduced representation shares samples across nearby time steps and
    describes inventory as execution pace relative to the remaining window.
    The opponent's previous child order remains part of the state.
    """

    state_encoding = "schedule_aware_v1"

    def state_key(self, obs: Observation) -> tuple[int, ...]:
        time_phase = min(5, obs.t // 10)
        steps_left = max(obs.horizon - obs.t, 1)
        pace_ratio = obs.remaining / max(obs.base_slice * steps_left, 1.0)
        if pace_ratio < 0.75:
            pace_bin = 0
        elif pace_ratio < 0.90:
            pace_bin = 1
        elif pace_ratio < 1.05:
            pace_bin = 2
        elif pace_ratio < 1.20:
            pace_bin = 3
        else:
            pace_bin = 4

        deviation_bps = (obs.mid / obs.initial_mid - 1.0) * 10_000.0
        price_bin = sum(deviation_bps >= cut for cut in (-6.0, -3.0, -1.0, 1.0, 3.0, 6.0))
        state: tuple[int, ...] = (time_phase, pace_bin, price_bin)
        if self.opponent_aware:
            opponent_ratio = obs.opponent_previous_qty / max(obs.base_slice, 1.0)
            opponent_bin = 0 if opponent_ratio < 0.25 else 1 if opponent_ratio < 1.25 else 2
            state += (opponent_bin,)
        return state

    def values(self, obs: Observation) -> list[float]:
        state = self.state_key(obs)
        self.visited.add(state)
        return self.q.setdefault(state, [0.0] * len(ACTIONS))

    def select(self, obs: Observation, rng: random.Random, epsilon: float = 0.0,
               allowed_min_index: int = 0) -> int:
        values = self.values(obs)
        state = self.state_key(obs)
        allowed = list(range(allowed_min_index, len(ACTIONS)))
        if epsilon > 0 and rng.random() < epsilon:
            return rng.choice(allowed)
        visits = self.action_visits.get(state, [0] * len(ACTIONS))
        tried = [i for i, count in enumerate(visits) if count > 0 and i in allowed]
        if not tried:
            return 2 if 2 in allowed else allowed[0]
        best = max(values[i] for i in tried)
        return rng.choice([i for i in tried if abs(values[i] - best) < 1e-12])

    def update(self, obs: Observation, action: int, reward: float,
               next_obs: Observation | None) -> None:
        state = self.state_key(obs)
        self.visited.add(state)
        current = self.q.setdefault(state, [0.0] * len(ACTIONS))
        visits = self.action_visits.setdefault(state, [0] * len(ACTIONS))
        visits[action] += 1
        if next_obs is None:
            future = 0.0
        else:
            next_values = self.values(next_obs)
            _, floor_index = feasible_action_floor(next_obs, self.config)
            next_state = self.state_key(next_obs)
            next_visits = self.action_visits.get(next_state, [0] * len(ACTIONS))
            tried = [i for i in range(floor_index, len(ACTIONS)) if next_visits[i] > 0]
            # All rewards are non-positive costs. An untried zero-initialized
            # action must not dominate actions with observed negative returns.
            future = max(next_values[i] for i in tried) if tried else 0.0
        target = reward + self.config.discount * future
        current[action] += self.config.learning_rate * (target - current[action])

    def initial_state_max_q(self) -> float:
        initial = Observation(
            0, self.config.order_size, self.config.initial_price,
            self.config.initial_price, 0.0, self.config.base_slice,
            self.config.horizon, self.config.step_volatility_bps,
        )
        return max(self.q.get(self.state_key(initial), [0.0] * len(ACTIONS)))
