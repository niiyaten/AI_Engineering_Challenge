from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_competition.cross_source_calculation import execute_cross_source_calculation
from rag_competition.schemas import ExtractionResult, FileRecord


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def synthetic_record(root: Path, path: Path, project: str) -> FileRecord:
    relative = path.relative_to(root).as_posix()
    return FileRecord(
        file_id=f"file_{hashlib.sha1(relative.encode()).hexdigest()[:16]}",
        raw_path=relative,
        relative_path=relative,
        file_name=path.name,
        extension=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        modified_at="",
        sha1=hashlib.sha1(path.read_bytes()).hexdigest(),
        area="synthetic",
        project_name=project,
        major_folder="calculation",
        document_kind="analysis",
        version_label="",
    )


def evaluate_synthetic(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = root / "evaluation/synthetic/calculation/cross_source_metric_difference"
    results: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for index, row in enumerate(read_csv(base / "cases.csv"), start=1):
        case_dir = base / row["case_id"]
        files = []
        for path in sorted(case_dir.glob("*.json")):
            project = "別案件" if row["case_id"] == "negative_unrelated_project" and path.name == "final.json" else "合成案件"
            files.append(synthetic_record(root, path, project))
        output = execute_cross_source_calculation(index, row["question"], row["question"], files, {}, root)
        expected_allowed = row["expected_allowed"].lower() == "true"
        actual_allowed = output.get("status") == "success" and bool(output.get("answer"))
        expected_answer = row.get("expected_answer", "")
        passed = actual_allowed == expected_allowed and (not expected_allowed or output.get("answer") == expected_answer)
        results.append({
            "case_id": row["case_id"],
            "expected_allowed": expected_allowed,
            "actual_allowed": actual_allowed,
            "expected_answer": expected_answer,
            "actual_answer": output.get("answer", ""),
            "failure_stage": output.get("failure_stage", ""),
            "warning": output.get("warning", ""),
            "passed": passed,
        })
        evidence_rows.append({"dataset": "synthetic", "case_id": row["case_id"], "result": output})
    return results, evidence_rows


def evaluate_silver(root: Path, source_run: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    run = root / "data/work" / source_run
    files = [FileRecord(**row) for row in read_jsonl(run / "inventory/file_records.jsonl")]
    extractions = [ExtractionResult(**row) for row in read_jsonl(run / "extracted/extraction_results.jsonl")]
    extraction_by_file = {item.file_id: item for item in extractions}
    base = root / "evaluation/silver/calculation/cross_source_metric_difference"
    answers = {row["silver_id"]: row["answer"] for row in read_csv(base / "answers.csv")}
    results: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for index, row in enumerate(read_csv(base / "questions.csv"), start=1):
        output = execute_cross_source_calculation(index, row["question"], row["question"], files, extraction_by_file, root)
        prediction = str(output.get("answer", ""))
        reference = answers[row["silver_id"]]
        correct = bool(prediction) and prediction == reference
        results.append({
            "silver_id": row["silver_id"],
            "question": row["question"],
            "prediction": prediction,
            "reference_answer": reference,
            "correct": correct,
            "answered": bool(prediction),
            "status": output.get("status", ""),
            "failure_stage": output.get("failure_stage", ""),
            "warning": output.get("warning", ""),
            "actual_used_files": " | ".join(output.get("evidence", {}).get("actual_used_files", [])),
            "verification_status": output.get("verification", {}).get("verification_status", ""),
        })
        evidence_rows.append({"dataset": "silver", "silver_id": row["silver_id"], "result": output})
    return results, evidence_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-run", default="calculation_capability_baseline_fresh_v1")
    parser.add_argument("--output-run", default="calculation_capability_phase_v1")
    args = parser.parse_args()
    root = args.root.resolve()
    analysis = root / "data/output" / args.output_run / "analysis"
    synthetic, synthetic_evidence = evaluate_synthetic(root)
    silver, silver_evidence = evaluate_silver(root, args.source_run)
    write_csv(analysis / "synthetic_calculation_results.csv", synthetic)
    write_csv(analysis / "silver_calculation_results.csv", silver)
    write_jsonl(analysis / "calculation_execution_evidence.jsonl", synthetic_evidence + silver_evidence)
    failures = Counter(
        row["failure_stage"] or "none"
        for row in synthetic + silver
        if not row.get("passed", row.get("correct", False))
    )
    write_csv(analysis / "calculation_failure_summary.csv", [{"failure_stage": key, "count": value} for key, value in sorted(failures.items())])
    summary = {
        "synthetic_positive": sum(row["expected_allowed"] for row in synthetic),
        "synthetic_positive_pass": sum(row["expected_allowed"] and row["passed"] for row in synthetic),
        "synthetic_negative": sum(not row["expected_allowed"] for row in synthetic),
        "synthetic_negative_pass": sum(not row["expected_allowed"] and row["passed"] for row in synthetic),
        "silver_questions": len(silver),
        "silver_correct": sum(row["correct"] for row in silver),
        "silver_incorrect": sum(row["answered"] and not row["correct"] for row in silver),
        "silver_blank": sum(not row["answered"] for row in silver),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
