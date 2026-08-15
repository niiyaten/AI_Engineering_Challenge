import unittest
from types import SimpleNamespace

from rag_competition.format_executor import build_format_spec, execute_format_question


def file_record(extension: str) -> SimpleNamespace:
    return SimpleNamespace(file_id="file_synthetic", raw_path="synthetic" + extension, extension=extension)


class FormatExecutorTests(unittest.TestCase):
    def test_docx_highlighted_runs_are_extracted(self):
        file = file_record(".docx")
        structures = {file.file_id: {"blocks": [{"index": 0, "runs": [
            {"text": "対象", "highlight_color": "YELLOW", "bold": False, "italic": False, "underline": False, "run_index": 0},
            {"text": "外側", "highlight_color": "none", "bold": False, "italic": False, "underline": False, "run_index": 1},
        ]}], "tables": []}}
        result = execute_format_question("黄色でハイライトされている部分をすべて抜き出してください", [file], structures, ["format_extraction"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["answer"], "対象")
        self.assertTrue(result["verification"]["condition_match"])

    def test_pptx_red_runs_are_extracted(self):
        file = file_record(".pptx")
        structures = {file.file_id: {"slides": [{"slide_number": 2, "shapes": [{"shape_index": 1, "runs": [
            {"text": "赤字", "font_color_normalized_name": "red", "font_color_resolution_status": "resolved", "run_index": 0},
            {"text": "通常", "font_color_normalized_name": "black", "font_color_resolution_status": "resolved", "run_index": 1},
        ]}]}]}}
        result = execute_format_question("赤字の箇所をすべて抜き出してください", [file], structures, ["format_extraction"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["answer"], "赤字")
        self.assertEqual(result["evidence"][0]["source_location"]["slide_number"], 2)

    def test_xlsx_fill_count_is_recomputed(self):
        file = file_record(".xlsx")
        structures = {file.file_id: {"sheets": [{"sheet_name": "Sheet1", "csv_path": "", "styled_cells": [
            {"coordinate": "A1", "value": "10", "fill_color": "FFFF00", "bold": False, "italic": False, "underline": False},
            {"coordinate": "A2", "value": "20", "fill_color": "FFFF00", "bold": False, "italic": False, "underline": False},
        ]}]}}
        result = execute_format_question("黄色にハイライトされたセルはいくつありますか", [file], structures, ["format_extraction"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["answer"], "2")

    def test_missing_format_is_suppressed(self):
        file = file_record(".docx")
        result = execute_format_question("該当部分を抽出してください", [file], {file.file_id: {"blocks": []}}, ["format_extraction"])
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["failure_stage"], "spec_generation_failure")

    def test_image_only_pdf_is_suppressed(self):
        file = file_record(".pdf")
        result = execute_format_question("黄色でマーカーされた文字を抽出してください", [file], {file.file_id: {"pages": [{"page_number": 1, "text": "", "blocks": []}]}}, ["format_extraction"])
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["failure_stage"], "format_failure")

    def test_format_spec_direction_is_generic(self):
        spec = build_format_spec("黄色でハイライトされたセルはいくつありますか", "xlsx")
        self.assertEqual(spec.operation_direction, "format_item_count")
        self.assertEqual(spec.format_property["fill_color"], "yellow")


if __name__ == "__main__":
    unittest.main()
