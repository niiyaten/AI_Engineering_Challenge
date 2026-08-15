from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip()


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(_norm(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _recalculate(evidence: dict[str, Any], answer: str) -> dict[str, Any]:
    """保存済み入力値と式だけを使い、Executorを呼ばずに検算する。"""
    formula = str(evidence.get("calculation_formula", ""))
    values = evidence.get("input_values", [])
    numeric = [_decimal(value) for value in values]
    numeric = [value for value in numeric if value is not None]
    recomputed: str | None = None
    if formula.startswith("sum(") and numeric:
        result = sum(numeric, Decimal(0))
        recomputed = format(result, "f").rstrip("0").rstrip(".") if result % 1 else str(int(result))
    elif formula.startswith("mean(") and numeric:
        result = sum(numeric, Decimal(0)) / Decimal(len(numeric))
        recomputed = format(result, "f")
    elif formula.startswith("count("):
        recomputed = str(len(values))
    match = recomputed is not None and _norm(recomputed) == _norm(answer)
    return {
        "pipeline_result": answer,
        "independently_recomputed_result": recomputed or "",
        "match": match,
        "input_value_count": len(values),
        "numeric_value_count": len(numeric),
        "formula": formula,
    }


def _question_intent(question: str) -> str:
    if any(term in question for term in ("予測値", "回帰係数", "係数を")):
        return "coefficient_prediction"
    if any(term in question for term in ("合計", "平均", "割合", "算出", "計算")):
        return "calculation"
    return "lookup"


def _operation_matches(question: str, formula: str, spec: dict[str, Any]) -> tuple[bool, str]:
    if _question_intent(question) == "coefficient_prediction":
        ok = spec.get("calculation_subtype") == "coefficient_prediction" and "coefficient" in formula.lower()
        return ok, "係数・特徴量・切片を使う予測式が必要"
    if "いくつ発行" in question:
        ok = formula.startswith("count(") or formula.startswith("nunique(")
        return ok, "発行数はID値のsumではなくcountまたはnuniqueが必要"
    if "バッファ" in question:
        lower = formula.lower()
        ok = ("バッファ" in formula or "buffer" in lower) and ("工数" in formula or "hour" in lower)
        return ok, "バッファ行の工数列を集計する必要がある"
    return bool(formula or spec.get("operations")), "質問に対応する式またはoperation graphが必要"


def _file_selection_unique(question: str, candidates: list[dict[str, Any]], selected: list[str], plan: dict[str, Any]) -> bool:
    selected_names = [Path(path).name for path in selected]
    explicitly_selected = [name for name in selected_names if name.lower() in question.lower()]
    if explicitly_selected:
        return len(selected) == 1
    if plan.get("source_requirements") and any(item.get("multiple_files_required") for item in plan["source_requirements"]):
        return len(selected) > 1
    if len(candidates) >= 2 and candidates[0].get("score") == candidates[1].get("score"):
        return len(selected) > 1
    return bool(selected)


def _required_gate_conditions(intent: str) -> list[str]:
    if intent in {"calculation", "coefficient_prediction"}:
        return [
            "question_type_match",
            "condition_coverage",
            "input_presence",
            "operation_validity",
            "reproducibility",
            "source_range",
            "file_selection_unique",
            "answer_format_valid",
        ]
    return ["input_presence", "source_range", "file_selection_unique"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate許可されたtest回答を正解なしで内部監査する")
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--output-run", required=True)
    parser.add_argument("--post-run")
    parser.add_argument("--questions", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    source_output = root / "data" / "output" / args.source_run
    source_work = root / "data" / "work" / args.source_run
    analysis_dir = root / "data" / "output" / args.output_run / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    with Path(args.questions).open(encoding="utf-8-sig", newline="") as handle:
        questions = {int(row["index"]): row["question"] for row in csv.DictReader(handle)}
    answers = {int(row["question_id"]): row for row in _jsonl(source_output / "answer_results.jsonl")}
    gates = {int(row["question_id"]): row for row in _jsonl(source_output / "answer_gate_results.jsonl")}
    allowed_ids = {qid for qid, gate in gates.items() if gate.get("gate_status") == "allowed"}
    analyses = {int(row["index"]): row for row in _jsonl(source_work / "planning" / "question_analysis.jsonl")}
    plans = {int(row["question_id"]): row for row in _jsonl(source_work / "planning" / "final_source_plans.jsonl")}
    execution_plans = {int(row["index"]): row for row in _jsonl(source_work / "planning" / "execution_plans.jsonl")}
    executions = {int(row["question_id"]): row for row in _jsonl(source_work / "execution" / "tool_executions.jsonl")}
    candidate_rows = _jsonl(source_work / "planning" / "candidate_files.jsonl")
    candidates: dict[int, list[dict[str, Any]]] = {}
    for row in candidate_rows:
        candidates.setdefault(int(row["index"]), []).append(row)
    post_answers: dict[int, dict[str, Any]] = {}
    if args.post_run:
        post_answers = {int(row["question_id"]): row for row in _jsonl(root / "data" / "output" / args.post_run / "answer_results.jsonl")}

    audit_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    recalculation_rows: list[dict[str, Any]] = []
    for question_id in sorted(allowed_ids):
        question = questions[question_id]
        answer = answers[question_id]
        gate = gates[question_id]
        analysis = analyses.get(question_id, {})
        plan = plans.get(question_id, {})
        execution = executions.get(question_id, {})
        tool_output = (execution.get("tool_outputs") or [{}])[-1]
        evidence = (answer.get("evidence_locations") or [{}])[0]
        spec = tool_output.get("spec", {})
        verification = tool_output.get("verification", {})
        intent = _question_intent(question)
        selected_files = answer.get("selected_files", [])
        file_unique = _file_selection_unique(question, candidates.get(question_id, []), selected_files, plan)
        operation_match, operation_reason = _operation_matches(question, str(evidence.get("calculation_formula", "")), spec)
        executor = (answer.get("operations_executed") or [""])[0]
        question_type_match = intent != "coefficient_prediction" or tool_output.get("question_type") == "calculation"
        recalculation = _recalculate(evidence, str(answer.get("answer", "")))
        source_range = bool(evidence.get("cell_ranges"))
        evidence_complete = bool(evidence.get("selected_file_id")) and source_range and bool(evidence.get("input_values")) and bool(evidence.get("calculation_formula"))
        answer_format_valid = not ("小数第" in question and not re.search(r"\.\d+$", str(answer.get("answer", ""))))
        conditions = {
            "question_type_match": question_type_match,
            "condition_coverage": operation_match,
            "input_presence": bool(evidence.get("selected_file_id")),
            "operation_validity": operation_match,
            "reproducibility": recalculation["match"],
            "source_range": source_range,
            "file_selection_unique": file_unique,
            "answer_format_valid": answer_format_valid,
        }
        required = _required_gate_conditions(intent)
        passed = [name for name in required if conditions.get(name) is True]
        failed = [name for name in required if conditions.get(name) is not True]
        if failed:
            safety = "should_be_suppressed"
            safety_reason = "; ".join(failed + [operation_reason])
        elif not file_unique:
            safety = "needs_human_review"
            safety_reason = "ファイル候補が一意ではありません"
        else:
            safety = "safe_to_submit"
            safety_reason = "質問条件・処理・Evidence・独立再計算が整合"
        post = post_answers.get(question_id, {})
        row = {
            "question_id": question_id,
            "question_original": question,
            "question_normalized": analysis.get("question_normalized", ""),
            "primary_question_type": intent,
            "secondary_question_types": _compact(analysis.get("provisional_routes", [])),
            "generated_execution_plan": _compact(execution_plans.get(question_id, {})),
            "selected_executor": executor,
            "executor_version": answer.get("executor_version", ""),
            "generated_calculation_spec": _compact(spec),
            "selected_operation": evidence.get("calculation_formula", ""),
            "operation_graph": _compact(spec.get("operations", answer.get("calculation_trace", []))),
            "candidate_files": _compact(candidates.get(question_id, [])),
            "selected_files": _compact(plan.get("final_selected_file_ids", [])),
            "actual_used_files": _compact(selected_files),
            "file_selection_reason": plan.get("selection_status", ""),
            "selected_sheets": evidence.get("sheet_name", ""),
            "selected_columns": _compact(evidence.get("columns_used", evidence.get("input_columns", []))),
            "selected_rows": evidence.get("matched_row_count", ""),
            "source_ranges": _compact(evidence.get("cell_ranges", [])),
            "filters": _compact(evidence.get("filter_conditions", [])),
            "filter_order": "and",
            "aggregation": evidence.get("calculation_formula", ""),
            "numerator_definition": spec.get("numerator_definition", ""),
            "denominator_definition": spec.get("denominator_definition", ""),
            "coefficient_source": spec.get("coefficient_source", ""),
            "rounding_rule": _compact(spec.get("rounding", {})),
            "unit": spec.get("unit", ""),
            "answer_format": spec.get("output_type", answer.get("answer_type", "")),
            "input_row_counts": _compact(evidence.get("input_row_counts", {"input_values": len(evidence.get("input_values", []))})),
            "output_row_counts": _compact(evidence.get("output_row_counts", {"matched": evidence.get("matched_row_count")})),
            "intermediate_values": _compact(evidence.get("intermediate_values", {})),
            "unrounded_result": evidence.get("raw_result", ""),
            "rounded_result": evidence.get("formatted_result", ""),
            "final_answer": answer.get("answer", ""),
            "evidence_locations": _compact({"file": evidence.get("selected_file"), "sheet": evidence.get("sheet_name"), "ranges": evidence.get("cell_ranges")}),
            "verification_result": _compact(verification),
            "gate_status": gate.get("gate_status", ""),
            "gate_allow_reason": gate.get("suppression_reason", "") or "旧Gateの共通Evidence条件を通過",
            "required_gate_conditions": _compact(required),
            "passed_gate_conditions": _compact(passed),
            "not_applicable_conditions": "[]",
            "failed_but_ignored_conditions": _compact(failed),
            "question_type_match": question_type_match,
            "operation_match": operation_match,
            "file_selection_unique": file_unique,
            "independent_recalculation_match": recalculation["match"],
            "evidence_complete": evidence_complete,
            "answer_format_match": answer_format_valid,
            "safety_classification": safety,
            "safety_reason": safety_reason,
            "warnings": _compact(answer.get("warnings", [])),
            "post_gate_status": post.get("gate_status", ""),
            "post_answer": post.get("answer", ""),
        }
        audit_rows.append(row)
        recalculation_rows.append({"question_id": question_id, **recalculation})
        values = evidence.get("input_values", [])
        evidence_rows.append({
            "question_id": question_id,
            "source": {"file": evidence.get("selected_file"), "file_id": evidence.get("selected_file_id"), "sheet": evidence.get("sheet_name"), "ranges": evidence.get("cell_ranges")},
            "operation": evidence.get("calculation_formula"),
            "input_value_count": len(values),
            "input_values_sha1": hashlib.sha1(_compact(values).encode("utf-8")).hexdigest(),
            "input_values_preview": values[:5],
            "raw_result": evidence.get("raw_result"),
            "formatted_result": evidence.get("formatted_result"),
            "verification": verification,
            "safety_classification": safety,
        })

    fields = list(audit_rows[0]) if audit_rows else ["question_id"]
    with (analysis_dir / "test_gate_allowed_audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit_rows)
    with (analysis_dir / "test_gate_allowed_recalculation.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(recalculation_rows[0]) if recalculation_rows else ["question_id"])
        writer.writeheader()
        writer.writerows(recalculation_rows)
    with (analysis_dir / "test_gate_allowed_evidence.jsonl").open("w", encoding="utf-8") as handle:
        for row in evidence_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = Counter(row["safety_classification"] for row in audit_rows)
    lines = ["# Test Gate許可回答の内部監査", "", f"対象: {len(audit_rows)}件", "", f"- safe_to_submit: {summary['safe_to_submit']}", f"- needs_human_review: {summary['needs_human_review']}", f"- should_be_suppressed: {summary['should_be_suppressed']}"]
    for row in audit_rows:
        recalc = next(item for item in recalculation_rows if item["question_id"] == row["question_id"])
        lines.extend([
            "", f"## Question {row['question_id']}", "", f"**質問文:** {row['question_original']}", "", f"**最終回答:** {row['final_answer']}", f"**安全性判定:** {row['safety_classification']}", f"**判定理由:** {row['safety_reason']}", f"**使用Executor:** {row['selected_executor']} ({row['executor_version']})", f"**使用ファイル・シート:** {row['actual_used_files']} / {row['selected_sheets']}", f"**質問から生成した条件:** {row['filters']}", f"**実際の処理手順:** {row['selected_operation']}", f"**主要な中間値:** raw={row['unrounded_result']} formatted={row['rounded_result']}", f"**根拠位置:** {row['evidence_locations']}", f"**独立再計算:** {recalc['independently_recomputed_result']} (match={recalc['match']})", f"**警告:** {row['warnings']}", f"**修正後Gate:** {row['post_gate_status'] or '未実行'}",
        ])
    (analysis_dir / "test_gate_allowed_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"audit_count": len(audit_rows), "safety": dict(summary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
