from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a curated, reproducible Round 5 Q-learning audit bundle.")
    parser.add_argument("--output", type=Path, default=ROOT / "deliverables" / "qlearning_audit_bundle_round5.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")

    files: list[Path] = []
    for folder in ("src_round5/execution_sim", "tests_round5", "tools_round5", "audit_round5", "deliverables"):
        base = ROOT / folder
        for path in base.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if folder == "tools_round5" and path.name not in {
                "replay_selected_training_episode.py",
                "replay_selected_training_update.py",
                "summarize_round5.py",
            }:
                continue
            if folder == "deliverables" and path.name not in {"round5_course_report.md"}:
                continue
            files.append(path)
    for name in (
        "run_qlearning_round5.py",
        "run_round5_pressure.py",
        "README.md",
        ".gitignore",
    ):
        path = ROOT / name
        if path.exists():
            files.append(path)
    for name in (
        "qlearning_config.json",
        "q_table_selected.json",
        "test_summary.json",
        "test_metrics.csv",
        "test_paired_comparison.csv",
        "test_action_distribution.csv",
        "test_action_trace.csv",
        "validation_candidates.csv",
        "model_reload_check.json",
    ):
        files.append(ROOT / "results_round5_standard" / name)
    for name in (
        "pressure_config.json",
        "pressure_summary.csv",
        "pressure_paired_differences.csv",
        "pressure_q_action_trace.csv",
    ):
        files.append(ROOT / "results_round5_pressure_02" / name)

    unique_files = sorted(set(files), key=lambda path: path.relative_to(ROOT).as_posix())
    for path in unique_files:
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = []
    for path in unique_files:
        data = path.read_bytes()
        manifest.append(f"{hashlib.sha256(data).hexdigest()}  {path.relative_to(ROOT).as_posix()}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=8) as archive:
        for path in unique_files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("BUNDLE_SHA256SUMS.txt", "\n".join(manifest) + "\n")
    with ZipFile(output) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"ZIP CRC failed for {bad_member}")
        members = archive.namelist()
    print(f"BUNDLE_OK members={len(members)} bytes={output.stat().st_size} path={output}")


if __name__ == "__main__":
    main()
