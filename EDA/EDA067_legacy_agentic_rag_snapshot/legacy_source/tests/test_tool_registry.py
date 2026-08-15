import tempfile
import unittest
from pathlib import Path

from rag_competition.schemas import CompactFileProfile, FileRecord, SearchRecord
from rag_competition.tool_registry import build_tool_registry, run_answer_pipeline
from rag_competition.table_executor import calculation


class ToolRegistryTest(unittest.TestCase):
    def test_registry_contains_required_tools(self):
        registry = build_tool_registry()
        for name in (
            "document_lookup",
            "table_lookup",
            "table_filter",
            "table_aggregation",
            "calculation",
            "version_diff",
            "format_extraction",
            "code_inspection",
            "notebook_inspection",
            "cross_file_aggregation",
            "answer_formatting",
        ):
            self.assertIn(name, registry)

    def test_answer_result_has_evidence(self):
        file = FileRecord("f1", "data/raw/a.csv", "a.csv", "a.csv", ".csv", 1, "", "", "", "案件", "data", "data", "")
        record = SearchRecord("r1", "f1", "table_file", file.raw_path, "columns=['id'] 1 | 42", {"row": 1})
        profile = CompactFileProfile("f1", file.raw_path, file.file_name, file.extension, file.project_name, file.major_folder, file.document_kind, file.version_label, "id 42")
        with tempfile.TemporaryDirectory() as tmp:
            result = run_answer_pipeline(
                [type("A", (), {"index": 0, "question_normalized": "idの値"})()],
                [{"question_id": 0, "question": "idの値", "final_selected_file_ids": ["f1"], "operations": [{"tool_name": "table_lookup"}], "warnings": [], "planner_mode": "heuristic", "selector_mode": "heuristic"}],
                [file],
                [record],
                [profile],
                Path(tmp),
            )
        self.assertEqual(result["execution_count"], 1)
        self.assertEqual(result["answered_count"], 0)
        self.assertTrue(result["answer_results"][0].evidence_locations)
        self.assertEqual(result["answer_results"][0].gate_status, "suppressed_preview_only")

    def test_calculation_trace(self):
        result = calculation("percentage_change", 125.0, 100.0, 2)
        self.assertEqual(result["formatted_result"], 25.0)
        self.assertIn("formula", result)


if __name__ == "__main__":
    unittest.main()
