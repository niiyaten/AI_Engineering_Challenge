from __future__ import annotations

import csv
from pathlib import Path

from rag_recovery.archive import extract_zip_safely
from rag_recovery.models import Question
from rag_recovery.runner import RecoveryRunner


def solve(runner: RecoveryRunner, text: str, sources: tuple[str, ...] = ()):
    result, _ = runner.solve(Question("test", 999, text, sources))
    return result


def test_document_numeric_difference(sample_share: Path):
    runner = RecoveryRunner(sample_share)
    source = "共有ドライブ/プロジェクト/株式会社テスト分析/00.提案/データサイエンティスト調査.docx"
    result = solve(runner, "テスト分析のデータサイエンティスト調査.docxにおいて、米国平均給与における機械学習（ML）エンジニアとデータエンジニアの差はいくらですか。", (source,))
    assert result.answered
    assert "14,744" in result.answer


def test_table_date_color_regression(sample_share: Path):
    runner = RecoveryRunner(sample_share)
    schedule = "共有ドライブ/プロジェクト/株式会社テスト分析/02.計画/スケジュール_r2.xlsx"
    result = solve(runner, "テスト分析のスケジュール_r2.xlsxにおいて、2025-08-11から2025-09-09の間に開始日または終了日が設定されているタスクIDをすべて挙げてください。", (schedule,))
    assert result.answered and result.answer == "T01、T02、T03"
    result = solve(runner, "テスト分析のスケジュール_r2.xlsxにおいて、オレンジにハイライトされている行のタスク名をすべて答えてください。", (schedule,))
    assert result.answered and "中間報告会実施" in result.answer
    regression = "共有ドライブ/プロジェクト/株式会社テスト分析/03.データ/regression.xlsx"
    result = solve(runner, "テスト分析のregression.xlsxにおいて、回帰分析の結果として記載されている係数をindex=1770のデータに当てはめたときの予測値はいくつですか。小数第5位まで答えてください。", (regression,))
    assert result.answered and result.answer == "17.00000"


def test_phase2_format_diff_chart(sample_share: Path):
    runner = RecoveryRunner(sample_share)
    report = "共有ドライブ/プロジェクト/株式会社テスト分析/05.会議/報告資料/報告資料.docx"
    result = solve(runner, "テスト分析の報告資料.docxの中で、太字、下線、イタリックのすべてに該当する箇所を抽出してください。", (report,))
    assert result.answered and result.answer == "重要な実施条件"
    r1 = "共有ドライブ/プロジェクト/株式会社テスト分析/02.計画/スケジュール_r1.xlsx"
    r3 = "共有ドライブ/プロジェクト/株式会社テスト分析/02.計画/スケジュール_r3.xlsx"
    result = solve(runner, "テスト分析のスケジュール_r1.xlsxとスケジュール_r3.xlsxを比較したとき、未着手から完了への変更を除いて、案件遂行に関連する変更点を挙げてください。", (r1, r3))
    assert result.answered and "小林 直樹" in result.answer and "ステータス" not in result.answer
    chart = "共有ドライブ/プロジェクト/株式会社テスト分析/03.データ/chart.xlsx"
    result = solve(runner, "テスト分析のchart.xlsxにあるグラフ1はどのカラムを可視化したものですか。", (chart,))
    assert result.answered and "hum" in result.answer


def test_code_json_and_cross_project(sample_share: Path):
    runner = RecoveryRunner(sample_share)
    metrics = "共有ドライブ/プロジェクト/株式会社テスト分析/04.分析/analysis_outputs/metrics.json"
    features = "共有ドライブ/プロジェクト/株式会社テスト分析/04.分析/features.py"
    result = solve(runner, "テスト分析のmetrics.jsonとfeatures.pyから、生成された特徴量はいくつありますか。", (metrics, features))
    assert result.answered and result.answer == "2"
    result = solve(runner, "全案件のtrain.csvにおいて、欠損行数が最も多い案件を案件名で答えてください。")
    assert result.answered and "第二分析" in result.answer


def test_full_130_csv_run(sample_share: Path, answers130: Path, tmp_path: Path):
    runner = RecoveryRunner(sample_share)
    out = tmp_path / "out"
    summary = runner.run_csv(answers130, out)
    assert summary["input_rows"] == 130
    assert summary["initial_unknown"] == 8
    assert summary["recovered"] >= 7
    with (out / "answers_130_phase12_recovered.csv").open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 130
    assert rows[129]["answer"] == "既存回答"
    assert (out / "recovery_evidence.jsonl").exists()


def test_zip_path_traversal_rejected(tmp_path: Path):
    import zipfile
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "bad")
    try:
        extract_zip_safely(archive, tmp_path / "extract")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe zip member was accepted")
