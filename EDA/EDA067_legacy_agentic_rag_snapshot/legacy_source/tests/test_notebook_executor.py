from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rag_competition.notebook_executor import (
    _axis_replay_script,
    execute_notebook_inspection,
    parse_correlation_matrix_output,
    parse_ranked_numeric_output,
)
from rag_competition.questions import analyze_questions, replace_terms
from rag_competition.schemas import ExtractionResult, FileRecord
from rag_competition.semantic_contract import verify_semantic_contract


class NotebookExecutorTest(unittest.TestCase):
    def _run(self, question: str, output: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extracted = root / "notebook.json"
            extracted.write_text(
                json.dumps({"cells": [{"cell_index": 3, "cell_type": "code", "source": "", "outputs_preview": [output]}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            file = FileRecord("file_nb", "raw/sample.ipynb", "raw/sample.ipynb", "sample.ipynb", ".ipynb", 1, "", "hash", "", "", "", "notebook", "")
            result = ExtractionResult("file_nb", file.raw_path, "success", "ipynb", str(extracted), 1)
            return execute_notebook_inspection(question, [file], {"file_nb": result}, root)

    def test_saved_series_output_selects_smallest_value(self) -> None:
        output = str(["目的変数との相関 上位3\n", "temp 0.45\n", "hum 0.28\n", "season 0.22\n", "Name: cnt, dtype: float64\n"])
        result = self._run("相関上位3で最も小さい列を答えてください", output)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["answer"], "season")
        self.assertTrue(result["verification"]["extremum_reproducible"])

    def test_absolute_value_is_used_only_when_requested(self) -> None:
        output = "目的変数との相関 上位2\nnegative -0.90\npositive 0.30\nName: cnt, dtype: float64"
        result = self._run("相関係数の絶対値が最も小さい列", output)
        self.assertEqual(result["answer"], "positive")

    def test_tied_extreme_is_suppressed(self) -> None:
        output = "目的変数との相関 上位2\na 0.20\nb 0.20\nName: cnt, dtype: float64"
        result = self._run("最も小さい列", output)
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["failure_stage"], "uniqueness_failure")

    def test_heatmap_question_requires_vision(self) -> None:
        result = self._run("ヒートマップの図で最も小さい列", "目的変数との相関 上位1\na 0.20")
        self.assertEqual(result["failure_stage"], "vision_required")

    def test_parser_does_not_accept_unstructured_numbers(self) -> None:
        self.assertEqual(parse_ranked_numeric_output(["accuracy 0.90", "rows 100"]), [])

    def test_axis_replay_script_observes_before_close(self) -> None:
        script = _axis_replay_script("notebook.ipynb", "evidence.json", "replay.png")
        self.assertIn("original_close = plt.close", script)
        self.assertIn("plt.close = observed_close", script)
        self.assertIn("visible_yticks", script)

    def test_axis_replay_script_uses_semantic_labels(self) -> None:
        script = _axis_replay_script("notebook.ipynb", "evidence.json", "replay.png")
        self.assertIn("目的変数", script)
        self.assertIn("件数", script)
        self.assertNotIn("question_id == 56", script)

    def test_axis_ticks_are_not_mistaken_for_table_aggregation(self) -> None:
        contract = verify_semantic_contract(
            "Notebook visualization y-axis tick maximum",
            ["notebook_axis_tick_lookup"],
            [{"question_type": "notebook_axis_ticks", "answer": "1200", "evidence": [{"location": {"cell": 13}}], "verification": {}}],
        )
        self.assertEqual([], contract["failed_checks"])

    def test_saved_correlation_matrix_excludes_target_and_identifier(self) -> None:
        rows = parse_correlation_matrix_output(
            [
                "       id       age       bmi   charges",
                "id  1.0000  0.010000  0.020000  0.030000",
                "age 0.0100  1.000000  0.100000  0.200000",
                "bmi 0.0200  0.100000  1.000000  0.300000",
                "charges 0.0300 0.200000 0.300000 1.000000",
            ],
            "charges",
        )
        self.assertEqual(["age", "bmi"], [row["name"] for row in rows])
        self.assertEqual(0.3, rows[1]["value"])

    def test_saved_correlation_matrix_rejects_incomplete_target_row(self) -> None:
        rows = parse_correlation_matrix_output(
            ["id age charges", "charges 0.1 0.2"],
            "charges",
        )
        self.assertEqual([], rows)

    def test_single_letter_term_does_not_expand_inside_file_name(self) -> None:
        expanded, replacements = replace_terms("AOSHIOのNB01_eda.ipynbとTG", {"AOSHIO": "青潮", "B": "太字", "TG": "目的変数"})
        self.assertEqual(expanded, "青潮のNB01_eda.ipynbと目的変数")
        self.assertNotIn("B", [item["token"] for item in replacements])

    def test_multiple_operations_do_not_imply_multiple_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            analyses = analyze_questions(
                [(1, "01_eda.ipynbで相関係数が最も高い列を計算してください")],
                {},
                Path(directory),
            )
        self.assertIn("calculation", analyses[0].provisional_routes)
        self.assertIn("code_execution", analyses[0].provisional_routes)
        self.assertFalse(analyses[0].needs_multiple_files)


if __name__ == "__main__":
    unittest.main()
