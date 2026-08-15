from __future__ import annotations

import argparse
import csv
import shutil
from collections import Counter
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--matrix-run", required=True)
    parser.add_argument("--calculation-run", required=True)
    parser.add_argument("--output-run", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / "data/output" / args.matrix_run / "analysis/capability_matrix_all_130_v3.csv"
    out = root / "data/output" / args.output_run / "analysis"
    rows = read_csv(source)
    calc = read_csv(root / "data/output" / args.calculation_run / "analysis/calculation_question_inventory.csv")
    calc_by_id = {str(x["question_id"]): x for x in calc}
    for row in rows:
        qid = str(row.get("question_id", ""))
        if row.get("dataset") == "valid" and "残余リスク" in row.get("question_original", ""):
            row["primary_capability"] = "semantic_fact_lookup"
            row["recommended_next_action"] = "semantic fact extraction; calculation classification error"
        if qid in calc_by_id:
            c = calc_by_id[qid]
            row["primary_capability"] = c.get("reclassified_pattern", row.get("primary_capability", ""))
            row["failure_stage"] = c.get("failure_stage", row.get("failure_stage", ""))
            row["gate_status"] = c.get("gate_status", row.get("gate_status", ""))
            row["answer_present"] = "true" if c.get("current_answer") else "false"
            row["recommended_next_action"] = "reclassified as semantic_fact_lookup" if c.get("reclassified_pattern") == "semantic_fact_lookup" else row.get("recommended_next_action", "")
    write_csv(out / "capability_matrix_after_calculation.csv", rows)
    grouped = {}
    for capability in sorted({x.get("primary_capability", "unknown") for x in rows}):
        valid = [x for x in rows if x.get("dataset") == "valid" and x.get("primary_capability") == capability]
        test = [x for x in rows if x.get("dataset") == "test" and x.get("primary_capability") == capability]
        grouped[capability] = {"capability": capability, "valid_total": len(valid), "valid_correct": sum(x.get("current_valid_result") == "correct" for x in valid), "valid_incorrect": sum(x.get("current_valid_result") == "incorrect" for x in valid), "valid_blank": sum(x.get("current_valid_result") != "correct" for x in valid), "valid_implementation_needed": sum(x.get("current_valid_result") != "correct" and x.get("current_status") not in {"implemented", "completed"} for x in valid), "test_total": len(test), "test_gate_allowed": sum(x.get("gate_status") == "allowed" for x in test), "test_needs_human_review": sum(x.get("human_review_status") == "needs_human_review" for x in test), "test_safe_to_submit": 0, "test_suppressed": sum(x.get("gate_status") != "allowed" for x in test), "test_implementation_needed": sum(x.get("gate_status") != "allowed" for x in test), "primary_failure_stages": "; ".join(sorted(Counter(x.get("failure_stage", "") or "none" for x in valid + test).keys())), "deterministic_possible": "true", "semantic_dependency": "true" if "semantic" in capability else "false", "vision_dependency": "true" if "vision" in capability or "chart" in capability else "false", "multisource_dependency": "true" if "cross_file" in capability or "difference" in capability else "false"}
    summary = list(grouped.values())
    write_csv(out / "capability_summary_after_calculation.csv", summary)
    write_csv(out / "gate_status_after_calculation.csv", [{"gate_status": status, "count": sum(x.get("gate_status") == status for x in rows if x.get("dataset") == "test")} for status in ["allowed", "suppressed", "needs_human_review"]])
    candidates = [
        ("semantic_fact_lookup", 1, 11, 1, 2.0, 2, 2, "既存IRと候補検索を再利用。意味選択だけを無料LLMに限定し、原文Evidenceで検証"),
        ("remaining_calculation", 1, 9, 1, 2.5, 3, 2, "ratio/ranking/係数/工数の明示入力束縛を追加。曖昧条件は抑制"),
        ("cross_file_calculation", 0, 1, 1, 3.5, 4, 3, "既存difference以外のjoinは資料関係とキー検証が必要"),
        ("semantic_role_lookup", 0, 8, 8, 3.5, 4, 3, "役割語の意味選択が必要で、Evidenceの一意性検証が難しい"),
        ("semantic_status_lookup", 0, 6, 6, 3.5, 4, 3, "状態語の揺れと複数候補の曖昧性が主リスク"),
        ("version_diff", 0, 1, 1, 4.0, 5, 4, "版ペアの確定と意味差分の検証が必要"),
        ("document_scope_item_count", 0, 1, 1, 2.5, 3, 2, "文書構造からスコープ外項目を列挙し全件性を検証"),
        ("feature_category_occurrence_count", 0, 1, 1, 3.0, 3, 3, "Notebook/分析結果のカテゴリ抽出と出現数の定義確認が必要"),
        ("vision_image_pdf", 1, 0, 0, 5.0, 5, 5, "OCR/Vision依存のため現時点では延期"),
        ("chart_reading", 0, 1, 1, 5.0, 5, 5, "グラフ値の根拠抽出にVision依存"),
    ]
    priority = []
    for order, (capability, valid_count, test_count, unresolved, difficulty, risk, evidence, reason) in enumerate(candidates, 1):
        score = round((test_count + valid_count * 2 + evidence) / (difficulty * risk), 4)
        priority.append({"recommended_order": order, "capability": capability, "valid_question_count": valid_count, "valid_unresolved": unresolved if valid_count else 0, "test_question_count": test_count, "test_implementation_needed": unresolved, "expected_valid_gain": 1 if valid_count and unresolved else 0, "expected_test_gate_gain": max(0, test_count - 1), "implementation_difficulty": difficulty, "error_risk": risk, "evidence_verifiability": evidence, "priority_score": score, "reason": reason})
    priority.sort(key=lambda x: x["priority_score"], reverse=True)
    for index, row in enumerate(priority, 1):
        row["recommended_order"] = index
    write_csv(out / "vertical_slice_priority_after_calculation.csv", priority)
    top = priority[:3]
    lines = ["# Recommended Next Phase After Calculation", "", "Calculation phase completed without valid regression. No next Executor is implemented in this report.", "", "## Top 3"]
    for index, row in enumerate(top, 1):
        lines += [f"{index}. {row['capability']}", f"- valid: {row['valid_question_count']} (unresolved {row['valid_unresolved']})", f"- test: {row['test_question_count']} (implementation needed {row['test_implementation_needed']})", f"- priority score: {row['priority_score']}", f"- reason: {row['reason']}", ""]
    lines += ["## First choice scope", "semantic_fact_lookupのうち、対象資料と見出しをPythonで一意に絞れる短い原文抽出だけを対象にする。LLMを使う場合も候補ID選択に限定し、最終回答はDocument IRの原文から生成する。候補の一意性、案件・資料役割、回答とEvidenceの一致をGate前に検証する。", "", "## Model", "意味選択が必要な場合は設定済みの無料OpenRouterモデルを低温度・JSON候補ID出力で使用する。有料fallbackは行わない。"]
    (out / "recommended_next_phase_after_calculation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"matrix_rows": len(rows), "summary_rows": len(summary), "top": [x["capability"] for x in top]})


if __name__ == "__main__":
    main()
