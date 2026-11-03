from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from execution_sim.models import SimulationConfig
from execution_sim.runner import run_named_episode
from execution_sim.strategies import STRATEGY_FACTORIES


STEP_FIELDS = [
    "seed", "step", "agent_id", "strategy", "opponent_strategy", "mid_price_before", "mid_price_after",
    "full_spread_bps", "liquidity_shares", "action_requested_shares", "filled_shares", "remaining_shares",
    "joint_filled_shares", "exogenous_shock_bps", "temporary_impact_bps", "permanent_impact_bps", "fill_price",
    "implementation_shortfall", "spread_cost_component_is_only", "temporary_impact_component_is_only", "fee",
    "terminal_unfilled_penalty", "reward",
]
METRIC_FIELDS = [
    "seed", "strategy", "opponent_strategy", "agent_id", "filled_shares", "unfilled_shares", "fill_ratio",
    "implementation_shortfall", "fees", "terminal_unfilled_penalty", "total_cost",
    "total_cost_bps_of_initial_notional", "average_fill_price",
]
SUMMARY_VALUE_FIELDS = [
    "filled_shares", "unfilled_shares", "fill_ratio", "implementation_shortfall", "fees",
    "terminal_unfilled_penalty", "total_cost", "total_cost_bps_of_initial_notional",
]


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_heatmap(path: Path, matrix: dict[tuple[str, str], float], names: list[str]) -> None:
    cell_w, cell_h, left, top = 150, 66, 155, 100
    width = left + cell_w * len(names) + 35
    height = top + cell_h * len(names) + 55
    values = list(matrix.values())
    low, high = min(values), max(values)
    span = max(high - low, 1e-12)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#20242a}.label{font-size:13px}.title{font-size:19px;font-weight:600}.cell{font-size:13px;font-weight:600}</style>',
        f'<text x="{left}" y="30" class="title">Average total execution cost (bps of initial order notional)</text>',
        f'<text x="{left}" y="58" class="label">Rows: A strategy | Columns: B strategy | one A result per paired seed; lower is less cost</text>',
        f'<text x="8" y="80" class="label">Own \\ Opp.</text>',
    ]
    for col, name in enumerate(names):
        x = left + col * cell_w + cell_w / 2
        parts.append(f'<text x="{x}" y="84" text-anchor="middle" class="label">{name}</text>')
    for row, own in enumerate(names):
        y = top + row * cell_h
        parts.append(f'<text x="{left - 10}" y="{y + 38}" text-anchor="end" class="label">{own}</text>')
        for col, opponent in enumerate(names):
            value = matrix[(own, opponent)]
            ratio = (value - low) / span
            red = int(239 - 74 * ratio)
            green = int(246 - 74 * ratio)
            blue = int(248 - 55 * ratio)
            x = left + col * cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w - 3}" height="{cell_h - 3}" rx="2" fill="rgb({red},{green},{blue})"/>')
            parts.append(f'<text x="{x + (cell_w - 3) / 2}" y="{y + 37}" text-anchor="middle" class="cell">{value:.2f}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _t_critical_95(df: int) -> float:
    z = 1.959963984540054
    v = float(df)
    return (
        z
        + (z**3 + z) / (4 * v)
        + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * v**2)
        + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * v**3)
    )


def run_experiment(config: SimulationConfig, output_dir: Path, seed_count: int, seed_start: int) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty; choose a new path: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    names = list(STRATEGY_FACTORIES)
    seeds = list(range(seed_start, seed_start + seed_count))
    all_steps: list[dict[str, object]] = []
    scenario_rows: list[dict[str, object]] = []

    for strategy_a in names:
        for strategy_b in names:
            for seed in seeds:
                steps, metrics = run_named_episode(config, strategy_a, strategy_b, seed)
                all_steps.extend(steps)
                for agent_id, own_strategy, opponent in (
                    ("A", strategy_a, strategy_b),
                    ("B", strategy_b, strategy_a),
                ):
                    scenario_rows.append(
                        {
                            "seed": seed,
                            "strategy": own_strategy,
                            "opponent_strategy": opponent,
                            **metrics[agent_id],
                        }
                    )

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in scenario_rows:
        if row["agent_id"] != "A":
            continue
        grouped[(str(row["strategy"]), str(row["opponent_strategy"]))].append(row)
    summary_rows: list[dict[str, object]] = []
    paired_difference_rows: list[dict[str, object]] = []
    cost_matrix: dict[tuple[str, str], float] = {}
    for own in names:
        for opponent in names:
            group = grouped[(own, opponent)]
            baseline_by_seed = {
                int(row["seed"]): row
                for row in grouped[("twap", opponent)]
            }
            paired_deltas = []
            for row in group:
                baseline = baseline_by_seed[int(row["seed"])]
                candidate_cost = float(row["total_cost_bps_of_initial_notional"])
                baseline_cost = float(baseline["total_cost_bps_of_initial_notional"])
                delta = candidate_cost - baseline_cost
                paired_deltas.append(delta)
                paired_difference_rows.append(
                    {
                        "seed": row["seed"],
                        "strategy": own,
                        "opponent_strategy": opponent,
                        "twap_baseline_cost_bps": baseline_cost,
                        "candidate_cost_bps": candidate_cost,
                        "delta_vs_twap_bps": delta,
                    }
                )
            delta_mean = statistics.fmean(paired_deltas)
            delta_sd = statistics.stdev(paired_deltas) if len(paired_deltas) > 1 else 0.0
            delta_half_width = (
                _t_critical_95(len(paired_deltas) - 1) * delta_sd / math.sqrt(len(paired_deltas))
                if len(paired_deltas) > 1
                else 0.0
            )
            summary: dict[str, object] = {
                "strategy": own,
                "opponent_strategy": opponent,
                "seed_count": len(group),
                "paired_delta_vs_twap_mean_bps": delta_mean,
                "paired_delta_vs_twap_seed_sd_bps": delta_sd,
                "paired_delta_vs_twap_95ci_low_bps": delta_mean - delta_half_width,
                "paired_delta_vs_twap_95ci_high_bps": delta_mean + delta_half_width,
            }
            for field in SUMMARY_VALUE_FIELDS:
                samples = [float(row[field]) for row in group]
                summary[f"mean_{field}"] = statistics.fmean(samples)
                summary[f"sd_{field}"] = statistics.stdev(samples) if len(samples) > 1 else 0.0
            summary_rows.append(summary)
            cost_matrix[(own, opponent)] = float(summary["mean_total_cost_bps_of_initial_notional"])

    config_payload = {
        "market": config.__dict__,
        "seed_start": seed_start,
        "seed_count": seed_count,
        "seeds": seeds,
        "strategy_names": names,
        "paired_design": "all ordered strategy pairs; each seed is shared across pair comparisons",
        "terminal_penalty": "separately reported currency per unfilled share; default is a teaching assumption",
        "reward": "negative implementation shortfall minus fees and terminal penalty; price impacts enter through prices only",
    }
    (output_dir / "config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    _write_csv(output_dir / "step_log.csv", STEP_FIELDS, all_steps)
    _write_csv(output_dir / "scenario_metrics.csv", METRIC_FIELDS, scenario_rows)
    summary_fields = [
        "strategy",
        "opponent_strategy",
        "seed_count",
        "paired_delta_vs_twap_mean_bps",
        "paired_delta_vs_twap_seed_sd_bps",
        "paired_delta_vs_twap_95ci_low_bps",
        "paired_delta_vs_twap_95ci_high_bps",
    ] + [
        item for field in SUMMARY_VALUE_FIELDS for item in (f"mean_{field}", f"sd_{field}")
    ]
    _write_csv(output_dir / "strategy_pair_summary.csv", summary_fields, summary_rows)
    paired_path = output_dir / "paired_strategy_differences.csv"
    _write_csv(
        paired_path,
        ["seed", "strategy", "opponent_strategy", "twap_baseline_cost_bps", "candidate_cost_bps", "delta_vs_twap_bps"],
        paired_difference_rows,
    )
    heatmap_path = output_dir / "cost_heatmap.svg"
    _write_heatmap(heatmap_path, cost_matrix, names)

    representative, _ = run_named_episode(config, "twap", "spread_urgency", seed_start)
    representative_path = output_dir / f"representative_{config.horizon_steps}_step.csv"
    _write_csv(representative_path, STEP_FIELDS, representative)
    return {
        "config": output_dir / "config.json",
        "step_log": output_dir / "step_log.csv",
        "scenario_metrics": output_dir / "scenario_metrics.csv",
        "strategy_pair_summary": output_dir / "strategy_pair_summary.csv",
        "paired_strategy_differences": paired_path,
        "cost_heatmap": heatmap_path,
        "representative_episode": representative_path,
    }
