from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.environment import MarketEnvironment  # noqa: E402
from execution_sim.models import SimulationConfig  # noqa: E402
from execution_sim.qlearning import TabularQLearningAgent  # noqa: E402
from execution_sim.runner import run_episode  # noqa: E402
from execution_sim.strategies import FrontLoadedStrategy, SpreadUrgencyStrategy, Strategy, TWAPStrategy  # noqa: E402


class ZeroRequestStrategy(Strategy):
    name = "zero_request_diagnostic"

    def act(self, observation):
        del observation
        return 0.0


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(values: list[float]) -> dict[str, float | int]:
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    # The planned evaluation uses 100 paired seeds; t_(0.975,99) ~= 1.984.
    half = 1.984 * sd / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": mean, "sample_sd": sd, "ci95_low": mean - half, "ci95_high": mean + half}


def q_episode(agent: TabularQLearningAgent, config: SimulationConfig, seed: int, opponent: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    env = MarketEnvironment(config, seed)
    b_strategy = FrontLoadedStrategy() if opponent == "front_loaded" else TWAPStrategy()
    trace: list[dict[str, object]] = []
    while not env.done:
        obs_a = env.observe("A")
        obs_b = env.observe("B")
        state = agent.encoder.encode(obs_a)
        q_values = agent.q_values(obs_a)
        visits = agent.action_visit_counts(obs_a)
        selected = agent.select_action_index(obs_a, explore=False)
        requested = agent.action_shares(obs_a, selected)
        clipped = min(max(math.floor(requested), 0), obs_a.remaining_shares, config.max_trade_per_step)
        result = env.step({"A": requested, "B": b_strategy.act(obs_b)})
        row = result.agents["A"]
        trace.append({
            "scenario_seed": seed,
            "step": obs_a.market.step,
            "opponent": opponent,
            "state": json.dumps(state),
            "state_seen_in_training": state in agent.q_table,
            "state_action_update_count": sum(visits),
            "q_values_before_action": json.dumps(q_values),
            "q_action_visits": json.dumps(visits),
            "all_q_values_zero": all(value == 0.0 for value in q_values),
            "valid_action_indices": json.dumps(agent.valid_action_indices(obs_a)),
            "action_index": selected,
            "action_multiplier": agent.config.action_multipliers[selected],
            "request_shares": requested,
            "clipped_request_shares": clipped,
            "minimum_required_shares": row.minimum_required_shares,
            "forced_fill_shares": row.completion_constraint_shares,
            "actual_fill_shares": row.filled_shares,
            "fill_reconciles": row.filled_shares == clipped + row.completion_constraint_shares,
            "remaining_after_shares": row.remaining_shares,
            "total_objective": row.total_objective,
            "reward": row.reward,
        })
    return env.final_metrics("A"), trace


def main() -> None:
    parser = argparse.ArgumentParser(description="Frozen Round 5 Q-learning policy pressure diagnostics.")
    parser.add_argument("--model", type=Path, default=ROOT / "results_round5_standard" / "q_table_selected.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results_round5_pressure")
    parser.add_argument("--seed-start", type=int, default=20261600)
    parser.add_argument("--seeds", type=int, default=100)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    agent = TabularQLearningAgent.load(args.model.resolve())
    if not agent.frozen or agent.epsilon != 0.0:
        raise ValueError("pressure tests require a frozen Q table with epsilon=0")
    base = SimulationConfig(enforce_completion=True)
    scenarios = [
        ("baseline", base, "twap"),
        ("high_volatility_8bps", SimulationConfig(**(base.__dict__ | {"volatility_bps": 8.0})), "twap"),
        ("low_liquidity_10000", SimulationConfig(**(base.__dict__ | {"liquidity_shares": 10_000})), "twap"),
        ("wide_spread_12bps", SimulationConfig(**(base.__dict__ | {"full_spread_bps": 12.0})), "twap"),
        ("opponent_front_loaded", base, "front_loaded"),
    ]
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    metrics_rows: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []
    comparison_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    diagnostic_zero_rows: list[dict[str, object]] = []

    for scenario, config, opponent in scenarios:
        per_policy: dict[str, list[dict[str, object]]] = {"q_learning_round5": [], "twap": [], "spread_urgency": []}
        for seed in seeds:
            q_metrics, q_trace = q_episode(agent, config, seed, opponent)
            q_metrics = {"agent_id": "A", **q_metrics}
            forced = sum(int(row["forced_fill_shares"]) for row in q_trace)
            total_filled = sum(int(row["actual_fill_shares"]) for row in q_trace)
            per_policy["q_learning_round5"].append(q_metrics)
            trace_rows.extend({"scenario": scenario, **row} for row in q_trace)
            for strategy_name, strategy in (("twap", TWAPStrategy()), ("spread_urgency", SpreadUrgencyStrategy())):
                _, both = run_episode(config, strategy, FrontLoadedStrategy() if opponent == "front_loaded" else TWAPStrategy(), seed)
                metrics = both["A"]
                per_policy[strategy_name].append(metrics)
            for strategy_name, rows in per_policy.items():
                row_metrics = rows[-1]
                if row_metrics.get("agent_id") is None:
                    row_metrics = {"agent_id": "A", **row_metrics}
                    rows[-1] = row_metrics
                metrics_rows.append({"scenario": scenario, "opponent": opponent, "seed": seed, "strategy": strategy_name, **row_metrics})
            q_cost = float(q_metrics["total_objective_bps_of_initial_notional"])
            twap_cost = float(per_policy["twap"][-1]["total_objective_bps_of_initial_notional"])
            urgency_cost = float(per_policy["spread_urgency"][-1]["total_objective_bps_of_initial_notional"])
            comparison_rows.append({
                "scenario": scenario, "opponent": opponent, "seed": seed,
                "q_minus_twap_bps": q_cost - twap_cost,
                "q_minus_spread_urgency_bps": q_cost - urgency_cost,
                "q_fill_ratio": q_metrics["fill_ratio"],
                "q_unfilled_shares": q_metrics["unfilled_shares"],
                "q_forced_fill_shares": forced,
                "q_forced_fill_fraction": forced / total_filled if total_filled else 0.0,
            })
        for strategy_name, rows in per_policy.items():
            costs = [float(row["total_objective_bps_of_initial_notional"]) for row in rows]
            fill_ratio = statistics.fmean(float(row["fill_ratio"]) for row in rows)
            unfilled = statistics.fmean(float(row["unfilled_shares"]) for row in rows)
            realized = statistics.fmean(float(row["realized_fill_shortfall"]) for row in rows)
            opportunity = statistics.fmean(float(row["unfilled_opportunity_cost"]) for row in rows)
            fees = statistics.fmean(float(row["fees"]) for row in rows)
            terminal = statistics.fmean(float(row["terminal_penalty"]) for row in rows)
            relevant = [row for row in comparison_rows if row["scenario"] == scenario]
            forced_shares = sum(int(row["q_forced_fill_shares"]) for row in relevant) if strategy_name == "q_learning_round5" else 0
            forced_fraction = (
                forced_shares / sum(int(value["filled_shares"]) for value in rows)
                if strategy_name == "q_learning_round5" and rows else 0.0
            )
            summary_rows.append({
                "scenario": scenario, "opponent": opponent, "strategy": strategy_name,
                **summarize(costs), "mean_fill_ratio": fill_ratio, "mean_unfilled_shares": unfilled,
                "mean_realized_fill_shortfall": realized,
                "mean_unfilled_opportunity_cost": opportunity,
                "mean_fees": fees,
                "mean_terminal_penalty": terminal,
                "forced_fill_share_fraction": forced_fraction,
                "note": "completion is a hard environment constraint" if config.enforce_completion else "",
            })
        diffs = [row for row in comparison_rows if row["scenario"] == scenario]
        summary_rows.append({
            "scenario": scenario, "opponent": opponent, "strategy": "paired_q_minus_twap",
            **summarize([float(row["q_minus_twap_bps"]) for row in diffs]),
            "mean_fill_ratio": statistics.fmean(float(row["q_fill_ratio"]) for row in diffs),
            "mean_unfilled_shares": statistics.fmean(float(row["q_unfilled_shares"]) for row in diffs),
            "mean_realized_fill_shortfall": "", "mean_unfilled_opportunity_cost": "",
            "mean_fees": "", "mean_terminal_penalty": "",
            "forced_fill_share_fraction": statistics.fmean(float(row["q_forced_fill_fraction"]) for row in diffs),
            "note": "paired by identical seed; positive means Q costs more",
        })
        summary_rows.append({
            "scenario": scenario, "opponent": opponent, "strategy": "paired_q_minus_spread_urgency",
            **summarize([float(row["q_minus_spread_urgency_bps"]) for row in diffs]),
            "mean_fill_ratio": statistics.fmean(float(row["q_fill_ratio"]) for row in diffs),
            "mean_unfilled_shares": statistics.fmean(float(row["q_unfilled_shares"]) for row in diffs),
            "mean_realized_fill_shortfall": "", "mean_unfilled_opportunity_cost": "",
            "mean_fees": "", "mean_terminal_penalty": "",
            "forced_fill_share_fraction": statistics.fmean(float(row["q_forced_fill_fraction"]) for row in diffs),
            "note": "paired by identical seed; positive means Q costs more",
        })
    model_config_path = args.model.resolve().parent / "qlearning_config.json"
    if not model_config_path.is_file():
        raise FileNotFoundError(f"standard run config required for test-set diagnostic: {model_config_path}")
    model_config = json.loads(model_config_path.read_text(encoding="utf-8"))
    test_seed_range = model_config["test_seed_range"]
    for seed in range(int(test_seed_range[0]), int(test_seed_range[1]) + 1):
        q_metrics, _ = q_episode(agent, base, seed, "twap")
        _, both = run_episode(base, ZeroRequestStrategy(), TWAPStrategy(), seed)
        metric = {"agent_id": "A", **both["A"]}
        q_cost = float(q_metrics["total_objective_bps_of_initial_notional"])
        zero_cost = float(metric["total_objective_bps_of_initial_notional"])
        diagnostic_zero_rows.append({"scenario": "standard_test_seed_posthoc", "opponent": "twap", "seed": seed,
                                     "strategy": "zero_request_posthoc_diagnostic", **metric,
                                     "q_objective_bps": q_cost,
                                     "q_minus_zero_request_bps": q_cost - zero_cost,
                                     "interpretation": "post-hoc diagnostic on the standard test seeds; not a pre-registered benchmark"})

    write_csv(output / "pressure_episode_metrics.csv", metrics_rows)
    write_csv(output / "pressure_q_action_trace.csv", trace_rows)
    write_csv(output / "pressure_paired_differences.csv", comparison_rows)
    write_csv(output / "pressure_summary.csv", summary_rows)
    write_csv(output / "posthoc_zero_request_diagnostic.csv", diagnostic_zero_rows)
    config_payload = {
        "model": str(args.model.resolve()),
        "model_frozen": agent.frozen,
        "epsilon": agent.epsilon,
        "updates_during_pressure_evaluation": False,
        "seed_range": [seeds[0], seeds[-1]],
        "seed_count": len(seeds),
        "scenarios": [{"name": name, "market_config": config.__dict__, "opponent": opponent} for name, config, opponent in scenarios],
        "strategies": ["round5 frozen Q", "TWAP", "spread_urgency"],
        "pairing": "same seed gives the same exogenous RNG stream across policies within each scenario",
        "posthoc_diagnostic": "zero-request policy is exploratory and must not be treated as a confirmatory benchmark",
    }
    (output / "pressure_config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    print(f"PRESSURE_COMPLETE scenarios={len(scenarios)} seeds={len(seeds)} q_trace_rows={len(trace_rows)}")
    print(f"OUTPUT={output}")


if __name__ == "__main__":
    main()
