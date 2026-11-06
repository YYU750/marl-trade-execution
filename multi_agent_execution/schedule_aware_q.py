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
        if self.frozen:
            return self.q.get(state, [0.0] * len(ACTIONS))
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

    def minimum_next_action_index(self, obs: Observation) -> int:
        """Legacy full-fill benchmark feasibility rule."""
        return feasible_action_floor(obs, self.config)[1]

    def update(self, obs: Observation, action: int, reward: float,
               next_obs: Observation | None) -> dict[str, float | str | None]:
        if self.frozen:
            raise RuntimeError("Cannot update a frozen Q-learning policy")
        state = self.state_key(obs)
        self.visited.add(state)
        current = self.q.setdefault(state, [0.0] * len(ACTIONS))
        q_before = current[action]
        visits = self.action_visits.setdefault(state, [0] * len(ACTIONS))
        visits[action] += 1
        if next_obs is None:
            future = 0.0
        else:
            next_values = self.values(next_obs)
            floor_index = self.minimum_next_action_index(next_obs)
            next_state = self.state_key(next_obs)
            next_visits = self.action_visits.get(next_state, [0] * len(ACTIONS))
            tried = [i for i in range(floor_index, len(ACTIONS)) if next_visits[i] > 0]
            # All rewards are non-positive costs. An untried zero-initialized
            # action must not dominate actions with observed negative returns.
            future = max(next_values[i] for i in tried) if tried else 0.0
        target = reward + self.config.discount * future
        current[action] += self.config.learning_rate * (target - current[action])
        return {
            "state_key": "|".join(map(str, state)),
            "next_state_key": ("|".join(map(str, self.state_key(next_obs)))
                               if next_obs is not None else None),
            "q_before": q_before,
            "future_value": future,
            "td_target": target,
            "q_after": current[action],
        }

    def initial_state_max_q(self) -> float:
        initial = Observation(
            0, self.config.order_size, self.config.initial_price,
            self.config.initial_price, 0.0, self.config.base_slice,
            self.config.horizon, self.config.step_volatility_bps,
        )
        return max(self.q.get(self.state_key(initial), [0.0] * len(ACTIONS)))


class ThresholdAlignedDoubleQAgent(ScheduleAwareQLearningAgent):
    """Rule-informed Double Q learner with state bins aligned to rule thresholds.

    The dynamic rule supplies an initial action prior for untrained states.
    Q-learning remains free to replace that action once exploration provides
    enough evidence. A separate pair of Q tables reduces maximization bias.
    """

    state_encoding = "threshold_aligned_double_q_v1"

    def __init__(self, config: Config, opponent_aware: bool = True, seed: int = 0):
        super().__init__(config, opponent_aware)
        self.qa: dict[tuple[int, ...], list[float]] = {}
        self.qb: dict[tuple[int, ...], list[float]] = {}
        self.prior_actions: dict[tuple[int, ...], int] = {}
        self.update_rng = random.Random(seed)
        self.improvement_margin = 0.0
        self.minimum_improvement_visits = 25

    def state_key(self, obs: Observation) -> tuple[int, ...]:
        pace_ratio = obs.remaining / max(
            obs.base_slice * max(obs.horizon - obs.t, 1), 1.0
        )
        pace_bin = sum(pace_ratio >= cut for cut in (0.75, 0.90, 0.98, 1.05, 1.20, 1.25))
        deviation_bps = (obs.mid / obs.initial_mid - 1.0) * 10_000.0
        price_bin = sum(deviation_bps >= cut for cut in (-6.0, -3.0, -1.0, 1.0, 2.0, 3.0, 6.0))
        volatility_bin = int(obs.volatility_bps > self.config.step_volatility_bps * 1.5)
        time_phase = min(11, obs.t // 5)
        terminal_step = int(obs.t == obs.horizon - 1)
        state: tuple[int, ...] = (time_phase, terminal_step, pace_bin,
                                  price_bin, volatility_bin)
        if self.opponent_aware:
            opponent_ratio = obs.opponent_previous_qty / max(obs.base_slice, 1.0)
            opponent_bin = sum(opponent_ratio >= cut for cut in (0.25, 0.75, 1.25, 2.0))
            state += (opponent_bin,)
        return state

    def _rule_prior(self, obs: Observation) -> int:
        deficit = obs.remaining / max(obs.base_slice * (obs.horizon - obs.t), 1.0)
        price_deviation = (obs.mid / obs.initial_mid - 1.0) * 10_000.0
        if obs.t == obs.horizon - 1 or deficit > 1.25:
            return 4
        if price_deviation < -1.0:
            return 3
        if price_deviation > 2.0 and deficit < 1.05:
            return 1
        if (self.config.temporary_impact_bps_per_slice * self.config.market_impact_multiplier
                * self.config.step_minutes) > 0.15 and deficit < 0.98:
            return 1
        return 2

    def values(self, obs: Observation) -> list[float]:
        state = self.state_key(obs)
        if self.frozen:
            zeros = [0.0] * len(ACTIONS)
            qa = self.qa.get(state, zeros)
            qb = self.qb.get(state, zeros)
            return [(a + b) / 2.0 for a, b in zip(qa, qb)]
        self.visited.add(state)
        qa = self.qa.setdefault(state, [0.0] * len(ACTIONS))
        qb = self.qb.setdefault(state, [0.0] * len(ACTIONS))
        prior = self._rule_prior(obs)
        _, min_index = feasible_action_floor(obs, self.config)
        self.prior_actions[state] = max(prior, min_index)
        merged = [(a + b) / 2.0 for a, b in zip(qa, qb)]
        self.q[state] = merged
        return merged

    def warm_start(self, obs: Observation, action: int, return_to_go: float,
                   sample_count: int = 1) -> None:
        """Initialize expert-action values from training-only demonstrations."""
        if self.frozen:
            raise RuntimeError("Cannot warm-start a frozen Double Q policy")
        state = self.state_key(obs)
        self.visited.add(state)
        _, min_index = feasible_action_floor(obs, self.config)
        prior = max(self._rule_prior(obs), min_index)
        self.prior_actions[state] = prior
        qa = self.qa.setdefault(state, [0.0] * len(ACTIONS))
        qb = self.qb.setdefault(state, [0.0] * len(ACTIONS))
        counts = self.action_visits.setdefault(state, [0] * len(ACTIONS))
        if action != prior:
            return
        old_count = counts[action]
        new_count = old_count + sample_count
        qa[action] += (return_to_go - qa[action]) * sample_count / new_count
        qb[action] += (return_to_go - qb[action]) * sample_count / new_count
        counts[action] = new_count
        self.q[state] = [(a + b) / 2.0 for a, b in zip(qa, qb)]

    def select(self, obs: Observation, rng: random.Random, epsilon: float = 0.0,
               allowed_min_index: int = 0) -> int:
        values = self.values(obs)
        state = self.state_key(obs)
        allowed = list(range(allowed_min_index, len(ACTIONS)))
        if epsilon > 0 and rng.random() < epsilon:
            return rng.choice(allowed)
        visits = self.action_visits.get(state, [0] * len(ACTIONS))
        candidates = [i for i in allowed if visits[i] > 0]
        prior = max(self._rule_prior(obs), allowed_min_index)
        if not self.frozen:
            self.prior_actions[state] = prior
        if prior in allowed and prior not in candidates:
            candidates.append(prior)
        best = max(values[i] for i in candidates)
        best_actions = [i for i in candidates if abs(values[i] - best) < 1e-12]
        best_action = rng.choice(best_actions)
        if best_action != prior:
            if visits[best_action] < self.minimum_improvement_visits:
                return prior
            if values[best_action] - values[prior] <= max(self.improvement_margin, 1e-12):
                return prior
        return best_action

    def update(self, obs: Observation, action: int, reward: float,
               next_obs: Observation | None) -> None:
        if self.frozen:
            raise RuntimeError("Cannot update a frozen Double Q policy")
        state = self.state_key(obs)
        current_a = self.qa.setdefault(state, [0.0] * len(ACTIONS))
        current_b = self.qb.setdefault(state, [0.0] * len(ACTIONS))
        visits = self.action_visits.setdefault(state, [0] * len(ACTIONS))
        visits[action] += 1
        choose_a = bool(self.update_rng.getrandbits(1))
        chosen, evaluator = (self.qa, self.qb) if choose_a else (self.qb, self.qa)
        if next_obs is None:
            future = 0.0
        else:
            self.values(next_obs)
            next_state = self.state_key(next_obs)
            _, min_index = feasible_action_floor(next_obs, self.config)
            next_visits = self.action_visits.get(next_state, [0] * len(ACTIONS))
            candidates = [i for i in range(min_index, len(ACTIONS)) if next_visits[i] > 0]
            prior = max(self._rule_prior(next_obs), min_index)
            self.prior_actions[next_state] = prior
            if prior >= min_index and prior not in candidates:
                candidates.append(prior)
            best = max(chosen[next_state][i] for i in candidates)
            best_actions = [i for i in candidates if abs(chosen[next_state][i] - best) < 1e-12]
            best_action = self.update_rng.choice(best_actions)
            future = evaluator[next_state][best_action]
        target = self.td_target(reward, future, terminal=next_obs is None)
        chosen.setdefault(state, [0.0] * len(ACTIONS))[action] += (
            self.config.learning_rate * (target - chosen[state][action])
        )
        self.q[state] = [(a + b) / 2.0 for a, b in zip(current_a, current_b)]

    def td_target(self, reward: float, future_value: float = 0.0,
                  terminal: bool = False) -> float:
        """Double-Q Bellman target: r + gamma * V(s'), with no terminal bootstrap."""
        return reward if terminal else reward + self.config.discount * future_value

    def initial_state_max_q(self) -> float:
        initial = Observation(
            0, self.config.order_size, self.config.initial_price,
            self.config.initial_price, 0.0, self.config.base_slice,
            self.config.horizon, self.config.step_volatility_bps,
        )
        return max(self.values(initial))


class LimitOrderAwareQLearningAgent(ScheduleAwareQLearningAgent):
    """Bilateral self-play Q learner that observes its live child-order queue.

    This class is used by the event-driven limit-order self-play model only.
    The historical full-fill benchmark keeps its original state encoding.
    """

    state_encoding = "schedule_aware_limit_order_v2"

    def state_key(self, obs: Observation) -> tuple[int, ...]:
        time_phase = min(5, obs.t // 10)
        steps_left = max(obs.horizon - obs.t, 1)
        pace_ratio = obs.remaining / max(obs.base_slice * steps_left, 1.0)
        pace_bin = sum(pace_ratio >= cut for cut in (0.95, 1.10, 1.40))

        deviation_bps = (obs.mid / obs.initial_mid - 1.0) * 10_000.0
        price_bin = sum(deviation_bps >= cut for cut in (-2.0, 2.0))
        opponent_ratio = obs.opponent_previous_qty / max(obs.base_slice, 1.0)
        opponent_bin = int(opponent_ratio >= 1.0)

        if obs.open_order_qty <= 1e-9 or obs.limit_price <= 0:
            order_price_bin = 0
            order_size_bin = 0
            queue_bin = 0
            age_bin = 0
        else:
            offset_bps = (obs.limit_price / obs.mid - 1.0) * 10_000.0
            # 1=deep passive, 2=best bid, 3=inside-spread, 4=marketable.
            order_price_bin = (1 if offset_bps <= -2.5 else
                               2 if offset_bps <= -1.5 else
                               3 if offset_bps < 0.0 else 4)
            order_size_bin = int(obs.open_order_qty > obs.base_slice)
            queue_ratio = obs.queue_ahead / max(obs.base_slice, 1.0)
            queue_bin = int(queue_ratio >= 1.0)
            age_bin = int(obs.order_age_steps >= 2)

        return (time_phase, pace_bin, price_bin, opponent_bin,
                order_price_bin, order_size_bin, queue_bin, age_bin,
                int(obs.t == obs.horizon - 1))

    def minimum_next_action_index(self, obs: Observation) -> int:
        # Submitting more shares does not ensure they execute. No action is
        # therefore declared feasible solely from the parent-order schedule.
        return 0

    def initial_state_max_q(self) -> float:
        initial = Observation(
            0, self.config.order_size, self.config.initial_price,
            self.config.initial_price, 0.0, self.config.base_slice,
            self.config.horizon, self.config.step_volatility_bps,
        )
        return max(self.q.get(self.state_key(initial), [0.0] * len(ACTIONS)))
