from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag_competition.document_executor import execute_document_question
from rag_competition.schemas import FileRecord


class MarkdownDefinitionLookupTest(unittest.TestCase):
    def test_special_value_is_extracted_from_same_table_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "カラム説明.md"
            path.write_text(
                "| カラム名 | データ型 | 説明 |\n| --- | --- | --- |\n| **pdays** | 整数 | 経過日数（-1は未連絡） |\n",
                encoding="utf-8",
            )
            file = FileRecord("file_md", "カラム説明.md", "カラム説明.md", "カラム説明.md", ".md", path.stat().st_size, "", "synthetic", "プロジェクト", "合成案件", "データ", "data", "")
            result = execute_document_question(
                "カラム説明において、カラム名pdaysの値-1は何を表していますか。",
                ["document_lookup"],
                [file],
                {},
                root,
            )
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["answer"], "未連絡")
            self.assertEqual(result["evidence"][0]["source_location"], {"line_number": 3})
            self.assertFalse(result["evidence"][0]["preview_only"])

    def test_multiple_different_definitions_are_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = []
            for index, meaning in enumerate(("未連絡", "不明"), start=1):
                path = root / f"columns_{index}.md"
                path.write_text(f"| カラム名 | 説明 |\n| --- | --- |\n| pdays | -1は{meaning} |\n", encoding="utf-8")
                files.append(FileRecord(f"file_{index}", path.name, path.name, path.name, ".md", path.stat().st_size, "", "synthetic", "", "", "", "data", ""))
            result = execute_document_question(
                "カラム説明において、カラム名pdaysの値-1は何を表していますか。",
                ["document_lookup"],
                files,
                {},
                root,
            )
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(result["failure_stage"], "uniqueness_failure")


if __name__ == "__main__":
    unittest.main()
