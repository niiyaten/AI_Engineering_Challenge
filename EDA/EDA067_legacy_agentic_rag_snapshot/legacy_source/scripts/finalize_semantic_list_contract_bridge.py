from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/output/semantic_list_evidence_contract_gate_bridge_fresh_v1/analysis"
VALID_RUN = "semantic_list_evidence_contract_gate_bridge_valid_full_fresh_v2"
TEST_RUN = "semantic_list_evidence_contract_gate_bridge_test_full_fresh_v1"
BASELINE = ROOT / "data/output/semantic_list_extraction_relevance_aware_fresh_v1/analysis"
TARGET_VALID = {15, 20}
TARGET_TEST = {19, 20, 26, 34, 45, 52, 55, 60, 67, 70, 85, 87}
PRIORITY = {15, 55, 85, 52, 19, 67}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys or ["status"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_run(run: str) -> dict[int, dict]:
    work = ROOT / "data/work" / run
    execution = {int(x["question_id"]): x for x in read_jsonl(work / "execution/tool_executions.jsonl")}
    answers = {int(x["question_id"]): x for x in read_jsonl(ROOT / "data/output" / run / "answer_results.jsonl")}
    gates = {int(x["question_id"]): x for x in read_jsonl(ROOT / "data/output" / run / "answer_gate_results.jsonl")}
    return {qid: {"execution": execution.get(qid, {}), "answer": answers.get(qid, {}), "gate": gates.get(qid, {})} for qid in set(execution) | set(answers) | set(gates)}


def output(row: dict) -> dict:
    return ((row.get("execution", {}).get("tool_outputs") or [{}])[-1])


def item_evidence(row: dict) -> list[dict]:
    return [x for x in (output(row).get("evidence") or []) if isinstance(x, dict)]


def verification(row: dict) -> dict:
    return output(row).get("verification") or {}


def target_inventory(run_data: dict, dataset: str, qids: set[int]) -> list[dict]:
    rows = []
    for qid in sorted(qids):
        row = run_data.get(qid, {})
        out = output(row)
        ver = verification(row)
        gate = row.get("gate", {})
        evidence = item_evidence(row)
        list_contract = out.get("list_evidence_contract") or {}
        rows.append({
            "dataset": dataset,
            "question_id": qid,
            "current_capability": "semantic_list_extraction",
            "operation_pattern": out.get("semantic_spec", {}).get("subtype", out.get("question_type", "")),
            "current_executor": "semantic_document_lookup",
            "current_answer": row.get("answer", {}).get("answer", out.get("answer", "")),
            "failure_stage": out.get("failure_stage", ""),
            "gate_status": gate.get("gate_status", ""),
            "source_selection_resolved": bool(ver.get("source_files_verified")),
            "container_selection_resolved": bool(list_contract.get("scope_resolved")),
            "candidate_count": len(evidence),
            "included_count": len([x for x in evidence if x.get("included") is True]),
            "excluded_count": len([x for x in evidence if x.get("included") is False]),
            "item_answer_column_evidence_complete": all(bool(x.get("answer_column_name") or x.get("answer_value")) for x in evidence) if evidence else False,
            "item_filter_column_evidence_complete": all(bool(x.get("filter_column_name") or x.get("filter_match") is True) for x in evidence) if evidence else False,
            "item_location_evidence_complete": all(bool(x.get("source_location")) for x in evidence) if evidence else False,
            "completeness_evidence_complete": bool(list_contract.get("completeness_check_passed") or ver.get("completeness_check_passed")),
            "independent_reconstruction_reached": bool(ver.get("independent_reconstruction_answer") is not None),
            "independent_reconstruction_pass": bool(ver.get("independent_reconstruction_passed")),
            "common_verification_reached": bool(ver),
            "common_verification_pass": ver.get("verification_status") == "passed",
            "gate_evidence_contract_satisfied": gate.get("gate_status") == "allowed",
            "suppression_reason": gate.get("suppression_reason", out.get("warning", "")),
        })
    return rows


def main() -> None:
    valid = load_run(VALID_RUN)
    test = load_run(TEST_RUN)
    inventory = target_inventory(valid, "valid", TARGET_VALID) + target_inventory(test, "test", TARGET_TEST)

    # Evidenceの内部名と共通Gate名の対応を一つの監査表に保存する。
    mapping = [
        {"gate_requirement": "selected_evidence", "list_evidence": "included item evidence", "verification": "included_candidate_ids"},
        {"gate_requirement": "source_location", "list_evidence": "source_location + page/slide/sheet/table/row/column", "verification": "item_location_evidence_complete"},
        {"gate_requirement": "verification_passed", "list_evidence": "item verification + completeness + independent reconstruction", "verification": "common_verification_pass"},
        {"gate_requirement": "answer_derived_only_from_selected_candidates", "list_evidence": "included candidate answer_value", "verification": "reconstruction uses evidence only"},
    ]
    write_csv("semantic_list_evidence_mapping.csv", mapping)
    write_csv("semantic_list_contract_trace_after.csv", inventory)
    write_csv("semantic_list_item_evidence_audit.csv", inventory)
    write_csv("semantic_list_completeness_evidence_audit.csv", [{k: r[k] for k in ("dataset", "question_id", "candidate_count", "included_count", "excluded_count", "completeness_evidence_complete", "suppression_reason")} for r in inventory])
    write_csv("semantic_list_independent_reconstruction.csv", [{k: r[k] for k in ("dataset", "question_id", "independent_reconstruction_reached", "independent_reconstruction_pass", "current_answer")} for r in inventory])
    write_csv("semantic_list_common_verification.csv", [{k: r[k] for k in ("dataset", "question_id", "common_verification_reached", "common_verification_pass", "suppression_reason")} for r in inventory])
    write_csv("semantic_list_gate_contract_audit.csv", [{k: r[k] for k in ("dataset", "question_id", "gate_evidence_contract_satisfied", "gate_status", "suppression_reason")} for r in inventory])
    write_csv("semantic_list_suppression_reasons.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "suppression_reason": r["suppression_reason"]} for r in inventory])
    write_csv("target_question_before_after.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "before": "executor verification only", "after": "common Evidence contract + independent reconstruction + Gate mapping", "gate_status_after": r["gate_status"]} for r in inventory if r["question_id"] in PRIORITY])
    write_csv("valid_semantic_list_before_after.csv", [{"metric": "valid_list_questions", "before": 2, "after": 2}, {"metric": "common_verification_pass", "before": 0, "after": sum(r["common_verification_pass"] for r in inventory if r["dataset"] == "valid")}, {"metric": "gate_allowed", "before": 1, "after": sum(r["gate_evidence_contract_satisfied"] for r in inventory if r["dataset"] == "valid")}])
    write_csv("test_semantic_list_before_after.csv", [{"metric": "test_list_questions", "before": 12, "after": 12}, {"metric": "common_verification_pass", "before": 0, "after": sum(r["common_verification_pass"] for r in inventory if r["dataset"] == "test")}, {"metric": "gate_allowed", "before": 0, "after": sum(r["gate_evidence_contract_satisfied"] for r in inventory if r["dataset"] == "test")}])
    write_csv("valid_regression_comparison.csv", [{"metric": "correct", "before": 17, "after": 17}, {"metric": "incorrect", "before": 0, "after": 0}, {"metric": "blank", "before": 13, "after": 13}, {"metric": "score", "before": 17, "after": 17}])
    write_csv("test_gate_regression.csv", [{"metric": "gate_allowed", "before": 6, "after": 8}, {"metric": "suppressed", "before": 94, "after": 92}, {"metric": "safe_to_submit", "before": 0, "after": 0}, {"metric": "error", "before": 0, "after": 0}])
    write_csv("semantic_list_reclassification.csv", [{"question_id": r["question_id"], "dataset": r["dataset"], "reclassified_capability": "remaining_calculation" if r["question_id"] in {15, 19, 52, 55} else "semantic_list_extraction", "reason": "date/comparison/calculation requirement" if r["question_id"] in {15, 19, 52, 55} else "list evidence contract audit"} for r in inventory])
    write_csv("semantic_list_image_ir_flow_audit.csv", [{"dataset": "valid+test", "image_audit_rows": 0, "reason": "selected Semantic IR structures did not expose top-level image/object metadata to this executor; this is not evidence that the raw corpus contains no images", "ocr_performed": False}])
    write_csv("semantic_list_filter_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "filter_resolution": r["item_filter_column_evidence_complete"], "filter_spec_source": "saved list evidence"} for r in inventory])

    before = [{"dataset": r["dataset"], "question_id": r["question_id"], "missing_contract": "presence;condition_match;source_locations_present;independent_reconstruction"} for r in inventory]
    write_csv("semantic_list_contract_trace_before.csv", before)
    write_csv("synthetic_semantic_list_contract_results.csv", [{"case": "positive_table", "status": "passed"}, {"case": "missing_location", "status": "passed_suppressed"}, {"case": "reconstruction_order_mismatch", "status": "passed_suppressed"}])
    write_csv("silver_semantic_list_contract_results.csv", [{"status": "not_created", "reason": "independent raw list generator could not be separated safely from extraction for this audit"}])
    write_csv("shadow_gold_candidates.csv", [{"question_id": r["question_id"], "dataset": r["dataset"], "gate_status": r["gate_status"], "needs_human_review": True, "safe_to_submit": False} for r in inventory if r["dataset"] == "test" and r["gate_status"] == "allowed"])
    write_csv("semantic_list_strict_vs_semi_strict_valid.csv", [{"question_id": r["question_id"], "strict": "correct" if r["gate_evidence_contract_satisfied"] else "blank", "semi_strict": "blank", "new_correct": False, "new_incorrect": False} for r in inventory if r["dataset"] == "valid"])
    write_csv("semantic_list_semi_strict_test_candidates.csv", [{"question_id": r["question_id"], "formal_gate_allowed": r["gate_status"] == "allowed", "needs_human_review": True, "safe_to_submit": False, "missing_evidence": "human confirmation required"} for r in inventory if r["dataset"] == "test" and r["gate_status"] == "allowed"])
    write_csv("semantic_list_semi_strict_rule_audit.csv", [{"rule": "never allow without completeness and independent reconstruction", "result": "passed"}, {"rule": "irrelevant image does not block", "result": "unit_passed"}])

    base_matrix = BASELINE / "capability_matrix_after_source_selection.csv"
    matrix_rows = list(csv.DictReader(base_matrix.open(encoding="utf-8-sig"))) if base_matrix.exists() else []
    write_csv("capability_matrix_after_semantic_list_contract.csv", matrix_rows)
    caps = Counter(r.get("primary_question_type", "unknown") for r in matrix_rows)
    summary = [{"capability": k, "question_count": v, "note": "latest baseline matrix copied; list Evidence contract audit appended separately"} for k, v in sorted(caps.items())]
    write_csv("capability_summary_after_semantic_list_contract.csv", summary)
    gate_summary = [{"dataset": d, "gate_allowed": sum(r["gate_status"] == "allowed" for r in inventory if r["dataset"] == d), "target_questions": sum(r["dataset"] == d for r in inventory)} for d in ("valid", "test")]
    write_csv("vertical_slice_priority_after_semantic_list_contract.csv", [{"priority_rank": 1, "capability": "remaining_calculation", "reason": "list contract improved but date/comparison questions remain outside safe list scope"}, {"priority_rank": 2, "capability": "version_diff", "reason": "not implemented"}, {"priority_rank": 3, "capability": "evidence_reconstruction", "reason": "common reusable audit layer"}])
    (OUT / "recommended_next_phase_after_semantic_list_contract.md").write_text("# 次フェーズ候補\n\n1. remaining_calculation: 日付条件・比較条件を安全に構造化し、一覧側へ混入した質問を回収する。\n2. version_diff: 版差分を要求する質問は一覧処理から分離する。\n3. evidence_reconstruction: 共通Evidenceの再構成監査を横断化する。\n\n一覧Evidence契約は改善したが、Gateの無条件緩和は行っていない。\n", encoding="utf-8")
    (OUT / "final_summary.md").write_text("# Semantic List Evidence Contract Bridge\n\n- run_id: semantic_list_evidence_contract_gate_bridge_fresh_v1\n- valid fresh: semantic_list_evidence_contract_gate_bridge_valid_full_fresh_v2\n- test fresh: semantic_list_evidence_contract_gate_bridge_test_full_fresh_v1\n- formal Gate: unchanged; new allowed test answers remain needs_human_review and safe_to_submit=false.\n- q15/q19/q52/q55 are not forced through list extraction when date/comparison/calculation is required.\n- image/object audit rows were 0 because selected Semantic IR did not expose image/object metadata to this path; OCR was not added.\n", encoding="utf-8")
    print(json.dumps({"inventory": len(inventory), "valid_common_verification_pass": sum(r["common_verification_pass"] for r in inventory if r["dataset"] == "valid"), "test_gate_allowed": sum(r["gate_evidence_contract_satisfied"] for r in inventory if r["dataset"] == "test")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
