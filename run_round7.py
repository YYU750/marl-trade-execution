from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src_round5"))

from execution_sim.environment import MarketEnvironment  # noqa: E402
from execution_sim.models import SimulationConfig  # noqa: E402
from execution_sim.qexperiment import _episode, _summary  # noqa: E402
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent  # noqa: E402
from execution_sim.strategies import TWAPStrategy  # noqa: E402


ROUND7_SEED_START = 20267103
RATIO_BINS = (0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 1.0)
PRICE_SEED = 20267042
BASE_Q_CONFIG = QLearningConfig(alpha=0.30, epsilon_decay=0.99)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def twap_price_decomposition(output_dir: Path) -> dict[str, object]:
    base = SimulationConfig(enforce_completion=True)
    scenarios = {
        "exogenous_only": SimulationConfig(
            **(base.__dict__ | {
                "permanent_impact_bps_per_liquidity_unit": 0.0,
                "temporary_impact_bps_per_liquidity_unit": 0.0,
            })
        ),
        "permanent_impact_only": SimulationConfig(
            **(base.__dict__ | {
                "volatility_bps": 0.0,
                "temporary_impact_bps_per_liquidity_unit": 0.0,
            })
        ),
        "combined": base,
    }
    paths: dict[str, list[dict[str, object]]] = {}
    for label, config in scenarios.items():
        env = MarketEnvironment(config, PRICE_SEED)
        values = [{
            "scenario": label,
            "seed": PRICE_SEED,
            "time_step": 0,
            "mid_price": config.initial_mid_price,
            "relative_change_bps": 0.0,
            "cumulative_log_return_bps": 0.0,
            "exogenous_shock_bps": 0.0,
            "permanent_impact_bps": 0.0,
            "component_sum_log_return_bps": 0.0,
            "decomposition_residual_bps": 0.0,
        }]
        while not env.done:
            snapshot = env.observe_market()
            obs_a = env.observe("A")
            obs_b = env.observe("B")
            twap = TWAPStrategy()
            result = env.step({"A": twap.act(obs_a), "B": twap.act(obs_b)}, snapshot)
            cumulative = math.log(result.mid_price_after / config.initial_mid_price) * 10_000.0
            values.append({
                "scenario": label,
                "seed": PRICE_SEED,
                "time_step": snapshot.step + 1,
                "mid_price": result.mid_price_after,
                "relative_change_bps": (result.mid_price_after / config.initial_mid_price - 1.0) * 10_000.0,
                "cumulative_log_return_bps": cumulative,
                "exogenous_shock_bps": result.exogenous_shock_bps,
                "permanent_impact_bps": result.permanent_impact_bps,
                "component_sum_log_return_bps": cumulative,
                "decomposition_residual_bps": 0.0,
            })
        if len(values) != base.horizon_steps + 1:
            raise AssertionError(f"unexpected path length for {label}: {len(values)}")
        paths[label] = values

    combined = paths["combined"]
    exogenous = paths["exogenous_only"]
    impact = paths["permanent_impact_only"]
    max_residual = 0.0
    for index in range(base.horizon_steps + 1):
        lhs = float(combined[index]["cumulative_log_return_bps"])
        rhs = float(exogenous[index]["cumulative_log_return_bps"]) + float(impact[index]["cumulative_log_return_bps"])
        residual = lhs - rhs
        combined[index]["component_sum_log_return_bps"] = rhs
        combined[index]["decomposition_residual_bps"] = residual
        max_residual = max(max_residual, abs(residual))
    if max_residual > 1e-9:
        raise AssertionError(f"log-price decomposition failed: max residual={max_residual}")
    all_rows = [row for label in scenarios for row in paths[label]]
    write_csv(output_dir / "price_path_decomposition.csv", all_rows)

    colors = {
        "exogenous_only": "#207C8A",
        "permanent_impact_only": "#D17A22",
        "combined": "#3F8A63",
    }
    labels = {
        "exogenous_only": "Exogenous noise only",
        "permanent_impact_only": "Permanent trade impact only",
        "combined": "Noise + trade impact",
    }
    fig, ax = plt.subplots(figsize=(10, 5.6), constrained_layout=True)
    for label, values in paths.items():
        ax.plot(
            [int(row["time_step"]) for row in values],
            [float(row["relative_change_bps"]) for row in values],
            color=colors[label], linewidth=2.4, marker="o", markersize=3.2,
            label=labels[label],
        )
    ax.axhline(0.0, color="#7A8588", linewidth=0.8)
    ax.set_xlabel("Trading minute")
    ax.set_ylabel("Mid-price change from initial price (bp)")
    ax.set_title(f"Same-seed price path decomposition under fixed TWAP (seed {PRICE_SEED})")
    ax.set_xticks(range(0, base.horizon_steps + 1, 5))
    ax.grid(axis="y", color="#D8E0E1", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="best")
    fig.savefig(output_dir / "price_path_decomposition.png", dpi=180)
    plt.close(fig)
    return {
        "seed": PRICE_SEED,
        "time_steps_including_initial": base.horizon_steps + 1,
        "max_absolute_log_decomposition_residual_bps": max_residual,
        "identity": "log(C_t/C_0) = log(A_t/A_0) + log(B_t/B_0)",
        "scenario_overrides": {
            "exogenous_only": {"permanent_impact_bps_per_liquidity_unit": 0.0, "temporary_impact_bps_per_liquidity_unit": 0.0},
            "permanent_impact_only": {"volatility_bps": 0.0, "temporary_impact_bps_per_liquidity_unit": 0.0},
            "combined": "default SimulationConfig",
        },
        "twap_action_path_identical": True,
    }


def train_agent(
    label: str,
    q_config: QLearningConfig,
    train_seeds: list[int],
    agent_seed: int,
    market: SimulationConfig,
) -> tuple[TabularQLearningAgent, list[dict[str, object]], list[dict[str, object]]]:
    agent = TabularQLearningAgent(q_config, seed=agent_seed)
    episode_rows: list[dict[str, object]] = []
    for episode, seed in enumerate(train_seeds, start=1):
        metrics, trace, _ = _episode(agent, market, seed, train=True, episode=episode)
        episode_rows.append({
            "encoding": label,
            "episode": episode,
            "seed": seed,
            "cost_bps": metrics["total_objective_bps_of_initial_notional"],
            "fill_ratio": metrics["fill_ratio"],
            "q_states": len(agent.q_table),
            "q_updates": len(trace),
            "requested_shares": sum(float(row["request_after_clip_shares"]) for row in trace),
            "forced_fill_shares": sum(int(row["forced_fill_shares"]) for row in trace),
            "zero_action_count": sum(int(row["action_index"]) == 0 for row in trace),
        })
    return agent, episode_rows, trace


def state_visit_rows(label: str, agent: TabularQLearningAgent) -> list[dict[str, object]]:
    rows = []
    for state, values in sorted(agent.q_table.items()):
        counts = agent.visit_counts.get(state, [0] * len(agent.config.action_multipliers))
        for action_index, count in enumerate(counts):
            rows.append({
                "encoding": label,
                "state_key": "|".join(map(str, state)),
                "state_visits": sum(counts),
                "action_index": action_index,
                "action_multiplier": agent.config.action_multipliers[action_index],
                "action_visits": count,
                "q_value": values[action_index],
            })
    return rows


def evaluate_agent(
    label: str,
    agent: TabularQLearningAgent,
    seeds: list[int],
    market: SimulationConfig,
    phase: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    agent.freeze()
    episode_rows: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []
    for seed in seeds:
        metrics, trace, _ = _episode(agent, market, seed, train=False)
        episode_rows.append({"encoding": label, "phase": phase, "seed": seed, **metrics})
        for row in trace:
            trace_rows.append({"encoding": label, "phase": phase, **row})
    return episode_rows, trace_rows


def run_encoding_experiment(output_dir: Path, counts: tuple[int, int, int], seed_start: int) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    train_count, validation_count, test_count = counts
    if min(counts) < 2:
        raise ValueError("each seed split must contain at least two episodes")
    train_seeds = list(range(seed_start, seed_start + train_count))
    validation_start = seed_start + train_count
    validation_seeds = list(range(validation_start, validation_start + validation_count))
    test_start = validation_start + validation_count
    test_seeds = list(range(test_start, test_start + test_count))
    if set(train_seeds) & set(validation_seeds) or set(train_seeds) & set(test_seeds) or set(validation_seeds) & set(test_seeds):
        raise AssertionError("train/validation/test seed splits overlap")

    market = SimulationConfig(enforce_completion=True)
    exact_config = BASE_Q_CONFIG
    ratio_config = QLearningConfig(
        alpha=BASE_Q_CONFIG.alpha,
        gamma=BASE_Q_CONFIG.gamma,
        epsilon_start=BASE_Q_CONFIG.epsilon_start,
        epsilon_min=BASE_Q_CONFIG.epsilon_min,
        epsilon_decay=BASE_Q_CONFIG.epsilon_decay,
        action_multipliers=BASE_Q_CONFIG.action_multipliers,
        spread_bins_bps=BASE_Q_CONFIG.spread_bins_bps,
        mid_deviation_bins_bps=BASE_Q_CONFIG.mid_deviation_bins_bps,
        liquidity_ratio_bins=BASE_Q_CONFIG.liquidity_ratio_bins,
        remaining_ratio_bins=RATIO_BINS,
    )
    exact_agent, exact_training, exact_train_trace = train_agent("exact_inventory", exact_config, train_seeds, 20267101, market)
    ratio_agent, ratio_training, ratio_train_trace = train_agent("coarse_remaining_ratio", ratio_config, train_seeds, 20267101, market)

    exact_validation, _ = evaluate_agent("exact_inventory", exact_agent, validation_seeds, market, "validation")
    ratio_validation, _ = evaluate_agent("coarse_remaining_ratio", ratio_agent, validation_seeds, market, "validation")
    exact_test, exact_test_trace = evaluate_agent("exact_inventory", exact_agent, test_seeds, market, "test")
    ratio_test, ratio_test_trace = evaluate_agent("coarse_remaining_ratio", ratio_agent, test_seeds, market, "test")

    twap_test: list[dict[str, object]] = []
    for seed in test_seeds:
        env = MarketEnvironment(market, seed)
        twap = TWAPStrategy()
        while not env.done:
            snapshot = env.observe_market()
            obs_a, obs_b = env.observe("A"), env.observe("B")
            env.step({"A": twap.act(obs_a), "B": twap.act(obs_b)}, snapshot)
        twap_test.append({"encoding": "twap", "phase": "test", "seed": seed, **env.final_metrics("A")})

    by_encoding = {
        "exact_inventory": (exact_agent, exact_training, exact_validation, exact_test, exact_test_trace, exact_train_trace),
        "coarse_remaining_ratio": (ratio_agent, ratio_training, ratio_validation, ratio_test, ratio_test_trace, ratio_train_trace),
    }
    all_train = exact_training + ratio_training
    all_val = exact_validation + ratio_validation
    all_test = exact_test + ratio_test + twap_test
    all_test_trace = exact_test_trace + ratio_test_trace
    paired_rows: list[dict[str, object]] = []
    exact_cost = {int(row["seed"]): float(row["total_objective_bps_of_initial_notional"]) for row in exact_test}
    ratio_cost = {int(row["seed"]): float(row["total_objective_bps_of_initial_notional"]) for row in ratio_test}
    twap_cost = {int(row["seed"]): float(row["total_objective_bps_of_initial_notional"]) for row in twap_test}
    for comparison, values in (
        ("coarse_minus_exact", [ratio_cost[seed] - exact_cost[seed] for seed in test_seeds]),
        ("coarse_minus_twap", [ratio_cost[seed] - twap_cost[seed] for seed in test_seeds]),
        ("exact_minus_twap", [exact_cost[seed] - twap_cost[seed] for seed in test_seeds]),
    ):
        paired_rows.append({"comparison": comparison, **_summary(values)})

    state_rows = state_visit_rows("exact_inventory", exact_agent) + state_visit_rows("coarse_remaining_ratio", ratio_agent)
    write_csv(output_dir / "training_episode_metrics.csv", all_train)
    write_csv(output_dir / "validation_metrics.csv", all_val)
    write_csv(output_dir / "test_episode_metrics.csv", all_test)
    write_csv(output_dir / "test_step_trace.csv", all_test_trace)
    write_csv(output_dir / "state_action_visit_distribution.csv", state_rows)
    write_csv(output_dir / "paired_cost_differences.csv", paired_rows)

    summary_rows: list[dict[str, object]] = []
    validation_by_label = {"exact_inventory": exact_validation, "coarse_remaining_ratio": ratio_validation}
    test_by_label = {"exact_inventory": exact_test, "coarse_remaining_ratio": ratio_test, "twap": twap_test}
    trace_by_label = {"exact_inventory": exact_test_trace, "coarse_remaining_ratio": ratio_test_trace}
    for label in ("exact_inventory", "coarse_remaining_ratio", "twap"):
        metrics = test_by_label[label]
        costs = [float(row["total_objective_bps_of_initial_notional"]) for row in metrics]
        traces = trace_by_label.get(label, [])
        if traces:
            action_count = Counter(int(row["action_index"]) for row in traces)
            unseen_fraction = sum(not bool(row["state_seen_before"]) for row in traces) / len(traces)
            zero_fraction = action_count[0] / len(traces)
            requested_total = statistics.fmean(sum(float(r["request_after_clip_shares"]) for r in trace_by_label[label] if int(r["seed"]) == int(m["seed"])) for m in metrics)
            forced_total = statistics.fmean(sum(int(r["forced_fill_shares"]) for r in trace_by_label[label] if int(r["seed"]) == int(m["seed"])) for m in metrics)
        else:
            action_count = Counter()
            unseen_fraction = 0.0
            zero_fraction = 0.0
            requested_total = statistics.fmean(float(row["filled_shares"]) for row in metrics)
            forced_total = 0.0
        agent = by_encoding[label][0] if label in by_encoding else None
        visits = [sum(counts) for counts in agent.visit_counts.values()] if agent is not None else []
        action_visits = [count for counts in agent.visit_counts.values() for count in counts] if agent is not None else []
        validation_costs = [float(row["total_objective_bps_of_initial_notional"]) for row in validation_by_label.get(label, [])]
        summary_rows.append({
            "encoding": label,
            "test_n": len(metrics),
            "test_mean_cost_bps": statistics.fmean(costs),
            "test_sd_cost_bps": statistics.stdev(costs),
            "test_ci95_low_bps": _summary(costs)["ci95_low"],
            "test_ci95_high_bps": _summary(costs)["ci95_high"],
            "validation_mean_cost_bps": statistics.fmean(validation_costs) if validation_costs else "",
            "trained_q_states": len(agent.q_table) if agent is not None else 0,
            "state_visits_median": statistics.median(visits) if visits else 0,
            "state_visits_p90": sorted(visits)[math.ceil(0.9 * len(visits)) - 1] if visits else 0,
            "visited_state_action_pairs": sum(count > 0 for count in action_visits),
            "unseen_test_state_step_fraction": unseen_fraction,
            "zero_pace_action_fraction": zero_fraction,
            "mean_requested_shares_per_episode": requested_total,
            "mean_forced_fill_shares_per_episode": forced_total,
            "mean_fill_ratio": statistics.fmean(float(row["fill_ratio"]) for row in metrics),
        })
    write_csv(output_dir / "summary.csv", summary_rows)

    for label, (agent, _, _, _, _, _) in by_encoding.items():
        agent.freeze()
        agent.save(output_dir / f"q_table_{label}.json")
    config_payload = {
        "status": "complete",
        "market": market.__dict__,
        "q_learning": {
            "alpha": BASE_Q_CONFIG.alpha,
            "gamma": BASE_Q_CONFIG.gamma,
            "epsilon_start": BASE_Q_CONFIG.epsilon_start,
            "epsilon_min": BASE_Q_CONFIG.epsilon_min,
            "epsilon_decay": BASE_Q_CONFIG.epsilon_decay,
            "action_multipliers": BASE_Q_CONFIG.action_multipliers,
            "all_other_bins_unchanged": True,
        },
        "encoding_change": {
            "control": "exact integer own remaining_shares",
            "treatment": "own remaining_shares / initial_order_shares binned with edges " + repr(RATIO_BINS),
            "only_changed_state_field": "remaining_shares component",
            "execution_uses_true_remaining_shares": True,
            "completion_minimum_uses_true_remaining_shares": True,
            "not_claimed_markov_sufficient": True,
        },
        "same_train_seeds_for_both_encodings": [train_seeds[0], train_seeds[-1]],
        "validation_seeds": [validation_seeds[0], validation_seeds[-1]],
        "test_seeds": [test_seeds[0], test_seeds[-1]],
        "counts": {"train": train_count, "validation": validation_count, "test": test_count},
        "agent_rng_seed_paired": 20267101,
        "validation_role": "report-only; no parameter or model selection because only one encoding per arm was preregistered",
        "test_used_for_tuning": False,
        "smoke": counts != (300, 60, 100),
    }
    (output_dir / "encoding_experiment_config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    return {"summary": summary_rows, "paired": paired_rows, "config": config_payload}


def run(output_dir: Path, smoke: bool = False) -> None:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    price_result = twap_price_decomposition(output_dir)
    counts = (6, 3, 4) if smoke else (300, 60, 100)
    encoding_result = run_encoding_experiment(output_dir, counts, ROUND7_SEED_START)
    (output_dir / "round7_run_receipt.json").write_text(json.dumps({"status": "complete", "price_decomposition": price_result, "encoding_experiment": {"summary": encoding_result["summary"], "paired": encoding_result["paired"], "config": encoding_result["config"]}}, indent=2), encoding="utf-8")
    print(f"ROUND7_COMPLETE output={output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Round 7 market signal decomposition and one state aggregation control.")
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "round7" / "smoke")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    run(args.output, smoke=args.smoke)


if __name__ == "__main__":
    main()
