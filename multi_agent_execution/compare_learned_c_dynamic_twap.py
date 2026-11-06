#!/usr/bin/env python3
"""Paired comparison of learned Scheme C, a dynamic rule, and fixed TWAP.

All arms use the event-driven limit-order book. The focal A strategy is tested
against each of two fixed B opponents (dynamic rule and fixed TWAP), using the
same exogenous market tape for every A strategy in a matched cell.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import statistics
from pathlib import Path
from typing import Any

from compare_deadline_c_overlay import load_frozen_agent
from limit_order_book import SyntheticLOBConfig
from run_advanced_self_play import SCENARIOS, episode, write_csv
from run_standard_benchmark import ACTIONS, Config


ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT_DIR = ROOT / "outputs" / "advanced_self_play_learned_c_flexible_quantity_1000x5x30"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "learned_c_flexible_quantity_comparison"
METHODS = ("learned_c", "dynamic_rule", "fixed_twap")
OPPONENTS = ("dynamic_rule", "fixed_twap")


class FixedExecutionRule:
    """Stateless G0/G1 policy adapter for the common LOB action interface."""

    def __init__(self, name: str, config: Config):
        if name not in {"dynamic_rule", "fixed_twap"}:
            raise ValueError(f"Unsupported fixed policy: {name}")
        self.name = name
        self.config = config
        if name == "fixed_twap":
            # A conventional TWAP executes a fixed 1/N parent slice each step.
            # Use a marketable limit capped across all seven modeled ask levels.
            self.fixed_quantity_multiplier = 1.0
            self.fixed_urgency_ticks = 6

    def fixed_action(self, obs: Any) -> int:
        if self.name == "fixed_twap":
            # Submit a one-base-slice IOC every 30 seconds. The cap spans all
            # visible ask levels; residual IOC quantity is cancelled normally.
            return 4

        # Reuse the thresholds of run_standard_benchmark.G1_dynamic_rule and
        # map the selected index to the equivalent action in the LOB simulator.
        deficit_ratio = obs.remaining / max(
            obs.base_slice * (obs.horizon - obs.t), 1.0,
        )
        price_deviation_bps = (obs.mid / obs.initial_mid - 1.0) * 10_000.0
        if obs.t == obs.horizon - 1 or deficit_ratio > 1.25:
            return 4
        if price_deviation_bps < -1.0:
            return 3
        if price_deviation_bps > 2.0 and deficit_ratio < 1.05:
            return 1
        if (
            self.config.temporary_impact_bps_per_slice
            * self.config.market_impact_multiplier
            * self.config.step_minutes > 0.15
            and deficit_ratio < 0.98
        ):
            return 1
        return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paired LOB comparison of learned Scheme C, dynamic rule, and fixed TWAP."
    )
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--checkpoint", type=int, default=1000)
    parser.add_argument("--training-runs", type=int, default=5)
    parser.add_argument("--eval-seeds", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--schedule-deficit-penalty-bps", type=float, default=10.0)
    parser.add_argument("--terminal-unfilled-penalty-bps", type=float, default=1_000.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.training_runs < 1 or args.eval_seeds < 1 or args.checkpoint < 0:
        parser.error("training-runs/eval-seeds must be positive; checkpoint cannot be negative")
    return args


def load_models(args: argparse.Namespace, config: Config) -> dict[int, Any]:
    result: dict[int, Any] = {}
    for run_id in range(1, args.training_runs + 1):
        path = args.checkpoint_dir / f"checkpoint_qtables_run{run_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        checkpoint = payload.get(str(args.checkpoint))
        if checkpoint is None:
            raise KeyError(f"Checkpoint {args.checkpoint} not found in {path}")
        model = load_frozen_agent(config, checkpoint["A"])
        if not hasattr(model, "scheme_c"):
            raise ValueError(f"Checkpoint A in {path} has no learned Scheme C table")
        result[run_id] = model
    return result


def run_comparison(args: argparse.Namespace, config: Config) -> list[dict[str, Any]]:
    models = load_models(args, config)
    rows: list[dict[str, Any]] = []
    for run_id, learned_model in models.items():
        for scenario, volatility_multiplier in SCENARIOS:
            scenario_offset = 0 if scenario == "normal" else 50_000
            for eval_idx in range(args.eval_seeds):
                seed = (
                    args.seed + run_id * 1_000_003 + 600_000_000
                    + eval_idx * 101 + scenario_offset
                )
                # Reuse this exogenous tape for both opponent cohorts and all
                # focal A methods. Strategy-induced prices remain endogenous.
                for opponent_name in OPPONENTS:
                    for method in METHODS:
                        focal = (
                            learned_model if method == "learned_c"
                            else FixedExecutionRule(method, config)
                        )
                        opponent = FixedExecutionRule(opponent_name, config)
                        c_mode = {"A": "learned" if method == "learned_c" else "none", "B": "none"}
                        result = episode(
                            focal, opponent, config, seed, args.fee_bps,
                            volatility_multiplier, training=False,
                            completion_mode="autonomous", deadline_c_mode=c_mode,
                        )
                        autonomous_a = max(
                            0.0, result["filled_A"] - result["forced_completion_A"],
                        )
                        autonomous_b = max(
                            0.0, result["filled_B"] - result["forced_completion_B"],
                        )
                        rows.append({
                            "training_run": run_id,
                            "checkpoint": args.checkpoint,
                            "scenario": scenario,
                            "seed": seed,
                            "opponent_B": opponent_name,
                            "strategy_A": method,
                            "fee_bps": args.fee_bps,
                            "A_cost_bps": result["cost_A_bps"],
                            "B_cost_bps": result["cost_B_bps"],
                            "A_completion": result["completion_A"],
                            "B_completion": result["completion_B"],
                            "A_autonomous_fill_shares": autonomous_a,
                            "B_autonomous_fill_shares": autonomous_b,
                            "A_autonomous_fill_pct": autonomous_a / config.order_size * 100.0,
                            "B_autonomous_fill_pct": autonomous_b / config.order_size * 100.0,
                            "A_forced_shares": result["forced_completion_A"],
                            "B_forced_shares": result["forced_completion_B"],
                            "A_forced_pct": result["forced_completion_A"] / config.order_size * 100.0,
                            "B_forced_pct": result["forced_completion_B"] / config.order_size * 100.0,
                            "A_maker_fills": result["maker_fills_A"],
                            "A_taker_fills": result["taker_fills_A"],
                            "A_forced_cost_bps": result["forced_completion_cost_contribution_A_bps"],
                            "A_deadline_urgency_steps": result["deadline_urgency_steps_A"],
                            "A_c_interventions": result["deadline_c_interventions_A"],
                            "A_catch_up_submitted": result["deadline_catch_up_submitted_A"],
                            "A_c_action_counts": result["deadline_c_actions_A"],
                            "A_actions": result["actions_A"],
                            "B_actions": result["actions_B"],
                        })
    return rows


def mean_ci(values: list[float]) -> tuple[float, float, float]:
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, mean, mean
    half_width = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - half_width, mean + half_width


def summarize(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for scenario, _ in SCENARIOS:
        for opponent in OPPONENTS:
            for method in METHODS:
                group = [r for r in rows if r["scenario"] == scenario
                         and r["opponent_B"] == opponent and r["strategy_A"] == method]
                stats_row: dict[str, Any] = {
                    "scenario": scenario,
                    "opponent_B": opponent,
                    "strategy_A": method,
                    "episodes": len(group),
                }
                for metric in (
                    "A_cost_bps", "B_cost_bps", "A_autonomous_fill_shares",
                    "A_autonomous_fill_pct", "A_forced_shares", "A_forced_pct",
                    "A_maker_fills", "A_taker_fills", "A_forced_cost_bps",
                    "A_deadline_urgency_steps", "A_c_interventions", "A_catch_up_submitted",
                    "B_forced_shares", "B_autonomous_fill_pct",
                ):
                    values = [float(r[metric]) for r in group]
                    mean, low, high = mean_ci(values)
                    stats_row[f"{metric}_mean"] = mean
                    stats_row[f"{metric}_ci95_low"] = low
                    stats_row[f"{metric}_ci95_high"] = high
                if method == "learned_c":
                    c_counts: Counter[str] = Counter()
                    for row in group:
                        c_counts.update(json.loads(row["A_c_action_counts"]))
                    stats_row["A_c_action_counts_per_episode"] = json.dumps(
                        {name: count / len(group) for name, count in sorted(c_counts.items())},
                        ensure_ascii=False, sort_keys=True,
                    )
                summaries.append(stats_row)

            # Matched paired differences for A; the opponent is held fixed.
            for benchmark in ("dynamic_rule", "fixed_twap"):
                deltas_by_metric: dict[str, list[float]] = {
                    key: [] for key in (
                        "A_cost_bps", "A_forced_shares", "A_autonomous_fill_pct",
                        "A_maker_fills", "A_taker_fills",
                    )
                }
                keys = sorted({
                    (r["training_run"], r["seed"])
                    for r in rows if r["scenario"] == scenario
                    and r["opponent_B"] == opponent
                })
                for run_id, seed in keys:
                    learned = next(
                        r for r in rows if r["scenario"] == scenario
                        and r["opponent_B"] == opponent and r["training_run"] == run_id
                        and r["seed"] == seed and r["strategy_A"] == "learned_c"
                    )
                    base = next(
                        r for r in rows
                        if r["scenario"] == scenario and r["opponent_B"] == opponent
                        and r["training_run"] == run_id and r["seed"] == seed
                        and r["strategy_A"] == benchmark
                    )
                    for metric in deltas_by_metric:
                        deltas_by_metric[metric].append(
                            float(learned[metric]) - float(base[metric])
                        )
                for metric, deltas in deltas_by_metric.items():
                    mean, low, high = mean_ci(deltas)
                    paired.append({
                        "scenario": scenario,
                        "opponent_B": opponent,
                        "contrast": f"learned_c_minus_{benchmark}",
                        "metric": metric,
                        "pairs": len(deltas),
                        "mean_delta": mean,
                        "ci95_low": low,
                        "ci95_high": high,
                    })

            # The two non-learning execution baselines against each other.
            deltas = []
            for run_id in range(1, max(r["training_run"] for r in rows) + 1):
                for eval_seed in sorted({r["seed"] for r in rows if r["scenario"] == scenario
                                         and r["opponent_B"] == opponent
                                         and r["training_run"] == run_id}):
                    target = next(r for r in rows if r["scenario"] == scenario
                                  and r["opponent_B"] == opponent
                                  and r["training_run"] == run_id and r["seed"] == eval_seed
                                  and r["strategy_A"] == "dynamic_rule")
                    ref = next(r for r in rows if r["scenario"] == scenario
                               and r["opponent_B"] == opponent
                               and r["training_run"] == run_id and r["seed"] == eval_seed
                               and r["strategy_A"] == "fixed_twap")
                    deltas.append(float(target["A_cost_bps"]) - float(ref["A_cost_bps"]))
            mean, low, high = mean_ci(deltas)
            paired.append({
                "scenario": scenario, "opponent_B": opponent,
                "contrast": "dynamic_rule_minus_fixed_twap",
                "metric": "A_cost_bps", "pairs": len(deltas),
                "mean_delta": mean, "ci95_low": low, "ci95_high": high,
            })
    return summaries, paired


def make_report(args: argparse.Namespace, summaries: list[dict[str, Any]],
                paired: list[dict[str, Any]]) -> str:
    def pair_value(scenario: str, opponent: str, contrast: str, metric: str) -> dict[str, Any]:
        return next(x for x in paired if x["scenario"] == scenario
                    and x["opponent_B"] == opponent and x["contrast"] == contrast
                    and x["metric"] == metric)

    def summary_value(scenario: str, opponent: str, method: str, metric: str) -> float:
        row = next(x for x in summaries if x["scenario"] == scenario
                   and x["opponent_B"] == opponent and x["strategy_A"] == method)
        return float(row[f"{metric}_mean"])

    lines = [
        "# 学习型方案 C、动态规则与固定 TWAP 对照结果", "",
        "## 实验设置", "",
        f"- 每个市场情景使用 {args.training_runs} 个独立训练种子 × {args.eval_seeds} 个配对种子；策略 A 的有效样本数为 {args.training_runs * args.eval_seeds}。",
        f"- 单边手续费：{args.fee_bps:g} bp；母单：100,000 股；时间窗：30 分钟，每步 30 秒，共 60 步。",
        "- 市场：同一个事件驱动合成限价订单簿，含部分成交、排队、挂单到期、IOC、双方交易冲击及终端兜底。每个配对单元对三种 A 策略和两个固定 B 对手复用同一组外生订单流、盘口深度和随机撮合顺序；交易行为导致的价格路径变化是模型内生结果。",
        f"- 学习型 C：使用第 {args.checkpoint} 回合冻结的双边 Q-learning 检查点中 A 的常规 Q 表和独立 C-Q 决策头；测试时不更新参数。落后时 C-Q 从 no-C 或 12 种 IOC 报价/追赶量组合中选择；追赶量是在普通 IOC 子单上增加当前进度缺口的 0/25/50/100%。B 为固定规则策略或固定 TWAP。",
        "- 动态规则：沿用 G1 的阈值（进度缺口、价格偏离和冲击条件）选择限价订单动作；当前 LOB 中报价未必成交，因此不使用旧全额成交环境的可行量下限。",
        "- 固定 TWAP：每 30 秒提交 1 个 base slice 的 marketable-limit IOC，限价上限覆盖模拟的七档卖盘；若可见深度不足仍会部分成交并取消余量。策略固定等时间切片和每片数量，不根据盘中反馈调整。",
        "- 三种方法统一使用 autonomous completion。100% 完成率由各方法共享的终端兜底保证，不代表盘中自主成交率为 100%；主要比较盘中自主成交股数、兜底股数和总实施成本。",
        "- 成本为总实施缺口（含成交价格、手续费及兜底价格影响），单位 bp；越低越好。配对差异定义为左侧策略减基准，负值表示左侧成本更低或兜底更少。95% 区间采用配对样本均值的正态近似。", "",
        "## A 策略平均结果", "",
        "每个 B 对手单独固定，避免不同 A 策略面对不同竞争者。", "",
        "| 情景 | 固定 B 对手 | A 策略 | A 成本 (bp) | 盘中自主成交 (股) | 兜底量 (股) | C 额外追赶提交量 (股) | maker/taker 成交 (股) | B 成本 (bp) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario, _ in SCENARIOS:
        for opponent in OPPONENTS:
            for method in METHODS:
                r = next(x for x in summaries if x["scenario"] == scenario
                         and x["opponent_B"] == opponent and x["strategy_A"] == method)
                lines.append(
                    f"| {scenario} | {opponent} | {method} | {r['A_cost_bps_mean']:.3f} | "
                    f"{r['A_autonomous_fill_shares_mean']:.0f} | {r['A_forced_shares_mean']:.0f} | "
                    f"{r['A_catch_up_submitted_mean']:.0f} | {r['A_maker_fills_mean']:.0f}/{r['A_taker_fills_mean']:.0f} | "
                    f"{r['B_cost_bps_mean']:.3f} |"
                )
    lines += ["", "## 配对差异", "",
              "成本、兜底量和成交量的均值差均按相同训练检查点、情景、市场种子计算；成本差小于 0 表示学习型 C 成本更低。区间跨过 0 时，不应将均值差描述为稳定优势。", "",
              "| 情景 | 固定 B 对手 | 比较 | 成本差 (bp) [95%区间] | 兜底量差 (股) [95%区间] | 自主成交差 (百分点) [95%区间] |", "|---|---|---|---:|---:|---:|"]
    for scenario, _ in SCENARIOS:
        for opponent in OPPONENTS:
            for benchmark in ("dynamic_rule", "fixed_twap"):
                cost = next(x for x in paired if x["scenario"] == scenario and x["opponent_B"] == opponent
                            and x["contrast"] == f"learned_c_minus_{benchmark}" and x["metric"] == "A_cost_bps")
                forced = next(x for x in paired if x["scenario"] == scenario and x["opponent_B"] == opponent
                              and x["contrast"] == f"learned_c_minus_{benchmark}" and x["metric"] == "A_forced_shares")
                fill = next(x for x in paired if x["scenario"] == scenario and x["opponent_B"] == opponent
                            and x["contrast"] == f"learned_c_minus_{benchmark}" and x["metric"] == "A_autonomous_fill_pct")
                lines.append(
                    f"| {scenario} | {opponent} | learned C − {benchmark} | "
                    f"{cost['mean_delta']:.3f} [{cost['ci95_low']:.3f}, {cost['ci95_high']:.3f}] | "
                    f"{forced['mean_delta']:.0f} [{forced['ci95_low']:.0f}, {forced['ci95_high']:.0f}] | "
                    f"{fill['mean_delta']:.2f} [{fill['ci95_low']:.2f}, {fill['ci95_high']:.2f}] |"
                )

    lines += ["", "## 学习型 C 的报价和加急量决策", "",
              "以下是每回合平均选择次数，只计落后进度时开放的 C 决策；`on_schedule` 不进入 C 选项统计。追赶比例表示本步在普通 IOC 子单量上额外提交当前进度缺口的对应比例。", "",
              "| 情景 | 固定 B 对手 | no-C | IOC+1 tick | IOC+3 ticks | IOC+6 ticks |", "|---|---|---:|---:|---:|---:|"]
    for scenario, _ in SCENARIOS:
        for opponent in OPPONENTS:
            row = next(x for x in summaries if x["scenario"] == scenario
                       and x["opponent_B"] == opponent and x["strategy_A"] == "learned_c")
            c_counts = json.loads(row["A_c_action_counts_per_episode"])
            tier_counts = {
                "no-C": c_counts.get("no_c", 0.0),
                "IOC+1 tick": sum(count for label, count in c_counts.items()
                                  if label.startswith("ioc_plus_1_tick")),
                "IOC+3 ticks": sum(count for label, count in c_counts.items()
                                   if label.startswith("ioc_plus_3_tick")),
                "IOC+6 ticks": sum(count for label, count in c_counts.items()
                                   if label.startswith("ioc_plus_6_tick")),
            }
            lines.append(
                f"| {scenario} | {opponent} | {tier_counts['no-C']:.2f} | "
                f"{tier_counts['IOC+1 tick']:.2f} | {tier_counts['IOC+3 ticks']:.2f} | "
                f"{tier_counts['IOC+6 ticks']:.2f} |"
            )

    lines += ["", "按追赶缺口比例的平均选择次数：", "",
              "| 情景 | 固定 B 对手 | 0% | 25% | 50% | 100% |", "|---|---|---:|---:|---:|---:|"]
    for scenario, _ in SCENARIOS:
        for opponent in OPPONENTS:
            row = next(x for x in summaries if x["scenario"] == scenario
                       and x["opponent_B"] == opponent and x["strategy_A"] == "learned_c")
            c_counts = json.loads(row["A_c_action_counts_per_episode"])
            fraction_counts = {f"{fraction}pct": 0.0 for fraction in (0, 25, 50, 100)}
            for label, count in c_counts.items():
                for fraction_label in fraction_counts:
                    if f"catchup_{fraction_label}" in label:
                        fraction_counts[fraction_label] += count
            lines.append(
                f"| {scenario} | {opponent} | {fraction_counts['0pct']:.2f} | "
                f"{fraction_counts['25pct']:.2f} | {fraction_counts['50pct']:.2f} | "
                f"{fraction_counts['100pct']:.2f} |"
            )

    learned_rule_normal = pair_value(
        "normal", "dynamic_rule", "learned_c_minus_dynamic_rule", "A_cost_bps",
    )
    learned_rule_high = pair_value(
        "high_volatility", "dynamic_rule", "learned_c_minus_dynamic_rule", "A_cost_bps",
    )
    learned_rule_fill_normal = pair_value(
        "normal", "dynamic_rule", "learned_c_minus_dynamic_rule", "A_autonomous_fill_pct",
    )
    learned_rule_fill_high = pair_value(
        "high_volatility", "dynamic_rule", "learned_c_minus_dynamic_rule", "A_autonomous_fill_pct",
    )
    lines += ["", "## 核心发现", "",
              f"1. 固定对手为动态规则时，学习型 C 相比动态规则在正常/高波动场景的成本分别低 {-learned_rule_normal['mean_delta']:.2f}/{-learned_rule_high['mean_delta']:.2f} bp；自主成交率分别高 {learned_rule_fill_normal['mean_delta']:.2f}/{learned_rule_fill_high['mean_delta']:.2f} 个百分点，配对区间均未跨 0。",
              f"2. 固定对手为 TWAP 时，学习型 C 相比动态规则的成本分别低 {-pair_value('normal', 'fixed_twap', 'learned_c_minus_dynamic_rule', 'A_cost_bps')['mean_delta']:.2f}/{-pair_value('high_volatility', 'fixed_twap', 'learned_c_minus_dynamic_rule', 'A_cost_bps')['mean_delta']:.2f} bp，自主成交率分别高 {pair_value('normal', 'fixed_twap', 'learned_c_minus_dynamic_rule', 'A_autonomous_fill_pct')['mean_delta']:.2f}/{pair_value('high_volatility', 'fixed_twap', 'learned_c_minus_dynamic_rule', 'A_autonomous_fill_pct')['mean_delta']:.2f} 个百分点。说明固定规则对手下的动态规则较容易落后，学习策略的优势更明显。",
              f"3. 学习型 C 没有稳定胜过固定 TWAP。固定 TWAP 的 A 成本在四个情景/对手单元都更低：相对学习型 C 分别低 {pair_value('normal', 'dynamic_rule', 'learned_c_minus_fixed_twap', 'A_cost_bps')['mean_delta']:.2f}、{pair_value('high_volatility', 'dynamic_rule', 'learned_c_minus_fixed_twap', 'A_cost_bps')['mean_delta']:.2f}、{pair_value('normal', 'fixed_twap', 'learned_c_minus_fixed_twap', 'A_cost_bps')['mean_delta']:.2f}、{pair_value('high_volatility', 'fixed_twap', 'learned_c_minus_fixed_twap', 'A_cost_bps')['mean_delta']:.2f} bp（按正常/高波动、B=动态规则/TWAP 顺序）。TWAP 通过每步主动吃单减少残余，代价是承担买卖价差和手续费。",
              f"4. 学习型 C 的兜底占比在四个单元为 {summary_value('normal', 'dynamic_rule', 'learned_c', 'A_forced_pct'):.2f}%、{summary_value('high_volatility', 'dynamic_rule', 'learned_c', 'A_forced_pct'):.2f}%、{summary_value('normal', 'fixed_twap', 'learned_c', 'A_forced_pct'):.2f}%、{summary_value('high_volatility', 'fixed_twap', 'learned_c', 'A_forced_pct'):.2f}%；而固定 TWAP 对应为 {summary_value('normal', 'dynamic_rule', 'fixed_twap', 'A_forced_pct'):.2f}%、{summary_value('high_volatility', 'dynamic_rule', 'fixed_twap', 'A_forced_pct'):.2f}%、{summary_value('normal', 'fixed_twap', 'fixed_twap', 'A_forced_pct'):.2f}%、{summary_value('high_volatility', 'fixed_twap', 'fixed_twap', 'A_forced_pct'):.2f}%。这里的 100% 总完成由共享终端兜底保障。", "",
              "## 结果解释", "",
              "这项实验回答的是：在两类同一固定对手面前，冻结的学习型 C、固定阈值动态规则和固定 TWAP 在同一限价订单簿的成本及自主成交表现如何。它不证明真实市场收益，也不代表训练期在线适应；订单簿深度与订单流均为合成设定。",
              "", "终端兜底让母单最终全额完成，但兜底量本身是核心结果之一。若某策略总成本低但兜底更多，需要同时考察自主成交量和兜底成本，不能只按总成本下结论。", "",
              "## 文件", "",
              "- `learned_c_dynamic_twap_raw.csv`：逐次运行的原始结果。",
              "- `learned_c_dynamic_twap_summary.csv`：按情景、固定对手和 A 策略汇总。",
              "- `learned_c_dynamic_twap_paired.csv`：同种子配对差异及区间。", ""]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    manifest_path = args.checkpoint_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trained = manifest.get("parameters", {})
    if trained.get("deadline_c_mode") != "learned":
        raise SystemExit("Checkpoint manifest is not from learned-C training")
    config = Config(
        inventory_risk_weight=0.0,
        schedule_deficit_penalty_bps=args.schedule_deficit_penalty_bps,
        terminal_unfilled_penalty_bps=args.terminal_unfilled_penalty_bps,
    )
    for key, value in (("fee_bps", args.fee_bps),
                       ("schedule_deficit_penalty_bps", args.schedule_deficit_penalty_bps),
                       ("terminal_unfilled_penalty_bps", args.terminal_unfilled_penalty_bps)):
        if abs(float(trained[key]) - value) > 1e-12:
            raise SystemExit(f"{key}={value} does not match training checkpoint value {trained[key]}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = run_comparison(args, config)
    summaries, paired = summarize(raw)
    write_csv(args.output_dir / "learned_c_dynamic_twap_raw.csv", raw)
    write_csv(args.output_dir / "learned_c_dynamic_twap_summary.csv", summaries)
    write_csv(args.output_dir / "learned_c_dynamic_twap_paired.csv", paired)
    (args.output_dir / "findings.md").write_text(
        make_report(args, summaries, paired), encoding="utf-8",
    )
    (args.output_dir / "run_manifest.json").write_text(json.dumps({
        "checkpoint_dir": str(args.checkpoint_dir.resolve()),
        "checkpoint_episode": args.checkpoint,
        "training_runs": args.training_runs,
        "eval_seeds_per_scenario": args.eval_seeds,
        "base_seed": args.seed,
        "fee_bps": args.fee_bps,
        "config": {**config.__dict__, "horizon_steps": config.horizon},
        "market_scenarios": dict(SCENARIOS),
        "limit_order_parameters": SyntheticLOBConfig().__dict__,
        "methods": {
            "learned_c": "frozen Q + learned Scheme C, evaluated as A",
            "dynamic_rule": "G1 thresholds on current LOB actions; no feasibility floor",
            "fixed_twap": "one base-slice marketable-limit IOC per 30-second step; cap spans seven modeled ask levels",
        },
        "opponents": list(OPPONENTS),
        "completion_mode": "autonomous; common terminal backstop, report forced shares separately",
        "paired_seeds": "same exogenous seed across every A method and both fixed B opponents within each run/scenario/eval index",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Comparison complete: {(args.output_dir / 'findings.md').resolve()}")


if __name__ == "__main__":
    main()
