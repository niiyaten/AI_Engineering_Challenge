import unittest

from rag_competition.document_evidence_verifier import verify_document_extraction
from rag_competition.document_reconstructor import reconstruct_items
from rag_competition.extraction_spec import build_extraction_spec
from rag_competition.question_conditioned_extractor import extract_conditioned
from rag_competition.schemas import FileRecord


class DocumentExtractionTest(unittest.TestCase):
    def setUp(self):
        self.file = FileRecord("f1", "data/raw/doc.docx", "doc.docx", "doc.docx", ".docx", 1, "", "", "", "project", "data", "doc", "")

    def test_spec_and_bold_continuous_runs(self):
        spec = build_extraction_spec("太字部分をそのまま抜き出してください")
        structure = {"blocks": [{"index": 0, "style": "Normal", "runs": [{"text": "モデル", "bold": True, "italic": False, "underline": False, "run_index": 0}, {"text": "構築", "bold": True, "italic": False, "underline": False, "run_index": 1}, {"text": "を実施", "bold": False, "italic": False, "underline": False, "run_index": 2}]}], "tables": []}
        result = extract_conditioned("太字部分をそのまま抜き出してください", spec, [self.file], {"f1": structure})
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["items"][0]["text"], "モデル構築")
        self.assertTrue(result["verification"]["verification_status"] in {"passed", "failed"})
        self.assertTrue(all(item["actual_format_values"]["bold"] for item in result["items"]))

    def test_identifier_table_row(self):
        spec = build_extraction_spec("アクションID A10の内容をそのまま抜き出す")
        structure = {"blocks": [], "tables": [{"table_index": 0, "rows": [["ID", "内容"], ["A10", "確認する"]]}]}
        result = extract_conditioned("アクションID A10の内容をそのまま抜き出す", spec, [self.file], {"f1": structure})
        self.assertTrue(result["items"])
        self.assertIn("A10", result["items"][0]["text"])

    def test_verifier_detects_ambiguous_single(self):
        spec = build_extraction_spec("指定項目を答えてください")
        items = [{"text": "A", "location": {"paragraph_index": 1}, "matched_format_conditions": {}} , {"text": "B", "location": {"paragraph_index": 2}, "matched_format_conditions": {}}]
        result = verify_document_extraction("A\nB", items, spec, 2, 2)
        self.assertFalse(result["uniqueness"])
        self.assertEqual(result["verification_status"], "failed")


if __name__ == "__main__":
    unittest.main()
