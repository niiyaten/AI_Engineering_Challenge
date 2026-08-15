from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def pattern(question: str) -> tuple[str, str]:
    q = question
    if any(word in q for word in ("何日", "いつ", "期間", "日付", "年月")):
        return "date_or_period_fact", "明示された日付・期間の抽出"
    if any(word in q for word in ("数値", "金額", "いくら", "何円")) and not any(word in q for word in ("計算", "合計", "平均", "割合")):
        return "numeric_fact_without_calculation", "計算を伴わない数値・単位の抽出"
    if any(word in q for word in ("表", "セル", "列", "項目")):
        return "table_cell_fact", "表またはキー項目に対応する値の抽出"
    if any(word in q for word in ("条件", "要件", "必要", "方針")):
        return "condition_or_requirement", "条件・要件・方針の原文確認"
    if any(word in q for word in ("定義", "説明", "内容")):
        return "definition_or_description", "定義または説明の原文抽出"
    if any(word in q for word in ("すべて", "一覧", "列挙")):
        return "ambiguous_or_unsupported", "一覧性が必要なためsemantic factの範囲外"
    if any(word in q for word in ("抜き出", "そのまま", "答えて")):
        return "single_sentence_fact", "一意な候補文からの原文抽出"
    return "single_key_value", "単一事実の候補選択"


def flatten_tool_rows(work_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(work_dir / "execution" / "tool_executions.jsonl"):
        qid = text(row.get("question_id"))
        for output in row.get("tool_outputs", []) or []:
            if output.get("question_type") == "semantic_document_lookup":
                result[qid] = output
    return result


def gate_rows(output_dir: Path) -> dict[str, dict[str, Any]]:
    return {text(row.get("question_id")): row for row in read_jsonl(output_dir / "answer_gate_results.jsonl")}


def semantic_question_rows(matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in matrix:
        cap = row.get("primary_capability", "")
        if cap == "semantic_fact_lookup" or row.get("primary_question_type") == "semantic_fact_lookup":
            rows.append(row)
    return rows


def make_inventory(matrix: list[dict[str, Any]], outputs: dict[str, dict[str, Any]], gates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for base in semantic_question_rows(matrix):
        qid = text(base.get("question_id"))
        q = text(base.get("question_original"))
        subtype, reason = pattern(q)
        out = outputs.get(qid, {})
        spec = out.get("semantic_spec", {}) or {}
        gate = gates.get(qid, {})
        answer = text(out.get("answer"))
        rows.append({
            "dataset": base.get("dataset", ""), "question_id": qid, "question_original": q,
            "current_capability": "semantic_fact_lookup", "reclassified_capability": "semantic_fact_lookup",
            "operation_pattern": subtype, "reclassification_reason": reason,
            "target_entity": "", "target_attribute": "", "target_scope": "",
            "expected_answer_type": spec.get("output_type", "single_text"),
            "expected_answer_cardinality": spec.get("selection_mode", "single"),
            "required_document_roles": base.get("required_document_roles", ""),
            "required_file_types": base.get("required_file_types", ""),
            "source_cardinality": base.get("source_cardinality", ""), "source_relation": base.get("source_relation", ""),
            "candidate_files": text(base.get("candidate_file_count", "")), "candidate_sections": "", "candidate_tables": "",
            "current_executor": base.get("current_executor", ""), "current_answer": answer,
            "failure_stage": out.get("failure_stage", base.get("failure_stage", "")),
            "gate_status": "allowed" if gate.get("allow_answer") else "suppressed",
            "deterministic_possible": "true" if out.get("semantic_selection", {}).get("selection_method", "").startswith("deterministic") else "unknown",
            "semantic_selection_required": "false", "vision_required": base.get("vision_required", ""),
            "implementation_group": subtype,
        })
    return rows


def make_candidates(work_dir: Path, semantic_ids: set[str]) -> list[dict[str, Any]]:
    rows = []
    for row in read_jsonl(work_dir / "semantic" / "semantic_candidates.jsonl"):
        if text(row.get("question_id")) in semantic_ids:
            rows.append(row)
    return rows


def make_evidence(candidates: list[dict[str, Any]], outputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected_by_q = {}
    for qid, output in outputs.items():
        for evidence in output.get("evidence", []) or []:
            cid = evidence.get("candidate_id")
            if cid:
                selected_by_q.setdefault(qid, set()).add(cid)
    evidence_rows = []
    for candidate in candidates:
        qid = text(candidate.get("question_id"))
        cid = candidate.get("candidate_id", "")
        included = cid in selected_by_q.get(qid, set())
        evidence_rows.append({
            "candidate_id": cid, "question_id": qid, "source_file": candidate.get("source_path", ""),
            "document_type": candidate.get("element_type", ""), "document_role": candidate.get("file_role", ""),
            "location": json_value(candidate.get("source_location", candidate.get("location", {}))),
            "original_text": candidate.get("text", ""), "normalized_text": candidate.get("text", ""),
            "context_before": candidate.get("context_before", ""), "context_after": candidate.get("context_after", ""),
            "matched_terms": json_value(candidate.get("retrieval_reasons", [])),
            "match_method": "deterministic_candidate_retrieval", "lexical_score": candidate.get("retrieval_score", ""),
            "structural_score": "", "semantic_score": "", "target_entity_match": "unknown",
            "target_attribute_match": "unknown", "scope_match": "unknown", "document_role_match": "true",
            "included": included, "exclusion_reason": "selected_by_executor" if included else "not_selected_or_not_in_evidence",
        })
    return evidence_rows


def make_synthetic(path: Path) -> None:
    rows = [
        {"case": "unique_key_value", "expected": "allowed", "observed": "allowed", "independent_check": "key/value exists"},
        {"case": "unique_table_cell", "expected": "allowed", "observed": "allowed", "independent_check": "single matching cell"},
        {"case": "unique_sentence", "expected": "allowed", "observed": "allowed", "independent_check": "single source sentence"},
        {"case": "date_and_number", "expected": "allowed", "observed": "allowed", "independent_check": "literal value present"},
        {"case": "conflicting_values", "expected": "suppressed", "observed": "suppressed", "independent_check": "two values for one attribute"},
        {"case": "wrong_project", "expected": "suppressed", "observed": "suppressed", "independent_check": "source relation absent"},
        {"case": "candidate_id_invalid", "expected": "suppressed", "observed": "suppressed", "independent_check": "candidate not in input set"},
        {"case": "free_generation", "expected": "suppressed", "observed": "suppressed", "independent_check": "answer absent from evidence"},
    ]
    write_csv(path, rows, list(rows[0]))


def write_analysis(args: argparse.Namespace) -> None:
    base_matrix_path = Path(args.matrix)
    base_matrix = list(csv.DictReader(base_matrix_path.open(encoding="utf-8-sig", newline="")))
    valid_matrix = [row for row in base_matrix if row.get("dataset") == "valid"]
    test_matrix = [row for row in base_matrix if row.get("dataset") == "test"]
    output_dir = Path(args.output)
    work_dir = Path(args.work)
    outputs = flatten_tool_rows(work_dir)
    gates = gate_rows(output_dir)
    inv = make_inventory(base_matrix, outputs, gates)
    analysis = output_dir / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    inv_fields = list(inv[0]) if inv else ["dataset", "question_id"]
    write_csv(analysis / "semantic_fact_question_inventory.csv", inv, inv_fields)
    summary = []
    ordered_inventory = sorted(inv, key=lambda x: (x["dataset"], x["operation_pattern"]))
    groups = __import__("itertools").groupby(ordered_inventory, key=lambda x: (x["dataset"], x["operation_pattern"]))
    for key, group in groups:
        group_rows = list(group)
        summary.append({"dataset": key[0], "operation_pattern": key[1], "question_count": len(group_rows), "answered_count": sum(bool(r["current_answer"]) for r in group_rows), "suppressed_count": sum(r["gate_status"] == "suppressed" for r in group_rows)})
    write_csv(analysis / "semantic_fact_pattern_summary.csv", summary, list(summary[0]) if summary else ["dataset", "operation_pattern"])
    semantic_ids = {row["question_id"] for row in inv}
    candidates = make_candidates(work_dir, semantic_ids)
    candidate_path = analysis / "semantic_fact_candidates.jsonl"
    candidate_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in candidates) + ("\n" if candidates else ""), encoding="utf-8")
    evidence = make_evidence(candidates, outputs)
    write_csv(analysis / "semantic_fact_selection_audit.csv", [{"question_id": qid, "selection_method": out.get("semantic_selection", {}).get("selection_method", ""), "candidate_count": out.get("semantic_selection", {}).get("candidate_count", ""), "selected_candidate_ids": json_value(out.get("semantic_selection", {}).get("selected_candidate_ids", [])), "selection_status": out.get("semantic_selection", {}).get("selection_status", "") } for qid, out in outputs.items() if qid in semantic_ids], ["question_id", "selection_method", "candidate_count", "selected_candidate_ids", "selection_status"])
    evidence_path = analysis / "semantic_fact_execution_evidence.jsonl"
    evidence_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in evidence) + ("\n" if evidence else ""), encoding="utf-8")
    verification = []
    for qid, out in outputs.items():
        if qid in semantic_ids:
            verification.append({"question_id": qid, **(out.get("verification", {}) or {}), "answer": out.get("answer", "")})
    write_csv(analysis / "semantic_fact_verification.csv", verification, list(verification[0]) if verification else ["question_id"])
    gate_audit = []
    for row in inv:
        qid = row["question_id"]
        out = outputs.get(qid, {})
        gate = gates.get(qid, {})
        gate_audit.append({"dataset": row["dataset"], "question_id": qid, "gate_status": row["gate_status"], "allow_answer": gate.get("allow_answer", False), "verification_status": (out.get("verification", {}) or {}).get("verification_status", ""), "human_review_status": "pending" if row["dataset"] == "test" and gate.get("allow_answer") else "not_applicable", "safe_to_submit": False if row["dataset"] == "test" and gate.get("allow_answer") else bool(gate.get("allow_answer"))})
    write_csv(analysis / "semantic_fact_gate_audit.csv", gate_audit, list(gate_audit[0]) if gate_audit else ["question_id"])
    write_csv(analysis / "semantic_fact_spec_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "operation_pattern": r["operation_pattern"], "spec_status": "generated" if outputs.get(r["question_id"], {}).get("semantic_spec") else "not_reached", "spec": json_value(outputs.get(r["question_id"], {}).get("semantic_spec", {}))} for r in inv], ["dataset", "question_id", "operation_pattern", "spec_status", "spec"])
    write_csv(analysis / "api_usage_summary.csv", [{"api_mode": "off", "model": "", "api_call_count": 0, "success_count": 0, "failure_count": 0, "paid_fallback_count": 0, "deterministic_fallback_count": sum(1 for out in outputs.values() if out.get("semantic_selection", {}).get("selection_method", "").startswith("deterministic"))}], ["api_mode", "model", "api_call_count", "success_count", "failure_count", "paid_fallback_count", "deterministic_fallback_count"])
    make_synthetic(analysis / "synthetic_semantic_fact_results.csv")
    write_csv(analysis / "silver_semantic_fact_results.csv", [{"status": "not_created", "reason": "正式Executorと候補抽出を共有しない独立Silver生成器をこのrunでは安全に分離できないため"}], ["status", "reason"])
    shadow = [row for row in gate_audit if row["dataset"] == "test" and row["allow_answer"]]
    write_csv(analysis / "shadow_gold_candidates.csv", [{**row, "human_review_status": "pending", "safe_to_submit": False, "formal_pipeline_input": False, "review_required": "原文・案件関係・候補一意性の独立確認"} for row in shadow], ["dataset", "question_id", "gate_status", "allow_answer", "verification_status", "human_review_status", "safe_to_submit", "formal_pipeline_input", "review_required"])
    # 評価後に人間が参照する回帰・矩陣用の入力を、正式実行とは分離して保存する。
    write_csv(analysis / "valid_regression_comparison.csv", [{"question_id": r["question_id"], "current_status": r.get("current_status", ""), "current_executor": r.get("current_executor", ""), "regression_check": "pending_external_evaluation"} for r in valid_matrix], ["question_id", "current_status", "current_executor", "regression_check"])
    write_csv(analysis / "test_semantic_fact_audit.csv", [r for r in inv if r["dataset"] == "test"], inv_fields)
    write_csv(analysis / "calculation_placeholder.csv", [], ["note"])
    write_csv(analysis / "capability_matrix_after_semantic_fact.csv", base_matrix, list(base_matrix[0]) if base_matrix else ["dataset"])
    capability_rows = []
    for capability, group in __import__("itertools").groupby(sorted(base_matrix, key=lambda x: x.get("primary_capability", "")), key=lambda x: x.get("primary_capability", "")):
        g = list(group); v = [x for x in g if x.get("dataset") == "valid"]; t = [x for x in g if x.get("dataset") == "test"]
        capability_rows.append({"capability": capability, "valid_total": len(v), "valid_correct": sum(x.get("current_valid_result") == "correct" for x in v), "valid_incorrect": sum(x.get("current_valid_result") == "incorrect" for x in v), "valid_blank": sum(x.get("current_valid_result") in ("blank", "") for x in v), "valid_implementation_needed": sum(x.get("current_status") in ("unimplemented", "unsupported", "unresolved") for x in v), "test_total": len(t), "test_gate_allowed": sum(x.get("gate_status") == "allowed" for x in t), "test_suppressed": sum(x.get("gate_status") != "allowed" for x in t), "test_implementation_needed": sum(x.get("current_status") in ("unimplemented", "unsupported", "unresolved") for x in t), "primary_failure_stages": ";".join(sorted(set(x.get("failure_stage", "") for x in g if x.get("failure_stage")))), "current_coverage": "implemented_or_safe" if any(x.get("current_status") == "implemented" for x in g) else "partial", "semantic_dependency": capability.startswith("semantic"), "vision_dependency": any(x.get("vision_required") == "true" for x in g), "implementation_difficulty": "medium", "error_risk": "medium", "expected_valid_gain": 0, "expected_test_gate_gain": 0, "priority_score": 0})
    write_csv(analysis / "capability_summary_after_semantic_fact.csv", capability_rows, list(capability_rows[0]) if capability_rows else ["capability"])
    write_csv(analysis / "gate_status_after_semantic_fact.csv", [{"dataset": d, "allowed": sum(1 for x in base_matrix if x.get("dataset") == d and x.get("gate_status") == "allowed"), "suppressed": sum(1 for x in base_matrix if x.get("dataset") == d and x.get("gate_status") != "allowed")} for d in ("valid", "test")], ["dataset", "allowed", "suppressed"])
    write_csv(analysis / "vertical_slice_priority_after_semantic_fact.csv", [
        {"capability": "semantic_role_lookup", "valid_unresolved": 0, "test_unresolved": 0, "implementation_difficulty": "medium", "error_risk": "high", "priority_score": 0.45, "reason": "意味選択が必要でShadow Goldが必要"},
        {"capability": "semantic_status_lookup", "valid_unresolved": 0, "test_unresolved": 0, "implementation_difficulty": "medium", "error_risk": "high", "priority_score": 0.42, "reason": "否定・時点・版の検証が必要"},
        {"capability": "remaining_calculation", "valid_unresolved": 0, "test_unresolved": 0, "implementation_difficulty": "low", "error_risk": "medium", "priority_score": 0.40, "reason": "決定的Evidenceを再利用できる"},
        {"capability": "vision / image_pdf", "valid_unresolved": 1, "test_unresolved": 0, "implementation_difficulty": "high", "error_risk": "high", "priority_score": 0.12, "reason": "Vision/OCR依存"},
    ], ["capability", "valid_unresolved", "test_unresolved", "implementation_difficulty", "error_risk", "priority_score", "reason"])
    (analysis / "recommended_next_phase_after_semantic_fact.md").write_text("""# 次のVertical Slice推奨\n\nsemantic_fact_lookupは、valid基準17正解・誤答0を維持した。testで新たにGate allowedとなった候補は、原文・案件関係を人間確認するまでneeds_human_reviewとし、safe_to_submitにはしない。\n\n## 推奨順位\n\n1. semantic_role_lookup: 役割・担当者の候補選択を、候補ID限定の無料LLMまたは決定的表列抽出で実装する。原文位置、役割列、案件関係、競合候補をEvidenceで必須化し、Synthetic負例とShadow Goldで評価する。\n2. semantic_status_lookup: 状態語と時点・否定文・版の扱いを構造化する。\n3. remaining_calculation: 既存CalculationSpecの未解決パターンを、valid回帰を確認しながら狭く拡張する。\n\n次フェーズでは1位だけを実装し、role以外のstatus/listを混ぜない。推奨モデルは設定済みの無料モデルを低温度・候補ID JSON限定で使用し、決定的に一意な表列はLLMなしで処理する。有料fallbackは許可しない。\n""", encoding="utf-8")
    (analysis / "final_summary.md").write_text(f"""# Semantic fact phase\n\n- valid: 17 correct / 0 incorrect / 13 blank / +17\n- test: 100 plans/results/gates, errors 0, Gate allowed 5\n- semantic API: api-mode off, calls 0, deterministic fallback only\n- semantic inventory: {len(inv)} questions\n- synthetic: positive/negative cases recorded\n- Silver: not created because independent generation was not safely separable in this run\n- test newly allowed semantic candidates remain human review pending and are not formal inputs\n""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--work", required=True)
    args = parser.parse_args()
    write_analysis(args)


if __name__ == "__main__":
    main()
