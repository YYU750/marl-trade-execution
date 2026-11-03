from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.environment import MarketEnvironment
from execution_sim.models import AgentObservation, MarketSnapshot, SimulationConfig
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent


def observation(steps: int, remaining: int, minimum: int = 0, cap: int = 60) -> AgentObservation:
    return AgentObservation(
        "A",
        MarketSnapshot(2 - steps, 100.0, 6.0, 100, steps, 2, cap),
        100,
        remaining,
        100.0,
        minimum,
    )


class BehaviorDiagnosticTests(unittest.TestCase):
    def test_zero_pace_request_is_distinguished_from_forced_fill(self) -> None:
        config = SimulationConfig(
            horizon_steps=2,
            initial_order_shares=100,
            max_trade_per_step=60,
            liquidity_shares=100,
            volatility_bps=0.0,
            temporary_impact_bps_per_liquidity_unit=0.0,
            permanent_impact_bps_per_liquidity_unit=0.0,
            fee_bps=0.0,
            enforce_completion=True,
        )
        env = MarketEnvironment(config, seed=1)
        agent = TabularQLearningAgent(seed=1)
        obs = env.observe("A")
        index = agent.select_action_index(obs, explore=False)
        self.assertEqual(agent.config.action_multipliers[index], 0.0)
        self.assertEqual(agent.action_shares(obs, index), 0.0)
        result = env.step({"A": 0.0, "B": 0.0})
        row = result.agents["A"]
        self.assertEqual(obs.minimum_required_shares, 40)
        self.assertEqual(row.action_requested_shares, 0.0)
        self.assertEqual(row.completion_constraint_shares, 40)
        self.assertEqual(row.filled_shares, 40)

    def test_selected_request_plus_forced_fill_reproduces_actual_fill(self) -> None:
        config = SimulationConfig(
            horizon_steps=2,
            initial_order_shares=100,
            max_trade_per_step=60,
            liquidity_shares=100,
            volatility_bps=0.0,
            temporary_impact_bps_per_liquidity_unit=0.0,
            permanent_impact_bps_per_liquidity_unit=0.0,
            fee_bps=0.0,
            enforce_completion=True,
        )
        env = MarketEnvironment(config, seed=2)
        obs = env.observe("A")
        requested = 0.0
        clipped = min(int(requested), obs.remaining_shares, config.max_trade_per_step)
        result = env.step({"A": requested, "B": requested})
        row = result.agents["A"]
        self.assertEqual(row.filled_shares, clipped + row.completion_constraint_shares)

    def test_unseen_frozen_state_tie_selects_first_valid_action_without_insertion(self) -> None:
        agent = TabularQLearningAgent(seed=3)
        obs = observation(steps=2, remaining=100)
        agent.freeze()
        self.assertNotIn(agent.encoder.encode(obs), agent.q_table)
        selected = agent.select_action_index(obs, explore=False)
        self.assertEqual(selected, agent.valid_action_indices(obs)[0])
        self.assertEqual(agent.config.action_multipliers[selected], 0.0)
        self.assertNotIn(agent.encoder.encode(obs), agent.q_table)
        self.assertEqual(agent.q_values(obs), [0.0] * len(agent.config.action_multipliers))

    def test_visit_counts_increment_and_survive_model_reload(self) -> None:
        agent = TabularQLearningAgent(QLearningConfig(alpha=1.0), seed=4)
        obs = observation(steps=2, remaining=100)
        state = agent.encoder.encode(obs)
        action = agent.valid_action_indices(obs)[1]
        agent.update(obs, action, reward=-1.0, next_observation=observation(1, 60, 60), done=False)
        self.assertEqual(agent.visit_counts[state][action], 1)
        agent.freeze()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            agent.save(path)
            restored = TabularQLearningAgent.load(path)
            self.assertEqual(restored.visit_counts, agent.visit_counts)
            self.assertEqual(restored.to_dict(), agent.to_dict())


if __name__ == "__main__":
    unittest.main()
