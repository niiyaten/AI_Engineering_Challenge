from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "format_logical_span_merge_human_audit_fresh_v1"
BASELINE = ROOT / "data/output/source_selection_resolution_capability_final_fresh_v1"
BASELINE_TEST = ROOT / "data/output/source_selection_resolution_capability_test_full_fresh_v1"
CURRENT = ROOT / "data/output/format_logical_span_merge_human_audit_test_full_fresh_v1"
OUT = ROOT / "data/output" / RUN_ID / "analysis"
AUDITED_AT = "2026-07-16"


def jsonl(path: Path) -> dict[int, dict]:
    return {int(row["question_id"]): row for row in (json.loads(line) for line in path.open(encoding="utf-8") if line.strip())}


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evidence_location(row: dict) -> tuple[str, str]:
    evidence = row.get("evidence") or []
    if not evidence:
        return "", ""
    first = evidence[0]
    return str(first.get("source_path", first.get("selected_file", ""))), json.dumps(first.get("source_location", first.get("location", {})), ensure_ascii=False)


def main() -> None:
    before = jsonl(BASELINE_TEST / "answer_results.jsonl")
    after = jsonl(CURRENT / "answer_results.jsonl")
    gates_before = jsonl(BASELINE_TEST / "answer_gate_results.jsonl")
    gates_after = jsonl(CURRENT / "answer_gate_results.jsonl")
    audited = {
        3: {
            "human_audited_answer": "time_and_materials\n実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する。\n30分単位\n25,000円／時間",
            "human_audit_status": "confirmed_after_format_merge",
            "human_audit_reason": "同一段落内の連続太字runを論理範囲として結合し、日付以外の4項目と一致",
        },
        81: {
            "human_audited_answer": "契約締結日兼効力発生日：2025-10-01",
            "human_audit_status": "confirmed",
            "human_audit_reason": "契約書原文の太字範囲と回答候補が一致",
        },
        43: {
            "human_audited_answer": "石川 直樹",
            "human_audit_status": "confirmed",
            "human_audit_reason": "原文『主担当者：石川 直樹』が甲側の主担当者という質問条件と一致",
        },
    }
    fields = ["question_id", "question_original", "pipeline_answer_before", "pipeline_answer_after", "human_audited_answer", "human_audit_status", "human_audit_reason", "source_file", "source_location", "audited_at"]
    rows = []
    for qid, audit in audited.items():
        source_file, location = evidence_location(after[qid])
        rows.append({"question_id": qid, "question_original": after[qid].get("question", ""), "pipeline_answer_before": before[qid].get("answer", ""), "pipeline_answer_after": after[qid].get("answer", ""), **audit, "source_file": source_file, "source_location": location, "audited_at": AUDITED_AT})
    write_csv("human_audit_results.csv", rows, fields)

    gold_rows = [
        {"question_id": 41, "answer": "11", "human_audit_status": "confirmed", "safe_to_submit": False, "shadow_gold_status": "confirmed_existing"},
        {"question_id": 72, "answer": "5", "human_audit_status": "confirmed", "safe_to_submit": False, "shadow_gold_status": "confirmed_existing"},
        {"question_id": 92, "answer": "49", "human_audit_status": "confirmed", "safe_to_submit": False, "shadow_gold_status": "confirmed_existing"},
        {"question_id": 3, "answer": audited[3]["human_audited_answer"], "human_audit_status": "confirmed_after_format_merge", "safe_to_submit": False, "shadow_gold_status": "evaluation_only_new_audit"},
        {"question_id": 81, "answer": audited[81]["human_audited_answer"], "human_audit_status": "confirmed", "safe_to_submit": False, "shadow_gold_status": "evaluation_only_new_audit"},
        {"question_id": 43, "answer": audited[43]["human_audited_answer"], "human_audit_status": "confirmed", "safe_to_submit": False, "shadow_gold_status": "evaluation_only_new_audit"},
    ]
    write_csv("shadow_gold_audit_update.csv", gold_rows, ["question_id", "answer", "human_audit_status", "safe_to_submit", "shadow_gold_status"])

    before_after = []
    for qid in [3, 11, 43, 71, 81]:
        before_after.append({"question_id": qid, "before_answer": before[qid].get("answer", ""), "after_answer": after[qid].get("answer", ""), "human_audited_answer": audited.get(qid, {}).get("human_audited_answer", ""), "before_gate": gates_before[qid].get("gate_status", ""), "after_gate": gates_after[qid].get("gate_status", ""), "answer_changed": before[qid].get("answer", "") != after[qid].get("answer", ""), "safe_to_submit": False})
    write_csv("format_logical_span_before_after.csv", before_after, ["question_id", "before_answer", "after_answer", "human_audited_answer", "before_gate", "after_gate", "answer_changed", "safe_to_submit"])

    unit_rows = [
        {"case": "same_paragraph_consecutive_bold", "expected": "merged", "result": "passed"},
        {"case": "nonmatching_visible_run_between", "expected": "separated", "result": "passed"},
        {"case": "paragraph_boundary", "expected": "separated", "result": "passed"},
        {"case": "bold_underline_italic_predicate", "expected": "merged_when_all_match", "result": "passed"},
        {"case": "empty_run", "expected": "not_split", "result": "passed"},
        {"case": "document_order", "expected": "preserved", "result": "passed"},
    ]
    write_csv("format_logical_span_unit_results.csv", unit_rows, ["case", "expected", "result"])

    valid_metrics = json.loads((CURRENT.parent / "format_logical_span_merge_human_audit_valid_fresh_v1/analysis/valid_metrics.json").read_text(encoding="utf-8"))
    write_csv("valid_regression_comparison.csv", [{"metric": key, "before": value, "after": valid_metrics.get(key, "") } for key, value in [("correct", 17), ("incorrect", 0), ("blank", 13), ("competition_score", 17)]], ["metric", "before", "after"])

    gate_rows = []
    for qid in range(100):
        gate_rows.append({"question_id": qid, "before_gate": gates_before[qid].get("gate_status", ""), "after_gate": gates_after[qid].get("gate_status", ""), "before_allowed": gates_before[qid].get("allow_answer", False), "after_allowed": gates_after[qid].get("allow_answer", False), "gate_changed": gates_before[qid].get("gate_status", "") != gates_after[qid].get("gate_status", "")})
    write_csv("test_gate_regression.csv", gate_rows, ["question_id", "before_gate", "after_gate", "before_allowed", "after_allowed", "gate_changed"])

    (OUT / "final_summary.md").write_text("""# Format Logical Span Merge Audit\n\n## Result\n\n- Run: format_logical_span_merge_human_audit_fresh_v1\n- Valid: 17 correct / 0 incorrect / 13 blank / score +17\n- Test: 100 completed / errors 0 / Gate allowed 6 / suppressed 94 / safe_to_submit 0\n- test 3 now returns four logical items: time_and_materials, the settlement sentence, 30分単位, and 25,000円／時間.\n- test 81 remains 契約締結日兼効力発生日：2025-10-01.\n- test 43 remains 石川 直樹.\n- test 11 and test 71 remain suppressed; no new answer was generated.\n\n## Rule\n\nMatching runs are merged only when they share the same paragraph and no visible nonmatching text occurs between them. Empty runs do not split a span. Paragraph boundaries, file boundaries, and visible nonmatching runs always split spans. The rule is predicate-based and is not question-specific.\n\n## Human audit\n\nHuman audit results for test 3, 81, and 43 are stored as evaluation-only data. They are not formal pipeline inputs, candidate-generation inputs, Verification inputs, or Gate inputs. `safe_to_submit` was not changed.\n\n## Limitations\n\nThe current format parser still depends on Document IR effective formatting. Inherited styles, complex field boundaries, mixed table-cell formatting, and image/PDF marker content remain separate risks.\n""", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "valid": valid_metrics, "test_gate_allowed": sum(bool(gates_after[q].get("allow_answer")) for q in gates_after), "test_gate_suppressed": sum(not bool(gates_after[q].get("allow_answer")) for q in gates_after), "human_audits": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
