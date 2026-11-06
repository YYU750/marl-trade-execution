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
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "c_overlay_comparison_with_stochastic_c"


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
                for overlay, c_mode in (
                    ("agent_only", "none"),
                    ("scheme_c", "deterministic"),
                    ("stochastic_c", "stochastic"),
                ):
                    result = episode(
                        agents["A"], agents["B"], config, seed, args.fee_bps,
                        volatility_multiplier, training=False,
                        completion_mode="autonomous", deadline_c_mode=c_mode,
                    )
                    rows.append({
                        "training_run": run_id,
                        "checkpoint": args.checkpoint,
                        "scenario": scenario,
                        "evaluation_seed": seed,
                        "execution_overlay": overlay,
                        "deadline_c_mode": c_mode,
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
                        "A_c_interventions": result["deadline_c_interventions_A"],
                        "B_c_interventions": result["deadline_c_interventions_B"],
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
        for overlay in ("agent_only", "scheme_c", "stochastic_c"):
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
                "A_c_interventions_mean": statistics.fmean(r["A_c_interventions"] for r in group),
                "B_c_interventions_mean": statistics.fmean(r["B_c_interventions"] for r in group),
            })
        # Pair both C variants against the identical pure-agent seed.
        for run_id in sorted({r["training_run"] for r in rows}):
            for variant in ("scheme_c", "stochastic_c"):
                c_rows = [r for r in rows if r["scenario"] == scenario
                          and r["training_run"] == run_id and r["execution_overlay"] == variant]
                for c_row in c_rows:
                    base = next(r for r in rows if r["scenario"] == scenario
                                and r["training_run"] == run_id
                                and r["evaluation_seed"] == c_row["evaluation_seed"]
                                and r["execution_overlay"] == "agent_only")
                    paired.append({
                        "training_run": run_id,
                        "scenario": scenario,
                        "evaluation_seed": c_row["evaluation_seed"],
                        "execution_overlay": variant,
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
        "- 比较对象：同一组冻结 A/B Q 表、同一市场路径下的纯 Agent、确定性 C 和随机 C；三组均保留第 60 步环境兜底。",
        "- 确定性 C 保留旧版 70%、85%、95% 截止加急逻辑。随机 C 从落后进度时即可低概率介入，离截止越近且缺口越大，介入概率越高；每次介入再随机抽取动作下限、报价加价档和追赶数量比例，前段偏被动、后段逐步提高成交确定性。",
        "- 本脚本属于冻结策略的评估期覆盖；Q 表不更新。随机 C 参与训练的结果须另行比较。", "",
        "## 平均结果", "",
        "兜底量越低表示普通限价撮合中的自主成交越多；经济成本包含实际成交、手续费及冲击，不含学习惩罚。", "",
              "| 场景 | 执行方式 | A 兜底股数 | B 兜底股数 | A 成本 (bp) | B 成本 (bp) | 完成率 A/B | A/B 落后进度步数 | A/B 动作上调步数 | A/B 随机C介入步数 |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for scenario, _ in SCENARIOS:
        for overlay in ("agent_only", "scheme_c", "stochastic_c"):
            row = next(r for r in summaries if r["scenario"] == scenario and r["execution_overlay"] == overlay)
            lines.append(
                f"| {scenario} | {overlay} | {row['A_forced_completion_mean']:.0f} | "
                f"{row['B_forced_completion_mean']:.0f} | {row['A_cost_mean_bps']:.3f} | "
                f"{row['B_cost_mean_bps']:.3f} | {row['A_completion_mean']:.3f}/{row['B_completion_mean']:.3f} | "
                f"{row['A_urgency_steps_mean']:.1f}/{row['B_urgency_steps_mean']:.1f} | "
                f"{row['A_action_overrides_mean']:.1f}/{row['B_action_overrides_mean']:.1f} | "
                f"{row['A_c_interventions_mean']:.1f}/{row['B_c_interventions_mean']:.1f} |"
            )
    lines += ["", "## 同种子配对差异", "",
              "差值定义为对应 C 版本 − 纯 Agent；兜底股数与成本差值小于零分别表示减少兜底量或降低成本。", "",
              "| 场景 | C 版本 | A 兜底量差 | B 兜底量差 | A 成本差 (bp) | B 成本差 (bp) |", "|---|---|---:|---:|---:|---:|"]
    for scenario, _ in SCENARIOS:
        for variant in ("scheme_c", "stochastic_c"):
            group = [r for r in paired if r["scenario"] == scenario and r["execution_overlay"] == variant]
            lines.append(
                f"| {scenario} | {variant} | {statistics.fmean(r['A_forced_delta_c_minus_agent'] for r in group):.0f} | "
                f"{statistics.fmean(r['B_forced_delta_c_minus_agent'] for r in group):.0f} | "
                f"{statistics.fmean(r['A_cost_delta_c_minus_agent_bps'] for r in group):.3f} | "
                f"{statistics.fmean(r['B_cost_delta_c_minus_agent_bps'] for r in group):.3f} |"
            )
    lines += ["", "## 解释边界", "",
              "本试验冻结相同 Q 检查点，比较纯 Agent、确定性 C 和随机 C；随机 C 在进度落后时以进度阶段和缺口大小决定介入概率，再抽取动作档位、报价加价档和追赶数量比例。该表仍是评估期对照，Q 表不更新；另需与随机 C 参与训练的 Q 模型分开报告。所有结果来自合成订单簿；100% 完成仍由终端兜底保证。", "",
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
            "activation": "randomized when behind linear schedule; probability increases with deficit and deadline stage",
            "early_window": {"base_probability": 0.12, "action_floors": [1, 2, 3], "ticks": [0, 1], "catch_up_fraction": [0.10, 0.30]},
            "urgency_window": {"base_probability": 0.32, "action_floors": [2, 3, 4], "ticks": [0, 1, 2], "catch_up_fraction": [0.25, 0.55]},
            "high_urgency_window": {"base_probability": 0.60, "action_floors": [3, 4], "ticks": [0, 1, 2, 3], "catch_up_fraction": [0.40, 0.80]},
            "final_sweep_window": {"base_probability": 0.88, "action_floors": [3, 4], "ticks": [0, 1, 2, 3, 4, 5, 6], "catch_up_fraction": [0.70, 1.00]},
            "deficit_probability_increment_per_base_slice": 0.03,
            "deficit_increment_cap": 0.20,
            "probability_cap": 0.98,
            "action_floor_distributions": {
                "early_window": {"1": 0.10, "2": 0.55, "3": 0.35},
                "urgency_window": {"2": 0.12, "3": 0.55, "4": 0.33},
                "high_urgency_window": {"3": 0.38, "4": 0.62},
                "final_sweep_window": {"3": 0.10, "4": 0.90},
            },
            "quote_tick_distributions": {
                "early_window": {"0": 0.85, "1": 0.15},
                "urgency_window": {"0": 0.62, "1": 0.30, "2": 0.08},
                "high_urgency_window": {"0": 0.52, "1": 0.28, "2": 0.15, "3": 0.05},
                "final_sweep_window": {"0": 0.24, "1": 0.22, "2": 0.18, "3": 0.14, "4": 0.10, "5": 0.07, "6": 0.05},
            },
            "training_action_overrides": False,
        },
        "comparison": "same frozen Q checkpoints and paired seeds; pure Q vs deterministic C vs randomized C evaluation overlays",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"C overlay comparison complete. Findings: {(args.output_dir / 'findings.md').resolve()}")


if __name__ == "__main__":
    main()
