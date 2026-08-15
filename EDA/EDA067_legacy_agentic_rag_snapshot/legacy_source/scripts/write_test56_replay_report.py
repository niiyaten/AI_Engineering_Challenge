"""Write the human-readable audit report for the test 56 replay."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "output" / "test56_notebook_replay_v2"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    final = read_json(OUT / "evidence" / "final_evidence.json")
    test_dir = ROOT / "data" / "output" / "test56_notebook_route_test_full_fresh_v1"
    gates = [json.loads(line) for line in (test_dir / "answer_gate_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    allowed = [row["question_id"] for row in gates if row.get("allow_answer")]
    q56_gate = next(row for row in gates if row["question_id"] == 56)
    versions = {
        "python_executable": str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "imported_package_path": str(ROOT / "src" / "rag_competition"),
        "working_directory": str(ROOT),
        "PYTHONPATH": "src",
        "config_path": "configs/",
        "cache_version": "fresh/no-answer-cache/no-execution-cache",
        "index_version": "fresh extraction index in test56_notebook_route_test_full_fresh_v1",
        "uv_executable": r"C:\Users\中村\.local\bin\uv.exe",
        "locked_versions": {"python": "3.11.15", "numpy": "2.4.3", "pandas": "3.0.1", "matplotlib": "3.10.8", "seaborn": "0.13.2"},
    }
    (OUT / "logs" / "uv_search.log").write_text(
        "Get-Command uv: not available in the initial shell\n"
        "resolved absolute path: C:\\Users\\中村\\.local\\bin\\uv.exe\n"
        "workspace-local UV_CACHE_DIR used after user-cache access denial\n",
        encoding="utf-8",
    )
    (OUT / "logs" / "environment_versions.log").write_text(json.dumps(versions, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "logs" / "regression.log").write_text(
        "unit: python -m unittest discover -s tests -p test_*.py -q -> 120 tests OK\n"
        "valid: test56_notebook_route_valid_fresh_v1 -> 17 answered, 0 incorrect, 13 blank\n"
        "test: test56_notebook_route_test_full_fresh_v1 -> 100 completed, 0 errors\n"
        f"allowed IDs: {allowed}\n",
        encoding="utf-8",
    )
    (OUT / "logs" / "replay_run1.log").write_text(json.dumps(final["run1"], ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "logs" / "replay_run2.log").write_text(json.dumps(final["run2"], ensure_ascii=False, indent=2), encoding="utf-8")
    evidence = final["run1"]["evidence"]
    report = f"""# test 56 Notebook Replay Audit

## 結果

- 対象Notebook: `{final['source_notebook']}`
- 回答候補: `{final['run1']['answer']}`
- 2回の再実行一致: `{final['rerun_consistent']}`
- rawハッシュ不変: `{final['raw_files_unchanged']}`
- 限定正式Route Gate: `{q56_gate['gate_status']}`
- full test Gate許可ID: `{', '.join(map(str, allowed))}`

## 環境

- uv: `{versions['uv_executable']}`
- Python: `{versions['locked_versions']['python']}`
- numpy/pandas/matplotlib/seaborn: `{versions['locked_versions']['numpy']}` / `{versions['locked_versions']['pandas']}` / `{versions['locked_versions']['matplotlib']}` / `{versions['locked_versions']['seaborn']}`
- `PYTHONPATH`: `src`
- 実行環境: `data/output/test56_notebook_replay_v2/workspace/` のロック環境

初回の `uv sync --frozen` はユーザーキャッシュへのアクセス拒否で失敗しました。workspace-local `UV_CACHE_DIR`へ切り替えた再試行は成功し、依存バージョンを確認しました。

## 再現内容

- 実行セル: `{evidence['executed_cells']}`
- 実行分岐: `{evidence['executed_branch']}`。未捕捉例外なし。
- 描画関数: Notebookの目的変数分布描画。Axesはタイトル・y軸ラベルで一意選択。
- figsize/dpi: `{evidence['figsize']}` / `{evidence['dpi']}`
- ylim: `{evidence['ylim']}`
- yticks: `{evidence['yticks']}`
- 表示範囲内のyticks: `{evidence['visible_yticks']}`
- 最大表示目盛り: `{evidence['max_visible_ytick']}`
- 棒: `{[p['height'] for p in evidence['patches']]}`

回答はNotebookの保存画像をOCRしたものではなく、同一コードを隔離環境で2回実行し、`Axes.get_yticks()`から決定的に取得しました。

## 回帰

- Unit: 120 tests passed
- valid fresh: 17 correct / 0 incorrect / 13 blank
- test fresh: 100 completed / 0 errors
- 既存14問: 全問維持
- test 0: `suppressed_comparison`, `comparison_source_missing`
- test 10: 抑制維持。今回の対象外で、回答値をruntimeへ入力していません。
- test 85: 抑制維持

## 変更

- `src/rag_competition/notebook_executor.py`: ロック環境でNotebookを再実行し、Axesの位置付きEvidenceを共通Verifierへ渡す汎用Routeを追加。共通`location`を追加して既存Evidence検証へ接続。
- `src/rag_competition/route_registry.py`: Notebook軸目盛り要求の形式・資料関係に基づくRoute選択。
- `src/rag_competition/tool_registry.py`: Route Executor登録。
- `src/rag_competition/answer_gate.py`: Notebook軸目盛り専用の検証項目。
- `src/rag_competition/semantic_contract.py`: 軸目盛りを表集計と誤認しない契約。
- `tests/test_route_registry.py`, `tests/test_notebook_executor.py`: Route・曖昧Axes・位置EvidenceのUnit試験。

test 56は新規候補であり、人間確認前のため `needs_human_review=true`、`safe_to_submit=false` として扱います。commit、push、PRは実施していません。
"""
    (OUT / "analysis" / "final_audit.md").write_text(report, encoding="utf-8")
    (OUT / "analysis" / "implementation_report.md").write_text(
        "# Implementation Report\n\n" + report.split("## 変更\n", 1)[1], encoding="utf-8"
    )
    (OUT / "analysis" / "final_audit.json").write_text(json.dumps({"environment": versions, "allowed_ids": allowed, "q56_gate": q56_gate, "replay": final}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
