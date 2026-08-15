"""B相当質問を再構成し、既存成功パターンに近い小規模修正候補を監査する。"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "output" / "valid_success_pattern_test_transfer_source_recovery_test_full_fresh_v1"
BASELINE_WORK = ROOT / "data" / "work" / "valid_success_pattern_test_transfer_source_recovery_test_full_fresh_v1"
TRANSFER = ROOT / "data" / "output" / "valid_success_pattern_test_transfer_source_recovery_fresh_v1" / "analysis"
B_AUDIT = ROOT / "data" / "output" / "b_group_41_failure_root_cause_priority_audit_v1" / "analysis"
C_AUDIT = ROOT / "data" / "output" / "c_group_rescue_vision_capability_audit_v1" / "analysis"
RUN_ID = "b0_valid_pattern_transfer_single_fix_fresh_v1"
OUT = ROOT / "data" / "output" / RUN_ID / "analysis"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(name: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(key for row in rows for key in row))
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalized(value: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFKC", value)).replace(" ", "").lower()


def named_source(question: str) -> str:
    matches = re.findall(r"[^\s、。]+?\.(?:xlsx|csv|tsv|docx|pptx|pdf|ipynb|py|md|json)", question, re.IGNORECASE)
    return matches[0] if matches else ""


def environment_audit() -> dict[str, Any]:
    import rag_competition.table_executor as table_executor

    try:
        import msoffcrypto  # noqa: F401

        msoffcrypto_importable = True
    except ImportError:
        msoffcrypto_importable = False
    return {
        "python_executable": sys.executable,
        "imported_package_path": str(Path(table_executor.__file__).resolve()),
        "working_directory": str(Path.cwd()),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "config_path": "config/openrouter_free.json",
        "cache_version": "fresh_no_execution_cache",
        "index_version": "baseline_raw_index",
        "msoffcrypto_importable": msoffcrypto_importable,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "execution_environment_audit.json").write_text(
        json.dumps(environment_audit(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    b_rows = read_csv(B_AUDIT / "b_group_reclassification.csv")
    c_rows = read_csv(C_AUDIT / "c_group_reclassification.csv")
    b_remaining = {int(row["question_id"]) for row in b_rows if row.get("reclassification") in {"B2", "B3"}}
    c_b2 = {int(row["question_id"]) for row in c_rows if row.get("reclassification") == "C-B2"}
    c_b3 = {int(row["question_id"]) for row in c_rows if row.get("reclassification") == "C-B3"}
    all_ids = b_remaining | c_b2 | c_b3
    overlap = (b_remaining & c_b2) | (b_remaining & c_b3) | (c_b2 & c_b3)
    excluded = {0, 85}
    eligible = sorted(all_ids - excluded)
    set_rows = [
        {"set_name": "original_b_remaining", "count": len(b_remaining), "question_ids": ",".join(map(str, sorted(b_remaining)))},
        {"set_name": "c_b2", "count": len(c_b2), "question_ids": ",".join(map(str, sorted(c_b2)))},
        {"set_name": "c_b3", "count": len(c_b3), "question_ids": ",".join(map(str, sorted(c_b3)))},
        {"set_name": "overlap", "count": len(overlap), "question_ids": ",".join(map(str, sorted(overlap)))},
        {"set_name": "final_unique_before_safety_exclusion", "count": len(all_ids), "question_ids": ",".join(map(str, sorted(all_ids)))},
        {"set_name": "final_execution_eligible", "count": len(eligible), "question_ids": ",".join(map(str, eligible))},
    ]
    write_csv("b_equivalent_set_reconstruction.csv", set_rows)

    valid_inventory = read_csv(TRANSFER / "valid_success_question_inventory.csv")
    valid_patterns = read_csv(TRANSFER / "valid_success_pattern_catalog.csv")
    write_csv("valid_success_pattern_inventory.csv", valid_inventory)
    write_csv("valid_success_execution_contracts.csv", valid_inventory)

    questions = {
        int(row["test_question_id"]): {**row, "question_id": row["test_question_id"]}
        for row in read_csv(TRANSFER / "test_success_pattern_matches.csv")
    }
    answers = {row["question_id"]: row for row in read_jsonl(BASELINE / "answer_results.jsonl")}
    gates = {row["question_id"]: row for row in read_jsonl(BASELINE / "answer_gate_results.jsonl")}
    plans = {row["question_id"]: row for row in read_jsonl(BASELINE_WORK / "planning" / "final_source_plans.jsonl")}
    b_first = {int(row["question_id"]): row for row in read_csv(B_AUDIT / "b_group_first_failure.csv")}
    b_root = {int(row["question_id"]): row for row in read_csv(B_AUDIT / "b_group_root_cause_audit.csv")}

    match_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    b0_rows: list[dict[str, Any]] = []
    b1_rows: list[dict[str, Any]] = []
    b2_rows: list[dict[str, Any]] = []
    b3_rows: list[dict[str, Any]] = []
    x_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []

    for qid in eligible:
        match = questions.get(qid, {})
        answer = answers.get(qid, {})
        plan = plans.get(qid, {})
        question = match.get("question_original", "")
        selected = " | ".join(answer.get("selected_files", []))
        named = named_source(question)
        selected_name = Path(answer.get("selected_files", [""])[0]).name if answer.get("selected_files") else ""
        source_status = "source_ambiguous"
        named_basename = named.rsplit("の", 1)[-1] if named else ""
        if named and normalized(named_basename) == normalized(selected_name):
            source_status = "source_correct"
        elif selected:
            source_status = "source_probably_correct"
        else:
            source_status = "source_missing"
        failure = b_first.get(qid, {})
        root = b_root.get(qid, {})
        first_phase = failure.get("first_failure_phase", "P6") if failure else "P6"
        root_cause = root.get("root_cause_category", failure.get("root_cause", "requires_reaudit")) if failure else "requires_reaudit"
        pattern = match.get("matched_success_pattern_id", "")
        is_styled_row = all(token in question for token in ("ハイライト", "行"))
        is_b0 = (
            pattern == "formatted_text_span"
            and source_status == "source_correct"
            and first_phase in {"P6", "P7", "P8", "P9", "P10", "P11", "P12", "P13", "P14"}
            and is_styled_row
            and answer.get("failure_stage") == "format_failure"
        )
        classification = "B0" if is_b0 else "B1" if source_status == "source_in_candidates_not_selected" else "B2" if qid in c_b2 or qid in b_remaining else "B3" if qid in c_b3 else "X"
        common = {
            "question_id": qid,
            "question_original": question,
            "matched_valid_pattern_id": pattern,
            "match_strength": match.get("match_type", ""),
            "selected_source": selected,
            "source_status": source_status,
            "existing_executor": " | ".join(answer.get("operations_executed", [])),
            "required_content_location": json.dumps(answer.get("evidence_locations", []), ensure_ascii=False),
            "first_failure_phase": first_phase,
            "root_cause": root_cause,
            "required_fix": "styled_row_return_column_binding" if is_b0 else "reclassification_required",
            "common_fix_cluster": "F1R_styled_row_return_column" if is_b0 else "other",
            "implementation_size": "small" if is_b0 else "medium",
            "incorrect_answer_risk": "low" if is_b0 else "medium",
            "regression_risk": "low" if is_b0 else "medium",
            "expected_candidate_gain": 1 if is_b0 else 0,
            "confidence": "high" if is_b0 else "medium",
        }
        match_rows.append({**common, "classification": classification})
        source_rows.append({
            "question_id": qid, "question_original": question, "question_named_source": named,
            "required_source_description": plan.get("source_requirements", []),
            "candidate_sources": ",".join(plan.get("final_selected_file_ids", [])), "selected_source": selected,
            "required_source_present": bool(named), "required_source_rank": 1 if source_status == "source_correct" else "unknown",
            "selected_source_status": source_status, "selected_source_likely_correct": source_status in {"source_correct", "source_probably_correct"},
            "evidence": "baseline answer selected_files and final source plan", "confidence": common["confidence"],
        })
        failure_rows.append({
            "question_id": qid, "question_original": question, "first_failure_phase": first_phase,
            "root_cause": root_cause, "final_suppression_reason": gates.get(qid, {}).get("suppression_reason", ""),
            "source_status": source_status,
        })
        baseline_rows.append({
            "question_id": qid, "question_original": question, "matched_valid_pattern": pattern,
            "selected_source": selected, "source_status": source_status, "first_failure_phase": first_phase,
            "root_cause": root_cause, "answer_candidate_before": answer.get("answer", ""),
            "evidence_before": json.dumps(answer.get("evidence_locations", []), ensure_ascii=False),
            "verification_before": gates.get(qid, {}).get("evidence_verified", False),
            "gate_before": gates.get(qid, {}).get("gate_status", ""),
            "suppression_reason_before": gates.get(qid, {}).get("suppression_reason", ""),
        })
        {"B0": b0_rows, "B1": b1_rows, "B2": b2_rows, "B3": b3_rows, "X": x_rows}[classification].append(common)

    write_csv("b_valid_pattern_matches.csv", match_rows)
    write_csv("b_source_correctness_audit.csv", source_rows)
    write_csv("b_first_failure_reaudit.csv", failure_rows)
    for name, rows in (("b0_candidates.csv", b0_rows), ("b1_candidates.csv", b1_rows), ("b2_candidates.csv", b2_rows), ("b3_candidates.csv", b3_rows), ("excluded_candidates.csv", x_rows)):
        write_csv(name, rows)
    write_csv("target_baseline_before_fix.csv", [row for row in baseline_rows if row["question_id"] in {item["question_id"] for item in b0_rows}])

    f1_ids = {2, 7, 11, 16, 17, 65, 71, 80, 82, 84}
    f1_rows = [row for row in source_rows if row["question_id"] in f1_ids]
    write_csv("previous_f1_target_reaudit.csv", f1_rows)
    effective = [row["question_id"] for row in b0_rows if row["question_id"] in f1_ids]
    (OUT / "previous_f1_effective_scope.md").write_text(
        f"# F1再監査\n\n旧F1対象は{len(f1_ids)}問。資料選択と既存形式抽出の両方を満たし、同じ小修正で扱える純粋対象は {len(effective)}問: {effective}。\n",
        encoding="utf-8",
    )

    cluster = {
        "cluster_id": "F1R_styled_row_return_column",
        "cluster_name": "書式一致行から一意な要求列を返す",
        "question_count": len(b0_rows),
        "question_ids": ",".join(str(row["question_id"]) for row in b0_rows),
        "b0_count": len(b0_rows), "b1_count": 0, "b2_count": 0, "b3_count": 0,
        "matched_valid_patterns": "formatted_text_span", "common_root_cause": "format_color_normalization_and_row_return_binding",
        "required_fix": "style hue normalization plus deterministic highlighted-row return-column binding",
        "source_correctness_rate": 1.0 if b0_rows else 0.0, "existing_executor_reuse_rate": 1.0 if b0_rows else 0.0,
        "implementation_size": "small", "implementation_complexity": "low", "incorrect_answer_risk": "low", "regression_risk": "low",
        "verification_strength": "high", "estimated_candidate_gain_min": 0, "estimated_candidate_gain_max": len(b0_rows),
        "estimated_gate_candidate_gain_min": 0, "estimated_gate_candidate_gain_max": len(b0_rows),
        "priority_score": 4.0 if b0_rows else 0.0, "priority_rank": 1,
    }
    write_csv("common_fix_clusters.csv", [cluster])
    write_csv("common_fix_cost_benefit.csv", [cluster])
    write_csv("common_fix_priority_ranking.csv", [cluster])
    write_csv("selected_fix_target_questions.csv", b0_rows)
    (OUT / "selected_fix_specification.md").write_text(
        "# 選定した共通修正\n\n"
        "色指定のExcel行質問で、セルのRGBを色相で正規化し、書式一致セルの行から質問文に完全一致する一意な列名の値を返す。"
        "列名、位置、色一致セルをEvidenceに残し、列が一意に解決できない場合は抑制する。"
        "質問ID、案件名、ファイル名、行番号、回答値による分岐は行わない。Gate条件は変更しない。\n",
        encoding="utf-8",
    )
    (OUT / "final_summary.md").write_text(
        f"# B0 Valid Pattern Transfer Audit\n\n"
        f"- B相当の和集合: {len(all_ids)}問。test 85を安全除外した実行候補: {len(eligible)}問。\n"
        f"- 厳格B0: {len(b0_rows)}問。選定修正は既存表書式抽出の行・列結線のみ。\n"
        "- valid正解値や人間監査結果は、資料選択・回答生成・Gateへ使用していない。\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": RUN_ID, "b_equivalent": len(all_ids), "eligible": len(eligible), "b0": [row["question_id"] for row in b0_rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
