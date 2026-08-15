from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


def jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def is_table(text: str) -> bool:
    return bool(re.search(r"\.xlsx|\.csv|\.tsv|Sheet|シート|表|列|セル|合計|平均|割合|件数|色|黄色|青色|オレンジ", text, re.I))


def classify(text: str, operations: list[str]) -> list[str]:
    types: list[str] = []
    lower = text.lower()
    if any(ext in lower for ext in (".docx", ".pptx", ".pdf")) or any(word in text for word in ("契約書", "提案書", "報告資料", "会議録", "ページ", "スライド", "段落", "見出し")):
        types.append("document_lookup")
    if any(word in text for word in ("そのまま", "抜き出", "すべて抽出", "原文", "全文")):
        types.append("verbatim_extraction")
    if any(word in text for word in ("太字", "斜体", "イタリック", "下線", "文字色", "ハイライト", "コメント", "bold", "italic")):
        types.append("format_extraction")
    if any(word in text for word in ("ページ番号", "何ページ", "スライド番号", "どのページ", "どのスライド")):
        types.append("location_lookup")
    if any(word in text for word in ("old", "new", "v1", "v2", "差分", "比較", "変更点")):
        types.append("version_diff")
    if any(word in lower for word in ("python", ".py", "コード", "関数")):
        types.append("code_inspection")
    if any(word in lower for word in ("notebook", ".ipynb")):
        types.append("notebook_inspection")
    if any(word in text for word in ("グラフ", "チャート")):
        types.append("chart_reading")
    if "画像" in text or "配置" in text:
        types.append("vision_spatial")
    if any(word in text for word in ("全案件", "すべての案件", "横断", "各社")):
        types.append("cross_file_aggregation")
    if "generated_python" in operations:
        types.append("generated_python")
    return list(dict.fromkeys(types or ["unknown"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    planning = args.run_dir / "planning"
    analyses = {int(row["index"]): row for row in jsonl(planning / "question_analysis.jsonl")}
    plans = {int(row["question_id"]): row for row in jsonl(planning / "final_source_plans.jsonl")}
    answer_path = args.run_dir.parent.parent / "output" / args.run_dir.name / "answer_results.jsonl"
    answers = {int(row["question_id"]): row for row in jsonl(answer_path)} if answer_path.exists() else {}
    table_path = args.output_dir.parent / "evaluation" / "table_slice_questions.csv"
    table_questions = {int(row["question_id"]) for row in csv_rows(table_path) if str(row.get("selected", "")).lower() == "true"} if table_path.exists() else set()
    remaining: list[dict] = []
    document: list[dict] = []
    for question_id, analysis in sorted(analyses.items()):
        question = analysis.get("question_original", analysis.get("question_normalized", ""))
        plan = plans.get(question_id, {})
        operations = [str(item.get("tool_name", item.get("operation_type", ""))) for item in plan.get("operations", []) if isinstance(item, dict)]
        types = classify(question, operations)
        answer = answers.get(question_id, {})
        if question_id not in table_questions:
            remaining.append({"question_id": question_id, "question": question, "detected_file_types": " | ".join(analysis.get("required_file_types", [])), "detected_document_roles": " | ".join(str(item.get("document_roles", "")) for item in plan.get("source_requirements", [])), "required_operations": " | ".join(operations), "primary_question_type": types[0], "secondary_question_types": " | ".join(types[1:]), "current_executor": " | ".join(answer.get("operations_executed", operations)), "current_status": answer.get("status", "missing"), "current_failure_stage": answer.get("failure_stage", ""), "recommended_next_executor": types[0]})
            if any(item in {"document_lookup", "verbatim_extraction", "format_extraction", "location_lookup"} for item in types):
                document.append({"question_id": question_id, "question": question, "reason": "document extension or document/content/location/style cue", "detected_file_types": " | ".join(analysis.get("required_file_types", [])), "question_types": " | ".join(types)})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, data, fallback in (("remaining_question_types.csv", remaining, ["question_id", "question"]), ("document_slice_questions.csv", document, ["question_id", "question", "reason", "detected_file_types", "question_types"])):
        path = args.output_dir / name
        fields = list(data[0].keys()) if data else fallback
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(data)
    counts = Counter(row["primary_question_type"] for row in remaining)
    with (args.output_dir / "remaining_question_type_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_type", "question_count"]); writer.writeheader(); writer.writerows({"question_type": key, "question_count": value} for key, value in sorted(counts.items()))
    subtype_rows = []
    for row in document:
        types = row["question_types"].split(" | ")
        if "format_extraction" in types and len(types) == 1:
            subtype = "format_only"
        elif "verbatim_extraction" in types and any(token in row["question"].lower() for token in ("id", "a10", "t01", "m01")):
            subtype = "identifier_verbatim"
        elif "verbatim_extraction" in types:
            subtype = "comment_extraction" if "コメント" in row["question"] else "identifier_verbatim"
        elif "location_lookup" in types:
            subtype = "heading_location" if "見出し" in row["question"] or "章" in row["question"] else "concept_location"
        elif "document_lookup" in types:
            subtype = "semantic_document_lookup"
        else:
            subtype = "unsupported_document"
        subtype_rows.append({"question_id": row["question_id"], "subtype": subtype, "question": row["question"]})
    with (args.output_dir / "document_extraction_subtypes.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "subtype", "question"]); writer.writeheader(); writer.writerows(subtype_rows)
    subtype_counts = Counter(row["subtype"] for row in subtype_rows)
    with (args.output_dir / "document_extraction_subtype_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["subtype", "question_count"]); writer.writeheader(); writer.writerows({"subtype": key, "question_count": value} for key, value in sorted(subtype_counts.items()))
    with (args.output_dir / "document_extraction_failure_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["failure_stage", "question_count"]); writer.writeheader(); writer.writerows([{"failure_stage": "not_evaluated_until_conditioned_executor", "question_count": len(subtype_rows)}])


if __name__ == "__main__":
    main()
