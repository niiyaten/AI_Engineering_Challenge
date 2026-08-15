from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/output/semantic_list_evidence_contract_gate_fresh_v1/analysis"
TARGETS = {"valid": {"15", "20"}, "test": {"19", "20", "26", "34", "45", "52", "55", "60", "67", "70", "85", "87"}}


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(name: str, values: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(key for value in values for key in value)) or ["empty"]
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(values)


def main() -> None:
    traces = []
    for dataset, run in (("valid", "semantic_list_extraction_relevance_aware_valid_fresh_v1"), ("test", "semantic_list_extraction_relevance_aware_test_full_fresh_v1")):
        work = ROOT / "data/work" / run
        execution = {str(row["question_id"]): row for row in rows(work / "execution/tool_executions.jsonl")}
        answers = {str(row["question_id"]): row for row in rows(ROOT / "data/output" / run / "answer_results.jsonl")}
        gates = {str(row["question_id"]): row for row in rows(ROOT / "data/output" / run / "answer_gate_results.jsonl")}
        for qid in sorted(TARGETS[dataset], key=int):
            x = execution.get(qid, {})
            output = (x.get("tool_outputs") or [{}])[-1]
            verification = output.get("verification") or {}
            gate = gates.get(qid, {})
            answers_row = answers.get(qid, {})
            required = ("selected_candidates_exist", "source_files_verified", "project_relation_verified", "presence", "condition_match", "answer_text_present_in_evidence", "answer_derived_only_from_selected_candidates", "source_locations_present", "no_unsupported_inference", "verbatim_match", "uniqueness")
            missing = [name for name in required if verification.get(name) is not True]
            traces.append({
                "dataset": dataset, "question_id": qid,
                "executor_status": output.get("status", ""), "executor_failure_stage": output.get("failure_stage", ""),
                "executor_verification_status": verification.get("verification_status", ""),
                "executor_evidence_count": len(output.get("evidence", [])),
                "common_verification_status": x.get("semantic_contract", {}).get("verification_status", ""),
                "common_verification_failed_checks": ";".join(x.get("semantic_contract", {}).get("failed_checks", [])),
                "gate_status": gate.get("gate_status", ""), "gate_reason": gate.get("suppression_reason", ""),
                "required_gate_fields_missing_before_bridge": ";".join(missing),
                "list_fields_present": ";".join(name for name in ("required_items_complete", "duplicate_policy_verified", "ordering_verified", "independent_recalculation_match") if verification.get(name) is True),
                "answer_present_after_gate": bool(answers_row.get("answer")),
            })
    write("semantic_list_contract_trace_before.csv", traces)
    mapping = [
        {"gate_requirement": "selected_candidates_exist", "list_evidence_field": "included_candidate_ids", "conversion": "nonempty candidate IDs"},
        {"gate_requirement": "presence", "list_evidence_field": "item_verification_passed", "conversion": "all included items true"},
        {"gate_requirement": "condition_match", "list_evidence_field": "filter_match and filter_spec", "conversion": "all selected items satisfy filter"},
        {"gate_requirement": "answer_text_present_in_evidence", "list_evidence_field": "original_text and answer_value", "conversion": "answer value contained in source text"},
        {"gate_requirement": "source_locations_present", "list_evidence_field": "source_location", "conversion": "all selected item locations nonempty"},
        {"gate_requirement": "verbatim_match", "list_evidence_field": "independent_reconstruction_answer", "conversion": "reconstructed output equals executor output"},
        {"gate_requirement": "uniqueness", "list_evidence_field": "duplicate_handling_verified and conflict check", "conversion": "duplicate policy and conflicts verified"},
        {"gate_requirement": "completeness", "list_evidence_field": "completeness_check_passed", "conversion": "scope scan and relevant-object check pass"},
    ]
    write("semantic_list_evidence_mapping.csv", mapping)
    write("semantic_list_contract_trace_after.csv", [])


if __name__ == "__main__":
    main()
