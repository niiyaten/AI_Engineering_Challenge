from __future__ import annotations

from typing import Any

from .schemas import AnswerGateResult


def verify_evidence(answer: str, evidence: list[dict[str, Any]], used_file_ids: list[str]) -> tuple[bool, str]:
    if not used_file_ids:
        return False, "実際に使用したファイルがありません"
    if not evidence:
        return False, "回答根拠がありません"
    if not answer.strip():
        return False, "回答が空です"
    if all(item.get("preview_only") for item in evidence):
        return False, "SearchRecord previewしか根拠がありません"
    locations = [item.get("location") or item.get("source_location") or item.get("cell_ranges") or item.get("evidence_locations") for item in evidence]
    if not any(location for location in locations):
        return False, "根拠位置がありません"
    return True, ""


def evaluate_answer_gate(
    question_id: int,
    answer: str,
    executor_name: str,
    implementation_status: str,
    used_file_ids: list[str],
    evidence: list[dict[str, Any]],
    execution_success: bool,
    preview_only: bool = False,
    ambiguous: bool = False,
    verification_success: bool | None = None,
    question_type: str = "",
    verification: dict[str, Any] | None = None,
    semantic_contract: dict[str, Any] | None = None,
) -> AnswerGateResult:
    # 比較質問は比較Executorが実行されるまで回答候補を作らない。
    # 上位で保存された構造化抑制理由をGate監査へ返す。
    if question_type == "comparison" and verification and verification.get("executor_not_run"):
        reason = str(verification.get("suppression_reason") or "comparison_not_executed")
        return AnswerGateResult(
            question_id,
            False,
            "suppressed_comparison",
            executor_name,
            implementation_status,
            used_file_ids,
            False,
            False,
            preview_only,
            ambiguous,
            reason,
        )
    if implementation_status in {"not_implemented", "eda_prototype", "fallback"}:
        return AnswerGateResult(question_id, False, "suppressed_unimplemented", executor_name, implementation_status, used_file_ids, bool(evidence), False, preview_only, ambiguous, "Executorが正式実装ではありません")
    if ambiguous:
        return AnswerGateResult(question_id, False, "suppressed_ambiguous", executor_name, implementation_status, used_file_ids, bool(evidence), False, preview_only, True, "対象が一意に特定できません")
    if not execution_success:
        return AnswerGateResult(question_id, False, "suppressed_execution_failure", executor_name, implementation_status, used_file_ids, bool(evidence), False, preview_only, ambiguous, "Executorが正常終了していません")
    if preview_only:
        return AnswerGateResult(question_id, False, "suppressed_preview_only", executor_name, implementation_status, used_file_ids, bool(evidence), False, True, ambiguous, "SearchRecord previewのみの回答です")
    if semantic_contract and semantic_contract.get("verification_status") != "passed":
        failed = ", ".join(semantic_contract.get("failed_checks", []))
        return AnswerGateResult(question_id, False, "suppressed_verification_failure", executor_name, implementation_status, used_file_ids, bool(evidence), False, preview_only, ambiguous, f"質問条件と実行計画が一致しません: {failed}")
    verified, reason = verify_evidence(answer, evidence, used_file_ids)
    verification = verification or {}
    if question_type == "format_only":
        required = ("presence", "condition_match", "completeness", "verbatim_match")
    elif question_type == "identifier_verbatim":
        required = ("presence", "condition_match", "verbatim_match")
        if verification.get("uniqueness") is not None:
            required += ("uniqueness",)
        if verification.get("completeness") is not None and verification.get("selection_mode") == "all":
            required += ("completeness",)
    elif question_type == "location":
        required = (
            "presence",
            "location_match",
            "uniqueness",
            "location_spec_complete",
            "location_unit_match",
            "position_base_confirmed",
            "independent_recalculation",
            "answer_format_valid",
        )
    elif question_type == "semantic_document_lookup":
        required = (
            "selected_candidates_exist",
            "source_files_verified",
            "project_relation_verified",
            "presence",
            "condition_match",
            "answer_text_present_in_evidence",
            "answer_derived_only_from_selected_candidates",
            "source_locations_present",
            "no_unsupported_inference",
            "verbatim_match",
            "uniqueness",
        )
    elif question_type == "calculation":
        required = (
            "question_type_match",
            "condition_coverage",
            "input_presence",
            "type_validity",
            "filter_validity",
            "operation_validity",
            "rounding_validity",
            "reproducibility",
            "source_range",
        )
        # 複数資料計算では、単一表向け検証に加えて役割・式・独立再計算を必須にする。
        if verification.get("required_inputs_present") is not None:
            required += (
                "required_inputs_present",
                "column_bindings_verified",
                "conditions_applied",
                "operation_graph_complete",
                "source_ranges_present",
                "units_consistent",
                "rounding_valid",
                "independent_recalculation_match",
                "answer_format_valid",
                "no_unverified_fallback",
            )
    elif question_type == "id_count":
        required = (
            "required_sources_present",
            "target_id_types_resolved",
            "selected_columns_verified",
            "excluded_file_types_respected",
            "raw_values_recorded",
            "normalization_recorded",
            "invalid_values_removed",
            "duplicate_policy_applied",
            "per_type_counts_present",
            "cross_source_counts_present",
            "final_count_reproducible",
            "answer_format_valid",
            "no_sum_of_id_values",
        )
    elif question_type == "code_inspection":
        required = ("presence", "condition_match", "source_location", "answer_format_valid")
    elif question_type == "notebook_axis_ticks":
        required = (
            "presence",
            "condition_match",
            "source_location",
            "output_saved",
            "target_axes_unique",
            "ticks_visible",
            "replay_consistent",
            "answer_format_valid",
            "raw_files_unchanged",
        )
    elif question_type == "notebook_inspection":
        required = (
            "presence",
            "condition_match",
            "source_location",
            "output_saved",
            "extremum_reproducible",
            "uniqueness",
            "answer_format_valid",
        )
    elif question_type == "chart_inspection":
        required = (
            "presence",
            "condition_match",
            "source_location",
            "series_reference",
            "header_match",
            "uniqueness",
            "answer_format_valid",
        )
    else:
        required = ("presence",)
    if verification and any(verification.get(name) is not True for name in required):
        verified = False
        reason = "質問タイプに必要なEvidence Verification条件を満たしていません"
    if verification_success is False or not verified:
        return AnswerGateResult(question_id, False, "suppressed_verification_failure", executor_name, implementation_status, used_file_ids, bool(evidence), False, preview_only, ambiguous, reason or "Evidence Verificationに失敗しました")
    return AnswerGateResult(question_id, True, "allowed", executor_name, implementation_status, used_file_ids, True, True, False, False)
