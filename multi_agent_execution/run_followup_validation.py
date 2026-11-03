#!/usr/bin/env python3
"""Fresh-seed validation of rule-guided Double Q against TWAP and dynamic rules."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import run_matched_rule_q_comparison as comparison
import run_standard_benchmark as sim
from schedule_aware_q import ThresholdAlignedDoubleQAgent


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "followup_validation_seed20261112"
TRAINING_MASTER_SEED = 20261107
TEST_MASTER_SEED = 20261112
FEE_BPS = 30.0
DEMONSTRATION_EPISODES = 2500
Q_EPISODES = 10000
EVALUATION_SEEDS = 50
FIXED_MARGIN_BPS = 5.0
POLICIES = ("G0_TWAP", "G1_dynamic_rule", "rule_guided_double_Q_m5")
SCENARIOS = (("normal", 1.0), ("high_volatility", 2.0))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def policy_digest(agent: ThresholdAlignedDoubleQAgent) -> str:
    def encode_table(table: dict[tuple[int, ...], list[Any]]) -> dict[str, list[Any]]:
        return {"|".join(map(str, key)): value for key, value in sorted(table.items())}

    payload = {
        "q": encode_table(agent.q),
        "qa": encode_table(agent.qa),
        "qb": encode_table(agent.qb),
        "action_visits": encode_table(agent.action_visits),
        "prior_actions": {"|".join(map(str, key)): value
                          for key, value in sorted(agent.prior_actions.items())},
        "visited": [list(key) for key in sorted(agent.visited)],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def save_policy(agent: ThresholdAlignedDoubleQAgent, path: Path) -> None:
    def encode_table(table: dict[tuple[int, ...], list[Any]]) -> dict[str, list[Any]]:
        return {"|".join(map(str, key)): value for key, value in sorted(table.items())}

    payload = {
        "state_encoding": agent.state_encoding,
        "opponent_aware": agent.opponent_aware,
        "discount": agent.config.discount,
        "improvement_margin_bps": agent.improvement_margin,
        "minimum_improvement_visits": agent.minimum_improvement_visits,
        "q": encode_table(agent.q),
        "qa": encode_table(agent.qa),
        "qb": encode_table(agent.qb),
        "action_visits": encode_table(agent.action_visits),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_policy(path: Path, config: sim.Config) -> ThresholdAlignedDoubleQAgent:
    payload = json.loads(path.read_text(encoding="utf-8"))
    agent = ThresholdAlignedDoubleQAgent(config, opponent_aware=bool(payload["opponent_aware"]))

    def decode_table(table: dict[str, list[Any]]) -> dict[tuple[int, ...], list[Any]]:
        return {tuple(int(part) for part in key.split("|")): values
                for key, values in table.items()}

    agent.q = decode_table(payload["q"])
    agent.qa = decode_table(payload["qa"])
    agent.qb = decode_table(payload["qb"])
    agent.action_visits = decode_table(payload["action_visits"])
    agent.improvement_margin = float(payload["improvement_margin_bps"])
    agent.minimum_improvement_visits = int(payload["minimum_improvement_visits"])
    return agent


def randomized_completion_control(trials: int = 1000) -> dict[str, Any]:
    """Compare the old unconstrained random schedule with the repaired one."""
    config = sim.Config()
    old_incomplete = new_incomplete = 0
    old_unfilled: list[float] = []
    for seed in range(trials):
        stream_seed = seed ^ 0x2468ACE0
        old_rng = random.Random(stream_seed)
        repaired = sim.OpponentAgent("randomized", config, random.Random(stream_seed))
        old_remaining = new_remaining = config.order_size
        for t in range(config.horizon):
            old_remaining -= min(old_remaining, config.base_slice * old_rng.choice((0.5, 1.5)))
            new_remaining -= repaired.desired_qty(t, new_remaining)
        old_unfilled.append(max(0.0, old_remaining))
        old_incomplete += int(old_remaining > 1e-7)
        new_incomplete += int(new_remaining > 1e-7)
    return {
        "trials": trials,
        "old_incomplete_episodes": old_incomplete,
        "old_mean_unfilled_shares": statistics.fmean(old_unfilled),
        "repaired_incomplete_episodes": new_incomplete,
    }


def paired_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    costs = {(row["strategy"], row["B_opponent"], row["scenario"], int(row["seed"])):
             float(row["cost_bps"]) for row in rows}
    output = []
    for scenario, _ in SCENARIOS:
        for opponent in sim.TEST_OPPONENTS:
            for strategy in ("rule_guided_double_Q_m5",):
                for baseline in ("G1_dynamic_rule", "G0_TWAP"):
                    seed_ids = sorted({
                        seed for candidate, b_name, scen, seed in costs
                        if b_name == opponent and scen == scenario
                        and candidate in (strategy, baseline)
                    })
                    differences = [
                        costs[(strategy, opponent, scenario, seed)]
                        - costs[(baseline, opponent, scenario, seed)]
                        for seed in seed_ids
                        if (strategy, opponent, scenario, seed) in costs
                        and (baseline, opponent, scenario, seed) in costs
                    ]
                    if differences:
                        mean = statistics.fmean(differences)
                        sd = statistics.stdev(differences) if len(differences) > 1 else 0.0
                        half = 1.96 * sd / math.sqrt(len(differences))
                        output.append({
                            "scenario": scenario, "B_opponent": opponent,
                            "strategy": strategy, "baseline": baseline,
                            "paired_cells": len(differences), "mean_cost_difference_bps": mean,
                            "ci95_low_bps": mean - half, "ci95_high_bps": mean + half,
                        })
        for strategy in ("rule_guided_double_Q_m5",):
            for baseline in ("G1_dynamic_rule", "G0_TWAP"):
                seed_ids = sorted({
                    seed for candidate, _, scen, seed in costs
                    if scen == scenario and candidate in (strategy, baseline)
                })
                differences = [
                    costs[(strategy, opponent, scenario, seed)]
                    - costs[(baseline, opponent, scenario, seed)]
                    for opponent in sim.TEST_OPPONENTS
                    for seed in seed_ids
                    if (strategy, opponent, scenario, seed) in costs
                    and (baseline, opponent, scenario, seed) in costs
                ]
                mean = statistics.fmean(differences)
                sd = statistics.stdev(differences) if len(differences) > 1 else 0.0
                half = 1.96 * sd / math.sqrt(len(differences))
                output.append({
                    "scenario": scenario, "B_opponent": "ALL_EQUAL_WEIGHTED",
                    "strategy": strategy, "baseline": baseline,
                    "paired_cells": len(differences), "mean_cost_difference_bps": mean,
                    "ci95_low_bps": mean - half, "ci95_high_bps": mean + half,
                })
    return output


def build_findings(summary: list[dict[str, Any]], differences: list[dict[str, Any]],
                   actions: list[dict[str, Any]], agreement: list[dict[str, Any]],
                   b_completion: list[dict[str, Any]], table_unchanged: bool,
                   gamma_check: dict[str, float], random_control: dict[str, Any]) -> str:
    lines = [
        "# 选定 Double Q 的独立留出验证",
        "",
        "本次只验证固定 5 bp 门槛的规则引导 Double Q，不在新测试集上重新挑门槛，也不重跑其余 Q 变体。",
        f"测试主种子为 `{TEST_MASTER_SEED}`；每类 B 对手、每个场景使用 {EVALUATION_SEEDS} 个配对种子，费用为 {FEE_BPS:g} bp。",
        "B 随机策略保留 0.5/1.5 TWAP 随机节奏，但加入按剩余步数计算的最低可行成交量，避免它把未完成订单带入终局。",
        f"完单约束控制对比 {random_control['trials']} 组随机流：修正前 {random_control['old_incomplete_episodes']} 局未完成（平均剩余 {random_control['old_mean_unfilled_shares']:.1f} 股），修正后 {random_control['repaired_incomplete_episodes']} 局未完成。",
        "",
        "## 成本和完成率",
        "",
        "成本为总实施缺口，越低越好。每个 Q 训练种子只使用一次；区间反映 250 个对手×随机种子配对格的评估波动，不包含训练种子不确定性。",
        "",
        "| 场景 | 策略 | 平均成本 (bp) | A 完成率 | B 完成率 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(f"| {row['scenario']} | {row['strategy']} | {row['mean_cost_bps']:.3f} ± {row['sd_cost_bps']:.3f} | {row['mean_A_completion']:.3%} | {row['mean_B_completion']:.3%} |")
    lines.extend(["", "## 配对成本差（Double Q 减基线）", "",
                  "负数有利于 Double Q；区间为近似 95% 配对区间。", "",
                  "| 场景 | B 对手 | 基线 | 配对格 | 平均差 (bp) | 近似 95% 区间 |",
                  "|---|---|---|---:|---:|---:|"])
    for row in differences:
        lines.append(f"| {row['scenario']} | {row['B_opponent']} | {row['baseline']} | {row['paired_cells']} | {row['mean_cost_difference_bps']:.3f} | [{row['ci95_low_bps']:.3f}, {row['ci95_high_bps']:.3f}] |")
    lines.extend(["", "## 动作一致性", "",
                  "一致率逐时点比较 Double Q 与动态规则在相同对手、场景、种子下的动作；策略改变市场路径，因此后续状态可以不同。", "",
                  "| 场景 | B 对手 | Q 与动态规则动作一致率 |",
                  "|---|---|---:|"])
    for row in agreement:
        lines.append(f"| {row['scenario']} | {row['B_opponent']} | {row['agreement_rate']:.2%} |")
    lines.extend(["", "## γ 与冻结策略检查", "",
                  f"训练配置 γ = {gamma_check['gamma']:.2f}。非终止样例目标：`−2 + γ × (−10) = {gamma_check['nonterminal_target']:.3f}`；终止样例不 bootstrap：`{gamma_check['terminal_target']:.3f}`。Double Q 更新使用 `reward + γ × evaluator_Q(next_state, argmax(chosen_Q(next_state)))`。",
                  f"评估前后策略表与访问计数字典的 SHA-256 一致：**{table_unchanged}**。冻结后若发生学习更新会直接报错。",
                  "", "## 动作量分解", "",
                  "各行动作档位的次数和成交股数见 `action_summary.csv`；每条逐回合动作序列保存在 `followup_raw.csv`。", "",
                  "## 范围说明", "",
                  "这是一项小范围独立验证：仅训练一个 Double Q 种子；TWAP 和动态规则不训练。测试种子与此前主比较、验证集和长训集分开。由于只用一个 Q 训练种子，成本区间不能表示训练随机性。",
                  "历史主实验中的随机 B 结果产生于本次完单修正之前；本报告用修正后的随机 B 规则重新评估选定策略，不回写或伪装成旧实验的复算结果。", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-policy", action="store_true",
                        help="reuse the exact policy artifact already saved in the output directory")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    config = sim.Config()
    random_control = randomized_completion_control()
    if random_control["repaired_incomplete_episodes"] != 0:
        raise RuntimeError("The repaired randomized B policy failed the completion control")
    train_args = SimpleNamespace(
        fee_bps=FEE_BPS,
        training_seed=TRAINING_MASTER_SEED,
        demonstration_episodes=DEMONSTRATION_EPISODES,
        rule_guided_episodes=Q_EPISODES,
    )
    policy_path = OUT / "selected_double_q_policy.json"
    if args.reuse_policy:
        if not policy_path.exists():
            raise FileNotFoundError(f"No saved policy to reuse: {policy_path}")
        print("Loading the previously trained selected Double Q policy ...", flush=True)
        agent = load_policy(policy_path, config)
    else:
        print("Training the selected rule-guided Double Q policy only ...", flush=True)
        agent = comparison.train_rule_guided_candidate(1, train_args, config)
        agent.improvement_margin = FIXED_MARGIN_BPS
        save_policy(agent, policy_path)
    if abs(agent.improvement_margin - FIXED_MARGIN_BPS) > 1e-12:
        raise RuntimeError("Saved policy does not use the pre-selected 5 bp margin")
    agent.freeze()
    before_digest = policy_digest(agent)

    raw: list[dict[str, Any]] = []
    action_totals: dict[tuple[str, str, float], list[float]] = defaultdict(lambda: [0, 0.0])
    agreement_totals: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    b_fills: dict[tuple[str, str, int], float] = {}
    for scenario_idx, (scenario, volatility) in enumerate(SCENARIOS):
        for opponent_idx, opponent in enumerate(sim.TEST_OPPONENTS):
            for eval_idx in range(EVALUATION_SEEDS):
                seed = TEST_MASTER_SEED + scenario_idx * 1_000_000 + opponent_idx * 10_000 + eval_idx * 101
                traces: dict[str, list[dict[str, Any]]] = {}
                cell_b_completion = []
                for policy in POLICIES:
                    q_agent = agent if policy == "rule_guided_double_Q_m5" else None
                    simulator_policy = "G3_opponent_aware_Q" if q_agent is not None else policy
                    result = sim.run_episode(
                        simulator_policy, opponent, FEE_BPS, seed, config, q_agent,
                        scenario_name=scenario, volatility_multiplier=volatility,
                        trace_enabled=True,
                    )
                    traces[policy] = result.trace
                    b_filled = sum(float(row["B_qty"]) for row in result.trace)
                    b_completion = min(1.0, b_filled / config.order_size)
                    cell_b_completion.append(b_completion)
                    b_fills[(policy, opponent, seed)] = b_filled
                    actions = [float(row["A_action_multiple"]) for row in result.trace]
                    for row, action in zip(result.trace, actions):
                        totals = action_totals[(policy, scenario, action)]
                        totals[0] += 1
                        totals[1] += float(row["A_qty"])
                    raw.append({
                        "strategy": policy, "B_opponent": opponent,
                        "scenario": scenario, "seed": seed,
                        "cost_bps": result.cost_bps,
                        "gross_cost_bps": result.gross_cost_bps,
                        "fee_cost_bps": result.fee_cost_bps,
                        "completion_rate": result.completion_rate,
                        "unfilled_shares": result.unfilled_shares,
                        "B_completion_rate": b_completion,
                        "action_counts": json.dumps(dict(result.action_counts), ensure_ascii=False),
                        "action_sequence": json.dumps(actions),
                    })
                if max(cell_b_completion) - min(cell_b_completion) > 1e-12:
                    raise RuntimeError("B randomized path changed across paired A strategies")
                q_actions = [float(row["A_action_multiple"]) for row in traces["rule_guided_double_Q_m5"]]
                rule_actions = [float(row["A_action_multiple"]) for row in traces["G1_dynamic_rule"]]
                matched = sum(q == rule for q, rule in zip(q_actions, rule_actions))
                agree = agreement_totals[(scenario, opponent)]
                agree[0] += matched
                agree[1] += len(rule_actions)
                if abs(sum(cell_b_completion) / len(cell_b_completion) - 1.0) > 1e-12:
                    raise RuntimeError(f"B failed full-fill constraint: {opponent} seed={seed}")
    after_digest = policy_digest(agent)
    table_unchanged = before_digest == after_digest
    if not table_unchanged:
        raise RuntimeError("Frozen test evaluation changed the Q tables or their structure")

    summary = []
    for scenario, _ in SCENARIOS:
        for strategy in POLICIES:
            group = [row for row in raw if row["scenario"] == scenario and row["strategy"] == strategy]
            costs = [float(row["cost_bps"]) for row in group]
            summary.append({
                "scenario": scenario, "strategy": strategy, "episodes": len(group),
                "mean_cost_bps": statistics.fmean(costs),
                "sd_cost_bps": statistics.stdev(costs) if len(costs) > 1 else 0.0,
                "mean_A_completion": statistics.fmean(float(r["completion_rate"]) for r in group),
                "mean_B_completion": statistics.fmean(float(r["B_completion_rate"]) for r in group),
                "mean_unfilled_shares": statistics.fmean(float(r["unfilled_shares"]) for r in group),
            })
    differences = paired_summary(raw)
    actions = []
    for (strategy, scenario, action), (count, volume) in sorted(action_totals.items()):
        total_episodes = EVALUATION_SEEDS * len(sim.TEST_OPPONENTS)
        actions.append({
            "strategy": strategy, "scenario": scenario, "action_multiple": action,
            "step_count": int(count), "step_share": count / (total_episodes * config.horizon),
            "filled_shares": volume, "mean_filled_shares_per_episode": volume / total_episodes,
        })
    agreement = [
        {"scenario": scenario, "B_opponent": opponent,
         "agreement_rate": matched / total, "matched_steps": matched, "total_steps": total}
        for (scenario, opponent), (matched, total) in sorted(agreement_totals.items())
    ]
    b_completion_rows = []
    for scenario, _ in SCENARIOS:
        for opponent in sim.TEST_OPPONENTS:
            values = [float(row["B_completion_rate"]) for row in raw
                      if row["strategy"] == "rule_guided_double_Q_m5"
                      and row["scenario"] == scenario and row["B_opponent"] == opponent]
            b_completion_rows.append({"scenario": scenario, "B_opponent": opponent,
                                      "episodes": len(values),
                                      "mean_B_completion": statistics.fmean(values)})
    gamma_check = {
        "gamma": agent.config.discount,
        "nonterminal_target": agent.td_target(-2.0, -10.0, terminal=False),
        "terminal_target": agent.td_target(-2.0, -10.0, terminal=True),
    }
    if abs(gamma_check["gamma"] - 0.98) > 1e-12 or abs(gamma_check["nonterminal_target"] + 11.8) > 1e-12 or abs(gamma_check["terminal_target"] + 2.0) > 1e-12:
        raise RuntimeError("Double-Q gamma/terminal target check failed")

    write_csv(OUT / "followup_raw.csv", raw)
    write_csv(OUT / "followup_summary.csv", summary)
    write_csv(OUT / "paired_cost_differences.csv", differences)
    write_csv(OUT / "action_summary.csv", actions)
    write_csv(OUT / "action_agreement.csv", agreement)
    write_csv(OUT / "B_completion_summary.csv", b_completion_rows)
    (OUT / "findings.md").write_text(
        build_findings(summary, differences, actions, agreement,
                       b_completion_rows, table_unchanged, gamma_check, random_control),
        encoding="utf-8",
    )
    manifest = {
        "fee_bps": FEE_BPS,
        "training_master_seed": TRAINING_MASTER_SEED,
        "test_master_seed": TEST_MASTER_SEED,
        "training_run_id": 1,
        "training_parameters": {
            "learning_rate": 0.08,
            "epsilon_start": 0.30,
            "epsilon_end": 0.03,
            "inventory_risk_weight_during_learning": 0.0,
            "discount_gamma": agent.config.discount,
        },
        "demonstration_episodes": DEMONSTRATION_EPISODES,
        "q_training_episodes": Q_EPISODES,
        "fixed_improvement_margin_bps": FIXED_MARGIN_BPS,
        "margin_retuned_on_test": False,
        "evaluation_seeds_per_opponent_scenario": EVALUATION_SEEDS,
        "B_opponents": list(sim.TEST_OPPONENTS),
        "scenarios": {name: volatility for name, volatility in SCENARIOS},
        "paired_seed_schedule": "same seed for TWAP, dynamic rule, and Double Q at each B-opponent/scenario/evaluation cell",
        "discount_gamma": agent.config.discount,
        "target_formula": "r + gamma * Q_evaluator(s', argmax_a Q_chosen(s', a)); terminal target=r",
        "randomized_B_completion_constraint": "required_now=max(0,remaining-steps_after*2*base_slice); sampled quantity=max(sampled quantity, required_now)",
        "randomized_B_completion_control": random_control,
        "Q_table_frozen_and_unchanged": table_unchanged,
        "Q_table_digest_before": before_digest,
        "Q_table_digest_after": after_digest,
        "selected_policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "Q_state_count": len(agent.qa),
        "counts": {"raw_rows": len(raw), "paired_cells_per_scenario": EVALUATION_SEEDS * len(sim.TEST_OPPONENTS)},
        "code_sha256": {
            "followup_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "simulator": hashlib.sha256((ROOT / "run_standard_benchmark.py").read_bytes()).hexdigest(),
            "double_q": hashlib.sha256((ROOT / "schedule_aware_q.py").read_bytes()).hexdigest(),
            "comparison_trainer": hashlib.sha256((ROOT / "run_matched_rule_q_comparison.py").read_bytes()).hexdigest(),
        },
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validation complete: {len(raw)} policy episodes; Q table unchanged={table_unchanged}", flush=True)
    print(f"Results: {OUT}", flush=True)


if __name__ == "__main__":
    main()
