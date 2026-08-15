from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .io_utils import sha1_text, write_jsonl
from .schemas import EXECUTOR_VERSION, PLANNER_VERSION, PROMPT_VERSION, SCHEMA_VERSION, TOOL_REGISTRY_VERSION, AnswerResult, CompactFileProfile, FileRecord, SearchRecord, to_dict
from .chart_executor import execute_chart_series_lookup, is_chart_series_question
from .table_executor import execute_table_question, is_table_question, write_table_slice_questions
from .document_executor import execute_document_question
from .extraction_spec import build_extraction_spec
from .answer_gate import evaluate_answer_gate
from .code_executor import execute_code_inspection
from .notebook_executor import execute_notebook_axis_ticks, execute_notebook_inspection
from .semantic_contract import verify_semantic_contract
from .source_requirements import verify_selected_sources
from .semantic_executor import build_semantic_spec, execute_semantic_document_lookup, is_semantic_document_question
from .llm_client import OpenRouterClient
from .cross_source_calculation import execute_cross_source_calculation, is_cross_source_calculation_question
from .id_count_executor import execute_id_count, is_id_count_question
from .route_registry import choose_route


@dataclass(frozen=True)
class ToolSpec:
    tool_name: str
    description: str
    supported_file_types: tuple[str, ...]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    implementation_status: str
    executor: str
    requires_llm: bool = False
    requires_python: bool = False
    requires_vision: bool = False


TOOL_NAMES = (
    "document_lookup",
    "table_lookup",
    "table_filter",
    "table_aggregation",
    "calculation",
    "version_diff",
    "format_extraction",
    "code_inspection",
    "notebook_inspection",
    "notebook_axis_tick_lookup",
    "chart_series_lookup",
    "cross_file_aggregation",
    "answer_formatting",
    "generated_python",
    "evidence_verification",
)


def build_tool_registry() -> dict[str, ToolSpec]:
    registry: dict[str, ToolSpec] = {}
    for name in TOOL_NAMES:
        registry[name] = ToolSpec(
            tool_name=name,
            description=f"汎用操作: {name}",
            supported_file_types=("docx", "pptx", "xlsx", "pdf", "csv", "tsv", "py", "ipynb", "md", "png", "jpg"),
            input_schema={"question": "string", "files": "FileRecord[]", "search_records": "SearchRecord[]", "conditions": "object"},
            output_schema={"answer": "string", "evidence": "Evidence[]", "warnings": "string[]"},
            implementation_status=("implemented" if name in {"document_lookup", "verbatim_extraction", "format_extraction", "location_lookup", "table_lookup", "table_filter", "table_aggregation", "calculation", "cross_file_aggregation", "answer_formatting", "code_inspection", "notebook_inspection", "notebook_axis_tick_lookup", "chart_series_lookup"} else "not_implemented"),
            executor=("execute_document_question" if name in {"document_lookup", "verbatim_extraction", "format_extraction", "location_lookup"} else "execute_code_inspection" if name == "code_inspection" else "execute_notebook_inspection" if name == "notebook_inspection" else "execute_notebook_axis_ticks" if name == "notebook_axis_tick_lookup" else "execute_generic_evidence_tool"),
            requires_python=name == "generated_python",
            requires_vision=name in {"format_extraction"},
        )
    return registry


def _terms(question: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[A-Za-z0-9_]{2,}|[一-龥ぁ-んァ-ン]{2,}", question or "")]


def _operation_name(operation: dict[str, Any]) -> str:
    name = operation.get("tool_name") or operation.get("operation_type") or "document_lookup"
    aliases = {
        "calculation_planning": "calculation",
        "format_check": "format_extraction",
        "diff_pair_selection": "version_diff",
        "image_or_chart_check": "format_extraction",
        "code_static_lookup": "code_inspection",
    }
    return aliases.get(str(name), str(name))


def _record_evidence(record: SearchRecord, terms: list[str]) -> dict[str, Any] | None:
    text = record.text or ""
    lowered = text.lower()
    matched = [term for term in terms if term in lowered]
    if not matched and record.record_type == "metadata":
        matched = terms[:1]
    if not matched:
        return None
    return {
        "record_id": record.record_id,
        "file_id": record.file_id,
        "source_path": record.raw_path,
        "location": record.metadata,
        "record_type": record.record_type,
        "matched_terms": matched[:12],
        "preview": re.sub(r"\s+", " ", text).strip()[:700],
        "preview_only": True,
    }


def execute_generic_evidence_tool(
    operation_name: str,
    question: str,
    files: list[FileRecord],
    search_records: list[SearchRecord],
    conditions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """選択済み資料の構造化レコードから、回答候補と位置付き根拠を作る。"""
    conditions = conditions or {}
    terms = _terms(question)
    if operation_name in {"format_extraction", "version_diff", "code_inspection", "notebook_inspection"}:
        terms = terms + ["style", "format", "version", "old", "new", "function", "cell"]
    evidence = []
    for record in search_records:
        item = _record_evidence(record, terms)
        if item:
            evidence.append(item)
    evidence.sort(key=lambda item: (-len(item["matched_terms"]), item["source_path"], item["record_id"]))
    if operation_name == "version_diff" and len(files) >= 2:
        evidence = evidence[:20]
    else:
        evidence = evidence[:8]
    previews = [item["preview"] for item in evidence if item["preview"]]
    answer = "\n".join(previews[:3])
    return {
        "tool_name": operation_name,
        "answer": answer[:1800],
        "evidence": evidence,
        "warnings": [] if evidence else ["関連する根拠レコードが見つかりません"],
        "calculation_trace": [],
    }


def run_answer_pipeline(
    analyses: list[Any],
    final_source_plans: list[dict[str, Any]],
    files: list[FileRecord],
    search_records: list[SearchRecord],
    profiles: list[CompactFileProfile],
    output_dir: Path,
    extraction_results: list[Any] | None = None,
    project_root: Path | None = None,
    table_executor_enabled: bool = True,
    dry_run: bool = False,
    execution_dir: Path | None = None,
                run_mode: str = "",
    api_mode: str = "",
    document_work_dir: Path | None = None,
    semantic_client: OpenRouterClient | None = None,
    semantic_work_dir: Path | None = None,
) -> dict[str, Any]:
    """Source Planを汎用ツールへ渡し、根拠付きAnswerResultを生成する。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    files_by_id = {item.file_id: item for item in files}
    records_by_file: dict[str, list[SearchRecord]] = {}
    for record in search_records:
        records_by_file.setdefault(record.file_id, []).append(record)
    analysis_by_id = {item.index: item for item in analyses}
    extraction_by_file = {item.file_id: item for item in (extraction_results or [])}
    table_analyses = write_table_slice_questions(analyses, output_dir / "evaluation")
    table_question_ids = {item.index for item in table_analyses}
    results: list[AnswerResult] = []
    gates: list[dict[str, Any]] = []
    executions: list[dict[str, Any]] = []
    registry = build_tool_registry()
    for plan in final_source_plans:
        question_id = int(plan["question_id"])
        analysis = analysis_by_id.get(question_id)
        question = analysis.question_normalized if analysis else str(plan.get("question", ""))
        selected_ids = [str(value) for value in plan.get("final_selected_file_ids", []) if str(value) in files_by_id]
        selected_files = [files_by_id[file_id] for file_id in selected_ids]
        selected_records = [record for file_id in selected_ids for record in records_by_file.get(file_id, [])]
        operations = plan.get("operations") or [{"tool_name": route} for route in (analysis.provisional_routes if analysis else ["document_lookup"])]
        operation_parameters = [item.get("parameters", {}) for item in operations if isinstance(item, dict)]
        operation_names = [_operation_name(item) for item in operations]
        route_question = getattr(analysis, "question_original", "") if analysis else question
        route_decision = choose_route(route_question or question, analysis, selected_files)
        # NotebookはPythonコードを含んでも、保存済みセルと出力を扱う専用Executorへ渡す。
        if selected_files and all(item.extension == ".ipynb" for item in selected_files) and "code_inspection" in operation_names:
            operation_names = ["notebook_inspection" if name == "code_inspection" else name for name in operation_names]
        if "answer_formatting" not in operation_names:
            operation_names.append("answer_formatting")
        all_evidence: list[dict[str, Any]] = []
        tool_outputs: list[dict[str, Any]] = []
        result_selected_ids = list(selected_ids)
        warnings = list(plan.get("warnings", []))
        # 比較Executorが未実装の質問は通常Executorへ渡さず、分類結果と抑制理由だけを保存する。
        comparison_spec = build_semantic_spec(question)
        comparison_preexecution = comparison_spec.unsupported_reason == "comparison_source_missing"
        if comparison_preexecution and not dry_run:
            operation_names = ["comparison"]
            comparison_output = {
                "status": "unsupported",
                "answer": "",
                "evidence": [],
                "used_file_ids": [],
                "question_type": "comparison",
                "primary_operation": "comparison",
                "comparison_type": "version_diff",
                "required_source_count": 2,
                "selected_source_count": len(selected_files),
                "source_relation": "previous_and_current_version",
                "comparison_executed": False,
                "executor_not_run": True,
                "suppression_reason": "comparison_source_missing",
                "failure_stage": "comparison_source_selection",
                "verification": {
                    "executor_not_run": True,
                    "comparison_executed": False,
                    "suppression_reason": "comparison_source_missing",
                },
                "semantic_spec": comparison_spec.__dict__,
            }
            tool_outputs.append(comparison_output)
            status = "unsupported"
            answer = ""
            failure_stage = "comparison_source_selection"
            warnings.append("comparison_source_missing")
        elif dry_run:
            status = "dry_run"
            answer = ""
            failure_stage = ""
        else:
            table_files = [item for item in selected_files if item.extension in {".xlsx", ".csv", ".tsv"}]
            if is_id_count_question(question) and project_root:
                count_output = execute_id_count(
                    question_id,
                    question,
                    getattr(analysis, "question_for_search", "") if analysis else question,
                    files,
                    extraction_by_file,
                    project_root,
                    (execution_dir.parent / "id_count") if execution_dir else None,
                )
                answer = str(count_output.get("answer", ""))
                if count_output.get("used_file_ids"):
                    result_selected_ids = list(count_output["used_file_ids"])
                all_evidence = [count_output["evidence"]] if count_output.get("evidence") else []
                tool_outputs.append(count_output)
                warnings.extend([count_output.get("warning", "")] if count_output.get("warning") else [])
                status = "completed" if count_output.get("status") == "success" and answer else "unsupported"
                failure_stage = count_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = count_output.get("operations_executed", operation_names)
            elif is_cross_source_calculation_question(question) and project_root:
                cross_output = execute_cross_source_calculation(
                    question_id,
                    question,
                    getattr(analysis, "question_for_search", "") if analysis else question,
                    files,
                    extraction_by_file,
                    project_root,
                    (execution_dir.parent / "calculation") if execution_dir else None,
                )
                answer = str(cross_output.get("answer", ""))
                if cross_output.get("used_file_ids"):
                    result_selected_ids = list(cross_output["used_file_ids"])
                all_evidence = [cross_output["evidence"]] if cross_output.get("evidence") else []
                tool_outputs.append(cross_output)
                warnings.extend([cross_output.get("warning", "")] if cross_output.get("warning") else [])
                status = "completed" if cross_output.get("status") == "success" and answer else "unsupported"
                failure_stage = cross_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = cross_output.get("operations_executed", operation_names)
            elif project_root and is_chart_series_question(question):
                chart_output = execute_chart_series_lookup(question, selected_files, project_root)
                if chart_output is None:
                    chart_output = {
                        "status": "unsupported", "answer": "", "evidence": [],
                        "warning": "chart_route_not_applicable", "failure_stage": "chart_structure_resolution",
                        "operations_executed": ["chart_series_lookup"], "question_type": "chart_inspection", "verification": {},
                    }
                answer = str(chart_output.get("answer", ""))
                all_evidence = list(chart_output.get("evidence", []))
                tool_outputs.append(chart_output)
                warnings.extend([chart_output.get("warning", "")] if chart_output.get("warning") else [])
                status = "completed" if chart_output.get("status") == "success" and answer else "unsupported"
                failure_stage = chart_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = chart_output.get("operations_executed", operation_names)
            elif table_executor_enabled and project_root and (
                question_id in table_question_ids
                or (route_decision.route_selected and route_decision.executor == "execute_table_question")
            ):
                table_output = execute_table_question(
                    analysis,
                    table_files,
                    extraction_by_file,
                    project_root,
                    operations,
                    available_files=files,
                    calculation_work_dir=(execution_dir.parent / "calculation") if execution_dir else None,
                )
                answer = str(table_output.get("answer", ""))
                all_evidence = [table_output["evidence"]] if table_output.get("evidence") else []
                if table_output.get("evidence", {}).get("selected_file_id"):
                    result_selected_ids = [table_output["evidence"]["selected_file_id"]]
                tool_outputs.append(table_output)
                warnings.extend([table_output.get("warning", "")] if table_output.get("warning") else [])
                status = "completed" if table_output.get("status") == "success" and answer else "unsupported"
                failure_stage = table_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = table_output.get("operations_executed", operation_names)
            elif is_semantic_document_question(question, operation_names, selected_files) or (
                build_semantic_spec(question).subtype in {"semantic_fact_lookup", "semantic_role_lookup", "semantic_status_lookup", "semantic_list_extraction"}
                and any(item.extension in {".docx", ".pptx", ".pdf"} for item in selected_files)
            ):
                semantic_output = execute_semantic_document_lookup(
                    question_id,
                    question,
                    getattr(analysis, "question_for_search", "") if analysis else question,
                    selected_files,
                    extraction_by_file,
                    project_root or Path.cwd(),
                    semantic_client,
                    semantic_work_dir or ((execution_dir or output_dir / "execution").parent / "semantic"),
                )
                answer = str(semantic_output.get("answer", ""))
                if semantic_output.get("used_file_ids"):
                    result_selected_ids = list(semantic_output["used_file_ids"])
                all_evidence = list(semantic_output.get("evidence", []))
                tool_outputs.append(semantic_output)
                warnings.extend([semantic_output.get("warning", "")] if semantic_output.get("warning") else [])
                status = "completed" if semantic_output.get("status") == "success" and answer else "unsupported"
                failure_stage = semantic_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = semantic_output.get("operations_executed", operation_names)
            elif (any(item.extension in {".docx", ".pptx", ".pdf", ".xlsx", ".md"} for item in selected_files) or (analysis and build_extraction_spec(question).target_type == "identifier_record")) and any(name in {"document_lookup", "verbatim_extraction", "format_extraction", "location_lookup"} for name in operation_names):
                # ExtractionSpecは意味を変えないquestion_normalizedから生成する。
                document_question = question
                search_question = getattr(analysis, "question_for_search", "") if analysis else ""
                document_output = execute_document_question(document_question, operation_names, selected_files, extraction_by_file, project_root or Path.cwd(), document_work_dir, question_id, files, search_question=search_question)
                answer = str(document_output.get("answer", ""))
                if document_output.get("used_file_ids"):
                    result_selected_ids = list(document_output["used_file_ids"])
                all_evidence = list(document_output.get("evidence", []))
                tool_outputs.append(document_output)
                warnings.extend([document_output.get("warning", "")] if document_output.get("warning") else [])
                if document_output.get("ambiguous"):
                    warnings.append("ambiguous_document_evidence")
                status = "completed" if document_output.get("status") == "success" and answer else "unsupported"
                failure_stage = document_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = document_output.get("operations_executed", operation_names)
            elif "code_inspection" in operation_names:
                code_output = execute_code_inspection(question, selected_files, project_root or Path.cwd())
                answer = str(code_output.get("answer", ""))
                all_evidence = list(code_output.get("evidence", []))
                tool_outputs.append(code_output)
                warnings.extend([code_output.get("warning", "")] if code_output.get("warning") else [])
                status = "completed" if code_output.get("status") == "success" and answer else "unsupported"
                failure_stage = code_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = code_output.get("operations_executed", operation_names)
            elif project_root and route_decision.route_selected and route_decision.executor == "execute_notebook_axis_ticks":
                notebook_output = execute_notebook_axis_ticks(question, selected_files, extraction_by_file, project_root)
                answer = str(notebook_output.get("answer", ""))
                all_evidence = list(notebook_output.get("evidence", []))
                tool_outputs.append(notebook_output)
                warnings.extend([notebook_output.get("warning", "")] if notebook_output.get("warning") else [])
                status = "completed" if notebook_output.get("status") == "success" and answer else "unsupported"
                failure_stage = notebook_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = notebook_output.get("operations_executed", ["notebook_axis_tick_lookup"])
            elif "notebook_inspection" in operation_names:
                notebook_output = execute_notebook_inspection(question, selected_files, extraction_by_file, project_root or Path.cwd())
                answer = str(notebook_output.get("answer", ""))
                all_evidence = list(notebook_output.get("evidence", []))
                tool_outputs.append(notebook_output)
                warnings.extend([notebook_output.get("warning", "")] if notebook_output.get("warning") else [])
                status = "completed" if notebook_output.get("status") == "success" and answer else "unsupported"
                failure_stage = notebook_output.get("failure_stage", "") or ("evidence_failure" if status != "completed" else "")
                operation_names = notebook_output.get("operations_executed", operation_names)
            else:
                for operation_name in operation_names:
                    if operation_name not in registry:
                        warnings.append(f"unknown_tool:{operation_name}")
                        continue
                    if operation_name in {"answer_formatting", "evidence_verification"}:
                        continue
                    output = execute_generic_evidence_tool(operation_name, question, selected_files, selected_records)
                    tool_outputs.append(output)
                    all_evidence.extend(output["evidence"])
                    warnings.extend(output["warnings"])
                unique_evidence = {item["record_id"]: item for item in all_evidence}
                all_evidence = list(unique_evidence.values())[:12]
                answer = "\n".join(item["preview"] for item in all_evidence[:3])[:1800]
                status = "completed" if answer and all_evidence else "unsupported"
                failure_stage = "" if status == "completed" else "evidence_failure"
        implementation_statuses = [registry.get(name).implementation_status for name in operation_names if name in registry]
        implementation_status = "implemented" if implementation_statuses and all(item == "implemented" for item in implementation_statuses) else "not_implemented"
        preview_only = bool(all_evidence) and all(item.get("preview_only", False) for item in all_evidence)
        semantic_contract = verify_semantic_contract(question, operation_names, tool_outputs)
        source_requirement = (
            tool_outputs[-1].get("source_requirement")
            if tool_outputs and isinstance(tool_outputs[-1], dict) and tool_outputs[-1].get("source_requirement")
            else (getattr(analysis, "source_requirement", {}) if analysis else {})
        )
        source_verification = verify_selected_sources(
            source_requirement,
            [files_by_id[file_id] for file_id in result_selected_ids if file_id in files_by_id],
            content_verified_file_ids=set(result_selected_ids),
        )
        semantic_contract["source_verification"] = source_verification
        semantic_contract["source_cardinality_match"] = source_verification["source_cardinality_match"]
        semantic_contract["source_relation_match"] = source_verification["source_relation_match"]
        if tool_outputs and tool_outputs[-1].get("question_type") == "semantic_document_lookup":
            verification = tool_outputs[-1].setdefault("verification", {})
            verification["source_files_verified"] = source_verification["verification_status"] == "passed"
            verification["project_relation_verified"] = source_verification["source_relation_match"] is True
        if source_verification["verification_status"] != "passed":
            for name in ("source_cardinality_match", "source_relation_match"):
                if source_verification.get(name) is not True and name not in semantic_contract["failed_checks"]:
                    semantic_contract["failed_checks"].append(name)
            semantic_contract["verification_status"] = "failed"
        gate = evaluate_answer_gate(
            question_id=question_id,
            answer=answer,
            executor_name=operation_names[0] if operation_names else "unknown",
            implementation_status=implementation_status,
            used_file_ids=result_selected_ids,
            evidence=all_evidence,
            execution_success=status in {"completed", "dry_run"} and not dry_run,
            preview_only=preview_only,
            ambiguous=any("ambiguous" in warning.lower() for warning in warnings) or any(output.get("ambiguous") for output in tool_outputs),
            question_type=(tool_outputs[-1].get("question_type", "") if tool_outputs and isinstance(tool_outputs[-1], dict) else ""),
            verification=(tool_outputs[-1].get("verification", {}) if tool_outputs and isinstance(tool_outputs[-1], dict) else {}),
            semantic_contract=semantic_contract,
        )
        gates.append(to_dict(gate))
        if not gate.allow_answer:
            answer = ""
            status = "unsupported"
            failure_stage = failure_stage or "evidence_failure"
            warnings.append(gate.suppression_reason)
        # AnswerResultには、Plannerが選んだ候補ではなく、Executorが実際に使った資料を記録する。
        actual_selected_files = [files_by_id[file_id] for file_id in result_selected_ids if file_id in files_by_id]
        result = AnswerResult(
            question_id=question_id,
            answer=answer,
            answer_type="text",
            selected_files=[item.raw_path for item in actual_selected_files],
            evidence_locations=all_evidence,
            operations_executed=operation_names,
            calculation_trace=[trace for output in tool_outputs for trace in output.get("calculation_trace", [])],
            confidence=min(1.0, len(all_evidence) / 5.0) if not dry_run else 0.0,
            status=status,
            warnings=list(dict.fromkeys(warnings))[:30],
            failure_stage=failure_stage,
            planner_mode=str(plan.get("planner_mode", "")),
            selector_mode=str(plan.get("selector_mode", "")),
            selected_file_ids=result_selected_ids,
            operation_parameters=operation_parameters,
            executor_version=EXECUTOR_VERSION,
            cache_key=sha1_text(json.dumps({
                "question_hash": sha1_text(question),
                "selected_file_hashes": [files_by_id[file_id].sha1 for file_id in result_selected_ids if file_id in files_by_id],
                  "planner_version": PLANNER_VERSION,
                  "prompt_version": PROMPT_VERSION,
                "tool_registry_version": TOOL_REGISTRY_VERSION,
                "executor_version": EXECUTOR_VERSION,
                "schema_version": SCHEMA_VERSION,
                "operation_parameters": operation_parameters,
                "run_mode": run_mode,
                "api_mode": api_mode,
            }, ensure_ascii=False, sort_keys=True)),
            gate_status=gate.gate_status,
            gate_reason=gate.suppression_reason,
        )
        results.append(result)
        executions.append({"question_id": question_id, "operations": operation_names, "tool_outputs": tool_outputs, "selected_file_ids": result_selected_ids, "semantic_contract": semantic_contract, "cache_key": result.cache_key, "route_trace": route_decision.to_dict()})
    write_jsonl(output_dir / "answer_results.jsonl", [to_dict(item) for item in results])
    write_jsonl(output_dir / "answer_gate_results.jsonl", gates)
    write_jsonl(output_dir / "route_traces.jsonl", [item["route_trace"] | {"question_id": item["question_id"]} for item in executions])
    execution_dir = execution_dir or (output_dir / "execution")
    write_jsonl(execution_dir / "tool_executions.jsonl", executions)
    write_jsonl(execution_dir / "tool_registry.jsonl", [asdict(item) for item in registry.values()])
    return {
        "answer_results": results,
        "execution_count": len(results),
        "answered_count": sum(1 for item in results if item.answer),
        "generated_python_count": sum(1 for item in results if "generated_python" in item.operations_executed),
    }
