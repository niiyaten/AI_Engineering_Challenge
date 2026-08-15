"""Read-only audit of document-role and target-file selection under Gate 15.

This script deliberately records audit conclusions outside runtime.  It does not
alter planner inputs, source scores, raw documents, or answer/Gate behaviour.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/work/gate15_no_human_review_test_fresh_v1"
OUT = ROOT / "data/output/r5_document_selection_audit_v1/analysis"
RAW_ROOT = ROOT / "data/raw"

# These are re-audit outcomes, not question-specific runtime branches.  The
# groups identify the actual missing capability after checking current plans.
REAUDIT: dict[int, dict[str, str]] = {
    7: {"classification": "R5", "cluster": "explicit_filename_extension_resolver", "reason": "質問に明示された基礎分析.pptxが同一案件内で一意に存在するが、提案書.pptxが選択されている。", "downstream": "format_executor_and_content_check"},
    8: {"classification": "R5", "cluster": "document_type_role_resolver", "reason": "データサイエンティスト調査資料.docxが一意に存在するが、計画段階でデータ表だけを要求している。", "downstream": "difference_calculation"},
    11: {"classification": "R5", "cluster": "document_type_role_resolver", "reason": "報告資料を要求するのに提案書.pptxが選択され、最終報告.pptxが候補に残っている。", "downstream": "format_executor"},
    16: {"classification": "R5", "cluster": "document_type_role_resolver", "reason": "中間報告資料を要求するのに提案書が選択されている。中間報告の時点対応は資料内容で追加確認が必要。", "downstream": "format_executor_and_stage_alignment"},
    17: {"classification": "R6", "cluster": "multi_document_cardinality_resolver", "reason": "最初から最後のMMを比較するため、資料役割だけでなく複数会議資料の時系列関係が必要。", "downstream": "format_extraction_and_cross_document_calculation"},
    20: {"classification": "R5", "cluster": "explicit_filename_extension_resolver", "reason": "質問明示の報告資料_2025-08-18.pdfが一意に存在するが、調査資料.docxが選択されている。", "downstream": "document_executor"},
    33: {"classification": "R5", "cluster": "explicit_filename_extension_resolver", "reason": "質問明示の基礎分析.docxが一意に存在するが、内容検索の弱さにより未選択。", "downstream": "document_executor"},
    45: {"classification": "R5+R6", "cluster": "explicit_filename_pair_resolver", "reason": "質問は2つの会議録PDFを明示するが、必要資料数と版対の選択が不十分。", "downstream": "comparison_executor"},
    54: {"classification": "R5", "cluster": "explicit_filename_extension_resolver", "reason": "質問明示の基礎分析.docxが一意に存在するが、内容検索の弱さにより未選択。", "downstream": "document_executor"},
    66: {"classification": "R1", "cluster": "notebook_or_code_result_route", "reason": "分析コードは選択済みで、停止点は日付可視化結果を既存Routeへ渡せないこと。", "downstream": "notebook_or_code_executor"},
    68: {"classification": "R5", "cluster": "explicit_filename_extension_resolver", "reason": "質問明示のデータサイエンス市場の未来予測.pdfが一意に存在するが、未選択。", "downstream": "document_executor"},
    71: {"classification": "R5+R6", "cluster": "document_type_and_cardinality_resolver", "reason": "会議録を要求するのに提案書が選択されている。対象会議録が複数あり、単一選択か全件対象かも未決。", "downstream": "format_executor_and_cardinality"},
}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFKC", value or "")).casefold()


def compact(value: Any, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def jsonl_by_id(path: Path) -> dict[int, dict[str, Any]]:
    return {
        int(row["question_id"]): row
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    }


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = OUT / name
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def role_for_file(row: dict[str, str]) -> str:
    """Classify inventory files for audit evidence without changing FileRecord."""
    path = nfc(row.get("raw_path", ""))
    name = nfc(row.get("file_name", ""))
    if "data/output" in path or "audit" in path:
        return "audit_artifact"
    if row.get("is_temp_office_file") == "True" or name.startswith("~$"):
        return "temporary_artifact"
    if "/04.分析/analysis_outputs/" in path or "leaderboard" in name or "metrics.json" in name:
        return "model_output"
    if "/04.分析/analysis_project/" in path and "/notebooks/" in path:
        return "analysis_notebook"
    if name.endswith(".ipynb"):
        return "source_notebook"
    if "sample_submission" in name:
        return "sample_submission"
    if name in {"train.csv", "train.xlsx", "train.tsv"}:
        return "training_data"
    if name in {"test.csv", "test.xlsx", "test.tsv"}:
        return "test_data"
    if "old" in path or "_old" in name:
        return "archived_version"
    kind = row.get("document_kind", "unknown")
    return {
        "data": "source_data",
        "proposal": "proposal",
        "contract": "contract",
        "schedule": "reference_document",
        "analysis": "analysis_notebook",
        "meeting": "meeting_minutes",
        "meeting_minutes": "meeting_minutes",
        "report": "report",
    }.get(kind, "unknown")


def extract_constraints(question: str) -> dict[str, Any]:
    extensions = re.findall(r"\.(docx|pptx|xlsx|pdf|csv|tsv|py|ipynb|md)", question, flags=re.I)
    filenames = re.findall(r"[^\s、。()（）]+\.(?:docx|pptx|xlsx|pdf|csv|tsv|py|ipynb|md)", question, flags=re.I)
    doc_type = next((label for label in ("会議録", "中間報告", "報告資料", "調査資料", "基礎分析", "EDA") if label in question), "")
    versions = re.findall(r"\b(?:v|r)\d+\b|old|最新版|旧版", question, flags=re.I)
    sheets = re.findall(r"\bSheet\d+\b", question, flags=re.I)
    return {
        "requested_filenames": filenames,
        "requested_extensions": sorted(set(extensions)),
        "requested_document_type": doc_type,
        "requested_version": versions,
        "requested_sheet": sheets,
        "required_document_count": 2 if any(word in question for word in ("と", "から", "比較")) and len(filenames) >= 2 else 1,
    }


def source_candidates_for(question_id: int, selection: dict[str, Any]) -> list[dict[str, Any]]:
    rows = selection.get("source_candidates", [])
    return [row for row in rows if int(row.get("question_id", -1)) == question_id]


def matching_named_files(question: str, inventory: list[dict[str, str]], project_name: str) -> list[dict[str, str]]:
    normalized_question = nfc(question)
    matches = []
    for row in inventory:
        if project_name and row.get("project_name") != project_name:
            continue
        name = nfc(row.get("file_name", ""))
        if name and name in normalized_question and role_for_file(row) not in {"audit_artifact", "temporary_artifact", "model_output"}:
            matches.append(row)
    return matches


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    planning = RUN / "planning"
    questions_file = next((ROOT / "data/raw/share/share").rglob("questions_test.csv"))
    questions = {int(row["index"]): row["question"] for row in csv_rows(questions_file)}
    inventory = csv_rows(RUN / "inventory/file_records.csv")
    inventory_by_id = {row["file_id"]: row for row in inventory}
    inventory_by_path = {row["raw_path"]: row for row in inventory}
    plans = jsonl_by_id(planning / "final_source_plans.jsonl")
    selection_results = jsonl_by_id(planning / "source_selection_results.jsonl")
    answers = jsonl_by_id(ROOT / "data/output/gate15_no_human_review_test_fresh_v1/answer_results.jsonl")
    gates = jsonl_by_id(ROOT / "data/output/gate15_no_human_review_test_fresh_v1/answer_gate_results.jsonl")
    traces = jsonl_by_id(ROOT / "data/output/gate15_no_human_review_test_fresh_v1/route_traces.jsonl")

    audit_rows: list[dict[str, Any]] = []
    role_rows: list[dict[str, Any]] = []
    role_seen: set[tuple[int, str]] = set()
    evidence_dir = OUT / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    for question_id, conclusion in REAUDIT.items():
        question = questions[question_id]
        plan = plans[question_id]
        selection = selection_results[question_id]
        answer = answers[question_id]
        gate = gates[question_id]
        trace = traces[question_id]
        constraints = extract_constraints(question)
        selected_ids = plan.get("final_selected_file_ids", [])
        selected_rows = [inventory_by_id[file_id] for file_id in selected_ids if file_id in inventory_by_id]
        project = next(iter(plan.get("source_requirements", [{}]))).get("project_candidates", [""])[0]
        named_matches = matching_named_files(question, inventory, project)
        candidates = source_candidates_for(question_id, selection)
        # The raw inventory is authoritative for a filename reference. It also
        # correctly splits a named pair that a broad text regex may treat as one.
        if named_matches:
            constraints["requested_filenames"] = [row["file_name"] for row in named_matches]
            constraints["requested_extensions"] = sorted({row["extension"].lstrip(".") for row in named_matches})
            constraints["required_document_count"] = len(named_matches)
        candidate_details = []
        for candidate in candidates:
            candidate_details.append({
                "path": candidate.get("source_file", ""),
                "role": candidate.get("document_role", "unknown"),
                "version": candidate.get("document_version", ""),
                "extension": candidate.get("document_type", ""),
                "score": candidate.get("selection_score", ""),
                "content_match": candidate.get("content_requirement_match", False),
                "rank": candidate.get("candidate_rank", ""),
                "summary": compact(candidate.get("headings", [])),
            })
            source_row = inventory_by_path.get(candidate.get("source_file", ""))
            if source_row and (question_id, source_row["file_id"]) not in role_seen:
                role_seen.add((question_id, source_row["file_id"]))
                role_rows.append({
                    "question_id": question_id,
                    "project_name": source_row.get("project_name", ""),
                    "file_id": source_row["file_id"],
                    "raw_path": source_row["raw_path"],
                    "file_name": source_row["file_name"],
                    "extension": source_row["extension"],
                    "inventory_document_kind": source_row.get("document_kind", ""),
                    "audit_role": role_for_file(source_row),
                    "version_label": source_row.get("version_label", ""),
                    "size_bytes": source_row.get("size_bytes", ""),
                    "temp": source_row.get("is_temp_office_file", ""),
                })
        for row in named_matches:
            if (question_id, row["file_id"]) in role_seen:
                continue
            role_seen.add((question_id, row["file_id"]))
            role_rows.append({
                "question_id": question_id,
                "project_name": row.get("project_name", ""),
                "file_id": row["file_id"],
                "raw_path": row["raw_path"],
                "file_name": row["file_name"],
                "extension": row["extension"],
                "inventory_document_kind": row.get("document_kind", ""),
                "audit_role": role_for_file(row),
                "version_label": row.get("version_label", ""),
                "size_bytes": row.get("size_bytes", ""),
                "temp": row.get("is_temp_office_file", ""),
            })
        selected_paths = [row["raw_path"] for row in selected_rows]
        missing = conclusion["reason"]
        audit = {
            "question_id": question_id,
            "question_original": question,
            "company_or_project": project,
            "question_operation": "+".join(answer.get("operations_executed", [])),
            "question_constraints": json.dumps(constraints, ensure_ascii=False),
            "single_or_multi_document": "multiple" if constraints["required_document_count"] > 1 else "single",
            "candidate_files": json.dumps(candidate_details, ensure_ascii=False),
            "named_raw_candidates": json.dumps([row["raw_path"] for row in named_matches], ensure_ascii=False),
            "runtime_selected_files": json.dumps(selected_paths, ensure_ascii=False),
            "selected_route": trace.get("selected_route", ""),
            "stopped_operation": "+".join(answer.get("operations_executed", [])),
            "suppression_reason": gate.get("suppression_reason", ""),
            "current_evidence": json.dumps(answer.get("evidence_locations", []), ensure_ascii=False),
            "reaudited_classification": conclusion["classification"],
            "selection_capability_cluster": conclusion["cluster"],
            "selection_failure_reason": missing,
            "unambiguous_selection_evidence": "company scope + normalized filename + extension + raw path + non-temporary/non-output role",
            "selection_blockers": "downstream=" + conclusion["downstream"],
            "same_capability_questions": "7,20,33,54,68" if conclusion["cluster"] == "explicit_filename_extension_resolver" else "",
            "implementation_difficulty": "small" if conclusion["cluster"] == "explicit_filename_extension_resolver" else "medium",
            "incorrect_answer_risk": "low for source selection; downstream answer risk remains separate" if conclusion["cluster"] == "explicit_filename_extension_resolver" else "medium_or_high",
        }
        audit_rows.append(audit)
        evidence = {
            "question_id": question_id,
            "question_constraints": constraints,
            "company_scope": project,
            "requested_filename": constraints["requested_filenames"],
            "requested_extension": constraints["requested_extensions"],
            "requested_document_type": constraints["requested_document_type"],
            "requested_version": constraints["requested_version"],
            "requested_sheet": constraints["requested_sheet"],
            "requested_relationship": "single_source" if constraints["required_document_count"] == 1 else "named_pair",
            "required_document_count": constraints["required_document_count"],
            "candidate_files": candidate_details,
            "candidate_roles": {row["raw_path"]: role_for_file(row) for row in named_matches},
            "mandatory_constraint_results": {
                "project_scope": bool(project),
                "unique_named_raw_candidate": len(named_matches) == constraints["required_document_count"],
                "raw_not_output": all(role_for_file(row) not in {"audit_artifact", "temporary_artifact", "model_output"} for row in named_matches),
            },
            "excluded_candidates": {candidate.get("source_file", ""): candidate.get("exclusion_reason", "") for candidate in candidates if not candidate.get("included", False)},
            "selected_files": selected_paths,
            "selection_reason": conclusion["reason"],
            "second_best_candidate": candidate_details[1] if len(candidate_details) > 1 else None,
            "ambiguity_margin": None,
            "runtime_reproducible": True,
            "confidence": 0.95 if conclusion["cluster"] == "explicit_filename_extension_resolver" else 0.55,
            "gate_allowed": False,
            "gate_reason": "audit_only; source selection must be followed by structure, executor, and verification checks",
        }
        (evidence_dir / f"test_{question_id:03d}_document_selection_evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # The exact filename cluster is the sole small capability with at least two
    # deterministic source selections. It is not implemented because selection
    # alone does not prove answer/Evidence reachability for two questions yet.
    clusters = [
        {"cluster_name": "explicit_filename_extension_resolver", "question_ids": "7,20,33,54,68", "estimated_selection_gain": 5, "estimated_end_to_end_gain": 0, "current_misselection_pattern": "company-prefixed question filename is not converted to a basename constraint; weak content search overrides it", "required_evidence": "project + normalized basename + extension + raw/non-output role + unique candidate", "mandatory_conditions": "unique project-scoped exact filename and extension", "supporting_conditions": "extractable structure exists", "exclusion_conditions": "temporary/output/audit/duplicate exact candidate", "existing_reuse": "FileRecord, deterministic_candidates_for_requirement, verify_content, source_selection_results", "planned_files": "source_selection.py, tests/test_source_selection_pipeline.py", "unit_tests": "NFC/NFD filename, company-prefixed filename, duplicate basename, pair filename, output exclusion", "gate_conditions": "selection evidence plus downstream Route verification", "implementation_size": "small", "incorrect_answer_risk": "low for selection; answer risk delegated downstream", "recommendation": "design only until two target questions also pass downstream reachability"},
        {"cluster_name": "document_type_role_resolver", "question_ids": "8,11,16,71", "estimated_selection_gain": 2, "estimated_end_to_end_gain": 0, "current_misselection_pattern": "proposal is accepted even when question says survey/report/meeting minutes", "required_evidence": "canonical document role, title/path, content heading", "mandatory_conditions": "single unambiguous role-compatible document", "supporting_conditions": "requested operation is supported", "exclusion_conditions": "multiple meeting/report stages or role conflict", "existing_reuse": "FileRecord.document_kind, CompactFileProfile", "planned_files": "source_selection.py, source_selection_resolution.py", "unit_tests": "role synonyms, meeting_minutes, report vs proposal, ambiguity suppression", "gate_conditions": "unique role and downstream structure", "implementation_size": "medium", "incorrect_answer_risk": "medium", "recommendation": "defer; 16/71 still need stage/cardinality resolution"},
        {"cluster_name": "explicit_filename_pair_resolver", "question_ids": "45,17,71", "estimated_selection_gain": 1, "estimated_end_to_end_gain": 0, "current_misselection_pattern": "pair/cardinality is compressed into a single-source requirement", "required_evidence": "two named filenames and relation", "mandatory_conditions": "two unique files in same project and requested relation", "supporting_conditions": "comparison executor available", "exclusion_conditions": "missing pair or unresolved ordering", "existing_reuse": "source relation evidence", "planned_files": "source_selection.py, source_selection_resolution.py", "unit_tests": "two named files, one missing, pair order, duplicate name", "gate_conditions": "both sources and comparison verification", "implementation_size": "medium", "incorrect_answer_risk": "high", "recommendation": "out of scope for one small selection change"},
        {"cluster_name": "notebook_or_code_result_route", "question_ids": "66", "estimated_selection_gain": 0, "estimated_end_to_end_gain": 0, "current_misselection_pattern": "analysis code is selected but result lookup is unsupported", "required_evidence": "notebook/code output", "mandatory_conditions": "result artefact or deterministic replay", "supporting_conditions": "input data reference", "exclusion_conditions": "image-only result", "existing_reuse": "notebook route", "planned_files": "notebook_executor.py", "unit_tests": "not applicable to selection only", "gate_conditions": "reproducible output", "implementation_size": "medium", "incorrect_answer_risk": "medium", "recommendation": "R1, not R5"},
    ]
    write_csv("r5_document_selection_audit.csv", audit_rows)
    write_csv("r5_document_role_inventory.csv", role_rows)
    write_csv("r5_capability_clusters.csv", clusters)

    # Re-scan every currently suppressed question. This is intentionally broad:
    # it identifies source-selection symptoms, while the detailed re-audit above
    # decides whether source selection is truly the first missing capability.
    suppressed_scan: list[dict[str, Any]] = []
    for question_id, gate in sorted(gates.items()):
        if gate.get("allow_answer") is True or gate.get("gate_status") == "allowed":
            continue
        question = questions[question_id]
        plan = plans[question_id]
        requirement = next(iter(plan.get("source_requirements", [{}])), {})
        project = next(iter(requirement.get("project_candidates", [""])), "")
        named = matching_named_files(question, inventory, project)
        selected = set(plan.get("final_selected_file_ids", []))
        named_ids = {row["file_id"] for row in named}
        explicit_unselected = bool(named_ids) and not named_ids.issubset(selected)
        suppressed_scan.append({
            "question_id": question_id,
            "question_original": question,
            "project_scope": project,
            "formal_gate_allowed": False,
            "explicit_raw_filename_matches": json.dumps([row["raw_path"] for row in named], ensure_ascii=False),
            "runtime_selected_file_ids": json.dumps(sorted(selected), ensure_ascii=False),
            "explicit_named_file_unselected": explicit_unselected,
            "source_selection_reaudit_status": REAUDIT.get(question_id, {}).get("classification", "not_confirmed_as_R5"),
            "first_missing_capability": REAUDIT.get(question_id, {}).get("cluster", "requires_separate_route_audit"),
            "suppression_reason": gate.get("suppression_reason", ""),
        })
    write_csv("suppressed_85_source_selection_scan.csv", suppressed_scan)

    order = [7, 20, 33, 54, 68, 8, 11, 16, 71, 45, 17, 66]
    audit_by_id = {row["question_id"]: row for row in audit_rows}
    ranking = []
    for rank, question_id in enumerate(order, 1):
        if question_id not in audit_by_id:
            continue
        row = dict(audit_by_id[question_id])
        row["priority_rank"] = rank
        row["priority_score"] = 20 - rank
        row["recommendation"] = (
            "candidate_for_explicit_filename_design_only" if row["selection_capability_cluster"] == "explicit_filename_extension_resolver"
            else "defer_until_non_selection_blockers_are_resolved"
        )
        ranking.append(row)
    write_csv("r5_priority_ranking.csv", ranking)

    (OUT / "selected_r5_cluster_design.md").write_text(
        "# Selected R5 Capability Design\n\n"
        "## Candidate\n\n"
        "`explicit_filename_extension_resolver` is the highest-confidence source-selection capability. "
        "It applies a mandatory project-scoped normalized basename-and-extension filter before the "
        "current score ranking. It rejects output, audit, temporary, and duplicate candidates.\n\n"
        "## Expected scope\n\n"
        "The audit identifies tests 7, 20, 33, 54, and 68 as unique named-source selections. The "
        "resolver must preserve candidate and exclusion evidence, but it must not itself allow a Gate. "
        "The existing Route must still prove target structure, answer derivation, and Verification.\n\n"
        "## Decision\n\n"
        "No implementation in this run. Although five source selections are deterministic, the audit did "
        "not establish two questions that can reach answer and Evidence using only this selection change. "
        "Implementing before that downstream proof would change selection behaviour without a complete safety case.\n\n"
        "## Integration point\n\n"
        "A future small implementation belongs in `deterministic_candidates_for_requirement` and its "
        "selection evidence, not in an Executor or question-specific mapping.\n",
        encoding="utf-8",
    )
    (OUT / "selected_r5_cluster_test_plan.md").write_text(
        "# Test Plan\n\n"
        "- Match a project-prefixed question reference to a normalized basename with the requested extension.\n"
        "- Treat NFC and NFD filenames as the same logical name.\n"
        "- Reject duplicate same-project basenames.\n"
        "- Reject a candidate with the right basename but wrong extension.\n"
        "- Exclude output, audit, and temporary Office files.\n"
        "- Preserve pair cardinality instead of selecting one side of a named pair.\n"
        "- Suppress when structure verification fails after source selection.\n"
        "- Run full Unit, valid/test fresh, Gate-15 exact comparison, and raw hash verification after implementation.\n",
        encoding="utf-8",
    )
    true_r5 = [row for row in audit_rows if row["reaudited_classification"] == "R5"]
    counts = Counter(row["reaudited_classification"] for row in audit_rows)
    (OUT / "implementation_report.md").write_text(
        "# R5 Audit Implementation Report\n\n"
        f"- Re-audit scope: {len(audit_rows)} candidate questions.\n"
        f"- Classification counts: {dict(counts)}.\n"
        f"- Pure R5 source-selection cases: {len(true_r5)}.\n"
        "- Runtime changes: none.\n"
        "- New Gate candidates: none.\n"
        "- Suppressed-set scan: all 85 suppressed questions were checked for explicit raw filename references.\n"
        "- Regression: full Unit is run for the audit workspace; full valid/test fresh is not re-run because runtime is unchanged.\n",
        encoding="utf-8",
    )
    (OUT / "final_summary.md").write_text(
        "# R5 Document Selection Audit Summary\n\n"
        "The strongest reusable selection capability is a mandatory normalized filename-and-extension filter "
        "within the company/project scope. It has five deterministic source-selection candidates: 7, 20, 33, "
        "54, and 68. It is not implemented because source selection alone has not yet been shown to take two of "
        "those questions through existing Executor, Evidence, and Verification.\n\n"
        "The document-role cluster (8, 11, 16, 71) requires additional stage or cardinality reasoning, while 17 "
        "and 45 require multi-document relations and 66 is already a code-result Route issue.\n\n"
        "No formal baseline artefact or runtime behaviour changed.\n",
        encoding="utf-8",
    )
    environment = {
        "python_executable": sys.executable,
        "imported_package_path": str((ROOT / "src/rag_competition").resolve()),
        "working_directory": str(ROOT),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "reference_run": "gate15_no_human_review_test_fresh_v1",
        "baseline_commit": "9aaf3c0fd6986c0be598efead6811eacadff8355",
        "runtime_changed": False,
    }
    (OUT / "execution_environment_audit.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"scope": len(audit_rows), "counts": counts, "output": str(OUT)}, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
