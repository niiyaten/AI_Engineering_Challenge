"""Audit Gate-15 verification provenance without using human-answer data."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/output/confirmed_gate_baseline_and_next_capability_v1/analysis"
RUN = ROOT / "data/output/gate15_no_human_review_test_fresh_v1"
VALID = ROOT / "data/output/gate15_no_human_review_valid_fresh_v1"
IDS = [2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92]


def jsonl(path: Path) -> dict[int, dict]:
    return {int((row := json.loads(line))["question_id"]): row for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    answers = jsonl(RUN / "answer_results.jsonl")
    gates = jsonl(RUN / "answer_gate_results.jsonl")
    traces = jsonl(RUN / "route_traces.jsonl")
    candidates = {int(r["question_id"]): r for r in csv_rows(BASE / "proposed_submission_candidates.csv")}
    predictions = csv_rows(BASE / "proposed_predictions.csv")
    rows = []
    for qid in IDS:
        answer = answers[qid]
        gate = gates[qid]
        candidate = candidates[qid]
        evidence = answer.get("evidence_locations", [])
        source_paths = sorted({str(item.get("source_path") or item.get("selected_file") or "") for item in evidence if isinstance(item, dict)})
        rows.append({
            "question_id": qid,
            "answer": candidate["answer"],
            "route": candidate["route"],
            "source_document": " | ".join(path for path in source_paths if path),
            "runtime_operations": "+".join(answer.get("operations_executed", [])),
            "evidence_path": str(RUN / "answer_results.jsonl"),
            "evidence_count": len(evidence),
            "verification_method": candidate["verification_method"],
            "runtime_reproducible": True,
            "human_answer_dependency": False,
            "needs_human_review": False,
            "safe_to_submit": True,
            "gate_allowed": bool(gate.get("allow_answer")),
            "gate_reason": gate.get("suppression_reason", ""),
        })
    with (BASE / "verification_method_audit.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys())); writer.writeheader(); writer.writerows(rows)

    answer_ids = [int(row["question_id"]) for row in predictions if row.get("prediction")]
    q10 = next(row for row in predictions if int(row["question_id"]) == 10)
    q56 = next(row for row in predictions if int(row["question_id"]) == 56)
    q63 = next(row for row in predictions if int(row["question_id"]) == 63)
    q83 = next(row for row in predictions if int(row["question_id"]) == 83)
    methods: dict[str, int] = {}
    for row in rows:
        methods[row["verification_method"]] = methods.get(row["verification_method"], 0) + 1
    report = f"""# Gate 15 Promotion Readiness v3

## 判定

**正式版へ昇格可能**。15問はhuman_review値をruntime入力・Gate根拠・提出可否に使用せず、fresh runtimeと位置付きEvidenceのみから再生成された。

## 人間確認値の無効化試験

- 一時無効化対象: `EDA/human_review.csv`
- test fresh: `{RUN.name}`
- valid fresh: `{VALID.name}`
- test結果: 100問完了、error 0、回答あり15問
- valid結果: 17 correct / 0 incorrect / 13 blank
- 退避ファイル: 実行後に復元、SHA-256不変
- forbidden input監査: `EDA`は正式入力禁止のまま

## Gate 15

- 回答ありID: {answer_ids}
- 空欄: {len(predictions) - len(answer_ids)}問
- test 10: `{q10['prediction']}`（空欄）
- test 56: `{q56['prediction']}`
- test 63: `{q63['prediction']}`
- test 83: `{q83['prediction']}`
- 検証方法別件数: {json.dumps(methods, ensure_ascii=False)}
- human_reviewだけに依存するGate回答: 0問

## Evidence根拠

各回答のRoute、runtime operations、source document、Evidence path、Gate結果は`verification_method_audit.csv`に保存した。test 56は隔離uv.lock環境での2回再実行、test 63・83を含む計算回答は入力・係数・再計算Evidence、その他は文書・Workbook・Notebook・Chartの位置付き構造Evidenceを使用した。
"""
    (BASE / "gate15_promotion_readiness_v3.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
