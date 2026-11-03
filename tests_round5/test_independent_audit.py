from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.environment import MarketEnvironment
from execution_sim.models import AgentObservation, MarketSnapshot, SimulationConfig
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent


def observation(
    *,
    mid: float = 100.0,
    remaining: int = 100_000,
    steps: int = 30,
    minimum: int = 0,
    cap: int = 10_000,
    spread: float = 6.0,
    liquidity: int = 20_000,
) -> AgentObservation:
    return AgentObservation(
        agent_id="A",
        market=MarketSnapshot(
            step=30 - steps,
            mid_price=mid,
            full_spread_bps=spread,
            liquidity_shares=liquidity,
            steps_remaining=steps,
            horizon_steps=30,
            max_trade_per_step=cap,
        ),
        initial_order_shares=100_000,
        remaining_shares=remaining,
        initial_mid_price=100.0,
        minimum_required_shares=minimum,
    )


class Round5IndependentTests(unittest.TestCase):
    def test_bellman_and_terminal_targets(self) -> None:
        config = QLearningConfig(alpha=0.5, gamma=0.9, action_multipliers=(0.0, 1.0))
        agent = TabularQLearningAgent(config, seed=7)
        current = observation(remaining=2, steps=2, cap=2)
        nxt = observation(remaining=1, steps=1, cap=2)
        next_state = agent.encoder.encode(nxt)
        agent.q_table[next_state] = [2.0, 5.0]
        result = agent.update(current, 1, reward=4.0, next_observation=nxt, done=False)
        self.assertEqual(result["target"], 8.5)
        self.assertEqual(result["new_q"], 4.25)
        terminal = agent.update(nxt, 0, reward=3.0, next_observation=None, done=True)
        self.assertEqual(terminal["target"], 3.0)
        self.assertEqual(terminal["new_q"], 2.5)

    def test_next_state_max_uses_only_valid_actions(self) -> None:
        config = QLearningConfig(alpha=1.0, gamma=1.0)
        agent = TabularQLearningAgent(config, seed=19)
        current = observation(remaining=100_000, steps=2, cap=10_000)
        # At one remaining share, multipliers 0/.5 alias at zero and 1/1.5/2 alias at one.
        nxt = observation(remaining=1, steps=1, cap=10_000)
        self.assertEqual(agent.valid_action_indices(nxt), [0, 2])
        next_state = agent.encoder.encode(nxt)
        agent.q_table[next_state] = [0.0, 1_000.0, 3.0, 4.0, 5.0]
        result = agent.update(current, 0, reward=7.0, next_observation=nxt, done=False)
        self.assertEqual(result["next_max_q"], 3.0)
        self.assertEqual(result["target"], 10.0)

    def test_known_two_step_mdp_values(self) -> None:
        """A tiny deterministic MDP has V(s0)=max(1, 5)=5 by enumeration."""
        config = QLearningConfig(alpha=1.0, gamma=1.0, epsilon_start=0.0,
                                 epsilon_min=0.0, action_multipliers=(0.0, 1.0))
        agent = TabularQLearningAgent(config, seed=8)
        s0 = observation(remaining=2, steps=2, cap=2)
        s1 = observation(remaining=1, steps=1, cap=2)
        agent.update(s1, 0, 1.0, None, True)
        agent.update(s0, 0, 0.0, s1, False)
        agent.update(s0, 1, 5.0, None, True)
        values = agent.q_values(s0)
        self.assertEqual(values, [1.0, 5.0])
        self.assertEqual(max(values), 5.0)

    def test_action_validation_and_action_aliases(self) -> None:
        agent = TabularQLearningAgent(seed=9)
        obs = observation()
        fills = [math.floor(agent.action_shares(obs, i)) for i in range(5)]
        self.assertEqual(fills, [0, 1666, 3333, 5000, 6666])
        self.assertEqual(len(set(fills)), 5)
        for bad in (-1, 5):
            with self.assertRaises(IndexError):
                agent.update(obs, bad, 0.0, None, True)
        for bad in (True, 1.0):
            with self.assertRaises(TypeError):
                agent.update(obs, bad, 0.0, None, True)

    def test_completion_constraint_is_explicit_and_feasible(self) -> None:
        config = SimulationConfig(
            horizon_steps=2, initial_order_shares=100, max_trade_per_step=60,
            initial_mid_price=100.0, full_spread_bps=0.0, volatility_bps=0.0,
            temporary_impact_bps_per_liquidity_unit=0.0,
            permanent_impact_bps_per_liquidity_unit=0.0, fee_bps=0.0,
            terminal_penalty_per_share=1.0, enforce_completion=True,
        )
        env = MarketEnvironment(config, seed=11)
        first = env.observe("A")
        self.assertEqual(first.minimum_required_shares, 40)
        result = env.step({"A": 0.0, "B": 0.0}, env.observe_market())
        self.assertEqual(result.agents["A"].filled_shares, 40)
        second = env.observe("A")
        self.assertEqual(second.minimum_required_shares, 60)
        result = env.step({"A": 0.0, "B": 0.0}, env.observe_market())
        self.assertEqual(result.agents["A"].filled_shares, 60)
        self.assertEqual(env.final_metrics("A")["unfilled_shares"], 0)
        with self.assertRaises(ValueError):
            SimulationConfig(horizon_steps=1, initial_order_shares=101, max_trade_per_step=100)

    def test_cost_identity_and_unfinished_pressure_case(self) -> None:
        config = SimulationConfig(
            horizon_steps=1, initial_order_shares=100, max_trade_per_step=30,
            initial_mid_price=100.0, full_spread_bps=0.0, volatility_bps=0.0,
            temporary_impact_bps_per_liquidity_unit=0.0,
            permanent_impact_bps_per_liquidity_unit=0.0, fee_bps=1.0,
            terminal_penalty_per_share=0.25, enforce_completion=False,
        )
        env = MarketEnvironment(config, seed=12)
        result = env.step({"A": 30.0, "B": 0.0}, env.observe_market())
        row = result.agents["A"]
        metrics = env.final_metrics("A")
        self.assertEqual(row.filled_shares, 30)
        self.assertEqual(row.unfilled_opportunity_cost, 0.0)
        self.assertEqual(row.realized_fill_shortfall, 0.0)
        self.assertAlmostEqual(row.total_objective, row.realized_fill_shortfall + row.unfilled_opportunity_cost + row.fee + row.terminal_penalty)
        self.assertAlmostEqual(metrics["total_objective"], -sum(r.reward for r in [row]))
        self.assertEqual(metrics["unfilled_shares"], 70)
        self.assertEqual(metrics["terminal_penalty"], 17.5)
        zero_fee = SimulationConfig(
            horizon_steps=1, initial_order_shares=10, max_trade_per_step=10,
            initial_mid_price=100.0, full_spread_bps=0.0, volatility_bps=0.0,
            temporary_impact_bps_per_liquidity_unit=0.0,
            permanent_impact_bps_per_liquidity_unit=0.0, fee_bps=0.0,
            terminal_penalty_per_share=0.0, enforce_completion=True,
        )
        zero_env = MarketEnvironment(zero_fee, seed=12)
        zero_result = zero_env.step({"A": 10.0, "B": 10.0}, zero_env.observe_market())
        self.assertEqual(zero_result.agents["A"].fee, 0.0)

    def test_reward_sum_equals_total_objective_over_an_episode(self) -> None:
        config = SimulationConfig(volatility_bps=1.0, enforce_completion=True)
        env = MarketEnvironment(config, seed=20)
        objective_sum = 0.0
        reward_sum = 0.0
        while not env.done:
            result = env.step({"A": 0.0, "B": 0.0}, env.observe_market())
            row = result.agents["A"]
            objective_sum += row.total_objective
            reward_sum += row.reward
        metrics = env.final_metrics("A")
        self.assertAlmostEqual(objective_sum, metrics["total_objective"], places=10)
        self.assertAlmostEqual(reward_sum, -metrics["total_objective"], places=10)

    def test_mid_price_state_and_frozen_unseen_state(self) -> None:
        agent = TabularQLearningAgent(seed=13)
        low = observation(mid=100.0)
        high = observation(mid=101.0)
        self.assertNotEqual(agent.encoder.encode(low), agent.encoder.encode(high))
        agent.q_values(low)
        agent.freeze()
        before = json.dumps(agent.to_dict(), sort_keys=True)
        values = agent.q_values(high)
        self.assertEqual(values, [0.0] * 5)
        self.assertEqual(before, json.dumps(agent.to_dict(), sort_keys=True))
        with self.assertRaises(RuntimeError):
            agent.update(low, 0, 0.0, None, True)

    def test_epsilon_and_rng_reproducibility(self) -> None:
        obs = observation(remaining=10, steps=2, cap=10)
        greedy = TabularQLearningAgent(QLearningConfig(epsilon_start=0.0, epsilon_min=0.0), seed=14)
        self.assertEqual(greedy.select_action_index(obs), 0)
        exploring = TabularQLearningAgent(QLearningConfig(epsilon_start=1.0, epsilon_min=1.0), seed=14)
        actions = {exploring.select_action_index(obs) for _ in range(100)}
        self.assertGreater(len(actions), 1)
        config = SimulationConfig(volatility_bps=2.0)
        a = MarketEnvironment(config, seed=15)
        b = MarketEnvironment(config, seed=15)
        c = MarketEnvironment(config, seed=16)
        ra = a.step({"A": 1000.0, "B": 1000.0}, a.observe_market())
        rb = b.step({"A": 1000.0, "B": 1000.0}, b.observe_market())
        rc = c.step({"A": 1000.0, "B": 1000.0}, c.observe_market())
        self.assertEqual(ra.exogenous_shock_bps, rb.exogenous_shock_bps)
        self.assertEqual(ra.mid_price_after, rb.mid_price_after)
        self.assertNotEqual(ra.exogenous_shock_bps, rc.exogenous_shock_bps)

    def test_snapshot_synchronization_and_model_roundtrip(self) -> None:
        config = SimulationConfig(volatility_bps=0.0)
        env = MarketEnvironment(config, seed=16)
        snapshot = env.observe_market()
        self.assertIs(snapshot, env.observe_market())
        env.step({"A": 1000.0, "B": 1000.0}, snapshot)
        with self.assertRaises(ValueError):
            env.step({"A": 1000.0, "B": 1000.0}, snapshot)
        agent = TabularQLearningAgent(seed=17)
        agent.q_values(observation())
        agent.freeze()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "q.json"
            agent.save(path)
            loaded = TabularQLearningAgent.load(path)
            self.assertEqual(agent.to_dict(), loaded.to_dict())

    def test_nonfinite_saved_q_rejected(self) -> None:
        agent = TabularQLearningAgent(seed=18)
        payload = agent.to_dict()
        payload["q_table"] = {"1|100000|3|6|1|10000": ["NaN"] * 5}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                TabularQLearningAgent.load(path)

    def test_nonfinite_configuration_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QLearningConfig(alpha=float("nan"))
        with self.assertRaises(ValueError):
            QLearningConfig(mid_deviation_bins_bps=(0.0, float("inf")))
        with self.assertRaises(ValueError):
            SimulationConfig(volatility_bps=float("nan"))
        with self.assertRaises(ValueError):
            SimulationConfig(initial_mid_price=float("inf"))


if __name__ == "__main__":
    unittest.main()
