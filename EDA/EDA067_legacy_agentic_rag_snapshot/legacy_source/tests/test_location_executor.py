from __future__ import annotations

import unittest

from rag_competition.location_executor import execute_heading_location
from rag_competition.schemas import FileRecord


class LocationExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.file = FileRecord("f1", "raw/contract.docx", "contract.docx", "contract.docx", ".docx", 1, "", "hash", "", "案件", "", "contract", "")

    def test_resolves_preceding_numbered_heading(self) -> None:
        structures = {"f1": {"blocks": [{"index": 0, "text": "3. 業務範囲"}, {"index": 1, "text": "本業務の対象データ、前提および制約は以下のとおりとする。"}]}}
        result = execute_heading_location("「本業務の対象データ、前提および制約」がある章番号を答えてください。", [self.file], structures)
        self.assertIsNotNone(result)
        self.assertEqual(result["answer"], "3")
        self.assertEqual(result["verification"]["verification_status"], "passed")

    def test_suppresses_ambiguous_chapters(self) -> None:
        structures = {"f1": {"blocks": [{"text": "2. 前提"}, {"text": "対象条件"}, {"text": "3. 制約"}, {"text": "対象条件"}]}}
        result = execute_heading_location("「対象条件」がある章番号を答えてください。", [self.file], structures)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "unsupported")
        self.assertTrue(result["ambiguous"])


if __name__ == "__main__":
    unittest.main()
