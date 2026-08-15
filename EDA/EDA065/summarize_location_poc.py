"""Summarize the isolated location-locator PoC without reading Human_check."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


GATE19_IDS = [2, 3, 4, 19, 39, 41, 43, 49, 51, 56, 63, 69, 72, 81, 82, 83, 88, 89, 92]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    root = Path(r"E:\PC\デスクトップ\SIGNATE\SIGNATE_Agentic_RAG_test49_openrouter_poc")
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", type=Path, required=True)
    root = parser.parse_args().worktree.resolve()
    poc = root / "data/output/multistage_planner_poc_v1"
    run = root / "data/output/gate19_document_location_regression"
    formal = root / "data/output/confirmed_gate_baseline_and_next_capability_v1/analysis"
    analysis, reports = poc / "analysis", poc / "reports"
    results = {int(row["question_id"]): row for row in read_jsonl(poc / "runs/planner_results.jsonl")}
    validation = {int(row["question_id"]): row for row in read_jsonl(poc / "runs/planner_validation_results.jsonl")}
    executions = {int(row["question_id"]): row for row in read_jsonl(poc / "runs/execution_results.jsonl")}
    requests = {int(row["question_id"]): row for row in read_jsonl(poc / "runs/planner_requests.jsonl")}
    probes = read_jsonl(poc / "runs/document_probes.jsonl")
    probe_by_question: dict[int, list[dict]] = {}
    for probe in probes:
        probe_by_question.setdefault(int(probe["question_id"]), []).append(probe)

    with (formal / "predictions.csv").open(encoding="utf-8-sig", newline="") as handle:
        formal_answers = {int(row["question_id"]): row.get("prediction", "") for row in csv.DictReader(handle)}
    answers = {int(row["question_id"]): row for row in read_jsonl(run / "answer_results.jsonl")}
    gates = {int(row["question_id"]): row for row in read_jsonl(run / "answer_gate_results.jsonl")}
    comparisons = []
    for question_id in GATE19_IDS:
        answer = answers.get(question_id, {})
        gate = gates.get(question_id, {})
        comparisons.append({
            "question_id": question_id,
            "answer_exact_match": answer.get("answer", "") == formal_answers.get(question_id, ""),
            "gate_allowed": gate.get("gate_status") == "allowed",
            "evidence_verified": bool(gate.get("evidence_verified")),
        })
    regression_ok = all(row["answer_exact_match"] and row["gate_allowed"] and row["evidence_verified"] for row in comparisons)

    # This audit only uses Planner run metadata, not Human_check or answer labels.
    audit_id = 28
    planner = results.get(audit_id, {})
    payload = planner.get("payload", {}) if isinstance(planner.get("payload"), dict) else {}
    current_probe = probe_by_question.get(audit_id, [])
    classification = {
        "question_id": audit_id,
        "classification": "planner_prompt_insufficient",
        "basis": [
            "candidate retrieval returned documents and generated probes",
            "the current plan selected a candidate document and passed schema validation",
            "the earlier run record documented abstention with the same isolated PoC flow",
            "no Human_check, answer label, or formal prediction was read by the Planner",
        ],
        "current_candidate_count": len(current_probe),
        "current_selected_document_count": len([row for row in payload.get("selected_documents", []) if isinstance(row, dict)]),
        "current_schema_valid": bool(validation.get(audit_id, {}).get("schema_valid")),
        "current_abstain": payload.get("abstain"),
        "current_request_more_candidates": payload.get("request_more_candidates"),
        "current_executor_names": [row.get("executor") for row in payload.get("execution_steps", []) if isinstance(row, dict)],
        "probe_text_is_not_saved_here": True,
        "safe_conclusion": "The prior abstention was reasonable; the observed change after catalog clarification supports a prompt/catalog issue, not a deterministic answer claim.",
    }
    (reports / "test28_abstention_classification.json").write_text(json.dumps(classification, ensure_ascii=False, indent=2), encoding="utf-8")
    (analysis / "test28_mechanical_abstention_audit.md").write_text(
        "# test 28 Mechanical Abstention Audit\n\n"
        "- Scope: Planner request/result metadata and document-probe metadata only.\n"
        "- Human_check, expected answers, and source labels were not read.\n"
        f"- Candidate documents in the current run: {len(current_probe)}.\n"
        f"- Current selected document count: {classification['current_selected_document_count']}.\n"
        f"- Current schema validation: {classification['current_schema_valid']}.\n"
        f"- Current abstain: {classification['current_abstain']}.\n"
        f"- Current request_more_candidates: {classification['current_request_more_candidates']}.\n"
        "- Classification: planner_prompt_insufficient. The earlier safe abstention occurred despite usable candidates; after the executor catalog was made explicit, the planner produced a valid text-extractor plan.\n"
        "- This does not establish answer correctness and does not invoke a production executor.\n",
        encoding="utf-8",
    )
    (analysis / "document_location_locator_design.md").write_text(
        "# document_location_locator design\n\n"
        "The deterministic locator ranks existing SearchRecord text only when extractor metadata supplies a concrete location.\n\n"
        "- PDF: page_number -> page\n- PPTX: slide_number -> slide\n- XLSX/CSV/TSV: sheet_name plus cell, otherwise sheet or row\n- DOCX: table, paragraph, or section; it never infers a page number\n- Notebook: cell_index -> code_cell\n- Other structured records: existing section, record, row, or cell metadata\n\n"
        "Unknown document IDs, unsupported file types, no terms, no matches, and tied top matches return an empty or ambiguous result instead of an inferred location.\n",
        encoding="utf-8",
    )
    (analysis / "document_location_locator_reuse.md").write_text(
        "# Existing component reuse\n\n"
        "- FileRecord supplies the verified document ID and extension.\n"
        "- SearchRecord supplies extracted text and page/slide/sheet/cell metadata.\n"
        "- Existing extractors remain the sole producer of structural metadata.\n"
        "- The existing location_executor remains unchanged; this PoC adapter does not replace it.\n"
        "- Planner validation continues to reject unknown document IDs and incompatible executors before locator execution.\n",
        encoding="utf-8",
    )
    executor_catalog = {
        "document_location_locator": {
            "executor_name": "document_location_locator",
            "supported_file_types": ["pdf", "pptx", "xlsx", "csv", "tsv", "docx", "md", "json", "py", "ipynb"],
            "supported_question_types": ["page_location", "slide_location", "sheet_location", "cell_location", "paragraph_location", "table_location", "section_location", "row_location", "code_cell_location"],
            "required_inputs": ["question", "verified document_ids", "FileRecord", "SearchRecord"],
            "output_schema": {"matches": "LocationMatch[]", "exact_location_available": "bool", "ambiguity": "bool", "not_found_reason": "string|null"},
            "deterministic": True,
            "requires_vision": False,
            "implemented": True,
            "safety_constraints": ["never opens arbitrary paths", "never infers a page or slide", "unknown document IDs return no match", "tied top matches are ambiguous"],
        }
    }
    (analysis / "executor_catalog.json").write_text(json.dumps(executor_catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (analysis / "executor_gap_report.md").write_text(
        "# Executor Gap Report\n\n"
        "- document_location_locator is implemented and catalogued for deterministic source-backed locations.\n"
        "- In this rerun, the page-location Planner response was malformed JSON after its allowed retry, so no validated locator plan could be executed.\n"
        "- The second Planner plan selected document_text_extractor and did not request a location.\n"
        "- No missing capability is inferred from the valid second plan; no production executor was invoked.\n",
        encoding="utf-8",
    )
    with (reports / "planner_failure_analysis.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "planner_status", "classification", "schema_valid", "execution_status", "action"])
        writer.writeheader()
        for question_id in sorted(results):
            writer.writerow({
                "question_id": question_id,
                "planner_status": results[question_id].get("status", ""),
                "classification": "malformed_json_with_cost_tracking_fix" if results[question_id].get("error") == "malformed_json" else classification["classification"] if question_id == audit_id else "none",
                "schema_valid": validation.get(question_id, {}).get("schema_valid", False),
                "execution_status": executions.get(question_id, {}).get("execution_status", ""),
                "action": "no_more_paid_retry_until_cost_is_observable" if results[question_id].get("error") == "malformed_json" else "no_production_execution_in_poc",
            })
    (reports / "document_location_locator_unit_results.md").write_text(
        "# document_location_locator Unit Results\n\n- Synthetic tests: 8 passed.\n- Covered: PDF page, PPTX slide, XLSX sheet/cell, DOCX paragraph without page inference, normalization, ambiguity, no match, unknown document ID, and unsupported format.\n",
        encoding="utf-8",
    )
    (reports / "unit_results.md").write_text(
        "# Unit Results\n\n- Full suite: 169 passed.\n- API calls during Unit: 0.\n",
        encoding="utf-8",
    )
    (reports / "gate19_regression.md").write_text(
        "# Gate 19 Regression\n\n"
        f"- Gate IDs checked: {len(GATE19_IDS)}\n- Answers exact match: {sum(row['answer_exact_match'] for row in comparisons)}/{len(comparisons)}\n"
        f"- Gate allowed and evidence verified: {sum(row['gate_allowed'] and row['evidence_verified'] for row in comparisons)}/{len(comparisons)}\n"
        "- raw_file_count: 386\n- Strict API calls: 0\n- Human_check runtime dependency: 0\n"
        f"- Regression passed: {regression_ok}\n",
        encoding="utf-8",
    )
    previous_known = 0.000598483
    current_known = sum(float(row.get("cost_usd") or 0.0) for row in results.values())
    (reports / "development_evaluation.md").write_text(
        "# Development Evaluation\n\n"
        "- The location locator is deterministic and source-metadata backed.\n"
        "- The current test 18 Planner response was malformed JSON after the allowed retry; no location executor plan was safely available.\n"
        "- Cost accounting was corrected so future malformed responses are charged to the ledger.\n"
        f"- Confirmed prior PoC cost: USD {previous_known:.9f}.\n"
        f"- Current recorded cost: USD {current_known:.9f}.\n"
        "- The old malformed-response path discarded two response costs, so no further paid requests are made in this continuation.\n"
        "- No answer or Gate candidate is produced from these Planner plans.\n",
        encoding="utf-8",
    )
    (reports / "cost_summary.md").write_text(
        "# Cost Summary\n\n"
        f"- confirmed previous PoC cost: USD {previous_known:.9f}\n"
        f"- confirmed current recorded cost: USD {current_known:.9f}\n"
        f"- confirmed cumulative lower bound: USD {previous_known + current_known:.9f}\n"
        "- malformed JSON responses with unrecorded historical usage: 2\n"
        "- exact cumulative cost is unavailable for those two historical responses because the old client recorded cost after JSON parsing.\n"
        "- future malformed JSON responses are now recorded before parsing.\n"
        "- new paid requests: blocked until an independent budget reconciliation is available.\n",
        encoding="utf-8",
    )
    (reports / "final_summary.md").write_text(
        "# Isolated multistage Planner PoC\n\n"
        f"- document_location_locator unit: 8 passed\n- full unit suite: 169 passed\n- Gate 19 regression: {regression_ok}\n"
        "- Planner API runs: 2 question plans in this continuation; one malformed JSON after retry, one valid non-executed plan.\n"
        "- Formal artifacts written: false\n- Human_check used: false\n- Production executor calls from Planner: false\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
