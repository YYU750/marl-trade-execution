from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable

from execution_sim.environment import MarketEnvironment
from execution_sim.models import SimulationConfig
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent
from execution_sim.runner import run_episode
from execution_sim.strategies import SpreadUrgencyStrategy, TWAPStrategy


ACTION_NAMES = ("0.0x_pace", "0.5x_pace", "1.0x_pace", "1.5x_pace", "2.0x_pace")


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _episode(agent: TabularQLearningAgent, config: SimulationConfig, seed: int, train: bool, episode: int | None = None) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    env = MarketEnvironment(config, seed)
    twap = TWAPStrategy()
    trace: list[dict[str, object]] = []
    action_counts: Counter[str] = Counter()
    first_update: dict[str, object] | None = None
    while not env.done:
        obs_a = env.observe("A")
        obs_b = env.observe("B")
        state = agent.encoder.encode(obs_a)
        state_seen_before = state in agent.q_table
        q_values_before = agent.q_values(obs_a)
        action_visits_before = agent.action_visit_counts(obs_a)
        action_index = agent.select_action_index(obs_a, explore=train)
        action_multiplier = agent.config.action_multipliers[action_index]
        actions = {"A": agent.action_shares(obs_a, action_index), "B": twap.act(obs_b)}
        result = env.step(actions)
        agent_result = result.agents["A"]
        clipped_request = min(
            max(math.floor(actions["A"]), 0),
            obs_a.remaining_shares,
            obs_a.market.max_trade_per_step,
        )
        next_obs = None if env.done else env.observe("A")
        update = None
        if train:
            update = agent.update(obs_a, action_index, agent_result.reward, next_obs, env.done)
            update = {**update, "seed": seed, "step": obs_a.market.step, "episode": episode}
            if first_update is None or float(update["reward"]) != 0.0 or bool(update["done"]):
                first_update = update
        action_counts[ACTION_NAMES[action_index]] += 1
        trace.append({
            "seed": seed, "step": obs_a.market.step, "state": list(state),
            "steps_remaining": obs_a.market.steps_remaining, "remaining_shares": obs_a.remaining_shares,
            "minimum_required_shares": obs_a.minimum_required_shares,
            "mid_price": obs_a.market.mid_price, "spread_bps": obs_a.market.full_spread_bps,
            "valid_action_indices": json.dumps(agent.valid_action_indices(obs_a)),
            "action_index": action_index, "action_multiplier": action_multiplier,
            "q_values_before": json.dumps(q_values_before),
            "action_visit_counts_before": json.dumps(action_visits_before),
            "state_visit_count_before": sum(action_visits_before),
            "state_seen_before": state_seen_before,
            "q_vector_all_zero_before": all(value == 0.0 for value in q_values_before),
            "action_requested_shares": actions["A"], "completion_constraint_shares": agent_result.completion_constraint_shares,
            "request_after_clip_shares": clipped_request,
            "forced_fill_shares": agent_result.completion_constraint_shares,
            "filled_shares": agent_result.filled_shares, "remaining_after_shares": agent_result.remaining_shares,
            "realized_fill_shortfall": agent_result.realized_fill_shortfall,
            "unfilled_opportunity_cost": agent_result.unfilled_opportunity_cost,
            "fees": agent_result.fee, "terminal_penalty": agent_result.terminal_penalty,
            "total_objective": agent_result.total_objective, "reward": agent_result.reward,
            "next_state": None if next_obs is None else list(agent.encoder.encode(next_obs)),
            "q_update": "" if update is None else json.dumps(update, sort_keys=True), "explore": train,
        })
    if train:
        agent.end_episode()
    return env.final_metrics("A"), trace, {"action_counts": dict(action_counts), "first_update": first_update}


def _evaluate(agent: TabularQLearningAgent, config: SimulationConfig, seeds: list[int], label: str) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    agent.freeze()
    metrics: list[dict[str, object]] = []
    traces: list[dict[str, object]] = []
    actions: Counter[str] = Counter()
    for seed in seeds:
        metric, trace, extra = _episode(agent, config, seed, train=False)
        metrics.append({"phase": label, "seed": seed, "strategy": "q_learning_round4", **metric})
        traces.extend({"phase": label, **row} for row in trace)
        actions.update(extra["action_counts"])
    return metrics, traces, {"action_counts": dict(actions)}


def _run_candidate(config: SimulationConfig, q_config: QLearningConfig, seeds: list[int], agent_seed: int, candidate_id: int) -> tuple[TabularQLearningAgent, list[dict[str, object]], dict[str, object] | None]:
    agent = TabularQLearningAgent(q_config, seed=agent_seed)
    curve: list[dict[str, object]] = []
    first_actual_update: dict[str, object] | None = None
    for episode, seed in enumerate(seeds, start=1):
        metric, _, extra = _episode(agent, config, seed, train=True, episode=episode)
        if first_actual_update is None and extra["first_update"] is not None:
            first_actual_update = extra["first_update"]
        curve.append({
            "candidate_id": candidate_id, "episode": episode, "seed": seed,
            "total_objective_bps": metric["total_objective_bps_of_initial_notional"],
            "realized_fill_shortfall": metric["realized_fill_shortfall"],
            "unfilled_opportunity_cost": metric["unfilled_opportunity_cost"],
            "fees": metric["fees"], "terminal_penalty": metric["terminal_penalty"],
            "unfilled_shares": metric["unfilled_shares"], "epsilon_after_episode": agent.epsilon,
            "q_states": len(agent.q_table),
        })
    return agent, curve, first_actual_update


def _summary(values: list[float]) -> dict[str, float | int]:
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    critical = 1.984 if n >= 60 else 2.045 if n >= 30 else 2.262 if n >= 10 else 2.571
    half = critical * sd / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": mean, "sample_sd": sd, "ci95_low": mean - half, "ci95_high": mean + half}


def run_qlearning_experiment(output_dir: Path, train_count: int = 300, validation_count: int = 60, test_count: int = 100, seed_start: int = 20261103) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty; choose a new path: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    config = SimulationConfig(enforce_completion=True)
    train_seeds = list(range(seed_start, seed_start + train_count))
    validation_seeds = list(range(seed_start + train_count, seed_start + train_count + validation_count))
    test_seeds = list(range(seed_start + train_count + validation_count, seed_start + train_count + validation_count + test_count))
    candidates = [
        QLearningConfig(alpha=0.15, epsilon_decay=0.99),
        QLearningConfig(alpha=0.15, epsilon_decay=0.995),
        QLearningConfig(alpha=0.30, epsilon_decay=0.99),
        QLearningConfig(alpha=0.30, epsilon_decay=0.995),
    ]
    validation_rows: list[dict[str, object]] = []
    training_curve_rows: list[dict[str, object]] = []
    candidate_agents: list[TabularQLearningAgent] = []
    candidate_updates: list[dict[str, object] | None] = []
    for index, q_config in enumerate(candidates):
        agent, curve, actual_update = _run_candidate(config, q_config, train_seeds, seed_start + 10_000 + index, index)
        training_curve_rows.extend(curve)
        metrics, _, _ = _evaluate(agent, config, validation_seeds, "validation")
        values = [float(row["total_objective_bps_of_initial_notional"]) for row in metrics]
        validation_rows.append({"candidate_id": index, "alpha": q_config.alpha, "epsilon_decay": q_config.epsilon_decay, "validation_seed_count": validation_count, "validation_mean_objective_bps": statistics.fmean(values), "q_states": len(agent.q_table)})
        candidate_agents.append(agent)
        candidate_updates.append(actual_update)
    selected_row = min(validation_rows, key=lambda row: (float(row["validation_mean_objective_bps"]), int(row["candidate_id"])))
    selected_index = int(selected_row["candidate_id"])
    selected_agent = candidate_agents[selected_index]
    selected_agent.freeze()
    selected_agent.save(output_dir / "q_table_selected.json")
    loaded_agent = TabularQLearningAgent.load(output_dir / "q_table_selected.json")
    _, selected_trace, _ = _episode(selected_agent, config, test_seeds[0], train=False)
    _, loaded_trace, _ = _episode(loaded_agent, config, test_seeds[0], train=False)
    reload_check = {"status": "passed" if [row["action_index"] for row in selected_trace] == [row["action_index"] for row in loaded_trace] else "failed", "seed": test_seeds[0], "steps": len(selected_trace), "action_sequence_match": [row["action_index"] for row in selected_trace] == [row["action_index"] for row in loaded_trace], "selected_epsilon": selected_agent.epsilon, "loaded_epsilon": loaded_agent.epsilon, "loaded_q_table_unchanged": selected_agent.to_dict() == loaded_agent.to_dict()}
    test_q, test_trace, test_extra = _evaluate(loaded_agent, config, test_seeds, "test")
    twap_rows: list[dict[str, object]] = []
    dynamic_rows: list[dict[str, object]] = []
    q_action_count: Counter[str] = Counter(test_extra["action_counts"])
    for seed in test_seeds:
        _, twap_metrics = run_episode(config, TWAPStrategy(), TWAPStrategy(), seed)
        _, dynamic_metrics = run_episode(config, SpreadUrgencyStrategy(), TWAPStrategy(), seed)
        twap_rows.append({"phase": "test", "seed": seed, "strategy": "twap", **twap_metrics["A"]})
        dynamic_rows.append({"phase": "test", "seed": seed, "strategy": "spread_urgency", **dynamic_metrics["A"]})
    comparison_rows: list[dict[str, object]] = []
    for q_row, twap_row, dynamic_row in zip(test_q, twap_rows, dynamic_rows):
        q_cost = float(q_row["total_objective_bps_of_initial_notional"])
        t_cost = float(twap_row["total_objective_bps_of_initial_notional"])
        d_cost = float(dynamic_row["total_objective_bps_of_initial_notional"])
        comparison_rows.append({"seed": q_row["seed"], "q_objective_bps": q_cost, "twap_objective_bps": t_cost, "spread_urgency_objective_bps": d_cost, "q_minus_twap_bps": q_cost - t_cost, "q_minus_spread_urgency_bps": q_cost - d_cost, "q_unfilled_shares": q_row["unfilled_shares"], "q_fill_ratio": q_row["fill_ratio"]})
    summaries: dict[str, object] = {}
    for strategy, rows in (("q_learning_round4", test_q), ("twap", twap_rows), ("spread_urgency", dynamic_rows)):
        summaries[strategy] = _summary([float(row["total_objective_bps_of_initial_notional"]) for row in rows]) | {"mean_fill_ratio": statistics.fmean(float(row["fill_ratio"]) for row in rows), "mean_unfilled_shares": statistics.fmean(float(row["unfilled_shares"]) for row in rows)}
    summaries["paired_q_minus_twap_bps"] = _summary([float(row["q_minus_twap_bps"]) for row in comparison_rows])
    summaries["paired_q_minus_spread_urgency_bps"] = _summary([float(row["q_minus_spread_urgency_bps"]) for row in comparison_rows])
    config_payload = {"implementation": "round5 diagnostic copy; Q-learning policy and hyperparameters unchanged from round4", "visit_tracking": "per-state-action update counts; test trace reports prior counts without updating", "market_config": config.__dict__, "train_seed_range": [train_seeds[0], train_seeds[-1]], "validation_seed_range": [validation_seeds[0], validation_seeds[-1]], "test_seed_range": [test_seeds[0], test_seeds[-1]], "train_count": train_count, "validation_count": validation_count, "test_count": test_count, "fixed_opponent": "B=TWAP", "selection_rule": "minimum validation mean total_objective_bps; test seeds untouched until selection", "gamma": 1.0, "action_space": list(QLearningConfig().action_multipliers), "state": "(exact steps_remaining, exact own remaining shares, binned observable spread, binned mid deviation bps, binned liquidity ratio, max_trade_per_step)", "reward": "negative realized_fill_shortfall - unfilled_opportunity_cost - fees - terminal_penalty", "completion_constraint": "minimum required fill max(0, remaining-(steps_left-1)*cap), enforce_completion=True", "test_policy": "loaded Q table, epsilon=0, no updates, unseen states return zero values without insertion", "actual_training_update": "selected_training_update.json is from the selected candidate training stream", "abides_reference": "algorithm idea only; no ABIDES source or dependency copied"}
    (output_dir / "qlearning_config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    _write_csv(output_dir / "validation_candidates.csv", list(validation_rows[0]), validation_rows)
    _write_csv(output_dir / "training_curve.csv", list(training_curve_rows[0]), training_curve_rows)
    _write_csv(output_dir / "test_metrics.csv", list(test_q[0]), test_q + twap_rows + dynamic_rows)
    _write_csv(output_dir / "test_paired_comparison.csv", list(comparison_rows[0]), comparison_rows)
    _write_csv(output_dir / "test_action_trace.csv", list(test_trace[0]), test_trace)
    action_rows = [{"phase": "test", "action": key, "count": value, "fraction": value / sum(q_action_count.values())} for key, value in sorted(q_action_count.items())]
    _write_csv(output_dir / "test_action_distribution.csv", ["phase", "action", "count", "fraction"], action_rows)
    (output_dir / "selected_training_update.json").write_text(json.dumps({"selected_candidate_id": selected_index, "update": candidate_updates[selected_index]}, indent=2), encoding="utf-8")
    (output_dir / "model_reload_check.json").write_text(json.dumps(reload_check, indent=2), encoding="utf-8")
    (output_dir / "test_summary.json").write_text(json.dumps({"status": "complete", "summaries": summaries}, indent=2), encoding="utf-8")
    return {"config": output_dir / "qlearning_config.json", "q_table": output_dir / "q_table_selected.json", "validation": output_dir / "validation_candidates.csv", "training_curve": output_dir / "training_curve.csv", "test_metrics": output_dir / "test_metrics.csv", "comparison": output_dir / "test_paired_comparison.csv", "trace": output_dir / "test_action_trace.csv", "action_distribution": output_dir / "test_action_distribution.csv", "training_update": output_dir / "selected_training_update.json", "reload_check": output_dir / "model_reload_check.json", "summary": output_dir / "test_summary.json"}
