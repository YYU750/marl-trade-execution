#!/usr/bin/env python3
"""Paired comparison of rule-based and learned execution policies.

All A policies share the same market simulator, fixed B opponent, fee, scenario,
and exogenous random seed for each paired cell. The script also trains a
cost-aligned, schedule-aware Q learner as a measured improvement candidate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from dataclasses import replace
from pathlib import Path
from typing import Any

import run_standard_benchmark as sim
from schedule_aware_q import (
    LimitOrderAwareQLearningAgent,
    ScheduleAwareQLearningAgent,
    ThresholdAlignedDoubleQAgent,
)


ROOT = Path(__file__).resolve().parent
OUT_DEFAULT = ROOT / "outputs" / "matched_rule_q_comparison"
SCENARIOS = (("normal", 1.0), ("high_volatility", 2.0))
RULES = ("G0_TWAP", "G1_dynamic_rule")
TEST_OPPONENTS = sim.TEST_OPPONENTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-episodes", type=int, default=1200)
    parser.add_argument("--training-runs", type=int, default=5)
    parser.add_argument("--rule-guided-episodes", type=int, default=10000,
                        help="episodes per seed for threshold-aligned rule-guided Double Q")
    parser.add_argument("--demonstration-episodes", type=int, default=2500,
                        help="dynamic-rule trajectories per seed for Monte Carlo Q initialization")
    parser.add_argument("--eval-seeds", type=int, default=50)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--training-seed", type=int, default=None,
                        help="separate master seed for training; defaults to --seed")
    parser.add_argument("--improvement-margins", default="0,0.1,0.25,0.5,1,2,5",
                        help="comma-separated Q advantage thresholds in bp")
    parser.add_argument("--output-dir", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()
    try:
        margins = [float(x) for x in args.improvement_margins.split(",")]
    except ValueError:
        parser.error("improvement-margins must be comma-separated numbers")
    if not margins or any(x < 0 for x in margins):
        parser.error("improvement-margins must contain non-negative values")
    args.improvement_margins = tuple(sorted(set(margins)))
    if min(args.train_episodes, args.training_runs, args.rule_guided_episodes,
           args.demonstration_episodes,
           args.eval_seeds) < 1:
        parser.error("training episodes, runs, and eval-seeds must be positive")
    if args.fee_bps < 0:
        parser.error("fee-bps cannot be negative")
    return args


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_advanced_q(path: Path, config: sim.Config) -> sim.QLearningAgent:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("state_encoding") == LimitOrderAwareQLearningAgent.state_encoding:
        raise ValueError(
            "This comparison uses the legacy full-fill environment. A limit-order "
            "Q table must be compared with rule policies in the same limit-order simulator."
        )
    agent_type = (ScheduleAwareQLearningAgent
                  if payload.get("state_encoding") == ScheduleAwareQLearningAgent.state_encoding
                  else sim.QLearningAgent)
    agent = agent_type(config, bool(payload["opponent_aware"]))
    agent.q = {tuple(int(x) for x in state.split("|")): [float(v) for v in values]
               for state, values in payload["q"].items()}
    agent.action_visits = {
        tuple(int(x) for x in state.split("|")): [int(v) for v in values]
        for state, values in payload.get("action_visits", {}).items()
    }
    agent.visited.update(agent.q)
    return agent


def train_candidate(run_id: int, args: argparse.Namespace,
                    environment_config: sim.Config) -> ScheduleAwareQLearningAgent:
    # Inventory-risk regularization had encouraged early buying even though
    # the scorecard minimizes implementation shortfall. Set it to zero during
    # learning so the TD reward aligns with the reported economic cost. The
    # market mechanics and evaluation config remain unchanged.
    learning_config = replace(environment_config, inventory_risk_weight=0.0)
    agent = ScheduleAwareQLearningAgent(learning_config, opponent_aware=True)
    training_master_seed = args.training_seed if args.training_seed is not None else args.seed
    training_seed = training_master_seed + 50_000 + run_id * 10_000
    opponent_rng = random.Random(training_seed)
    for episode in range(args.train_episodes):
        epsilon = learning_config.epsilon_start + (
            learning_config.epsilon_end - learning_config.epsilon_start
        ) * episode / max(args.train_episodes - 1, 1)
        # Train across the full fixed-opponent test family for broader coverage.
        opponent_name = opponent_rng.choice(TEST_OPPONENTS)
        sim.run_episode(
            "G3_opponent_aware_Q", opponent_name, args.fee_bps,
            training_seed + episode * 37 + 11, learning_config, agent, epsilon,
        )
    return agent


def train_rule_guided_candidate(run_id: int, args: argparse.Namespace,
                                environment_config: sim.Config) -> ThresholdAlignedDoubleQAgent:
    learning_config = replace(
        environment_config, inventory_risk_weight=0.0, learning_rate=0.08,
        epsilon_start=0.30, epsilon_end=0.03,
    )
    training_master_seed = args.training_seed if args.training_seed is not None else args.seed
    training_seed = training_master_seed + 500_000 + run_id * 100_000
    training_rng = random.Random(training_seed)
    agent = ThresholdAlignedDoubleQAgent(
        learning_config, opponent_aware=True, seed=training_seed + 17,
    )
    # Initialize the dynamic-rule action values from separate training-only
    # Monte Carlo demonstrations. Evaluation seeds are generated elsewhere.
    for demo_idx in range(args.demonstration_episodes):
        opponent_name = training_rng.choice(TEST_OPPONENTS)
        volatility_multiplier = 2.0 if training_rng.random() < 0.5 else 1.0
        scenario = "high_volatility" if volatility_multiplier > 1.0 else "normal"
        demo_seed = training_seed + demo_idx * 59 + 37
        demo = sim.run_episode(
            "G1_dynamic_rule", opponent_name, args.fee_bps, demo_seed,
            learning_config, trace_enabled=True, scenario_name=scenario,
            volatility_multiplier=volatility_multiplier,
        )
        returns = [0.0] * len(demo.trace)
        running_return = 0.0
        for idx in range(len(demo.trace) - 1, -1, -1):
            row = demo.trace[idx]
            running_return = float(row["step_reward"]) + learning_config.discount * running_return
            if idx == len(demo.trace) - 1:
                running_return -= (float(row["A_remaining_after"]) / learning_config.order_size
                                   * learning_config.terminal_unfilled_penalty_bps)
            returns[idx] = running_return
        for idx, row in enumerate(demo.trace):
            obs = sim.make_observation(
                int(row["t"]) - 1, float(row["A_remaining_before"]),
                float(row["mid_before"]), learning_config.initial_price,
                float(row["B_previous_qty"]), learning_config,
                volatility_multiplier,
            )
            action = min(range(len(sim.ACTIONS)),
                         key=lambda i: abs(sim.ACTIONS[i] - float(row["A_action_multiple"])))
            agent.warm_start(obs, action, returns[idx])
    for episode in range(args.rule_guided_episodes):
        epsilon = learning_config.epsilon_start + (
            learning_config.epsilon_end - learning_config.epsilon_start
        ) * episode / max(args.rule_guided_episodes - 1, 1)
        opponent_name = training_rng.choice(TEST_OPPONENTS)
        volatility_multiplier = 2.0 if training_rng.random() < 0.5 else 1.0
        scenario = "high_volatility" if volatility_multiplier > 1.0 else "normal"
        sim.run_episode(
            "G3_opponent_aware_Q", opponent_name, args.fee_bps,
            training_seed + episode * 53 + 29, learning_config, agent, epsilon,
            scenario_name=scenario, volatility_multiplier=volatility_multiplier,
        )
    return agent


def add_result(rows: list[dict[str, Any]], strategy: str, training_run: int | None,
               opponent: str, scenario: str, seed: int, result: sim.EpisodeResult) -> None:
    rows.append({
        "strategy": strategy,
        "training_run": training_run if training_run is not None else "fixed_or_existing",
        "B_opponent": opponent,
        "scenario": scenario,
        "seed": seed,
        "cost_bps": result.cost_bps,
        "gross_cost_bps": result.gross_cost_bps,
        "fee_cost_bps": result.fee_cost_bps,
        "opportunity_cost_bps": result.opportunity_cost_bps,
        "completion_rate": result.completion_rate,
        "unfilled_shares": result.unfilled_shares,
    })


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["strategy"], row["B_opponent"], row["scenario"]), []).append(row)
    output = []
    for (strategy, opponent, scenario), group in sorted(groups.items()):
        costs = [float(row["cost_bps"]) for row in group]
        output.append({
            "strategy": strategy, "B_opponent": opponent, "scenario": scenario,
            "episodes": len(group), "mean_cost_bps": statistics.fmean(costs),
            "sd_cost_bps": statistics.stdev(costs) if len(costs) > 1 else 0.0,
            "mean_completion_rate": statistics.fmean(float(r["completion_rate"]) for r in group),
            "mean_unfilled_shares": statistics.fmean(float(r["unfilled_shares"]) for r in group),
        })
    return output


def paired_differences(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # For learned policies, average across training seeds within each paired
    # evaluation seed before computing intervals. This avoids treating the
    # repeated rule-policy observation as independent data.
    by_cell: dict[tuple[str, str, str, int], list[float]] = {}
    for row in rows:
        key = (row["strategy"], row["B_opponent"], row["scenario"], int(row["seed"]))
        by_cell.setdefault(key, []).append(float(row["cost_bps"]))
    cell_means = {key: statistics.fmean(values) for key, values in by_cell.items()}
    metadata = sorted({(strategy, opponent, scenario)
                       for strategy, opponent, scenario, _ in by_cell
                       if strategy not in RULES})
    output = []
    for strategy, opponent, scenario in metadata:
        for rule in RULES:
            differences = []
            for seed in sorted({key[3] for key in by_cell
                                if key[:3] == (strategy, opponent, scenario)}):
                learned_key = (strategy, opponent, scenario, seed)
                rule_key = (rule, opponent, scenario, seed)
                if learned_key in cell_means and rule_key in cell_means:
                    differences.append(cell_means[learned_key] - cell_means[rule_key])
            if not differences:
                continue
            mean = statistics.fmean(differences)
            sd = statistics.stdev(differences) if len(differences) > 1 else 0.0
            half_width = 1.96 * sd / math.sqrt(len(differences))
            output.append({
                "strategy": strategy, "rule_baseline": rule,
                "B_opponent": opponent, "scenario": scenario,
                "paired_eval_seeds": len(differences),
                "mean_cost_difference_bps": mean,
                "ci95_low_bps": mean - half_width,
                "ci95_high_bps": mean + half_width,
                "interpretation": "learned policy lower cost" if mean < 0 else "rule baseline lower cost",
            })
    return output


def build_findings(summary: list[dict[str, Any]], differences: list[dict[str, Any]],
                   raw: list[dict[str, Any]], args: argparse.Namespace) -> str:
    lines = [
        "# 规则策略与 Q-learning 配对比较",
        "",
        f"- 运行参数：手续费 {args.fee_bps:g} bp；成本对齐候选训练 {args.training_runs} 个种子 × {args.train_episodes} 回合，阈值对齐双 Q 每个种子先用 {args.demonstration_episodes} 条规则轨迹初始化，再训练 {args.rule_guided_episodes} 回合；每个固定 B 对手/场景 {args.eval_seeds} 个配对评估种子。",
        "- 固定 TWAP、动态规则、历史 G2/G3、当前双边自博弈 A 策略及改进候选 Q 策略均调用同一个 run_standard_benchmark.run_episode 市场模拟器。",
        "- 每个 B 对手、波动场景和评估种子对所有 A 策略完全相同；策略随机数、对手随机数和市场冲击使用隔离随机流。费用、母单、期限、价差、冲击和成交假设相同。",
        "- 改进候选使用紧凑的时间/执行进度状态编码、全部测试对手训练、成本对齐的 TD 奖励，并修复未尝试动作的零初始化 Q 值虚高问题。实际市场清算与评价口径没有改变。",
        "- 阈值对齐双 Q 候选使用 5 步时间阶段、规则阈值对齐的状态边界、双 Q 表降低最大化偏差，并用训练集动态规则轨迹的 Monte Carlo 回报初始化；训练覆盖两种波动场景和全部固定对手。",
        "- 成本差定义为学习策略减规则策略；负值有利于学习策略。区间是按配对评估种子计算的近似 95% 区间；训练种子先在同一评估种子内取均值。",
        "",
        "## 各策略汇总",
        "",
        "下表对五类固定 B 对手等权汇总，详细分层结果见 matched_comparison_summary.csv。",
        "",
        "| A 策略 | 场景 | 平均成本 (bp) | 完成率 | 局数 |",
        "|---|---|---:|---:|---:|",
    ]
    macro: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in summary:
        macro.setdefault((row["strategy"], row["scenario"]), []).append(row)
    for (strategy, scenario), group in sorted(macro.items()):
        n = sum(int(row["episodes"]) for row in group)
        cost = statistics.fmean(float(row["mean_cost_bps"]) for row in group)
        completion = statistics.fmean(float(row["mean_completion_rate"]) for row in group)
        lines.append(f"| {strategy} | {scenario} | {cost:.3f} | {completion:.3f} | {n} |")
    lines.extend(["", "## 配对成本差", "",
                  "| 学习策略 | 对照规则 | B 对手 | 场景 | 配对种子 | 成本差 (bp) | 近似 95% 区间 |",
                  "|---|---|---|---|---:|---:|---:|"])
    for row in differences:
        lines.append(
            f"| {row['strategy']} | {row['rule_baseline']} | {row['B_opponent']} | {row['scenario']} | "
            f"{row['paired_eval_seeds']} | {row['mean_cost_difference_bps']:.3f} | "
            f"[{row['ci95_low_bps']:.3f}, {row['ci95_high_bps']:.3f}] |"
        )
    cell_costs: dict[tuple[str, str, str, int], list[float]] = {}
    for row in raw:
        key = (str(row["strategy"]), row["B_opponent"], row["scenario"], int(row["seed"]))
        cell_costs.setdefault(key, []).append(float(row["cost_bps"]))
    strategy_families = sorted({
        strategy.split("_run")[0] for strategy, _, _, _ in cell_costs
        if strategy not in RULES
    })
    lines.extend(["", "## 汇总配对差", "",
                  "下表将五类固定 B 对手和 50 个评估种子作为 250 个配对测试格；学习策略的 5 个训练种子先在格内取均值。成本差为学习策略减规则策略。",
                  "", "| 学习策略 | 规则基线 | 场景 | 配对格数 | 平均成本差 (bp) | 近似 95% 区间 |",
                  "|---|---|---|---:|---:|---:|"])
    for family in strategy_families:
        for rule in RULES:
            for scenario, _ in SCENARIOS:
                deltas = []
                cells = sorted({(opponent, seed) for strategy, opponent, scen, seed in cell_costs
                                if scen == scenario and strategy.split("_run")[0] == family})
                for opponent, seed in cells:
                    learned_values = [value for (strategy, opp, scen, eval_seed), values in cell_costs.items()
                                      if opp == opponent and scen == scenario and eval_seed == seed and
                                      strategy.split("_run")[0] == family for value in values]
                    baseline_values = cell_costs.get((rule, opponent, scenario, seed), [])
                    if learned_values and baseline_values:
                        deltas.append(statistics.fmean(learned_values) - statistics.fmean(baseline_values))
                if deltas:
                    mean = statistics.fmean(deltas)
                    sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
                    half = 1.96 * sd / math.sqrt(len(deltas))
                    lines.append(f"| {family} | {rule} | {scenario} | {len(deltas)} | {mean:.3f} | [{mean-half:.3f}, {mean+half:.3f}] |")
    lines.extend([
        "", "## 解释限制", "",
        "本比较检验的是：A 的不同执行策略面对相同固定 B 规则时的表现。双边自博弈 Q 表是在另一个学习型 B 的训练分布中得到，再冻结到相同固定对手环境测试；此项衡量迁移表现。改进候选在固定规则对手混合分布中训练。规则策略若成本更低，应如实保留为结果，不因改进候选的训练设置而宣称 Q-learning 必然更优。",
        "当前环境仍假设每个提交的子单全额成交，并以共同可行性下界保证母单在截止前可完成；因此 100% 完成率不是不同策略的区分性证据。",
        "成本降低是该模拟设定下的结果，不意味着真实市场中同样有效。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    out = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    config = sim.Config()

    strategies: list[tuple[str, int | None, sim.QLearningAgent | None]] = [
        ("G0_TWAP", None, None),
        ("G1_dynamic_rule", None, None),
        ("G2_Q_learning_existing", None,
         sim.load_q_table(ROOT / "outputs" / "qtable_G2_Q_learning_30bps.json", config)),
        ("G3_opponent_aware_Q_existing", None,
         sim.load_q_table(ROOT / "outputs" / "qtable_G3_opponent_aware_Q_30bps.json", config)),
    ]

    for run_id in range(1, args.training_runs + 1):
        q_path = ROOT / "outputs" / "advanced_self_play" / f"qtable_run{run_id}_A.json"
        if not q_path.exists():
            raise FileNotFoundError(f"Missing trained self-play policy: {q_path}")
        strategies.append((f"selfplay_Q_A_run{run_id}", run_id, load_advanced_q(q_path, config)))

    for run_id in range(1, args.training_runs + 1):
        print(f"Training cost-aligned schedule-aware Q candidate {run_id}/{args.training_runs} ...", flush=True)
        agent = train_candidate(run_id, args, config)
        strategies.append((f"cost_aligned_schedule_Q_run{run_id}", run_id, agent))

    rule_guided_agents: list[tuple[int, ThresholdAlignedDoubleQAgent]] = []
    for run_id in range(1, args.training_runs + 1):
        print(f"Training threshold-aligned Double Q candidate {run_id}/{args.training_runs} ...", flush=True)
        agent = train_rule_guided_candidate(run_id, args, config)
        rule_guided_agents.append((run_id, agent))
    improvement_margins = args.improvement_margins
    for margin in improvement_margins:
        for run_id, agent in rule_guided_agents:
            strategies.append((f"rule_guided_double_Q_m{margin:g}_run{run_id}", run_id, agent))

    raw: list[dict[str, Any]] = []
    seed_by_cell: dict[tuple[int, str, int], int] = {}
    for scenario_idx, (scenario, volatility_multiplier) in enumerate(SCENARIOS):
        for opponent_idx, opponent in enumerate(TEST_OPPONENTS):
            for eval_idx in range(args.eval_seeds):
                seed_by_cell[(scenario_idx, opponent, eval_idx)] = (
                    args.seed + 2_000_000 + scenario_idx * 100_000 + opponent_idx * 1_000 + eval_idx * 101
                )
    for strategy, training_run, agent in strategies:
        if strategy.startswith("rule_guided_double_Q_m") and isinstance(agent, ThresholdAlignedDoubleQAgent):
            margin_text = strategy.split("_m", 1)[1].split("_run", 1)[0]
            agent.improvement_margin = float(margin_text)
        if agent is not None:
            agent.freeze()
        if strategy in RULES:
            policy_name = strategy
        elif strategy.startswith("G2_"):
            policy_name = "G2_Q_learning"
        else:
            policy_name = "G3_opponent_aware_Q"
        print(f"Evaluating {strategy} ...", flush=True)
        for scenario_idx, (scenario, volatility_multiplier) in enumerate(SCENARIOS):
            for opponent in TEST_OPPONENTS:
                for eval_idx in range(args.eval_seeds):
                    seed = seed_by_cell[(scenario_idx, opponent, eval_idx)]
                    result = sim.run_episode(
                        policy_name, opponent, args.fee_bps, seed, config, agent,
                        scenario_name=scenario, volatility_multiplier=volatility_multiplier,
                    )
                    add_result(raw, strategy, training_run, opponent, scenario, seed, result)

    summary = summarize(raw)
    differences = paired_differences(raw)
    write_csv(out / "matched_comparison_raw.csv", raw)
    write_csv(out / "matched_comparison_summary.csv", summary)
    write_csv(out / "matched_paired_differences.csv", differences)
    (out / "findings.md").write_text(build_findings(summary, differences, raw, args), encoding="utf-8")
    manifest = {
        "fee_bps": args.fee_bps,
        "train_episodes": args.train_episodes,
        "rule_guided_episodes": args.rule_guided_episodes,
        "demonstration_episodes": args.demonstration_episodes,
        "training_runs": args.training_runs,
        "evaluation_seeds_per_opponent_scenario": args.eval_seeds,
        "master_seed": args.seed,
        "training_master_seed": args.training_seed if args.training_seed is not None else args.seed,
        "scenarios": {name: multiplier for name, multiplier in SCENARIOS},
        "B_opponents": list(TEST_OPPONENTS),
        "paired_seed_schedule": "same exogenous market seed for every A policy in each B opponent/scenario/evaluation cell",
        "evaluation_environment": "run_standard_benchmark.run_episode with Config defaults",
        "training_inventory_risk_weight": 0.0,
        "code_sha256": {
            "comparison_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "market_simulator": hashlib.sha256((ROOT / "run_standard_benchmark.py").read_bytes()).hexdigest(),
            "schedule_aware_q_agent": hashlib.sha256((ROOT / "schedule_aware_q.py").read_bytes()).hexdigest(),
            "advanced_self_play": hashlib.sha256((ROOT / "run_advanced_self_play.py").read_bytes()).hexdigest(),
        },
        "improved_q_changes": [
            "schedule-aware compact state abstraction",
            "training on all fixed test-opponent types",
            "remove inventory-risk shaping from TD reward to align with implementation-shortfall scorecard",
            "bootstrap only from tried feasible actions to avoid zero-initialized optimistic bias",
            "rule-threshold-aligned state bins with exact time step and observed volatility regime",
            "Double Q tables to reduce maximization bias",
            "dynamic-rule action prior for untrained states; training on all test opponents and both volatility regimes",
            "Monte Carlo warm-start from dynamic-rule training demonstrations",
            f"evaluation-only conservative policy-improvement margins: {list(improvement_margins)} bp",
        ],
        "counts": {"raw_evaluations": len(raw), "summary_rows": len(summary),
                   "paired_difference_rows": len(differences)},
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Complete. Wrote {len(raw)} paired evaluation rows to {out}", flush=True)


if __name__ == "__main__":
    main()
