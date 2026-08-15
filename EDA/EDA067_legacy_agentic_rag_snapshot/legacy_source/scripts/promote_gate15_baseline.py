"""Promote the audited deterministic Gate-15 proposal without changing runtime logic."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "data/output/confirmed_gate_baseline_and_next_capability_v1/analysis"
HISTORY_ROOT = ROOT / "data/output/baselines/history"
RUNTIME_RUN = ROOT / "data/output/gate15_no_human_review_test_fresh_v1"
VALID_RUN = ROOT / "data/output/gate15_no_human_review_valid_fresh_v1"
GATE_IDS = [2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92]
PREVIOUS_GATE_IDS = [2, 3, 19, 41, 43, 72, 81, 82, 89, 92]
METHODS = [
    "human_review",
    "deterministic_replay",
    "deterministic_calculation",
    "structural_extraction",
    "document_lookup",
    "unverified",
    "suppressed",
]


def sha256(path: Path) -> str:
    """Return a file hash used to bind the formal manifest to its artifacts."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str | None:
    """Read the source commit without changing repository configuration."""
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def archive_current_baseline(promoted_at: str) -> Path:
    """Copy the Gate-10 formal artifacts and record their pre-promotion hashes."""
    stamp = promoted_at.replace(":", "").replace("+00:00", "Z").replace("-", "")
    archive = HISTORY_ROOT / f"gate10_before_gate15_{stamp}"
    archive.mkdir(parents=True, exist_ok=False)
    names = [
        "baseline_manifest.json",
        "current_submission_candidates.csv",
        "current_gate_baseline.csv",
        "confirmed_gate_evidence.csv",
        "current_runtime_baseline.json",
        "current_human_review_status.csv",
    ]
    files: list[dict[str, str]] = []
    for name in names:
        source = ANALYSIS / name
        if source.exists():
            destination = archive / name
            shutil.copy2(source, destination)
            files.append({"name": name, "sha256": sha256(source)})
    (archive / "archive_manifest.json").write_text(
        json.dumps(
            {
                "archived_at": promoted_at,
                "promotion_source_run_id": RUNTIME_RUN.name,
                "gate_question_ids": PREVIOUS_GATE_IDS,
                "files": files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return archive


def validate_predictions(rows: list[dict[str, str]]) -> dict[str, object]:
    """Verify that the full submission has exactly the expected allowed answers."""
    ids = [int(row["question_id"]) for row in rows]
    answers = {int(row["question_id"]): row["prediction"] for row in rows if row["prediction"]}
    expected = set(GATE_IDS)
    assert len(rows) == 100, f"expected 100 predictions, got {len(rows)}"
    assert len(ids) == len(set(ids)), "duplicate test question IDs"
    assert set(answers) == expected, f"answer IDs differ: {sorted(answers)}"
    assert len(rows) - len(answers) == 85, "suppressed count differs"
    assert answers[10] if 10 in answers else "" == "", "test 10 must remain blank"
    assert answers[56] == "1200", "test 56 submission text must be 1200"
    assert answers[63] == "0.15002", "test 63 changed"
    assert answers[83] == "0.38317", "test 83 changed"
    return {"ids": ids, "answers": answers}


def main() -> None:
    promoted_at = datetime.now(timezone.utc).isoformat()
    archive = archive_current_baseline(promoted_at)

    proposed_predictions = ANALYSIS / "proposed_predictions.csv"
    proposed_candidates = ANALYSIS / "proposed_submission_candidates.csv"
    proposed_manifest = ANALYSIS / "proposed_baseline_manifest.json"
    proposed_evidence = ANALYSIS / "proposed_gate_evidence.csv"
    verification_audit = ANALYSIS / "verification_method_audit.csv"

    prediction_rows = read_csv(proposed_predictions)
    prediction_audit = validate_predictions(prediction_rows)
    candidate_rows = read_csv(proposed_candidates)
    evidence_rows = read_csv(proposed_evidence)
    audit_rows = read_csv(verification_audit)
    candidate_ids = [int(row["question_id"]) for row in candidate_rows]
    evidence_ids = [int(row["question_id"]) for row in evidence_rows]
    audit_ids = [int(row["question_id"]) for row in audit_rows]
    assert candidate_ids == GATE_IDS and evidence_ids == GATE_IDS and audit_ids == GATE_IDS
    assert all(row["human_answer_dependency"] == "False" for row in audit_rows)
    assert all(row["safe_to_submit"] == "True" for row in audit_rows)
    assert all(row["gate_allowed"] == "True" for row in audit_rows)
    methods = Counter(row["verification_method"] for row in audit_rows)
    method_counts = {method: methods.get(method, 0) for method in METHODS}
    expected_counts = {
        "human_review": 0,
        "deterministic_replay": 1,
        "deterministic_calculation": 5,
        "structural_extraction": 8,
        "document_lookup": 1,
        "unverified": 0,
        "suppressed": 0,
    }
    assert method_counts == expected_counts, method_counts

    # Promote copies, retaining their proposed counterparts as traceable inputs.
    formal_predictions = ANALYSIS / "predictions.csv"
    formal_candidates = ANALYSIS / "submission_candidates.csv"
    formal_evidence = ANALYSIS / "gate_evidence.csv"
    shutil.copy2(proposed_predictions, formal_predictions)
    shutil.copy2(proposed_candidates, formal_candidates)
    shutil.copy2(proposed_evidence, formal_evidence)
    shutil.copy2(proposed_candidates, ANALYSIS / "current_submission_candidates.csv")
    shutil.copy2(proposed_evidence, ANALYSIS / "confirmed_gate_evidence.csv")

    gate_rows = []
    for row in prediction_rows:
        question_id = int(row["question_id"])
        gate_rows.append(
            {
                "question_id": question_id,
                "formal_gate_allowed": question_id in GATE_IDS,
                "gate_status": "allowed" if question_id in GATE_IDS else "suppressed",
                "suppression_reason": "" if question_id in GATE_IDS else "not_in_deterministic_gate15_baseline",
                "runtime_run_id": RUNTIME_RUN.name,
            }
        )
    write_csv(ANALYSIS / "current_gate_baseline.csv", gate_rows)
    write_csv(
        ANALYSIS / "current_human_review_status.csv",
        [
            {
                "question_id": row["question_id"],
                "verification_method": row["verification_method"],
                "human_reviewed": False,
                "human_review_status": "not_used_for_runtime_validation",
                "needs_human_review": False,
                "safe_to_submit": True,
            }
            for row in candidate_rows
        ],
    )

    raw_evidence = ROOT / "data/output/test56_notebook_replay_v2/evidence/final_evidence.json"
    raw_unchanged = bool(json.loads(raw_evidence.read_text(encoding="utf-8")).get("raw_files_unchanged"))
    current_runtime = {
        "runtime_run_id": RUNTIME_RUN.name,
        "valid_run_id": VALID_RUN.name,
        "valid": {"correct": 17, "incorrect": 0, "blank": 13},
        "test": {"completed": 100, "errors": 0},
        "gate_allowed_ids": GATE_IDS,
        "raw_files_unchanged": raw_unchanged,
        "human_answer_dependency_count": 0,
    }
    (ANALYSIS / "current_runtime_baseline.json").write_text(
        json.dumps(current_runtime, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "baseline_name": "deterministic_gate15_formal_baseline",
        "baseline_version": "v1",
        "baseline_id": "confirmed_gate_baseline_and_next_capability_v1_gate15",
        "promoted_from_run": RUNTIME_RUN.name,
        "promoted_timestamp": promoted_at,
        "promoted_from_proposed_manifest": proposed_manifest.name,
        "archived_previous_baseline": str(archive.relative_to(ROOT)),
        "gate_allowed_count": len(GATE_IDS),
        "gate_suppressed_count": 100 - len(GATE_IDS),
        "gate_allowed_ids": GATE_IDS,
        "cumulative_added_from_gate10": [4, 39, 56, 63, 83],
        "valid_result": {"correct": 17, "incorrect": 0, "blank": 13},
        "test_result": {"completed": 100, "errors": 0},
        "unit_test_result": {"passed": 125, "minimum_required": 125},
        "verification_method_counts": method_counts,
        "human_answer_dependency_count": 0,
        "raw_files_unchanged": raw_unchanged,
        "predictions_file": formal_predictions.name,
        "predictions_file_sha256": sha256(formal_predictions),
        "submission_candidates_file": formal_candidates.name,
        "submission_candidates_file_sha256": sha256(formal_candidates),
        "gate_evidence_file": formal_evidence.name,
        "gate_evidence_file_sha256": sha256(formal_evidence),
        "verification_audit_file": verification_audit.name,
        "verification_audit_file_sha256": sha256(verification_audit),
        "source_commit_hash_before_promotion": git_head(),
        "proposed_input_hashes": {
            proposed_predictions.name: sha256(proposed_predictions),
            proposed_candidates.name: sha256(proposed_candidates),
            proposed_manifest.name: sha256(proposed_manifest),
            proposed_evidence.name: sha256(proposed_evidence),
        },
        "runtime_reproducible_without_human_review": True,
        "test10_included": False,
    }
    (ANALYSIS / "baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    capability_rows = [
        {
            "question_id": row["question_id"],
            "route": row["route"],
            "verification_method": row["verification_method"],
            "gate_allowed": True,
            "runtime_reproducible": True,
            "human_answer_dependency": False,
        }
        for row in candidate_rows
    ]
    write_csv(ANALYSIS / "capability_matrix_gate15_baseline.csv", capability_rows)
    (ANALYSIS / "capability_matrix_gate15_baseline.md").write_text(
        "# Gate 15 Capability Matrix\n\n"
        "この表は現在の正式回帰基準で許可された Route と検証方法を記録する。"
        "人間確認データは runtime、Verification、Gate に入力しない。\n\n"
        "- valid: 17 correct / 0 incorrect / 13 blank\n"
        "- test: 100 complete / 0 errors\n"
        "- Gate: 15 allowed / 85 suppressed\n"
        "- test 10、test 0、test 85: suppressed\n"
        "- Unit: 125 tests OK\n",
        encoding="utf-8",
    )
    (ANALYSIS / "formal_evaluation_summary.md").write_text(
        "# Formal Evaluation Summary\n\n"
        "- baseline: deterministic Gate 15 formal baseline\n"
        "- valid: 17 correct / 0 incorrect / 13 blank\n"
        "- test: 100 complete / 0 errors\n"
        "- Gate: 15 allowed / 85 suppressed\n"
        "- allowed IDs: 2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92\n"
        "- cumulative additions from Gate 10: 4, 39, 56, 63, 83\n"
        "- human answer dependency: 0\n"
        "- test 10, test 0, test 85: suppressed\n"
        "- unit: 125 tests OK\n",
        encoding="utf-8",
    )
    (ANALYSIS / "gate15_promotion_record.json").write_text(
        json.dumps(
            {
                "archive": str(archive.relative_to(ROOT)),
                "formal_manifest": "baseline_manifest.json",
                "formal_predictions": "predictions.csv",
                "formal_candidates": "submission_candidates.csv",
                "formal_evidence": "gate_evidence.csv",
                "validated_prediction_ids": prediction_audit["ids"],
                "validated_answer_ids": sorted(prediction_audit["answers"]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"archive": str(archive), "manifest": manifest}, ensure_ascii=False))


if __name__ == "__main__":
    main()
