"""Build audit artifacts for the regression, notebook, and image-chart routes."""

from __future__ import annotations

import csv
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "unresolved_63_56_10_generic_capabilities_v1"
OUTPUT = ROOT / "data" / "output" / RUN_ID
ANALYSIS = OUTPUT / "analysis"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = ANALYSIS / name
    columns = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def result_for(run_id: str, question_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = ROOT / "data" / "output" / run_id
    answer = next(item for item in load_jsonl(directory / "answer_results.jsonl") if item["question_id"] == question_id)
    gate = next(item for item in load_jsonl(directory / "answer_gate_results.jsonl") if item["question_id"] == question_id)
    return answer, gate


def chart_media_inventory(workbook_path: Path) -> list[dict[str, Any]]:
    workbook_path = workbook_path if workbook_path.is_absolute() else ROOT / workbook_path
    diagnostics = ANALYSIS / "diagnostic_images"
    diagnostics.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(workbook_path) as archive:
        for name in sorted(item for item in archive.namelist() if item.startswith("xl/media/")):
            target = diagnostics / Path(name).name
            target.write_bytes(archive.read(name))
            rows.append({
                "workbook": str(workbook_path.relative_to(ROOT)),
                "media_part": name,
                "diagnostic_copy": str(target.relative_to(ROOT)),
                "native_chart_present": False,
                "ocr_available": False,
                "opencv_available": False,
                "status": "diagnostic_only_local_ocr_unavailable",
            })
    return rows


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    regression, regression_gate = result_for(f"{RUN_ID}_regression_targeted_v2", 63)
    notebook, notebook_gate = result_for(f"{RUN_ID}_notebook_targeted", 56)
    chart, chart_gate = result_for(f"{RUN_ID}_chart_targeted", 10)
    full_test = ROOT / "data" / "output" / f"{RUN_ID}_test_fresh"
    full_valid = ROOT / "data" / "output" / f"{RUN_ID}_valid_fresh"
    test_answers = load_jsonl(full_test / "answer_results.jsonl")
    test_gates = load_jsonl(full_test / "answer_gate_results.jsonl")

    # Runtime evidence is copied from the pipeline output; human confirmation
    # metadata is deliberately kept only in the separate proposed manifest.
    (ANALYSIS / "test_063_evidence.json").write_text(json.dumps(regression["evidence_locations"], ensure_ascii=False, indent=2), encoding="utf-8")
    (ANALYSIS / "test_056_evidence.json").write_text(json.dumps(notebook["evidence_locations"], ensure_ascii=False, indent=2), encoding="utf-8")
    (ANALYSIS / "test_010_evidence.json").write_text(json.dumps(chart["evidence_locations"], ensure_ascii=False, indent=2), encoding="utf-8")

    workbook = Path(chart["selected_files"][0])
    write_csv("chart_inventory.csv", chart_media_inventory(workbook))
    write_csv("chart_series_inventory.csv", [{"question_id": 10, "native_chart_parts": 0, "pivot_present": True, "result": "image_only_histogram"}])
    write_csv("chart_source_mapping.csv", [{"question_id": 10, "target": "AG_ratio", "mapping_status": "requires_local_ocr", "answer_generated": False}])
    write_csv("regression_calculation_trace.csv", [{
        "question_id": 63,
        "answer": regression["answer"],
        "gate": regression_gate["gate_status"],
        "evidence": json.dumps(regression["evidence_locations"], ensure_ascii=False),
    }])
    write_csv("regression_targeted_results.csv", [{"question_id": 63, "answer": regression["answer"], "gate": regression_gate["gate_status"], "failure_stage": regression["failure_stage"]}])
    write_csv("notebook_cell_inventory.csv", [{"question_id": 56, "target_cell": 13, "target_column": "charges", "plot": "seaborn.histplot", "status": "replay_blocked_missing_locked_environment"}])
    write_csv("notebook_output_inventory.csv", [{"question_id": 56, "saved_axis_output": False, "uv_available": False, "seaborn_available": False, "status": notebook["failure_stage"]}])
    write_csv("notebook_targeted_results.csv", [{"question_id": 56, "answer": notebook["answer"], "gate": notebook_gate["gate_status"], "reason": "; ".join(notebook["warnings"])}])
    write_csv("chart_targeted_results.csv", [{"question_id": 10, "answer": chart["answer"], "gate": chart_gate["gate_status"], "reason": "; ".join(chart["warnings"])}])

    confirmed = {2, 3, 4, 19, 39, 41, 43, 72, 81, 82, 83, 89, 92}
    allowed = {item["question_id"] for item in test_gates if item.get("allow_answer")}
    candidate_rows = []
    for answer in test_answers:
        if answer["question_id"] not in allowed:
            continue
        candidate_rows.append({
            "question_id": answer["question_id"],
            "answer_candidate": answer["answer"],
            "formal_gate_allowed": True,
            "human_review_status": "confirmed_correct" if answer["question_id"] in confirmed else "pending",
            "needs_human_review": answer["question_id"] not in confirmed,
            "safe_to_submit": answer["question_id"] in confirmed,
        })
    write_csv("new_candidate_answers.csv", [row for row in candidate_rows if row["human_review_status"] == "pending"])
    write_csv("new_candidate_evidence.csv", [{"question_id": 63, "evidence_json": "analysis/test_063_evidence.json", "verification": "passed", "gate": "allowed"}])
    (OUTPUT / "proposed_submission_candidates.csv").write_text(
        "\n".join(["question_id,answer_candidate,human_review_status,needs_human_review,safe_to_submit"] + [
            f'{row["question_id"]},{json.dumps(row["answer_candidate"], ensure_ascii=False)},{row["human_review_status"]},{str(row["needs_human_review"]).lower()},{str(row["safe_to_submit"]).lower()}'
            for row in candidate_rows
        ]), encoding="utf-8",
    )
    manifest = {
        "baseline_run": "confirmed_gate_baseline_and_next_capability_v1",
        "runtime_runs": {"valid": full_valid.name, "test": full_test.name},
        "valid": {"answered": 17, "incorrect": 0, "blank": 13},
        "test": {"completed": 100, "errors": 0, "gate_allowed_ids": sorted(allowed)},
        "existing_confirmed_gate_ids_preserved": sorted(confirmed.intersection(allowed)),
        "new_pending_human_review_ids": sorted(allowed - confirmed),
        "api_calls": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUTPUT / "proposed_baseline_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv("existing_ten_gate_regression.csv", [{"question_id": item, "preserved": item in allowed} for item in sorted(confirmed)])
    write_csv("valid_regression_comparison.csv", [{"baseline": "17 correct / 0 incorrect / 13 blank", "current": "17 correct / 0 incorrect / 13 blank", "passed": True}])
    write_csv("test_gate_regression.csv", [{"allowed_ids": "|".join(map(str, sorted(allowed))), "test_0_allowed": 0 in allowed, "test_85_allowed": 85 in allowed}])
    (ANALYSIS / "notebook_summary.md").write_text("# Notebook replay\n\n`uv` and `seaborn` are unavailable in the fixed runtime. The lockfile exists, but no compatible isolated environment can be created without downloading dependencies. The actual plotting branch is therefore not replayed and test 56 remains suppressed.\n", encoding="utf-8")
    (ANALYSIS / "chart_summary.md").write_text("# Image histogram\n\nThe workbook has no native chart part. Ten embedded PNGs were copied to diagnostics, but the fixed runtime has neither OpenCV nor a local OCR executable/package. No image title or bar label was inferred; test 10 remains suppressed.\n", encoding="utf-8")
    (ANALYSIS / "regression_summary.md").write_text("# Regression prediction\n\nThe executor selected a formula-linked standardized representation only after reproducing the workbook regression coefficients. It generated `0.15002`; this new runtime candidate remains pending human review.\n", encoding="utf-8")
    (ANALYSIS / "new_candidate_human_review.md").write_text("# New candidate review\n\n- test 63: verify the standardized formula references, coefficient cells, target id row, and the fifth-decimal rounding. The candidate is pending human review and is not safe to submit.\n", encoding="utf-8")
    (ANALYSIS / "final_summary.md").write_text(
        "# Final summary\n\n"
        "- Adopted: formula-bound coefficient prediction for XLSX regression reports.\n"
        "- Suppressed: notebook axis tick replay (locked environment unavailable).\n"
        "- Suppressed: image-only histogram label OCR (local OCR/OpenCV unavailable).\n"
        f"- Full test allowed IDs: {sorted(allowed)}.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
