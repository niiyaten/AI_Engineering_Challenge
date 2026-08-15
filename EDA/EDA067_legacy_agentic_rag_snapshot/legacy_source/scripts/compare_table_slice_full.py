from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_run(root: Path, run_id: str, question_ids: set[int]) -> dict[int, dict]:
    output = root / "data" / "output" / run_id
    work = root / "data" / "work" / run_id
    answers = {int(row["question_id"]): row for row in jsonl(output / "answer_results.jsonl")}
    plans = {int(row["question_id"]): row for row in jsonl(work / "planning" / "final_source_plans.jsonl")}
    evaluation = {}
    eval_path = output / "evaluation" / "valid_evaluation.csv"
    if eval_path.exists():
        with eval_path.open("r", encoding="utf-8-sig", newline="") as handle:
            evaluation = {int(row["question_id"]): row for row in csv.DictReader(handle)}
    result = {}
    for question_id in question_ids:
        answer = answers.get(question_id, {})
        plan = plans.get(question_id, {})
        evidence = (answer.get("evidence_locations") or [{}])[0]
        selected_ids = answer.get("selected_file_ids") or plan.get("final_selected_file_ids", [])
        result[question_id] = {
            "selected_file": evidence.get("selected_file") or (answer.get("selected_files") or [""])[0],
            "selected_file_id": " | ".join(selected_ids),
            "sheet_name": evidence.get("sheet_name", ""),
            "tool_name": " | ".join(answer.get("operations_executed", [])),
            "operation_parameters": json.dumps(answer.get("operation_parameters", []), ensure_ascii=False, sort_keys=True),
            "filter_conditions": json.dumps(evidence.get("filter_conditions", []), ensure_ascii=False, sort_keys=True),
            "columns_used": " | ".join(evidence.get("columns_used", [])) if isinstance(evidence.get("columns_used"), list) else str(evidence.get("columns_used", "")),
            "cell_ranges": " | ".join(evidence.get("cell_ranges", [])) if isinstance(evidence.get("cell_ranges"), list) else str(evidence.get("cell_ranges", "")),
            "matched_row_count": evidence.get("matched_row_count", ""),
            "raw_result": json.dumps(evidence.get("raw_result"), ensure_ascii=False),
            "formatted_result": str(evidence.get("formatted_result", "")),
            "final_answer": answer.get("answer", ""),
            "status": answer.get("status", "missing"),
            "warnings": " | ".join(answer.get("warnings", [])),
            "normalized_match": evaluation.get(question_id, {}).get("normalized_match", ""),
            "plan_file_ids": " | ".join(plan.get("final_selected_file_ids", [])),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare table slice and full valid outputs after execution.")
    parser.add_argument("--slice-run", required=True)
    parser.add_argument("--full-run", required=True)
    parser.add_argument("--comparison-run-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    slice_questions_path = root / "data" / "output" / args.slice_run / "evaluation" / "table_slice_questions.csv"
    with slice_questions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        questions = {int(row["question_id"]): row["question"] for row in csv.DictReader(handle) if row.get("selected", "").lower() == "true"}
    slice_rows = load_run(root, args.slice_run, set(questions))
    full_rows = load_run(root, args.full_run, set(questions))
    rows = []
    for question_id, question in questions.items():
        for mode, source in (("table-slice", slice_rows), ("full-valid", full_rows)):
            row = {"question_id": question_id, "question": question, "run_mode": mode}
            row.update(source.get(question_id, {}))
            rows.append(row)
    output_dir = root / "data" / "output" / args.comparison_run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = ["question_id", "question", "run_mode", "selected_file", "selected_file_id", "sheet_name", "tool_name", "operation_parameters", "filter_conditions", "columns_used", "cell_ranges", "matched_row_count", "raw_result", "formatted_result", "final_answer", "status", "warnings", "normalized_match", "plan_file_ids"]
    with (output_dir / "table_slice_full_comparison.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Table Slice and Full Valid Comparison", "", f"- slice run: `{args.slice_run}`", f"- full run: `{args.full_run}`", ""]
    for question_id, question in questions.items():
        left, right = slice_rows.get(question_id, {}), full_rows.get(question_id, {})
        equal_answer = left.get("final_answer") == right.get("final_answer")
        equal_plan = left.get("plan_file_ids") == right.get("plan_file_ids")
        lines.extend([
            f"## Question {question_id}",
            f"- question: {question}",
            f"- answer_equal: `{equal_answer}`",
            f"- plan_file_ids_equal: `{equal_plan}`",
            f"- slice: `{left.get('final_answer', '')}` / status=`{left.get('status', '')}`",
            f"- full: `{right.get('final_answer', '')}` / status=`{right.get('status', '')}`",
            "",
        ])
    (output_dir / "table_slice_full_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"question_count": len(questions), "output_dir": output_dir.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
