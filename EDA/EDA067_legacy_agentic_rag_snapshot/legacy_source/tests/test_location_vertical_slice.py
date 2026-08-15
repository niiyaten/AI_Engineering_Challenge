import unittest

from rag_competition.location_executor import execute_location_question
from rag_competition.schemas import FileRecord


def file_record(file_id: str, name: str, extension: str) -> FileRecord:
    return FileRecord(file_id, name, name, name, extension, 1, "", "hash", "", "project", "", "", "")


class LocationVerticalSliceTests(unittest.TestCase):
    def test_pptx_returns_requested_slide_number(self) -> None:
        file = file_record("ppt", "proposal.pptx", ".pptx")
        result = execute_location_question(
            "\u300c\u9032\u6357\u72b6\u6cc1\u300d\u304c\u3042\u308b\u30b9\u30e9\u30a4\u30c9\u756a\u53f7\u3092\u7b54\u3048\u3066\u304f\u3060\u3055\u3044",
            [file],
            {"ppt": {"slides": [{"slide_number": 1, "shapes": [{"shape_index": 1, "text": "概要"}]}, {"slide_number": 2, "shapes": [{"shape_index": 3, "text": "進捗状況"}]}]}},
        )
        self.assertEqual(result["answer"], "2")
        self.assertTrue(result["verification"]["position_base_confirmed"])

    def test_duplicate_locations_are_suppressed(self) -> None:
        file = file_record("ppt", "proposal.pptx", ".pptx")
        result = execute_location_question(
            "\u300c\u9032\u6357\u72b6\u6cc1\u300d\u304c\u3042\u308b\u30b9\u30e9\u30a4\u30c9\u756a\u53f7\u3092\u7b54\u3048\u3066\u304f\u3060\u3055\u3044",
            [file],
            {"ppt": {"slides": [{"slide_number": 1, "shapes": [{"shape_index": 1, "text": "進捗状況"}]}, {"slide_number": 2, "shapes": [{"shape_index": 3, "text": "進捗状況"}]}]}},
        )
        self.assertEqual(result["failure_stage"], "uniqueness_failure")

    def test_xlsx_returns_cell_without_duplicate_merged_cells(self) -> None:
        file = file_record("book", "table.xlsx", ".xlsx")
        result = execute_location_question(
            "\u300c\u767a\u6ce8\u91d1\u984d\u300d\u304c\u3042\u308b\u30bb\u30eb\u756a\u5730\u3092\u7b54\u3048\u3066\u304f\u3060\u3055\u3044",
            [file],
            {"book": {"sheets": [{"sheet_name": "Sheet1", "csv_path": "", "styled_cells": [{"coordinate": "B3", "value": "発注金額"}]}]}},
        )
        self.assertEqual(result["answer"], "B3")

    def test_docx_page_without_page_mapping_is_suppressed(self) -> None:
        file = file_record("doc", "report.docx", ".docx")
        result = execute_location_question(
            "\u300c\u9032\u6357\u30b5\u30de\u30ea\u300d\u304c\u3042\u308b\u30da\u30fc\u30b8\u3092\u7b54\u3048\u3066\u304f\u3060\u3055\u3044",
            [file],
            {"doc": {"blocks": [{"index": 2, "text": "進捗サマリ"}]}},
        )
        self.assertEqual(result["status"], "unsupported")

    def test_notebook_cell_location_is_preserved(self) -> None:
        file = file_record("nb", "analysis.ipynb", ".ipynb")
        result = execute_location_question(
            "\u300c\u7279\u5fb4\u91cf\u3092\u8a08\u7b97\u300d\u304c\u3042\u308bNotebook\u30bb\u30eb\u3092\u7b54\u3048\u3066\u304f\u3060\u3055\u3044",
            [file],
            {"nb": {"cells": [{"cell_index": 4, "cell_type": "code", "source": "特徴量を計算"}]}},
        )
        self.assertEqual(result["answer"], "4")


if __name__ == "__main__":
    unittest.main()
