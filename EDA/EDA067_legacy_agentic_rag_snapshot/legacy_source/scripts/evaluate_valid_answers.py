from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path


def normalize_answer(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"^[\s\-*・]+|[\s\-*・]+$", "", text)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"(\.0+)(?=($|[^0-9]))", "", text)
    text = re.sub(r"(?:円|歳|日|時間|分|秒|%)$", "", text)
    return text


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def classify_failure(prediction: dict, exact: bool, normalized: bool) -> str:
    if exact or normalized:
        return ""
    status = prediction.get("status")
    if status == "unsupported" or not prediction.get("answer"):
        return prediction.get("failure_stage") or "evidence_failure"
    return prediction.get("failure_stage") or "unknown_failure"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate completed AnswerResult against valid references.")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--question-ids", default="", help="評価対象を外部で抽出した質問IDへ限定する")
    args = parser.parse_args()
    selected_ids = {int(value) for value in args.question_ids.split(",") if value.strip()} if args.question_ids else None
    predictions = {int(row["question_id"]): row for row in read_jsonl(args.predictions)}
    with args.references.open("r", encoding="utf-8-sig", newline="") as handle:
        references = list(csv.DictReader(handle))
    rows = []
    for reference in references:
        question_id = int(reference["index"])
        if selected_ids is not None and question_id not in selected_ids:
            continue
        prediction = predictions.get(question_id, {})
        answer = str(prediction.get("answer", ""))
        expected = str(reference.get("answer", ""))
        exact = answer == expected
        normalized = normalize_answer(answer) == normalize_answer(expected)
        answered = bool(answer.strip())
        point = 1 if normalized else (-1 if answered else 0)
        rows.append(
            {
                "question_id": question_id,
                "question": reference.get("question", ""),
                "prediction": answer,
                "reference_answer": expected,
                "exact_match": exact,
                "normalized_match": normalized,
                "competition_point": point,
                "answered": answered,
                "selected_files": " | ".join(prediction.get("selected_files", [])),
                "operations": " | ".join(prediction.get("operations_executed", [])),
                "status": prediction.get("status", "missing"),
                "failure_stage": classify_failure(prediction, exact, normalized),
                "warnings": " | ".join(prediction.get("warnings", [])),
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["question_id"]
    with (args.output_dir / "valid_evaluation.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    failure_counts: dict[str, int] = {}
    for row in rows:
        failure = row["failure_stage"]
        if failure:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
    metrics = {
        "total_questions": len(rows),
        "answered_count": sum(row["answered"] for row in rows),
        "blank_count": sum(not row["answered"] for row in rows),
        "exact_match_count": sum(row["exact_match"] for row in rows),
        "normalized_match_count": sum(row["normalized_match"] for row in rows),
        "incorrect_count": sum(row["answered"] and not row["normalized_match"] for row in rows),
        "accuracy": round(sum(row["normalized_match"] for row in rows) / len(rows), 4) if rows else 0.0,
        "competition_score": sum(row["competition_point"] for row in rows),
        "failure_stage_counts": failure_counts,
    }
    (args.output_dir / "valid_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "failure_analysis.csv").write_text(
        "failure_stage,count\n" + "\n".join(f"{key},{value}" for key, value in sorted(failure_counts.items())) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "evaluation_report.md").write_text(
        "# Valid Answer Evaluation\n\n" + json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
