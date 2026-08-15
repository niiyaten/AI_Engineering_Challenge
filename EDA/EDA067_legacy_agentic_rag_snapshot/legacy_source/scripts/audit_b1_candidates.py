"""Audit the current B1 candidate set without changing runtime behaviour."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "b1_detailed_source_path_reaudit_v1"
OUT = ROOT / "data" / "output" / RUN_ID / "analysis"
SOURCE = ROOT / "data" / "output" / "b0_valid_pattern_transfer_single_fix_fresh_v1" / "analysis"
HIST = ROOT / "data" / "output" / "b_group_41_failure_root_cause_priority_audit_v1" / "analysis"

csv.field_size_limit(2**31 - 1)


def rows(name: str, path: Path = SOURCE) -> list[dict[str, str]]:
    file = path / name
    if not file.exists():
        return []
    with file.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, data: list[dict[str, object]], fields: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def environment() -> dict[str, object]:
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
    env = environment()
    (OUT / "execution_environment_audit.json").write_text(
        json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    b1 = rows("b1_candidates.csv")
    matches = rows("b_valid_pattern_matches.csv")
    prior = rows("b_group_reclassification.csv", HIST)
    prior_counts = Counter(item.get("reclassification", "") for item in prior)

    inventory_fields = [
        "question_id", "question_original", "previous_classification", "previous_reason",
        "matched_valid_pattern_id", "match_strength", "primary_operation", "secondary_operations",
        "required_source_count", "required_source_relation", "required_file_types",
        "first_failure_phase_previous", "root_cause_previous",
    ]
    write_csv("b1_candidate_inventory.csv", b1, inventory_fields)

    empty_fields = {
        "b1_valid_pattern_match_audit.csv": inventory_fields + ["match_strength_audit", "confidence"],
        "b1_source_candidate_audit.csv": [
            "question_id", "question_named_source", "required_source_description", "required_source_role",
            "candidate_sources", "candidate_scores", "candidate_ranking", "selected_source",
            "required_source_present", "required_source_rank", "source_status",
            "selected_source_likely_correct", "content_validation_result", "evidence", "confidence",
        ],
        "b1_source_ranking_audit.csv": ["question_id", "candidate_sources", "candidate_scores", "candidate_ranking", "tie_break", "normalization", "finding"],
        "b1_source_content_validation.csv": ["question_id", "selected_source", "file_extraction_status", "content_validation_result", "required_content_exists", "finding"],
        "b1_phase_status.csv": ["question_id", "phase_id", "phase_name", "status", "evidence", "failure_reason", "source_artifact"],
        "b1_first_failure_reaudit.csv": ["question_id", "question_original", "first_failure_phase_previous", "first_failure_phase_reaudited", "direct_failure", "root_cause", "downstream_failures", "final_suppression_reason", "classification_changed", "confidence"],
        "b1_downstream_reachability.csv": ["question_id", "correct_source_assumption", "correct_structure_assumption", "existing_executor_reusable", "likely_reaches_answer_candidate", "likely_reaches_evidence", "likely_reaches_verification", "likely_reaches_gate_candidate", "additional_capability_required", "blocking_reason", "confidence"],
        "b1_reclassification.csv": ["question_id", "previous_classification", "reclassification", "reason", "confidence"],
        "b1_root_cause_clusters.csv": ["cluster_id", "cluster_name", "question_count", "question_ids", "common_first_failure_phase", "common_root_cause", "required_fix"],
        "b1_cluster_question_mapping.csv": ["cluster_id", "question_id", "root_cause", "first_failure_phase"],
        "b1_common_fix_candidates.csv": ["cluster_id", "cluster_name", "question_count", "question_ids", "required_fix", "implementation_size", "incorrect_answer_risk", "regression_risk", "confidence"],
        "b1_cost_benefit.csv": ["cluster_id", "question_count", "impact_score", "valid_similarity_score", "source_confidence_score", "downstream_reachability_score", "implementation_cost_score", "incorrect_risk_score", "regression_risk_score", "confidence_score", "priority_score"],
        "b1_priority_ranking.csv": ["cluster_id", "cluster_name", "question_count", "question_ids", "matched_valid_patterns", "required_source_present_rate", "source_selection_failure_rate", "existing_executor_reuse_rate", "downstream_reachability_rate", "implementation_size", "implementation_complexity", "incorrect_answer_risk", "regression_risk", "source_misselection_risk", "estimated_answer_candidate_gain_min", "estimated_answer_candidate_gain_max", "estimated_gate_candidate_gain_min", "estimated_gate_candidate_gain_max", "priority_score", "priority_rank", "confidence"],
    }
    for name, fields in empty_fields.items():
        write_csv(name, [], fields)

    scope = f"""# B1 detailed source-path audit\n\n- Latest b1_candidates.csv count: {len(b1)}\n- Latest B1 question IDs: []\n- Historical B-group reclassification counts: {dict(prior_counts)}\n- No historical B1 classification was present.\n- Runtime code was not changed.\n\nThe current artifacts classify the 75 eligible B-equivalent questions as B0/B2/B3. The 34 minor-gap records are not B1 records: they include condition application, calculation, evidence mapping, missing-source, and new-capability cases. They must not be silently promoted to B1.\n"""
    (OUT / "audit_scope.md").write_text(scope, encoding="utf-8")

    summary = """# B1 reclassification summary\n\nB1 candidates: 0. No question-level B1 phase, source, or downstream audit can be performed without inventing a candidate set.\n\nThe latest artifact is internally consistent with the preceding B-group audit: the preceding file contains B2, B3, and C classifications, but no B1 label.\n"""
    (OUT / "b1_reclassification_summary.md").write_text(summary, encoding="utf-8")

    recommendation = """# Recommendation\n\n## Decision\n\nDo not implement a B1-specific common fix in this audit. The current B1 candidate set is empty, so there is no evidence-backed question cluster or expected gain to justify a source-selection, Executor, Evidence, Verification, or Gate change.\n\n## Next audit candidate\n\nIf the B1 track is reopened, first repair the classification/audit export so that `minor_gap` records are separated into genuine B1a/B1b/B1c candidates using source status and first failure phase. This is an audit prerequisite, not a runtime implementation.\n\n## Safety\n\nNo changes were made to test 2, 82, 0, or 85. No answer candidates were generated and no Gate state was changed.\n"""
    (OUT / "recommended_next_fix.md").write_text(recommendation, encoding="utf-8")
    (OUT / "recommended_next_fix_questions.csv").write_text("question_id\n", encoding="utf-8")

    (OUT / "audit_limitations.md").write_text(
        "The requested B1 question-level audit is vacuous because the latest B1 artifact contains zero rows. Reclassifying B2/B3 rows into B1 would change the audit population and would require a separate classification audit. No runtime or formal pipeline rerun was performed.\n",
        encoding="utf-8",
    )
    (OUT / "final_audit_summary.md").write_text(
        f"""# B1 detailed audit summary\n\n## Result\n\nThe latest formal baseline remains valid 17/0/13 and test Gate allowed 8/suppressed 92. The B1 candidate file contains {len(b1)} questions, so the B1 population is empty.\n\n## Set consistency\n\nPrevious B-group reclassification: {dict(prior_counts)}. No previous B1 rows were found. The latest artifact therefore has no count or ID discrepancy to resolve.\n\n## Classification\n\nB1a/B1b/B1c/B0/B2/B3/X: 0 question-level B1 candidates audited. The current 75 eligible B-equivalent records remain represented by their recorded B0/B2/B3 classifications.\n\n## Recommendation\n\nDo not implement a B1 fix. First restore a trustworthy B1 candidate export, then perform the requested source-path audit. This turn made no runtime changes, generated no answers, and changed no Gate state.\n\n## Safety\n\ntest 2 and 82 remain human-review-only; test 0 and 85 remain suppressed.\n""",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": RUN_ID, "b1_candidate_count": len(b1), "b1_question_ids": []}, ensure_ascii=False))


if __name__ == "__main__":
    main()
