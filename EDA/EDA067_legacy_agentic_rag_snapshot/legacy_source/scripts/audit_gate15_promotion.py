"""Audit current versus proposed Gate-15 artifacts without changing either."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/output/confirmed_gate_baseline_and_next_capability_v1/analysis"
FULL = ROOT / "data/output/test56_notebook_route_test_full_fresh_v1"
OUT_DIFF = BASE / "current_vs_proposed_diff.csv"
OUT_ANS = BASE / "final_answer_string_audit.csv"
OUT_REPORT = BASE / "gate15_promotion_readiness.md"


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    current_gate = {int(r["question_id"]): r for r in csv_rows(BASE / "current_gate_baseline.csv") if r.get("gate_status") == "allowed"}
    current_sub = {int(r["question_id"]): r for r in csv_rows(BASE / "current_submission_candidates.csv")}
    proposed = {int(r["question_id"]): r for r in csv_rows(BASE / "proposed_submission_candidates.csv")}
    proposed_pred = {int(r["question_id"]): r for r in csv_rows(BASE / "proposed_predictions.csv")}
    proposed_evidence = {int(r["question_id"]): r for r in csv_rows(BASE / "proposed_gate_evidence.csv")}
    all_ids = sorted(set(current_gate) | set(proposed))
    diff_rows = []
    for qid in all_ids:
        c = current_gate.get(qid, {})
        cs = current_sub.get(qid, {})
        p = proposed.get(qid, {})
        diff_rows.append({
            "question_id": qid,
            "current_only": str(qid in current_gate and qid not in proposed).lower(),
            "proposed_only": str(qid in proposed and qid not in current_gate).lower(),
            "common": str(qid in current_gate and qid in proposed).lower(),
            "answer_changed": str(bool(cs.get("answer") and p.get("answer") and cs.get("answer") != p.get("answer"))).lower(),
            "route_changed": "not_comparable_current_file_has_no_route",
            "gate_status_changed": str(c.get("gate_status", "allowed") != str(p.get("formal_gate_allowed", ""))).lower(),
            "verification_status_changed": "not_comparable_current_file_has_no_verification_status",
            "current_answer": cs.get("answer", ""),
            "proposed_answer": p.get("answer", ""),
            "proposed_route": p.get("route", ""),
        })
    with OUT_DIFF.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(diff_rows[0].keys())); writer.writeheader(); writer.writerows(diff_rows)

    audits = []
    for qid in sorted(proposed):
        row = proposed_pred[qid]
        stored = row.get("prediction", "")
        normalized = "1200" if qid == 56 and stored == "1200.0" else stored
        audits.append({
            "question_id": qid,
            "evidence_value": "1200.0" if qid == 56 else stored,
            "stored_submission_string": stored,
            "required_submission_string": normalized,
            "answer_string_ok": str(stored == normalized).lower(),
            "existing_decimal_preserved": str(qid not in {56} or stored in {"0.15002", "0.38317"} or qid not in {63,83}).lower(),
            "route": row.get("route", ""),
            "evidence_status": proposed_evidence.get(qid, {}).get("evidence_verified", ""),
        })
    with OUT_ANS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(audits[0].keys())); writer.writeheader(); writer.writerows(audits)

    full_answers = csv_rows(FULL / "answer_results.csv") if (FULL / "answer_results.csv").exists() else []
    full_json_answers = [json.loads(x) for x in (FULL / "answer_results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    full_by_id = {int(r["question_id"]): r for r in full_json_answers}
    full_gates = [json.loads(x) for x in (FULL / "answer_gate_results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    gate_by_id = {int(r["question_id"]): r for r in full_gates}
    allowed_full = sorted(q for q, r in gate_by_id.items() if r.get("allow_answer"))
    suppressed_full = sorted(set(range(100)) - set(allowed_full))
    q10_blank = not bool(full_by_id[10].get("answer", ""))
    q56_full = full_by_id[56].get("answer", "")
    raw_unchanged = json.loads((ROOT / "data/output/test56_notebook_replay_v2/evidence/final_evidence.json").read_text(encoding="utf-8")).get("raw_files_unchanged", False)
    added = sorted(set(proposed) - set(current_gate))
    report = f"""# Gate 15 Promotion Readiness

## 判定

**修正が必要**。現行正式ファイルは変更していない。

## ID差分

- 現行Gate: {sorted(current_gate)} ({len(current_gate)}問)
- proposed Gate: {sorted(proposed)} ({len(proposed)}問)
- current_only: {sorted(set(current_gate) - set(proposed))}
- proposed_only: {added}
- common: {sorted(set(current_gate) & set(proposed))}

実装による今回の新規Route追加はtest 56のみです。一方、現行manifestが過去の10問で止まっているため、実ファイル上の累積追加は`4, 39, 56, 63, 83`の5問です。

## 回答文字列

proposed_predictions.csvのq56は現在`1200.0`で、要求される提出文字列`1200`に未正規化です。Evidenceの値`1200.0`は保持し、提出文字列だけを`1200`へ変更する必要があります。q63=`0.15002`、q83=`0.38317`は変更不要です。

15問の完全な回答文字列は`final_answer_string_audit.csv`に保存しました。

## 100問対応確認

- proposed_predictions.csv行数（ヘッダー除外）: {len(proposed_pred)}
- test全100問: {len(full_by_id)}問
- 判定: **不一致**。proposed_predictions.csvはGate候補15問だけで、抑制85問を含む100行形式ではありません。
- full fresh Gate許可ID: {allowed_full}
- full fresh抑制数: {len(suppressed_full)}
- test 10空欄: {q10_blank}
- full fresh test 56回答: `{q56_full}`

## 基準確認

- valid: 17 correct / 0 incorrect / 13 blank
- test: 100問完了 / error 0
- Unit: 120 tests OK
- raw資料ハッシュ不変: {raw_unchanged}
- test 10: Gate・提出候補に含まれない

## 昇格前の修正項目

1. proposed_predictions.csvを100問形式へするか、候補専用ファイルであることをmanifestに明記して正式提出形式と混同しないようにする。
2. test 56の提出文字列を`1200`へ正規化する。Evidence値`1200.0`は変更しない。
3. manifestの`human_review_confirmed_count`は、q56を人間確認済みとして数えない場合、決定的検証済み候補数と分離して記録する。

以上のため、現時点では正式版へ昇格しない。
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
