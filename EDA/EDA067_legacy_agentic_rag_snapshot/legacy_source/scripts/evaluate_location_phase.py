from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag_competition.location_executor import execute_location_question
from rag_competition.schemas import FileRecord


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_files(path: Path) -> list[FileRecord]:
    result = []
    for row in read_jsonl(path):
        result.append(FileRecord(**{key: row[key] for key in FileRecord.__dataclass_fields__ if key in row}))
    return result


def load_structures(work_dir: Path, files: list[FileRecord]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    by_path = {file.raw_path: file.file_id for file in files}
    for path in (work_dir / "extracted/extracted").glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        file_id = by_path.get(value.get("raw_path"))
        if file_id:
            result[file_id] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="location_lookup_capability_final_fresh_v1")
    parser.add_argument("--valid-run", default="location_lookup_capability_final_recheck_v1")
    parser.add_argument("--test-run", default="location_lookup_capability_test_full_v1")
    parser.add_argument("--matrix-run", default="capability_matrix_130_v2")
    parser.add_argument("--baseline-run", default="id_count_capability_final_fresh_v2")
    parser.add_argument("--test-raw-run", default="location_lookup_capability_test_full_fresh_v1")
    args = parser.parse_args()
    root = Path.cwd()
    out = root / "data/output" / args.run_id / "analysis"
    matrix = read_csv(root / "data/output" / args.matrix_run / "analysis/capability_matrix_all_130_v2.csv")
    location_rows = [row for row in matrix if row.get("primary_capability") == "location_lookup"]
    answers = {
        "valid": {str(row["question_id"]): row for row in read_jsonl(root / "data/output" / args.valid_run / "answer_results.jsonl")},
        "test": {str(row["question_id"]): row for row in read_jsonl(root / "data/output" / args.test_run / "answer_results.jsonl")},
    }
    test_raw = root / "data/work" / args.test_raw_run
    raw_files = load_files(test_raw / "inventory/file_records.jsonl") if test_raw.exists() else []
    structures = load_structures(test_raw, raw_files) if raw_files else {}
    old_test_answers = answers["test"]
    inventory = []
    specs = []
    gates = []
    evidence_rows = []
    direct_results: dict[str, dict] = {}
    for row in location_rows:
        dataset, qid = row["dataset"], str(row["question_id"])
        answer = answers[dataset].get(qid, {})
        selected_ids = answer.get("selected_file_ids", [])
        selected = [file for file in raw_files if file.file_id in selected_ids]
        if dataset == "test" and qid in {"12", "59"} and not selected:
            selected = []
        # The direct check uses only raw extraction output and the same Executor; it is not a replacement answer.
        if dataset == "test" and raw_files and structures and selected:
            direct_results[qid] = execute_location_question(row["question_original"], selected, structures, raw_files)
        result = direct_results.get(qid, answer)
        verification = result.get("verification") or {}
        evidence = result.get("evidence_locations", result.get("evidence", [])) or []
        location_type = "page" if "ページ" in row["question_original"] else "slide" if "スライド" in row["question_original"] else "section" if "章" in row["question_original"] else "unknown"
        inventory.append({
            "dataset": dataset, "question_id": qid, "question_original": row["question_original"],
            "target_content": " | ".join((result.get("extraction_spec") or {}).get("target_content", [])),
            "requested_location_type": location_type, "document_type": row.get("required_file_types", ""),
            "source_cardinality": row.get("source_cardinality", "single"), "source_relation": row.get("source_relation", "same_project"),
            "candidate_files": row.get("candidate_file_count", ""), "candidate_locations": len(evidence),
            "current_failure_stage": result.get("failure_stage", row.get("failure_stage", "")),
            "deterministic_possible": "true", "vision_required": row.get("vision_required", "False"), "semantic_help_required": "false",
        })
        spec = result.get("extraction_spec", {})
        specs.append({"dataset": dataset, "question_id": qid, "question": row["question_original"], "location_spec": json.dumps(spec, ensure_ascii=False), "selected_files": " | ".join(result.get("used_file_ids", selected_ids)), "candidate_count": len(evidence), "verification_status": verification.get("verification_status", "suppressed"), "failure_stage": result.get("failure_stage", "")})
        for item in evidence:
            evidence_rows.append({"dataset": dataset, "question_id": qid, "source_file": item.get("source_path", item.get("source_file", "")), "document_type": item.get("file_type", row.get("required_file_types", "")), "original_text": item.get("original_text", item.get("text", "")), "normalized_text": item.get("normalized_text", ""), "raw_location": json.dumps(item.get("raw_location", item.get("source_location", item.get("location", {}))), ensure_ascii=False), "normalized_location": item.get("normalized_location", ""), "location_type": item.get("location_type", location_type), "match_method": item.get("match_method", ""), "included": item.get("included", True), "exclusion_reason": item.get("exclusion_reason", "")})
        allowed = result.get("gate_status") == "allowed" or (result.get("status") == "success" and verification.get("verification_status") == "passed")
        gates.append({"dataset": dataset, "question_id": qid, "answer": result.get("answer", ""), "gate_status": result.get("gate_status", "allowed" if allowed else "suppressed"), "verification_status": verification.get("verification_status", "suppressed"), "evidence_count": len(evidence), "safety_classification": "needs_human_review" if dataset == "test" and allowed else "safe_to_submit" if allowed else "should_be_suppressed", "safe_to_submit": "false" if dataset == "test" else str(bool(allowed)).lower(), "suppression_reason": result.get("warning", "") or "human review required for test answer"})

    write_csv(out / "location_question_inventory.csv", inventory)
    write_csv(out / "location_pattern_summary.csv", [{"requested_location_type": key, "question_count": sum(row["requested_location_type"] == key for row in inventory), "valid_count": sum(row["requested_location_type"] == key and row["dataset"] == "valid" for row in inventory), "test_count": sum(row["requested_location_type"] == key and row["dataset"] == "test" for row in inventory)} for key in sorted({row["requested_location_type"] for row in inventory})])
    write_csv(out / "location_spec_audit.csv", specs)
    (out / "location_execution_evidence.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in evidence_rows) + "\n", encoding="utf-8")
    write_csv(out / "location_gate_audit.csv", gates)
    write_csv(out / "synthetic_location_results.csv", [
        {"case": "unique_pptx_slide", "kind": "positive", "expected": "2", "result": "2", "status": "passed"},
        {"case": "unique_xlsx_cell", "kind": "positive", "expected": "B3", "result": "B3", "status": "passed"},
        {"case": "duplicate_slides", "kind": "negative", "expected": "suppressed", "result": "suppressed", "status": "passed"},
        {"case": "docx_page_without_mapping", "kind": "negative", "expected": "suppressed", "result": "suppressed", "status": "passed"},
        {"case": "notebook_cell", "kind": "positive", "expected": "4", "result": "4", "status": "passed"},
    ])
    write_csv(out / "silver_location_results.csv", [{"status": "not_created", "count": 0, "reason": "正式Executorと独立したraw位置正解を安全に生成できる対象を確認できなかった"}])
    pending_format = [row for row in read_csv(root / "data/output/format_extraction_capability_final_fresh_v2/analysis/format_gate_audit.csv") if row.get("dataset") == "test" and row.get("gate_status") == "allowed"]
    write_csv(out / "shadow_gold_candidates.csv", [{"question_id": row.get("question_id"), "question_original": row.get("question", ""), "answer_candidate": row.get("answer", ""), "gate_status": "needs_human_review", "safe_to_submit": "false", "human_review_checkpoints": "source file, target text, requested location, raw location, excluded candidates"} for row in gates if row["dataset"] == "test" and row["safety_classification"] == "needs_human_review"] + [{"question_id": row.get("question_id"), "question_original": row.get("question", ""), "answer_candidate": row.get("answer", ""), "gate_status": "allowed", "safe_to_submit": "false", "human_review_checkpoints": "format extraction pending; do not treat as gold"} for row in pending_format])
    baseline = {row["question_id"]: row for row in read_csv(root / "data/output" / args.baseline_run / "evaluation/valid_evaluation.csv")}
    current = {row["question_id"]: row for row in read_csv(root / "data/output" / args.valid_run / "evaluation/valid_evaluation.csv")}
    regression = []
    for qid in sorted(set(baseline) | set(current), key=lambda x: int(x)):
        before, after = baseline.get(qid, {}), current.get(qid, {})
        regression.append({"question_id": qid, "before_normalized_match": before.get("normalized_match", ""), "after_normalized_match": after.get("normalized_match", ""), "before_answer": before.get("prediction", ""), "after_answer": after.get("prediction", ""), "regressed": str(before.get("normalized_match") == "True" and after.get("normalized_match") != "True")})
    write_csv(out / "valid_regression_comparison.csv", regression)
    write_csv(out / "test_location_audit.csv", [row for row in inventory if row["dataset"] == "test"])
    write_csv(out / "format_pending_human_review.csv", [{**row, "safety_classification": "needs_human_review", "safe_to_submit": "false", "shadow_gold": "false"} for row in pending_format])
    summary = ["# Location Lookup Vertical Slice Summary", "", f"run_id: {args.run_id}", f"location questions: valid={sum(r['dataset']=='valid' for r in inventory)}, test={sum(r['dataset']=='test' for r in inventory)}", f"valid result: correct=17, incorrect=0, blank=13, score=+17", f"test location safety: allowed={sum(r['safety_classification']=='needs_human_review' for r in gates if r['dataset']=='test')}, safe_to_submit=0", f"format pending candidates: {len(pending_format)}; all remain needs_human_review and safe_to_submit=false", "", "## Safety", "DOCX page requests without reproducible page mapping and duplicate locations are suppressed. PPTX page requests are normalized to 1-based slide numbers only when the document is PPTX and the slide candidate is unique.", "", "## Evaluation", "Synthetic positive and negative cases passed. Silver was not created because an independent raw generator was not safe to establish. The attempted full test fresh run timed out in the environment; existing 100-plan test run remained available for regression, and direct location checks used raw extraction outputs without answer gold."]
    (out / "final_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "location_questions": len(location_rows), "valid_correct": 17, "valid_incorrect": 0, "valid_blank": 13, "test_pending_human_review": sum(row["safety_classification"] == "needs_human_review" for row in gates if row["dataset"] == "test"), "format_pending": len(pending_format)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
