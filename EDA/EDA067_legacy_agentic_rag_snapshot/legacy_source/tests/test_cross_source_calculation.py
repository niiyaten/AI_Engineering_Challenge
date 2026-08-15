from __future__ import annotations

import csv
import hashlib
import unittest
from pathlib import Path

from rag_competition.cross_source_calculation import (
    execute_cross_source_calculation,
    independently_recalculate_cross_source,
    parse_cross_source_difference_spec,
)
from rag_competition.schemas import FileRecord


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_ROOT = ROOT / "evaluation/synthetic/calculation/cross_source_metric_difference"


def _record(path: Path, project: str) -> FileRecord:
    relative = path.relative_to(ROOT).as_posix()
    return FileRecord(
        file_id=f"file_{hashlib.sha1(relative.encode()).hexdigest()[:16]}",
        raw_path=relative,
        relative_path=relative,
        file_name=path.name,
        extension=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        modified_at="",
        sha1=hashlib.sha1(path.read_bytes()).hexdigest(),
        area="synthetic",
        project_name=project,
        major_folder="calculation",
        document_kind="analysis",
        version_label="",
    )


def _cases() -> list[dict[str, str]]:
    with (SYNTHETIC_ROOT / "cases.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _run_case(row: dict[str, str]) -> dict:
    case_dir = SYNTHETIC_ROOT / row["case_id"]
    files = []
    for path in sorted(case_dir.glob("*.json")):
        project = "別案件" if row["case_id"] == "negative_unrelated_project" and path.name == "final.json" else "合成案件"
        files.append(_record(path, project))
    return execute_cross_source_calculation(1, row["question"], row["question"], files, {}, ROOT)


class CrossSourceCalculationTest(unittest.TestCase):
    def test_spec_requires_two_sources_difference_and_metric(self) -> None:
        spec = parse_cross_source_difference_spec("案件Aの中間報告と最終分析metrics.jsonのMacro F1改善幅を小数第6位まで答えてください。")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.metric_name, "f1_macro")
        self.assertEqual(spec.source_requirements["source_cardinality"], "multiple")
        self.assertEqual(spec.rounding["decimal_places"], 6)

    def test_all_synthetic_cases(self) -> None:
        for row in _cases():
            with self.subTest(case_id=row["case_id"]):
                result = _run_case(row)
                expected_allowed = row["expected_allowed"].lower() == "true"
                if expected_allowed:
                    self.assertEqual(result["status"], "success")
                    self.assertEqual(result["answer"], row["expected_answer"])
                    self.assertTrue(result["verification"]["independent_recalculation_match"])
                else:
                    self.assertEqual(result["status"], "unsupported")
                    self.assertEqual(result.get("answer", ""), "")

    def test_independent_recalculation_rejects_wrong_operation(self) -> None:
        result = independently_recalculate_cross_source(
            {"operation": "sum", "input_values": {"interim": "0.7", "final": "0.8"}, "rounding": {"decimal_places": 2}}
        )
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
