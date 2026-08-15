from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_predictions(path: Path) -> dict[int, str]:
    with path.open(encoding="utf-8", newline="") as f:
        return {int(row[0]): row[1] for row in csv.reader(f)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--expected", default="validation/expected_reaudit8.csv")
    args = parser.parse_args()

    predictions = read_predictions(Path(args.predictions))
    with Path(args.expected).open(encoding="utf-8-sig", newline="") as f:
        expected = {
            int(row["index"]): row["expected_answer"]
            for row in csv.DictReader(f)
        }

    results = {
        index: {
            "expected": answer,
            "actual": predictions.get(index),
            "matched": predictions.get(index) == answer,
        }
        for index, answer in expected.items()
    }
    payload = {
        "matched": sum(item["matched"] for item in results.values()),
        "total": len(results),
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(item["matched"] for item in results.values()) else 1)


if __name__ == "__main__":
    main()
