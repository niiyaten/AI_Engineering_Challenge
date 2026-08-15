from rag_competition.semantic_executor import _condition_evidence_audit, _detect_comparison_requirement, build_list_spec


def main() -> None:
    cases = [
        ("旧版から新版への変更内容をすべて挙げてください", True),
        ("資料に記載された機能をすべて抽出してください", False),
        ("3つの報告書に記載された担当者をすべて挙げてください", False),
    ]
    for question, expected in cases:
        actual = _detect_comparison_requirement(question)["is_comparison"]
        assert actual == expected, (question, actual)
    assert build_list_spec("旧版から新版への変更内容をすべて挙げてください").unsupported_reason == "comparison_source_missing"
    positive = _condition_evidence_audit("KPIとして未達成の項目を挙げてください", [{"candidate_id": "a", "item_value": "KPI A 未達成", "original_text": "KPI A 未達成"}], [])
    negative = _condition_evidence_audit("KPIとして未達成の項目を挙げてください", [{"candidate_id": "b", "item_value": "KPI A", "original_text": "KPI A"}], [])
    assert positive["all_conditions_supported"] is True
    assert negative["all_conditions_supported"] is False
    print("comparison_condition_guard_tests=passed")


if __name__ == "__main__":
    main()
