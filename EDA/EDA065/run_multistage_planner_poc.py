"""Isolated multistage Planner PoC.

This is an EDA-side runner. It never imports the production pipeline entrypoint,
does not read Human_check, and writes only to the requested PoC output tree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run isolated multistage planner PoC.")
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--max-api-questions", type=int, default=2)
    parser.add_argument("--execute-api", action="store_true")
    parser.add_argument("--planner-mode", choices=("legacy", "minimal"), default="minimal")
    parser.add_argument("--stability-trials", type=int, default=1)
    parser.add_argument("--fallback-offset", type=int, default=0)
    parser.add_argument("--budget-usd", type=float, default=0.02)
    parser.add_argument("--soft-stop-usd", type=float, default=0.01)
    parser.add_argument("--max-cost-per-request-usd", type=float, default=0.01)
    parser.add_argument("--retrieval-top-k", type=int, choices=(5, 10), default=5)
    parser.add_argument("--candidate-document-limit", type=int, default=5)
    return parser.parse_args()


def build_probe(file: dict[str, Any], records: list[Any], question: str) -> dict[str, Any]:
    """Create a compact deterministic document description from already extracted chunks."""
    sample = "\n".join(record.text[:700] for record in records[:3])[:1800]
    metadata = [record.metadata for record in records]
    return {
        "document_id": file["file_id"], "relative_path": file["raw_path"], "file_name": file["file_name"],
        "project_name": file.get("project_name", ""), "file_type": file.get("extension", "").lstrip("."),
        "document_role": file.get("document_kind", "unknown"),
        "slide_or_sheet_locations": [meta.get("slide_number") or meta.get("sheet_name") for meta in metadata[:8] if meta.get("slide_number") or meta.get("sheet_name")],
        "matched_question_terms": [term for term in question.split() if len(term) >= 2 and term in sample][:12],
        "top_text_evidence": sample,
        "structural_features": sorted({record.record_type for record in records}),
        "available_executor_hints": ["pptx_shape_coordinate_extractor" if file.get("extension") == ".pptx" else "xlsx_table_filter" if file.get("extension") == ".xlsx" else "document_text_extractor"],
    }


def planner_prompt(question: str, candidates: list[dict[str, Any]]) -> str:
    """Ask only for document and executor planning; no answer or Human labels are included."""
    schema = {
        "selected_documents": [{"document_id": "string", "role": "primary_source|supporting_source|layout_source", "reason": "string", "confidence": 0.0}],
        "rejected_documents": [{"document_id": "string", "reason": "string"}],
        "question_type": "string", "required_file_types": ["string"], "required_attributes": ["string"],
        "required_capabilities": ["string"], "execution_steps": [{"step": 1, "executor": "string", "document_ids": ["string"], "parameters": {}, "expected_output": "string"}],
        "requires_calculation": False, "requires_vision": False, "request_more_candidates": False,
        "additional_probe_requests": [], "expected_answer_type": "string", "ambiguity": False, "abstain": False, "abstain_reason": None,
    }
    executor_catalog = {
        "document_location_locator": "Use for a requested page, slide, sheet, cell, paragraph, table, section, row, or code-cell location. It returns only extractor-backed locations.",
        "document_text_extractor": "Use for text evidence from DOCX, PDF, Markdown, or text.",
        "xlsx_table_filter": "Use for spreadsheet table or filter operations.",
        "pptx_text_extractor": "Use for slide text evidence.",
        "pptx_shape_coordinate_extractor": "Use for PPTX geometry questions.",
        "python_numeric_calculator": "Use only after source values have been selected.",
    }
    return (
        "Use only supplied candidate document probes. Do not answer the user question. "
        "Return one Japanese JSON object matching the schema. Select only listed document_id values. "
        "If the evidence is insufficient, set abstain=true or request_more_candidates=true. "
        "For a location question, use document_location_locator instead of inventing a page-number executor.\n"
        f"Question: {question}\nExecutor catalog: {json.dumps(executor_catalog, ensure_ascii=False)}\n"
        f"Schema: {json.dumps(schema, ensure_ascii=False)}\nCandidates: {json.dumps(candidates, ensure_ascii=False)}"
    )


EXECUTOR_FILE_TYPES = {
    "document_text_extractor": {"docx", "pdf", "txt", "md"},
    "xlsx_table_filter": {"xlsx", "csv", "tsv"},
    "pptx_text_extractor": {"pptx"},
    "pptx_shape_coordinate_extractor": {"pptx"},
    "document_location_locator": {"docx", "pdf", "pptx", "xlsx", "csv", "tsv", "md", "json", "py", "ipynb"},
    "vision_page_interpreter": {"pptx", "pdf", "png", "jpg", "jpeg"},
    "python_numeric_calculator": set(),
}


def validate_plan(plan: dict[str, Any], candidate_files: list[dict[str, Any]]) -> list[str]:
    """Reject unknown documents, unsupported executors, and file-type mismatches before file access."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["payload_not_object"]
    candidate_ids = {row["document_id"] for row in candidate_files}
    candidate_types = {row["document_id"]: str(row.get("file_type", "")).lower() for row in candidate_files}
    for field in ("request_more_candidates", "abstain", "ambiguity"):
        if field in plan and not isinstance(plan[field], bool):
            errors.append(f"{field}_not_bool")
    selected = plan.get("selected_documents", [])
    if not isinstance(selected, list):
        errors.append("selected_documents_not_list")
        return errors
    for row in selected:
        if not isinstance(row, dict) or str(row.get("document_id", "")) not in candidate_ids:
            errors.append("unknown_selected_document")
    steps = plan.get("execution_steps", [])
    if not isinstance(steps, list):
        errors.append("execution_steps_not_list")
        return list(dict.fromkeys(errors))
    if not steps and not (plan.get("request_more_candidates") or plan.get("abstain")):
        errors.append("missing_execution_steps")
    selected_ids = {str(row.get("document_id", "")) for row in selected if isinstance(row, dict)}
    for step in steps:
        if not isinstance(step, dict) or not step.get("executor"):
            errors.append("invalid_execution_step")
            continue
        executor = str(step["executor"])
        if executor not in EXECUTOR_FILE_TYPES:
            errors.append("unsupported_executor")
            continue
        document_ids = step.get("document_ids", [])
        if not isinstance(document_ids, list):
            errors.append("execution_step_document_ids_not_list")
            continue
        for document_id in map(str, document_ids):
            if document_id not in candidate_ids or document_id not in selected_ids:
                errors.append("execution_step_unknown_document")
                continue
            compatible_types = EXECUTOR_FILE_TYPES[executor]
            if compatible_types and candidate_types.get(document_id) not in compatible_types:
                errors.append("executor_file_type_mismatch")
    return list(dict.fromkeys(errors))


def execution_status(plan: dict[str, Any], validation_errors: list[str]) -> str:
    """Classify a validated plan without invoking a production executor."""
    if validation_errors:
        return "invalid_plan"
    if plan.get("abstain"):
        return "planner_abstained"
    if plan.get("request_more_candidates"):
        return "additional_candidates_requested"
    return "plan_validated_only"


def minimal_probe(file: dict[str, Any], records: list[Any], question: str, expanded_question: str = "") -> dict[str, Any]:
    """質問シグナルに近いSearchRecordだけを既存抽出結果から選ぶ。"""
    from rag_competition.llm.question_aware_probe import build_question_aware_probe

    probe = build_question_aware_probe(file, records, question, expanded_question=expanded_question)
    # Plannerへ渡すprobeは局所Evidenceだけで、raw全文や回答を含めない。
    return probe


def minimal_planner_prompt(question: str, candidates: list[dict[str, Any]], executor_catalog: dict[str, str], schema: dict[str, Any]) -> str:
    """回答や詳細パラメータを求めず、選択だけを求める短いPoCプロンプト。"""
    return (
        "Return JSON only. Do not answer the question and do not create execution parameters. "
        "Choose only candidate document IDs and one registered executor. "
        "If action is execute, provide at least one document ID and one executor. "
        "If action is request_more_candidates or abstain, executor must be null. "
        "If evidence is insufficient choose request_more_candidates or abstain.\n"
        f"Question: {question}\n"
        "Fallback reason: deterministic source selection did not produce a safe unique source.\n"
        f"Candidates: {json.dumps(candidates, ensure_ascii=False)}\n"
        f"Executors: {json.dumps(executor_catalog, ensure_ascii=False)}\n"
        f"Required JSON schema: {json.dumps(schema, ensure_ascii=False)}"
    )


def planner_probe_view(probe: dict[str, Any]) -> dict[str, Any]:
    """API入力は上位局所Evidenceだけへさらに圧縮し、資料全文化を防ぐ。"""
    snippets = []
    for item in probe.get("evidence_snippets", [])[:2]:
        snippets.append({
            "text": str(item.get("text", ""))[:350],
            "location_type": item.get("location_type"),
            "location": item.get("location"),
            "matched_terms": item.get("matched_terms", [])[:10],
            "table_headers": item.get("table_headers", [])[:10],
        })
    return {
        "document_id": probe["document_id"], "file_name": probe["file_name"],
        "file_type": probe["file_type"], "project_name": probe.get("project_name"),
        "document_title": probe.get("document_title"), "query_signals": probe.get("query_signals", {}),
        "evidence_snippets": snippets, "evidence_density": probe.get("evidence_density", 0.0),
        "location_metadata_available": probe.get("location_metadata_available", False),
        "structural_attributes": probe.get("structural_attributes", []),
    }


def main() -> None:
    args = parse_args()
    root = args.worktree.resolve()
    sys.path.insert(0, str(root / "src"))
    from rag_competition.llm.cache import CandidateCache
    from rag_competition.llm.company_retrieval import CompanyScopedRetriever
    from rag_competition.llm.config import CandidateModeConfig
    from rag_competition.llm.model_registry import choose_low_cost_model
    from rag_competition.llm.minimal_planner import MINIMAL_PLANNER_SCHEMA, build_execution_plan, validate_minimal_plan
    from rag_competition.llm.openrouter_client import OpenRouterCandidateClient
    from rag_competition.document_location_locator import locate_document_content
    from rag_competition.schemas import FileRecord, SearchRecord

    run = root / "data/work/gate19_test100_final_candidate"
    out = root / "data/output/multistage_planner_poc_v1"
    analysis_dir, runs_dir, reports_dir = out / "analysis", out / "runs", out / "reports"
    for directory in (analysis_dir, runs_dir, reports_dir, out / "fixtures"):
        directory.mkdir(parents=True, exist_ok=True)
    files = jsonl(run / "inventory/file_records.jsonl")
    records = jsonl(run / "extracted/search_records.jsonl")
    plans = jsonl(run / "planning/final_source_plans.jsonl")
    analyses = {int(row["index"]): row for row in jsonl(run / "planning/question_analysis.jsonl")}
    file_by_id = {row["file_id"]: row for row in files}
    records_by_file: dict[str, list[SearchRecord]] = defaultdict(list)
    for record in records:
        records_by_file[record["file_id"]].append(SearchRecord(**record))
    retriever = CompanyScopedRetriever(files, records)

    strict_cases = [plan for plan in plans if plan.get("final_selected_file_ids")]
    fallback_cases = [plan for plan in plans if not plan.get("final_selected_file_ids") or plan.get("selection_status") in {"ambiguous", "not_found"}]
    fallback_cases = fallback_cases[max(0, args.fallback_offset) :]
    chosen = ([strict_cases[0]] if strict_cases else []) + fallback_cases[: max(0, args.max_api_questions)]
    if not chosen:
        raise RuntimeError("No observable Strict or fallback cases in the existing Gate19 planning run")
    reuse = {
        "strict_source_plan": "Gate19 final_source_plans.jsonl", "generic_retrieval": "CompanyScopedRetriever over existing 1614 SearchRecords",
        "llm_client": "OpenRouterCandidateClient used only when --execute-api is set", "human_check_used": False,
        "formal_artifacts_written": False, "raw_written": False,
    }
    (analysis_dir / "existing_component_reuse.md").write_text("# Existing component reuse\n\n" + json.dumps(reuse, ensure_ascii=False, indent=2), encoding="utf-8")
    legacy_schema = {"selected_documents": "list", "execution_steps": "list", "request_more_candidates": "bool", "abstain": "bool", "ambiguity": "bool"}
    (analysis_dir / "planner_fallback_schema.json").write_text(json.dumps(legacy_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    (analysis_dir / "planner_output_schema.json").write_text(json.dumps({
        **legacy_schema,
        "question_type": "string", "required_file_types": ["string"],
        "required_attributes": ["string"], "required_capabilities": ["string"],
        "expected_answer_type": "string", "additional_probe_requests": ["string"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    serializable_catalog = {name: sorted(file_types) for name, file_types in EXECUTOR_FILE_TYPES.items()}
    minimal_catalog = {
        "document_location_locator": "Return extractor-backed page, slide, sheet, cell, paragraph, table, or section locations.",
        "document_text_extractor": "Return existing text evidence candidates from a selected text document.",
    }
    (analysis_dir / "executor_catalog.json").write_text(json.dumps(serializable_catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (analysis_dir / "document_probe_schema.json").write_text(json.dumps({"document_id": "string", "relative_path": "string", "file_type": "string", "document_role": "string", "top_text_evidence": "string", "structural_features": ["string"]}, ensure_ascii=False, indent=2), encoding="utf-8")

    base_config = CandidateModeConfig.from_env()
    # The PoC has a tighter budget than the reusable Candidate Mode defaults.
    config = CandidateModeConfig(
        api_key=base_config.api_key, budget_usd=args.budget_usd, soft_stop_usd=args.soft_stop_usd,
        max_cost_per_request_usd=args.max_cost_per_request_usd, max_retries=1,
        max_output_tokens=base_config.max_output_tokens,
        text_max_input_tokens=base_config.text_max_input_tokens,
        vision_max_input_tokens=base_config.vision_max_input_tokens,
        timeout_sec=base_config.timeout_sec,
    )
    client = OpenRouterCandidateClient(config, cache=CandidateCache(out / "candidate_cache"))
    models = client.fetch_models() if args.execute_api and config.api_key else []
    text_model = choose_low_cost_model(models, vision=False, minimum_context=2000, input_tokens=2000, output_tokens=config.max_output_tokens, max_cost=config.max_cost_per_request_usd, preferred_terms=("deepseek",)) if models else None
    (analysis_dir / "implementation_freeze.json").write_text(json.dumps({"head": "29e1fc9", "planner_schema_hash": hashlib.sha256(json.dumps(MINIMAL_PLANNER_SCHEMA, sort_keys=True).encode()).hexdigest(), "api_key_present": bool(config.api_key), "execute_api": args.execute_api, "model": text_model.model_id if text_model else "", "budget_usd": config.budget_usd, "planner_mode": args.planner_mode}, ensure_ascii=False, indent=2), encoding="utf-8")

    file_objects = [FileRecord(**row) for row in files]
    search_record_objects = [SearchRecord(**row) for row in records]
    probes, requests, results, validations, executions, evidences, stability_rows = [], [], [], [], [], [], []
    for plan in chosen:
        qid = int(plan["question_id"])
        analysis = analyses.get(qid, {})
        question = str(analysis.get("question_original") or analysis.get("question_normalized") or plan.get("question", ""))
        retrieval_query = str(analysis.get("question_for_search") or analysis.get("question_term_expanded") or question)
        strict_ids = [str(item) for item in plan.get("final_selected_file_ids", [])]
        if strict_ids:
            executions.append({"question_id": qid, "mode": "strict_reused", "selected_file_ids": strict_ids, "planner_called": False, "execution_status": "not_reexecuted", "reason": "existing Strict source plan already selected a set"})
            continue
        retrieved, retrieval_meta = retriever.retrieve(retrieval_query, mode="two_stage", top_k=args.retrieval_top_k)
        candidate_files = []
        for item in retrieved:
            if item.document_id not in {row["document_id"] for row in candidate_files} and item.document_id in file_by_id:
                candidate_files.append(minimal_probe(
                    file_by_id[item.document_id], records_by_file[item.document_id], question,
                    str(analysis.get("question_for_search") or analysis.get("question_term_expanded") or ""),
                ))
                if len(candidate_files) >= max(1, args.candidate_document_limit):
                    break
        probes.extend({"question_id": qid, **probe} for probe in candidate_files)
        prompt_candidates = [planner_probe_view(item) for item in candidate_files]
        prompt = minimal_planner_prompt(question, prompt_candidates, minimal_catalog, MINIMAL_PLANNER_SCHEMA)
        trial_count = max(1, min(3, args.stability_trials))
        first_valid = False
        for trial in range(trial_count):
            request = {
                "question_id": qid,
                "trial": trial + 1,
                "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest(),
                "candidate_count": len(candidate_files),
                "retrieval_meta": retrieval_meta,
                "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "probe_char_count": sum(int(row["probe_character_count"]) for row in candidate_files),
                "planner_probe_char_count": len(json.dumps(prompt_candidates, ensure_ascii=False)),
                "human_check_used": False,
            }
            requests.append(request)
            result: dict[str, Any] = {"question_id": qid, "trial": trial + 1, "status": "api_not_requested", "selected_document_ids": [], "cost_usd": 0.0}
            if args.execute_api and text_model and candidate_files:
                call = client.request_json(
                    model=text_model,
                    prompt=prompt,
                    prompt_version=f"minimal_planner_v1_trial_{trial + 1}",
                    response_format={"type": "json_object"},
                )
                result.update({
                    "status": "api_error" if call.error else "ok", "model": call.model,
                    "provider": call.provider, "cost_usd": call.cost_usd,
                    "latency_ms": call.latency_ms, "input_tokens": call.input_tokens,
                    "output_tokens": call.output_tokens, "reasoning_tokens": call.reasoning_tokens,
                    "cache_hit": call.cache_hit, "error": call.error,
                    "payload": call.payload if not call.error else {},
                    "format_diagnostics": call.format_diagnostics,
                })
            results.append(result)
            payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
            errors = validate_minimal_plan(payload, candidate_files, EXECUTOR_FILE_TYPES) if result["status"] == "ok" else [result["status"]]
            semantic_valid = not errors
            validations.append({
                "question_id": qid, "trial": trial + 1, "schema_valid": semantic_valid,
                "semantic_valid": semantic_valid, "errors": errors,
                "candidate_document_count": len(candidate_files), "format_diagnostics": result.get("format_diagnostics", {}),
                "human_check_used": False,
            })
            execution_plan, execution_error = build_execution_plan(payload, candidate_files, EXECUTOR_FILE_TYPES, question) if semantic_valid else (None, "invalid_plan")
            selected_ids = list(payload.get("selected_document_ids", [])) if isinstance(payload.get("selected_document_ids"), list) else []
            location_result: dict[str, Any] | None = None
            text_result: dict[str, Any] | None = None
            if execution_plan and execution_plan["executor"] == "document_location_locator":
                location_result = locate_document_content(question, file_objects, search_record_objects, document_ids=selected_ids)
            elif execution_plan and execution_plan["executor"] == "document_text_extractor":
                selected_probe_map = {row["document_id"]: row for row in candidate_files}
                matches = [
                    snippet for document_id in selected_ids for snippet in selected_probe_map[document_id]["evidence_snippets"]
                    if snippet["matched_terms"]
                ]
                text_result = {"matches": matches, "exact_location_available": any(item["location"] is not None for item in matches)}
            status = execution_error or "execution_plan_generated"
            if location_result is not None:
                status = "location_evidence_generated" if location_result["matches"] else "location_not_found"
            if text_result is not None:
                status = "text_evidence_generated" if text_result["matches"] else "text_evidence_not_found"
            executions.append({
                "question_id": qid, "trial": trial + 1, "mode": "minimal_planner_fallback",
                "selected_file_ids": selected_ids, "planner_called": result["status"] == "ok",
                "execution_status": status, "execution_plan": execution_plan or {},
                "reason": "Python adapter builds parameters after minimal schema validation.",
            })
            evidences.append({
                "question_id": qid, "trial": trial + 1, "selected_document_ids": selected_ids,
                "candidate_document_ids": [row["document_id"] for row in candidate_files],
                "evidence_kind": "document_location_locator" if location_result is not None else "document_text_extractor" if text_result is not None else "planner_probe_only",
                "production_evidence_generated": False, "location_result": location_result or {}, "text_result": text_result or {},
            })
            stability_rows.append({
                "question_id": qid, "trial": trial + 1,
                "direct_parse_success": result.get("format_diagnostics", {}).get("direct_parse_success", False),
                "normalized_parse_success": result.get("format_diagnostics", {}).get("normalized_parse_success", False),
                "schema_valid": semantic_valid, "selected_document_ids": "|".join(selected_ids),
                "executor": payload.get("executor"), "action": payload.get("action"),
                "cost_usd": result.get("cost_usd", 0.0), "latency_ms": result.get("latency_ms", 0),
            })
            if trial == 0:
                first_valid = semantic_valid
            if not first_valid:
                break
    write_jsonl(runs_dir / "document_probes.jsonl", probes)
    write_jsonl(runs_dir / "planner_requests.jsonl", requests)
    write_jsonl(runs_dir / "planner_results.jsonl", results)
    write_jsonl(runs_dir / "planner_validation_results.jsonl", validations)
    write_jsonl(runs_dir / "execution_results.jsonl", executions)
    write_jsonl(runs_dir / "evidence_results.jsonl", evidences)
    with (runs_dir / "planner_stability_trials.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["question_id", "trial", "direct_parse_success", "normalized_parse_success", "schema_valid", "selected_document_ids", "executor", "action", "cost_usd", "latency_ms"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(stability_rows)
    with (runs_dir / "cost_ledger.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "trial", "status", "model", "provider", "input_tokens", "output_tokens", "reasoning_tokens", "cost_usd", "latency_ms", "cache_hit", "error", "format_diagnostics"])
        writer.writeheader()
        for row in results:
            writer.writerow({field: row.get(field, "") for field in writer.fieldnames})
    (reports_dir / "cost_summary.md").write_text(f"# Cost\n\n- cumulative_cost_usd: {client.ledger.cumulative_cost_usd}\n- api_calls: {client.api_call_count}\n", encoding="utf-8")
    (reports_dir / "api_execution_status.md").write_text(
        "# API execution status\n\n"
        f"- execute_api_requested: {args.execute_api}\n- openrouter_key_present: {bool(config.api_key)}\n"
        f"- api_calls: {client.api_call_count}\n- cumulative_cost_usd: {client.ledger.cumulative_cost_usd}\n"
        "The runner never reads, prints, or writes an API key. A missing key leaves the PoC in offline-validation mode.\n",
        encoding="utf-8",
    )
    gap_rows = [row for row in executions if row["execution_status"] in {"invalid_plan", "request_more_candidates", "abstain", "missing_executor_adapter"}]
    (analysis_dir / "executor_gap_report.md").write_text(
        "# Executor compatibility audit\n\n"
        "- This PoC never invokes the production pipeline; it may run an isolated deterministic adapter after validation.\n"
        f"- plans requiring follow-up: {len(gap_rows)}\n"
        "- Unknown executors and incompatible file types are rejected before file execution.\n",
        encoding="utf-8",
    )
    (analysis_dir / "planner_fallback_design.md").write_text(
        "# Planner fallback\n\n"
        "1. Reuse an existing Strict source plan when it already selected documents.\n"
        "2. Otherwise retrieve up to five existing SearchRecord-backed document probes.\n"
        "3. Ask Candidate Mode only for document IDs, a registered executor, and an action.\n"
        "4. Build all execution parameters in Python after ID and file-type validation.\n"
        "5. Keep the result isolated from formal predictions, Evidence, Gate, and production execution.\n",
        encoding="utf-8",
    )
    (reports_dir / "final_summary.md").write_text(f"# Isolated multistage planner PoC\n\n- strict_reused: {sum(row['mode'] == 'strict_reused' for row in executions)}\n- planner_fallback_attempted: {sum(row['mode'] == 'minimal_planner_fallback' for row in executions)}\n- api_calls: {client.api_call_count}\n- cost_usd: {client.ledger.cumulative_cost_usd}\n- Human_check used: false\n- production pipeline invoked: false\n", encoding="utf-8")
    (reports_dir / "resume_checkpoint.md").write_text(
        "# Resume checkpoint\n\n"
        "- Offline retrieval, document probes, and plan validation are complete.\n"
        f"- API calls completed: {client.api_call_count}.\n"
        f"- Planner mode: {args.planner_mode}; stability trials requested: {args.stability_trials}.\n"
        f"- Current PoC cost: {client.ledger.cumulative_cost_usd}.\n"
        "- Strict Mode and formal artifacts were not invoked.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
