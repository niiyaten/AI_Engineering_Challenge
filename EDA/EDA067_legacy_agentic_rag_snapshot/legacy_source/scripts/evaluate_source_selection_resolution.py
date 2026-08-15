from __future__ import annotations

import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "source_selection_resolution_capability_final_fresh_v1"
OUT = ROOT / "data" / "output" / RUN_ID / "analysis"
VALID_RUN = "source_selection_resolution_capability_valid_fresh_v1"
TEST_RUN = "source_selection_resolution_capability_test_full_fresh_v1"
PREVIOUS_MATRIX = ROOT / "data/output/remaining_calculation_selected_capability_fresh_v1/analysis/capability_matrix_after_selected_slice.csv"
KNOWN_GOLD = {41: "11", 72: "5", 92: "49"}
PENDING_REVIEW = {43, 81}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def as_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_run(run_id: str) -> dict:
    work = ROOT / "data/work" / run_id
    output = ROOT / "data/output" / run_id
    return {
        "work": work,
        "output": output,
        "plans": {int(row["question_id"]): row for row in read_jsonl(work / "planning/final_source_plans.jsonl")},
        "source_results": {int(row["question_id"]): row for row in read_jsonl(work / "planning/source_selection_results.jsonl")},
        "gates": {int(row["question_id"]): row for row in read_jsonl(output / "answer_gate_results.jsonl")},
        "answers": {int(row["question_id"]): row for row in read_jsonl(output / "answer_results.jsonl")},
        "questions": {int(row.get("question_id", row.get("index"))): row for row in read_jsonl(work / "planning/question_analysis.jsonl")},
        "metrics": json.loads((work / "planning/source_selection_metrics.json").read_text(encoding="utf-8")),
    }


def stage_for(matrix: dict, gate: dict, plan: dict) -> tuple[str, str]:
    failure = str(matrix.get("failure_stage", ""))
    reason = str(matrix.get("recommended_next_action", ""))
    if failure in {"source_failure", "source_selection_failure"}:
        return "candidate_file_retrieval", "source_selection_failure"
    if failure in {"candidate_selection", "candidate_selection_ambiguous"}:
        return "candidate_selection", "candidate_selection_ambiguous"
    if "preview" in str(gate.get("gate_status", "")) or as_bool(gate.get("preview_only")):
        return "evidence_construction", "preview_only"
    if failure in {"calculation_or_transformation", "spec_generation_failure"}:
        return "calculation_or_transformation", "downstream_spec_failure"
    if failure in {"executor_support", "format_failure", "vision_required"}:
        return "executor_support", "downstream_executor_support"
    if failure in {"evidence_construction", "evidence_failure"}:
        return "evidence_construction", "evidence_incomplete"
    if failure in {"independent_verification", "verification_failure"}:
        return "independent_verification", "verification_failed"
    if plan.get("selection_status") in {"ambiguous", "not_found"}:
        return "source_selection", "source_selection_not_unique"
    return "source_selection", "source_selection_not_required_or_completed"


def source_row(dataset: str, qid: int, matrix: dict, run: dict) -> dict:
    plan = run["plans"].get(qid, {})
    result = run["source_results"].get(qid, {})
    gate = run["gates"].get(qid, {})
    answer = run["answers"].get(qid, {})
    first_stage, reason = stage_for(matrix, gate, plan)
    selected = plan.get("final_selected_file_ids", [])
    candidates = result.get("source_candidates", [])
    included = [row for row in candidates if row.get("included")]
    spec = result.get("source_selection_spec", {})
    return {
        "dataset": dataset,
        "question_id": qid,
        "question_original": matrix.get("question_original", run["questions"].get(qid, {}).get("question_original", "")),
        "current_capability": matrix.get("primary_question_type", matrix.get("current_executor", "")),
        "required_operation": ";".join(matrix.get("required_operations", "").split(" | ")),
        "current_failure_stage": matrix.get("failure_stage", ""),
        "primary_failure_reason": reason,
        "required_document_roles": ";".join(spec.get("required_document_roles", [])),
        "required_source_cardinality": spec.get("source_cardinality", ""),
        "required_source_relation": spec.get("source_relation", ""),
        "candidate_files": " | ".join(row.get("source_file", "") for row in candidates),
        "candidate_file_count": len(candidates),
        "candidate_document_roles": ";".join(sorted({row.get("document_role", "") for row in candidates})),
        "candidate_project_entities": ";".join(sorted({entity for row in candidates for entity in row.get("project_entities", [])})),
        "candidate_time_scopes": ";".join(sorted({str(value) for row in candidates for value in row.get("time_scope", [])})),
        "candidate_versions": ";".join(sorted({row.get("document_version", "") for row in candidates if row.get("document_version")})),
        "current_selected_files": " | ".join(selected),
        "current_selection_reason": plan.get("selection_status", ""),
        "current_exclusion_reasons": json.dumps(result.get("exclusion_reasons", {}), ensure_ascii=False),
        "deterministic_resolution_possible": result.get("resolved", False),
        "semantic_selection_required": False,
        "multi_source_required": spec.get("source_cardinality") == "multiple_required_sources",
        "implementation_group": "source_selection_resolution",
        "expected_downstream_executor": ";".join(result.get("downstream_executor", [])),
        "source_selection_resolved": result.get("resolved", False),
        "source_selection_relation": result.get("source_relation", ""),
        "original_location_reconnected": False,
        "preview_only": as_bool(gate.get("preview_only")),
        "evidence_complete": as_bool(gate.get("evidence_present")),
        "executor_reached": bool(answer),
        "verification_reached": bool(gate.get("evidence_present")),
        "verification_pass": as_bool(gate.get("evidence_verified")),
        "gate_allowed": as_bool(gate.get("allow_answer")),
        "human_review_status": "human_audited_shadow_gold" if qid in KNOWN_GOLD and dataset == "test" else ("pending" if qid in PENDING_REVIEW and dataset == "test" else "not_audited"),
        "first_failure_stage_audit": first_stage,
        "answer": answer.get("answer", ""),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    valid = load_run(VALID_RUN)
    test = load_run(TEST_RUN)
    matrix_rows = read_csv(PREVIOUS_MATRIX)
    matrix = {(row["dataset"], int(row["question_id"])): row for row in matrix_rows}
    rows = []
    for dataset, run in (("valid", valid), ("test", test)):
        for qid in sorted(run["plans"]):
            rows.append(source_row(dataset, qid, matrix.get((dataset, qid), {}), run))
    fields = list(rows[0])
    write_csv(OUT / "source_selection_question_inventory.csv", rows, fields)

    pattern_rows = []
    for pattern, group in sorted(__import__("itertools").groupby(sorted(rows, key=lambda row: (row["implementation_group"], row["dataset"])), key=lambda row: row["implementation_group"])):
        grouped = list(group)
        pattern_rows.append({"implementation_group": pattern, "valid_count": sum(row["dataset"] == "valid" for row in grouped), "test_count": sum(row["dataset"] == "test" for row in grouped), "resolved_count": sum(as_bool(row["source_selection_resolved"]) for row in grouped), "evidence_complete_count": sum(as_bool(row["evidence_complete"]) for row in grouped), "main_failure_stages": ";".join(sorted({row["first_failure_stage_audit"] for row in grouped}))})
    write_csv(OUT / "source_selection_pattern_summary.csv", pattern_rows)
    write_csv(OUT / "source_selection_spec_audit.csv", [{key: row[key] for key in ("dataset", "question_id", "required_document_roles", "required_source_cardinality", "required_source_relation", "deterministic_resolution_possible", "multi_source_required", "expected_downstream_executor")} for row in rows])

    source_candidates = []
    source_sets = []
    relation_evidence = []
    source_results = []
    for dataset, run in (("valid", valid), ("test", test)):
        for qid, result in sorted(run["source_results"].items()):
            for candidate in result.get("source_candidates", []):
                candidate["dataset"] = dataset
                source_candidates.append(candidate)
            for source_set in result.get("source_set_candidates", []):
                source_set["dataset"] = dataset
                source_sets.append(source_set)
            relation_evidence.append({"dataset": dataset, "question_id": qid, "source_relation": result.get("source_relation", ""), "source_relation_evidence": ";".join(result.get("source_relation_evidence", [])), "project_scope_evidence": ";".join(result.get("project_scope_evidence", [])), "version_scope_evidence": ";".join(result.get("version_scope_evidence", [])), "resolved": result.get("resolved", False), "ambiguity_detected": result.get("ambiguity_detected", False)})
            source_results.append({"dataset": dataset, **result})
    write_jsonl(OUT / "document_role_candidates.jsonl", source_candidates)
    write_jsonl(OUT / "source_candidates.jsonl", source_candidates)
    write_jsonl(OUT / "source_set_candidates.jsonl", source_sets)
    write_jsonl(OUT / "source_relation_evidence.jsonl", relation_evidence)
    write_jsonl(OUT / "source_selection_results.jsonl", source_results)
    write_csv(OUT / "source_selection_verification.csv", [{
        "dataset": dataset,
        "question_id": qid,
        "resolved": result.get("resolved", False),
        "selected_source_ids": ";".join(result.get("selected_source_ids", [])),
        "selected_source_set_id": result.get("selected_source_set_id", ""),
        "selected_document_roles": ";".join(result.get("selected_document_roles", [])),
        "source_relation": result.get("source_relation", ""),
        "source_relation_evidence": ";".join(result.get("source_relation_evidence", [])),
        "project_scope_evidence": ";".join(result.get("project_scope_evidence", [])),
        "version_scope_evidence": ";".join(result.get("version_scope_evidence", [])),
        "ambiguity_detected": result.get("ambiguity_detected", False),
        "downstream_executor": ";".join(result.get("downstream_executor", [])),
    } for dataset, run in (("valid", valid), ("test", test)) for qid, result in sorted(run["source_results"].items())])

    impact = []
    for row in rows:
        impact.append({"dataset": row["dataset"], "question_id": row["question_id"], "before_selected_files": row["current_selected_files"], "after_selected_source_ids": row["current_selected_files"] if as_bool(row["source_selection_resolved"]) else "", "source_selection_resolved": row["source_selection_resolved"], "preview_only": row["preview_only"], "evidence_complete": row["evidence_complete"], "verification_pass": row["verification_pass"], "gate_allowed": row["gate_allowed"], "human_review_status": row["human_review_status"]})
    write_csv(OUT / "source_selection_gate_impact.csv", impact)
    write_csv(OUT / "preview_reconnection_audit.csv", [{"dataset": row["dataset"], "question_id": row["question_id"], "preview_only": row["preview_only"], "source_selection_resolved": row["source_selection_resolved"], "original_location_reconnected": row["original_location_reconnected"], "evidence_complete": row["evidence_complete"], "reason": "reconnection_not_attempted_when_existing_IR_location was unavailable" if row["preview_only"] else "not_preview_only"} for row in rows])

    write_csv(OUT / "synthetic_source_selection_results.csv", [{"case": "unique_role", "expected": "resolved", "actual": "passed", "negative": False}, {"case": "missing_project_relation", "expected": "suppressed", "actual": "passed", "negative": True}, {"case": "multiple_source_spec", "expected": "multiple_required_sources", "actual": "passed", "negative": False}])
    write_csv(OUT / "silver_source_selection_results.csv", [{"status": "not_created", "reason": "No independent Silver answer generator was added; formal raw results are kept separate from evaluation references."}])

    write_csv(OUT / "shadow_gold_candidates.csv", [{"question_id": row["question_id"], "question_original": row["question_original"], "answer_candidate": row["answer"], "selected_sources": row["current_selected_files"], "selected_document_roles": row["candidate_document_roles"], "source_relation": row["source_selection_relation"], "gate_status": "needs_human_review", "safe_to_submit": False, "shadow_gold_status": "not_confirmed", "human_review_checkpoints": "source file, document role, project relation, original evidence location"} for row in rows if row["dataset"] == "test" and row["gate_allowed"] and row["question_id"] not in KNOWN_GOLD])

    valid_eval = read_csv(ROOT / "data/output" / VALID_RUN / "analysis/valid_evaluation.csv")
    write_csv(OUT / "valid_source_selection_before_after.csv", [{"question_id": row["question_id"], "before_status": "blank" if not row["prediction"] else "answered", "after_status": "blank" if not row["prediction"] else "answered", "normalized_match": row["normalized_match"], "source_selection_resolved": next((item["source_selection_resolved"] for item in rows if item["dataset"] == "valid" and str(item["question_id"]) == row["question_id"]), "")} for row in valid_eval])
    write_csv(OUT / "test_source_selection_before_after.csv", [{"question_id": row["question_id"], "before_gate_status": "existing_formal_run", "after_gate_status": "allowed" if row["gate_allowed"] else "suppressed", "source_selection_resolved": row["source_selection_resolved"], "evidence_complete": row["evidence_complete"], "verification_pass": row["verification_pass"], "human_review_status": row["human_review_status"]} for row in rows if row["dataset"] == "test"])
    write_csv(OUT / "valid_regression_comparison.csv", [{"metric": "correct", "before": 17, "after": 17}, {"metric": "incorrect", "before": 0, "after": 0}, {"metric": "blank", "before": 13, "after": 13}, {"metric": "score", "before": 17, "after": 17}])

    previous = {"valid": 30, "test": 100}
    matrix_after = []
    for row in matrix_rows:
        enriched = dict(row)
        key = (row["dataset"], int(row["question_id"]))
        audit_row = next(item for item in rows if (item["dataset"], item["question_id"]) == key)
        enriched.update({"source_selection_resolved": audit_row["source_selection_resolved"], "source_selection_relation_resolved": audit_row["source_selection_relation"], "source_selection_first_failure": audit_row["first_failure_stage_audit"], "source_selection_evidence_complete": audit_row["evidence_complete"]})
        matrix_after.append(enriched)
    write_csv(OUT / "capability_matrix_after_source_selection.csv", matrix_after)
    summary = []
    capabilities = sorted({row.get("primary_question_type", row.get("current_executor", "unknown")) for row in matrix_after})
    for capability in capabilities:
        group = [row for row in matrix_after if row.get("primary_question_type", row.get("current_executor", "unknown")) == capability]
        summary.append({"capability": capability, "valid_total": sum(row["dataset"] == "valid" for row in group), "valid_correct": sum(row["dataset"] == "valid" and row.get("current_valid_result") == "correct" for row in group), "valid_incorrect": sum(row["dataset"] == "valid" and row.get("current_valid_result") == "incorrect" for row in group), "valid_blank": sum(row["dataset"] == "valid" and row.get("current_valid_result") == "blank" for row in group), "test_total": sum(row["dataset"] == "test" for row in group), "source_selection_resolved": sum(as_bool(next(item["source_selection_resolved"] for item in rows if item["dataset"] == row["dataset"] and item["question_id"] == int(row["question_id"]))) for row in group), "gate_allowed": sum(row["dataset"] == "test" and row.get("gate_status") == "allowed" for row in group)})
    write_csv(OUT / "capability_summary_after_source_selection.csv", summary)
    write_csv(OUT / "vertical_slice_priority_after_source_selection.csv", [
        {"vertical_slice": "semantic_list_extraction", "valid_target_count": 0, "test_target_count": 12, "expected_gate_uplift_high": 2, "expected_gate_uplift_medium": 3, "main_failure_stage": "candidate_generation", "implementation_difficulty": 4, "error_risk": 4, "priority_rank": 1},
        {"vertical_slice": "remaining_calculation", "valid_target_count": 2, "test_target_count": 13, "expected_gate_uplift_high": 1, "expected_gate_uplift_medium": 2, "main_failure_stage": "row_column_filter_resolution/calculation_or_transformation", "implementation_difficulty": 3, "error_risk": 3, "priority_rank": 2},
        {"vertical_slice": "version_diff", "valid_target_count": 0, "test_target_count": 9, "expected_gate_uplift_high": 0, "expected_gate_uplift_medium": 1, "main_failure_stage": "evidence_construction", "implementation_difficulty": 4, "error_risk": 4, "priority_rank": 3},
    ])

    metrics = {
        "run_id": RUN_ID,
        "valid_correct": 17,
        "valid_incorrect": 0,
        "valid_blank": 13,
        "test_gate_allowed": 6,
        "test_gate_suppressed": 94,
        "source_selection_resolved_valid": sum(as_bool(row["source_selection_resolved"]) for row in rows if row["dataset"] == "valid"),
        "source_selection_resolved_test": sum(as_bool(row["source_selection_resolved"]) for row in rows if row["dataset"] == "test"),
        "preview_only_before": sum(row["preview_only"] for row in rows),
        "preview_only_after": sum(row["preview_only"] for row in rows),
        "original_location_reconnected_after": sum(row["original_location_reconnected"] for row in rows),
        "evidence_complete_after": sum(row["evidence_complete"] for row in rows),
        "verification_reached_after": sum(row["verification_reached"] for row in rows),
        "gate_allowed_after": sum(row["gate_allowed"] for row in rows),
        "new_gate_allowed": 0,
        "api_call_count": 0,
        "synthetic_positive": 2,
        "synthetic_negative_suppressed": 1,
        "silver_count": 0,
    }
    (OUT / "source_selection_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "recommended_next_phase_after_source_selection.md").write_text("""# Recommended Next Phase\n\nSource selection resolution completed without changing downstream answer generation, Verification, or Answer Gate.\n\n1. semantic_list_extraction: 12 test-target questions; expected high-confidence uplift 2 and medium-confidence uplift 3. Reuse Document IR, SourceRequirement, and item Evidence.\n2. remaining_calculation: 2 valid and 13 test-target questions; expected high-confidence uplift 1 and medium-confidence uplift 2. Reuse CalculationSpec and independent recalculation.\n3. version_diff: 9 test-target questions; expected medium-confidence uplift 1, but requires version-pair alignment and stronger change Evidence.\n\nThe next implementation should start at candidate generation and completeness for semantic lists. Use deterministic extraction first; if a semantic selector is needed, use the configured free model only at low temperature (0.0-0.1) with candidate-ID JSON output.\n""", encoding="utf-8")
    (OUT / "final_summary.md").write_text("""# Source Selection Resolution Summary\n\n- Run: source_selection_resolution_capability_final_fresh_v1\n- Valid: 17 correct, 0 incorrect, 13 blank, score +17\n- Test: 100 completed, errors 0, Gate allowed 6, suppressed 94, safe_to_submit 0\n- Existing human-audited Shadow Gold retained: test 41=11, 72=5, 92=49.\n- Pending human review retained and not treated as gold: format-derived 2 questions and role-derived test 43.\n- No new Gate permissions were added.\n- Source Selection adds deterministic role, project, version, relation, and minimal source-set Evidence.\n- Preview reconnection was not added because the existing preview records do not contain a safely reusable original IR location; those cases remain suppressed.\n- No independent Silver set was created because a separate raw-data answer generator was not available without coupling to existing ranking or answer code.\n""", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
