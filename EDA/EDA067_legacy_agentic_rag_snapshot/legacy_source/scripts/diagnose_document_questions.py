from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rag_competition.extraction_spec import build_extraction_spec
from rag_competition.question_conditioned_extractor import _iter_structure
from rag_competition.schemas import ExtractionResult, FileRecord


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analysis_rows = {int(row["question_id"]): row for row in csv.DictReader((args.output_dir / "document_slice_questions.csv").open(encoding="utf-8-sig"))}
    plans = {int(row["question_id"]): row for row in jsonl(args.run_dir / "planning" / "final_source_plans.jsonl")}
    answers = {int(row["question_id"]): row for row in jsonl(args.run_dir.parent.parent / "output" / args.run_dir.name / "answer_results.jsonl")}
    specs = {int(row["question_id"]): row for row in jsonl(args.run_dir / "document_extraction" / "extraction_specs.jsonl") if row.get("question_id") is not None}
    candidates = jsonl(args.run_dir / "document_extraction" / "extraction_candidates.jsonl")
    reconstructions = jsonl(args.run_dir / "document_extraction" / "reconstructed_items.jsonl")
    verifications = {int(row["question_id"]): row for row in jsonl(args.run_dir / "document_extraction" / "document_verification.jsonl") if row.get("question_id") is not None}
    inventory = {row.file_id: row for row in (FileRecord(**json.loads(line)) for line in (args.run_dir / "inventory" / "file_records.jsonl").open(encoding="utf-8") if line.strip())}
    extraction_rows = {row.file_id: row for row in (ExtractionResult(**json.loads(line)) for line in (args.run_dir / "extracted" / "extraction_results.jsonl").open(encoding="utf-8") if line.strip())}
    fields = ["question_id", "question", "subtype", "question_analysis_status", "selected_candidate_file_ids", "selected_candidate_paths", "actual_used_file_ids", "actual_used_paths", "file_selection_status", "extraction_spec_status", "extraction_spec", "document_ir_status", "document_ir_element_count", "search_term_count", "identifier_term_count", "search_term_match_count", "identifier_match_count", "format_condition_count", "format_match_count", "raw_candidate_count", "reconstructed_item_count", "verification_presence", "verification_condition_match", "verification_exclusion_match", "verification_location_match", "verification_completeness", "verification_uniqueness", "verification_verbatim_match", "verification_status", "answer_gate_status", "suppression_reason", "failure_stage", "warnings", "errors"]
    output: list[dict] = []
    for question_id, row in sorted(analysis_rows.items()):
        plan = plans.get(question_id, {}); answer = answers.get(question_id, {})
        spec_row = specs.get(question_id, {}); spec = spec_row.get("spec") or build_extraction_spec(row["question"]).to_dict()
        selected_ids = [str(value) for value in plan.get("final_selected_file_ids", [])]
        actual_ids = [str(value) for value in answer.get("selected_file_ids", [])]
        selected_paths = [inventory[file_id].raw_path for file_id in selected_ids if file_id in inventory]
        actual_paths = [inventory[file_id].raw_path for file_id in actual_ids if file_id in inventory]
        ir_count = 0
        for file_id in actual_ids or selected_ids:
            extraction = extraction_rows.get(file_id)
            if not extraction: continue
            path = Path(extraction.extracted_path); path = path if path.is_absolute() else args.run_dir.parent.parent.parent / path
            try:
                structure = json.loads(path.read_text(encoding="utf-8")); ir_count += len(_iter_structure(inventory[file_id], structure))
            except (OSError, json.JSONDecodeError, KeyError):
                pass
        cand = [item for item in candidates if item.get("question_id") == question_id]
        recon = [item for item in reconstructions if item.get("question_id") == question_id]
        verification = verifications.get(question_id, {})
        search_matches = sum(len(item.get("matched_search_terms", [])) for item in cand)
        identifier_matches = sum(len(item.get("matched_identifier_terms", [])) for item in cand)
        format_matches = sum(1 for item in cand if item.get("matched_format_conditions"))
        if not selected_ids: stage = "file_selection_failure"
        elif not spec_row and "spec_generation_failure" in " ".join(answer.get("warnings", [])): stage = "extraction_spec_failure"
        elif ir_count == 0: stage = "document_ir_failure"
        elif spec.get("identifier_terms") and identifier_matches == 0: stage = "identifier_no_match"
        elif spec.get("search_terms") and search_matches == 0: stage = "search_term_no_match"
        elif spec.get("format_conditions") and any(value is not None for value in spec["format_conditions"].values()) and format_matches == 0: stage = "format_no_match"
        elif not recon and cand: stage = "reconstruction_failure"
        elif verification.get("verification_status") == "failed":
            stage = "completeness_failure" if verification.get("completeness") is False else "uniqueness_failure" if verification.get("uniqueness") is False else "verbatim_failure" if verification.get("verbatim_match") is False else "verification_failure"
        elif not answer.get("answer"): stage = "answer_gate_failure"
        else: stage = ""
        output.append({"question_id": question_id, "question": row["question"], "subtype": row.get("question_types", ""), "question_analysis_status": "available", "selected_candidate_file_ids": " | ".join(selected_ids), "selected_candidate_paths": " | ".join(selected_paths), "actual_used_file_ids": " | ".join(actual_ids), "actual_used_paths": " | ".join(actual_paths), "file_selection_status": "selected" if selected_ids else "not_found", "extraction_spec_status": "generated" if spec else "failed", "extraction_spec": json.dumps(spec, ensure_ascii=False, sort_keys=True), "document_ir_status": "available" if ir_count else "missing", "document_ir_element_count": ir_count, "search_term_count": len(spec.get("search_terms", [])), "identifier_term_count": len(spec.get("identifier_terms", [])), "search_term_match_count": search_matches, "identifier_match_count": identifier_matches, "format_condition_count": sum(value is not None for value in spec.get("format_conditions", {}).values()), "format_match_count": format_matches, "raw_candidate_count": len(cand), "reconstructed_item_count": len(recon), "verification_presence": verification.get("presence", ""), "verification_condition_match": verification.get("condition_match", ""), "verification_exclusion_match": verification.get("exclusion_match", ""), "verification_location_match": verification.get("location_match", ""), "verification_completeness": verification.get("completeness", ""), "verification_uniqueness": verification.get("uniqueness", ""), "verification_verbatim_match": verification.get("verbatim_match", ""), "verification_status": verification.get("verification_status", ""), "answer_gate_status": answer.get("gate_status", ""), "suppression_reason": answer.get("gate_reason", ""), "failure_stage": stage, "warnings": " | ".join(answer.get("warnings", [])), "errors": " | ".join(answer.get("errors", []))})
    write_csv(args.output_dir / "document_question_diagnostics.csv", output, fields)
    write_csv(args.output_dir / "document_failure_stage_summary.csv", [{"failure_stage": key, "question_count": value} for key, value in sorted(Counter(row["failure_stage"] for row in output).items())], ["failure_stage", "question_count"])
    lines = ["# Document Question Diagnostics", "", f"- question_count: {len(output)}", "", "| question_id | subtype | failure_stage | gate_status | candidates | reconstructed | verification |", "|---:|---|---|---|---:|---:|---|"]
    lines.extend(f"| {row['question_id']} | {row['subtype']} | {row['failure_stage']} | {row['answer_gate_status']} | {row['raw_candidate_count']} | {row['reconstructed_item_count']} | {row['verification_status']} |" for row in output)
    (args.output_dir / "document_question_diagnostics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    diag_dir = args.run_dir / "document_diagnostics"; diag_dir.mkdir(parents=True, exist_ok=True)
    for name in ("document_question_diagnostics",):
        (diag_dir / f"{name}.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in output) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
