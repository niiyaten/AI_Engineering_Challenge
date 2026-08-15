from __future__ import annotations

from rag_competition.answer_gate import evaluate_answer_gate
from rag_competition.semantic_executor import _build_list_verification, _list_item_evidence


def candidate(value: str, row: int, location: bool = True) -> dict:
    return {
        "candidate_id": f"c{row}", "file_id": "file1", "source_path": "raw.xlsx", "file_role": "schedule",
        "source_relation": "same_project", "element_type": "table_row", "text": f"{value} | 未完了",
        "item_value": value, "filter_match": True, "answer_column_name": "ID", "answer_column_index": 0,
        "filter_column_name": "状態", "filter_column_index": 1, "filter_actual_value": "未完了",
        "table_index": 2, "row_index": row, "source_order": row,
        **({"page_number": 1} if location else {}), "metadata": {"headers": ["ID", "状態"], "cells": [value, "未完了"]},
    }


def main() -> None:
    included = [candidate("T1", 1), candidate("T2", 2)]
    excluded = [dict(candidate("T3", 3), exclusion_reason="filter_mismatch")]
    completeness = {"completeness_check_passed": True}
    verification, reconstructed = _build_list_verification(included, excluded, completeness, "T1\nT2")
    evidence = [_list_item_evidence(item, True, None) for item in included]
    gate = evaluate_answer_gate(1, reconstructed, "semantic_list_extraction", "implemented", ["file1"], evidence, True, question_type="semantic_document_lookup", verification=verification, semantic_contract={"verification_status": "passed"})
    checks = [
        ("positive_reconstruction", reconstructed == "T1\nT2"),
        ("answer_column_evidence", all(item.get("answer_column_name") == "ID" for item in evidence)),
        ("filter_column_evidence", all(item.get("filter_column_name") == "状態" for item in evidence)),
        ("location_evidence", all(item.get("source_location") for item in evidence)),
        ("common_verification_fields", all(verification.get(key) is True for key in ("presence", "condition_match", "source_locations_present", "verbatim_match", "uniqueness", "independent_reconstruction_passed"))),
        ("gate_allowed", gate.allow_answer),
    ]
    missing_raw = candidate("T1", 1, location=False)
    for key in ("table_index", "row_index"):
        missing_raw.pop(key, None)
    missing_location = [_list_item_evidence(missing_raw, True, None)]
    checks.append(("missing_location_fails", not missing_location[0]["item_verification_passed"]))
    print("semantic_list_contract_tests=%d passed=%d failed=%d" % (len(checks), sum(ok for _, ok in checks), sum(not ok for _, ok in checks)))
    for name, ok in checks:
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
    if not all(ok for _, ok in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
