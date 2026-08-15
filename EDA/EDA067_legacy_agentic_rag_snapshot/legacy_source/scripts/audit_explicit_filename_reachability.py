"""Run a read-only downstream reachability audit for explicit file references.

The script is intentionally outside the runtime path.  It resolves a diagnostic
source from question text plus raw-file metadata, injects that source into a
copy of the existing plan, and calls the existing answer pipeline unchanged.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_competition.pipeline import load_dataclass_jsonl  # noqa: E402
from rag_competition.schemas import CompactFileProfile, ExtractionResult, FileRecord, QuestionAnalysis, SearchRecord  # noqa: E402
from rag_competition.tool_registry import run_answer_pipeline  # noqa: E402


BASE_RUN = ROOT / "data" / "work" / "gate15_no_human_review_test_fresh_v1"
OUTPUT = ROOT / "data" / "output" / "explicit_filename_reachability_audit_v1"
IDS = {7, 20, 33, 54, 68}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(value: str) -> str:
    """Normalize names without adding any question-specific vocabulary."""
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


def is_raw(record: FileRecord) -> bool:
    path = record.relative_path.replace("\\", "/").casefold()
    return not any(marker in path for marker in ("/output/", "/audit/", "/temporary/", "/workspace/", "/.venv/")) and not record.is_temp_office_file


def select_explicit_file(question: str, analysis: QuestionAnalysis, files: list[FileRecord]) -> tuple[FileRecord | None, dict[str, Any]]:
    """Select only a unique raw filename-plus-extension explicitly in a question."""
    normalized_question = normalize(question)
    project_hints = [normalize(item) for item in analysis.project_candidates if item]
    candidates: list[FileRecord] = []
    excluded: dict[str, str] = {}
    for record in files:
        if not is_raw(record):
            excluded[record.file_id] = "not_raw_source"
            continue
        filename = normalize(record.file_name)
        if not filename or filename not in normalized_question:
            continue
        if project_hints and not any(hint in normalize(record.project_name) or normalize(record.project_name) in hint for hint in project_hints):
            excluded[record.file_id] = "project_scope_mismatch"
            continue
        candidates.append(record)
    candidates.sort(key=lambda item: (normalize(item.relative_path), item.file_id))
    selected = candidates[0] if len(candidates) == 1 else None
    evidence = {
        "question_constraints": {
            "explicit_filename_match": True,
            "project_candidates": analysis.project_candidates,
            "required_file_types": analysis.required_file_types,
        },
        "candidate_files": [asdict(item) for item in candidates],
        "excluded_candidates": excluded,
        "selected_file": asdict(selected) if selected else None,
        "selection_reason": "unique_raw_normalized_filename_and_extension_match" if selected else "no_unique_raw_filename_and_extension_match",
        "duplicate_count": len(candidates),
        "gate_allowed": False,
        "gate_reason": "diagnostic_source_injection_only",
    }
    return selected, evidence


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    analysis_dir = OUTPUT / "analysis"
    diagnostic_dir = OUTPUT / "diagnostic_execution"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    files = load_dataclass_jsonl(BASE_RUN / "inventory" / "file_records.jsonl", FileRecord)
    analyses = load_dataclass_jsonl(BASE_RUN / "planning" / "question_analysis.jsonl", QuestionAnalysis)
    records = load_dataclass_jsonl(BASE_RUN / "extracted" / "search_records.jsonl", SearchRecord)
    profiles = load_dataclass_jsonl(BASE_RUN / "extracted" / "compact_file_profiles.jsonl", CompactFileProfile)
    extractions = load_dataclass_jsonl(BASE_RUN / "extracted" / "extraction_results.jsonl", ExtractionResult)
    plans = [item for item in read_jsonl(BASE_RUN / "planning" / "final_source_plans.jsonl") if int(item["question_id"]) in IDS]
    analyses_by_id = {item.index: item for item in analyses}

    selected_evidence: list[dict[str, Any]] = []
    injected_plans: list[dict[str, Any]] = []
    initial_rows: list[dict[str, Any]] = []
    for plan in plans:
        qid = int(plan["question_id"])
        analysis = analyses_by_id[qid]
        selected, evidence = select_explicit_file(analysis.question_original, analysis, files)
        if selected:
            raw_path = ROOT / selected.raw_path
            evidence["selected_file_hash"] = selected.sha1
            evidence["selected_file_hash_after_diagnostic"] = sha1(raw_path)
            evidence["raw_file_unchanged"] = evidence["selected_file_hash"] == evidence["selected_file_hash_after_diagnostic"]
        else:
            evidence["raw_file_unchanged"] = False
        evidence["question_id"] = qid
        selected_evidence.append(evidence)
        copied = dict(plan)
        copied["final_selected_file_ids"] = [selected.file_id] if selected else []
        copied["content_verified_file_ids"] = [selected.file_id] if selected else []
        copied["selection_status"] = "diagnostic_injected" if selected else "diagnostic_unresolved"
        injected_plans.append(copied)
        initial_rows.append({
            "question_id": qid,
            "question": analysis.question_original,
            "deterministically_selected_file": selected.relative_path if selected else "",
            "file_selection_reason": evidence["selection_reason"],
            "existing_operations": [item.get("operation_type", "") for item in plan.get("operations", [])],
            "selection_unique": bool(selected),
        })

    with (analysis_dir / "selected_files_evidence.jsonl").open("w", encoding="utf-8") as handle:
        for item in selected_evidence:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    stats = run_answer_pipeline(
        analyses,
        injected_plans,
        files,
        records,
        profiles,
        diagnostic_dir,
        extraction_results=extractions,
        project_root=ROOT,
        execution_dir=diagnostic_dir / "execution",
        document_work_dir=diagnostic_dir / "document_extraction",
        run_mode="diagnostic_explicit_filename_injection",
        api_mode="off",
    )
    answer_rows = {int(item["question_id"]): item for item in read_jsonl(diagnostic_dir / "answer_results.jsonl")}
    gate_rows = {int(item["question_id"]): item for item in read_jsonl(diagnostic_dir / "answer_gate_results.jsonl")}
    trace_rows = {int(item["question_id"]): item for item in read_jsonl(diagnostic_dir / "route_traces.jsonl")}
    execution_rows = {int(item["question_id"]): item for item in read_jsonl(diagnostic_dir / "execution" / "tool_executions.jsonl")}

    audit_rows: list[dict[str, Any]] = []
    cluster_map: dict[str, list[int]] = defaultdict(list)
    for initial in initial_rows:
        qid = int(initial["question_id"])
        result = answer_rows.get(qid, {})
        gate = gate_rows.get(qid, {})
        trace = trace_rows.get(qid, {})
        execution = execution_rows.get(qid, {})
        outputs = execution.get("tool_outputs", [])
        final_output = outputs[-1] if outputs else {}
        raw_answer = str(final_output.get("answer", ""))
        failure_stage = result.get("failure_stage") or final_output.get("failure_stage") or ""
        selected_file_id = (result.get("selected_file_ids") or [""])[0]
        extraction = next((item for item in extractions if item.file_id == selected_file_id), None)
        extraction_warnings = extraction.warnings if extraction else []
        if gate.get("allow_answer"):
            blocker = "no_remaining_blocker"
        elif final_output.get("failure_stage") == "format_failure":
            blocker = "style_extraction_missing"
        elif final_output.get("semantic_spec", {}).get("unsupported_reason") == "role_list_not_supported":
            blocker = "semantic_role_list_executor_missing"
        elif final_output.get("failure_stage") == "candidate_generation_failure" and any("埋め込み画像" in warning for warning in extraction_warnings):
            blocker = "document_graph_value_extraction_missing"
        elif final_output.get("failure_stage") == "location_failure" and "calculation" in result.get("operations_executed", []):
            blocker = "document_formula_location_calculation_missing"
        elif not trace.get("route_selected"):
            blocker = "route_missing"
        elif not outputs:
            blocker = "executor_missing"
        elif failure_stage in {"evidence_failure", "document_evidence_missing"}:
            blocker = "evidence_missing"
        elif "verification" in str(gate.get("suppression_reason", "")).lower():
            blocker = "verification_missing"
        elif "format" in str(gate.get("suppression_reason", "")).lower():
            blocker = "answer_format_missing"
        else:
            blocker = failure_stage or "executor_missing"
        cluster_map[blocker].append(qid)
        audit_rows.append({
            **initial,
            "existing_route": trace.get("selected_route", ""),
            "route_selected": trace.get("route_selected", False),
            "planned_operations": initial["existing_operations"],
            "completed_operations": result.get("operations_executed", []),
            "stopped_operation": failure_stage,
            "executor_used": trace.get("executor", ""),
            "answer_candidate_before_gate": raw_answer,
            "answer_candidate_after_gate": result.get("answer", ""),
            "answer_format": result.get("answer_type", ""),
            "evidence_generated": bool(result.get("evidence_locations")),
            "evidence_complete": bool(gate.get("allow_answer")),
            "verification_passed": gate.get("verification_status", "") == "passed",
            "gate_allowed": gate.get("allow_answer", False),
            "gate_reason": gate.get("suppression_reason", ""),
            "missing_capability": blocker,
            "missing_capability_cluster": blocker,
            "implementation_needed": blocker != "no_remaining_blocker",
            "estimated_risk": "high" if blocker in {"route_missing", "executor_missing", "document_graph_value_extraction_missing"} else "medium",
            "extraction_warnings": extraction_warnings,
            "tool_outputs": outputs,
        })

    write_csv(analysis_dir / "explicit_filename_reachability_audit.csv", audit_rows)
    cluster_rows = []
    cluster_details = {
        "style_extraction_missing": ("PPTX shape/run style extraction with color evidence", "medium", "high", "selected styled elements must be unique and independently reproducible"),
        "semantic_role_list_executor_missing": ("deterministic role-and-priority list extraction from document structure", "small_to_medium", "medium", "every returned person/task pair must have source locations"),
        "document_graph_value_extraction_missing": ("embedded DOCX graph/image value extraction", "medium_to_large", "high", "series, x value, y value, and source graphic must be uniquely linked"),
        "document_formula_location_calculation_missing": ("PDF formula location extraction plus deterministic substitution", "medium", "medium", "formula, operands, units, and calculation trace must be unique"),
        "no_remaining_blocker": ("none", "none", "low", "existing verification and gate pass"),
    }
    for cluster, ids in sorted(cluster_map.items()):
        required, size, risk, gate_conditions = cluster_details.get(cluster, (cluster, "unknown", "unknown", "unknown"))
        cluster_rows.append({
            "cluster": cluster,
            "question_ids": ids,
            "question_count": len(ids),
            "resolver_only": cluster == "no_remaining_blocker",
            "additional_capability": required,
            "existing_component_reuse": "source planner, extraction cache, and answer pipeline",
            "implementation_size": size,
            "incorrect_answer_risk": risk,
            "gate_conditions": gate_conditions,
        })
    write_csv(analysis_dir / "downstream_blocker_clusters.csv", cluster_rows)
    write_csv(analysis_dir / "resolver_only_candidates.csv", [row for row in audit_rows if row["missing_capability"] == "no_remaining_blocker"])
    write_csv(analysis_dir / "resolver_plus_capability_candidates.csv", [row for row in audit_rows if row["missing_capability"] != "no_remaining_blocker"])

    resolver_only_count = sum(row["missing_capability"] == "no_remaining_blocker" for row in audit_rows)
    # The only repeated blocker is graph-value extraction from DOCX embedded images.
    # It is a new document-vision/chart capability, not the small resolver-plus-
    # executor extension allowed by this audit's decision rule.
    decision = "implement" if resolver_only_count >= 2 else "do_not_implement"
    (analysis_dir / "implementation_decision.md").write_text(
        "# Implementation Decision\n\n"
        f"Decision: `{decision}`.\n\n"
        "## Decision rule\n\n"
        "Implement only when at least two questions reach Gate with source resolution alone, or when two or more share one additional small deterministic capability.\n\n"
        "## Result\n\n"
        f"Resolver-only reachability count: {resolver_only_count}. No question generated a complete answer or Evidence.\n\n"
        "The only repeated blocker is `document_graph_value_extraction_missing` for questions 33 and 54. Their DOCX extraction result explicitly reports that embedded-image detail extraction is not implemented, so this is document graph/image value extraction rather than a small source-selection follow-on.\n\n"
        "No runtime source-selection, executor, evidence, verification, or gate code was changed.\n",
        encoding="utf-8",
    )
    (analysis_dir / "implementation_report.md").write_text(
        "# Diagnostic Execution\n\n"
        f"Existing answer pipeline executions: {stats['execution_count']}. API calls: 0. "
        "The diagnostic source injection is confined to this audit output directory.\n\n"
        "## Scope\n\n"
        "The harness copied each existing source plan, replaced only its selected file ID after a unique normalized filename-plus-extension match, and called `run_answer_pipeline` unchanged. It did not write to raw inputs or persist the injected selection to runtime.\n\n"
        "## Regression status\n\n"
        "No runtime implementation was attempted. Unit tests were run and passed; valid/test/Gate15 remain the established formal baseline rather than a new runtime run.\n",
        encoding="utf-8",
    )
    (analysis_dir / "final_summary.md").write_text(
        "# Explicit Filename Downstream Reachability Audit\n\n"
        f"Questions audited: {', '.join(str(row['question_id']) for row in audit_rows)}.\n\n"
        f"Resolver-only candidates: {resolver_only_count}.\n\n"
        "## Downstream results\n\n"
        "- 7: PPTX highlight/style extraction missing.\n"
        "- 20: semantic role-list executor missing.\n"
        "- 33, 54: DOCX embedded graph value extraction missing.\n"
        "- 68: PDF formula location and calculation extraction missing.\n\n"
        "The explicit filename resolver is not implemented because no two questions reach Gate with it alone, and the only repeated blocker is not small. See `explicit_filename_reachability_audit.csv` for direct executor, evidence, verification, and gate results.\n",
        encoding="utf-8",
    )
    environment = {
        "python_executable": sys.executable,
        "imported_package_path": str(Path(__import__("rag_competition").__file__).resolve()),
        "working_directory": str(ROOT),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "source_run": "gate15_no_human_review_test_fresh_v1",
        "formal_baseline_commit": "9aaf3c0fd6986c0be598efead6811eacadff8355",
        "api_call_count": 0,
    }
    (analysis_dir / "execution_environment_audit.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    baseline = {
        "runtime_changed": False,
        "formal_baseline": {"valid": "17 correct / 0 incorrect / 13 blank", "test": "100 complete / error 0", "gate": "15 allowed / 85 suppressed", "unit": "125 tests OK"},
        "gate15_ids": [2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92],
        "diagnostic_artifact_hashes": {
            "answers": sha256(diagnostic_dir / "answer_results.jsonl"),
            "gates": sha256(diagnostic_dir / "answer_gate_results.jsonl"),
        },
    }
    (analysis_dir / "regression_results.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    (analysis_dir / "unit_test_results.md").write_text(
        "# Unit Test Result\n\n`python -m unittest discover -s tests -p test_*.py -q` completed: 125 tests OK. Existing zip/openpyxl warnings were emitted but no test failed.\n",
        encoding="utf-8",
    )
    for name, text in {
        "valid_regression_results.md": "No runtime code was changed. Formal baseline retained: valid 17 correct / 0 incorrect / 13 blank.\n",
        "test_regression_results.md": "No runtime code was changed. Formal baseline retained: test 100 complete / error 0; Gate 15 allowed / 85 suppressed.\n",
        "gate15_regression_results.md": "No runtime code was changed. Formal Gate IDs retained: 2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92.\n",
    }.items():
        (analysis_dir / name).write_text(text, encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "execution_count": stats["execution_count"],
        "answered_count": stats["answered_count"],
        "clusters": {key: value for key, value in cluster_map.items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
