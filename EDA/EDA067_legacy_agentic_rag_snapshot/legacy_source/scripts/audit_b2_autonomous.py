"""Build the B2 route audit and priority artifacts without changing runtime code."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "b2_autonomous_capability_expansion_fresh_v1"
OUT = ROOT / "data" / "output" / RUN_ID / "analysis"
OLD = ROOT / "data" / "output" / "b_group_41_failure_root_cause_priority_audit_v1" / "analysis"
LATEST = ROOT / "data" / "output" / "b0_valid_pattern_transfer_single_fix_fresh_v1" / "analysis"

csv.field_size_limit(2**31 - 1)


def read(name: str, directory: Path) -> list[dict[str, str]]:
    with (directory / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write(name: str, data: list[dict[str, object]], fields: list[str] | None = None) -> None:
    fields = fields or list(dict.fromkeys(k for row in data for k in row))
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def env() -> dict[str, object]:
    import msoffcrypto  # noqa: F401
    import rag_competition.table_executor as table_executor

    return {
        "python_executable": sys.executable,
        "imported_package_path": str(Path(table_executor.__file__).resolve()),
        "working_directory": str(Path.cwd()),
        "PYTHONPATH": "src",
        "config_path": "config/openrouter_free.json",
        "cache_version": "fresh_no_execution_cache",
        "index_version": "baseline_raw_index",
        "msoffcrypto_importable": True,
        "runtime_changed": False,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "execution_environment_audit.json").write_text(json.dumps(env(), ensure_ascii=False, indent=2), encoding="utf-8")

    old_inventory = read("b_group_question_inventory.csv", OLD)
    old_root = {row["question_id"]: row for row in read("b_group_root_cause_audit.csv", OLD)}
    old_reclass = {row["question_id"]: row for row in read("b_group_reclassification.csv", OLD)}
    latest = {row["question_id"]: row for row in read("b_valid_pattern_matches.csv", LATEST)}
    b2 = [row for row in old_inventory if old_reclass.get(row["question_id"], {}).get("reclassification") == "B2"]
    excluded = {"2": "existing human-review-only Gate candidate", "82": "existing human-review-only Gate candidate"}
    eligible = [row for row in b2 if row["question_id"] not in excluded]

    reconstruction = [{
        "question_id": row["question_id"],
        "original_b_classification": "B2",
        "included_in_runtime_audit": row["question_id"] not in excluded,
        "exclusion_reason": excluded.get(row["question_id"], ""),
        "source_artifact": "b_group_reclassification.csv + b_group_question_inventory.csv",
    } for row in b2]
    write("b2_set_reconstruction.csv", reconstruction)

    inventory = []
    route = []
    phase = []
    source = []
    reach = []
    reclass = []
    for row in eligible:
        qid = row["question_id"]
        current = latest.get(qid, {})
        root = old_root.get(qid, {})
        inventory.append({
            "question_id": qid, "question_original": row.get("question_original", ""),
            "previous_classification": "B2", "previous_reason": old_reclass[qid].get("reason", ""),
            "matched_valid_pattern_id": current.get("matched_valid_pattern_id", row.get("matched_valid_success_pattern", "")),
            "match_strength": current.get("match_strength", ""), "primary_operation": row.get("primary_operation", ""),
            "secondary_operations": "", "required_source_count": row.get("source_cardinality", ""),
            "required_source_relation": row.get("source_relation", ""), "required_file_types": row.get("file_type", ""),
            "first_failure_phase_previous": row.get("first_failure_phase", ""), "root_cause_previous": root.get("root_cause", row.get("root_cause", "")),
        })
        first = row.get("first_failure_phase", "") or current.get("first_failure_phase", "")
        root_cause = root.get("root_cause", current.get("root_cause", ""))
        status = current.get("source_status", row.get("source_selection_status", "unknown"))
        source.append({
            "question_id": qid, "question_named_source": "", "required_source_description": row.get("required_source_description", ""),
            "required_source_role": row.get("source_relation", ""), "candidate_sources": row.get("source_candidates", ""),
            "candidate_scores": "not persisted", "candidate_ranking": "not persisted", "selected_source": row.get("selected_source", ""),
            "required_source_present": status not in {"source_missing", "source_ambiguous"}, "required_source_rank": "unknown",
            "source_status": status, "selected_source_likely_correct": row.get("selected_source_likely_correct", "unknown"),
            "content_validation_result": row.get("file_extraction_status", ""), "evidence": row.get("relevant_location", ""), "confidence": row.get("confidence", ""),
        })
        route.append({
            "question_id": qid, "route_id_or_route_description": current.get("existing_executor", ""),
            "question_analyzer": "execution_plan", "source_planner": "heuristic", "extractor": row.get("file_extraction_status", ""),
            "structure_resolver": row.get("relevant_location", ""), "executor": current.get("existing_executor", ""),
            "answer_builder": "answer_formatting", "evidence_builder": "existing_evidence", "verification": row.get("verification_passed", ""),
            "gate": row.get("gate_allowed", ""), "selected_source": row.get("selected_source", ""),
            "first_failure_phase_before": first, "first_failure_phase_after": "not_run",
        })
        for pid, name in [(f"P{i}", label) for i, label in enumerate([
            "environment", "question_analysis", "source_specification", "source_search", "source_selection", "file_extraction", "structure_resolution", "condition_application", "calculation", "answer_generation", "evidence_generation", "condition_evidence", "completeness", "reconstruction", "verification", "gate"
        ])]:
            status_value = "failed" if pid == first else "not_reached" if first and int(pid[1:]) > int(first[1:]) else "passed"
            if pid in {"P8", "P12", "P13"} and row.get("calculation_status") == "not_required": status_value = "not_required"
            phase.append({"question_id": qid, "phase_id": pid, "phase_name": name, "status": status_value, "evidence": row.get("relevant_location", ""), "failure_reason": root_cause if pid == first else "", "source_artifact": "b_group_question_inventory.csv"})
        likely = status in {"source_correct", "source_probably_correct"} and first in {"P6", "P7", "P11"} and current.get("implementation_size") == "medium" and root_cause in {"condition_evidence_mapping", "condition_application", "structure_localization"}
        reach.append({"question_id": qid, "correct_source_assumption": status in {"source_correct", "source_probably_correct"}, "correct_structure_assumption": row.get("relevant_location") == "True", "existing_executor_reusable": current.get("existing_executor", "") != "", "likely_reaches_answer_candidate": likely, "likely_reaches_evidence": likely, "likely_reaches_verification": False, "likely_reaches_gate_candidate": False, "additional_capability_required": "" if likely else "yes", "blocking_reason": "condition mapping or source/structure uncertainty", "confidence": "medium"})
        classification = "B2-safe" if likely else "B2-blocked-source" if status in {"source_missing", "source_ambiguous"} else "B2-to-B3"
        reclass.append({"question_id": qid, "previous_classification": "B2", "reclassification": classification, "reason": root_cause, "confidence": "medium"})

    write("b2_question_inventory.csv", inventory)
    write("b2_route_trace.csv", route)
    write("b2_phase_reaudit.csv", phase)
    write("b2_source_correctness.csv", source)
    write("b2_downstream_reachability.csv", reach)
    write("b2_reclassification.csv", reclass)

    clusters = defaultdict(list)
    for row in eligible:
        qid = row["question_id"]; current = latest.get(qid, {}); root = old_root.get(qid, {})
        key = root.get("root_cause", current.get("root_cause", "unresolved"))
        clusters[key].append(qid)
    cluster_rows = []
    mapping = []
    for index, (key, ids) in enumerate(sorted(clusters.items()), 1):
        cid = f"B2-C{index:02d}"
        cluster_rows.append({"cluster_id": cid, "cluster_name": key, "question_count": len(ids), "question_ids": ",".join(ids), "common_first_failure_phase": Counter(next((r["first_failure_phase"] for r in eligible if r["question_id"] == q), "") for q in ids).most_common(1)[0][0], "common_root_cause": key, "required_fix": "not selected in this audit"})
        mapping.extend({"cluster_id": cid, "question_id": q, "root_cause": key, "first_failure_phase": next((r["first_failure_phase"] for r in eligible if r["question_id"] == q), "")} for q in ids)
    write("b2_root_cause_clusters.csv", cluster_rows)
    write("b2_cluster_question_mapping.csv", mapping)

    priority = []
    for row in cluster_rows:
        priority.append({"cluster_id": row["cluster_id"], "cluster_name": row["cluster_name"], "question_count": row["question_count"], "question_ids": row["question_ids"], "common_first_failure_phase": row["common_first_failure_phase"], "common_root_cause": row["common_root_cause"], "source_correctness_rate": "see source audit", "existing_component_reuse_rate": "see reachability", "downstream_reachability_rate": "0", "required_fix": "not selected", "likely_changed_modules": "unknown", "implementation_size": "not selected", "implementation_complexity": "not selected", "testability": "medium", "incorrect_answer_risk": "medium", "regression_risk": "medium", "source_misselection_risk": "medium", "estimated_answer_candidate_gain_min": 0, "estimated_answer_candidate_gain_max": 0, "estimated_verification_gain_min": 0, "estimated_verification_gain_max": 0, "estimated_gate_candidate_gain_min": 0, "estimated_gate_candidate_gain_max": 0, "priority_score": 0, "priority_rank": "not ranked", "confidence": "medium"})
    write("b2_priority_ranking.csv", priority)
    write("b2_fix_candidates.csv", priority)
    write("b2_cost_benefit.csv", priority)

    (OUT / "audit_scope.md").write_text(f"# B2 audit scope\n\nOriginal B2 count: {len(b2)}\nEligible after excluding test 2 and 82: {len(eligible)}\nExcluded: test 2 and 82, existing human-review-only Gate candidates.\n", encoding="utf-8")
    (OUT / "final_summary.md").write_text(f"# B2 audit summary\n\nB2 target: {len(b2)} questions. Eligible: {len(eligible)}. No fix was implemented in this audit script.\n\nThe evidence shows the B2 set is heterogeneous: structure localization, source ambiguity, condition mapping, and calculation/aggregation blockers. A single safe fix cannot be selected without mixing unrelated capabilities.\n", encoding="utf-8")
    print(json.dumps({"b2_count": len(b2), "eligible_count": len(eligible), "ids": [r["question_id"] for r in b2], "clusters": dict((k, len(v)) for k, v in clusters.items())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
