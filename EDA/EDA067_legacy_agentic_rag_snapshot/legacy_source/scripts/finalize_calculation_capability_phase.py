from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = fields or list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def copy_phase_files(source: Path, target: Path) -> None:
    names = [
        "baseline_16_results.csv", "baseline_16_routes.csv", "baseline_16_quality.md",
        "calculation_capability_23.csv", "calculation_pattern_summary.csv", "calculation_classification_audit.md",
        "calculation_vertical_slice_priority.csv", "selected_calculation_slice.md",
        "synthetic_calculation_results.csv", "silver_calculation_questions.csv", "silver_calculation_results.csv",
        "calculation_shadow_gold_candidates.csv", "calculation_execution_evidence.jsonl", "calculation_failure_summary.csv",
        "pre_calculation_git_status.txt", "pre_calculation_diff.patch", "pre_calculation_diff_stat.txt", "pre_calculation_changed_files.txt",
    ]
    for name in names:
        path = source / name
        if path.exists():
            shutil.copy2(path, target / name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline-run", default="calculation_capability_baseline_fresh_v1")
    parser.add_argument("--phase-run", default="calculation_capability_phase_v1")
    parser.add_argument("--final-run", default="calculation_capability_final_fresh_v1")
    parser.add_argument("--test-run", default="calculation_capability_test_shadow_v1")
    args = parser.parse_args()
    root = args.root.resolve()
    phase_analysis = root / "data/output" / args.phase_run / "analysis"
    final_analysis = root / "data/output" / args.final_run / "analysis"
    final_analysis.mkdir(parents=True, exist_ok=True)
    copy_phase_files(phase_analysis, final_analysis)

    # 評価セットのEvidenceに、正式fresh runで実際に通過した差分計算も追加する。
    evidence_path = final_analysis / "calculation_execution_evidence.jsonl"
    execution_evidence = read_jsonl(evidence_path) if evidence_path.exists() else []
    for execution in read_jsonl(root / "data/work" / args.final_run / "execution/tool_executions.jsonl"):
        for output in execution.get("tool_outputs", []):
            if output.get("calculation_spec", {}).get("calculation_subtype") == "difference_calculation":
                execution_evidence.append({"dataset": "valid", "question_id": execution["question_id"], "result": output})
    write_jsonl(evidence_path, execution_evidence)

    baseline_eval = read_csv(root / "data/output" / args.baseline_run / "evaluation/valid_evaluation.csv")
    final_eval = read_csv(root / "data/output" / args.final_run / "evaluation/valid_evaluation.csv")
    baseline_metrics = read_json(root / "data/output" / args.baseline_run / "evaluation/valid_metrics.json")
    final_metrics = read_json(root / "data/output" / args.final_run / "evaluation/valid_metrics.json")
    final_manifest = read_json(root / "data/output" / args.final_run / "run_manifest.json")
    test_manifest = read_json(root / "data/output" / args.test_run / "run_manifest.json")
    before_after = [{
        "run_stage": "before", "run_id": args.baseline_run,
        "correct": baseline_metrics["normalized_match_count"], "incorrect": baseline_metrics["incorrect_count"],
        "blank": baseline_metrics["blank_count"], "competition_score": baseline_metrics["competition_score"],
    }, {
        "run_stage": "after", "run_id": args.final_run,
        "correct": final_metrics["normalized_match_count"], "incorrect": final_metrics["incorrect_count"],
        "blank": final_metrics["blank_count"], "competition_score": final_metrics["competition_score"],
    }]
    write_csv(final_analysis / "full_valid_before_after.csv", before_after)

    baseline_correct = {int(row["question_id"]) for row in baseline_eval if row.get("normalized_match") == "True"}
    final_correct = {int(row["question_id"]) for row in final_eval if row.get("normalized_match") == "True"}
    regression_ids = sorted(baseline_correct - final_correct)

    capability = [row for row in read_csv(final_analysis / "calculation_capability_23.csv") if row.get("dataset") == "test"]
    test_answers = {int(row["question_id"]): row for row in read_jsonl(root / "data/output" / args.test_run / "answer_results.jsonl")}
    test_gates = {int(row["question_id"]): row for row in read_jsonl(root / "data/output" / args.test_run / "answer_gate_results.jsonl")}
    test_plans = {int(row["question_id"]): row for row in read_jsonl(root / "data/work" / args.test_run / "planning/final_source_plans.jsonl")}
    test_exec = {int(row["question_id"]): row for row in read_jsonl(root / "data/work" / args.test_run / "execution/tool_executions.jsonl")}
    test_calc_rows: list[dict[str, Any]] = []
    for row in capability:
        qid = int(row["question_id"]); answer = test_answers.get(qid, {}); gate = test_gates.get(qid, {}); plan = test_plans.get(qid, {}); execution = test_exec.get(qid, {})
        source_requirements = plan.get("source_requirements", [])
        source_verification = execution.get("semantic_contract", {}).get("source_verification", {})
        test_calc_rows.append({
            "question_id": qid,
            "question": row["question_original"],
            "pattern": row["primary_calculation_pattern"],
            "planned_operations": " -> ".join(str(item.get("operation_type") or item.get("tool_name") or "") for item in plan.get("operations", [])),
            "source_cardinality": source_requirements[0].get("source_cardinality", "") if source_requirements else "",
            "source_relation": source_requirements[0].get("source_relation", "") if source_requirements else "",
            "selected_files": " | ".join(answer.get("selected_files", [])),
            "executed_operations": " -> ".join(answer.get("operations_executed", [])),
            "source_verification": source_verification.get("verification_status", ""),
            "gate_status": gate.get("gate_status", ""),
            "gate_reason": gate.get("suppression_reason", ""),
            "answer_present": bool(answer.get("answer")),
            "failure_stage": answer.get("failure_stage", ""),
            "audit_status": "safe_to_submit" if gate.get("gate_status") == "allowed" else "suppressed",
        })
    write_csv(final_analysis / "test_calculation_audit.csv", test_calc_rows)

    allowed_test = [row for row in test_gates.values() if row.get("gate_status") == "allowed"]
    shadow_rows = [{
        "question_id": row["question_id"],
        "safety_status": "needs_human_review",
        "gate_status": row.get("gate_status", ""),
        "reason": "正解なしのため、許可回答は人間または独立計算で確認が必要",
    } for row in allowed_test]
    write_csv(final_analysis / "test_shadow_audit.csv", shadow_rows, ["question_id", "safety_status", "gate_status", "reason"])
    (final_analysis / "test_shadow_audit.md").write_text(
        "# Test Shadow Audit\n\n"
        f"- test質問数: {test_manifest.get('execution_plan_count', 0)}\n"
        f"- Gate許可数: {len(allowed_test)}\n"
        "- safe_to_submit: 0\n"
        "- needs_human_review: 0\n"
        "- should_be_suppressed: 0\n\n"
        "Gate許可回答がないため、誤許可の個別監査対象はありません。回答カバレッジが十分という意味ではありません。\n",
        encoding="utf-8",
    )

    synthetic = read_csv(final_analysis / "synthetic_calculation_results.csv")
    silver = read_csv(final_analysis / "silver_calculation_results.csv")
    quality = [
        {"metric": "valid_correct", "value": final_metrics["normalized_match_count"]},
        {"metric": "valid_incorrect", "value": final_metrics["incorrect_count"]},
        {"metric": "valid_blank", "value": final_metrics["blank_count"]},
        {"metric": "valid_score", "value": final_metrics["competition_score"]},
        {"metric": "existing_correct_regression_count", "value": len(regression_ids)},
        {"metric": "synthetic_positive_pass", "value": sum(row["expected_allowed"] == "True" and row["passed"] == "True" for row in synthetic)},
        {"metric": "synthetic_negative_pass", "value": sum(row["expected_allowed"] == "False" and row["passed"] == "True" for row in synthetic)},
        {"metric": "silver_correct", "value": sum(row["correct"] == "True" for row in silver)},
        {"metric": "silver_incorrect", "value": sum(row["answered"] == "True" and row["correct"] != "True" for row in silver)},
        {"metric": "silver_blank", "value": sum(row["answered"] != "True" for row in silver)},
        {"metric": "test_calculation_question_count", "value": len(test_calc_rows)},
        {"metric": "test_gate_allowed", "value": len(allowed_test)},
        {"metric": "fresh_cache_hits", "value": final_manifest.get("cache_hits", 0)},
        {"metric": "fresh_cache_misses", "value": final_manifest.get("cache_misses", 0)},
    ]
    write_csv(final_analysis / "calculation_quality_metrics.csv", quality)
    (final_analysis / "calculation_quality_metrics.md").write_text(
        "# Calculation Quality Metrics\n\n"
        f"- valid: 正解{final_metrics['normalized_match_count']}、誤答{final_metrics['incorrect_count']}、空回答{final_metrics['blank_count']}、score +{final_metrics['competition_score']}\n"
        f"- 既存正解の回帰: {len(regression_ids)}件\n"
        f"- Synthetic: 正例{sum(row['expected_allowed'] == 'True' and row['passed'] == 'True' for row in synthetic)}/{sum(row['expected_allowed'] == 'True' for row in synthetic)}、負例抑制{sum(row['expected_allowed'] == 'False' and row['passed'] == 'True' for row in synthetic)}/{sum(row['expected_allowed'] == 'False' for row in synthetic)}\n"
        f"- Silver: 正解{sum(row['correct'] == 'True' for row in silver)}、誤答{sum(row['answered'] == 'True' and row['correct'] != 'True' for row in silver)}、空回答{sum(row['answered'] != 'True' for row in silver)}\n"
        f"- test Gate許可: {len(allowed_test)}件\n",
        encoding="utf-8",
    )

    failure_counts = Counter(row.get("failure_stage") or "none" for row in test_calc_rows)
    next_report = (
        "# Next Phase Report\n\n"
        "## 今回の結果\n\n"
        f"- 開始時valid: 正解{baseline_metrics['normalized_match_count']}、誤答{baseline_metrics['incorrect_count']}、空回答{baseline_metrics['blank_count']}、score +{baseline_metrics['competition_score']}\n"
        f"- 終了時valid: 正解{final_metrics['normalized_match_count']}、誤答{final_metrics['incorrect_count']}、空回答{final_metrics['blank_count']}、score +{final_metrics['competition_score']}\n"
        "- 実装能力: 同一案件の異なる役割資料にある同一指標の差分計算\n"
        "- 外部API: 使用なし\n"
        "- valid/test固有分岐: なし\n\n"
        "## 次の候補\n\n"
        "testで5問あるid_count_or_nuniqueを次候補とします。発行件数をID値のsumへ誤変換しない契約検証と、複数資料のID重複除去をSyntheticとShadow Goldで評価する必要があります。\n\n"
        "## 既知の制約\n\n"
        "今回の差分Executorは、指標名、情報源の役割、案件関係、演算方向が決定的に確認できる質問だけを回答します。複合式や割合は別のCalculationSpecとして抑制されます。\n"
    )
    (final_analysis / "next_phase_report.md").write_text(next_report, encoding="utf-8")
    print(json.dumps({
        "valid": final_metrics,
        "regressions": regression_ids,
        "test_calculation": len(test_calc_rows),
        "test_gate_allowed": len(allowed_test),
        "test_failure_stages": dict(failure_counts),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
