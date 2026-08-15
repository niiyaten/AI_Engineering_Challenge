from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from rag_competition.id_count_executor import (
    build_count_spec,
    execute_id_count,
    independently_recalculate_count,
    normalize_id,
    verify_count_evidence,
)
from rag_competition.schemas import ExtractionResult, FileRecord


def _file(file_id: str, path: Path, project: str = "人工案件") -> FileRecord:
    return FileRecord(file_id, path.as_posix(), path.name, path.name, path.suffix, 1, "", file_id, "project", project, "02.計画", "schedule", "")


def _csv_extraction(tmp_path: Path, file: FileRecord, rows: list[list[str]], sheet: str = "WBS") -> ExtractionResult:
    table_path = tmp_path / f"{file.file_id}_{sheet}.csv"
    with table_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(rows)
    structure_path = tmp_path / f"{file.file_id}.json"
    structure_path.write_text(json.dumps({"sheets": [{"sheet_name": sheet, "csv_path": table_path.as_posix()}]}, ensure_ascii=False), encoding="utf-8")
    return ExtractionResult(file.file_id, file.raw_path, "success", "xlsx", structure_path.as_posix(), 1, [table_path.as_posix()])


def _multi_sheet_extraction(tmp_path: Path, file: FileRecord, sheets: dict[str, list[list[str]]]) -> ExtractionResult:
    definitions = []
    paths = []
    for name, rows in sheets.items():
        table_path = tmp_path / f"{file.file_id}_{name}.csv"
        with table_path.open("w", encoding="utf-8-sig", newline="") as handle:
            csv.writer(handle).writerows(rows)
        definitions.append({"sheet_name": name, "csv_path": table_path.as_posix()})
        paths.append(table_path.as_posix())
    structure_path = tmp_path / f"{file.file_id}.json"
    structure_path.write_text(json.dumps({"sheets": definitions}, ensure_ascii=False), encoding="utf-8")
    return ExtractionResult(file.file_id, file.raw_path, "success", "xlsx", structure_path.as_posix(), len(sheets), paths)


class IdCountExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_normalize_id(self) -> None:
        for value, expected in [("Ｔ０１", "T01"), (" T01 ", "T01"), ("1.0", "1"), ("未発行", None), ("N/A", None)]:
            with self.subTest(value=value):
                self.assertEqual(normalize_id(value), expected)

    def test_count_spec_distinguishes_id_types_and_never_sums_ids(self) -> None:
        spec = build_count_spec("案件でマイルストーンID、タスクID、アクションIDは合計でいくつ発行されていますか。")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.count_semantics, "issued_id_count")
        self.assertEqual(spec.target_id_types, ["milestone_id", "task_id", "action_id"])
        self.assertEqual(spec.aggregation, "sum_type_counts")
        self.assertNotIn("sum(id)", json.dumps(spec.__dict__, ensure_ascii=False))

    def test_task_count_filters_assignee_and_deduplicates(self) -> None:
        path = self.tmp_path / "schedule.xlsx"
        file = _file("f1", path)
        extraction = _csv_extraction(self.tmp_path, file, [
        ["タスクID", "担当者", "id"],
        ["T01", "加藤 大輔", "100"],
        ["T01", "加藤 大輔", "101"],
        ["T02", "斉藤 悠斗", "102"],
        ["T03", "加藤 大輔 / 斉藤 悠斗", "103"],
        ["未発行", "加藤 大輔", "104"],
    ])
        result = execute_id_count(1, "人工案件の計画で、加藤さんが担当者に含まれるタスクIDはいくつありますか。", "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["answer"], "2")
        self.assertEqual(result["evidence"]["selected_columns"], ["タスクID"])
        self.assertEqual(independently_recalculate_count(result["evidence"]), 2)

    def test_multiple_id_types_keep_namespaces_separate(self) -> None:
        path = self.tmp_path / "schedule.xlsx"
        file = _file("f1", path)
        extraction = _csv_extraction(self.tmp_path, file, [
        ["マイルストーンID", "タスクID", "アクションID"],
        ["T01", "T01", "T01"],
        ["MS2", "T02", "A02"],
    ])
        question = "人工案件でマイルストーンID、タスクID、アクションIDの3種類は合計でいくつ発行されていますか。"
        result = execute_id_count(1, question, "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["answer"], "6")

    def test_role_name_is_resolved_from_resource_sheet(self) -> None:
        path = self.tmp_path / "schedule.xlsx"
        file = _file("f1", path)
        extraction = _multi_sheet_extraction(self.tmp_path, file, {
            "WBS": [["タスクID", "担当者"], ["T01", "斎藤 悠斗"], ["T02", "加藤 大輔"], ["T03", "斎藤 悠斗 / 加藤 大輔"]],
            "リソース": [["役割", "氏名"], ["データエンジニア", "斎藤 悠斗"], ["PM", "加藤 大輔"]],
        })
        result = execute_id_count(1, "人工案件でデータエンジニアが担当するタスクIDはいくつありますか。", "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["answer"], "2")

    def test_missing_required_id_type_is_suppressed(self) -> None:
        path = self.tmp_path / "schedule.xlsx"
        file = _file("f1", path)
        extraction = _csv_extraction(self.tmp_path, file, [["タスクID"], ["T01"]])
        question = "人工案件でタスクIDとアクションIDは合計でいくつ発行されていますか。"
        result = execute_id_count(1, question, "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["failure_stage"], "id_type_resolution_failure")

    def test_occurrence_count_preserves_duplicates(self) -> None:
        path = self.tmp_path / "schedule.xlsx"
        file = _file("f1", path)
        extraction = _csv_extraction(self.tmp_path, file, [["タスクID"], ["T01"], ["T01"], ["T02"]])
        result = execute_id_count(1, "人工案件のタスクIDを重複を含めた出現回数で数えるといくつですか。", "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["answer"], "3")
        self.assertEqual(independently_recalculate_count(result["evidence"]), 3)

    def test_non_null_count_excludes_invalid_values(self) -> None:
        path = self.tmp_path / "schedule.xlsx"
        file = _file("f1", path)
        extraction = _csv_extraction(self.tmp_path, file, [["タスクID"], ["T01"], [""], ["未発行"], ["T02"]])
        result = execute_id_count(1, "人工案件のタスクID列で空白でないIDはいくつありますか。", "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["answer"], "2")

    def test_generic_id_column_is_not_used_as_business_id(self) -> None:
        path = self.tmp_path / "data.xlsx"
        file = _file("f1", path)
        extraction = _csv_extraction(self.tmp_path, file, [["id", "value"], ["1", "x"]])
        result = execute_id_count(1, "人工案件のタスクIDはいくつありますか。", "人工案件", [file], {file.file_id: extraction}, self.tmp_path)
        self.assertEqual(result["status"], "unsupported")

    def test_verifier_rejects_sum_of_id_values(self) -> None:
        spec = build_count_spec("人工案件のタスクIDはいくつありますか。")
        assert spec is not None
        evidence = {
        "actual_used_file_ids": ["f1"], "actual_used_files": ["x.xlsx"], "selected_columns": ["タスクID"],
        "raw_values": [{"id_type": "task_id", "normalized_id": "T01"}], "normalization": spec.normalization,
        "invalid_value_count": 0, "duplicate_policy": spec.duplicate_policy, "per_type_counts": {"task_id": 1},
        "cross_source_duplicate_count": 0, "final_count": 1, "calculation_formula": "sum(id)",
        }
        verification = verify_count_evidence(evidence, spec)
        self.assertEqual(verification["verification_status"], "failed")
        self.assertFalse(verification["no_sum_of_id_values"])


if __name__ == "__main__":
    unittest.main()
