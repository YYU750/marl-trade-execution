from __future__ import annotations

import csv
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Round 5 result identity and diagnostic invariants.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results_round5_standard" / "round5_key_findings.json",
        help="write the summary receipt to a new path; existing files are never overwritten",
    )
    args = parser.parse_args()
    old_trace = read_csv(ROOT / "results_round4_standard_02" / "test_action_trace.csv")
    new_trace = read_csv(ROOT / "results_round5_standard" / "test_action_trace.csv")
    old_metrics = read_csv(ROOT / "results_round4_standard_02" / "test_metrics.csv")
    new_metrics = read_csv(ROOT / "results_round5_standard" / "test_metrics.csv")
    old_q = [row for row in old_metrics if row["strategy"] == "q_learning_round4"]
    new_q = [row for row in new_metrics if row["strategy"] == "q_learning_round4"]
    action_key = lambda rows: {(row["seed"], row["step"]): row["action_index"] for row in rows}
    action_sequences_equal = action_key(old_trace) == action_key(new_trace)
    q_costs_equal = all(
        float(left["total_objective_bps_of_initial_notional"]) == float(right["total_objective_bps_of_initial_notional"])
        for left, right in zip(old_q, new_q)
    )
    if not action_sequences_equal or not q_costs_equal or len(old_q) != len(new_q):
        raise AssertionError("instrumented rerun changed the standard test decisions or costs")
    forced = sum(int(row["forced_fill_shares"]) for row in new_trace)
    filled = sum(int(row["filled_shares"]) for row in new_trace)
    reconcile_failures = sum(
        int(row["filled_shares"]) != int(row["request_after_clip_shares"]) + int(row["forced_fill_shares"])
        for row in new_trace
    )
    zero_diag = read_csv(ROOT / "results_round5_pressure_02" / "posthoc_zero_request_diagnostic.csv")
    pressure = read_csv(ROOT / "results_round5_pressure_02" / "pressure_summary.csv")
    pconfig = json.loads((ROOT / "results_round5_pressure_02" / "pressure_config.json").read_text(encoding="utf-8"))
    pressure_seed_range = pconfig["seed_range"]
    train_cfg = json.loads((ROOT / "results_round5_standard" / "qlearning_config.json").read_text(encoding="utf-8"))
    split_ranges = {key: train_cfg[f"{key}_seed_range"] for key in ("train", "validation", "test")}
    overlap = {
        key: not (pressure_seed_range[1] < values[0] or pressure_seed_range[0] > values[1])
        for key, values in split_ranges.items()
    }
    if any(overlap.values()):
        raise AssertionError(f"pressure seed range overlaps a standard split: {overlap}")
    if reconcile_failures:
        raise AssertionError(f"{reconcile_failures} trace rows fail the fill reconciliation")
    result = {
        "status": "complete",
        "standard_rerun_identity": {
            "q_costs_equal_to_round4": q_costs_equal,
            "action_sequences_equal_to_round4": action_sequences_equal,
            "q_test_episodes": len(new_q),
        },
        "standard_q_behavior": {
            "test_decision_steps": len(new_trace),
            "zero_multiplier_requests": sum(float(row["action_multiplier"]) == 0.0 for row in new_trace),
            "steps_with_forced_completion": sum(int(row["forced_fill_shares"]) > 0 for row in new_trace),
            "forced_shares": forced,
            "filled_shares": filled,
            "forced_share_fraction": forced / filled if filled else 0.0,
            "unseen_q_states": sum(row["state_seen_before"] == "False" for row in new_trace),
            "all_zero_q_vectors": sum(row["q_vector_all_zero_before"] == "True" for row in new_trace),
            "fill_reconciliation_failures": reconcile_failures,
        },
        "posthoc_zero_request_test_set": {
            "n": len(zero_diag),
            "zero_request_mean_bps": sum(float(row["total_objective_bps_of_initial_notional"]) for row in zero_diag) / len(zero_diag),
            "q_mean_bps": sum(float(row["q_objective_bps"]) for row in zero_diag) / len(zero_diag),
            "note": "diagnostic only; post hoc and not a pre-registered confirmatory comparison",
        },
        "pressure": {
            "seeds": pressure_seed_range,
            "seed_count": pconfig["seed_count"],
            "split_overlap": overlap,
            "scenarios": sorted({row["scenario"] for row in pressure}),
            "paired_summary_rows": sum(row["strategy"].startswith("paired_") for row in pressure),
        },
        "cost_definition": "total_objective = realized_fill_shortfall + unfilled_opportunity_cost + fees + terminal_penalty; reported bps divide by initial order notional",
    }
    destination = args.output.resolve()
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"SUMMARY_OK output={destination.resolve()} forced_share_fraction={forced/filled:.8f} unseen={result['standard_q_behavior']['unseen_q_states']} all_zero={result['standard_q_behavior']['all_zero_q_vectors']}")


if __name__ == "__main__":
    main()
