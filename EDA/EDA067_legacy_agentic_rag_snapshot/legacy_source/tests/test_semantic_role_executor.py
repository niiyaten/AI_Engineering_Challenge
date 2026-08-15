from __future__ import annotations

import unittest

from rag_competition.semantic_executor import (
    _derive_role_answer,
    _derive_status_answer,
    build_role_spec,
    build_status_spec,
)


class SemanticRoleExecutorTests(unittest.TestCase):
    def test_role_to_person_uses_explicit_role_value(self) -> None:
        spec = build_role_spec("\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u8cac\u4efb\u8005\u306f\u5c71\u7530\u592a\u90ce\u3067\u3059\u3002")
        answer, method = _derive_role_answer(
            "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u8cac\u4efb\u8005\u306f\u5c71\u7530\u592a\u90ce\u3067\u3059\u3002",
            spec,
            {"text": "\u8cac\u4efb\u8005\uff1a\u5c71\u7530\u592a\u90ce", "metadata": {}},
        )
        self.assertTrue(spec.supported)
        self.assertEqual(answer, "\u5c71\u7530\u592a\u90ce")
        self.assertEqual(method, "explicit_role_colon_value")

    def test_person_to_role_uses_parenthesized_role(self) -> None:
        question = "\u5c71\u7530\u592a\u90ce\u3055\u3093\u306e\u5f79\u5272\u306f\u4f55\u3067\u3059\u304b\u3002"
        spec = build_role_spec(question)
        answer, method = _derive_role_answer(
            question,
            spec,
            {"text": "\u5c71\u7530\u592a\u90ce\uff08PM\uff09", "metadata": {}},
        )
        self.assertTrue(spec.supported)
        self.assertEqual(answer, "PM")
        self.assertEqual(method, "person_parenthesized_role")

    def test_calculation_and_list_questions_are_not_role_questions(self) -> None:
        calculation = build_role_spec("\u62c5\u5f53\u8005\u5225\u306e\u60f3\u5b9a\u5de5\u6570\u306e\u5e73\u5747\u3092\u8a08\u7b97\u3059\u308b\u3002")
        listing = build_role_spec("\u62c5\u5f53\u8005\u3092\u3059\u3079\u3066\u4e00\u89a7\u3067\u62bd\u51fa\u3059\u308b\u3002")
        self.assertFalse(calculation.supported)
        self.assertEqual(calculation.unsupported_reason, "calculation_or_comparison_required")
        self.assertFalse(listing.supported)
        self.assertEqual(listing.subtype, "semantic_list_extraction")

    def test_status_table_value_is_returned_from_the_status_column(self) -> None:
        question = "\u30bf\u30b9\u30afA\u306e\u30b9\u30c6\u30fc\u30bf\u30b9\u306f\u4f55\u3067\u3059\u304b\u3002"
        spec = build_status_spec(question)
        answer, method = _derive_status_answer(
            question,
            spec,
            {"text": "\u30bf\u30b9\u30afA | \u5b8c\u4e86", "metadata": {"headers": ["\u30bf\u30b9\u30af", "\u30b9\u30c6\u30fc\u30bf\u30b9"], "cells": ["A", "\u5b8c\u4e86"]}},
        )
        self.assertTrue(spec.supported)
        self.assertEqual(answer, "\u5b8c\u4e86")
        self.assertEqual(method, "status_table_value")

    def test_status_yes_no_handles_explicit_negative(self) -> None:
        question = "\u30bf\u30b9\u30afA\u306f\u5b8c\u4e86\u3057\u3066\u3044\u307e\u3059\u304b\u3002"
        spec = build_status_spec(question)
        answer, method = _derive_status_answer(question, spec, {"text": "\u30bf\u30b9\u30afA\u306f\u5b8c\u4e86\u3057\u3066\u3044\u306a\u3044", "metadata": {}})
        self.assertEqual(answer, "\u3044\u3044\u3048")
        self.assertEqual(method, "status_yes_no")

    def test_status_list_and_planned_values_are_suppressed(self) -> None:
        listing = build_status_spec("\u5b8c\u4e86\u3057\u305f\u9805\u76ee\u3092\u3059\u3079\u3066\u6319\u3052\u3066\u304f\u3060\u3055\u3044\u3002")
        self.assertFalse(listing.supported)
        self.assertEqual(listing.subtype, "semantic_list_extraction")
        spec = build_status_spec("\u30bf\u30b9\u30afA\u306e\u73fe\u5728\u72b6\u614b\u306f\u4f55\u3067\u3059\u304b\u3002")
        answer, method = _derive_status_answer(spec.target_terms[0], spec, {"text": "\u30bf\u30b9\u30afA\u306f\u5b8c\u4e86\u4e88\u5b9a", "metadata": {}})
        self.assertEqual(answer, "")
        self.assertEqual(method, "planned_status_not_current")


if __name__ == "__main__":
    unittest.main()
