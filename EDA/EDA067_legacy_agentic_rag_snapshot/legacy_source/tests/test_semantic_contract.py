from __future__ import annotations

import unittest

from rag_competition.semantic_contract import verify_semantic_contract


class SemanticContractTests(unittest.TestCase):
    def test_condition_and_aggregation_question_requires_both_contracts(self) -> None:
        result = verify_semantic_contract(
            "黄色セルの抽出条件と集計内容を答えてください",
            ["format_extraction", "answer_formatting"],
            [{"answer": "E10", "evidence": [{"location": {"cell": "E10"}}]}],
        )
        self.assertEqual(result["verification_status"], "failed")
        self.assertIn("filter_condition_match", result["failed_checks"])
        self.assertIn("aggregation_operation_match", result["failed_checks"])

    def test_numeric_date_fragment_is_not_an_identifier_contract(self) -> None:
        result = verify_semantic_contract(
            "報告資料_2025-08-18.pdfから担当タスクを抽出してください",
            ["document_lookup"],
            [{"question_type": "identifier_verbatim", "extraction_spec": {"identifier_terms": ["18"]}}],
        )
        self.assertEqual(result["verification_status"], "failed")
        self.assertIn("identifier_intent_match", result["failed_checks"])

    def test_calculation_with_operation_graph_passes(self) -> None:
        result = verify_semantic_contract(
            "部署別の平均を計算してください",
            ["table_filter", "table_aggregation", "calculation"],
            [{"spec": {"filters": [{"column": "部署"}], "operations": [{"operation": "mean"}]}}],
        )
        self.assertEqual(result["verification_status"], "passed")

    def test_pivot_hierarchy_is_filter_contract_evidence(self) -> None:
        result = verify_semantic_contract(
            "平均が最大となる抽出条件を答えてください",
            ["table_lookup", "table_aggregation"],
            [{"answer": "Gender = Female", "evidence": {"reconstructed_hierarchy": {"Gender": "Female"}, "calculation_formula": "max(value)"}}],
        )
        self.assertEqual(result["verification_status"], "passed")

    def test_all_identifier_output_does_not_require_specific_identifier_term(self) -> None:
        result = verify_semantic_contract(
            "該当するタスクIDをすべて抽出してください",
            ["document_lookup"],
            [{
                "question_type": "identifier_verbatim",
                "extraction_spec": {"identifier_output_only": True, "identifier_terms": []},
                "evidence": [{"text": "T09"}, {"text": "T10"}],
            }],
        )
        self.assertEqual(result["verification_status"], "passed")


if __name__ == "__main__":
    unittest.main()
