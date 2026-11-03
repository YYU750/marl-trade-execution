from __future__ import annotations

from execution_sim.environment import MarketEnvironment
from execution_sim.models import SimulationConfig
from execution_sim.strategies import Strategy, make_strategy


def run_episode(config: SimulationConfig, strategy_a: Strategy, strategy_b: Strategy, seed: int):
    env = MarketEnvironment(config, seed)
    strategies = {"A": strategy_a, "B": strategy_b}
    step_log: list[dict[str, float | int | str]] = []
    while not env.done:
        shared_snapshot = env.observe_market()
        observations = {agent_id: env.observe(agent_id) for agent_id in env.AGENTS}
        actions = {agent_id: strategies[agent_id].act(observations[agent_id]) for agent_id in env.AGENTS}
        result = env.step(actions, shared_snapshot)
        for agent_id in env.AGENTS:
            agent_result = result.agents[agent_id]
            step_log.append({
                "seed": seed, "step": shared_snapshot.step, "agent_id": agent_id,
                "strategy": strategies[agent_id].name,
                "opponent_strategy": strategies["B" if agent_id == "A" else "A"].name,
                "mid_price_before": shared_snapshot.mid_price, "mid_price_after": result.mid_price_after,
                "full_spread_bps": shared_snapshot.full_spread_bps, "liquidity_shares": shared_snapshot.liquidity_shares,
                "action_requested_shares": agent_result.action_requested_shares,
                "completion_constraint_shares": agent_result.completion_constraint_shares,
                "filled_shares": agent_result.filled_shares, "remaining_shares": agent_result.remaining_shares,
                "joint_filled_shares": result.joint_filled_shares, "exogenous_shock_bps": result.exogenous_shock_bps,
                "temporary_impact_bps": result.temporary_impact_bps, "permanent_impact_bps": result.permanent_impact_bps,
                "fill_price": agent_result.fill_price,
                "realized_fill_shortfall": agent_result.realized_fill_shortfall,
                "spread_cost_component_explanatory": agent_result.spread_cost_component,
                "temporary_impact_component_explanatory": agent_result.temporary_impact_cost_component,
                "unfilled_opportunity_cost": agent_result.unfilled_opportunity_cost,
                "fee": agent_result.fee, "terminal_penalty": agent_result.terminal_penalty,
                "total_objective": agent_result.total_objective, "reward": agent_result.reward,
            })
    return step_log, {agent_id: env.final_metrics(agent_id) for agent_id in env.AGENTS}


def run_named_episode(config: SimulationConfig, strategy_a_name: str, strategy_b_name: str, seed: int):
    return run_episode(config, make_strategy(strategy_a_name), make_strategy(strategy_b_name), seed)
