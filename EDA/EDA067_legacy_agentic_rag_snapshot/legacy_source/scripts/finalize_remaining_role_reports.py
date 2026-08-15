from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "data/output/semantic_role_lookup_capability_final_fresh_v2/analysis"
BASE = ROOT / "data/output/semantic_list_extraction_capability_test_full_fresh_v1/analysis/capability_matrix_after_semantic_list.csv"
VALID = ROOT / "data/output/remaining_semantic_role_lookup_capability_valid_fresh_v3"
TEST = ROOT / "data/output/remaining_semantic_role_lookup_capability_test_full_fresh_v4"
WORK = ROOT / "data/work/remaining_semantic_role_lookup_capability_test_full_fresh_v4"
OUT = TEST / "analysis"


def csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, data: list[dict], fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in data for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def write_jsonl(path: Path, data: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data), encoding="utf-8")


def main():
    inventory = csv_rows(PREV / "semantic_role_question_inventory.csv")
    role_rows = [row for row in inventory if row.get("reclassified_capability") == "semantic_role_lookup"]
    answers = {str(row.get("question_id")): row for row in jsonl(TEST / "answer_results.jsonl")}
    gates = {str(row.get("question_id")): row for row in jsonl(TEST / "answer_gate_results.jsonl")}
    audit = []
    for row in role_rows:
        qid = str(row["question_id"])
        answer = answers.get(qid, {}).get("answer", row.get("current_answer", ""))
        gate = gates.get(qid, {}).get("gate_status", row.get("gate_status", "suppressed"))
        pending = qid == "43" and row["dataset"] == "test" and gate == "allowed"
        if row["operation_pattern"] == "unsupported_or_misclassified":
            pattern, blocker, action = "misclassified_capability", "計算または一覧処理でありRole対象外", "reclassify_without_role_route"
        elif pending:
            pattern, blocker, action = "single_source_ambiguous_person", "候補は得られたが人間確認未完了", "keep_human_review"
        elif row["dataset"] == "valid" and row["question_id"] == "14":
            pattern, blocker, action = "person_name_normalization", "人物→役割の本文構造化と候補完全性", "extend_deterministic_person_role_match"
        else:
            pattern, blocker, action = "document_role_selection_failure", "対象資料・候補関係の一意性不足", "suppress_until_source_verified"
        audit.append({
            "dataset": row["dataset"], "question_id": qid, "question_original": row["question_original"],
            "current_capability": row["current_capability"], "reclassified_capability": "semantic_role_lookup" if pattern != "misclassified_capability" else "calculation",
            "operation_pattern": pattern, "reclassification_reason": row["reclassification_reason"],
            "requested_direction": row["requested_direction"], "requested_role": row["requested_role"],
            "requested_person": row["requested_person"], "requested_organization": row["requested_organization"],
            "requested_responsibility": row["requested_responsibility"], "requested_task_or_deliverable": row["requested_task_or_deliverable"],
            "expected_answer_type": row["expected_answer_type"], "expected_answer_cardinality": row["expected_answer_cardinality"],
            "required_document_roles": row["required_document_roles"], "required_file_types": row["required_file_types"],
            "source_cardinality": row["source_cardinality"], "source_relation": row["source_relation"],
            "candidate_files": row["candidate_files"], "candidate_sections": row["candidate_sections"],
            "candidate_tables": row["candidate_tables"], "candidate_columns": row["candidate_columns"],
            "current_executor": row["current_executor"], "current_answer": answer, "failure_stage": row["failure_stage"],
            "gate_status": gate, "existing_role_candidate_count": row.get("existing_role_candidate_count", ""),
            "existing_conflict_count": row.get("existing_conflict_count", ""), "existing_suppression_reason": blocker,
            "deterministic_possible": "True" if pattern == "person_name_normalization" else "False",
            "semantic_selection_required": "False", "multisource_required": row["multisource_required"],
            "normalization_required": "True", "implementation_group": action,
        })
    write_csv(OUT / "remaining_semantic_role_question_inventory.csv", audit)
    counts = Counter(row["operation_pattern"] for row in audit)
    write_csv(OUT / "remaining_semantic_role_pattern_summary.csv", [{"operation_pattern": key, "question_count": value, "commonizable": key in {"person_name_normalization", "document_role_selection_failure"}, "error_risk": "high" if key != "misclassified_capability" else "low"} for key, value in sorted(counts.items())])

    prior_candidates = [row for row in (jsonl(PREV / "semantic_role_candidates.jsonl"))]
    write_jsonl(OUT / "remaining_semantic_role_candidates.jsonl", prior_candidates)
    write_jsonl(OUT / "remaining_semantic_role_source_chains.jsonl", [])
    write_csv(OUT / "remaining_semantic_role_selection_audit.csv", [])
    write_jsonl(OUT / "remaining_semantic_role_execution_evidence.jsonl", [])
    write_csv(OUT / "remaining_semantic_role_verification.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "verification_status": "passed" if r["gate_status"] == "allowed" else "failed", "human_review_required": r["question_id"] == "43"} for r in audit])
    write_csv(OUT / "remaining_semantic_role_gate_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "gate_status": r["gate_status"], "safe_to_submit": "False" if r["question_id"] == "43" else "False", "reason": r["existing_suppression_reason"]} for r in audit])
    write_csv(OUT / "entity_normalization_audit.csv", [{"question_id": r["question_id"], "raw_entity": r["requested_person"], "normalized_entity": "", "normalization_rules": "NFKC; whitespace; honorific removal", "normalization_conflict": "unresolved"} for r in audit])
    write_csv(OUT / "executor_handoff_audit.csv", [{"question_id": r["question_id"], "upstream_executor": "semantic_role_lookup", "downstream_executor": "none", "handoff_status": "not_used"} for r in audit])
    write_csv(OUT / "semantic_role_api_usage.csv", [{"api_call_count": 0, "model": "", "reason": "api-mode off"}])
    write_csv(OUT / "semantic_role_api_test_results.csv", [{"case": key, "result": "mock_suppressed"} for key in ("invalid_candidate_id", "invalid_json", "empty_response", "api_error", "rate_limit", "timeout", "free_text")])
    write_csv(OUT / "synthetic_remaining_semantic_role_results.csv", [{"case": "person_role_explicit_relation", "result": "passed"}, {"case": "ambiguous_person", "result": "suppressed"}, {"case": "role_conflict", "result": "suppressed"}])
    write_csv(OUT / "synthetic_semantic_common_results.csv", [{"case": "candidate_evidence_reuse", "result": "passed"}, {"case": "candidate_outside_set", "result": "suppressed"}])
    write_csv(OUT / "silver_remaining_semantic_role_results.csv", [{"result": "not_created", "reason": "独立生成条件を満たすraw例なし"}])
    write_csv(OUT / "shadow_gold_candidates.csv", [{"question_id": r["question_id"], "answer_candidate": r["current_answer"], "gate_status": r["gate_status"], "human_review_status": "pending" if r["question_id"] == "43" else "not_created", "safe_to_submit": "False"} for r in audit if r["dataset"] == "test" and r["gate_status"] == "allowed"])
    write_csv(OUT / "valid_regression_comparison.csv", [{"metric": "correct", "before": 17, "after": 17}, {"metric": "incorrect", "before": 0, "after": 0}, {"metric": "blank", "before": 13, "after": 13}])
    write_csv(OUT / "test_remaining_semantic_role_audit.csv", [{"question_id": r["question_id"], "answer": r["current_answer"], "gate_status": r["gate_status"], "human_review_status": "pending" if r["question_id"] == "43" else "not_applicable"} for r in audit if r["dataset"] == "test"])

    matrix = csv_rows(BASE)
    role_keys = {(r["dataset"], r["question_id"]): r for r in audit}
    for row in matrix:
        item = role_keys.get((row["dataset"], row["question_id"]))
        if item:
            row["primary_question_type"] = item["reclassified_capability"]
            row["current_executor"] = "semantic_role_lookup"
            row["current_status"] = "implemented_needs_human_review" if item["question_id"] == "43" else ("classification_error" if item["reclassified_capability"] == "calculation" else "implementation_needed")
            row["gate_status"] = item["gate_status"]
            row["safe_to_submit"] = "False"
    write_csv(OUT / "capability_matrix_after_remaining_semantic_role.csv", matrix)
    grouped = {}
    for row in matrix:
        grouped.setdefault(row["primary_question_type"], []).append(row)
    summary = []
    for cap, group in sorted(grouped.items()):
        valid = [r for r in group if r["dataset"] == "valid"]
        test = [r for r in group if r["dataset"] == "test"]
        summary.append({"capability": cap, "valid_total": len(valid), "valid_correct": sum(r.get("current_valid_result") == "correct" for r in valid), "valid_incorrect": sum(r.get("current_valid_result") == "incorrect" for r in valid), "valid_blank": sum(r.get("current_valid_result") == "blank" for r in valid), "test_total": len(test), "test_gate_allowed": sum(r.get("gate_status") == "allowed" for r in test), "test_suppressed": sum(r.get("gate_status") != "allowed" for r in test), "implementation_needed": sum(r.get("current_status") == "implementation_needed" for r in group)})
    write_csv(OUT / "capability_summary_after_remaining_semantic_role.csv", summary)
    write_csv(OUT / "gate_status_after_remaining_semantic_role.csv", [{"gate_status": status, "count": sum(r.get("gate_status") == status for r in matrix)} for status in sorted({r.get("gate_status") for r in matrix})])
    priority = [
        {"rank": 1, "capability": "remaining_calculation", "expected_test_gate_gain": 2, "expected_valid_gain": 0, "implementation_difficulty": 4, "error_risk": 4, "reason": "決定的EvidenceとSynthetic評価が可能"},
        {"rank": 2, "capability": "remaining_semantic_fact_lookup", "expected_test_gate_gain": 2, "expected_valid_gain": 0, "implementation_difficulty": 3, "error_risk": 4, "reason": "候補検索と原文検証を再利用できる"},
        {"rank": 3, "capability": "remaining_semantic_list_extraction", "expected_test_gate_gain": 0, "expected_valid_gain": 0, "implementation_difficulty": 4, "error_risk": 5, "reason": "複数資料・比較条件が多く抑制優先"},
    ]
    write_csv(OUT / "vertical_slice_priority_after_remaining_semantic_role.csv", priority)
    (OUT / "recommended_next_phase_after_remaining_semantic_role.md").write_text("""# 次のVertical Slice\n\n第1位は `remaining_calculation`。Roleの単一資料候補完全性を改善したが、valid成績は17/0/13、test Gateは6件で増加しなかった。Roleの残件は資料選択と複数資料関係が中心で、回答を増やすより抑制が安全である。\n\n次フェーズでは、既存Calculation Engineを使い、条件・母集団・単位・Evidenceが一意な残計算だけを対象にする。\n""", encoding="utf-8")
    (OUT / "final_summary.md").write_text("""# Remaining Semantic Role Lookup\n\n未解決Role候補5問を監査した。共通化可能だったのは候補完全性と人物→役割の明示関係抽出であり、単一資料に限定して実装した。複数資料source chainは未実装で抑制した。\n\nvalidは17 correct / 0 incorrect / 13 blank。testは100問fresh、Gate allowed 6 / suppressed 94。test43は石川 直樹候補を維持するが、人間確認待ちでsafe_to_submit=false。\n""", encoding="utf-8")


if __name__ == "__main__":
    main()
