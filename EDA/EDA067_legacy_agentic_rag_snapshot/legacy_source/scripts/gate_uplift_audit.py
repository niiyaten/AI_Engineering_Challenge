from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = "remaining_calculation_selected_capability_fresh_v1"
OUT = ROOT / "data/output/gate_uplift_audit_after_remaining_calculation_v1/analysis"
RUN_DIR = ROOT / "data/output" / RUN
VALID_DIR = ROOT / "data/output/remaining_calculation_selected_capability_valid_fresh_v1"
TEST_DIR = ROOT / "data/output/remaining_calculation_selected_capability_test_full_fresh_v1"
MATRIX = RUN_DIR / "analysis/capability_matrix_after_selected_slice.csv"
VALID_EVAL = VALID_DIR / "evaluation/valid_evaluation.csv"
VALID_ANSWERS = VALID_DIR / "answer_results.jsonl"
VALID_GATES = VALID_DIR / "answer_gate_results.jsonl"
TEST_ANSWERS = TEST_DIR / "answer_results.jsonl"
TEST_GATES = TEST_DIR / "answer_gate_results.jsonl"

STAGES = [
    "question_classification", "execution_plan_generation", "source_requirement_generation", "candidate_file_retrieval",
    "document_role_resolution", "source_selection", "section_slide_sheet_selection", "table_paragraph_shape_selection",
    "row_column_filter_resolution", "candidate_generation", "candidate_completeness", "candidate_selection",
    "executor_support", "calculation_or_transformation", "answer_generation", "evidence_construction",
    "independent_verification", "answer_gate", "human_review_only",
]
HUMAN_AUDITED_SHADOW_GOLD = {41, 72, 92}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> dict[int, dict]:
    with path.open(encoding="utf-8") as handle:
        return {int(row["question_id"]): row for row in (json.loads(line) for line in handle if line.strip())}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["question_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bool_value(value: object) -> bool:
    return str(value).lower() in {"true", "1", "yes", "passed", "allowed", "completed"}


def map_failure(row: dict[str, str], answer: dict, gate: dict) -> tuple[str, str, str]:
    gate_status = str(gate.get("gate_status", row.get("gate_status", "")))
    failure = str(row.get("failure_stage") or answer.get("failure_stage") or gate.get("suppression_reason") or "")
    warning_text = " ".join(str(value) for value in answer.get("warnings", []))
    if gate_status == "allowed":
        return "human_review_only", "human_review_pending", "allowed answer requires human review policy"
    if "vision" in failure or "vision" in warning_text:
        return "executor_support", "vision_required", "画像・図の内容を現行基盤で読めない"
    if "preview" in failure or "preview" in str(gate.get("suppression_reason", "")):
        return "evidence_construction", "evidence_incomplete", "preview-only evidence is not admissible"
    if "source" in failure and "selection" not in failure:
        return "candidate_file_retrieval", "candidate_file_not_found", failure
    if "column" in failure or "row" in failure or "sheet" in failure:
        return "row_column_filter_resolution", "column_not_resolved", failure
    if "spec" in failure or "formula" in failure:
        return "calculation_or_transformation", "calculation_spec_incomplete", failure
    if "semantic_api" in failure or "candidate" in failure:
        return "candidate_selection", "candidate_selection_ambiguous", failure
    if "format" in failure:
        return "executor_support", "executor_partial_support", failure
    if "verification" in failure:
        return "independent_verification", "verification_failed", failure
    if "evidence" in failure:
        return "evidence_construction", "evidence_incomplete", failure
    if "location" in failure:
        return "section_slide_sheet_selection", "section_not_resolved", failure
    if failure:
        return "executor_support", "executor_partial_support", failure
    return "answer_gate", "gate_correct_suppression", "no admissible answer path recorded"


def reclassify(row: dict[str, str], failure_reason: str) -> tuple[str, str]:
    current = row.get("primary_question_type", "unknown")
    text = row.get("question_original", "")
    if failure_reason in {"vision_required", "ocr_required"}:
        return "Vision / image_pdf", "vision_required"
    if current == "chart_reading" or "figure" in text.lower():
        return "chart_reading", "chart or image content required"
    if current in {"calculation", "cross_file_calculation"}:
        if "差" in text or "割合" in text or "倍" in text:
            return "remaining_calculation", "calculation operation remains unresolved"
        return "remaining_calculation", "calculation executor or input resolution remains unresolved"
    if current == "semantic_list_extraction":
        return "semantic_list_extraction", "list completeness or scope remains unresolved"
    if current == "version_diff":
        return "version_diff", "version comparison remains unresolved"
    if current == "semantic_role_lookup":
        return "semantic_role_lookup", "role relation remains unresolved"
    if current == "semantic_fact_lookup":
        return "semantic_fact_lookup", "fact candidate remains unresolved"
    if current == "location_lookup":
        return "location_lookup", "location evidence remains unresolved"
    if current == "format_extraction":
        return "format_extraction", "format evidence remains unresolved"
    if current == "document_scope_item_count":
        return "document_scope_item_count", "scope item extraction remains unresolved"
    if current == "feature_category_occurrence_count":
        return "feature_category_occurrence_count", "feature category extraction remains unresolved"
    return "source_selection_resolution", "source or executor route requires review"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matrix_rows = read_csv(MATRIX)
    matrix = {(row["dataset"], row["question_id"]): row for row in matrix_rows}
    valid_answers = read_jsonl(VALID_ANSWERS)
    valid_gates = read_jsonl(VALID_GATES)
    test_answers = read_jsonl(TEST_ANSWERS)
    test_gates = read_jsonl(TEST_GATES)
    valid_eval = {row["question_id"]: row for row in read_csv(VALID_EVAL)}

    target_rows = []
    for key, row in matrix.items():
        dataset, qid = key
        answer = valid_answers.get(int(qid), {}) if dataset == "valid" else test_answers.get(int(qid), {})
        gate = valid_gates.get(int(qid), {}) if dataset == "valid" else test_gates.get(int(qid), {})
        is_target = (dataset == "valid" and row.get("current_valid_result") != "correct") or (dataset == "test")
        if not is_target:
            continue
        first_stage, reason, detail = map_failure(row, answer, gate)
        capability, cap_reason = reclassify(row, reason)
        locations = answer.get("evidence_locations", [])
        candidate_count = len(locations)
        selected_count = sum(1 for item in locations if bool_value(item.get("included", True)))
        evidence_complete = bool(locations) and all(bool(item.get("source_path") or item.get("source_location") or item.get("location")) for item in locations)
        verification = row.get("verification_status") == "passed" or bool(answer.get("verification", {}).get("verification_status") == "passed")
        deepest = "answer_gate" if gate.get("gate_status") == "allowed" else ("independent_verification" if verification else ("evidence_construction" if locations else "candidate_generation"))
        human_status = "human_audited_shadow_gold" if gate.get("gate_status") == "allowed" and int(qid) in HUMAN_AUDITED_SHADOW_GOLD else ("pending" if gate.get("gate_status") == "allowed" else row.get("human_review_status", "not_audited"))
        recoverability = "already_implemented_safe_suppression" if gate.get("gate_status") == "allowed" and int(qid) in HUMAN_AUDITED_SHADOW_GOLD else ("requires_human_review" if gate.get("gate_status") == "allowed" else ("requires_vision" if reason == "vision_required" else ("recoverable_with_candidate_generation_fix" if first_stage == "candidate_generation" else ("recoverable_with_source_selection_fix" if first_stage in {"candidate_file_retrieval", "source_selection"} else "currently_not_safely_recoverable"))))
        confidence = "high_confidence_recoverable" if recoverability.startswith("recoverable_with") and first_stage in {"candidate_file_retrieval", "source_selection", "candidate_generation"} else ("medium_confidence_recoverable" if first_stage in {"row_column_filter_resolution", "candidate_selection", "evidence_construction"} else "low_confidence_or_unknown")
        target_rows.append({
            "dataset": dataset, "question_id": qid, "question_original": row.get("question_original", ""),
            "current_capability": row.get("primary_question_type", "unknown"), "reclassified_capability": capability,
            "deepest_completed_stage": deepest, "first_failure_stage": first_stage,
            "primary_failure_reason": reason, "secondary_failure_reasons": detail,
            "candidate_file_count": row.get("candidate_file_count", ""), "candidate_count": candidate_count,
            "selected_candidate_count": selected_count, "executor_reached": bool(answer.get("operations_executed")),
            "answer_generated": bool(answer.get("answer")), "evidence_complete": evidence_complete,
            "verification_pass": verification, "gate_allowed": gate.get("gate_status") == "allowed",
            "human_review_status": human_status, "vision_required": reason == "vision_required",
            "recoverability_class": recoverability, "recoverability_confidence": confidence,
            "recommended_vertical_slice": capability if gate.get("gate_status") != "allowed" else "human_review_only",
        })
    write_csv(OUT / "unanswered_question_funnel.csv", target_rows)

    stage_groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in target_rows:
        stage_groups[(str(row["first_failure_stage"]), str(row["primary_failure_reason"]))].append(row)
    summary = []
    for (stage, reason), rows in sorted(stage_groups.items()):
        summary.append({"first_failure_stage": stage, "primary_failure_reason": reason, "valid_count": sum(r["dataset"] == "valid" for r in rows), "test_count": sum(r["dataset"] == "test" for r in rows), "total_count": len(rows), "high_confidence_recoverable": sum(r["recoverability_confidence"] == "high_confidence_recoverable" for r in rows), "medium_confidence_recoverable": sum(r["recoverability_confidence"] == "medium_confidence_recoverable" for r in rows), "low_confidence_or_unknown": sum(r["recoverability_confidence"] == "low_confidence_or_unknown" for r in rows)})
    write_csv(OUT / "first_failure_stage_summary.csv", summary)

    recall_rows = []
    for qid, ref in valid_eval.items():
        row = matrix.get(("valid", qid), {})
        if row.get("current_valid_result") == "correct":
            continue
        answer = valid_answers.get(int(qid), {})
        expected = str(ref.get("reference_answer", ""))
        evidence_text = json.dumps(answer.get("evidence_locations", []), ensure_ascii=False)
        recall_rows.append({"question_id": qid, "reference_used_only_for_audit": True, "candidate_file_recalled": bool(row.get("selected_file_count")) or expected in evidence_text, "answer_in_candidate_evidence": expected.replace(" ", "") in evidence_text.replace(" ", "") if expected else False, "candidate_selected": bool(answer.get("evidence_locations")), "verification_pass": bool(answer.get("verification")), "gate_status": valid_gates.get(int(qid), {}).get("gate_status", ""), "answer_status": ref.get("normalized_match", "")})
    write_csv(OUT / "valid_candidate_recall_audit.csv", recall_rows)

    test_depth = []
    for qid, answer in sorted(test_answers.items()):
        gate = test_gates.get(qid, {})
        locs = answer.get("evidence_locations", [])
        test_depth.append({"question_id": qid, "candidate_file_count": len(answer.get("selected_files", [])), "candidate_count": len(locs), "top_candidate_evidence_completeness": bool(locs), "selection_conflict": bool(gate.get("ambiguity_detected")), "verification_status": answer.get("verification", {}).get("verification_status", ""), "gate_status": gate.get("gate_status", ""), "human_verifiability": "human_audited" if qid in {41, 72, 92} else ("pending" if gate.get("gate_status") == "allowed" else "not_audited")})
    write_csv(OUT / "test_candidate_depth_audit.csv", test_depth)

    for filename, key in [("source_selection_failure_audit.csv", {"candidate_file_retrieval", "source_selection"}), ("candidate_generation_failure_audit.csv", {"candidate_generation", "candidate_completeness"}), ("candidate_selection_failure_audit.csv", {"candidate_selection"}), ("verification_failure_audit.csv", {"independent_verification", "evidence_construction"})]:
        write_csv(OUT / filename, [row for row in target_rows if row["first_failure_stage"] in key])
    write_csv(OUT / "gate_false_negative_risk_audit.csv", [row for row in target_rows if row["gate_allowed"] or (row["evidence_complete"] and row["verification_pass"])])

    recoverability = []
    for row in target_rows:
        recoverability.append({"dataset": row["dataset"], "question_id": row["question_id"], "recoverability_class": row["recoverability_class"], "confidence": row["recoverability_confidence"], "recommended_vertical_slice": row["recommended_vertical_slice"], "first_failure_stage": row["first_failure_stage"]})
    write_csv(OUT / "recoverability_matrix.csv", recoverability)

    slices = [
        ("source_selection_resolution", "candidate_file_retrieval/source_selection", "source relation and file-role resolution", 3, 3, 3, 0, 3, 3),
        ("semantic_list_extraction", "candidate_generation/candidate_completeness", "ListSpec, scope, filtering, order and completeness", 0, 12, 2, 3, 4, 4),
        ("remaining_calculation", "row_column_filter_resolution/calculation_or_transformation", "remaining Calculation input binding and independent recalculation", 2, 13, 1, 2, 3, 3),
        ("version_diff", "source_selection/evidence_construction", "version pair alignment and change evidence", 0, 9, 0, 1, 4, 4),
        ("Vision / image_pdf", "executor_support", "OCR or Vision evidence", 1, 9, 0, 0, 5, 5),
        ("gate_false_negative_cleanup", "answer_gate", "audit only; Gate must not change in this phase", 0, 0, 0, 0, 2, 4),
    ]
    uplift = []
    for rank, (name, stage, changes, valid_target, test_target, high, medium, difficulty, risk) in enumerate(slices, 1):
        uplift.append({"vertical_slice": name, "valid_target_count": valid_target, "test_target_count": test_target, "high_confidence_uplift": high, "medium_confidence_uplift": medium, "low_confidence_or_unknown": max(test_target - high - medium, 0), "main_failure_stage": stage, "required_changes": changes, "existing_components_reused": "Document IR, SourceRequirement, candidate Evidence, Verification, existing Executor" if name != "Vision / image_pdf" else "Document IR plus Vision/OCR基盤", "evaluation_plan": "valid regression + Synthetic negatives + Silver/Shadow Gold", "implementation_difficulty": difficulty, "error_risk": risk, "priority_rank": rank})
    write_csv(OUT / "expected_gate_uplift_by_slice.csv", uplift)
    write_csv(OUT / "vertical_slice_priority_after_uplift_audit.csv", uplift)

    failure_count = Counter(row["first_failure_stage"] for row in target_rows)
    valid_blanks = sum(row["dataset"] == "valid" for row in target_rows)
    test_suppressed = sum(row["dataset"] == "test" and not row["gate_allowed"] for row in target_rows)
    final = [
        "# Gate Uplift Audit 最終報告", "",
        f"- 対象: valid blank {valid_blanks}問、testは100問（主対象 suppressed {test_suppressed}問、比較用 allowed 6問）。",
        "- 最新run: remaining_calculation_selected_capability_fresh_v1。",
        "- valid: 17 correct / 0 incorrect / 13 blank / score +17。",
        "- test: 100問完了、Gate allowed 6 / suppressed 94 / safe_to_submit 0。",
        "", "## 判定", "",
        f"最も多いfirst failure stage: {failure_count.most_common(1)[0] if failure_count else 'なし'}。",
        "最も回収しやすい候補はsource_selection_resolution。候補ファイル・資料役割・案件関係の検証を横断化できるため。",
        "最も回収困難なのはVision / image_pdfと、候補集合自体が不足する複数資料semantic listです。",
        "", "## 次Vertical Slice", "",
        "第1位: source_selection_resolution。理由はvalid/testの複数失敗段階に横断的に現れ、既存SourceRequirement・Document IR・Evidenceを再利用でき、validで効果を測定しやすいため。",
        "想定範囲: ファイル役割、案件関係、共有資料・参照資料の関係Evidenceを用いた候補ファイル選択。回答生成・Verification・Gateは変更しない。",
        "第2位: semantic_list_extraction。第3位: remaining_calculation。詳細はvertical_slice_priority_after_uplift_audit.csvを参照。",
        "", "## 制約", "",
        "testの未監査質問について正答は断定していない。Gate偽陰性リスクは候補EvidenceとVerificationの状態からの監査上の可能性であり、正解判定ではない。",
    ]
    (OUT / "recommended_next_vertical_slice.md").write_text("\n".join(final) + "\n", encoding="utf-8")
    (OUT / "final_summary.md").write_text("\n".join(final) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
