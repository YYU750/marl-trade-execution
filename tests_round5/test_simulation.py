from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src_round5"))

from execution_sim.environment import MarketEnvironment  # noqa: E402
from execution_sim.models import AgentObservation, DiscreteActionSpace, MarketSnapshot, SimulationConfig  # noqa: E402
from execution_sim.runner import run_episode  # noqa: E402
from execution_sim.strategies import SpreadUrgencyStrategy, Strategy, TWAPStrategy  # noqa: E402


class NeverTrade(Strategy):
    name = "never_trade_test"

    def act(self, observation):
        del observation
        return 0.0


class SnapshotRecorder(Strategy):
    def __init__(self, name: str) -> None:
        self.name = name
        self.observations = []

    def act(self, observation):
        self.observations.append(observation)
        return 1_000.0


class SimulationTests(unittest.TestCase):
    def test_order_conservation_and_step_cap(self) -> None:
        config = SimulationConfig(horizon_steps=30, max_trade_per_step=2_000, enforce_completion=False)
        env = MarketEnvironment(config, seed=11)
        while not env.done:
            snapshot = env.observe_market()
            result = env.step({"A": 9_000, "B": 1_500}, snapshot)
            for agent_id in env.AGENTS:
                self.assertGreaterEqual(env.remaining[agent_id], 0)
                filled = env._totals[agent_id]["filled_shares"]
                self.assertEqual(filled + env.remaining[agent_id], config.initial_order_shares)
                self.assertLessEqual(result.agents[agent_id].filled_shares, config.max_trade_per_step)

    def test_zero_impact_prevents_cross_agent_price_effect(self) -> None:
        config = SimulationConfig(
            horizon_steps=1,
            initial_order_shares=20_000,
            max_trade_per_step=20_000,
            volatility_bps=0,
            temporary_impact_bps_per_liquidity_unit=0,
            permanent_impact_bps_per_liquidity_unit=0,
            enforce_completion=False,
        )
        env_a = MarketEnvironment(config, seed=7)
        env_b = MarketEnvironment(config, seed=7)
        snap_a, snap_b = env_a.observe_market(), env_b.observe_market()
        a = env_a.step({"A": 5_000, "B": 0}, snap_a)
        b = env_b.step({"A": 5_000, "B": 20_000}, snap_b)
        self.assertEqual(a.agents["A"].fill_price, b.agents["A"].fill_price)
        self.assertEqual(a.mid_price_after, b.mid_price_after)

    def test_hand_calculable_zero_cost_case(self) -> None:
        config = SimulationConfig(
            horizon_steps=1,
            initial_order_shares=100,
            initial_mid_price=100,
            full_spread_bps=0,
            liquidity_shares=100,
            volatility_bps=0,
            temporary_impact_bps_per_liquidity_unit=0,
            permanent_impact_bps_per_liquidity_unit=0,
            max_trade_per_step=100,
            fee_bps=0,
            terminal_penalty_per_share=0,
            enforce_completion=False,
        )
        env = MarketEnvironment(config, seed=1)
        snapshot = env.observe_market()
        result = env.step({"A": 50, "B": 0}, snapshot)
        metrics = env.final_metrics("A")
        self.assertEqual(result.agents["A"].fill_price, 100)
        self.assertEqual(metrics["realized_fill_shortfall"], 0)
        self.assertEqual(metrics["fees"], 0)
        self.assertEqual(metrics["unfilled_shares"], 50)
        self.assertEqual(metrics["terminal_penalty"], 0)

    def test_same_seed_repeats_exogenous_shocks(self) -> None:
        config = SimulationConfig(horizon_steps=5, enforce_completion=False)
        shocks = []
        for _ in range(2):
            env = MarketEnvironment(config, seed=99)
            current = []
            while not env.done:
                snapshot = env.observe_market()
                current.append(env.step({"A": 0, "B": 0}, snapshot).exogenous_shock_bps)
            shocks.append(current)
        self.assertEqual(shocks[0], shocks[1])

    def test_both_agents_decide_from_same_market_snapshot(self) -> None:
        a, b = SnapshotRecorder("a"), SnapshotRecorder("b")
        config = SimulationConfig(horizon_steps=2, initial_order_shares=2_000, max_trade_per_step=1_000)
        run_episode(config, a, b, seed=5)
        for obs_a, obs_b in zip(a.observations, b.observations):
            self.assertIs(obs_a.market, obs_b.market)
            self.assertEqual(obs_a.market.step, obs_b.market.step)

    def test_unfinished_order_and_penalty_are_reported(self) -> None:
        config = SimulationConfig(
            horizon_steps=3,
            initial_order_shares=1_000,
            terminal_penalty_per_share=0.25,
            max_trade_per_step=100,
            full_spread_bps=0,
            volatility_bps=0,
            temporary_impact_bps_per_liquidity_unit=0,
            permanent_impact_bps_per_liquidity_unit=0,
            fee_bps=0,
            enforce_completion=False,
        )
        _, metrics = run_episode(config, NeverTrade(), NeverTrade(), seed=2)
        result = metrics["A"]
        self.assertEqual(result["filled_shares"], 0)
        self.assertEqual(result["unfilled_shares"], 1_000)
        self.assertEqual(result["realized_fill_shortfall"], 0)
        self.assertEqual(result["terminal_penalty"], 250)
        self.assertEqual(result["total_objective"], 250)

    def test_twap_stays_within_order(self) -> None:
        config = SimulationConfig(horizon_steps=30)
        _, metrics = run_episode(config, TWAPStrategy(), TWAPStrategy(), seed=3)
        self.assertEqual(metrics["A"]["unfilled_shares"], 0)
        self.assertEqual(metrics["A"]["filled_shares"], config.initial_order_shares)

    def test_learning_hook_is_only_a_reserved_interface(self) -> None:
        with self.assertRaises(NotImplementedError):
            TWAPStrategy().learn(None)

    def test_reset_observe_step_api_and_private_observation(self) -> None:
        env = MarketEnvironment(SimulationConfig(horizon_steps=2, enforce_completion=False), seed=1)
        first = env.reset(seed=41)
        obs_a = env.observe("A")
        obs_b = env.observe("B")
        self.assertIs(first, obs_a.market)
        self.assertIs(obs_a.market, obs_b.market)
        self.assertFalse(hasattr(obs_a, "opponent_remaining_shares"))
        with self.assertRaises((AttributeError, TypeError)):
            obs_a.market.mid_price = 101
        result = env.step({"A": 10, "B": 20})
        self.assertEqual(result.snapshot, first)
        self.assertEqual(result.joint_filled_shares, 30)

    def test_stale_snapshot_is_rejected(self) -> None:
        env = MarketEnvironment(SimulationConfig(horizon_steps=2, enforce_completion=False), seed=8)
        stale = env.observe_market()
        env.step({"A": 0, "B": 0}, stale)
        with self.assertRaises(ValueError):
            env.step({"A": 0, "B": 0}, stale)

    def test_spread_urgency_changes_with_spread_and_deadline(self) -> None:
        strategy = SpreadUrgencyStrategy()

        def observation(step: int, horizon: int, remaining_steps: int, spread_bps: float):
            market = MarketSnapshot(step, 100.0, spread_bps, 20_000, remaining_steps, horizon)
            return AgentObservation("A", market, 100_000, 100_000)

        narrow = strategy.act(observation(4, 30, 26, 3.0))
        wide = strategy.act(observation(4, 30, 26, 12.0))
        urgent = strategy.act(observation(24, 30, 6, 3.0))
        self.assertGreater(narrow, wide)
        self.assertGreater(urgent, narrow)

    def test_terminal_unfilled_counterexample_has_separate_is_and_penalty(self) -> None:
        config = SimulationConfig(
            horizon_steps=30,
            initial_order_shares=100_000,
            max_trade_per_step=1_000,
            full_spread_bps=0,
            volatility_bps=0,
            temporary_impact_bps_per_liquidity_unit=0,
            permanent_impact_bps_per_liquidity_unit=0,
            fee_bps=0,
            terminal_penalty_per_share=0.25,
            enforce_completion=False,
        )
        _, metrics = run_episode(config, TWAPStrategy(), TWAPStrategy(), seed=101)
        result = metrics["A"]
        self.assertEqual(result["filled_shares"], 30_000)
        self.assertEqual(result["unfilled_shares"], 70_000)
        self.assertEqual(result["fill_ratio"], 0.3)
        self.assertEqual(result["realized_fill_shortfall"], 0)
        self.assertEqual(result["terminal_penalty"], 17_500)
        self.assertEqual(result["total_objective"], 17_500)

    def test_discrete_action_contract_is_separate_from_continuous_rule_quantity(self) -> None:
        self.assertEqual(DiscreteActionSpace().fractions, (0.0, 0.25, 0.5, 0.75, 1.0))
        with self.assertRaises(ValueError):
            DiscreteActionSpace((0.0, 1.2))


if __name__ == "__main__":
    unittest.main()
