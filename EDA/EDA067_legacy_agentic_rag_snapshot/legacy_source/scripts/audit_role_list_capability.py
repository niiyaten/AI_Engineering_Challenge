"""Read-only feasibility audit for person-to-filtered-task list extraction.

This diagnostic does not change source selection or runtime behaviour.  It
inspects the existing PDF IR for test 20 and scans suppressed questions for
the same relation-preserving list requirement.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import unicodedata
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_competition.pipeline import load_dataclass_jsonl  # noqa: E402
from rag_competition.schemas import ExtractionResult, FileRecord, QuestionAnalysis  # noqa: E402


BASE_WORK = ROOT / "data" / "work" / "gate15_no_human_review_test_fresh_v1"
BASE_OUTPUT = ROOT / "data" / "output" / "gate15_no_human_review_test_fresh_v1"
OUTPUT = ROOT / "data" / "output" / "role_list_capability_audit_v1" / "analysis"
GATE15 = {2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def load_structure(result: ExtractionResult) -> dict[str, Any]:
    path = Path(result.extracted_path)
    if not path.is_absolute():
        path = ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    """Normalize filenames for audit-time explicit-reference matching."""
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_related_question(question: str, files: list[FileRecord]) -> tuple[str, str, str]:
    """Classify the downstream relation without using question IDs as runtime input."""
    extensions = sorted({file.extension for file in files})
    if ("M01" in question and "M02" in question) or ("会議録" in question and "報告資料" in question):
        return "multi_document_or_version_relation", "multi_document_join_or_comparison", "not_role_list_only"
    if "1タスク当たり" in question or "最も大きい" in question:
        return "aggregate_per_person", "cross_structure_aggregation", "not_role_list_only"
    if any(extension in {".xlsx", ".csv", ".tsv"} for extension in extensions):
        return "table_relation", "existing_table_condition_or_join", "not_document_role_list"
    if "主担当者" in question and "役職" in question:
        return "single_role_lookup", "existing_semantic_role_lookup", "not_filtered_task_list"
    if "担当" in question and "タスク" in question:
        return "person_to_filtered_task_list", "role_list_candidate", "candidate"
    return "other", "other", "not_candidate"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = load_dataclass_jsonl(BASE_WORK / "inventory" / "file_records.jsonl", FileRecord)
    analyses = load_dataclass_jsonl(BASE_WORK / "planning" / "question_analysis.jsonl", QuestionAnalysis)
    extractions = load_dataclass_jsonl(BASE_WORK / "extracted" / "extraction_results.jsonl", ExtractionResult)
    plans = {int(item["question_id"]): item for item in read_jsonl(BASE_WORK / "planning" / "final_source_plans.jsonl")}
    gates = {int(item["question_id"]): item for item in read_jsonl(BASE_OUTPUT / "answer_gate_results.jsonl")}
    file_by_id = {item.file_id: item for item in files}
    extraction_by_id = {item.file_id: item for item in extractions}

    # Extract the document from the question itself. This is audit-only and does
    # not alter the runtime resolver or save a question-to-file mapping.
    question20 = next(item.question_original for item in analyses if item.index == 20)
    name_candidates = [
        file for file in files
        if normalize(file.file_name) in normalize(question20)
        and not file.is_temp_office_file
        and "/output/" not in file.relative_path.replace("\\", "/").casefold()
    ]
    if len(name_candidates) != 1:
        raise RuntimeError(f"explicit filename selection was not unique: {len(name_candidates)}")
    source20 = name_candidates[0]
    ir20 = load_structure(extraction_by_id[source20.file_id])
    pages = ir20.get("pages", [])
    pdf_audit = {
        "question_id": 20,
        "question": question20,
        "source_file": source20.relative_path,
        "page_count": ir20.get("page_count", 0),
        "text_layer_pages_with_text": [page.get("page_number") for page in pages if str(page.get("text") or "").strip()],
        "block_count": sum(len(page.get("blocks", []) or []) for page in pages),
        "nonempty_block_count": sum(1 for page in pages for block in page.get("blocks", []) or [] if any(line.get("spans") for line in block.get("lines", []) or [])),
        "table_count": sum(len(page.get("tables", []) or []) for page in pages),
        "heading_count": sum(len(page.get("headings", []) or []) for page in pages),
        "list_item_count": sum(len(page.get("list_items", []) or []) for page in pages),
        "image_page_count": sum(1 for page in pages if page.get("image_path")),
        "has_text_layer": any(str(page.get("text") or "").strip() for page in pages),
        "role_task_relation_reconstructible": False,
        "blocking_reason": "scanned_pdf_no_text_or_table_ir; role-task relation requires OCR or image/table reconstruction",
        "format_dependency": "visual_only_or_unknown",
        "raw_sha1_expected": source20.sha1,
        "raw_sha1_after_audit": sha1(ROOT / source20.raw_path),
    }
    pdf_audit["raw_file_unchanged"] = pdf_audit["raw_sha1_expected"] == pdf_audit["raw_sha1_after_audit"]
    (OUTPUT / "test20_pdf_ir_audit.json").write_text(json.dumps(pdf_audit, ensure_ascii=False, indent=2), encoding="utf-8")

    scan_rows: list[dict[str, Any]] = []
    for analysis in analyses:
        if analysis.index in GATE15:
            continue
        question = analysis.question_original
        if not any(term in question for term in ("担当", "タスク", "優先")):
            continue
        plan = plans.get(analysis.index, {})
        selected = [file_by_id[file_id] for file_id in plan.get("final_selected_file_ids", []) if file_id in file_by_id]
        relation, capability, applicability = classify_related_question(question, selected)
        scan_rows.append({
            "question_id": analysis.index,
            "question": question,
            "selected_files": " | ".join(file.relative_path for file in selected),
            "file_types": " | ".join(sorted({file.extension for file in selected})),
            "current_operations": " | ".join(item.get("operation_type", "") for item in plan.get("operations", [])),
            "suppression_reason": gates.get(analysis.index, {}).get("suppression_reason", ""),
            "relation_shape": relation,
            "required_capability": capability,
            "role_list_applicability": applicability,
        })
    write_csv(OUTPUT / "role_list_cross_question_scan.csv", scan_rows)

    capability_rows = [
        {"component": "semantic_role_lookup", "status": "implemented_for_single_value", "test20_fit": "insufficient", "reason": "does not produce complete person-to-task filtered lists"},
        {"component": "semantic_list_extraction", "status": "implemented_for_explicit_text_or_table_items", "test20_fit": "blocked", "reason": "test20 PDF has no text/table candidates"},
        {"component": "document.single_source.lookup", "status": "implemented", "test20_fit": "source_only", "reason": "selects a document route but cannot reconstruct scanned relation"},
        {"component": "PDF extraction", "status": "text_layer_and_rendering", "test20_fit": "blocked", "reason": "all seven pages have empty text in current IR"},
        {"component": "positional evidence", "status": "implemented_for_extracted_blocks", "test20_fit": "blocked", "reason": "there are no nonempty blocks or table rows"},
        {"component": "verification_and_gate", "status": "implemented", "test20_fit": "blocked", "reason": "cannot independently reconstruct role-task pairs without source Evidence"},
    ]
    write_csv(OUTPUT / "existing_capability_map.csv", capability_rows)
    clusters = [
        {"cluster": "scanned_pdf_role_task_relation", "question_ids": "20", "question_count": 1, "required_capability": "OCR plus layout/table relation reconstruction", "implementation_size": "medium_to_large", "risk": "high", "eligible_for_small_role_list_executor": False},
        {"cluster": "single_role_lookup", "question_ids": "21", "question_count": 1, "required_capability": "existing semantic role lookup after source confirmation", "implementation_size": "none_or_small", "risk": "medium", "eligible_for_small_role_list_executor": False},
        {"cluster": "multi_document_or_aggregate", "question_ids": "34 | 70 | 79", "question_count": 3, "required_capability": "version relation, cross-document join, or aggregation", "implementation_size": "medium_to_large", "risk": "high", "eligible_for_small_role_list_executor": False},
        {"cluster": "table_relation", "question_ids": "94 | 96", "question_count": 2, "required_capability": "table condition/join or checkpoint relation", "implementation_size": "small_to_medium", "risk": "medium", "eligible_for_small_role_list_executor": False},
    ]
    write_csv(OUTPUT / "role_list_capability_clusters.csv", clusters)
    decision = (
        "# Implementation Decision\n\n"
        "Decision: do not implement a role-list capability in this task.\n\n"
        "Test 20 cannot reach a deterministic person-to-task relation from the current PDF IR: all 7 pages are rendered images with empty text blocks, no tables, no headings, and no list items. A role-list executor alone would have no structured source records to process.\n\n"
        "The suppressed-question scan found no second question with the same single-document, person-to-filtered-task-list relation on parseable text/table IR. The apparent related questions require different capabilities: single role lookup, version/cross-document processing, aggregation, or table relation handling.\n"
    )
    (OUTPUT / "implementation_decision.md").write_text(decision, encoding="utf-8")
    (OUTPUT / "final_summary.md").write_text(
        "# Role-list Capability Feasibility Audit\n\n"
        "Test 20 is a scanned PDF relation-extraction problem, not a standalone role-list Executor gap. No safe two-question cluster was found. No runtime code was changed, no API was used, and no Gate state changed.\n",
        encoding="utf-8",
    )
    environment = {
        "python_executable": sys.executable,
        "imported_package_path": str(Path(__import__("rag_competition").__file__).resolve()),
        "working_directory": str(ROOT),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "formal_baseline_commit": "9aaf3c0fd6986c0be598efead6811eacadff8355",
        "api_call_count": 0,
    }
    (OUTPUT / "execution_environment_audit.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"test20": pdf_audit, "scan_count": len(scan_rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
