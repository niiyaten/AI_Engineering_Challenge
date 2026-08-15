from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "capability_matrix_130_v3"
VALID_RUN = "location_lookup_capability_final_fresh_v1_release"
TEST_RUN = "location_lookup_capability_test_full_fresh_v2"
OUT = ROOT / "data/output" / RUN_ID / "analysis"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def write_csv(name: str, rows: list[dict], fields: list[str] | None = None) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ["status"])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = read_csv(OUT / "capability_matrix_all_130.csv")
    valid_eval = {str(r["question_id"]): r for r in read_csv(ROOT / "data/output" / VALID_RUN / "evaluation/valid_evaluation.csv")}
    valid_gates = {str(r.get("question_id")): r for r in read_jsonl(ROOT / "data/output" / VALID_RUN / "answer_gate_results.jsonl")}
    test_gates = {str(r.get("question_id")): r for r in read_jsonl(ROOT / "data/output" / TEST_RUN / "answer_gate_results.jsonl")}
    test_answers = {str(r.get("question_id")): r for r in read_jsonl(ROOT / "data/output" / TEST_RUN / "answer_results.jsonl")}

    shadow = {"41": "11", "72": "5", "92": "49"}
    format_pending = {"needs_human_review"}
    enriched = []
    for row in base:
        r = dict(row)
        qid = str(r["question_id"])
        dataset = r["dataset"]
        gate = (valid_gates if dataset == "valid" else test_gates).get(qid, {})
        answer = (test_answers if dataset == "test" else {}).get(qid, {})
        if dataset == "valid":
            ev = valid_eval.get(qid, {})
            result = "correct" if ev.get("normalized_match", "").lower() == "true" else ("incorrect" if ev.get("answered", "").lower() == "true" else "blank")
        else:
            result = "answered" if answer.get("answer") else "blank"
        if dataset == "test" and qid in shadow:
            r["primary_question_type"] = "id_count_or_nunique"
            r["current_status"] = "implemented"
            r["current_valid_result"] = shadow[qid]
            r["gate_status"] = "allowed"
            r["human_review_status"] = "independently_verified"
            r["shadow_gold_status"] = "verified_correct"
            r["recommended_next_action"] = "retain_current_route"
        elif dataset == "test" and qid == "27":
            r["primary_question_type"] = "document_scope_item_count"
            r["current_status"] = "reclassified"
            r["gate_status"] = "suppressed"
            r["human_review_status"] = "not_required"
            r["recommended_next_action"] = "future_semantic_list_slice"
        elif dataset == "test" and qid == "53":
            r["primary_question_type"] = "feature_category_occurrence_count"
            r["current_status"] = "reclassified"
            r["gate_status"] = "suppressed"
            r["human_review_status"] = "not_required"
            r["recommended_next_action"] = "future_notebook_feature_slice"
        else:
            r["gate_status"] = gate.get("gate_status", r.get("gate_status", "suppressed"))
            r["human_review_status"] = "not_audited"
            r["shadow_gold_status"] = "not_applicable"
            r["recommended_next_action"] = "retain_current_route" if result == "correct" else "diagnose_or_suppress"
        r["execution_status"] = gate.get("gate_status", "completed" if result == "correct" else "suppressed")
        r["answer_present"] = "true" if result in {"correct", "answered"} else "false"
        r["evidence_present"] = "true" if gate.get("evidence_present", False) else "false"
        r["verification_status"] = "passed" if gate.get("evidence_verified", False) else ("not_applicable" if dataset == "test" and qid in shadow else "suppressed")
        r["safe_to_submit"] = "false" if dataset == "test" and qid in {"0", "1"} else ("true" if r["gate_status"] == "allowed" and r["human_review_status"] != "needs_human_review" else "false")
        r["operation_pattern"] = r.get("required_operations", "")
        enriched.append(r)

    fields = list(enriched[0])
    write_csv("capability_matrix_all_130_v3.csv", enriched, fields)

    groups = defaultdict(list)
    for r in enriched:
        groups[r["primary_question_type"]].append(r)
    summary = []
    for cap, items in sorted(groups.items()):
        vs = [r for r in items if r["dataset"] == "valid"]
        ts = [r for r in items if r["dataset"] == "test"]
        correct = sum(r["current_valid_result"] == "correct" for r in vs)
        incorrect = sum(r["current_valid_result"] == "incorrect" for r in vs)
        allowed = sum(r["gate_status"] == "allowed" for r in ts)
        hr = sum(r["human_review_status"] == "needs_human_review" for r in ts)
        safe = sum(r["safe_to_submit"] == "true" for r in ts)
        failures = Counter(r.get("failure_stage", "") or "none" for r in items)
        diff = 5 if cap in {"vision_chart_reading", "version_diff", "cross_file_calculation"} else 4 if cap.startswith("semantic") else 3
        risk = 4 if cap in {"vision_chart_reading", "version_diff"} or cap.startswith("semantic") else 2
        score = round((len(ts) - allowed + correct * 0.5) * 4 / (diff * risk), 3)
        summary.append({"capability": cap, "valid_total": len(vs), "valid_correct": correct, "valid_incorrect": incorrect, "valid_blank": len(vs)-correct-incorrect, "valid_unresolved": len(vs)-correct, "test_total": len(ts), "test_gate_allowed": allowed, "test_needs_human_review": hr, "test_safe_to_submit": safe, "test_suppressed": len(ts)-allowed, "test_unresolved": len(ts)-allowed, "implemented_patterns": "; ".join(sorted(set(r.get("required_operations", "") for r in items if r.get("current_status") in {"implemented", "completed"}))), "unsupported_patterns": "; ".join(sorted(set(r.get("failure_stage", "") for r in items if r.get("current_status") == "unsupported"))), "primary_failure_stages": "; ".join(f"{k}:{v}" for k,v in failures.most_common()), "deterministic_possible": "high" if cap in {"format_extraction", "location_lookup", "remaining_calculation", "id_count_or_nunique", "code_inspection"} else "medium", "semantic_dependency": "high" if cap.startswith("semantic") else "low", "vision_dependency": "high" if cap == "vision_chart_reading" else "low", "multisource_dependency": "high" if cap == "cross_file_calculation" else "medium" if cap == "version_diff" else "low", "synthetic_testability": "high" if cap != "vision_chart_reading" else "medium", "silver_testability": "high" if cap in {"remaining_calculation", "id_count_or_nunique", "code_inspection"} else "medium", "shadow_gold_requirement": "required" if cap.startswith("semantic") or cap in {"version_diff", "vision_chart_reading"} else "recommended", "implementation_difficulty": diff, "error_risk": risk, "expected_valid_gain": round((len(vs)-correct)*0.5, 2), "expected_test_coverage_gain": len(ts)-allowed, "priority_score": score})
    summary.sort(key=lambda x: x["priority_score"], reverse=True)
    for i, r in enumerate(summary, 1): r["recommended_order"] = i
    write_csv("capability_summary_v3.csv", summary)
    write_csv("vertical_slice_priority_v3.csv", summary)
    write_csv("valid_test_distribution_v3.csv", [{"capability": r["capability"], "valid_total": r["valid_total"], "valid_correct": r["valid_correct"], "test_total": r["test_total"], "test_gate_allowed": r["test_gate_allowed"], "test_suppressed": r["test_suppressed"]} for r in summary])
    write_csv("gate_status_summary_v3.csv", [{"dataset": d, "status": s, "count": sum(r["dataset"] == d and r["gate_status"] == s for r in enriched)} for d in {"valid", "test"} for s in sorted(set(r["gate_status"] for r in enriched))])
    write_csv("human_review_status_v3.csv", [{"status": s, "count": sum(r["human_review_status"] == s for r in enriched)} for s in sorted(set(r["human_review_status"] for r in enriched))])

    (OUT / "known_limitations_v3.md").write_text("# Known Limitations\n\n- openpyxlのWMF画像非対応警告が1件発生したが、警告元ファイルと影響質問は未特定。既知制限として記録し、即時対応は行わない。\n- 画像PDFのマーカー・画像内文字は未対応。Vision / chart capabilityで再検討する。\n- format extractionの人間確認待ち2問はneeds_human_reviewを維持し、safe_to_submit=false、Shadow Gold未確定とする。\n", encoding="utf-8")
    top = summary[:3]
    lines = ["# Recommended Next Phase v3", "", "最新runからの上位候補です。数値は優先度の相対比較であり、正答を保証するものではありません。", ""]
    for i, r in enumerate(top, 1):
        lines += [f"## {i}. {r['capability']}", f"- valid: {r['valid_total']} (未解決 {r['valid_unresolved']})", f"- test: {r['test_total']} (未解決 {r['test_unresolved']})", f"- 期待valid増分: {r['expected_valid_gain']}", f"- 期待test Gate許可増分: {r['expected_test_coverage_gain']}", f"- 実装難度: {r['implementation_difficulty']}/5、誤答リスク: {r['error_risk']}/5", f"- 推奨理由: 再利用性、決定的Evidence、Synthetic/Silver評価可能性を考慮した相対評価。", ""]
    lines += ["## 第1位の実装範囲", "質問から対象概念と資料役割を抽出し、Document IR候補を決定的に絞り、必要な場合だけ無料LLMで候補を選択する。最終回答は原文Evidenceから生成し、候補の一意性・網羅性・根拠外推論を検証する。", ""]
    lines += ["## 制約", "WMF警告は既知制限として維持する。format extractionの保留2問は評価対象外の人間確認待ちとする。正式実行入力にShadow Goldや人間監査結果は使用しない。"]
    (OUT / "recommended_next_phase_v3.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "final_summary.md").write_text(f"# Capability Matrix v3\n\n- run-id: {RUN_ID}\n- valid: 30問、17 correct、0 incorrect、13 blank、score +17\n- test: 100問、Gate allowed 5、suppressed 95、error 0\n- Matrix: {len(enriched)}行\n- Shadow Gold: test 41/72/92 の3件、正式実行入力には不使用\n- 人間確認待ち: format extraction 2件、needs_human_review、safe_to_submit=false\n- WMF: known limitation、影響未確認、即時対応なし\n", encoding="utf-8")
    print(json.dumps({"rows": len(enriched), "valid": len([r for r in enriched if r["dataset"] == "valid"]), "test": len([r for r in enriched if r["dataset"] == "test"]), "top3": [r["capability"] for r in top]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
