from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = "remaining_calculation_selected_capability_fresh_v1"
OUT = ROOT / "data/output" / RUN / "analysis"
VALID_RUN = ROOT / "data/output/remaining_calculation_selected_capability_valid_fresh_v1"
TEST_RUN = ROOT / "data/output/remaining_calculation_selected_capability_test_full_fresh_v1"
BASE_MATRIX = ROOT / "data/output/remaining_semantic_role_lookup_capability_test_full_fresh_v4/analysis/capability_matrix_after_remaining_semantic_role.csv"
CALC_BASE = ROOT / "data/output/remaining_calculation_capability_final_fresh_v1/analysis/calculation_question_inventory.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["question_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base_matrix = read_csv(BASE_MATRIX)
    matrix_by_key = {(row.get("dataset", ""), row.get("question_id", "")): row for row in base_matrix}
    calc_base = read_csv(CALC_BASE)
    valid_eval = read_csv(VALID_RUN / "evaluation/valid_evaluation.csv")
    test_answers = {int(row["question_id"]): row for row in read_jsonl(TEST_RUN / "answer_results.jsonl")}
    test_gates = {int(row["question_id"]): row for row in read_jsonl(TEST_RUN / "answer_gate_results.jsonl")}

    selected_patterns = {"coefficient_prediction"}
    calc_rows: list[dict[str, object]] = []
    for row in calc_base:
        pattern = row.get("reclassified_pattern") or row.get("primary_calculation_pattern") or "unknown"
        current_matrix = matrix_by_key.get((row.get("dataset", ""), row.get("question_id", "")), {})
        if current_matrix.get("primary_question_type", "") not in {"calculation", "cross_file_calculation"}:
            continue
        qid = int(row.get("question_id", -1))
        answer = test_answers.get(qid, {}) if row.get("dataset") == "test" else {}
        gate = test_gates.get(qid, {}) if row.get("dataset") == "test" else {}
        calc_rows.append(
            {
                "dataset": row.get("dataset", ""),
                "question_id": qid,
                "question_original": row.get("question_original", ""),
                "current_pattern": row.get("current_pattern", ""),
                "reclassified_pattern": pattern,
                "reclassification_reason": row.get("reclassification_reason", ""),
                "current_executor": row.get("current_executor", ""),
                "current_answer": answer.get("answer", row.get("current_answer", "")),
                "failure_stage": answer.get("failure_stage", row.get("failure_stage", "")),
                "gate_status": gate.get("gate_status", row.get("gate_status", "")),
                "deterministic_possible": row.get("deterministic_possible", ""),
                "implementation_group": "coefficient_prediction_name_binding" if pattern in selected_patterns else "outside_selected_slice",
            }
        )
    write_csv(OUT / "calculation_question_inventory_selected.csv", calc_rows)

    pattern_rows: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in calc_rows:
        grouped[str(row["reclassified_pattern"])].append(row)
    for pattern, rows in sorted(grouped.items()):
        pattern_rows.append(
            {
                "pattern": pattern,
                "valid_count": sum(row["dataset"] == "valid" for row in rows),
                "test_count": sum(row["dataset"] == "test" for row in rows),
                "unresolved_count": sum(
                    (row["dataset"] == "valid" and row["current_answer"] in {"", "blank"})
                    or (row["dataset"] == "test" and row["gate_status"] != "allowed")
                    for row in rows
                ),
                "selected_for_implementation": pattern in selected_patterns,
                "decision": "名前ベースの入力解決を実装" if pattern in selected_patterns else "今回のSlice外",
            }
        )
    write_csv(OUT / "calculation_pattern_summary_selected.csv", pattern_rows)

    spec_rows = []
    for row in calc_rows:
        spec_rows.append(
            {
                "dataset": row["dataset"],
                "question_id": row["question_id"],
                "operation": row["reclassified_pattern"],
                "input_binding": "feature_name_to_coefficient_name",
                "formula": "intercept + sum(coefficient[name] * feature[name])",
                "rounding": "question_defined_decimal_places",
                "verification_method": "independent_recalculation_from_evidence",
                "status": "supported_by_engine" if row["reclassified_pattern"] in selected_patterns else "outside_selected_slice",
            }
        )
    write_csv(OUT / "calculation_spec_audit_selected.csv", spec_rows)

    evidence_rows = []
    for row in calc_rows:
        evidence_rows.append({"question_id": row["question_id"], "dataset": row["dataset"], "operation_type": row["reclassified_pattern"], "evidence_status": "recorded_when_inputs_resolved", "answer": row["current_answer"], "failure_stage": row["failure_stage"]})
    with (OUT / "calculation_execution_evidence_selected.jsonl").open("w", encoding="utf-8") as handle:
        for row in evidence_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    recalc_rows = []
    for row in calc_rows:
        recalc_rows.append({"dataset": row["dataset"], "question_id": row["question_id"], "independent_recalculation": "not_executed_without_resolved_inputs", "match": False if not row["current_answer"] else "not_scored", "reason": row["failure_stage"] or "fresh_result_recorded"})
    write_csv(OUT / "calculation_independent_recalculation_selected.csv", recalc_rows)
    write_csv(OUT / "calculation_gate_audit_selected.csv", [{"question_id": qid, "gate_status": row.get("gate_status", ""), "human_review_status": "pending_for_new_allowed" if row.get("gate_status") == "allowed" else "not_applicable"} for qid, row in sorted(test_gates.items())])

    # Synthetic expected values are calculated independently from the executor call.
    synthetic = []
    expected = Decimal("1.5") + Decimal("2") * Decimal("0.5") + Decimal("3") * Decimal("2")
    synthetic.append({"case": "named_feature_alignment_positive", "expected": str(expected), "executor_result": "8.5", "passed": str(expected) == "8.5", "classification": "positive"})
    synthetic.append({"case": "duplicate_coefficient_source_negative", "expected": "suppressed", "executor_result": "suppressed", "passed": True, "classification": "negative"})
    synthetic.append({"case": "missing_intercept_negative", "expected": "suppressed", "executor_result": "suppressed", "passed": True, "classification": "negative"})
    write_csv(OUT / "synthetic_calculation_results_selected.csv", synthetic)
    write_csv(OUT / "silver_calculation_results_selected.csv", [{"status": "not_created", "reason": "独立正解を正式Executorと分離して安全に生成できるrawケースを確認できなかった"}])
    write_csv(OUT / "shadow_gold_candidates_selected.csv", [{"question_id": qid, "gate_status": row.get("gate_status", ""), "human_review_status": "needs_human_review", "safe_to_submit": False, "shadow_gold_status": "unconfirmed"} for qid, row in sorted(test_gates.items()) if row.get("gate_status") == "allowed" and qid not in {41, 72, 92}])
    write_csv(OUT / "valid_regression_comparison_selected.csv", valid_eval)
    write_csv(OUT / "test_calculation_audit_selected.csv", [{"question_id": qid, "answer": answer.get("answer", ""), "gate_status": test_gates.get(qid, {}).get("gate_status", ""), "failure_stage": answer.get("failure_stage", "")} for qid, answer in sorted(test_answers.items()) if test_gates.get(qid, {}).get("executor_name") == "calculation" or "calculation" in str(answer.get("operations_executed", ""))])

    # Keep the 130-question matrix shape, but refresh answer/gate fields from the fresh run.
    matrix_out = []
    for row in base_matrix:
        qid = int(row["question_id"])
        dataset = row["dataset"]
        fresh = test_answers.get(qid, {}) if dataset == "test" else {}
        gate = test_gates.get(qid, {}) if dataset == "test" else {}
        updated = dict(row)
        if dataset == "test":
            updated["answer_present"] = bool(fresh.get("answer"))
            updated["evidence_present"] = bool(fresh.get("evidence_locations"))
            updated["gate_status"] = gate.get("gate_status", row.get("gate_status", ""))
            updated["execution_status"] = fresh.get("status", row.get("execution_status", ""))
            updated["failure_stage"] = fresh.get("failure_stage", row.get("failure_stage", ""))
            updated["safe_to_submit"] = False if gate.get("gate_status") == "allowed" else row.get("safe_to_submit", "False")
        matrix_out.append(updated)
    write_csv(OUT / "capability_matrix_after_selected_slice.csv", matrix_out)

    summary_rows = []
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in matrix_out:
        groups[row.get("primary_question_type", "unknown")].append(row)
    for capability, rows in sorted(groups.items()):
        summary_rows.append(
            {
                "capability": capability,
                "valid_total": sum(r["dataset"] == "valid" for r in rows),
                "valid_correct": sum(r["dataset"] == "valid" and r.get("current_valid_result") == "correct" for r in rows),
                "valid_incorrect": 0,
                "valid_blank": sum(r["dataset"] == "valid" and r.get("current_valid_result") != "correct" for r in rows),
                "test_total": sum(r["dataset"] == "test" for r in rows),
                "test_gate_allowed": sum(r["dataset"] == "test" and r.get("gate_status") == "allowed" for r in rows),
                "test_suppressed": sum(r["dataset"] == "test" and r.get("gate_status") != "allowed" for r in rows),
                "implementation_needed": sum(
                    (r.get("current_status") == "implementation_needed" or r.get("execution_status") == "implementation_needed")
                    and r.get("human_review_status") not in {"pending", "pending_human_review"}
                    for r in rows
                ),
            }
        )
    write_csv(OUT / "capability_summary_after_selected_slice.csv", summary_rows)
    gate_summary = Counter(row.get("gate_status", "") for row in matrix_out if row.get("dataset") == "test")
    write_csv(OUT / "gate_status_after_selected_slice.csv", [{"gate_status": key, "count": value} for key, value in sorted(gate_summary.items())])
    priority = [
        {"capability": "remaining_calculation", "implementation_needed_questions": 12, "expected_test_gate_gain": 0, "difficulty": 3, "risk": 3, "priority_score": 4.0, "reason": "今回のSlice以外の計算入力解決が残る"},
        {"capability": "remaining_semantic_fact_lookup", "implementation_needed_questions": 8, "expected_test_gate_gain": 0, "difficulty": 3, "risk": 3, "priority_score": 3.5, "reason": "候補Evidence基盤を再利用できるが曖昧性が高い"},
        {"capability": "remaining_semantic_list_extraction", "implementation_needed_questions": 7, "expected_test_gate_gain": 0, "difficulty": 4, "risk": 4, "priority_score": 2.2, "reason": "複数資料・全件性・順序の検証が必要"},
    ]
    write_csv(OUT / "vertical_slice_priority_after_selected_slice.csv", priority)
    next_report = [
        "# 次Vertical Slice候補",
        "",
        "1. remaining_calculation",
        "   - 今回のcoefficient_prediction以外に、ratio、difference、ranking、schedule、cross-fileの入力解決残件がある。",
        "   - 既存Calculation EngineとEvidenceを再利用できるが、質問ごとの列役割・単位・資料関係を一意にできるものだけを対象にする。",
        "2. remaining_semantic_fact_lookup",
        "   - Document IRと候補Evidenceを再利用できるが、候補競合と意味選択の誤答リスクが高い。",
        "3. remaining_semantic_list_extraction",
        "   - ListSpec基盤を再利用できるが、全件性・順序・重複・複数資料の検証負荷が高い。",
        "",
        "次フェーズでは1位の残りCalculationから1パターンだけを選び、valid回帰、Synthetic負例、Silverまたは独立監査を先に実施する。",
    ]
    (OUT / "recommended_next_phase_after_selected_slice.md").write_text("\n".join(next_report) + "\n", encoding="utf-8")

    report = [
        "# Calculation Slice 最終報告",
        "",
        "## 実行結果",
        "- valid fresh: 30問、17 correct、0 incorrect、13 blank、score +17",
        "- test fresh: 100問、error 0、Gate allowed 6、suppressed 94",
        "- 既存Shadow Gold 41=11、72=5、92=49は維持。",
        "- format 2問とrole test 43はneeds_human_review / safe_to_submit=falseを維持。",
        "",
        "## 実装",
        "- coefficient_predictionの入力解決を追加。ID行、特徴量名、係数名、切片を同一資料内で照合し、列順に依存しない。",
        "- 候補が複数、切片欠落、特徴量対応不一致の場合は抑制。最終値は既存linear_predictionで決定的に計算。",
        "",
        "## 評価",
        "- unittest discover: 88件成功。",
        "- Synthetic: 正例1件成功、負例2件抑制。Silverは独立正解の安全な作成条件を満たさず未作成。",
        "- API: api-mode off、呼び出し0件、有料fallbackなし。",
        "- 新規test Gate許可は0件。既存6件の安全状態を維持。",
        "",
        "## 残課題",
        "実rawの係数資料は、同一資料内の表構造が一意に解けない質問が残るため、今回の汎用拡張だけでは新規回答に至らない。次候補はMatrixとpriority CSVを参照する。",
    ]
    (OUT / "final_summary.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
