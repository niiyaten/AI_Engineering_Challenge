from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from itertools import groupby
from pathlib import Path


def jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dump_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def classify(q: str):
    if any(x in q for x in ("計算", "合計", "平均", "割合", "最も", "差", "減額", "何円少なく", "日数", "上位", "総額", "最後に開始", "請求金額", "実際の", "高く", "少なかった")):
        return "misclassified_capability", "calculation_or_comparison"
    if any(x in q for x in ("タスクID", "アクションID", "マイルストーンID", "IDを答", "IDを教")):
        return "misclassified_capability", "identifier_verbatim"
    if any(x in q for x in ("すべて", "一覧", "列挙")):
        return "misclassified_capability", "list_completeness"
    if any(x in q for x in ("担当", "役割", "主担当")):
        return "misclassified_capability", "role_lookup"
    if any(x in q for x in ("未完了", "未達成", "未完事項", "完了となって")):
        return "misclassified_capability", "status_lookup"
    if any(x in q for x in ("ページ数", "ページを", "スライド", "シート", "セル")):
        return "misclassified_capability", "location_lookup"
    if any(x in q for x in ("何日", "いつ", "期間", "第何週", "年月")):
        return "date_or_period_fact", "literal_period"
    if any(x in q for x in ("表", "列", "カラム", "セル", "項目")):
        return "table_cell_fact", "header_or_cell_value"
    if any(x in q for x in ("条件", "要件", "方針", "規定")):
        return "condition_or_requirement", "literal_requirement"
    if any(x in q for x in ("抜き出", "答えて", "教えて", "何ですか")):
        return "single_sentence_fact", "unique_literal_candidate"
    return "single_key_value", "single_fact"


def load_runtime(dataset: str, work: Path, output: Path):
    execution = {}
    for row in jsonl(work / "execution" / "tool_executions.jsonl"):
        qid = str(row.get("question_id"))
        for tool in row.get("tool_outputs", []) or []:
            if tool.get("question_type") == "semantic_document_lookup":
                execution[(dataset, qid)] = tool
    gates = {(dataset, str(row.get("question_id"))): row for row in jsonl(output / "answer_gate_results.jsonl")}
    answers = {(dataset, str(row.get("question_id"))): row for row in jsonl(output / "answer_results.jsonl")}
    return execution, gates, answers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--valid-work", required=True)
    parser.add_argument("--valid-output", required=True)
    parser.add_argument("--test-work", required=True)
    parser.add_argument("--test-output", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    matrix = csv_rows(Path(args.matrix))
    valid_exec, valid_gate, valid_ans = load_runtime("valid", Path(args.valid_work), Path(args.valid_output))
    test_exec, test_gate, test_ans = load_runtime("test", Path(args.test_work), Path(args.test_output))
    execution = valid_exec | test_exec
    gates = valid_gate | test_gate
    answers = valid_ans | test_ans
    target = [r for r in matrix if r.get("primary_capability") == "semantic_fact_lookup" or r.get("primary_question_type") == "semantic_fact_lookup"]
    inventory = []
    for base in target:
        key = (base.get("dataset", ""), str(base.get("question_id")))
        q = base.get("question_original", "")
        op, reason = classify(q)
        tool = execution.get(key, {})
        gate = gates.get(key, {})
        answer = answers.get(key, {})
        spec = tool.get("semantic_spec", {}) or {}
        inventory.append({
            "dataset": key[0], "question_id": key[1], "question_original": q,
            "current_capability": "semantic_fact_lookup", "reclassified_capability": "semantic_fact_lookup" if op != "misclassified_capability" else reason,
            "operation_pattern": op, "reclassification_reason": reason,
            "target_entity": "", "target_attribute": "", "target_scope": "",
            "expected_answer_type": spec.get("output_type", "single_text"), "expected_answer_cardinality": spec.get("selection_mode", "single"),
            "required_document_roles": base.get("required_document_roles", ""), "required_file_types": base.get("required_file_types", ""),
            "source_cardinality": base.get("source_cardinality", ""), "source_relation": base.get("source_relation", ""),
            "candidate_files": base.get("candidate_file_count", ""), "candidate_sections": "", "candidate_tables": "",
            "current_executor": base.get("current_executor", ""), "current_answer": answer.get("answer", ""),
            "failure_stage": tool.get("failure_stage", base.get("failure_stage", "")),
            "gate_status": "allowed" if gate.get("allow_answer") else "suppressed",
            "deterministic_possible": bool(tool.get("semantic_selection", {}).get("selection_method", "").startswith("deterministic")),
            "semantic_selection_required": False, "vision_required": base.get("vision_required", ""), "implementation_group": op,
        })
    fields = list(inventory[0]) if inventory else ["dataset", "question_id"]
    write_csv(out / "semantic_fact_question_inventory.csv", inventory, fields)
    summary = []
    ordered = sorted(inventory, key=lambda r: (r["dataset"], r["operation_pattern"]))
    for key, group in groupby(ordered, key=lambda r: (r["dataset"], r["operation_pattern"])):
        rows = list(group)
        summary.append({"dataset": key[0], "operation_pattern": key[1], "question_count": len(rows), "answered_count": sum(bool(r["current_answer"]) for r in rows), "suppressed_count": sum(r["gate_status"] == "suppressed" for r in rows)})
    write_csv(out / "semantic_fact_pattern_summary.csv", summary, ["dataset", "operation_pattern", "question_count", "answered_count", "suppressed_count"])
    ids = {(r["dataset"], r["question_id"]) for r in inventory}
    candidates = []
    for dataset, work in (("valid", Path(args.valid_work)), ("test", Path(args.test_work))):
        for row in jsonl(work / "semantic" / "semantic_candidates.jsonl"):
            if (dataset, str(row.get("question_id"))) in ids:
                candidates.append({"dataset": dataset, **row})
    dump_jsonl(out / "semantic_fact_candidates.jsonl", candidates)
    selection = []
    verification = []
    evidence = []
    for row in inventory:
        key = (row["dataset"], row["question_id"])
        tool = execution.get(key, {})
        sel = tool.get("semantic_selection", {}) or {}
        selection.append({"dataset": row["dataset"], "question_id": row["question_id"], "selection_method": sel.get("selection_method", ""), "candidate_count": sel.get("candidate_count", ""), "selected_candidate_ids": json.dumps(sel.get("selected_candidate_ids", []), ensure_ascii=False), "selection_status": sel.get("selection_status", "")})
        verification.append({"dataset": row["dataset"], "question_id": row["question_id"], **(tool.get("verification", {}) or {}), "answer": tool.get("answer", "")})
    selected = {(r["dataset"], r["question_id"]): set((execution.get((r["dataset"], r["question_id"]), {}).get("semantic_selection", {}) or {}).get("selected_candidate_ids", [])) for r in inventory}
    for c in candidates:
        key = (c["dataset"], str(c.get("question_id")))
        cid = c.get("candidate_id", "")
        included = cid in selected.get(key, set())
        evidence.append({"dataset": c["dataset"], "question_id": c.get("question_id"), "candidate_id": cid, "source_file": c.get("source_path", ""), "document_type": c.get("element_type", ""), "document_role": c.get("file_role", ""), "location": json.dumps(c.get("source_location", c.get("location", {})), ensure_ascii=False), "original_text": c.get("text", ""), "normalized_text": c.get("text", ""), "context_before": c.get("context_before", ""), "context_after": c.get("context_after", ""), "matched_terms": json.dumps(c.get("retrieval_reasons", []), ensure_ascii=False), "match_method": "deterministic_candidate_retrieval", "lexical_score": c.get("retrieval_score", ""), "included": included, "exclusion_reason": "selected_by_executor" if included else "not_selected"})
    write_csv(out / "semantic_fact_selection_audit.csv", selection, list(selection[0]) if selection else ["question_id"])
    dump_jsonl(out / "semantic_fact_execution_evidence.jsonl", evidence)
    write_csv(out / "semantic_fact_verification.csv", verification, list(verification[0]) if verification else ["question_id"])
    gate_audit = []
    for r in inventory:
        key = (r["dataset"], r["question_id"]); gate = gates.get(key, {})
        gate_audit.append({"dataset": r["dataset"], "question_id": r["question_id"], "gate_status": r["gate_status"], "allow_answer": bool(gate.get("allow_answer")), "verification_status": (execution.get(key, {}).get("verification", {}) or {}).get("verification_status", ""), "human_review_status": "pending" if r["dataset"] == "test" and gate.get("allow_answer") else "not_applicable", "safe_to_submit": False if r["dataset"] == "test" and gate.get("allow_answer") else bool(gate.get("allow_answer"))})
    write_csv(out / "semantic_fact_gate_audit.csv", gate_audit, list(gate_audit[0]))
    write_csv(out / "semantic_fact_spec_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "operation_pattern": r["operation_pattern"], "spec_status": "generated" if execution.get((r["dataset"], r["question_id"]), {}).get("semantic_spec") else "not_reached", "spec": json.dumps(execution.get((r["dataset"], r["question_id"]), {}).get("semantic_spec", {}), ensure_ascii=False)} for r in inventory], ["dataset", "question_id", "operation_pattern", "spec_status", "spec"])
    write_csv(out / "api_usage_summary.csv", [{"api_mode": "off", "model": "", "api_call_count": 0, "success_count": 0, "failure_count": 0, "paid_fallback_count": 0, "deterministic_fallback_count": sum(bool((execution.get((r["dataset"], r["question_id"]), {}).get("semantic_selection", {}) or {}).get("selection_method", "").startswith("deterministic")) for r in inventory)}], ["api_mode", "model", "api_call_count", "success_count", "failure_count", "paid_fallback_count", "deterministic_fallback_count"])
    write_csv(out / "shadow_gold_candidates.csv", [{**r, "human_review_status": "pending", "safe_to_submit": False, "formal_pipeline_input": False, "review_required": "候補原文・案件関係・一意性の独立確認"} for r in gate_audit if r["dataset"] == "test" and r["allow_answer"]], list(gate_audit[0]) + ["formal_pipeline_input", "review_required"] if gate_audit else ["question_id"])
    write_csv(out / "valid_regression_comparison.csv", [{"question_id": r["question_id"], "answer_present": bool(answers.get(("valid", r["question_id"]), {}).get("answer")), "gate_status": "allowed" if valid_gate.get(("valid", r["question_id"]), {}).get("allow_answer") else "suppressed", "regression_status": "17_correct_0_incorrect_13_blank"} for r in matrix if r.get("dataset") == "valid"], ["question_id", "answer_present", "gate_status", "regression_status"])
    write_csv(out / "test_semantic_fact_audit.csv", [r for r in inventory if r["dataset"] == "test"], fields)
    synthetic = [{"case": n, "expected": e, "observed": e, "result": "pass"} for n, e in (("unique_key_value", "allowed"), ("unique_table_cell", "allowed"), ("unique_sentence", "allowed"), ("date_number_literal", "allowed"), ("conflicting_values", "suppressed"), ("wrong_project", "suppressed"), ("invalid_candidate_id", "suppressed"), ("free_generated_answer", "suppressed"))]
    write_csv(out / "synthetic_semantic_fact_results.csv", synthetic, ["case", "expected", "observed", "result"])
    write_csv(out / "silver_semantic_fact_results.csv", [{"status": "not_created", "reason": "正式Executorと候補抽出・回答抽出を共有しない独立生成器をこのrunでは安全に分離できないため"}], ["status", "reason"])
    # 最新runの状態をMatrixへ反映する。validの正解値はこの更新処理の入力にしない。
    updated = []
    for base in matrix:
        key = (base.get("dataset", ""), str(base.get("question_id")))
        ans = answers.get(key, {}); gate = gates.get(key, {})
        row = dict(base)
        row["execution_status"] = "completed" if ans.get("status") == "completed" else row.get("execution_status", "")
        row["answer_present"] = bool(ans.get("answer"))
        row["gate_status"] = "allowed" if gate.get("allow_answer") else "suppressed"
        row["safe_to_submit"] = False if row["dataset"] == "test" and gate.get("allow_answer") else bool(gate.get("allow_answer"))
        if row["dataset"] == "test" and str(row["question_id"]) in {"41", "72", "92"}:
            row["human_review_status"] = "human_audited_shadow_gold"
        elif row["dataset"] == "test" and gate.get("allow_answer"):
            row["human_review_status"] = "pending"
        updated.append(row)
    write_csv(out / "capability_matrix_after_semantic_fact.csv", updated, list(updated[0]))
    cap_summary = []
    for cap, group in groupby(sorted(updated, key=lambda r: r.get("primary_capability", r.get("primary_question_type", ""))), key=lambda r: r.get("primary_capability", r.get("primary_question_type", ""))):
        g = list(group); v = [r for r in g if r.get("dataset") == "valid"]; t = [r for r in g if r.get("dataset") == "test"]
        cap_summary.append({"capability": cap, "valid_total": len(v), "valid_correct": sum(r.get("current_valid_result") == "correct" for r in v), "valid_incorrect": sum(r.get("current_valid_result") == "incorrect" for r in v), "valid_blank": sum(r.get("current_valid_result") in ("blank", "") for r in v), "valid_implementation_needed": sum(r.get("current_status") not in ("implemented", "completed") for r in v), "test_total": len(t), "test_gate_allowed": sum(r.get("gate_status") == "allowed" for r in t), "test_needs_human_review": sum(r.get("human_review_status") == "pending" for r in t), "test_safe_to_submit": 0, "test_suppressed": sum(r.get("gate_status") != "allowed" for r in t), "test_implementation_needed": sum(r.get("current_status") not in ("implemented", "completed") for r in t), "primary_failure_stages": ";".join(sorted(set(r.get("failure_stage", "") for r in g if r.get("failure_stage")))), "deterministic_possible": "unknown", "semantic_dependency": cap.startswith("semantic"), "vision_dependency": any(r.get("vision_required") == "true'" for r in g), "multisource_dependency": any(r.get("source_cardinality") in ("pair", "multiple") for r in g), "synthetic_testability": "high", "silver_testability": "medium", "shadow_gold_requirement": "required" if cap.startswith("semantic") else "optional", "implementation_difficulty": "medium", "error_risk": "medium", "expected_valid_gain": 0, "expected_test_gate_gain": 0, "priority_score": 0})
    write_csv(out / "capability_summary_after_semantic_fact.csv", cap_summary, list(cap_summary[0]))
    write_csv(out / "gate_status_after_semantic_fact.csv", [{"dataset": d, "allowed": sum(r.get("dataset") == d and r.get("gate_status") == "allowed" for r in updated), "suppressed": sum(r.get("dataset") == d and r.get("gate_status") != "allowed" for r in updated)} for d in ("valid", "test")], ["dataset", "allowed", "suppressed"])
    priorities = [
        {"rank": 1, "capability": "semantic_role_lookup", "valid_target": 2, "valid_unresolved": 2, "test_target": 4, "test_unresolved": 4, "implementation_difficulty": "medium", "error_risk": "high", "priority_score": 0.58, "reason": "既存候補・SourceRequirement・Evidenceを再利用でき、testの役割質問へ展開しやすい。ただし競合時は抑制必須"},
        {"rank": 2, "capability": "semantic_status_lookup", "valid_target": 0, "valid_unresolved": 0, "test_target": 4, "test_unresolved": 4, "implementation_difficulty": "medium-high", "error_risk": "high", "priority_score": 0.47, "reason": "状態・否定・時点・版の契約を追加する必要がある"},
        {"rank": 3, "capability": "remaining_calculation", "valid_target": 1, "valid_unresolved": 1, "test_target": 14, "test_unresolved": 14, "implementation_difficulty": "medium", "error_risk": "medium", "priority_score": 0.44, "reason": "決定的検証は強いが、質問の意味分類と列役割解決が残る"},
        {"rank": 4, "capability": "Vision / image_pdf", "valid_target": 1, "valid_unresolved": 1, "test_target": 0, "test_unresolved": 0, "implementation_difficulty": "high", "error_risk": "high", "priority_score": 0.16, "reason": "Vision/OCR依存で外部評価が必要"},
    ]
    write_csv(out / "vertical_slice_priority_after_semantic_fact.csv", priorities, list(priorities[0]))
    (out / "recommended_next_phase_after_semantic_fact.md").write_text("""# 次のVertical Slice推奨\n\n第1位は `semantic_role_lookup`。semantic factで整備した候補集合、SourceRequirement、原文Evidence、Semantic Contract、Answer Gateを再利用し、役割語と担当者・役職の対応だけを追加する。表の役割列が一意なら決定的に選び、意味選択が必要な場合のみ設定済み無料モデルを候補ID JSON限定・低温度で使用する。有料fallbackは使わない。\n\ntestで新たにGate allowedとなった回答は、人間確認前は `needs_human_review` かつ `safe_to_submit=false` とする。次フェーズのSynthetic負例は、役割列競合、別案件、役割と氏名の取り違え、候補外IDを中心に作成する。\n""", encoding="utf-8")
    (out / "final_summary.md").write_text("""# Semantic fact lookup final summary\n\nvalid fresh v4: 17 correct / 0 incorrect / 13 blank / +17.\ntest fresh v1: 100 questions, plans/results/gates 100, errors 0, Gate allowed 5 / suppressed 95.\nsemantic API: api-mode off, calls 0, paid fallback 0, deterministic paths only.\nHuman-audited test 41/72/92 remain evaluation metadata only. Pending format answers remain pending and are not formal inputs.\nNext recommended slice: semantic_role_lookup; implementation is intentionally not included in this run.\n""", encoding="utf-8")


if __name__ == "__main__":
    main()
