from pathlib import Path


def test_primary_alias_only_answers_keep_supporting_metrics_out_of_answer() -> None:
    source = Path(
        "src/rag_recovery/executors/remaining50_generalization.py"
    ).read_text(encoding="utf-8")

    assert "return _answer(alias,'cross_project_missing_row_count'" in source
    assert "missing_row_count=n" in source
    assert "return _answer(alias,'tm_estimate_actual_hours_gap'" in source
    assert "gap_hours=gap" in source
    assert "f'{alias}、{n:,}行'" not in source
    assert "f'{alias}、{gap:g}時間'" not in source
