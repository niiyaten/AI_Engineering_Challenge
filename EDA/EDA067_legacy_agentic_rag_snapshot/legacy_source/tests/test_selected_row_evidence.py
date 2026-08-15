import unittest
from types import SimpleNamespace

from rag_competition.table_executor import _selected_row_evidence


class SelectedRowEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.table = SimpleNamespace(columns=["フェーズNo.", "開始日", "タスク名"], rows=[])

    def test_argmax_date_keeps_answer_and_condition_on_same_row(self):
        rows = [{"フェーズNo.": "6", "開始日": "2025-11-11", "タスク名": "最終報告・成果物提出・検収会", "__row_number__": 28}]
        evidence = _selected_row_evidence(self.table, rows, ["フェーズNo.", "開始日"], "開始日", "タスク名", "2025-11-11")
        self.assertEqual(evidence[0]["row_number"], 28)
        self.assertEqual(evidence[0]["aggregate_cell"], "B28")
        self.assertEqual(evidence[0]["answer_cell"], "C28")
        self.assertEqual(evidence[0]["condition_cells"], {"フェーズNo.": "A28", "開始日": "B28"})

    def test_multiple_equal_extremes_are_preserved(self):
        rows = [{"開始日": "2025-11-11", "タスク名": "A", "__row_number__": 28}, {"開始日": "2025-11-11", "タスク名": "B", "__row_number__": 30}]
        evidence = _selected_row_evidence(self.table, rows, ["開始日"], "開始日", "タスク名", "2025-11-11")
        self.assertEqual([item["row_number"] for item in evidence], [28, 30])

    def test_missing_row_number_is_not_fabricated(self):
        rows = [{"開始日": "2025-11-11", "タスク名": "A"}]
        self.assertEqual(_selected_row_evidence(self.table, rows, ["開始日"], "開始日", "タスク名", "2025-11-11"), [])


if __name__ == "__main__":
    unittest.main()
