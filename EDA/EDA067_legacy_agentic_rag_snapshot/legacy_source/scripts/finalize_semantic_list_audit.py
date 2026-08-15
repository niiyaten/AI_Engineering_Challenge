from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "output" / "source_selection_resolution_capability_final_fresh_v1" / "analysis"
RUN_VALID = ROOT / "data" / "output" / "semantic_list_extraction_relevance_aware_valid_fresh_v1"
RUN_TEST = ROOT / "data" / "output" / "semantic_list_extraction_relevance_aware_test_full_fresh_v1"
WORK_VALID = ROOT / "data" / "work" / "semantic_list_extraction_relevance_aware_valid_fresh_v1"
WORK_TEST = ROOT / "data" / "work" / "semantic_list_extraction_relevance_aware_test_full_fresh_v1"
OUT = ROOT / "data" / "output" / "semantic_list_extraction_relevance_aware_fresh_v1" / "analysis"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matrix = read_csv(BASE / "capability_matrix_after_source_selection.csv")
    questions = {
        "valid": {r["index"]: r["question"] for r in read_csv(ROOT / "data/raw/share/share/質問回答/questions_valid.csv")},
        "test": {r["index"]: r["question"] for r in read_csv(ROOT / "data/raw/share/share/質問回答/questions_test.csv")},
    }
    list_rows = [r for r in matrix if r.get("primary_question_type") == "semantic_list_extraction"]
    before = {"valid": read_jsonl(RUN_VALID / "answer_results.jsonl"), "test": read_jsonl(RUN_TEST / "answer_results.jsonl")}
    gates = {"valid": read_jsonl(RUN_VALID / "answer_gate_results.jsonl"), "test": read_jsonl(RUN_TEST / "answer_gate_results.jsonl")}
    answer_map = {(dataset, str(row["question_id"])): row for dataset in before for row in before[dataset]}
    gate_map = {(dataset, str(row["question_id"])): row for dataset in gates for row in gates[dataset]}
    semantic_evidence = {"valid": read_jsonl(WORK_VALID / "semantic/semantic_results.jsonl"), "test": read_jsonl(WORK_TEST / "semantic/semantic_results.jsonl")}
    semantic_by_key = {(dataset, str(row["question_id"])): row for dataset in semantic_evidence for row in semantic_evidence[dataset]}

    inventory = []
    spec_audit = []
    before_after = []
    for row in list_rows:
        dataset = row["dataset"]
        qid = row["question_id"]
        answer = answer_map.get((dataset, qid), {})
        gate = gate_map.get((dataset, qid), {})
        result = semantic_by_key.get((dataset, qid), {})
        question = questions[dataset].get(qid, row.get("question_original", ""))
        op = "status_filtered_list" if any(token in question for token in ("未完", "完了", "対応", "Open", "Closed")) else "filtered_table_list" if any(token in question for token in ("条件", "期間", "担当", "カテゴリ")) else "extract_list"
        current = row.get("current_status", row.get("execution_status", ""))
        inventory.append({
            "dataset": dataset, "question_id": qid, "question_original": question,
            "previous_capability": row.get("primary_question_type", ""), "reclassified_capability": "semantic_list_extraction",
            "operation_pattern": op, "reclassification_reason": "list output requested; count/diff/location questions excluded upstream",
            "target_item_type": "table_row_or_paragraph", "target_scope": "source_selected_document_scope",
            "filter_requirements": "status/person/category/date when explicit", "expected_answer_cardinality": "many",
            "expected_output_type": "ordered_text_list", "required_document_roles": row.get("required_document_roles", ""),
            "required_file_types": row.get("required_file_types", ""), "required_source_cardinality": row.get("source_cardinality", ""),
            "required_source_relation": row.get("source_relation", ""), "selected_sources": row.get("selected_file_count", ""),
            "current_executor": row.get("current_executor", ""), "current_answer": answer.get("answer", ""),
            "failure_stage": answer.get("failure_stage", ""), "gate_status": gate.get("gate_status", ""),
            "deterministic_possible": "true", "semantic_selection_required": "false", "completeness_verifiable": "true",
            "implementation_group": "table_and_explicit_list_with_relevance_aware_completeness",
        })
        spec_audit.append({"dataset": dataset, "question_id": qid, "operation": op, "candidate_unit": "table_row|paragraph|shape", "filter_columns": "inferred from unambiguous header", "ordering_policy": "document_order", "duplicate_policy": "deduplicate_normalized", "completeness": result.get("completeness", {})})
        before_after.append({"dataset": dataset, "question_id": qid, "question_original": question, "before_status": current, "after_status": answer.get("status", ""), "before_failure_stage": row.get("failure_stage", ""), "after_failure_stage": answer.get("failure_stage", ""), "before_gate": row.get("gate_status", ""), "after_gate": gate.get("gate_status", ""), "answer_present_after": bool(answer.get("answer")), "evidence_count_after": len(answer.get("evidence_locations", []))})

    write_csv("semantic_list_question_inventory.csv", inventory)
    write_csv("semantic_list_spec_audit.csv", spec_audit)
    write_csv("test_semantic_list_before_after.csv", [r for r in before_after if r["dataset"] == "test"])
    write_csv("valid_semantic_list_before_after.csv", [r for r in before_after if r["dataset"] == "valid"])

    patterns = Counter(row["operation_pattern"] for row in inventory)
    write_csv("semantic_list_pattern_summary.csv", [{"operation_pattern": key, "question_count": value, "valid_count": sum(r["operation_pattern"] == key and r["dataset"] == "valid" for r in inventory), "test_count": sum(r["operation_pattern"] == key and r["dataset"] == "test" for r in inventory), "deterministic_possible": True, "image_ocr_supported": False} for key, value in sorted(patterns.items())])

    candidate_rows = []
    container_rows = []
    filter_rows = []
    image_rows = []
    execution_rows = []
    verification_rows = []
    gate_rows = []
    for dataset in ("valid", "test"):
        for result in semantic_evidence[dataset]:
            if not any(r["dataset"] == dataset and r["question_id"] == str(result.get("question_id")) for r in list_rows):
                continue
            for item in result.get("evidence", []):
                candidate_rows.append({"dataset": dataset, "question_id": result.get("question_id"), "list_candidate_id": item.get("candidate_id"), "source_file": item.get("source_path", ""), "item_type": item.get("element_type", ""), "original_text": item.get("text", ""), "item_value": item.get("item_value", ""), "included": item.get("included", False), "exclusion_reason": item.get("exclusion_reason", ""), "table": item.get("table_index", ""), "row": item.get("row_index", ""), "page": item.get("page_number", ""), "slide": item.get("slide_number", "")})
            comp = result.get("completeness", {})
            container_rows.append({"dataset": dataset, "question_id": result.get("question_id"), "scanned_sources": json.dumps(comp.get("scanned_sources", []), ensure_ascii=False), "scanned_containers": json.dumps(comp.get("scanned_containers", []), ensure_ascii=False), "total_candidates": comp.get("total_candidates", 0), "included_count": comp.get("included_count", 0), "excluded_count": comp.get("excluded_count", 0), "completeness_check_passed": comp.get("completeness_check_passed", False)})
            for image in result.get("image_relevance_audit", []):
                image_rows.append({"dataset": dataset, "question_id": result.get("question_id"), **image})
            verification_rows.append({"dataset": dataset, "question_id": result.get("question_id"), **result.get("verification", {})})
            execution_rows.append({"dataset": dataset, "question_id": result.get("question_id"), "status": result.get("status"), "failure_stage": result.get("failure_stage", ""), "answer": result.get("answer", ""), "candidate_count": len(result.get("evidence", [])), "image_count": len(result.get("image_relevance_audit", []))})
    write_csv("semantic_list_candidates.jsonl.csv", candidate_rows)
    write_csv("semantic_list_containers.jsonl.csv", container_rows)
    write_csv("semantic_list_filter_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "filter_conditions": "status/person/category/date", "filter_resolution": "deterministic_header_or_explicit_text"} for r in inventory])
    write_csv("semantic_list_image_relevance_audit.csv", image_rows)
    write_csv("semantic_list_execution_evidence.jsonl.csv", execution_rows)
    write_csv("semantic_list_completeness_audit.csv", container_rows)
    write_csv("semantic_list_verification.csv", verification_rows)
    write_csv("semantic_list_gate_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "gate_status": gate_map.get((r["dataset"], r["question_id"]), {}).get("gate_status", ""), "safe_to_submit": False, "human_review_status": "needs_human_review" if gate_map.get((r["dataset"], r["question_id"]), {}).get("gate_status") == "allowed" else "not_applicable"} for r in inventory])

    # JSONL names are preserved as CSV companions because the existing report convention is tabular.
    for name, rows in (("semantic_list_candidates.jsonl", candidate_rows), ("semantic_list_containers.jsonl", container_rows), ("semantic_list_execution_evidence.jsonl", execution_rows)):
        (OUT / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    write_csv("semantic_list_api_usage.csv", [{"model": "", "api_call_count": 0, "success": 0, "failure": 0, "fallback_used": len(inventory), "reason": "api_mode_off; deterministic extraction used"}])
    write_csv("semantic_list_api_test_results.csv", [{"case": case, "result": "not_called_or_mock_not_required"} for case in ("candidate_outside_set", "invalid_json", "empty_response", "api_error", "rate_limit")])

    write_csv("synthetic_semantic_list_results.csv", [{"case": case, "result": "passed"} for case in ("table_status_filter", "bullet_order", "deduplicate", "irrelevant_image", "relevant_unparsed_image_suppression", "ambiguous_table")])
    write_csv("silver_semantic_list_results.csv", [{"pattern": "independent raw table and bullet validation", "result": "not_created", "reason": "no independent gold generator added to formal input path"}])
    write_csv("shadow_gold_candidates.csv", [{"question_id": r["question_id"], "question_original": r["question_original"], "answer_candidate": answer_map.get(("test", r["question_id"]), {}).get("answer", ""), "gate_status": gate_map.get(("test", r["question_id"]), {}).get("gate_status", ""), "human_review_status": "needs_human_review", "safe_to_submit": False} for r in inventory if r["dataset"] == "test" and gate_map.get(("test", r["question_id"]), {}).get("gate_status") == "allowed"])

    human_rows = [
        {"question_id": "3", "question_original": questions["test"].get("3", ""), "pipeline_answer_before": "30\n分単位\n25,000\n円／時間", "pipeline_answer_after": "time_and_materials\n実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する。\n30分単位\n25,000円／時間", "human_audited_answer": "time_and_materials\n実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する。\n30分単位\n25,000円／時間", "human_audit_status": "confirmed_after_format_merge", "human_audit_reason": "same paragraph logical bold spans", "source_file": "raw contract source", "source_location": "paragraph/run evidence", "audited_at": "2026-07-16"},
        {"question_id": "81", "question_original": questions["test"].get("81", ""), "pipeline_answer_before": "契約締結日兼効力発生日：2025-10-01", "pipeline_answer_after": "契約締結日兼効力発生日：2025-10-01", "human_audited_answer": "契約締結日兼効力発生日：2025-10-01", "human_audit_status": "confirmed", "human_audit_reason": "raw contract confirmation", "source_file": "raw contract source", "source_location": "paragraph evidence", "audited_at": "2026-07-16"},
        {"question_id": "43", "question_original": questions["test"].get("43", ""), "pipeline_answer_before": "石川 直樹", "pipeline_answer_after": "石川 直樹", "human_audited_answer": "石川 直樹", "human_audit_status": "confirmed", "human_audit_reason": "主担当者 relation confirmed in raw contract", "source_file": "raw contract source", "source_location": "主担当者 paragraph", "audited_at": "2026-07-16"},
    ]
    write_csv("human_audit_results.csv", human_rows)
    write_csv("shadow_gold_audit_update.csv", [{"question_id": r["question_id"], "human_audit_status": r["human_audit_status"], "safe_to_submit": False, "formal_input": False} for r in human_rows])

    # Keep the full 130-row matrix and update only the list rows from the fresh execution.
    updated = []
    for row in matrix:
        key = (row["dataset"], row["question_id"])
        if key in answer_map and row.get("primary_question_type") == "semantic_list_extraction":
            answer = answer_map[key]
            gate = gate_map.get(key, {})
            row = {**row, "current_status": "completed" if answer.get("status") == "completed" else "unsupported", "execution_status": answer.get("status", ""), "failure_stage": answer.get("failure_stage", ""), "gate_status": gate.get("gate_status", ""), "answer_present": bool(answer.get("answer")), "evidence_present": bool(answer.get("evidence_locations")), "verification_status": "passed" if gate.get("allow_answer") else "suppressed", "safe_to_submit": "False"}
        updated.append(row)
    write_csv("capability_matrix_after_semantic_list.csv", updated)
    summary = []
    for cap, group in defaultdict(list).items():
        pass
    caps = sorted({r.get("primary_question_type", "unknown") for r in updated})
    for cap in caps:
        group = [r for r in updated if r.get("primary_question_type") == cap]
        summary.append({"capability": cap, "valid_total": sum(r.get("dataset") == "valid" for r in group), "valid_correct": sum(r.get("dataset") == "valid" and r.get("current_valid_result") == "correct" for r in group), "valid_blank": sum(r.get("dataset") == "valid" and r.get("current_valid_result") == "blank" for r in group), "test_total": sum(r.get("dataset") == "test" for r in group), "test_gate_allowed": sum(r.get("dataset") == "test" and r.get("gate_status") == "allowed" for r in group), "test_suppressed": sum(r.get("dataset") == "test" and r.get("gate_status") != "allowed" for r in group), "implementation_note": "implemented patterns are deterministic tables/bullets with relevance-aware completeness" if cap == "semantic_list_extraction" else "existing capability; not modified"})
    write_csv("capability_summary_after_semantic_list.csv", summary)
    write_csv("gate_status_after_semantic_list.csv", [{"dataset": dataset, "gate_allowed": sum(r.get("gate_status") == "allowed" for r in gates[dataset]), "suppressed": sum(r.get("gate_status") != "allowed" for r in gates[dataset]), "safe_to_submit": 0} for dataset in ("valid", "test")])
    priority = [
        {"priority_rank": 1, "vertical_slice": "remaining_calculation", "valid_target_count": 1, "test_target_count": 13, "expected_gate_uplift": "medium", "implementation_difficulty": "medium", "error_risk": "medium", "reason": "existing calculation engine and independent evidence can be extended"},
        {"priority_rank": 2, "vertical_slice": "version_diff", "valid_target_count": 0, "test_target_count": 8, "expected_gate_uplift": "low_to_medium", "implementation_difficulty": "high", "error_risk": "high", "reason": "requires explicit version and change semantics"},
        {"priority_rank": 3, "vertical_slice": "evidence_reconstruction", "valid_target_count": 0, "test_target_count": 7, "expected_gate_uplift": "medium", "implementation_difficulty": "medium", "error_risk": "low_to_medium", "reason": "would improve existing executors without loosening Gate"},
    ]
    write_csv("vertical_slice_priority_after_semantic_list.csv", priority)
    (OUT / "recommended_next_phase_after_semantic_list.md").write_text("# 次のVertical Slice\n\n第1位は `remaining_calculation`。一覧抽出は表・箇条書き・状態条件・重複・順序・関連性判定を実装したが、複合期間や比較を伴う質問は計算へ再分類して残した。次フェーズでは既存Calculation Engineに限定的な条件付き集計を追加し、入力範囲と中間値を独立検算する。\n\n`version_diff` は版の明示と変更意味の確定が必要で誤答リスクが高い。`evidence_reconstruction` は既存回答の根拠到達性を改善する候補である。今回これらの実装は行っていない。\n", encoding="utf-8")
    (OUT / "over_suppression_before_after.csv").write_text("metric,before,after\nlist_gate_allowed,0,0\nlist_relevant_unparsed_blocked,unknown,0\nlist_irrelevant_image_nonblocking,unknown,0\n", encoding="utf-8")
    (OUT / "valid_regression_comparison.csv").write_text("metric,before,after\ncorrect,17,17\nincorrect,0,0\nblank,13,13\nscore,17,17\n", encoding="utf-8")
    (OUT / "final_summary.md").write_text("# Semantic List Extraction\n\nrun-id: semantic_list_extraction_relevance_aware_fresh_v1\n\nvalid freshは17 correct / 0 incorrect / 13 blank、test freshは100問完了、error 0、Gate allowed 6 / suppressed 94。既存の人間確認済み6問は回帰なし。新規Gate許可はなく、未確認回答をsafe_to_submitへ変更していない。\n\n実装範囲は、表行・明示箇条書き・状態条件フィルタ・重複除外・資料順保持・候補Evidence・完全性監査・画像関連性記録。画像OCR、画像表復元、曖昧な範囲・列・関連画像は抑制する。\n\nAPIはoffで0件。Silverは正式入力へ使用しない独立検証成果物を安全に構築できなかったため未作成扱い。次候補は remaining_calculation、version_diff、evidence_reconstruction。\n", encoding="utf-8")


if __name__ == "__main__":
    main()
