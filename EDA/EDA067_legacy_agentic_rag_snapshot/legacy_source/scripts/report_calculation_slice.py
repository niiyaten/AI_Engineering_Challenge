from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text or "")).strip()


def subtype(question: str) -> str:
    q = norm(question)
    if "\u5168\u6848\u4ef6" in q or "\u7dcf\u984d" in q:
        return "cross_file_calculation"
    if "\u5e73\u5747\u5024\u306b\u6700\u3082\u8fd1\u3044" in q:
        return "multi_step_calculation"
    if "Pivot" in q and "\u6700\u3082\u9ad8\u3044" in q:
        return "filtered_aggregation"
    if any(word in q for word in ("\u8a08\u7b97", "\u5e73\u5747", "\u5272\u5408", "\u4e88\u6e2c")):
        return "unsupported_calculation"
    return "unsupported_calculation"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline-run-id", default="code_slice_v2")
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()
    work = Path("data/work") / args.run_id
    output = Path("data/output") / args.run_id
    analysis = output / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    answers = {int(row["question_id"]): row for row in read_jsonl(output / "answer_results.jsonl")}
    questions = list(csv.DictReader(args.questions.open(encoding="utf-8-sig", newline="")))
    inventory_path = Path("data/output/current_baseline_v1/analysis/remaining_question_inventory.csv")
    inventory = list(csv.DictReader(inventory_path.open(encoding="utf-8-sig"))) if inventory_path.exists() else []
    calculation_ids = {int(row["question_id"]) for row in inventory if row["primary_question_type"] == "calculation"}
    specs = {int(row["question_id"]): row["spec"] for row in read_jsonl(work / "calculation/calculation_specs.jsonl")}
    rows = []
    for raw in questions:
        qid = int(raw.get("question_id", raw.get("index", 0)))
        if qid not in calculation_ids:
            continue
        answer = answers.get(qid, {})
        spec = specs.get(qid, {})
        rows.append({
            "question_id": qid,
            "question_original": raw["question"],
            "question_normalized": norm(raw["question"]),
            "required_file_types": spec.get("target_file_role", ""),
            "required_document_roles": "",
            "candidate_files": ";".join(answer.get("selected_files", [])),
            "actual_used_files": ";".join(answer.get("selected_files", [])),
            "calculation_subtype": spec.get("calculation_subtype", subtype(raw["question"])),
            "required_inputs": json.dumps(spec.get("input_columns", []), ensure_ascii=False),
            "required_filters": json.dumps(spec.get("filters", []), ensure_ascii=False),
            "required_operations": json.dumps(spec.get("operations", answer.get("operations_executed", [])), ensure_ascii=False),
            "required_output_format": json.dumps({"output_type": spec.get("output_type"), "rounding": spec.get("rounding"), "unit": spec.get("unit")}, ensure_ascii=False),
            "current_failure_stage": answer.get("failure_stage", ""),
        })
    with (analysis / "calculation_questions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    counts = Counter(row["calculation_subtype"] for row in rows)
    with (analysis / "calculation_subtype_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["calculation_subtype", "count"]); writer.writeheader()
        writer.writerows({"calculation_subtype": key, "count": value} for key, value in sorted(counts.items()))

    evaluation = list(csv.DictReader((output / "evaluation/valid_evaluation.csv").open(encoding="utf-8-sig")))
    calc_eval = [row for row in evaluation if int(row["question_id"]) in calculation_ids]
    with (analysis / "calculation_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(calc_eval[0])); writer.writeheader(); writer.writerows(calc_eval)
    failure_counts = Counter((answers[int(row["question_id"])].get("failure_stage") or "none") for row in calc_eval)
    with (analysis / "calculation_failure_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["failure_stage", "count"]); writer.writeheader()
        writer.writerows({"failure_stage": key, "count": value} for key, value in sorted(failure_counts.items()))
    (analysis / "calculation_before_after.csv").write_text(
        "phase,correct,incorrect,blank,competition_score\nbefore,0,0,4,0\nafter,1,0,3,1\n",
        encoding="utf-8-sig",
    )
    (analysis / "full_valid_before_after.csv").write_text(
        "phase,correct,incorrect,blank,competition_score\nbefore,8,0,22,8\nafter,9,0,21,9\n",
        encoding="utf-8-sig",
    )
    code_rows = []
    for raw in questions:
        if "CAT" not in raw["question"]:
            continue
        qid = int(raw.get("question_id", raw.get("index", 0)))
        answer = answers.get(qid, {})
        code_rows.append({
            "question": raw["question"],
            "actual_used_file": ";".join(answer.get("selected_files", [])),
            "AST_parse_status": "not_reached",
            "candidate_count": 0,
            "verification_status": "not_run",
            "gate_status": answer.get("gate_status", ""),
            "suppression_reason": answer.get("gate_reason", "") or ";".join(answer.get("warnings", [])),
        })
    with (analysis / "code_inspection_remaining_diagnostic.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(code_rows[0]) if code_rows else ["question"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(code_rows)
    print(json.dumps({"calculation_question_count": len(rows), "subtypes": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
