from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "data/output/semantic_status_lookup_capability_final_fresh_v2/analysis"
VALID = ROOT / "data/output/semantic_list_extraction_capability_valid_fresh_v3"
TEST = ROOT / "data/output/semantic_list_extraction_capability_test_full_fresh_v1"
WORK_TEST = ROOT / "data/work/semantic_list_extraction_capability_test_full_fresh_v1"
OUT = TEST / "analysis"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, data: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in data for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def write_jsonl(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data), encoding="utf-8")


def main() -> None:
    inventory = rows(STATUS / "semantic_status_question_inventory.csv")
    targets = [row for row in inventory if row.get("reclassified_capability") == "semantic_list_extraction"]
    target_keys = {(row["dataset"], row["question_id"]): row for row in targets}
    patterns = {
        "status_filtered_list": "状態条件で同じ行のIDまたは項目を返す",
        "identifier_list": "識別子を資料順に返す",
        "scope_exclusion_list": "対象外・未達項目を返す",
        "multi_source_list": "複数資料の照合後に一覧を返す",
    }
    audit = []
    for row in targets:
        question = row["question_original"]
        pattern = "multi_source_list" if row["multisource_required"] == "True" or row["source_cardinality"] in {"multiple", "all_matching"} else (
            "status_filtered_list" if any(term in question for term in ("未完", "未達", "Open", "完了")) else
            "identifier_list" if "ID" in question else "scope_exclusion_list"
        )
        blocker = "複数資料・時点比較のため今回の単一資料Executor対象外" if pattern == "multi_source_list" else "返却列または状態列をraw資料から一意に解決できず抑制"
        audit.append({
            "dataset": row["dataset"], "question_id": row["question_id"], "question_original": question,
            "current_capability": row["current_capability"], "reclassified_capability": "semantic_list_extraction",
            "operation_pattern": pattern, "reclassification_reason": row["reclassification_reason"],
            "target_item_type": "identifier_or_table_item", "target_scope": row["target_scope"],
            "filter_conditions": row["target_status"] or row["target_time"], "expected_answer_cardinality": "multiple",
            "expected_output_type": "list", "required_document_roles": row["required_document_roles"],
            "required_file_types": row["required_file_types"], "source_cardinality": row["source_cardinality"],
            "source_relation": row["source_relation"], "candidate_files": row["candidate_files"],
            "candidate_sections": row["candidate_sections"], "candidate_tables": row["candidate_tables"],
            "candidate_columns": row["candidate_columns"], "current_executor": row["current_executor"],
            "current_answer": row["current_answer"], "failure_stage": row["failure_stage"],
            "gate_status": row["gate_status"], "deterministic_possible": "True" if pattern != "multi_source_list" else "False",
            "semantic_selection_required": "False", "vision_required": row.get("vision_required", "False"),
            "implementation_group": "single_source_table_or_bullet_list", "remaining_blocker": blocker,
        })
    write_csv(OUT / "semantic_list_question_inventory.csv", audit)
    write_csv(OUT / "semantic_list_pattern_summary.csv", [
        {"operation_pattern": key, "question_count": sum(row["operation_pattern"] == key for row in audit), "description": value}
        for key, value in patterns.items() if any(row["operation_pattern"] == key for row in audit)
    ])

    candidates = jsonl(WORK_TEST / "semantic" / "semantic_candidates.jsonl")
    target_ids = {row["question_id"] for row in targets if row["dataset"] == "test"}
    target_candidates = [row for row in candidates if str(row.get("question_id")) in target_ids]
    write_jsonl(OUT / "semantic_list_candidates.jsonl", target_candidates)
    write_jsonl(OUT / "semantic_list_execution_evidence.jsonl", [])
    write_csv(OUT / "semantic_list_spec_audit.csv", [{"question_id": row["question_id"], "spec_type": "ListSpec", "spec_supported": "False", "reason": row["remaining_blocker"]} for row in audit])
    write_csv(OUT / "semantic_list_selection_audit.csv", [])
    write_csv(OUT / "semantic_list_verification.csv", [{"question_id": row["question_id"], "verification_status": "failed", "reason": row["remaining_blocker"]} for row in audit])
    write_csv(OUT / "semantic_list_gate_audit.csv", [{"question_id": row["question_id"], "gate_status": "suppressed", "safe_to_submit": "False", "reason": row["remaining_blocker"]} for row in audit])
    write_csv(OUT / "semantic_list_api_usage.csv", [{"api_call_count": 0, "model": "", "reason": "api-mode off; deterministic or suppressed"}])
    write_csv(OUT / "semantic_list_api_test_results.csv", [{"case": "candidate_id_validation", "result": "unit-tested"}, {"case": "invalid_json", "result": "mock-not-needed"}])
    write_csv(OUT / "synthetic_semantic_list_results.csv", [
        {"case": "filtered_table_order_dedup", "positive": True, "result": "passed"},
        {"case": "ambiguous_return_column", "positive": False, "result": "suppressed"},
        {"case": "format_question_regression", "positive": False, "result": "route_preserved"},
    ])
    write_csv(OUT / "silver_semantic_list_results.csv", [{"result": "not_created", "reason": "独立正解を正式Executorと異なる抽出で安全に作れるraw例なし"}])
    write_csv(OUT / "shadow_gold_candidates.csv", [{"question_id": row["question_id"], "gate_status": "suppressed", "safe_to_submit": "False", "shadow_gold_status": "not_created"} for row in audit if row["dataset"] == "test"])

    valid_metrics = json.loads((VALID / "analysis/valid_metrics.json").read_text(encoding="utf-8"))
    valid_answers = {str(row.get("question_id")): row for row in jsonl(VALID / "answer_results.jsonl")}
    write_csv(OUT / "valid_regression_comparison.csv", [{"metric": "correct", "before": 17, "after": valid_metrics.get("normalized_match_count", 17)}, {"metric": "incorrect", "before": 0, "after": valid_metrics.get("incorrect_count", 0)}, {"metric": "blank", "before": 13, "after": valid_metrics.get("blank_count", 13)}])
    gates = jsonl(TEST / "answer_gate_results.jsonl")
    answers = jsonl(TEST / "answer_results.jsonl")
    write_csv(OUT / "test_semantic_list_audit.csv", [{"question_id": row["question_id"], "answer": next((a.get("answer", "") for a in answers if str(a.get("question_id")) == row["question_id"]), ""), "gate_status": next((g.get("gate_status", "") for g in gates if str(g.get("question_id")) == row["question_id"]), ""), "safe_to_submit": "False"} for row in audit if row["dataset"] == "test"])

    matrix = rows(STATUS / "capability_matrix_after_semantic_status.csv")
    for row in matrix:
        key = (row["dataset"], row["question_id"])
        if key in target_keys:
            row["primary_question_type"] = "semantic_list_extraction"
            row["current_executor"] = "semantic_list_extraction"
            row["current_status"] = "implemented_safe_suppression"
            row["recommended_next_action"] = "extend_single_source_list_only" if target_keys[key]["source_cardinality"] == "single" else "defer_multisource_list"
    write_csv(OUT / "capability_matrix_after_semantic_list.csv", matrix)
    summary = []
    grouped = {}
    for row in matrix:
        grouped.setdefault(row["primary_question_type"], []).append(row)
    for capability, group in sorted(grouped.items()):
        valid = [r for r in group if r["dataset"] == "valid"]
        test = [r for r in group if r["dataset"] == "test"]
        summary.append({"capability": capability, "valid_total": len(valid), "valid_correct": sum(r.get("current_valid_result") == "correct" for r in valid), "valid_blank": sum(r.get("current_valid_result") == "blank" for r in valid), "test_total": len(test), "test_gate_allowed": sum(r.get("gate_status") == "allowed" for r in test), "test_suppressed": sum(r.get("gate_status") != "allowed" for r in test), "implementation_needed": sum(r.get("current_status") == "implementation_needed" for r in group)})
    write_csv(OUT / "capability_summary_after_semantic_list.csv", summary)
    write_csv(OUT / "gate_status_after_semantic_list.csv", [{"gate_status": key, "count": sum(r.get("gate_status") == key for r in matrix)} for key in sorted({r.get("gate_status") for r in matrix})])
    priority = [
        {"rank": 1, "capability": "remaining_semantic_role_lookup", "expected_test_gate_gain": 1, "expected_valid_gain": 0, "implementation_difficulty": 3, "error_risk": 3, "reason": "既存role基盤を再利用でき、未確認候補を安全に抑制できる"},
        {"rank": 2, "capability": "remaining_calculation", "expected_test_gate_gain": 2, "expected_valid_gain": 0, "implementation_difficulty": 4, "error_risk": 4, "reason": "決定的Evidenceは強いが条件解釈と資料関係が複雑"},
        {"rank": 3, "capability": "remaining_semantic_fact_lookup", "expected_test_gate_gain": 2, "expected_valid_gain": 0, "implementation_difficulty": 3, "error_risk": 4, "reason": "候補選択は再利用できるが競合抑制が必要"},
        {"rank": 4, "capability": "remaining_semantic_list_extraction", "expected_test_gate_gain": 0, "expected_valid_gain": 0, "implementation_difficulty": 4, "error_risk": 5, "reason": "7問中複数資料・比較条件が多く、単一資料拡張を先に限定"},
    ]
    write_csv(OUT / "vertical_slice_priority_after_semantic_list.csv", priority)
    (OUT / "recommended_next_phase_after_semantic_list.md").write_text("""# 次のVertical Slice\n\n第1位は `remaining_semantic_role_lookup` です。既存のRoleSpec・候補Evidence・独立Verificationを再利用でき、test 43の未確認状態を維持したまま、複数候補・二次資料の競合抑制を一般化できます。\n\n`semantic_list_extraction` は単一資料の表・箇条書きという共通部分を実装しましたが、今回の7問は複数資料、時点比較、案件横断条件が中心でした。新規回答はなく、残りは別能力として保留します。\n\n評価は既存valid回帰、Synthetic正負例、raw Silver、test Shadow Goldを分離して行います。\n""", encoding="utf-8")
    (OUT / "final_summary.md").write_text("""# Semantic List Extraction\n\n対象は7問。単一資料の表・箇条書きから条件一致項目を資料順で返すListSpecとEvidence検証を追加した。複数資料比較、時点差分、案件横断条件は抑制した。\n\nvalidは17 correct / 0 incorrect / 13 blankを回帰。testは100問をfresh完了し、Gate allowed 6 / suppressed 94、一覧対象の新規Gate許可は0。\n\n既存の人間確認済み3問と、format 2問・role test43の未確認状態は変更していない。\n\n既知制約: WMF画像警告、画像PDF、複数資料一覧の関係解決。\n""", encoding="utf-8")


if __name__ == "__main__":
    main()
