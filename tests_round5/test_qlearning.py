from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src_round5"))

from execution_sim.models import AgentObservation, MarketSnapshot  # noqa: E402
from execution_sim.qlearning import QLearningConfig, StateEncoder, TabularQLearningAgent  # noqa: E402
from execution_sim.environment import MarketEnvironment  # noqa: E402
from execution_sim.strategies import TWAPStrategy  # noqa: E402


def observation(steps: int = 2, remaining: int = 50_000, spread: float = 6.0) -> AgentObservation:
    return AgentObservation(
        "A",
        MarketSnapshot(30 - steps, 100.0, spread, 20_000, steps, 30),
        100_000,
        remaining,
    )


class QLearningTests(unittest.TestCase):
    def test_bellman_update_hand_calculation(self) -> None:
        config = QLearningConfig(alpha=0.25, gamma=1.0)
        agent = TabularQLearningAgent(config, seed=1)
        current = observation(steps=30, remaining=100_000)
        next_obs = observation(steps=1, remaining=10_000)
        next_state = agent.encoder.encode(next_obs)
        agent._values(next_state)[0] = 8.0
        update = agent.update(current, action_index=1, reward=-4.0, next_observation=next_obs, done=False)
        self.assertEqual(update["old_q"], 0.0)
        self.assertEqual(update["next_max_q"], 8.0)
        self.assertEqual(update["target"], 4.0)
        self.assertEqual(update["new_q"], 1.0)

    def test_action_is_legal_and_uses_only_own_observation(self) -> None:
        agent = TabularQLearningAgent(seed=4)
        obs = observation(steps=4, remaining=4_000)
        action_index = agent.select_action_index(obs, explore=False)
        shares = agent.action_shares(obs, action_index)
        self.assertIn(agent.config.action_multipliers[action_index], (0.0, 0.5, 1.0, 1.5, 2.0))
        self.assertGreaterEqual(shares, 0.0)
        self.assertLessEqual(shares, obs.remaining_shares)
        self.assertFalse(hasattr(obs, "opponent_remaining_shares"))

    def test_state_encoder_changes_when_observable_state_changes(self) -> None:
        encoder = StateEncoder(QLearningConfig())
        self.assertNotEqual(encoder.encode(observation(steps=2)), encoder.encode(observation(steps=1)))
        self.assertNotEqual(encoder.encode(observation(remaining=50_000)), encoder.encode(observation(remaining=10_000)))
        self.assertNotEqual(encoder.encode(observation(spread=2.0)), encoder.encode(observation(spread=12.0)))

    def test_save_load_reproduces_frozen_action(self) -> None:
        agent = TabularQLearningAgent(seed=3)
        obs = observation(steps=30, remaining=100_000)
        state = agent.encoder.encode(obs)
        agent._values(state)[:] = [-2.0, -1.0, 0.5, 0.1, -5.0]
        agent.freeze()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "q.json"
            agent.save(path)
            restored = TabularQLearningAgent.load(path)
            self.assertEqual(agent.select_action_index(obs, explore=False), restored.select_action_index(obs, explore=False))
            self.assertEqual(agent.action_shares(obs, 2), restored.action_shares(obs, 2))
            self.assertEqual(restored.epsilon, 0.0)

    def test_gamma_one_is_default_for_finite_horizon(self) -> None:
        self.assertEqual(QLearningConfig().gamma, 1.0)

    def test_ratio_aggregation_merges_states_but_keeps_real_order_for_actions(self) -> None:
        config = QLearningConfig(remaining_ratio_bins=(0.0, 0.25, 0.5, 0.75, 1.0))
        encoder = StateEncoder(config)
        first = observation(steps=10, remaining=45_000)
        second = observation(steps=10, remaining=49_000)
        self.assertNotEqual(StateEncoder(QLearningConfig()).encode(first), StateEncoder(QLearningConfig()).encode(second))
        self.assertEqual(encoder.encode(first), encoder.encode(second))

        first_agent = TabularQLearningAgent(config, seed=1)
        action_index = 2
        self.assertIn(action_index, first_agent.valid_action_indices(first))
        self.assertIn(action_index, first_agent.valid_action_indices(second))
        self.assertEqual(first_agent.encoder.encode(first), first_agent.encoder.encode(second))
        self.assertEqual(first_agent.action_shares(first, action_index), 4_500.0)
        self.assertEqual(first_agent.action_shares(second, action_index), 4_900.0)
        self.assertLessEqual(first_agent.action_shares(first, action_index), first.remaining_shares)

    def test_ratio_aggregation_config_roundtrips_and_legacy_config_loads(self) -> None:
        config = QLearningConfig(remaining_ratio_bins=(0.0, 0.5, 1.0))
        agent = TabularQLearningAgent(config, seed=2)
        agent.freeze()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aggregated.json"
            agent.save(path)
            loaded = TabularQLearningAgent.load(path)
            self.assertEqual(loaded.config.remaining_ratio_bins, (0.0, 0.5, 1.0))

            payload = agent.to_dict()
            payload["config"].pop("remaining_ratio_bins")
            path.write_text(__import__("json").dumps(payload), encoding="utf-8")
            legacy = TabularQLearningAgent.load(path)
            self.assertEqual(legacy.config.remaining_ratio_bins, ())

    def test_deterministic_training_keeps_action_feasible(self) -> None:
        # No random price shock. A permanent impact makes waiting more expensive;
        # a positive terminal penalty makes leaving inventory unfinished costly.
        config = __import__("execution_sim.models", fromlist=["SimulationConfig"]).SimulationConfig(
            horizon_steps=2,
            initial_order_shares=100,
            max_trade_per_step=100,
            full_spread_bps=0,
            liquidity_shares=100,
            volatility_bps=0,
            temporary_impact_bps_per_liquidity_unit=0,
            permanent_impact_bps_per_liquidity_unit=1.0,
            fee_bps=0,
            terminal_penalty_per_share=1.0,
        )
        agent = TabularQLearningAgent(
            QLearningConfig(alpha=0.5, epsilon_start=0.5, epsilon_min=0.01, epsilon_decay=0.99),
            seed=1,
        )
        twap = TWAPStrategy()
        for episode_seed in range(1_000):
            env = MarketEnvironment(config, seed=episode_seed)
            while not env.done:
                obs_a = env.observe("A")
                obs_b = env.observe("B")
                action_index = agent.select_action_index(obs_a, explore=True)
                result = env.step({"A": agent.action_shares(obs_a, action_index), "B": twap.act(obs_b)})
                next_obs = None if env.done else env.observe("A")
                agent.update(obs_a, action_index, result.agents["A"].reward, next_obs, env.done)
            agent.end_episode()
        agent.freeze()
        probe = MarketEnvironment(config, seed=0)
        obs = probe.observe("A")
        index = agent.select_action_index(obs, explore=False)
        self.assertIn(index, agent.valid_action_indices(obs))
        self.assertLessEqual(agent.action_shares(obs, index), config.max_trade_per_step)


if __name__ == "__main__":
    unittest.main()
