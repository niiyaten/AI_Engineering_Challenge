from __future__ import annotations

import re
import unicodedata
from typing import Any


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").lower()


def verify_semantic_contract(
    question: str,
    operation_names: list[str],
    tool_outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    """質問に明示された操作と、実際に実行した処理・根拠の対応を検証する。"""
    text = _normalize(question)
    output = tool_outputs[-1] if tool_outputs else {}
    spec = output.get("calculation_spec") or output.get("spec") or output.get("extraction_spec") or {}
    evidence_value = output.get("evidence") or []
    evidence = evidence_value if isinstance(evidence_value, list) else [evidence_value]
    answer = str(output.get("answer") or "")
    evidence_dicts = [item for item in evidence if isinstance(item, dict)]
    formula = str(output.get("calculation_formula") or next((item.get("calculation_formula") for item in evidence_dicts if item.get("calculation_formula")), ""))

    asks_filter_definition = "抽出条件" in text
    asks_aggregation_definition = "集計内容" in text or "集計方法" in text
    asks_aggregation = asks_aggregation_definition or any(
        term in text for term in ("合計", "平均", "割合", "件数", "最大", "最小", "予測値", "計算")
    )
    asks_identifier = bool(re.search(r"(?:id|識別子|コード|番号)(?:を|:|：|\s|$)", text, re.IGNORECASE))
    output_question_type = str(output.get("question_type") or "")
    # An axis-tick question asks for a rendered axis property, not a table aggregation.
    if output_question_type == "notebook_axis_ticks":
        asks_aggregation = False
    semantic_verification = output.get("verification") or {}
    semantic_spec_present = bool(output.get("semantic_spec"))

    has_filter_contract = bool(
        spec.get("filters")
        or spec.get("filter_conditions")
        or any(
            item.get("filter_conditions") or item.get("filters")
            or item.get("reconstructed_hierarchy")
            for item in evidence_dicts
        )
        or (formula and re.search(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[^、,]+", answer))
    )
    has_aggregation_contract = bool(
        spec.get("aggregation")
        or spec.get("operations")
        or formula
        or any(name in {"table_aggregation", "calculation"} for name in operation_names)
    )
    identifier_terms = [str(value) for value in spec.get("identifier_terms", []) if str(value).strip()]
    identifier_contract_valid = True
    if output_question_type == "identifier_verbatim" and not asks_identifier:
        # 日付やページ番号の数字を識別子として扱う経路を拒否する。
        identifier_contract_valid = False
    if asks_identifier and output_question_type == "identifier_verbatim":
        identifier_items = [str(item.get("text") or "").strip() for item in evidence_dicts]
        all_identifier_output = bool(spec.get("identifier_output_only")) and bool(identifier_items) and all(
            re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*\d+", value) for value in identifier_items
        )
        identifier_contract_valid = bool(identifier_terms) or all_identifier_output

    checks: dict[str, bool | None] = {
        "filter_condition_match": has_filter_contract if asks_filter_definition else None,
        "aggregation_operation_match": has_aggregation_contract if asks_aggregation else None,
        "identifier_intent_match": identifier_contract_valid if (asks_identifier or output_question_type == "identifier_verbatim") else None,
        "target_concept_match": semantic_verification.get("condition_match") if semantic_spec_present else None,
        "requested_output_type_match": bool(output.get("semantic_spec", {}).get("output_type")) if semantic_spec_present else None,
        "verbatim_requirement_match": semantic_verification.get("verbatim_match") if semantic_spec_present else None,
        "list_requirement_match": None if not semantic_spec_present or output.get("semantic_spec", {}).get("selection_mode") != "all" else semantic_verification.get("required_items_complete"),
    }
    if output_question_type == "calculation" and semantic_verification.get("required_inputs_present") is not None:
        checks.update({
            "document_role_match": semantic_verification.get("document_role_match"),
            "target_metric_match": semantic_verification.get("target_metric_match"),
            "operation_match": semantic_verification.get("operation_match"),
            "condition_coverage": semantic_verification.get("condition_coverage"),
            "unit_match": semantic_verification.get("unit_match"),
            "rounding_match": semantic_verification.get("rounding_match"),
            "output_type_match": semantic_verification.get("output_type_match"),
        })
    if output_question_type == "id_count":
        count_spec = output.get("count_spec") or {}
        checks.update({
            "target_id_types_match": semantic_verification.get("target_id_types_resolved"),
            "count_semantics_match": bool(count_spec.get("count_semantics")),
            "duplicate_policy_match": semantic_verification.get("duplicate_policy_applied"),
            "invalid_value_policy_match": semantic_verification.get("invalid_values_removed"),
            "file_exclusion_conditions_match": semantic_verification.get("excluded_file_types_respected"),
            "output_type_match": semantic_verification.get("answer_format_valid"),
            "no_sum_of_id_values": semantic_verification.get("no_sum_of_id_values"),
        })
    failed = [name for name, value in checks.items() if value is False]
    return {
        "question_contract": {
            "filter_definition_required": asks_filter_definition,
            "aggregation_definition_required": asks_aggregation_definition,
            "aggregation_required": asks_aggregation,
            "identifier_required": asks_identifier,
        },
        "execution_contract": {
            "operations": operation_names,
            "filter_contract_present": has_filter_contract,
            "aggregation_contract_present": has_aggregation_contract,
            "identifier_terms": identifier_terms,
            "output_question_type": output_question_type,
        },
        **checks,
        "failed_checks": failed,
        "verification_status": "passed" if not failed else "failed",
    }
