from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.dual_qexperiment import run_episode
from execution_sim.models import SimulationConfig
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent


class DualQLearningTests(unittest.TestCase):
    def small_config(self) -> SimulationConfig:
        return SimulationConfig(
            horizon_steps=3, initial_order_shares=300, max_trade_per_step=100,
            liquidity_shares=1000, enforce_completion=True,
        )

    def test_two_agents_update_independent_tables_from_synchronous_episode(self) -> None:
        config = self.small_config()
        a = TabularQLearningAgent(QLearningConfig(), seed=11)
        b = TabularQLearningAgent(QLearningConfig(), seed=29)
        self.assertIsNot(a.q_table, b.q_table)
        self.assertIsNot(a.visit_counts, b.visit_counts)
        metrics, trace = run_episode(config, 71, {"A": a, "B": b}, train=True, keep_trace=True)
        self.assertEqual(len(trace), config.horizon_steps * 2)
        for index in range(0, len(trace), 2):
            self.assertEqual(trace[index]["same_snapshot_id"], trace[index + 1]["same_snapshot_id"])
        for agent_id, agent in (("A", a), ("B", b)):
            self.assertEqual(sum(sum(v) for v in agent.visit_counts.values()), config.horizon_steps)
            self.assertEqual(metrics[agent_id]["q_updates"], config.horizon_steps)
            self.assertEqual(metrics[agent_id]["filled_shares"], config.initial_order_shares)
            self.assertEqual(metrics[agent_id]["unfilled_shares"], 0)
        self.assertTrue(all(row["q_update"] for row in trace))
        for index in range(0, len(trace), 2):
            pair = trace[index:index + 2]
            self.assertEqual(pair[0]["joint_filled_shares"], pair[0]["filled_shares"] + pair[1]["filled_shares"])

    def test_frozen_evaluation_does_not_update_either_q_table(self) -> None:
        config = self.small_config()
        a = TabularQLearningAgent(seed=5)
        b = TabularQLearningAgent(seed=9)
        a.freeze()
        b.freeze()
        before_a, before_b = a.to_dict(), b.to_dict()
        run_episode(config, 91, {"A": a, "B": b}, train=False)
        self.assertEqual(before_a, a.to_dict())
        self.assertEqual(before_b, b.to_dict())

    def test_requested_and_completion_forced_shares_are_separate(self) -> None:
        config = SimulationConfig(
            horizon_steps=2, initial_order_shares=100, max_trade_per_step=100,
            liquidity_shares=1000, enforce_completion=True,
        )
        a = TabularQLearningAgent(seed=1)
        b = TabularQLearningAgent(seed=2)
        a.freeze()
        b.freeze()
        metrics, trace = run_episode(config, 3, {"A": a, "B": b}, train=False, keep_trace=True)
        for agent_id in ("A", "B"):
            self.assertEqual(metrics[agent_id]["requested_after_clip_shares"] + metrics[agent_id]["forced_fill_shares"], config.initial_order_shares)
        self.assertTrue(any(row["forced_shares"] > 0 for row in trace))

    def test_joint_impact_costs_and_rewards_match_hand_calculation(self) -> None:
        config = SimulationConfig(
            horizon_steps=1, initial_order_shares=1000, initial_mid_price=100.0,
            full_spread_bps=6.0, liquidity_shares=1000, volatility_bps=0.0,
            temporary_impact_bps_per_liquidity_unit=2.0,
            permanent_impact_bps_per_liquidity_unit=0.6,
            max_trade_per_step=1000, fee_bps=0.0,
            terminal_penalty_per_share=0.0, enforce_completion=False,
        )
        metrics, trace = run_episode(config, 15, {
            "A": lambda obs: 100.0,
            "B": lambda obs: 200.0,
        }, keep_trace=True)
        fill_price = 100.0 * (1.0 + (3.0 + 0.6) / 10_000.0)
        expected_next_mid = 100.0 * __import__("math").exp(0.18 / 10_000.0)
        self.assertAlmostEqual(metrics["A"]["realized_fill_shortfall"], 100.0 * (fill_price - 100.0), places=9)
        self.assertAlmostEqual(metrics["B"]["realized_fill_shortfall"], 200.0 * (fill_price - 100.0), places=9)
        self.assertAlmostEqual(trace[0]["mid_after"], expected_next_mid, places=12)
        self.assertAlmostEqual(trace[0]["reward"], -metrics["A"]["total_objective"], places=9)
        self.assertAlmostEqual(trace[1]["reward"], -metrics["B"]["total_objective"], places=9)

    def test_frozen_evaluation_repeats_for_fixed_seed(self) -> None:
        config = self.small_config()
        a, b = TabularQLearningAgent(seed=1), TabularQLearningAgent(seed=2)
        a.freeze()
        b.freeze()
        first, first_trace = run_episode(config, 501, {"A": a, "B": b}, keep_trace=True)
        second, second_trace = run_episode(config, 501, {"A": a, "B": b}, keep_trace=True)
        self.assertEqual(first, second)
        self.assertEqual(
            [(row["requested_shares"], row["filled_shares"], row["reward"]) for row in first_trace],
            [(row["requested_shares"], row["filled_shares"], row["reward"]) for row in second_trace],
        )

    def test_two_independent_frozen_tables_roundtrip_and_reproduce_episode(self) -> None:
        config = self.small_config()
        agents = {"A": TabularQLearningAgent(seed=31), "B": TabularQLearningAgent(seed=47)}
        run_episode(config, 601, agents, train=True)
        for agent in agents.values():
            agent.freeze()
        with tempfile.TemporaryDirectory() as directory:
            paths = {key: Path(directory) / f"{key}.json" for key in agents}
            for key, agent in agents.items():
                agent.save(paths[key])
            loaded = {key: TabularQLearningAgent.load(paths[key]) for key in agents}
            self.assertEqual(agents["A"].to_dict(), loaded["A"].to_dict())
            self.assertEqual(agents["B"].to_dict(), loaded["B"].to_dict())
            direct, _ = run_episode(config, 607, agents, train=False)
            restored, _ = run_episode(config, 607, loaded, train=False)
            self.assertEqual(direct, restored)


if __name__ == "__main__":
    unittest.main()
