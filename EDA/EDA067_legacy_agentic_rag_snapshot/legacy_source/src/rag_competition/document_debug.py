from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from .extraction_spec import build_extraction_spec
from .question_conditioned_extractor import _identifier_match, _iter_structure, _format_matches
from .schemas import FileRecord, ExtractionResult


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _raw_office_summary(path: Path) -> dict[str, Any]:
    summary = {"source_path": path.as_posix(), "raw_element_location": [], "raw_explicit_format": {}, "raw_style_reference": [], "raw_inherited_format": {}, "xml_readable": False}
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            summary["xml_readable"] = True
            relevant = [name for name in names if name.endswith("document.xml") or "/slides/slide" in name or name.endswith("styles.xml") or name.endswith("theme1.xml") or name.endswith("comments.xml")]
            summary["raw_element_location"] = relevant[:100]
            text = "\n".join(archive.read(name).decode("utf-8", errors="ignore") for name in relevant)
            summary["raw_explicit_format"] = {"bold_tags": text.count("<w:b"), "italic_tags": text.count("<w:i"), "underline_tags": text.count("<w:u"), "highlight_tags": text.count("highlight"), "color_tags": text.count("color"), "solid_fill_tags": text.count("solidFill"), "scheme_color_tags": text.count("schemeClr"), "rgb_color_tags": text.count("srgbClr")}
            summary["raw_style_reference"] = [token for token in ("styles.xml", "theme1.xml", "slideLayouts", "slideMasters") if token in "\n".join(names)]
    except (OSError, zipfile.BadZipFile):
        pass
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose document extraction without changing formal pipeline inputs.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--split", choices=["valid", "test"], default="valid")
    parser.add_argument("--subtype", default="")
    parser.add_argument("--failure-stage", default="")
    parser.add_argument("--question-id", action="append", type=int, default=[])
    args = parser.parse_args()
    root = Path.cwd()
    run_dir = root / "data" / "work" / args.run_id
    output_dir = root / "data" / "output" / args.run_id
    analysis_dir = output_dir / "analysis"
    debug_dir = output_dir / "document_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = _load_csv(analysis_dir / "document_question_diagnostics.csv")
    selected = [row for row in diagnostics if (not args.subtype or args.subtype in row.get("subtype", "")) and (not args.failure_stage or row.get("failure_stage") == args.failure_stage) and (not args.question_id or int(row["question_id"]) in args.question_id)]
    files = {row["file_id"]: FileRecord(**row) for row in _jsonl(run_dir / "inventory" / "file_records.jsonl")}
    extraction = {row["file_id"]: ExtractionResult(**row) for row in _jsonl(run_dir / "extracted" / "extraction_results.jsonl")}
    questions = {int(row["index"]): row["question_original"] for row in _jsonl(run_dir / "planning" / "question_analysis.jsonl")}
    traces: list[dict[str, Any]] = []
    raw_comparison: list[dict[str, Any]] = []
    identifier_comparison: list[dict[str, Any]] = []
    gate_details: list[dict[str, Any]] = []
    for row in selected:
        qid = int(row["question_id"]); question = questions.get(qid, row.get("question", "")); spec = build_extraction_spec(question)
        actual_ids = [value for value in row.get("actual_used_file_ids", "").split(" | ") if value]
        candidates = []
        for file_id in actual_ids:
            result = extraction.get(file_id)
            if not result: continue
            structure_path = Path(result.extracted_path); structure_path = structure_path if structure_path.is_absolute() else root / structure_path
            try: structure = json.loads(structure_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): structure = {}
            file = files[file_id]
            ir_items = _iter_structure(file, structure)
            candidates.extend(ir_items)
            raw_summary = _raw_office_summary(root / file.raw_path)
            if spec.format_conditions and any(value is not None for value in spec.format_conditions.values()):
                for item in ir_items:
                    match, actual = _format_matches(item, spec.format_conditions)
                    raw_comparison.append({"question_id": qid, "file_id": file_id, "source_path": file.raw_path, "raw_element_location": json.dumps(raw_summary["raw_element_location"], ensure_ascii=False), "text": item.get("text", ""), "raw_explicit_format": json.dumps(raw_summary["raw_explicit_format"], ensure_ascii=False), "raw_style_reference": json.dumps(raw_summary["raw_style_reference"], ensure_ascii=False), "raw_inherited_format": json.dumps({key: item.get("actual_format_values", {}).get(f"{key}_source", "unknown") for key in ("bold", "italic", "underline")}, ensure_ascii=False), "computed_effective_format": json.dumps(item.get("actual_format_values", {}), ensure_ascii=False), "document_ir_format": json.dumps(item.get("actual_format_values", {}), ensure_ascii=False), "normalization_result": "ok", "match_result": match, "mismatch_reason": "" if match else "condition mismatch"})
            for identifier in spec.identifier_terms:
                for item in ir_items:
                    identifier_comparison.append({"question_id": qid, "question_identifier_raw": identifier, "question_identifier_normalized": identifier, "document_identifier_raw": item.get("text", ""), "document_identifier_normalized": item.get("normalized_text", ""), "source_location": json.dumps(item.get("location", {}), ensure_ascii=False), "boundary_match": _identifier_match(item.get("text", ""), identifier), "exact_match": identifier == item.get("text", ""), "normalized_match": identifier in item.get("normalized_text", "")})
        traces.append({"question_id": qid, "question": question, "subtype": row.get("subtype", ""), "failure_stage": row.get("failure_stage", ""), "selected_candidate_files": row.get("selected_candidate_file_ids", ""), "actual_used_files": row.get("actual_used_file_ids", ""), "document_role": ";".join(files[file_id].document_kind for file_id in actual_ids if file_id in files), "file_selection_reason": row.get("file_selection_status", ""), "extraction_spec": row.get("extraction_spec", ""), "search_terms": spec.search_terms, "identifier_terms": spec.identifier_terms, "format_conditions": spec.format_conditions, "selection_mode": spec.selection_mode, "output_scope": spec.output_scope, "exclude_conditions": spec.exclude_conditions, "raw_element_count": len(candidates), "document_ir_element_count": len(candidates), "raw_matching_elements": row.get("raw_candidate_count", ""), "ir_matching_elements": row.get("raw_candidate_count", ""), "reconstructed_items": row.get("reconstructed_item_count", ""), "verification_result": row.get("verification_status", ""), "gate_result": row.get("answer_gate_status", ""), "suppression_reason": row.get("suppression_reason", "")})
        gate_details.append({"question_id": qid, "candidate_count": row.get("raw_candidate_count", ""), "reconstructed_item_count": row.get("reconstructed_item_count", ""), "candidate_texts": "", "source_locations": "", "presence": row.get("verification_presence", ""), "condition_match": row.get("verification_condition_match", ""), "exclusion_match": row.get("verification_exclusion_match", ""), "location_match": row.get("verification_location_match", ""), "completeness": row.get("verification_completeness", ""), "uniqueness": row.get("verification_uniqueness", ""), "verbatim_match": row.get("verification_verbatim_match", ""), "required_gate_conditions": "", "failed_gate_conditions": row.get("failure_stage", ""), "suppression_reason": row.get("suppression_reason", "")})
    _write_jsonl(debug_dir / "question_trace.jsonl", traces)
    _write_jsonl(debug_dir / "raw_structure_trace.jsonl", raw_comparison)
    _write_jsonl(debug_dir / "document_ir_trace.jsonl", raw_comparison)
    _write_jsonl(debug_dir / "extraction_trace.jsonl", traces)
    _write_jsonl(debug_dir / "verification_trace.jsonl", gate_details)
    _write_jsonl(debug_dir / "gate_trace.jsonl", gate_details)
    fields = list(raw_comparison[0].keys()) if raw_comparison else ["question_id"]
    with (debug_dir / "raw_format_ir_comparison.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(raw_comparison)
    fields = list(identifier_comparison[0].keys()) if identifier_comparison else ["question_id"]
    with (debug_dir / "identifier_normalization_comparison.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(identifier_comparison)
    fields = list(gate_details[0].keys()) if gate_details else ["question_id"]
    with (debug_dir / "gate_failure_details.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(gate_details)
    (debug_dir / "document_debug_report.md").write_text("# Document Debug Report\n\n" + json.dumps({"run_id": args.run_id, "split": args.split, "question_count": len(selected), "failure_stage_counts": dict(Counter(row.get("failure_stage", "") for row in selected))}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
