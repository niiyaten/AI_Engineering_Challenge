from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path


def normalize_path(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").replace("\\", "/").replace("\xa0", " ")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def split_sources(value: str) -> list[str]:
    parts = re.split(r"[;\n|]", value or "")
    return [part.strip() for part in parts if part.strip()]


def source_matches(expected: str, actual: str) -> bool:
    exp = normalize_path(expected)
    act = normalize_path(actual)
    if not exp or not act:
        return False
    exp_name = Path(exp).name
    return exp in act or act in exp or (exp_name and exp_name in act)


def load_final_plans(path: Path) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            rows[int(row["question_id"])] = row
    return rows


def load_comparison_paths(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {int(row["question_id"]): row.get("final_selected_paths", "") for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare final source plans with an external human review file.")
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, default=None)
    parser.add_argument("--human-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plans = load_final_plans(args.plans)
    comparison_path = args.comparison or args.plans.parent / "source_selection_comparison.csv"
    comparison_paths = load_comparison_paths(comparison_path)
    rows = []
    matched = 0
    comparable = 0
    with args.human_review.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            qid = int(row["index"])
            if qid not in plans:
                continue
            expected_sources = split_sources(row.get("human_sorce_files") or row.get("source_files") or "")
            if not expected_sources:
                continue
            comparable += 1
            final_paths = plans[qid].get("final_selected_file_ids", [])
            # final_source_plans stores file ids; source paths are available in the compact comparison output.
            selected_paths = split_sources(comparison_paths.get(qid, ""))
            is_match = any(source_matches(expected, actual) for expected in expected_sources for actual in selected_paths)
            matched += int(is_match)
            rows.append(
                {
                    "question_id": qid,
                    "expected_sources": " | ".join(expected_sources),
                    "final_selected_files": " | ".join(final_paths),
                    "final_selected_paths": " | ".join(selected_paths),
                    "matched": is_match,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "comparable_count": comparable,
        "matched_count": matched,
        "match_rate": round(matched / comparable, 4) if comparable else None,
    }
    (args.output.with_suffix(".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "expected_sources", "final_selected_files", "final_selected_paths", "matched"])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
