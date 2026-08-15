from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

SLICE_TYPES = [
    "semantic_document_lookup", "location_lookup", "verbatim_extraction",
    "format_extraction", "identifier_verbatim", "version_diff", "code_inspection",
    "notebook_inspection", "table_lookup", "table_filter", "table_aggregation",
    "calculation", "chart_reading", "vision_spatial", "cross_file_aggregation",
    "generated_python", "unsupported", "unknown",
]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", "".join(ch for ch in text if unicodedata.category(ch) != "Cf")).strip()


def classify(question: str) -> tuple[str, list[str], list[str]]:
    q = norm(question)
    secondary: list[str] = []
    file_types = re.findall(r"\.(xlsx|xls|csv|tsv|pptx|docx|pdf|py|ipynb)\b", q, re.I)
    if ".ipynb" in q or "Notebook" in q:
        primary = "notebook_inspection"
    elif ".py" in q or "Python" in q or "コード" in q:
        primary = "code_inspection"
    elif "差分" in q or "比較" in q or "old" in q or "新版" in q:
        primary = "version_diff"
    elif "グラフ" in q or "ヒートマップ" in q or "figure_" in q:
        primary = "chart_reading"
    elif "ページ" in q or "スライド" in q or "何章" in q:
        primary = "location_lookup"
    elif "色" in q or "太字" in q or "ハイライト" in q or "マーカー" in q:
        primary = "format_extraction"
    elif "計算" in q or "平均" in q or "合計" in q or "割合" in q or "最も" in q:
        primary = "calculation"
    elif "すべて" in q and "ID" in q:
        primary = "identifier_verbatim"
    elif "表" in q and any(word in q for word in ("列", "行", "セル", "条件")):
        primary = "table_lookup"
    elif "抽出" in q or "答えて" in q or "何" in q:
        primary = "semantic_document_lookup"
    else:
        primary = "unknown"
    if "xlsx" in q or "csv" in q:
        secondary.append("table_lookup")
    if "金額" in q or "数値" in q:
        secondary.append("calculation")
    if "複数" in q or "全案件" in q:
        secondary.append("cross_file_aggregation")
    return primary, list(dict.fromkeys(secondary)), list(dict.fromkeys(file_types))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--valid-questions", type=Path, required=True)
    parser.add_argument("--test-questions", type=Path, required=True)
    args = parser.parse_args()
    out = args.run_dir.parent.parent / "output" / args.run_dir.name / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    answers = {int(row["question_id"]): row for row in read_jsonl(out.parent / "answer_results.jsonl")}
    rows = list(csv.DictReader(args.valid_questions.open(encoding="utf-8-sig", newline="")))
    inventory = []
    for row in rows:
        qid = int(row.get("question_id", row.get("index", 0)))
        answer = answers.get(qid, {})
        if answer.get("answer", ""):
            continue
        primary, secondary, file_types = classify(row["question"])
        selected = answer.get("selected_files", [])
        operations = answer.get("operations_executed", [])
        inventory.append({
            "question_id": qid,
            "question_original": row["question"],
            "question_normalized": norm(row["question"]),
            "primary_question_type": primary,
            "secondary_question_types": ";".join(secondary),
            "required_file_types": ";".join(file_types),
            "required_document_roles": "",
            "required_operations": ";".join(operations),
            "current_executor": ";".join(operations),
            "implementation_status": answer.get("status", "unknown"),
            "current_failure_stage": answer.get("failure_stage", "unknown"),
            "external_api_required": primary == "semantic_document_lookup",
            "vision_required": primary in {"vision_spatial", "chart_reading"},
            "deterministic_processing_possible": primary not in {"semantic_document_lookup", "vision_spatial", "chart_reading"},
            "candidate_file_count": len(selected),
            "actual_used_file_count": len(selected),
            "current_gate_status": answer.get("gate_status", ""),
            "suppression_reason": ";".join(answer.get("warnings", [])),
        })
    fields = list(inventory[0]) if inventory else ["question_id"]
    with (out / "remaining_question_inventory.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(inventory)
    counts = Counter(row["primary_question_type"] for row in inventory)
    with (out / "remaining_question_type_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_type", "valid_question_count"]); writer.writeheader()
        writer.writerows({"question_type": key, "valid_question_count": counts.get(key, 0)} for key in SLICE_TYPES)
    test_rows = list(csv.DictReader(args.test_questions.open(encoding="utf-8-sig", newline="")))
    test_counts = Counter(classify(row["question"])[0] for row in test_rows)
    candidates = []
    for kind in ("semantic_document_lookup", "location_lookup", "version_diff", "code_inspection", "notebook_inspection", "cross_file_aggregation", "chart_reading", "vision_spatial"):
        valid_count = counts.get(kind, 0); test_count = test_counts.get(kind, 0)
        deterministic = kind in {"location_lookup", "code_inspection", "notebook_inspection", "version_diff"}
        vision = kind in {"chart_reading", "vision_spatial"}
        effort = {"semantic_document_lookup": 4, "location_lookup": 2, "version_diff": 5, "code_inspection": 3, "notebook_inspection": 3, "cross_file_aggregation": 5, "chart_reading": 5, "vision_spatial": 6}[kind]
        score = (valid_count + test_count * 0.5 + (2 if deterministic else 0)) / effort
        candidates.append({
            "question_type": kind, "valid_question_count": valid_count, "test_question_count": test_count,
            "already_partially_implemented": kind == "location_lookup" and valid_count > 0,
            "deterministic_processing_possible": deterministic, "external_api_required": kind == "semantic_document_lookup",
            "free_model_available": "pending_probe", "api_probe_success": "pending_probe",
            "structured_output_parse_rate": "pending_probe", "vision_required": vision,
            "estimated_implementation_effort": effort, "expected_reusability": "high" if deterministic else "medium",
            "expected_valid_score_gain": valid_count, "estimated_rate_limit_risk": "high" if kind == "semantic_document_lookup" else "low",
            "estimated_answer_verifiability": "high" if deterministic else "medium",
            "current_main_failure_stage": next((r["current_failure_stage"] for r in inventory if r["primary_question_type"] == kind), "not_observed"),
            "priority_score": round(score, 3),
        })
    with (out / "vertical_slice_candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candidates[0])); writer.writeheader(); writer.writerows(sorted(candidates, key=lambda r: r["priority_score"], reverse=True))
    ranking = sorted(candidates, key=lambda r: r["priority_score"], reverse=True)
    (out / "vertical_slice_ranking.md").write_text("# Vertical Slice ranking\n\n" + "\n".join(f"{i}. {r['question_type']} score={r['priority_score']} valid={r['valid_question_count']} test={r['test_question_count']} effort={r['estimated_implementation_effort']}" for i, r in enumerate(ranking, 1)), encoding="utf-8")
    print(json.dumps({"remaining_count": len(inventory), "type_counts": counts, "ranking": ranking}, ensure_ascii=False))


if __name__ == "__main__":
    main()
