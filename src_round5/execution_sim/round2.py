from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Iterable

from execution_sim.models import SimulationConfig
from execution_sim.runner import run_named_episode
from execution_sim.strategies import SpreadUrgencyStrategy, TWAPStrategy


SCENARIOS: dict[str, dict[str, object]] = {
    "baseline": {},
    "spread_narrow_2bp": {"full_spread_bps": 2.0},
    "spread_wide_12bp": {"full_spread_bps": 12.0},
    "liquidity_low_10000": {"liquidity_shares": 10_000},
    "liquidity_high_40000": {"liquidity_shares": 40_000},
    "impact_low_half": {
        "temporary_impact_bps_per_liquidity_unit": 1.0,
        "permanent_impact_bps_per_liquidity_unit": 0.3,
    },
    "impact_high_double": {
        "temporary_impact_bps_per_liquidity_unit": 4.0,
        "permanent_impact_bps_per_liquidity_unit": 1.2,
    },
    "volatility_zero": {"volatility_bps": 0.0},
    "volatility_high_8bp": {"volatility_bps": 8.0},
    "fee_only_1bp": {"fee_bps": 1.0},
}


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _t_critical_95(df: int) -> float:
    z = 1.959963984540054
    v = float(df)
    return (
        z
        + (z**3 + z) / (4 * v)
        + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * v**2)
        + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * v**3)
    )


def _mean_sd_ci(values: list[float]) -> tuple[float, float, float, float]:
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    half_width = _t_critical_95(len(values) - 1) * sd / math.sqrt(len(values))
    return mean, sd, mean - half_width, mean + half_width


def _write_baseline_heatmap(path: Path, baseline_rows: list[dict[str, object]]) -> None:
    values = {str(row["strategy"]): float(row["mean_cost_bps"]) for row in baseline_rows}
    strategies = ("twap", "spread_urgency")
    low, high = min(values.values()), max(values.values())
    span = max(high - low, 1e-12)
    cell_w, cell_h, left, top = 220, 78, 180, 112
    width, height = left + cell_w * len(strategies) + 35, top + cell_h + 55
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#20242a}.label{font-size:13px}.title{font-size:18px;font-weight:600}.cell{font-size:14px;font-weight:600}</style>',
        f'<text x="{left}" y="28" class="title">A strategy cost against fixed B=TWAP (baseline parameters)</text>',
        f'<text x="{left}" y="54" class="label">Unit: bp of A initial order notional; each cell is mean of {baseline_rows[0]["seed_count"]} paired seeds; lower is cheaper</text>',
        f'<text x="10" y="82" class="label">Focus A</text>',
    ]
    for column, name in enumerate(strategies):
        x = left + column * cell_w
        value = values[name]
        ratio = (value - low) / span
        red, green, blue = int(239 - 74 * ratio), int(246 - 74 * ratio), int(248 - 55 * ratio)
        parts.append(f'<rect x="{x}" y="{top}" width="{cell_w - 4}" height="{cell_h - 4}" rx="2" fill="rgb({red},{green},{blue})"/>')
        parts.append(f'<text x="{x + (cell_w - 4) / 2}" y="{top + 31}" text-anchor="middle" class="label">{name} vs B=twap</text>')
        parts.append(f'<text x="{x + (cell_w - 4) / 2}" y="{top + 56}" text-anchor="middle" class="cell">{value:.3f} bp</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def run_round2(output_dir: Path, seed_count: int, seed_start: int) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty; choose a new path: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    base = SimulationConfig()
    seeds = list(range(seed_start, seed_start + seed_count))
    scenario_rows: list[dict[str, object]] = []
    step_rows: list[dict[str, object]] = []

    for scenario_name, overrides in SCENARIOS.items():
        config = SimulationConfig(**{**base.__dict__, **overrides})
        for seed in seeds:
            # Same seed gives common exogenous shocks for the paired strategy runs.
            for own_strategy in ("twap", "spread_urgency"):
                steps, metrics = run_named_episode(config, own_strategy, "twap", seed)
                step_rows.extend(
                    {"scenario": scenario_name, "focus_strategy": own_strategy, **row}
                    for row in steps
                    if row["agent_id"] == "A"
                )
                scenario_rows.append(
                    {
                        "scenario": scenario_name,
                        "seed": seed,
                        "strategy": own_strategy,
                        "opponent_strategy": "twap",
                        **metrics["A"],
                    }
                )

    grouped: dict[str, dict[str, list[dict[str, object]]]] = {}
    for scenario in SCENARIOS:
        grouped[scenario] = {
            strategy: sorted(
                (row for row in scenario_rows if row["scenario"] == scenario and row["strategy"] == strategy),
                key=lambda row: int(row["seed"]),
            )
            for strategy in ("twap", "spread_urgency")
        }

    summary_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    baseline_heatmap_rows: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        twap_rows = grouped[scenario]["twap"]
        adaptive_rows = grouped[scenario]["spread_urgency"]
        costs_twap = [float(row["total_cost_bps_of_initial_notional"]) for row in twap_rows]
        costs_adaptive = [float(row["total_cost_bps_of_initial_notional"]) for row in adaptive_rows]
        paired_delta = [adaptive - twap for adaptive, twap in zip(costs_adaptive, costs_twap)]
        for twap_row, adaptive_row, delta in zip(twap_rows, adaptive_rows, paired_delta):
            paired_rows.append(
                {
                    "scenario": scenario,
                    "seed": twap_row["seed"],
                    "twap_cost_bps": twap_row["total_cost_bps_of_initial_notional"],
                    "spread_urgency_cost_bps": adaptive_row["total_cost_bps_of_initial_notional"],
                    "delta_adaptive_minus_twap_bps": delta,
                }
            )
        mean_t, sd_t, lo_t, hi_t = _mean_sd_ci(costs_twap)
        mean_a, sd_a, lo_a, hi_a = _mean_sd_ci(costs_adaptive)
        mean_d, sd_d, lo_d, hi_d = _mean_sd_ci(paired_delta)
        requested = [
            float(row["action_requested_shares"])
            for row in step_rows
            if row["scenario"] == scenario and row["strategy"] == "spread_urgency"
        ]
        summary_rows.append(
            {
                "scenario": scenario,
                "seed_count": seed_count,
                "twap_mean_cost_bps": mean_t,
                "twap_seed_sd_bps": sd_t,
                "twap_95ci_low_bps": lo_t,
                "twap_95ci_high_bps": hi_t,
                "spread_urgency_mean_cost_bps": mean_a,
                "spread_urgency_seed_sd_bps": sd_a,
                "spread_urgency_95ci_low_bps": lo_a,
                "spread_urgency_95ci_high_bps": hi_a,
                "paired_delta_adaptive_minus_twap_mean_bps": mean_d,
                "paired_delta_seed_sd_bps": sd_d,
                "paired_delta_95ci_low_bps": lo_d,
                "paired_delta_95ci_high_bps": hi_d,
                "spread_urgency_mean_requested_shares": statistics.fmean(requested),
                "spread_urgency_first_step_requested_shares": requested[0],
            }
        )
        if scenario == "baseline":
            baseline_heatmap_rows.extend(
                [
                    {"strategy": "twap", "mean_cost_bps": mean_t, "seed_count": seed_count},
                    {"strategy": "spread_urgency", "mean_cost_bps": mean_a, "seed_count": seed_count},
                ]
            )

    config_payload = {
        "base_config": base.__dict__,
        "scenario_overrides": SCENARIOS,
        "seeds": seeds,
        "focus": "A strategy vs B fixed TWAP",
        "paired_unit": "one A result per seed; A/B role swaps are not counted as independent samples",
        "paired_comparison": "spread_urgency minus TWAP on the same seed within each scenario",
        "interval": "two-sided 95% paired Student t interval; t critical value uses Cornish-Fisher approximation",
        "fee_scenario_isolated": "fee_only_1bp changes only fee_bps from the baseline 0.3",
        "impact_scenarios_separate": "liquidity and impact coefficients are varied in separate named scenarios",
    }
    config_path = output_dir / "pressure_config.json"
    config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    metrics_path = output_dir / "pressure_metrics.csv"
    summary_path = output_dir / "pressure_summary_paired.csv"
    paired_path = output_dir / "pressure_paired_differences.csv"
    step_path = output_dir / "pressure_focus_step_log.csv"
    _write_csv(metrics_path, ["scenario", "seed", "strategy", "opponent_strategy", "agent_id", "filled_shares", "unfilled_shares", "fill_ratio", "implementation_shortfall", "fees", "terminal_unfilled_penalty", "total_cost", "total_cost_bps_of_initial_notional", "average_fill_price"], scenario_rows)
    _write_csv(summary_path, list(summary_rows[0]), summary_rows)
    _write_csv(paired_path, list(paired_rows[0]), paired_rows)
    _write_csv(step_path, list(step_rows[0]), step_rows)
    heatmap_path = output_dir / "baseline_cost_heatmap.svg"
    _write_baseline_heatmap(heatmap_path, baseline_heatmap_rows)

    failure_config = SimulationConfig(
        horizon_steps=30,
        initial_order_shares=100_000,
        max_trade_per_step=1_000,
        terminal_penalty_per_share=0.25,
    )
    failure_steps, failure_metrics = run_named_episode(failure_config, "twap", "twap", seed_start)
    failure_path = output_dir / "terminal_unfilled_counterexample.csv"
    failure_fields = ["scenario", *failure_steps[0].keys()]
    _write_csv(failure_path, failure_fields, ({"scenario": "max_trade_1000_over_30_steps", **row} for row in failure_steps))
    failure_metrics_path = output_dir / "terminal_unfilled_metrics.csv"
    _write_csv(failure_metrics_path, ["scenario", "seed", "agent_id", "filled_shares", "unfilled_shares", "fill_ratio", "implementation_shortfall", "fees", "terminal_unfilled_penalty", "total_cost", "total_cost_bps_of_initial_notional", "average_fill_price"], ({"scenario": "max_trade_1000_over_30_steps", "seed": seed_start, **failure_metrics[agent_id]} for agent_id in ("A", "B")))

    return {
        "config": config_path,
        "pressure_metrics": metrics_path,
        "pressure_summary": summary_path,
        "pressure_paired_differences": paired_path,
        "pressure_step_log": step_path,
        "baseline_heatmap": heatmap_path,
        "terminal_counterexample": failure_path,
        "terminal_metrics": failure_metrics_path,
    }
