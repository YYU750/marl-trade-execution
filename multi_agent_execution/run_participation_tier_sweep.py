#!/usr/bin/env python3
"""Run matched low/medium/high A+B participation scenarios and compare outputs."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TIERS = ("low", "medium", "high")
SCENARIOS = ("normal", "high_volatility")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and evaluate the same two-agent model in 5%, 25%, and 60% planned participation tiers."
    )
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--training-runs", type=int, default=5)
    parser.add_argument("--eval-seeds", type=int, default=30)
    parser.add_argument("--checkpoint-interval", type=int, default=100)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--deadline-c-mode", choices=("none", "stochastic", "learned"), default="learned")
    parser.add_argument("--completion-mode", choices=("autonomous", "none"), default="autonomous")
    parser.add_argument("--seed", type=int, default=20261111)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--aggregate-only", action="store_true",
                        help="reuse existing low/medium/high outputs and only rebuild comparison files")
    args = parser.parse_args()
    if args.output_dir is None:
        suffix = {
            "learned": "primary_learned_c",
            "stochastic": "stochastic_c",
            "none": "no_c",
        }[args.deadline_c_mode]
        args.output_dir = ROOT / "outputs" / f"participation_tier_sweep_{suffix}"
    if min(args.episodes, args.training_runs, args.eval_seeds, args.checkpoint_interval) < 1:
        parser.error("episodes, training-runs, eval-seeds, and checkpoint-interval must be positive")
    return args


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in (None, "") else float("nan")


def mean(values: list[float]) -> float:
    finite = [value for value in values if value == value]
    return statistics.fmean(finite) if finite else float("nan")


def sample_sd(values: list[float]) -> float:
    finite = [value for value in values if value == value]
    return statistics.stdev(finite) if len(finite) > 1 else 0.0


def write_outputs(args: argparse.Namespace) -> None:
    records: list[dict[str, Any]] = []
    for tier in TIERS:
        tier_dir = args.output_dir / tier
        summary_rows = read_csv(tier_dir / "cross_play_summary.csv")
        manifest_path = tier_dir / "run_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing completed run manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        params = manifest["parameters"]
        method = manifest["method"]
        final_episode = max(int(row["A_checkpoint"]) for row in summary_rows)
        for scenario in SCENARIOS:
            group = [row for row in summary_rows
                     if int(row["A_checkpoint"]) == final_episode
                     and int(row["B_checkpoint"]) == final_episode
                     and row["scenario"] == scenario]
            if not group:
                raise RuntimeError(f"No final-checkpoint summary for {tier}/{scenario}")
            records.append({
                "participation_tier": tier,
                "episodes": final_episode,
                "evaluation_seeds": int(group[0]["evaluation_seeds"]),
                "target_participation": as_float(group[0], "target_market_participation_AB"),
                "volatility_scenario": scenario,
                "training_runs": len(group),
                "deadline_c_mode": params["deadline_c_mode"],
                "completion_mode": method["completion_mode"],
                "fee_bps": params["fee_bps"],
                "seed": params["seed"],
                "realized_participation_ordinary_mean": mean([
                    as_float(row, "realized_market_participation_AB_mean") for row in group
                ]),
                "realized_participation_ordinary_sd_across_training_runs": sample_sd([
                    as_float(row, "realized_market_participation_AB_mean") for row in group
                ]),
                "realized_participation_including_backstop_mean": mean([
                    as_float(row, "realized_market_participation_AB_including_backstop_mean") for row in group
                ]),
                "background_volume_shares_mean": mean([
                    as_float(row, "realized_background_market_volume_mean") for row in group
                ]),
                "ordinary_ab_fills_shares_mean": mean([
                    as_float(row, "ordinary_market_fills_AB_mean") for row in group
                ]),
                "A_cost_bps_mean": mean([as_float(row, "A_cost_mean_bps") for row in group]),
                "A_cost_bps_sd_across_training_runs": sample_sd([as_float(row, "A_cost_mean_bps") for row in group]),
                "B_cost_bps_mean": mean([as_float(row, "B_cost_mean_bps") for row in group]),
                "B_cost_bps_sd_across_training_runs": sample_sd([as_float(row, "B_cost_mean_bps") for row in group]),
                "A_completion_mean": mean([as_float(row, "A_completion_mean") for row in group]),
                "B_completion_mean": mean([as_float(row, "B_completion_mean") for row in group]),
                "A_forced_shares_mean": mean([as_float(row, "A_forced_completion_mean") for row in group]),
                "B_forced_shares_mean": mean([as_float(row, "B_forced_completion_mean") for row in group]),
                "A_forced_shares_sd_across_training_runs": sample_sd([as_float(row, "A_forced_completion_mean") for row in group]),
                "B_forced_shares_sd_across_training_runs": sample_sd([as_float(row, "B_forced_completion_mean") for row in group]),
            })

    fields = list(records[0]) if records else []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "tier_comparison.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    lines = [
        f"# A+B 市场参与率三档配对比较（C模式：{records[0]['deadline_c_mode']}）", "",
        f"- 每档：{records[0]['training_runs']} 个独立训练种子 × {records[0]['episodes']} 回合；每个评估单元 {records[0]['evaluation_seeds']} 个配对种子。",
        f"- C 决策模式：{records[0]['deadline_c_mode']}；完单模式：{records[0]['completion_mode']}；单边手续费：{records[0]['fee_bps']:g} bp；随机种子基准：{records[0]['seed']}。",
        "- 每档分别训练策略；结果是同一模拟假设下的档位敏感性比较，不是对真实市场参与率的实证估计。",
        "- 实现参与率主口径排除合成终端兜底；含兜底口径仅作补充。成本单位为 bp，越低越好；兜底量越低表示 Agent 普通盘中撮合完成得越多。",
        "- 背景成交量是外生模拟代理，并未逐笔生成第三方订单。autonomous 完单下，含兜底比例会因总成交量接近计划母单而按构造接近目标参与率，不是独立实验发现。", "",
        "| 目标档 | 波动 | 目标参与率 | 普通成交参与率均值±训练种子SD | 含兜底比例 | 背景量代理均值 (股) | A+B 普通成交均值 (股) | A成本均值±SD (bp) | B成本均值±SD (bp) | A兜底均值 (股) | B兜底均值 (股) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in records:
        lines.append(
            f"| {row['participation_tier']} | {row['volatility_scenario']} | "
            f"{row['target_participation']:.0%} | "
            f"{row['realized_participation_ordinary_mean']:.2%} ± {row['realized_participation_ordinary_sd_across_training_runs']:.2%} | "
            f"{row['realized_participation_including_backstop_mean']:.2%} | "
            f"{row['background_volume_shares_mean']:,.0f} | "
            f"{row['ordinary_ab_fills_shares_mean']:,.0f} | "
            f"{row['A_cost_bps_mean']:.3f} ± {row['A_cost_bps_sd_across_training_runs']:.3f} | "
            f"{row['B_cost_bps_mean']:.3f} ± {row['B_cost_bps_sd_across_training_runs']:.3f} | "
            f"{row['A_forced_shares_mean']:,.0f} | {row['B_forced_shares_mean']:,.0f} |"
        )
    lines += [
        "", "## 解读边界", "",
        "低参与档代表背景成交量较大，合成卖方流和显示深度同步扩大，冲击系数降低；高参与档反之。普通成交参与率低于计划档位，通常意味着 Agent 盘中普通撮合未完成全部计划量；如启用 autonomous，差额由单列的终端合成兜底完成。",
        "各档使用相同种子生成相同的外生价格冲击和标准化随机创新，但市场活动强度按档位变化。由于 A、B 的成交会内生改变价格路径，最终价格不要求相同。",
        "背景成交量、盘口活动缩放、平方根冲击缩放和波动过程均为合成假设；正式报告应在取得真实 30 分钟成交量数据后校准，并继续做参数敏感性分析。", "",
    ]
    (args.output_dir / "tier_comparison.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.aggregate_only:
        script = ROOT / "run_advanced_self_play.py"
        for tier in TIERS:
            tier_dir = args.output_dir / tier
            command = [
                sys.executable, str(script),
                "--participation-tier", tier,
                "--episodes", str(args.episodes),
                "--training-runs", str(args.training_runs),
                "--eval-seeds", str(args.eval_seeds),
                "--checkpoint-interval", str(args.checkpoint_interval),
                "--fee-bps", str(args.fee_bps),
                "--deadline-c-mode", args.deadline_c_mode,
                "--completion-mode", args.completion_mode,
                "--seed", str(args.seed),
                "--output-dir", str(tier_dir),
            ]
            print(f"\n=== Participation tier: {tier} ===", flush=True)
            subprocess.run(command, cwd=ROOT, check=True)
    write_outputs(args)
    print(f"\nTier comparison written to {args.output_dir.resolve()}", flush=True)


if __name__ == "__main__":
    main()
