from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Callable

from execution_sim.environment import MarketEnvironment
from execution_sim.models import AgentObservation, SimulationConfig
from execution_sim.qlearning import QLearningConfig, TabularQLearningAgent
from execution_sim.strategies import FrontLoadedStrategy, SpreadUrgencyStrategy, TWAPStrategy


QAgent = TabularQLearningAgent
Policy = Callable[[AgentObservation], float]
ACTION_LABELS = ("0.0x", "0.5x", "1.0x", "1.5x", "2.0x")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _rule(name: str) -> Policy:
    if name == "twap":
        return TWAPStrategy().act
    if name == "front_loaded":
        return FrontLoadedStrategy().act
    if name == "spread_urgency":
        return SpreadUrgencyStrategy().act
    raise ValueError(f"unsupported fixed policy: {name}")


def run_episode(
    config: SimulationConfig,
    seed: int,
    policies: dict[str, QAgent | Policy],
    train: bool = False,
    keep_trace: bool = False,
) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    env = MarketEnvironment(config, seed)
    trace: list[dict[str, object]] = []
    actions_seen = {agent_id: Counter() for agent_id in env.AGENTS}
    requested_sum = Counter()
    forced_sum = Counter()
    updates = Counter()
    while not env.done:
        observations = {agent_id: env.observe(agent_id) for agent_id in env.AGENTS}
        snapshot = observations["A"].market
        if observations["B"].market is not snapshot:
            raise AssertionError("agents did not receive the same market snapshot")

        actions: dict[str, float] = {}
        choices: dict[str, dict[str, object]] = {}
        for agent_id in env.AGENTS:
            policy = policies[agent_id]
            observation = observations[agent_id]
            if isinstance(policy, QAgent):
                state = policy.encoder.encode(observation)
                q_before = policy.q_values(observation)
                visits_before = policy.action_visit_counts(observation)
                action_index = policy.select_action_index(observation, explore=train)
                action = policy.action_shares(observation, action_index)
                choices[agent_id] = {
                    "kind": "q", "state": state, "q_before": q_before,
                    "visits_before": visits_before, "action_index": action_index,
                    "multiplier": policy.config.action_multipliers[action_index],
                }
                actions_seen[agent_id][ACTION_LABELS[action_index]] += 1
            else:
                action = float(policy(observation))
                choices[agent_id] = {"kind": "rule", "action_index": "", "multiplier": ""}
                actions_seen[agent_id]["rule"] += 1
            actions[agent_id] = action

        # The environment consumes both decisions together; neither policy sees the other's action.
        result = env.step(actions, snapshot=snapshot)
        next_observations = None if env.done else {agent_id: env.observe(agent_id) for agent_id in env.AGENTS}
        for agent_id in env.AGENTS:
            step = result.agents[agent_id]
            requested_sum[agent_id] += min(
                max(math.floor(actions[agent_id]), 0),
                observations[agent_id].remaining_shares,
                observations[agent_id].market.max_trade_per_step,
            )
            forced_sum[agent_id] += step.completion_constraint_shares
            choice = choices[agent_id]
            update: dict[str, object] | None = None
            if train and choice["kind"] == "q":
                agent = policies[agent_id]
                assert isinstance(agent, QAgent)
                update = agent.update(
                    observations[agent_id], int(choice["action_index"]), step.reward,
                    None if env.done else next_observations[agent_id], env.done,
                )
                updates[agent_id] += 1
            if keep_trace:
                trace.append({
                    "seed": seed, "step": snapshot.step, "agent_id": agent_id,
                    "mid_before": snapshot.mid_price, "same_snapshot_id": id(snapshot),
                    "remaining_before": observations[agent_id].remaining_shares,
                    "valid_actions": json.dumps(
                        policies[agent_id].valid_action_indices(observations[agent_id])
                        if choice["kind"] == "q" else []
                    ),
                    "q_state": json.dumps(choice.get("state", [])),
                    "q_before": json.dumps(choice.get("q_before", [])),
                    "visits_before": json.dumps(choice.get("visits_before", [])),
                    "action_index": choice["action_index"], "multiplier": choice["multiplier"],
                    "requested_shares": actions[agent_id],
                    "forced_shares": step.completion_constraint_shares,
                    "filled_shares": step.filled_shares, "remaining_after": step.remaining_shares,
                    "joint_filled_shares": result.joint_filled_shares,
                    "temporary_impact_bps": result.temporary_impact_bps,
                    "permanent_impact_bps": result.permanent_impact_bps,
                    "mid_after": result.mid_price_after, "reward": step.reward,
                    "total_objective": step.total_objective,
                    "q_update": "" if update is None else json.dumps(update, sort_keys=True),
                })

    if train:
        for policy in policies.values():
            if isinstance(policy, QAgent):
                policy.end_episode()
    metrics: dict[str, dict[str, object]] = {}
    for agent_id in env.AGENTS:
        item = env.final_metrics(agent_id)
        item.update({
            "requested_after_clip_shares": int(requested_sum[agent_id]),
            "forced_fill_shares": int(forced_sum[agent_id]),
            "action_distribution": json.dumps(dict(actions_seen[agent_id]), sort_keys=True),
            "q_updates": int(updates[agent_id]),
            "q_states": len(policies[agent_id].q_table) if isinstance(policies[agent_id], QAgent) else 0,
            "q_state_action_visits": sum(sum(x) for x in policies[agent_id].visit_counts.values()) if isinstance(policies[agent_id], QAgent) else 0,
        })
        metrics[agent_id] = item
    return metrics, trace


def _summary_rows(metric_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in metric_rows:
        groups.setdefault((str(row["scenario"]), str(row["agent_id"])), []).append(row)
    output = []
    for (scenario, agent_id), rows in sorted(groups.items()):
        costs = [float(row["total_objective_bps_of_initial_notional"]) for row in rows]
        mean = statistics.fmean(costs)
        sd = statistics.stdev(costs) if len(costs) > 1 else 0.0
        half = 1.984 * sd / math.sqrt(len(costs)) if len(costs) > 1 else 0.0
        action_counts: Counter[str] = Counter()
        for row in rows:
            action_counts.update(json.loads(str(row["action_distribution"])))
        total_actions = sum(action_counts.values())
        action_distribution = {
            action: {"count": count, "fraction": count / total_actions}
            for action, count in sorted(action_counts.items())
        }
        output.append({
            "scenario": scenario, "agent_id": agent_id, "n": len(rows),
            "mean_cost_bps": mean, "sample_sd_bps": sd,
            "ci95_low_bps": mean - half, "ci95_high_bps": mean + half,
            "mean_fill_ratio": statistics.fmean(float(x["fill_ratio"]) for x in rows),
            "mean_requested_after_clip_shares": statistics.fmean(float(x["requested_after_clip_shares"]) for x in rows),
            "mean_forced_fill_shares": statistics.fmean(float(x["forced_fill_shares"]) for x in rows),
            "mean_q_states": statistics.fmean(float(x["q_states"]) for x in rows),
            "mean_q_state_action_visits": statistics.fmean(float(x["q_state_action_visits"]) for x in rows),
            "mean_realized_fill_shortfall": statistics.fmean(float(x["realized_fill_shortfall"]) for x in rows),
            "mean_unfilled_opportunity_cost": statistics.fmean(float(x["unfilled_opportunity_cost"]) for x in rows),
            "mean_fees": statistics.fmean(float(x["fees"]) for x in rows),
            "mean_terminal_penalty": statistics.fmean(float(x["terminal_penalty"]) for x in rows),
            "action_distribution": json.dumps(action_distribution, sort_keys=True),
        })
    return output


def run_dual_experiment(
    output_dir: Path,
    baseline_q_path: Path,
    train_episodes: int = 300,
    test_episodes: int = 100,
    train_seed_start: int = 20263103,
    test_seed_start: int = 20263403,
) -> None:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    if train_episodes < 2 or test_episodes < 2:
        raise ValueError("train_episodes and test_episodes must be at least 2")
    if set(range(train_seed_start, train_seed_start + train_episodes)) & set(range(test_seed_start, test_seed_start + test_episodes)):
        raise ValueError("training and test seed ranges overlap")
    output_dir.mkdir(parents=True, exist_ok=True)

    frozen_g1 = QAgent.load(baseline_q_path)
    inherited_config: QLearningConfig = frozen_g1.config
    frozen_g1.freeze()
    q_a = QAgent(inherited_config, seed=20261101)
    q_b = QAgent(inherited_config, seed=20261102)
    if q_a.q_table is q_b.q_table or q_a.visit_counts is q_b.visit_counts:
        raise AssertionError("independent learners unexpectedly share tables")

    config = SimulationConfig(enforce_completion=True)
    train_seeds = list(range(train_seed_start, train_seed_start + train_episodes))
    test_seeds = list(range(test_seed_start, test_seed_start + test_episodes))
    diagnostics: list[dict[str, object]] = []
    selected_trace: list[dict[str, object]] = []
    for episode, seed in enumerate(train_seeds, 1):
        before = {"A": len(q_a.q_table), "B": len(q_b.q_table)}
        episode_metrics, trace = run_episode(config, seed, {"A": q_a, "B": q_b}, train=True, keep_trace=(episode == 1))
        if episode == 1:
            selected_trace = trace
        for agent_id in ("A", "B"):
            m = episode_metrics[agent_id]
            diagnostics.append({
                "episode": episode, "seed": seed, "agent_id": agent_id,
                "cost_bps": m["total_objective_bps_of_initial_notional"],
                "fill_ratio": m["fill_ratio"], "requested_after_clip_shares": m["requested_after_clip_shares"],
                "forced_fill_shares": m["forced_fill_shares"], "action_distribution": m["action_distribution"],
                "q_states_before": before[agent_id], "q_states_after": len((q_a if agent_id == "A" else q_b).q_table),
                "q_updates": m["q_updates"], "q_state_action_visits": m["q_state_action_visits"],
                "epsilon_after_episode": (q_a if agent_id == "A" else q_b).epsilon,
            })
    q_a.freeze()
    q_b.freeze()
    q_a_path = output_dir / "iql_agent_A.json"
    q_b_path = output_dir / "iql_agent_B.json"
    q_a.save(q_a_path)
    q_b.save(q_b_path)
    _write_csv(output_dir / "dual_q_training_diagnostics.csv", diagnostics)
    _write_csv(output_dir / "dual_q_training_episode1_trace.csv", selected_trace)

    twap_a, twap_b = _rule("twap"), _rule("twap")
    front = _rule("front_loaded")
    scenarios: list[tuple[str, dict[str, QAgent | Policy]]] = [
        ("G0_rule_twap_vs_twap", {"A": twap_a, "B": twap_b}),
        ("G1_frozen_round5_q_vs_twap", {"A": frozen_g1, "B": _rule("twap")}),
        ("G2_iql_selfplay", {"A": q_a, "B": q_b}),
        ("G3_iql_A_vs_twap", {"A": q_a, "B": _rule("twap")}),
        ("G3_iql_A_vs_front_loaded", {"A": q_a, "B": front}),
    ]
    metrics_rows: list[dict[str, object]] = []
    for scenario, policies in scenarios:
        for seed in test_seeds:
            episode_metrics, _ = run_episode(config, seed, policies, train=False)
            for agent_id in ("A", "B"):
                metrics_rows.append({"scenario": scenario, "seed": seed, **episode_metrics[agent_id]})
    _write_csv(output_dir / "dual_q_test_summary.csv", _summary_rows(metrics_rows))
    _write_csv(output_dir / "dual_q_test_by_seed.csv", metrics_rows)
    metric_index = {
        (str(row["scenario"]), int(row["seed"]), str(row["agent_id"])): float(row["total_objective_bps_of_initial_notional"])
        for row in metrics_rows
    }
    pair_specs = (
        ("G1_A_Q_vs_G0_A_TWAP", "G1_frozen_round5_q_vs_twap", "G0_rule_twap_vs_twap", "A"),
        ("G2_A_IQL_vs_G0_A_TWAP", "G2_iql_selfplay", "G0_rule_twap_vs_twap", "A"),
        ("G2_B_IQL_vs_G0_B_TWAP", "G2_iql_selfplay", "G0_rule_twap_vs_twap", "B"),
        ("G3_A_vs_TWAP_minus_selfplay", "G3_iql_A_vs_twap", "G2_iql_selfplay", "A"),
        ("G3_A_vs_front_minus_selfplay", "G3_iql_A_vs_front_loaded", "G2_iql_selfplay", "A"),
    )
    paired_rows = []
    for comparison, treatment, control, agent_id in pair_specs:
        differences = [
            metric_index[(treatment, seed, agent_id)] - metric_index[(control, seed, agent_id)]
            for seed in test_seeds
        ]
        mean = statistics.fmean(differences)
        sd = statistics.stdev(differences)
        half = 1.984 * sd / math.sqrt(len(differences))
        paired_rows.append({
            "comparison": comparison, "agent_id": agent_id, "n": len(differences),
            "paired_mean_delta_bps": mean, "sample_sd_bps": sd,
            "ci95_low_bps": mean - half, "ci95_high_bps": mean + half,
            "direction": "treatment_minus_control",
        })
    _write_csv(output_dir / "dual_q_paired_differences.csv", paired_rows)
    with (output_dir / "round6_config.json").open("w", encoding="utf-8") as stream:
        json.dump({
            "status": "complete", "market_config": config.__dict__,
            "baseline_q_table": "results_round5_standard/q_table_selected.json",
            "baseline_q_sha256": _sha256(baseline_q_path),
            "inherited_q_config": q_a.to_dict()["config"],
            "trained_q_tables": {
                "A": {"path": q_a_path.name, "sha256": _sha256(q_a_path), "states": len(q_a.q_table)},
                "B": {"path": q_b_path.name, "sha256": _sha256(q_b_path), "states": len(q_b.q_table)},
            },
            "independent_agent_rng_seeds": {"A": 20261101, "B": 20261102},
            "train_seed_range": [train_seeds[0], train_seeds[-1]], "train_episodes": train_episodes,
            "test_seed_range": [test_seeds[0], test_seeds[-1]], "test_episodes": test_episodes,
            "no_validation_or_test_tuning": True,
            "G0": "TWAP vs TWAP; same market seeds",
            "G1": "frozen Round 5 A Q-table vs TWAP B",
            "G2": "independent Q tables; simultaneous actions and independent reward updates",
            "G3": "frozen self-play A Q-table tested against TWAP and front-loaded B",
            "iql_note": "independent Q-learning faces a policy-dependent non-stationary environment; no equilibrium claim",
        }, stream, indent=2)
