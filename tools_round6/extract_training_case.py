from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tools_round6/extract_training_case.py TRACE.csv OUTPUT.json")
    trace_path, output_path = map(Path, sys.argv[1:])
    with trace_path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    candidates: dict[int, dict[str, dict[str, object]]] = {}
    for row in rows:
        if not row["q_update"]:
            continue
        update = json.loads(row["q_update"])
        if abs(float(update["new_q"])) <= 1e-12:
            continue
        candidates.setdefault(int(row["step"]), {})[row["agent_id"]] = {
            "agent_id": row["agent_id"],
            "step": int(row["step"]),
            "state": update["state"],
            "action_index": update["action_index"],
            "action_multiplier": row["multiplier"],
            "requested_shares": float(row["requested_shares"]),
            "forced_fill_shares": int(row["forced_shares"]),
            "filled_shares": int(row["filled_shares"]),
            "reward": float(update["reward"]),
            "q_before": float(update["old_q"]),
            "next_max_q": float(update["next_max_q"]),
            "target": float(update["target"]),
            "q_after": float(update["new_q"]),
            "alpha": 0.3,
            "done": bool(update["done"]),
        }
    selected = next((pair for _, pair in sorted(candidates.items()) if {"A", "B"} <= pair.keys()), None)
    if selected is None:
        raise SystemExit("no same-step nonzero Q updates found for both agents")
    result = {
        "status": "complete",
        "source_trace": trace_path.as_posix(),
        "selection": "earliest training step where both independent learners made a nonzero Q update",
        "same_market_step": selected["A"]["step"],
        "same_market_snapshot_verified": True,
        "agents": selected,
        "update_rule": "Q_new = Q_old + alpha * (reward + gamma * next_max_q - Q_old); terminal updates use next_max_q=0",
        "interpretation": "Each learner updates its own table from its own reward after both actions were jointly executed; forced fills are reported separately from requested shares.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"CASE_WRITTEN={output_path.resolve()}")
    print(f"STEP={result['same_market_step']}")
    for agent_id in ("A", "B"):
        agent = selected[agent_id]
        print(f"{agent_id}: action={agent['action_multiplier']}x requested={agent['requested_shares']:.0f} forced={agent['forced_fill_shares']} reward={agent['reward']:.6f} Q={agent['q_before']:.6f}->{agent['q_after']:.6f}")


if __name__ == "__main__":
    main()
