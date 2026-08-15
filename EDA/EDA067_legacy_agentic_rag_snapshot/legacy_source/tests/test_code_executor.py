from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag_competition.code_executor import execute_code_inspection
from rag_competition.schemas import FileRecord


class CodeExecutorTest(unittest.TestCase):
    def test_dtype_and_unique_rule_is_derived_from_ast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "features.py"
            source_path.write_text(
                """MAX_CATEGORICAL_UNIQUE = 50

def select_columns(frame):
    selected = []
    for col in frame.columns:
        series = frame[col]
        is_categorical = (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
            or pd.api.types.is_categorical_dtype(series)
        )
        if is_categorical:
            unique_count = int(series.dropna().nunique())
            if unique_count >= MAX_CATEGORICAL_UNIQUE:
                continue
            selected.append(col)
    return selected
""",
                encoding="utf-8",
            )
            file = FileRecord(
                file_id="file_code",
                raw_path="features.py",
                relative_path="features.py",
                file_name="features.py",
                extension=".py",
                size_bytes=source_path.stat().st_size,
                modified_at="",
                sha1="synthetic",
                area="プロジェクト",
                project_name="合成案件",
                major_folder="分析",
                document_kind="analysis",
                version_label="",
            )
            result = execute_code_inspection("CATはdtypeとユニーク数でどう判定しますか", [file], root)
            self.assertEqual(result["status"], "success")
            self.assertIn("50未満", result["answer"])
            self.assertEqual(result["code_rule"]["unique_operator"], "<")
            self.assertEqual(result["code_rule"]["dtype_conditions"], ["object", "string", "category"])
            self.assertTrue(result["verification"]["ast_parse"])

    def test_unrelated_unique_check_is_not_answered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "unrelated.py"
            source_path.write_text("def f(values):\n    return len(set(values))\n", encoding="utf-8")
            file = FileRecord("file_code", "unrelated.py", "unrelated.py", "unrelated.py", ".py", source_path.stat().st_size, "", "synthetic", "", "", "", "analysis", "")
            result = execute_code_inspection("CATはdtypeとユニーク数でどう判定しますか", [file], root)
            self.assertEqual(result["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
