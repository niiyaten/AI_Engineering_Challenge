from __future__ import annotations

import unittest
from types import SimpleNamespace

from rag_competition.answer_gate import evaluate_answer_gate
from rag_competition.table_executor import TableData, _condition_coverage, _condition_match, _parse_schedule_conditions, _target_column, format_extraction


class TableAnswerSafetyTest(unittest.TestCase):
    def test_pastel_orange_highlighted_rows_return_named_column(self) -> None:
        """淡いテーマ色でも、書式一致行から質問で明示された列を返す。"""
        table = TableData(
            file=SimpleNamespace(file_id="file_synthetic", raw_path="synthetic.xlsx"),
            sheet_name="WBS",
            columns=["タスクID", "タスク名"],
            rows=[
                {"タスクID": "T01", "タスク名": "準備", "__row_number__": 2},
                {"タスクID": "T02", "タスク名": "実施", "__row_number__": 3},
            ],
            matrix=[["タスクID", "タスク名"], ["T01", "準備"], ["T02", "実施"]],
            structure={"header_row_number": 1, "styled_cells": [
                {"coordinate": "A3", "fill_color": "type=rgb;rgb=FFFFF0E6"},
                {"coordinate": "B3", "fill_color": "type=rgb;rgb=FFFFF0E6"},
            ]},
            structure_path="",
        )
        result = format_extraction(table, "青嶺案件でオレンジ色にハイライトされている行のタスクIDをすべて答えてください")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["formatted_result"], ["T02"])
        self.assertEqual(result["row_evidence"][0]["answer_coordinate"], "A3")

    def test_highlighted_row_without_unique_header_is_suppressed(self) -> None:
        table = TableData(
            file=SimpleNamespace(file_id="file_synthetic", raw_path="synthetic.xlsx"),
            sheet_name="Sheet1",
            columns=["項目", "値"],
            rows=[{"項目": "A", "値": "1", "__row_number__": 2}],
            matrix=[["項目", "値"], ["A", "1"]],
            structure={"header_row_number": 1, "styled_cells": [{"coordinate": "A2", "fill_color": "type=rgb;rgb=FFF2E0D0"}]},
            structure_path="",
        )
        result = format_extraction(table, "オレンジにハイライトされている行を答えてください")
        self.assertEqual(result["status"], "unsupported")

    def test_highlighted_row_uses_the_named_column_after_column_reordering(self) -> None:
        """The requested header, rather than its position, determines the returned cell."""
        table = TableData(
            file=SimpleNamespace(file_id="file_synthetic", raw_path="synthetic.xlsx"),
            sheet_name="WBS",
            columns=["Task name", "Task ID"],
            rows=[{"Task name": "Kickoff", "Task ID": "T02", "__row_number__": 4}],
            matrix=[["Task name", "Task ID"], ["Kickoff", "T02"]],
            structure={
                "header_row_number": 3,
                "styled_cells": [
                    {"coordinate": "A4", "fill_color": "type=rgb;rgb=FFFFF0E6"},
                    {"coordinate": "B4", "fill_color": "type=rgb;rgb=FFFFF0E6"},
                ],
            },
            structure_path="",
        )
        result = format_extraction(table, "Return the Task ID in rows highlighted orange.")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["formatted_result"], ["T02"])
        self.assertEqual(result["row_evidence"], [{
            "row_number": 4,
            "answer_column_name": "Task ID",
            "answer_column_index": 2,
            "answer_coordinate": "B4",
            "answer_value": "T02",
            "matched_style_cells": ["A4", "B4"],
        }])

    def test_duplicate_named_headers_are_suppressed(self) -> None:
        """Ambiguous duplicate headers must not be resolved by a positional fallback."""
        table = TableData(
            file=SimpleNamespace(file_id="file_synthetic", raw_path="synthetic.xlsx"),
            sheet_name="Sheet1",
            columns=["Task ID", "Task ID"],
            rows=[{"Task ID": "T02", "__row_number__": 2}],
            matrix=[["Task ID", "Task ID"], ["T02", "T99"]],
            structure={"header_row_number": 1, "styled_cells": [{"coordinate": "A2", "fill_color": "type=rgb;rgb=FFFFF0E6"}]},
            structure_path="",
        )
        result = format_extraction(table, "Return the Task ID in rows highlighted orange.")
        self.assertEqual(result["status"], "unsupported")

    def test_schedule_condition_parser_supports_date_or_and_contains(self) -> None:
        columns = ["タスクID", "フェーズNo.", "担当者", "開始日", "終了日", "マイルストーン"]
        question = "2025-08-11から2025-09-09の間に開始日または終了日が設定され、MS3に紐づきビジネスアナリストが関わるタスクID"
        conditions = _parse_schedule_conditions(question, columns)
        self.assertEqual(3, len(conditions))
        row = {"開始日": "2025-08-12", "終了日": "2025-08-20", "マイルストーン": "MS3", "担当者": "ビジネスアナリスト / 佐藤"}
        self.assertTrue(all(_condition_match(row, condition) for condition in conditions))

    def test_schedule_condition_parser_does_not_guess_ambiguous_date_columns(self) -> None:
        columns = ["開始日", "開始日（実績）", "終了日"]
        conditions = _parse_schedule_conditions("2025-08-11から2025-09-09の間に開始日が設定", columns)
        self.assertEqual([], conditions)

    def test_schedule_condition_parser_supports_phase_number(self) -> None:
        conditions = _parse_schedule_conditions("フェーズNo6のタスク名", ["フェーズNo.", "タスク名"])
        self.assertEqual([{"column": "フェーズNo.", "operator": "eq", "value": "6"}], conditions)

    def test_schedule_condition_parser_english_synthetic(self) -> None:
        columns = ["task_id", "phase_no", "assignee", "start_date", "end_date", "milestone"]
        question = "2025-08-11\u304b\u30892025-09-09\u306e\u9593\u306bstart_date\u307e\u305f\u306fend_date, MS3 milestone, business analyst\u304c\u95a2\u308f\u308b task_id"
        conditions = _parse_schedule_conditions(question, columns)
        self.assertEqual(3, len(conditions))
        row = {"start_date": "2025-08-12", "end_date": "2025-08-20", "milestone": "MS3", "assignee": "business analyst / Sato"}
        self.assertTrue(all(_condition_match(row, condition) for condition in conditions))

    def test_schedule_condition_parser_rejects_ambiguous_date_columns(self) -> None:
        columns = ["start_date", "start_date_actual", "end_date"]
        self.assertEqual([], _parse_schedule_conditions("2025-08-11 to 2025-09-09 between start_date", columns))

    def test_schedule_condition_parser_supports_phase_number(self) -> None:
        conditions = _parse_schedule_conditions("phase no6 task name", ["phase_no", "task_name"])
        self.assertEqual([{"column": "phase_no", "operator": "eq", "value": "6"}], conditions)

    def test_target_column_resolves_task_id_by_header(self) -> None:
        self.assertEqual("task_id", _target_column("return task_id", ["task_name", "task_id"]))

    def test_target_column_rejects_duplicate_task_id_headers(self) -> None:
        self.assertIsNone(_target_column("return task_id", ["task_id", "task_id"]))

    def test_target_column_is_not_guessed_from_first_numeric_column(self) -> None:
        self.assertIsNone(_target_column("バッファとして使用した工数の合計", ["No.", "Task", "Hours"]))

    def test_explicit_ascii_target_column_is_resolved(self) -> None:
        self.assertEqual("loan_amnt", _target_column("loan_amntの平均", ["id", "loan_amnt"]))

    def test_condition_coverage_requires_every_explicit_condition(self) -> None:
        question = "purpose=credit_card、grade=B1の平均"
        conditions = [{"column": "purpose", "operator": "eq", "value": "credit_card"}]
        self.assertFalse(_condition_coverage(question, conditions, ["purpose", "grade"]))

    def test_calculation_gate_rejects_missing_required_verification(self) -> None:
        gate = evaluate_answer_gate(
            question_id=1,
            answer="10",
            executor_name="calculation",
            implementation_status="implemented",
            used_file_ids=["file_1"],
            evidence=[{"cell_ranges": ["A1:B2"]}],
            execution_success=True,
            question_type="calculation",
            verification={"input_presence": True},
        )
        self.assertFalse(gate.allow_answer)
        self.assertEqual("suppressed_verification_failure", gate.gate_status)

    def test_calculation_gate_allows_complete_verification(self) -> None:
        verification = {
            "question_type_match": True,
            "condition_coverage": True,
            "input_presence": True,
            "type_validity": True,
            "filter_validity": True,
            "operation_validity": True,
            "rounding_validity": True,
            "reproducibility": True,
            "source_range": True,
        }
        gate = evaluate_answer_gate(
            question_id=1,
            answer="10",
            executor_name="calculation",
            implementation_status="implemented",
            used_file_ids=["file_1"],
            evidence=[{"cell_ranges": ["A1:B2"]}],
            execution_success=True,
            question_type="calculation",
            verification=verification,
        )
        self.assertTrue(gate.allow_answer)


if __name__ == "__main__":
    unittest.main()
