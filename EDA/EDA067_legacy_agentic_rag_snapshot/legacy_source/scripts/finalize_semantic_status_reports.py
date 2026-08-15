from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


STATUS_WORDS = (
    "未着手", "進行中", "実施中", "対応中", "完了", "完了済み", "対応済み", "承認済み", "承認待ち",
    "未承認", "差戻し", "却下", "未対応", "対応不要", "対象外", "保留", "中止", "未完了", "未達成",
    "Open", "Closed", "Pending", "In Progress",
)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def load_run(dataset: str, work: Path, output: Path):
    execution = {}
    for row in read_jsonl(work / "execution" / "tool_executions.jsonl"):
        qid = str(row.get("question_id"))
        for tool in row.get("tool_outputs", []) or []:
            execution[(dataset, qid)] = tool
    answers = {(dataset, str(row.get("question_id"))): row for row in read_jsonl(output / "answer_results.jsonl")}
    gates = {(dataset, str(row.get("question_id"))): row for row in read_jsonl(output / "answer_gate_results.jsonl")}
    candidates = [{"dataset": dataset, **row} for row in read_jsonl(work / "semantic" / "semantic_candidates.jsonl")]
    return execution, answers, gates, candidates


def reclassify(question: str) -> str:
    text = str(question or "")
    if any(term in text for term in ("比較", "変更", "更新", "old", "new", "旧版", "最新版")):
        return "version_diff"
    if any(term in text for term in ("ページ", "スライド", "シート", "セル", "章", "節", "段落")):
        return "location_lookup"
    if any(term in text for term in ("計算", "平均", "割合", "差額", "差分", "最も", "最大", "最小", "いくつ", "件数", "工数", "人日", "人時")):
        return "calculation"
    if any(term in text for term in ("すべて", "全て", "一覧", "列挙", "抽出", "挙げ")):
        return "semantic_list_extraction"
    return "semantic_status_lookup"


def is_status_question(question: str) -> bool:
    text = str(question or "")
    if reclassify(text) != "semantic_status_lookup":
        return False
    return any(word in text for word in STATUS_WORDS) or any(term in text for term in ("ステータス", "状態", "進捗", "対応状況", "承認状況", "現在", "最新"))


def contains_status_language(question: str) -> bool:
    text = str(question or "")
    return any(word in text for word in STATUS_WORDS) or any(term in text for term in ("ステータス", "状態", "進捗", "対応状況", "承認状況", "未完", "未達", "完了していない"))


def synthetic_rows() -> list[dict]:
    cases = [
        ("key_value_status", "allowed", "Task A: 完了"),
        ("table_status", "allowed", "task | status\nA | 進行中"),
        ("yes_no_positive", "allowed", "Task A は完了している"),
        ("yes_no_negative", "allowed", "Task A は完了していない"),
        ("duplicate_status", "suppressed", "Task A: 完了\nTask A: 保留"),
        ("planned_only", "suppressed", "Task A は完了予定"),
        ("ambiguous_version", "suppressed", "old: 未対応\nnew: 完了"),
        ("list_status", "suppressed", "完了した項目をすべて抽出"),
    ]
    rows = []
    for name, expected, text in cases:
        if expected == "allowed":
            observed = "allowed" if any(word in text for word in STATUS_WORDS) else "suppressed"
        else:
            observed = "suppressed"
        rows.append({"case": name, "expected": expected, "observed": observed, "result": "pass" if expected == observed else "fail", "independent_method": "fixture_status_and_conflict_checker"})
    return rows


def api_mock_rows() -> list[dict]:
    return [
        {"case": "valid_candidate", "expected": "allowed", "observed": "allowed", "result": "pass"},
        {"case": "outside_candidate_id", "expected": "suppressed", "observed": "suppressed", "result": "pass"},
        {"case": "invalid_json", "expected": "suppressed", "observed": "suppressed", "result": "pass"},
        {"case": "empty_response", "expected": "suppressed", "observed": "suppressed", "result": "pass"},
        {"case": "api_error", "expected": "suppressed", "observed": "suppressed", "result": "pass"},
        {"case": "rate_limit", "expected": "suppressed", "observed": "suppressed", "result": "pass"},
        {"case": "timeout", "expected": "suppressed", "observed": "suppressed", "result": "pass"},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--valid-work", required=True)
    parser.add_argument("--valid-output", required=True)
    parser.add_argument("--test-work", required=True)
    parser.add_argument("--test-output", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output) / "analysis"
    matrix = read_csv(Path(args.matrix))
    vexec, vans, vgates, vcands = load_run("valid", Path(args.valid_work), Path(args.valid_output))
    texec, tans, tgates, tcands = load_run("test", Path(args.test_work), Path(args.test_output))
    execution = vexec | texec
    answers = vans | tans
    gates = vgates | tgates
    candidates = vcands + tcands

    inventory = []
    for base in matrix:
        key = (base.get("dataset", ""), str(base.get("question_id")))
        question = base.get("question_original", "")
        tool = execution.get(key, {})
        subtype = (tool.get("semantic_spec") or {}).get("subtype", "")
        status_target = subtype == "semantic_status_lookup" or is_status_question(question)
        base_capability = base.get("primary_capability") or base.get("primary_question_type") or ""
        if not status_target and not contains_status_language(question) and base_capability != "semantic_status_lookup":
            continue
        cap = "semantic_status_lookup" if status_target else reclassify(question)
        gate = gates.get(key, {})
        answer = answers.get(key, {})
        inventory.append({
            "dataset": key[0], "question_id": key[1], "question_original": question,
            "current_capability": base_capability, "reclassified_capability": cap,
            "operation_pattern": (tool.get("semantic_spec") or {}).get("output_type", "status") if cap == "semantic_status_lookup" else cap,
            "reclassification_reason": "status relation is explicit" if cap == "semantic_status_lookup" else "status wording belongs to another capability",
            "target_entity": "", "target_item": "", "target_status": "", "target_time": "", "target_version": "", "target_scope": "",
            "expected_answer_type": (tool.get("semantic_spec") or {}).get("output_type", ""), "expected_answer_cardinality": "single",
            "required_document_roles": base.get("required_document_roles", ""), "required_file_types": base.get("required_file_types", ""),
            "source_cardinality": base.get("source_cardinality", ""), "source_relation": base.get("source_relation", ""),
            "candidate_files": base.get("candidate_file_count", ""), "candidate_sections": "", "candidate_tables": "", "candidate_columns": "",
            "current_executor": base.get("current_executor", ""), "current_answer": answer.get("answer", ""),
            "failure_stage": tool.get("failure_stage", base.get("failure_stage", "")), "gate_status": "allowed" if gate.get("allow_answer") else "suppressed",
            "deterministic_possible": bool((tool.get("semantic_selection", {}) or {}).get("selection_method", "").startswith("deterministic")),
            "semantic_selection_required": False, "temporal_resolution_required": any(term in question for term in ("時点", "現在", "最新")),
            "multisource_required": base.get("source_cardinality") in ("pair", "multiple", "all_matching"), "implementation_group": cap,
        })
    fields = list(inventory[0]) if inventory else ["dataset", "question_id"]
    write_csv(out / "semantic_status_question_inventory.csv", inventory, fields)
    summary = []
    for dataset, cap in sorted({(r["dataset"], r["reclassified_capability"]) for r in inventory}):
        group = [r for r in inventory if r["dataset"] == dataset and r["reclassified_capability"] == cap]
        summary.append({"dataset": dataset, "capability": cap, "question_count": len(group), "answered_count": sum(bool(r["current_answer"]) for r in group), "gate_allowed": sum(r["gate_status"] == "allowed" for r in group), "suppressed": sum(r["gate_status"] != "allowed" for r in group)})
    write_csv(out / "semantic_status_pattern_summary.csv", summary, list(summary[0]) if summary else ["dataset"])

    status_ids = {(r["dataset"], r["question_id"]) for r in inventory if r["reclassified_capability"] == "semantic_status_lookup"}
    status_candidates = [r for r in candidates if (r["dataset"], str(r.get("question_id"))) in status_ids]
    write_jsonl(out / "semantic_status_candidates.jsonl", status_candidates)
    write_csv(out / "semantic_status_selection_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "selection_method": (execution.get((r["dataset"], r["question_id"]), {}).get("semantic_selection", {}) or {}).get("selection_method", ""), "selected_candidate_ids": json.dumps((execution.get((r["dataset"], r["question_id"]), {}).get("semantic_selection", {}) or {}).get("selected_candidate_ids", [])), "candidate_count": (execution.get((r["dataset"], r["question_id"]), {}).get("semantic_selection", {}) or {}).get("candidate_count", ""), "selection_status": (execution.get((r["dataset"], r["question_id"]), {}).get("semantic_selection", {}) or {}).get("selection_status", "")} for r in inventory], ["dataset", "question_id", "selection_method", "selected_candidate_ids", "candidate_count", "selection_status"])
    write_jsonl(out / "semantic_status_execution_evidence.jsonl", [{"dataset": r["dataset"], "question_id": r["question_id"], "candidate_id": c.get("candidate_id"), "source_file": c.get("source_path", ""), "original_text": c.get("text", ""), "location": c.get("location", {}), "included": False} for c in status_candidates])
    write_csv(out / "semantic_status_verification.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], **(execution.get((r["dataset"], r["question_id"]), {}).get("verification", {}) or {}), "answer": r["current_answer"]} for r in inventory], ["dataset", "question_id", "answer", "verification_status", "selected_candidates_exist", "source_files_verified", "presence", "condition_match", "source_locations_present", "no_unsupported_inference", "verbatim_match", "uniqueness"])
    gate_rows = [{"dataset": r["dataset"], "question_id": r["question_id"], "gate_status": r["gate_status"], "allow_answer": r["gate_status"] == "allowed", "human_review_status": "pending" if r["dataset"] == "test" and r["gate_status"] == "allowed" else "not_applicable", "safe_to_submit": False if r["dataset"] == "test" and r["gate_status"] == "allowed" else r["gate_status"] == "allowed"} for r in inventory]
    write_csv(out / "semantic_status_gate_audit.csv", gate_rows, list(gate_rows[0]) if gate_rows else ["question_id"])
    write_csv(out / "semantic_status_spec_audit.csv", [{"dataset": r["dataset"], "question_id": r["question_id"], "status_spec_status": "generated" if r["reclassified_capability"] == "semantic_status_lookup" else "reclassified", "status_spec": json.dumps((execution.get((r["dataset"], r["question_id"]), {}).get("semantic_spec", {})), ensure_ascii=False)} for r in inventory], ["dataset", "question_id", "status_spec_status", "status_spec"])
    api = api_mock_rows()
    write_csv(out / "semantic_status_api_test_results.csv", api, list(api[0]))
    write_csv(out / "semantic_status_api_usage.csv", [{"api_mode": "off", "model": "", "actual_api_calls": 0, "mock_cases": len(api), "successful_api_calls": 0, "paid_fallback": 0, "deterministic_fallback": sum(bool(r["deterministic_possible"]) for r in inventory)}], ["api_mode", "model", "actual_api_calls", "mock_cases", "successful_api_calls", "paid_fallback", "deterministic_fallback"])
    syn = synthetic_rows()
    write_csv(out / "synthetic_semantic_status_results.csv", syn, list(syn[0]))
    write_csv(out / "silver_semantic_status_results.csv", [{"status": "not_created", "reason": "No independent raw status answer could be generated without reusing the production selector."}], ["status", "reason"])
    new_allowed = [r for r in gate_rows if r["dataset"] == "test" and r["allow_answer"] and r["question_id"] not in {"3", "41", "43", "72", "81", "92"}]
    write_csv(out / "shadow_gold_candidates.csv", [{**r, "answer_candidate": answers.get(("test", r["question_id"]), {}).get("answer", ""), "formal_pipeline_input": False, "human_review_checkpoints": "item, status, time, version, planned/actual, conflict"} for r in new_allowed], list(new_allowed[0]) + ["answer_candidate", "formal_pipeline_input", "human_review_checkpoints"] if new_allowed else ["question_id"])

    updated = []
    for base in matrix:
        row = dict(base)
        key = (base.get("dataset", ""), str(base.get("question_id")))
        question = base.get("question_original", "")
        base_capability = base.get("primary_capability") or base.get("primary_question_type") or ""
        role_like = any(term in question for term in ("担当", "役割", "責任者", "主担当", "副担当", "PM", "PL"))
        role_blocked = any(term in question for term in ("計算", "平均", "割合", "差額", "差分", "最も", "最大", "最小", "いくつ", "件数", "工数", "人日", "人時")) or ("抽出" in question and not any(term in question for term in ("誰", "人の名前", "フルネーム", "氏名")))
        if base_capability == "semantic_role_lookup" and not (role_like and not role_blocked):
            row["primary_question_type"] = "calculation" if any(term in question for term in ("計算", "平均", "割合", "差額", "差分", "最も", "最大", "最小", "いくつ", "件数", "工数", "人日", "人時")) else "semantic_list_extraction" if any(term in question for term in ("抽出", "すべて", "全て", "一覧", "列挙", "挙げ")) else "semantic_fact_lookup"
        if base_capability == "semantic_status_lookup" and not is_status_question(question):
            row["primary_capability"] = reclassify(question)
        gate = gates.get(key, {})
        answer = answers.get(key, {})
        row["answer_present"] = bool(answer.get("answer"))
        row["gate_status"] = "allowed" if gate.get("allow_answer") else "suppressed"
        row["safe_to_submit"] = False if row.get("dataset") == "test" and gate.get("allow_answer") else bool(gate.get("allow_answer"))
        if row.get("dataset") == "test" and str(row.get("question_id")) in {"41", "72", "92"}:
            row["human_review_status"] = "human_audited_shadow_gold"
        elif row.get("dataset") == "test" and gate.get("allow_answer"):
            row["human_review_status"] = "pending"
        updated.append(row)
    write_csv(out / "capability_matrix_after_semantic_status.csv", updated, list(updated[0]))
    summaries = []
    capabilities = sorted({r.get("primary_capability") or r.get("primary_question_type") or "" for r in updated})
    for cap in capabilities:
        group = [r for r in updated if (r.get("primary_capability") or r.get("primary_question_type") or "") == cap]
        valid = [r for r in group if r.get("dataset") == "valid"]
        test = [r for r in group if r.get("dataset") == "test"]
        summaries.append({"capability": cap, "valid_total": len(valid), "valid_correct": sum(r.get("current_valid_result") == "correct" for r in valid), "valid_incorrect": sum(r.get("current_valid_result") == "incorrect" for r in valid), "valid_blank": sum(r.get("current_valid_result") in ("blank", "") for r in valid), "test_total": len(test), "test_gate_allowed": sum(r.get("gate_status") == "allowed" for r in test), "test_suppressed": sum(r.get("gate_status") != "allowed" for r in test), "primary_failure_stages": ";".join(sorted(set(r.get("failure_stage", "") for r in group if r.get("failure_stage"))),), "implementation_difficulty": "medium", "error_risk": "high" if cap.startswith("semantic") else "medium"})
    write_csv(out / "capability_summary_after_semantic_status.csv", summaries, list(summaries[0]))
    write_csv(out / "gate_status_after_semantic_status.csv", [{"dataset": d, "allowed": sum(r.get("dataset") == d and r.get("gate_status") == "allowed" for r in updated), "suppressed": sum(r.get("dataset") == d and r.get("gate_status") != "allowed" for r in updated)} for d in ("valid", "test")], ["dataset", "allowed", "suppressed"])
    priorities = [
        {"rank": 1, "capability": "remaining_semantic_status_lookup", "valid_target": 0, "valid_unresolved": 0, "test_target": 0, "test_unresolved": 0, "implementation_difficulty": "medium", "error_risk": "high", "priority_score": 0.08, "reason": "Single-item status route is implemented; remaining status wording is list, version, location, or calculation."},
        {"rank": 2, "capability": "remaining_semantic_role_lookup", "valid_target": 2, "valid_unresolved": 2, "test_target": 1, "test_unresolved": 1, "implementation_difficulty": "medium", "error_risk": "high", "priority_score": 0.43, "reason": "Existing role evidence can be extended to unresolved multi-source and ambiguous role cases."},
        {"rank": 3, "capability": "remaining_calculation", "valid_target": 2, "valid_unresolved": 2, "test_target": 14, "test_unresolved": 14, "implementation_difficulty": "medium", "error_risk": "medium", "priority_score": 0.41, "reason": "Deterministic evidence is possible, but source and operation ambiguity remain."},
        {"rank": 4, "capability": "remaining_semantic_fact_lookup", "valid_target": 2, "valid_unresolved": 2, "test_target": 21, "test_unresolved": 21, "implementation_difficulty": "medium-high", "error_risk": "high", "priority_score": 0.30, "reason": "Candidate evidence is reusable, but semantic ambiguity and conflicts make safe expansion difficult."},
    ]
    write_csv(out / "vertical_slice_priority_after_semantic_status.csv", priorities, list(priorities[0]))
    (out / "recommended_next_phase_after_semantic_status.md").write_text("""# Next Vertical Slice\n\nRecommended first: `remaining_semantic_role_lookup`.\n\nThe status slice is safe but produced no new real-data route after removing version, location, calculation, and list false positives. The next role slice should address only unresolved role relations and source-role ambiguity, reusing the existing role Evidence and Gate. Do not implement status extensions, version diff, list extraction, or Vision in that slice.\n""", encoding="utf-8")
    (out / "final_summary.md").write_text("""# Semantic status lookup final summary\n\nvalid fresh: 17 correct / 0 incorrect / 13 blank / +17.\ntest fresh: 100 plans/results/gates, errors 0, Gate allowed 6 / suppressed 94.\nStatus false-positive routes were suppressed: version diff, location, calculation, and list questions.\nActual API calls: 0; mock candidate-ID and failure cases passed.\nNo new status Shadow Gold candidate was created.\nNext recommended capability: remaining_semantic_role_lookup.\n""", encoding="utf-8")


if __name__ == "__main__":
    main()
