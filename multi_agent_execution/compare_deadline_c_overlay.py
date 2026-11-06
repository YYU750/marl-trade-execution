"""Paired evaluation of the historical Scheme C deadline overlay.

The Q-learning checkpoints are trained without C. This script freezes the
same final A/B checkpoints and compares pure policy execution with the
evaluation-only C urgency overlay on identical market seeds.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from limit_order_book import SyntheticLOBConfig
from run_advanced_self_play import SCENARIOS, episode, write_csv
from run_standard_benchmark import Config
from schedule_aware_q import LimitOrderAwareQLearningAgent


ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT_DIR = ROOT / "outputs" / "advanced_self_play_autonomous_completion"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "c_overlay_comparison_current_model"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare the current frozen Q policies with and without the historical C deadline overlay."
    )
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--checkpoint", type=int, default=500)
    parser.add_argument("--training-runs", type=int, default=5)
    parser.add_argument("--eval-seeds", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--fee-bps", type=float, default=30.0)
    parser.add_argument("--schedule-deficit-penalty-bps", type=float, default=10.0)
    parser.add_argument("--terminal-unfilled-penalty-bps", type=float, default=1_000.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.training_runs < 1 or args.eval_seeds < 1 or args.checkpoint < 0:
        parser.error("training-runs and eval-seeds must be positive; checkpoint cannot be negative")
    if min(args.fee_bps, args.schedule_deficit_penalty_bps,
           args.terminal_unfilled_penalty_bps) < 0:
        parser.error("fee and penalty coefficients cannot be negative")
    return args


def load_frozen_agent(config: Config, payload: dict[str, Any]) -> LimitOrderAwareQLearningAgent:
    if payload.get("state_encoding") != LimitOrderAwareQLearningAgent.state_encoding:
        raise ValueError(
            "Checkpoint state encoding does not match the current limit-order Q agent: "
            f"{payload.get('state_encoding')!r}"
        )
    agent = LimitOrderAwareQLearningAgent(config, opponent_aware=True)
    agent.q = {
        tuple(int(value) for value in state.split("|")): [float(q) for q in values]
        for state, values in payload["q"].items()
    }
    agent.action_visits = {
        tuple(int(value) for value in state.split("|")): [int(count) for count in counts]
        for state, counts in payload["action_visits"].items()
    }
    agent.freeze()
    return agent


def load_checkpoints(args: argparse.Namespace, config: Config) -> dict[int, dict[str, LimitOrderAwareQLearningAgent]]:
    result: dict[int, dict[str, LimitOrderAwareQLearningAgent]] = {}
    for run_id in range(1, args.training_runs + 1):
        path = args.checkpoint_dir / f"checkpoint_qtables_run{run_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Checkpoint file not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        checkpoint = payload.get(str(args.checkpoint))
        if checkpoint is None:
            raise KeyError(f"Checkpoint {args.checkpoint} is absent from {path}")
        result[run_id] = {
            side: load_frozen_agent(config, checkpoint[side]) for side in ("A", "B")
        }
    return result


def run_comparison(args: argparse.Namespace, config: Config) -> list[dict[str, Any]]:
    checkpoints = load_checkpoints(args, config)
    rows: list[dict[str, Any]] = []
    for run_id, agents in checkpoints.items():
        for scenario, volatility_multiplier in SCENARIOS:
            for eval_idx in range(args.eval_seeds):
                seed = (args.seed + run_id * 1_000_003 + 500_000_000
                        + eval_idx * 101 + (0 if scenario == "normal" else 50_000))
                for overlay, enabled in (("agent_only", False), ("scheme_c", True)):
                    result = episode(
                        agents["A"], agents["B"], config, seed, args.fee_bps,
                        volatility_multiplier, training=False,
                        completion_mode="autonomous", deadline_c_overlay=enabled,
                    )
                    rows.append({
                        "training_run": run_id,
                        "checkpoint": args.checkpoint,
                        "scenario": scenario,
                        "evaluation_seed": seed,
                        "execution_overlay": overlay,
                        "A_cost_bps": result["cost_A_bps"],
                        "B_cost_bps": result["cost_B_bps"],
                        "A_completion": result["completion_A"],
                        "B_completion": result["completion_B"],
                        "A_autonomous_fills": result["filled_A"] - result["forced_completion_A"],
                        "B_autonomous_fills": result["filled_B"] - result["forced_completion_B"],
                        "A_forced_completion": result["forced_completion_A"],
                        "B_forced_completion": result["forced_completion_B"],
                        "A_forced_cost_bps": result["forced_completion_cost_contribution_A_bps"],
                        "B_forced_cost_bps": result["forced_completion_cost_contribution_B_bps"],
                        "A_deadline_urgency_steps": result["deadline_urgency_steps_A"],
                        "B_deadline_urgency_steps": result["deadline_urgency_steps_B"],
                        "A_deadline_action_overrides": result["deadline_action_overrides_A"],
                        "B_deadline_action_overrides": result["deadline_action_overrides_B"],
                        "A_schedule_penalty_bps": result["schedule_deficit_penalty_A_bps"],
                        "B_schedule_penalty_bps": result["schedule_deficit_penalty_B_bps"],
                        "A_terminal_penalty_bps": result["terminal_residual_penalty_A_bps"],
                        "B_terminal_penalty_bps": result["terminal_residual_penalty_B_bps"],
                    })
    return rows


def summarize(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for scenario, _ in SCENARIOS:
        for overlay in ("agent_only", "scheme_c"):
            group = [r for r in rows if r["scenario"] == scenario and r["execution_overlay"] == overlay]
            summaries.append({
                "scenario": scenario,
                "execution_overlay": overlay,
                "episodes": len(group),
                "A_cost_mean_bps": statistics.fmean(r["A_cost_bps"] for r in group),
                "B_cost_mean_bps": statistics.fmean(r["B_cost_bps"] for r in group),
                "A_completion_mean": statistics.fmean(r["A_completion"] for r in group),
                "B_completion_mean": statistics.fmean(r["B_completion"] for r in group),
                "A_autonomous_fills_mean": statistics.fmean(r["A_autonomous_fills"] for r in group),
                "B_autonomous_fills_mean": statistics.fmean(r["B_autonomous_fills"] for r in group),
                "A_forced_completion_mean": statistics.fmean(r["A_forced_completion"] for r in group),
                "B_forced_completion_mean": statistics.fmean(r["B_forced_completion"] for r in group),
                "A_forced_cost_mean_bps": statistics.fmean(r["A_forced_cost_bps"] for r in group),
                "B_forced_cost_mean_bps": statistics.fmean(r["B_forced_cost_bps"] for r in group),
                "A_urgency_steps_mean": statistics.fmean(r["A_deadline_urgency_steps"] for r in group),
                "B_urgency_steps_mean": statistics.fmean(r["B_deadline_urgency_steps"] for r in group),
                "A_action_overrides_mean": statistics.fmean(r["A_deadline_action_overrides"] for r in group),
                "B_action_overrides_mean": statistics.fmean(r["B_deadline_action_overrides"] for r in group),
            })
        # Every key occurs once per overlay; explicitly pair both execution modes.
        for run_id in sorted({r["training_run"] for r in rows}):
            c_rows = [r for r in rows if r["scenario"] == scenario
                      and r["training_run"] == run_id and r["execution_overlay"] == "scheme_c"]
            for c_row in c_rows:
                base = next(r for r in rows if r["scenario"] == scenario
                            and r["training_run"] == run_id
                            and r["evaluation_seed"] == c_row["evaluation_seed"]
                            and r["execution_overlay"] == "agent_only")
                paired.append({
                    "training_run": run_id,
                    "scenario": scenario,
                    "evaluation_seed": c_row["evaluation_seed"],
                    "A_forced_delta_c_minus_agent": c_row["A_forced_completion"] - base["A_forced_completion"],
                    "B_forced_delta_c_minus_agent": c_row["B_forced_completion"] - base["B_forced_completion"],
                    "A_cost_delta_c_minus_agent_bps": c_row["A_cost_bps"] - base["A_cost_bps"],
                    "B_cost_delta_c_minus_agent_bps": c_row["B_cost_bps"] - base["B_cost_bps"],
                    "A_completion_delta": c_row["A_completion"] - base["A_completion"],
                    "B_completion_delta": c_row["B_completion"] - base["B_completion"],
                })
    return summaries, paired


def findings_text(args: argparse.Namespace, summaries: list[dict[str, Any]],
                  paired: list[dict[str, Any]]) -> str:
    lines = [
        "# 方案 C 截止加急：配对评估记录", "",
        f"- Q 检查点：第 {args.checkpoint} 回合；来自逐步进度惩罚与终局残余惩罚训练的当前双边模型。",
        f"- 每个场景：{args.training_runs} 个训练运行 × {args.eval_seeds} 个配对随机种子；单边手续费 {args.fee_bps:g} bp。",
        "- 比较对象：同一组冻结 A/B Q 表、同一市场路径、纯 Agent 动作 vs 旧版 C 截止覆盖；两组都保留第 60 步环境兜底。",
        "- C 规则：仅当剩余量落后于线性进度时启用；在执行窗口 70%、85%、95% 后将动作下限抬到可成交限价 IOC，并分别增加 1、3、6 个最小价位；加急阶段的 IOC 子单量至少覆盖剩余量除以剩余步数。",
        "- C 仅作为评估期动作覆盖；Q 表在两种模式下都冻结，不把 C 覆盖后的动作回写成 Q-learning 的学习样本。", "",
        "## 平均结果", "",
        "兜底量越低表示普通限价撮合中的自主成交越多；经济成本包含实际成交、手续费及冲击，不含学习惩罚。", "",
        "| 场景 | 执行方式 | A 兜底股数 | B 兜底股数 | A 成本 (bp) | B 成本 (bp) | 完成率 A/B | A/B 加急阶段步数 | A/B 动作档位上调步数 |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for scenario, _ in SCENARIOS:
        for overlay in ("agent_only", "scheme_c"):
            row = next(r for r in summaries if r["scenario"] == scenario and r["execution_overlay"] == overlay)
            lines.append(
                f"| {scenario} | {overlay} | {row['A_forced_completion_mean']:.0f} | "
                f"{row['B_forced_completion_mean']:.0f} | {row['A_cost_mean_bps']:.3f} | "
                f"{row['B_cost_mean_bps']:.3f} | {row['A_completion_mean']:.3f}/{row['B_completion_mean']:.3f} | "
                f"{row['A_urgency_steps_mean']:.1f}/{row['B_urgency_steps_mean']:.1f} | "
                f"{row['A_action_overrides_mean']:.1f}/{row['B_action_overrides_mean']:.1f} |"
            )
    lines += ["", "## 同种子配对差异", "",
              "差值定义为 C − 纯 Agent；兜底股数与成本差值小于零分别表示 C 减少兜底量或降低成本。", "",
              "| 场景 | A 兜底量差 | B 兜底量差 | A 成本差 (bp) | B 成本差 (bp) |", "|---|---:|---:|---:|---:|"]
    for scenario, _ in SCENARIOS:
        group = [r for r in paired if r["scenario"] == scenario]
        lines.append(
            f"| {scenario} | {statistics.fmean(r['A_forced_delta_c_minus_agent'] for r in group):.0f} | "
            f"{statistics.fmean(r['B_forced_delta_c_minus_agent'] for r in group):.0f} | "
            f"{statistics.fmean(r['A_cost_delta_c_minus_agent_bps'] for r in group):.3f} | "
            f"{statistics.fmean(r['B_cost_delta_c_minus_agent_bps'] for r in group):.3f} |"
        )
    lines += ["", "## 解释边界", "",
              "本试验只回答 C 覆盖能否减少当前 Q 检查点的终端兜底量，不比较 C 训练与纯 Q 训练的收敛性，也不代表 C 是最优方案。C 的加急阶段会提高限价上限；如果 Q 已选择 IOC，报价仍会被抬高，即使动作档位没有变化。更积极的 IOC 可能降低兜底量，也可能因更高 Taker 成交量、冲击或手续费而增加成本。所有结果来自未用真实盘口校准的合成订单簿；100% 完成仍由终端兜底保证。", "",
              f"- 冻结策略来源：`{args.checkpoint_dir}`。",
              f"- 原始配对结果：`c_overlay_raw.csv`；配对差异：`c_overlay_paired_differences.csv`；汇总：`c_overlay_summary.csv`。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    manifest_path = args.checkpoint_dir / "run_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Checkpoint run manifest not found: {manifest_path}")
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    trained = source.get("parameters", {})
    for key, current in (
        ("fee_bps", args.fee_bps),
        ("schedule_deficit_penalty_bps", args.schedule_deficit_penalty_bps),
        ("terminal_unfilled_penalty_bps", args.terminal_unfilled_penalty_bps),
    ):
        if key not in trained:
            raise SystemExit(f"Checkpoint manifest lacks {key}; use a checkpoint from the current training code")
        if abs(float(trained[key]) - current) > 1e-12:
            raise SystemExit(
                f"{key}={current} does not match the checkpoint training value {trained[key]} in {manifest_path}"
            )
    config = Config(
        inventory_risk_weight=0.0,
        schedule_deficit_penalty_bps=args.schedule_deficit_penalty_bps,
        terminal_unfilled_penalty_bps=args.terminal_unfilled_penalty_bps,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = run_comparison(args, config)
    summaries, paired = summarize(raw)
    write_csv(args.output_dir / "c_overlay_raw.csv", raw)
    write_csv(args.output_dir / "c_overlay_summary.csv", summaries)
    write_csv(args.output_dir / "c_overlay_paired_differences.csv", paired)
    (args.output_dir / "findings.md").write_text(
        findings_text(args, summaries, paired), encoding="utf-8",
    )
    (args.output_dir / "run_manifest.json").write_text(json.dumps({
        "checkpoint_dir": str(args.checkpoint_dir.resolve()),
        "checkpoint_episode": args.checkpoint,
        "training_runs": args.training_runs,
        "eval_seeds_per_scenario": args.eval_seeds,
        "base_seed": args.seed,
        "fee_bps": args.fee_bps,
        "schedule_deficit_penalty_bps": args.schedule_deficit_penalty_bps,
        "terminal_unfilled_penalty_bps": args.terminal_unfilled_penalty_bps,
        "scenarios": dict(SCENARIOS),
        "limit_order_parameters": {
            "tick_bps": SyntheticLOBConfig().tick_bps,
            "quote_ttl_steps": SyntheticLOBConfig().quote_ttl_steps,
        },
        "deadline_c_policy": {
            "only_when_behind_linear_schedule": True,
            "progress_stages": [0.70, 0.85, 0.95],
            "action_floor": 4,
            "extra_quote_ticks": [1, 3, 6],
            "catch_up_quantity": "min(remaining, max(2x base slice, remaining parent quantity / remaining steps))",
            "training_action_overrides": False,
        },
        "comparison": "same frozen Q checkpoints and paired seeds; agent-only vs evaluation-only C overlay",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"C overlay comparison complete. Findings: {(args.output_dir / 'findings.md').resolve()}")


if __name__ == "__main__":
    main()
