from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rag_competition.llm_client import LlmResult
from rag_competition.schemas import ExtractionResult, FileRecord
from rag_competition.semantic_executor import (
    _derive_answer,
    _validate_selection,
    build_semantic_candidates,
    build_semantic_spec,
    execute_semantic_document_lookup,
)


def _file() -> FileRecord:
    return FileRecord("f1", "raw/contract.docx", "contract.docx", "contract.docx", ".docx", 1, "", "hash", "", "案件", "", "contract", "")


def _result(path: Path) -> ExtractionResult:
    return ExtractionResult("f1", "raw/contract.docx", "success", "docx", str(path), 1)


class FakeClient:
    def __init__(self, candidate_id: str) -> None:
        self.candidate_id = candidate_id

    def call_json(self, purpose: str, prompt: str, max_tokens: int = 500) -> LlmResult:
        parsed = {"selected_candidate_ids": [self.candidate_id], "selection_status": "selected", "confidence": 0.9}
        return LlmResult(True, parsed, "", "prompt", "model:free", "test", "stop", 0, purpose, True, False, True)


class SemanticExecutorTests(unittest.TestCase):
    def test_candidate_generation_and_duration_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            structure_path = root / "doc.json"
            structure_path.write_text(
                json.dumps({"blocks": [{"index": 0, "style": "Heading 1", "text": "8. 秘密保持"}, {"index": 1, "text": "本条の義務は、本契約終了後も3年間存続するものとする。"}], "tables": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            question = "契約書第8条において、本契約終了後に秘密保持義務が存続する期間は何年間ですか。"
            candidates = build_semantic_candidates(question, question, [_file()], {"f1": _result(structure_path)}, root)
            target = next(item for item in candidates if "3年間" in item["text"])
            output = execute_semantic_document_lookup(1, question, question, [_file()], {"f1": _result(structure_path)}, root, FakeClient(target["candidate_id"]), root / "work")
            self.assertEqual(output["answer"], "3年間")
            self.assertEqual(output["verification"]["verification_status"], "passed")
            self.assertFalse(output["evidence"][0]["preview_only"])

    def test_unique_duration_can_be_selected_without_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            structure_path = root / "doc.json"
            structure_path.write_text(
                json.dumps({"blocks": [{"index": 0, "text": "8. 秘密保持"}, {"index": 1, "text": "本契約終了後も3年間存続する。"}], "tables": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            question = "秘密保持義務が存続する期間は何年間ですか。"
            output = execute_semantic_document_lookup(1, question, question, [_file()], {"f1": _result(structure_path)}, root, None, root / "work")
            self.assertEqual(output["answer"], "3年間")
            self.assertEqual(output["semantic_selection"]["selection_method"], "deterministic_unique_value")

    def test_invalid_candidate_id_is_rejected(self) -> None:
        spec = build_semantic_spec("契約金額はいくらですか。")
        valid, reason = _validate_selection(
            {"selected_candidate_ids": ["missing"], "selection_status": "selected", "confidence": 0.9},
            [{"candidate_id": "cand_1"}],
            spec,
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "invalid_candidate_id")

    def test_list_questions_use_generic_list_spec(self) -> None:
        spec = build_semantic_spec("対象範囲をすべて一覧で答えてください。")
        self.assertEqual(spec.selection_mode, "all")
        self.assertEqual(spec.subtype, "semantic_list_extraction")

    def test_filtered_table_list_preserves_order_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            structure_path = root / "table.json"
            structure_path.write_text(
                json.dumps({"blocks": [], "tables": [{"table_index": 0, "rows": [["ID", "状態"], ["A-2", "未完了"], ["A-1", "完了"], ["A-2", "未完了"]]}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            question = "未完了のIDをすべて抽出してください。"
            output = execute_semantic_document_lookup(1, question, question, [_file()], {"f1": _result(structure_path)}, root, None, root / "work")
            self.assertEqual(output["status"], "success")
            self.assertEqual(output["answer"], "A-2")
            self.assertTrue(output["verification"]["independent_recalculation_match"])

    def test_list_with_ambiguous_return_columns_is_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            structure_path = root / "table.json"
            structure_path.write_text(
                json.dumps({"blocks": [], "tables": [{"table_index": 0, "rows": [["ID", "項目", "状態"], ["A-1", "項目A", "未完了"]]}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            question = "未完了のIDと項目をすべて抽出してください。"
            output = execute_semantic_document_lookup(1, question, question, [_file()], {"f1": _result(structure_path)}, root, None, root / "work")
            self.assertEqual(output["status"], "unsupported")

    def test_hypothetical_difference_is_not_reduced_to_value_lookup(self) -> None:
        spec = build_semantic_spec("仮に実績工数が見込工数の4分の3なら、税込金額よりいくら少なくなりますか。")
        self.assertFalse(spec.supported)
        self.assertEqual(spec.unsupported_reason, "calculation_or_comparison_required")

    def test_answer_is_not_freely_generated(self) -> None:
        spec = build_semantic_spec("契約金額(税込)はいくらですか。")
        answer, method = _derive_answer(
            "契約金額(税込)はいくらですか。",
            spec,
            {"text": "契約金額（税込）：5,775,000円", "context_before": "", "context_after": "", "element_type": "paragraph"},
        )
        self.assertEqual(answer, "5,775,000円")
        self.assertEqual(method, "tax_inclusive_amount")


if __name__ == "__main__":
    unittest.main()
