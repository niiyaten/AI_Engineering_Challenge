from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {str(item.get("question_id", item.get("index"))): item for item in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}


def compact(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value or "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the capability matrix from the latest runs.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base-run", default="capability_matrix_130_v1")
    parser.add_argument("--valid-run", default="id_count_capability_final_fresh_v2")
    parser.add_argument("--test-run", default="id_count_test_full_v2")
    parser.add_argument("--id-count-run", default="id_count_capability_final_fresh_v2")
    parser.add_argument("--run-id", default="capability_matrix_130_v2")
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "data/output" / args.run_id / "analysis"
    base = read_csv(root / "data/output" / args.base_run / "analysis/capability_matrix_all_130.csv")
    valid_eval = {r["question_id"]: r for r in read_csv(root / "data/output" / args.valid_run / "evaluation/valid_evaluation.csv")}
    id_audit = {r["question_id"]: r for r in read_csv(root / "data/output" / args.id_count_run / "analysis/test_id_count_audit.csv")}
    id_quality = {r["metric"]: r["value"] for r in read_csv(root / "data/output" / args.id_count_run / "analysis/id_count_quality_metrics.csv")}

    audited = {
        "41": {"capability": "id_count_or_nunique", "operation": "unique_count", "status": "implemented", "failure": "", "gate": "allowed", "gold": "verified_correct", "answer": "11"},
        "72": {"capability": "id_count_or_nunique", "operation": "unique_count", "status": "implemented", "failure": "", "gate": "allowed", "gold": "verified_correct", "answer": "5"},
        "92": {"capability": "id_count_or_nunique", "operation": "issued_id_count", "status": "implemented", "failure": "", "gate": "allowed", "gold": "verified_correct", "answer": "49"},
        "27": {"capability": "document_scope_item_count", "operation": "semantic_list_item_count", "status": "reclassified", "failure": "semantic_api_unavailable", "gate": "suppressed", "gold": "not_applicable", "answer": ""},
        "53": {"capability": "feature_category_occurrence_count", "operation": "notebook_feature_category_count", "status": "reclassified", "failure": "evidence_failure", "gate": "suppressed", "gold": "not_applicable", "answer": ""},
    }

    rows: list[dict[str, object]] = []
    for row in base:
        qid = str(row["question_id"])
        item = dict(row)
        item["primary_capability"] = row["primary_question_type"]
        item["operation_pattern"] = row["required_operations"]
        item["gate_status"] = ""
        item["shadow_gold_status"] = "not_applicable"
        item["human_audit_status"] = "not_audited"
        item["recommended_next_action"] = "retain_current_route"
        item["current_status"] = row.get("current_status", "")
        if row["dataset"] == "valid":
            ev = valid_eval.get(qid, {})
            item["current_valid_result"] = "correct" if ev.get("normalized_match", "").lower() == "true" else ("incorrect" if ev.get("answered", "").lower() == "true" else "blank")
            item["gate_status"] = "allowed" if ev.get("answered", "").lower() == "true" else "suppressed"
        else:
            item["gate_status"] = "suppressed"
        # 監査済みIDはtest側の監査結果だけに適用する。valid側の同じ番号を再分類しない。
        if row["dataset"] == "test" and qid in audited:
            override = audited[qid]
            item["primary_capability"] = override["capability"]
            item["primary_question_type"] = override["capability"]
            item["operation_pattern"] = override["operation"]
            item["current_status"] = override["status"]
            item["failure_stage"] = override["failure"]
            item["gate_status"] = override["gate"]
            item["shadow_gold_status"] = override["gold"]
            item["human_audit_status"] = "independently_verified" if qid in {"41", "72", "92"} else "not_required"
            item["current_valid_result"] = override["answer"] if row["dataset"] == "test" else item["current_valid_result"]
            item["recommended_next_action"] = "retain_id_count_capability" if qid in {"41", "72", "92"} else "reclassify_for_future_slice"
        rows.append(item)

    # Preserve the original fields and add the fields required for v2 reporting.
    fields = list(rows[0])
    for field in ["primary_capability", "operation_pattern", "gate_status", "shadow_gold_status", "human_audit_status", "recommended_next_action"]:
        if field not in fields:
            fields.append(field)
    write_csv(out / "capability_matrix_all_130_v2.csv", [{key: row.get(key, "") for key in fields} for row in rows])

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["primary_capability"])].append(row)
    summary: list[dict[str, object]] = []
    for capability, items in sorted(groups.items()):
        valid = [r for r in items if r["dataset"] == "valid"]
        test = [r for r in items if r["dataset"] == "test"]
        test_gold = [r for r in test if r["shadow_gold_status"] != "not_applicable"]
        allowed = [r for r in test if r["gate_status"] == "allowed"]
        unresolved = [r for r in items if r["current_status"] not in {"implemented", "allowed", "completed"} and r["current_valid_result"] not in {"correct", "not_applicable"}]
        failures = Counter(str(r.get("failure_stage", "")) for r in items if r.get("failure_stage"))
        difficulty = 2 if capability in {"format_extraction", "location_lookup", "document_scope_item_count"} else 3 if capability in {"remaining_calculation", "id_count_or_nunique", "feature_category_occurrence_count", "notebook_inspection"} else 4 if capability.startswith("semantic") else 5
        risk = 1 if capability in {"format_extraction", "location_lookup", "id_count_or_nunique"} else 2 if capability in {"remaining_calculation", "document_scope_item_count", "feature_category_occurrence_count", "notebook_inspection"} else 4
        valid_correct = sum(r["current_valid_result"] == "correct" for r in valid)
        test_reclassified = sum(str(r["current_status"]) == "reclassified" for r in test)
        priority = ((len(test) - len(allowed)) + valid_correct * 0.5 + len(test_gold) * 0.5) * 4 / (difficulty * risk)
        summary.append({
            "capability": capability, "valid_total": len(valid), "valid_correct": valid_correct,
            "valid_unresolved": sum(r["current_valid_result"] != "correct" for r in valid),
            "test_total": len(test), "test_gate_allowed": len(allowed), "test_shadow_gold_count": len(test_gold),
            "test_shadow_gold_correct": sum(r["shadow_gold_status"] == "verified_correct" for r in test_gold),
            "test_unresolved": len(test) - len(allowed), "test_reclassified": test_reclassified,
            "current_coverage": round((valid_correct + len(allowed)) / max(1, len(valid) + len(test)), 3),
            "primary_failure_stages": "; ".join(f"{key}:{value}" for key, value in failures.most_common()),
            "valid_measurability": "high" if valid else "low", "synthetic_testability": "high" if capability not in {"vision_spatial", "chart_reading"} else "medium",
            "silver_testability": "high" if capability in {"id_count_or_nunique", "remaining_calculation", "feature_category_occurrence_count", "notebook_inspection"} else "medium",
            "shadow_gold_requirement": "required" if capability.startswith("semantic") or capability in {"version_diff", "vision_spatial"} else "recommended",
            "implementation_difficulty": difficulty, "error_risk": risk,
            "expected_valid_gain": sum(r["current_valid_result"] != "correct" for r in valid) * 0.5,
            "expected_test_coverage_gain": len(test) - len(allowed), "priority_score": round(priority, 3),
        })
    summary.sort(key=lambda r: float(r["priority_score"]), reverse=True)
    for i, row in enumerate(summary, 1): row["recommended_order"] = i
    write_csv(out / "capability_summary_v2.csv", summary)
    write_csv(out / "vertical_slice_priority_v2.csv", summary)

    comparison = []
    for row in summary:
        comparison.append({"capability": row["capability"], "valid_total": row["valid_total"], "valid_correct": row["valid_correct"], "test_total": row["test_total"], "test_gate_allowed": row["test_gate_allowed"], "test_unresolved": row["test_unresolved"], "test_share_minus_valid_share": round(float(row["test_total"]) / 100 - float(row["valid_total"]) / 30, 3)})
    write_csv(out / "valid_test_distribution_comparison_v2.csv", comparison)

    gold = [{"question_id": qid, "dataset": "test", "capability": "id_count_or_nunique", "shadow_gold_status": "verified_correct", "human_audit_status": "independently_verified", "answer": audited[qid]["answer"], "source": "human_audited_shadow_gold", "formal_pipeline_input": "false"} for qid in ("41", "72", "92")]
    write_csv(out / "shadow_gold_status_v2.csv", gold)

    top3 = summary[:3]
    gap = ["# Capability Gap Analysis v2", "", "この集計は最新Matrixを基礎に、ID件数監査と人間監査済みShadow Goldを評価欄へ反映したものです。Shadow Goldは正式パイプラインの入力には使用していません。", "", "## 主な差分", "", "- ID件数: test 5件中、対応済み3件、文書項目数へ再分類1件、Notebook特徴量カテゴリ数へ再分類1件。", "- test 41、72、92: Gate許可、Shadow Gold 3/3正解。", "- 日本語シート名の抽出キャッシュ衝突修正後、最新ID件数ルートの使用ファイルと失敗段階を反映。", "- valid: 正解17、誤答0、空回答13。", "", "## 対応済み・部分対応", "", "- Excel/CSV、Calculation、DOCX/PPTX書式、identifier_verbatim、code_inspection、Pivot、Markdown定義表、Notebook保存出力、ID件数。", "- 部分対応: semantic、remaining calculation、Notebook残件、location、version diff、cross-file calculation。", "", "## 未対応・評価が必要", "", "- semantic role/status/list、document scope item count、feature category occurrence count、version diff、chart/vision、cross-file calculation。", "", "## 解釈", "", "- priority_scoreはtest未対応数、valid測定可能性、再利用性、評価可能性を実装難度と誤答リスクで割った相対値です。絶対的な成功確率ではありません。"]
    (out / "capability_gap_analysis_v2.md").write_text("\n".join(gap) + "\n", encoding="utf-8")

    top = top3[0]
    report = ["# Recommended Next Phase v2", "", f"## 第1位: {top['capability']}", "", f"- 対象valid: {top['valid_total']}問", f"- 未解決valid: {top['valid_unresolved']}問", f"- 対象test: {top['test_total']}問", f"- 未解決test: {top['test_unresolved']}問", f"- priority_score: {top['priority_score']}", "", "## 上位3候補", ""]
    for rank, candidate in enumerate(top3, 1):
        report.append(f"{rank}. `{candidate['capability']}`: valid {candidate['valid_total']}、test {candidate['test_total']}、未解決test {candidate['test_unresolved']}、難度 {candidate['implementation_difficulty']}、リスク {candidate['error_risk']}、priority {candidate['priority_score']}")
    report += ["", "## 第1位の実装方針", "", "質問文から対象項目・一覧性・除外条件を構造化し、Document IRの見出し・段落・表行・shapeを候補化します。候補が複数ある場合は一意性を確認し、回答は原文と位置情報から決定的に構成します。候補不足、意味の曖昧さ、全件性未確認時はAnswer Gateで抑制します。", "", "## 今回の範囲", "", "今回は分析と推奨のみを実施し、新規Executor、正式パイプライン、Gate条件は変更していません。"]
    (out / "recommended_next_phase_v2.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps({"run_id": args.run_id, "matrix_rows": len(rows), "valid_rows": sum(r["dataset"] == "valid" for r in rows), "test_rows": sum(r["dataset"] == "test" for r in rows), "top3": [r["capability"] for r in top3], "id_count_gold": len(gold), "id_count_quality": id_quality}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
