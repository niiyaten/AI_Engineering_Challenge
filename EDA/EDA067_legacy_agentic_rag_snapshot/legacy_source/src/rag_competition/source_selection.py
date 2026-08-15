from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import sha1_text, write_csv, write_json, write_jsonl
from .llm_client import OpenRouterClient
from .protected_files import masked_path
from .schemas import CandidateFile, CompactFileProfile, ExecutionPlan, FileRecord, QuestionAnalysis, SearchRecord, to_dict
from .search import tokenize
from .source_selection_resolution import resolve_source_selection


DOCUMENT_ROLES = ["contract", "proposal", "schedule", "data", "analysis", "meeting", "report", "management", "unknown"]
OPERATIONS = [
    "document_lookup",
    "table_lookup",
    "calculation_planning",
    "format_check",
    "diff_pair_selection",
    "image_or_chart_check",
    "code_static_lookup",
    "cross_file_aggregation",
]
ROUTE_TO_OPERATION = {
    "document_qa": "document_lookup",
    "table_lookup": "table_lookup",
    "calculation": "calculation_planning",
    "format_extraction": "format_check",
    "diff_comparison": "diff_pair_selection",
    "image_ocr": "image_or_chart_check",
    "code_execution": "code_static_lookup",
    "cross_file_aggregation": "cross_file_aggregation",
    "location_lookup": "location_lookup",
}


@dataclass
class PlanningResult:
    analyses: list[QuestionAnalysis]
    candidates: list[CandidateFile]
    plans: list[ExecutionPlan]
    stats: dict[str, Any]


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").replace("\xa0", " ")


def compact(value: str, limit: int = 800) -> str:
    return re.sub(r"\s+", " ", value or "").strip()[:limit]


def list_unique(values: list[str], limit: int = 30) -> list[str]:
    result: list[str] = []
    for value in values:
        text = normalize_text(str(value)).strip()
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def explicit_file_hints(question: str) -> list[str]:
    pattern = r"[\w一-龥ぁ-んァ-ンー・（）()＝=._\-]+(?:\.docx|\.pptx|\.xlsx|\.pdf|\.csv|\.tsv|\.py|\.ipynb|\.md|\.png|\.jpg|\.jpeg)"
    normalized = normalize_text(question)
    broad_matches = re.findall(pattern, normalized, flags=re.IGNORECASE)
    # 助詞を含む長い一致とは別にbasenameを抽出し、明示名の完全一致を優先できるようにする。
    extensions = r"docx|pptx|xlsx|pdf|csv|tsv|py|ipynb|md|png|jpg|jpeg"
    basename_pattern = rf"(?<![A-Za-z0-9_.-])[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:{extensions})"
    basename_matches = re.findall(basename_pattern, normalized, flags=re.IGNORECASE)
    return list_unique(basename_matches + broad_matches)


def identifier_hints(question: str) -> list[str]:
    text = normalize_text(question)
    hints = re.findall(r"\b[A-Za-z][A-Za-z0-9_]{1,40}\b|\b[A-Z]{1,6}[-_]\d{1,6}\b", text)
    hints += re.findall(r"[一-龥ぁ-んァ-ンー]{1,12}(?:ID|コード|列|項目|パラメータ|変数)", text)
    return list_unique(hints)


def date_hints(question: str) -> list[str]:
    text = normalize_text(question)
    dates = []
    for match in re.finditer(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?", text):
        y, m, d = match.groups()
        dates.append(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    return list_unique(dates)


def version_hints(question: str) -> list[str]:
    text = normalize_text(question).lower()
    hints = re.findall(r"\bold\b|\bnew\b|\bv\d+\b|\br\d+\b|旧版|旧|最新版|最新|差分|比較", text)
    return list_unique(hints)


def question_terms(question: str, limit: int = 24) -> list[str]:
    terms = [term for term in tokenize(normalize_text(question)) if len(term) >= 2]
    return list_unique(terms, limit)


def project_candidates(question: str, files: list[FileRecord]) -> list[str]:
    normalized_question = normalize_text(question)
    projects = sorted({file.project_name for file in files if file.project_name and file.project_name != "社内管理"}, key=len, reverse=True)
    return [project for project in projects if normalize_text(project) in normalized_question]


def answer_format_constraints(question: str) -> list[str]:
    constraints = []
    text = normalize_text(question)
    if any(word in text for word in ["数値", "小数", "四捨五入", "%", "割合"]):
        constraints.append("numeric")
    if any(word in text for word in ["ファイル名", "資料名"]):
        constraints.append("file_name")
    if any(word in text for word in ["色", "太字", "コメント", "下線"]):
        constraints.append("format")
    return constraints


def classify_question_types(analysis: QuestionAnalysis) -> list[str]:
    q = normalize_text(analysis.question_normalized)
    types = []
    if explicit_file_hints(q):
        types.append("explicit_file")
    if version_hints(q):
        types.append("version_comparison")
    if any(word in q for word in ["提案書", "契約書", "スケジュール", "報告書", "会議録", "資料"]):
        types.append("document_role")
    if identifier_hints(q):
        types.append("identifier_or_column")
    if analysis.needs_multiple_files or any(word in q for word in ["照合", "横断", "全案件", "すべて", "比較"]):
        types.append("multiple_or_cross_file")
    if any(word in q for word in ["前段", "その結果", "抽出した", "該当する"]):
        types.append("multi_step")
    if any(word in q for word in ["全案件", "全社", "すべての案件", "横断"]):
        types.append("cross_project")
    if any(word in q for word in ["色", "太字", "コメント", "下線", "書式"]):
        types.append("format")
    if any(word in q.lower() for word in ["python", "ipynb", "notebook", "コード", "パラメータ", "モデル"]):
        types.append("code_or_notebook")
    if any(word in q for word in ["画像", "グラフ", "図", "配置", "スライド"]):
        types.append("image_or_layout")
    return types or ["general"]


def select_analysis_subset(analyses: list[QuestionAnalysis], question_ids: list[int], limit: int, output_dir: Path) -> list[QuestionAnalysis]:
    if question_ids:
        wanted = set(question_ids)
        selected = [analysis for analysis in analyses if analysis.index in wanted]
        reason = {analysis.index: "explicit_question_ids" for analysis in selected}
    elif limit > 0 and limit < len(analyses):
        target_types = [
            "explicit_file",
            "version_comparison",
            "document_role",
            "identifier_or_column",
            "multiple_or_cross_file",
            "multi_step",
            "cross_project",
            "format",
            "code_or_notebook",
            "image_or_layout",
        ]
        selected = []
        reason: dict[int, str] = {}
        used = set()
        for target in target_types:
            for analysis in analyses:
                if analysis.index in used:
                    continue
                if target in classify_question_types(analysis):
                    selected.append(analysis)
                    used.add(analysis.index)
                    reason[analysis.index] = f"representative:{target}"
                    break
            if len(selected) >= limit:
                break
        for analysis in analyses:
            if len(selected) >= limit:
                break
            if analysis.index not in used:
                selected.append(analysis)
                used.add(analysis.index)
                reason[analysis.index] = "fill_by_original_order"
    else:
        selected = analyses
        reason = {analysis.index: "all_questions" for analysis in analyses}

    write_jsonl(
        output_dir / "question_selection.jsonl",
        [
            {
                "question_id": analysis.index,
                "question": analysis.question_normalized,
                "question_types": classify_question_types(analysis),
                "selection_reason": reason.get(analysis.index, ""),
            }
            for analysis in selected
        ],
    )
    return selected


def document_roles_from_analysis(analysis: QuestionAnalysis) -> list[str]:
    q = normalize_text(analysis.question_normalized)
    roles = []
    role_keywords = [
        ("contract", ["契約書", "契約", "CT"]),
        ("proposal", ["提案書", "提案", "PP"]),
        ("schedule", ["スケジュール", "計画", "PL"]),
        ("data", ["train", "データ", "列", "カラム説明", "CSV", "XLSX"]),
        ("analysis", ["分析", "notebook", "python", "モデル"]),
        ("meeting", ["会議録", "定例", "議事"]),
        ("report", ["報告書", "最終報告", "中間報告"]),
        ("management", ["社内管理", "用語集", "規定"]),
    ]
    for role, keywords in role_keywords:
        if any(keyword.lower() in q.lower() for keyword in keywords):
            roles.append(role)
    for route in analysis.provisional_routes:
        if route == "calculation":
            roles.append("data")
        elif route == "diff_comparison":
            roles.extend(["report", "proposal", "contract"])
        elif route == "format_extraction":
            roles.extend(["proposal", "report", "contract", "schedule"])
        elif route == "code_execution":
            roles.append("analysis")
        elif route == "cross_file_aggregation":
            roles.extend(["report", "analysis"])
    return list_unique([role for role in roles if role in DOCUMENT_ROLES]) or ["unknown"]


def build_heuristic_source_plan(analysis: QuestionAnalysis, files: list[FileRecord]) -> dict[str, Any]:
    search_question = analysis.question_for_search or analysis.question_normalized
    projects = project_candidates(search_question, files)
    scope = "cross_project" if analysis.needs_cross_project else ("specified_project" if projects else "unspecified")
    file_hints = explicit_file_hints(search_question)
    roles = document_roles_from_analysis(analysis)
    search_terms = question_terms(search_question)
    source_contract = dict(getattr(analysis, "source_requirement", {}) or {})
    requirements = [
        {
            "requirement_id": "src_1",
            "purpose": compact(analysis.question_normalized, 240),
            "scope": scope,
            "project_candidates": projects,
            "document_roles": roles,
            "file_name_hints": file_hints,
            "required_file_types": analysis.required_file_types,
            "search_terms": search_terms,
            "identifier_hints": identifier_hints(search_question),
            "date_hints": date_hints(search_question),
            "version_hints": version_hints(search_question),
            "multiple_files_required": analysis.needs_multiple_files,
            "source_cardinality": source_contract.get("source_cardinality", "multiple" if analysis.needs_multiple_files else "single"),
            "source_relation": source_contract.get("source_relation", "cross_project" if analysis.needs_cross_project else "same_project"),
            "relation_evidence_required": bool(source_contract.get("relation_evidence_required", True)),
            "depends_on": [],
        }
    ]
    if analysis.needs_multiple_files and not any(req["multiple_files_required"] for req in requirements):
        requirements[0]["multiple_files_required"] = True
    operations = [
        {
            "operation_id": f"op_{i + 1}",
            "operation_type": ROUTE_TO_OPERATION.get(route, "document_lookup"),
            "inputs": ["src_1"],
            "depends_on": [],
        }
        for i, route in enumerate(analysis.provisional_routes or ["document_qa"])
    ]
    return {
        "question_id": analysis.index,
        "planner_mode": "heuristic",
        "source_requirements": requirements,
        "operations": operations,
        "confidence": 0.55,
        "warnings": [],
    }


def normalize_llm_source_plan(parsed: dict[str, Any], heuristic: dict[str, Any], analysis: QuestionAnalysis, files: list[FileRecord]) -> tuple[dict[str, Any], bool, str]:
    if not isinstance(parsed, dict):
        return heuristic, False, "planner_response_not_object"
    reqs = parsed.get("source_requirements")
    ops = parsed.get("operations")
    if not isinstance(reqs, list) or not reqs:
        return heuristic, False, "source_requirements_missing"
    normalized_reqs = []
    projects = project_candidates(analysis.question_normalized, files)
    for i, req in enumerate(reqs, start=1):
        if not isinstance(req, dict):
            continue
        requirement_id = str(req.get("requirement_id") or f"src_{i}")
        roles = [role for role in list_unique([str(x) for x in req.get("document_roles", [])]) if role in DOCUMENT_ROLES]
        file_types = [str(x).lower().lstrip(".") for x in req.get("required_file_types", []) if str(x).strip()]
        normalized_reqs.append(
            {
                "requirement_id": requirement_id,
                "purpose": compact(str(req.get("purpose") or heuristic["source_requirements"][0]["purpose"]), 300),
                "scope": str(req.get("scope") or heuristic["source_requirements"][0]["scope"]),
                "project_candidates": list_unique([str(x) for x in req.get("project_candidates", [])] or projects),
                "document_roles": roles or heuristic["source_requirements"][0]["document_roles"],
                "file_name_hints": list_unique([str(x) for x in req.get("file_name_hints", [])] + explicit_file_hints(analysis.question_normalized)),
                "required_file_types": list_unique(file_types or heuristic["source_requirements"][0]["required_file_types"]),
                "search_terms": list_unique([str(x) for x in req.get("search_terms", [])] + question_terms(analysis.question_normalized, 12)),
                "identifier_hints": list_unique([str(x) for x in req.get("identifier_hints", [])] + identifier_hints(analysis.question_normalized)),
                "date_hints": list_unique([str(x) for x in req.get("date_hints", [])] + date_hints(analysis.question_normalized)),
                "version_hints": list_unique([str(x) for x in req.get("version_hints", [])] + version_hints(analysis.question_normalized)),
                "multiple_files_required": bool(req.get("multiple_files_required", False)),
                "source_cardinality": str(req.get("source_cardinality") or heuristic["source_requirements"][0].get("source_cardinality", "single")),
                "source_relation": str(req.get("source_relation") or heuristic["source_requirements"][0].get("source_relation", "unknown")),
                "relation_evidence_required": bool(req.get("relation_evidence_required", True)),
                "depends_on": list_unique([str(x) for x in req.get("depends_on", [])]),
            }
        )
    if not normalized_reqs:
        return heuristic, False, "no_valid_source_requirement"
    normalized_ops = []
    for operation in (ops if isinstance(ops, list) else []):
        if not isinstance(operation, dict):
            continue
        normalized_ops.append(
            {
                "operation_id": str(operation.get("operation_id") or f"op_{len(normalized_ops) + 1}"),
                "tool_name": str(operation.get("tool_name") or operation.get("operation_type") or "document_lookup"),
                "parameters": operation.get("parameters") if isinstance(operation.get("parameters"), dict) else {},
                "inputs": operation.get("inputs", []),
                "depends_on": operation.get("depends_on", []),
            }
        )
    normalized_ops = normalized_ops or heuristic["operations"]
    warnings = list_unique([str(x) for x in parsed.get("warnings", [])])
    if analysis.needs_multiple_files and len(normalized_reqs) == 1 and not normalized_reqs[0]["multiple_files_required"]:
        warnings.append("question_looks_multi_source_but_planner_returned_single_source")
    return (
        {
            "question_id": analysis.index,
            "planner_mode": "llm",
            "source_requirements": normalized_reqs,
            "operations": normalized_ops,
            "confidence": float(parsed.get("confidence", 0.0) or 0.0),
            "warnings": warnings,
        },
        True,
        "",
    )


def call_source_planner(
    analysis: QuestionAnalysis,
    files: list[FileRecord],
    client: OpenRouterClient | None,
    planner_model: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    heuristic = build_heuristic_source_plan(analysis, files)
    if client is None:
        meta = {
            "question_id": analysis.index,
            "planner_mode": "heuristic",
            "api_called": False,
            "cache_hit": False,
            "model": "",
            "prompt_hash": "",
            "parse_success": False,
            "fallback_used": False,
            "fallback_reason": "",
        }
        return heuristic, meta
    extracted = {
        "project_candidates": project_candidates(analysis.question_normalized, files),
        "explicit_file_names": explicit_file_hints(analysis.question_normalized),
        "document_roles": document_roles_from_analysis(analysis),
        "extensions": analysis.required_file_types,
        "dates": date_hints(analysis.question_normalized),
        "versions": version_hints(analysis.question_normalized),
        "identifiers": identifier_hints(analysis.question_normalized),
        "answer_format_constraints": answer_format_constraints(analysis.question_normalized),
    }
    prompt = f"""You are planning source selection for a document-grounded RAG competition.
Do not choose concrete file paths. Output only JSON.

Original question:
{analysis.question_original}

Normalized question:
{analysis.question_normalized}

Mechanically extracted hints:
{json.dumps(extracted, ensure_ascii=False)}

Available document roles:
{DOCUMENT_ROLES}

Available operations:
{OPERATIONS}

Return this schema:
{{
  "source_requirements": [
    {{
      "requirement_id": "src_1",
      "purpose": "information needed",
      "scope": "specified_project",
      "project_candidates": [],
      "document_roles": ["proposal"],
      "file_name_hints": [],
      "required_file_types": ["pptx"],
      "search_terms": [],
      "identifier_hints": [],
      "date_hints": [],
      "version_hints": [],
      "multiple_files_required": false,
      "depends_on": []
    }}
  ],
  "operations": [
    {{"operation_id": "op_1", "operation_type": "document_lookup", "inputs": ["src_1"], "depends_on": []}}
  ],
  "confidence": 0.0,
  "warnings": []
}}
"""
    result = client.call_json("source_planner", prompt, max_tokens=1400, model=planner_model)
    plan, parse_success, fallback_reason = normalize_llm_source_plan(result.parsed_json, heuristic, analysis, files)
    fallback_used = not (result.success and parse_success)
    if fallback_used:
        plan = heuristic
        plan["planner_mode"] = "heuristic_fallback"
    meta = {
        "question_id": analysis.index,
        "planner_mode": plan["planner_mode"],
        "api_called": result.api_called,
        "cache_hit": result.cache_hit,
        "model": result.model,
        "prompt_hash": result.prompt_hash,
        "parse_success": bool(result.parse_success and parse_success),
        "fallback_used": fallback_used,
        "fallback_reason": result.error or fallback_reason,
        "raw_response_path": result.raw_response_path,
    }
    plan.update({key: meta[key] for key in ("api_called", "cache_hit", "model", "prompt_hash", "parse_success", "fallback_used", "fallback_reason")})
    return plan, meta


def file_matches_explicit_hint(file: FileRecord, hint: str) -> tuple[bool, bool]:
    hint_name = normalize_text(Path(hint).name).lower()
    file_name = normalize_text(file.file_name).lower()
    return file_name == hint_name, file_name.replace(" ", "") == hint_name.replace(" ", "")


def deterministic_candidates_for_requirement(
    analysis: QuestionAnalysis,
    requirement: dict[str, Any],
    files: list[FileRecord],
    profiles_by_file: dict[str, CompactFileProfile],
    top_n: int,
    excluded_file_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded = excluded_file_ids or set()
    rows: list[dict[str, Any]] = []
    project_targets = requirement.get("project_candidates") or project_candidates(analysis.question_normalized, files)
    explicit_hints = requirement.get("file_name_hints") or []
    roles = set(requirement.get("document_roles") or [])
    file_types = {str(ext).lower().lstrip(".") for ext in requirement.get("required_file_types") or []}
    ids = list_unique((requirement.get("identifier_hints") or []) + (requirement.get("search_terms") or []), 30)
    versions = requirement.get("version_hints") or []
    scope = requirement.get("scope", "unspecified")
    for file in files:
        if file.file_id in excluded:
            continue
        profile = profiles_by_file.get(file.file_id)
        haystacks = {
            "path": normalize_text(file.relative_path + " " + file.file_name),
            "profile": normalize_text((profile.summary if profile else "") + " " + " ".join(profile.keywords if profile else [])),
        }
        score = 0.0
        breakdown: dict[str, float] = {}
        matched_fields: list[str] = []
        missing_fields: list[str] = []
        if explicit_hints:
            exact = any(file_matches_explicit_hint(file, hint)[0] for hint in explicit_hints)
            normalized = any(file_matches_explicit_hint(file, hint)[1] for hint in explicit_hints)
            if exact:
                breakdown["explicit_file_exact"] = 100.0
                matched_fields.append("file_name")
            elif normalized:
                breakdown["explicit_file_normalized"] = 95.0
                matched_fields.append("file_name_normalized")
            else:
                missing_fields.append("explicit_file_name")
        file_stem = normalize_text(Path(file.file_name).stem).strip().lower()
        normalized_question = normalize_text(analysis.question_normalized).lower()
        if len(file_stem) >= 3 and file_stem in normalized_question:
            breakdown["file_stem_in_question"] = 35.0
            matched_fields.append("file_name_stem")
        if project_targets:
            if file.project_name in project_targets:
                breakdown["project_match"] = 40.0
                matched_fields.append("project_name")
            elif scope == "specified_project" and file.project_name and file.project_name != "社内管理":
                breakdown["project_mismatch_penalty"] = -45.0
                missing_fields.append("project_name")
        if roles and file.document_kind in roles:
            breakdown["document_role_match"] = 20.0
            matched_fields.append("document_kind")
        elif roles and "unknown" not in roles:
            missing_fields.append("document_kind")
        if file_types:
            if file.extension.lstrip(".") in file_types:
                breakdown["extension_match"] = 15.0
                matched_fields.append("extension")
            else:
                missing_fields.append("extension")
        if versions:
            if file.version_label or any(normalize_text(v).lower() in haystacks["path"].lower() for v in versions):
                breakdown["version_match"] = 10.0
                matched_fields.append("version")
            else:
                missing_fields.append("version")
        id_matches = [term for term in ids if normalize_text(term).lower() in haystacks["path"].lower()]
        profile_matches = [term for term in ids if normalize_text(term).lower() in haystacks["profile"].lower()]
        if id_matches:
            breakdown["path_identifier_match"] = min(10.0, len(id_matches) * 2.0)
            matched_fields.append("path_identifier")
        if profile_matches:
            breakdown["profile_term_match"] = min(12.0, len(profile_matches) * 1.5)
            matched_fields.append("profile_summary")
        if not id_matches and not profile_matches and ids:
            missing_fields.append("identifier_or_search_terms")
        if scope == "specified_project" and project_targets and file.project_name not in project_targets and "explicit_file_exact" not in breakdown:
            breakdown["cross_project_guard"] = breakdown.get("cross_project_guard", -20.0)
        score = round(sum(breakdown.values()), 4)
        if score <= 0:
            continue
        rows.append(
            {
                "question_id": analysis.index,
                "candidate_file_id": file.file_id,
                "source_requirement_id": requirement["requirement_id"],
                "source_path": masked_path(file.raw_path),
                "project_name": file.project_name,
                "document_kind": file.document_kind,
                "deterministic_score": score,
                "score_breakdown": breakdown,
                "matched_fields": list_unique(matched_fields),
                "missing_fields": list_unique(missing_fields),
            }
        )
    # 同点候補でもファイル列挙順に依存しないよう、正規化済みパスとIDを最終キーにする。
    rows.sort(
        key=lambda row: (
            -float(row["deterministic_score"]),
            normalize_text(str(row.get("source_path", ""))).casefold(),
            str(row.get("candidate_file_id", "")),
        )
    )
    return rows[:top_n]


def heuristic_select_for_requirement(requirement: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {
            "requirement_id": requirement["requirement_id"],
            "selected_file_ids": [],
            "selection_status": "not_found",
            "selection_reason": "no_deterministic_candidates",
            "confidence": 0.0,
            "missing_information": list_unique(requirement.get("search_terms", [])),
            "content_checks": [],
            "selector_mode": "heuristic",
        }
    top = candidates[0]
    second = candidates[1]["deterministic_score"] if len(candidates) > 1 else 0.0
    if top["deterministic_score"] < 12:
        status = "needs_additional_search"
    elif second and top["deterministic_score"] - second < 3 and requirement.get("multiple_files_required") is not True:
        status = "ambiguous"
    else:
        status = "selected"
    selected = [row["candidate_file_id"] for row in candidates[:2 if requirement.get("multiple_files_required") else 1]]
    return {
        "requirement_id": requirement["requirement_id"],
        "selected_file_ids": selected if status != "needs_additional_search" else [],
        "selection_status": status,
        "selection_reason": "deterministic_score_gap",
        "confidence": min(top["deterministic_score"] / 100.0, 0.95),
        "missing_information": [] if status == "selected" else list_unique(requirement.get("search_terms", []))[:8],
        "content_checks": [],
        "selector_mode": "heuristic",
    }


def normalize_selector_response(parsed: dict[str, Any], requirements: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool, str]:
    if not isinstance(parsed, dict):
        return [], False, "selector_response_not_object"
    selections = parsed.get("selections")
    if selections is None and parsed.get("requirement_id"):
        selections = [parsed]
    if not isinstance(selections, list) or not selections:
        return [], False, "selections_missing"
    requirement_ids = {req["requirement_id"] for req in requirements}
    normalized = []
    for raw in selections:
        if not isinstance(raw, dict):
            continue
        req_id = str(raw.get("requirement_id", ""))
        if req_id not in requirement_ids:
            continue
        status = str(raw.get("selection_status") or "ambiguous")
        if status not in {"selected", "ambiguous", "not_found", "needs_content_check", "needs_additional_search", "planner_api_failed", "selector_api_failed", "error"}:
            status = "ambiguous"
        selected = [str(x) for x in raw.get("selected_file_ids", []) if str(x)]
        normalized.append(
            {
                "requirement_id": req_id,
                "selected_file_ids": selected,
                "selection_status": status,
                "selection_reason": compact(str(raw.get("selection_reason", "")), 500),
                "confidence": float(raw.get("confidence", 0.0) or 0.0),
                "missing_information": list_unique([str(x) for x in raw.get("missing_information", [])]),
                "content_checks": raw.get("content_checks", []) if isinstance(raw.get("content_checks", []), list) else [],
                "selector_mode": "llm",
            }
        )
    return normalized, bool(normalized), "" if normalized else "no_valid_selection"


def call_candidate_selector(
    analysis: QuestionAnalysis,
    source_plan: dict[str, Any],
    candidates_by_requirement: dict[str, list[dict[str, Any]]],
    profiles_by_file: dict[str, CompactFileProfile],
    client: OpenRouterClient | None,
    selector_model: str,
    selector_candidate_limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requirements = source_plan["source_requirements"]
    if client is None:
        selections = [heuristic_select_for_requirement(req, candidates_by_requirement.get(req["requirement_id"], [])) for req in requirements]
        return selections, {
            "question_id": analysis.index,
            "selector_mode": "heuristic",
            "api_called": False,
            "cache_hit": False,
            "model": "",
            "prompt_hash": "",
            "parse_success": False,
            "fallback_used": False,
            "fallback_reason": "",
        }
    payload = []
    for req in requirements:
        candidate_payload = []
        for candidate in candidates_by_requirement.get(req["requirement_id"], [])[:selector_candidate_limit]:
            profile = profiles_by_file.get(candidate["candidate_file_id"])
            candidate_payload.append(
                {
                    "candidate_file_id": candidate["candidate_file_id"],
                    "source_path": candidate["source_path"],
                    "project_name": candidate["project_name"],
                    "document_kind": candidate["document_kind"],
                    "deterministic_score": candidate["deterministic_score"],
                    "score_breakdown": candidate["score_breakdown"],
                    "matched_fields": candidate["matched_fields"],
                    "missing_fields": candidate["missing_fields"],
                    "compact_profile": compact(profile.summary if profile else "", 700),
                    "text_preview": compact(profile.summary if profile else "", 500),
                }
            )
        payload.append({"requirement": req, "candidates": candidate_payload})
    prompt = f"""Select source files for each requirement. Do not answer the user question.
If candidates are ambiguous or missing, say so; do not force the top candidate.
Output only JSON.

Original question:
{analysis.question_original}

Source planner result:
{json.dumps(source_plan, ensure_ascii=False)}

Candidates by requirement:
{json.dumps(payload, ensure_ascii=False)}

Return:
{{
  "selections": [
    {{
      "requirement_id": "src_1",
      "selected_file_ids": [],
      "selection_status": "selected",
      "selection_reason": "",
      "confidence": 0.0,
      "missing_information": [],
      "content_checks": []
    }}
  ]
}}
"""
    result = client.call_json("candidate_selector", prompt, max_tokens=1800, model=selector_model)
    selections, parse_success, fallback_reason = normalize_selector_response(result.parsed_json, requirements)
    fallback_used = not (result.success and parse_success)
    if fallback_used:
        selections = [heuristic_select_for_requirement(req, candidates_by_requirement.get(req["requirement_id"], [])) for req in requirements]
        for selection in selections:
            selection["selector_mode"] = "heuristic_fallback"
            selection["fallback_reason"] = result.error or fallback_reason
    meta = {
        "question_id": analysis.index,
        "selector_mode": "llm" if not fallback_used else "heuristic_fallback",
        "api_called": result.api_called,
        "cache_hit": result.cache_hit,
        "model": result.model,
        "prompt_hash": result.prompt_hash,
        "parse_success": bool(result.parse_success and parse_success),
        "fallback_used": fallback_used,
        "fallback_reason": result.error or fallback_reason,
        "raw_response_path": result.raw_response_path,
    }
    for selection in selections:
        selection.update({key: meta[key] for key in ("api_called", "cache_hit", "model", "prompt_hash", "parse_success", "fallback_used", "fallback_reason")})
        selection["question_id"] = analysis.index
    return selections, meta


def verify_content(
    analysis: QuestionAnalysis,
    requirement: dict[str, Any],
    file_id: str,
    search_records_by_file: dict[str, list[SearchRecord]],
) -> dict[str, Any]:
    terms = list_unique(
        (requirement.get("search_terms") or [])
        + (requirement.get("identifier_hints") or [])
        + (requirement.get("file_name_hints") or [])
        + question_terms(requirement.get("purpose", ""), 10)
        + question_terms(analysis.question_normalized, 10),
        30,
    )
    records = search_records_by_file.get(file_id, [])
    matched_sections: list[str] = []
    evidence_locations: list[str] = []
    matched_terms: list[str] = []
    for record in records:
        text = normalize_text(record.text).lower()
        hits = [term for term in terms if normalize_text(term).lower() and normalize_text(term).lower() in text]
        if not hits:
            continue
        matched_sections.append(record.record_type)
        location = record.metadata.get("sheet_name") or record.metadata.get("slide_number") or record.metadata.get("page_number") or record.metadata.get("table_index") or record.record_id
        evidence_locations.append(f"{record.record_type}:{location}")
        matched_terms.extend(hits)
        if len(evidence_locations) >= 5:
            break
    information_present = bool(evidence_locations)
    status = "present" if information_present else "weak_or_missing"
    additional_needed = not information_present or bool(requirement.get("multiple_files_required") and len({file_id}) < 2)
    return {
        "question_id": analysis.index,
        "file_id": file_id,
        "requirement_id": requirement["requirement_id"],
        "verification_status": status,
        "matched_sections": list_unique(matched_sections),
        "evidence_locations": list_unique(evidence_locations),
        "matched_terms": list_unique(matched_terms, 12),
        "information_present": information_present,
        "additional_source_needed": additional_needed,
        "reason": "matched_related_terms_in_search_records" if information_present else "no_related_terms_found_in_limited_check",
        "confidence": 0.75 if information_present else 0.25,
    }


def additional_search(
    analysis: QuestionAnalysis,
    requirement: dict[str, Any],
    missing_information: list[str],
    files: list[FileRecord],
    profiles_by_file: dict[str, CompactFileProfile],
    search_records_by_file: dict[str, list[SearchRecord]],
    excluded_file_ids: set[str],
    max_iterations: int,
    top_n: int,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    logs = []
    selected: list[str] = []
    verifications: list[dict[str, Any]] = []
    terms = list_unique((requirement.get("search_terms") or []) + missing_information + [requirement.get("purpose", "")], 20)
    for iteration in range(1, max_iterations + 1):
        extended = dict(requirement)
        extended["search_terms"] = terms
        candidates = deterministic_candidates_for_requirement(analysis, extended, files, profiles_by_file, top_n, excluded_file_ids | set(selected))
        new_ids = [row["candidate_file_id"] for row in candidates[:3]]
        chosen: list[str] = []
        status = "not_found"
        for file_id in new_ids:
            verification = verify_content(analysis, requirement, file_id, search_records_by_file)
            verifications.append(verification)
            if verification["information_present"]:
                chosen.append(file_id)
                status = "selected"
                break
        selected.extend(chosen)
        logs.append(
            {
                "question_id": analysis.index,
                "requirement_id": requirement["requirement_id"],
                "iteration": iteration,
                "search_reason": "content_verification_missing_information",
                "new_search_terms": terms,
                "excluded_file_ids": list(excluded_file_ids | set(selected)),
                "new_candidate_file_ids": new_ids,
                "new_selected_file_ids": chosen,
                "result_status": status,
            }
        )
        if chosen or not candidates:
            break
    return logs, selected, verifications


def make_legacy_candidate_rows(analyses: list[QuestionAnalysis], candidate_rows: list[dict[str, Any]]) -> list[CandidateFile]:
    result = []
    rank_by_key: dict[tuple[int, str], int] = defaultdict(int)
    for row in candidate_rows:
        key = (row["question_id"], row["source_requirement_id"])
        rank_by_key[key] += 1
        result.append(
            CandidateFile(
                index=row["question_id"],
                file_id=row["candidate_file_id"],
                raw_path=row["source_path"],
                rank=rank_by_key[key],
                score=float(row["deterministic_score"]),
                score_breakdown=row["score_breakdown"],
                matched_terms=row["matched_fields"],
                candidate_reason="deterministic_candidate_generator",
                confidence=min(float(row["deterministic_score"]) / 100.0, 1.0),
            )
        )
    return result


def make_execution_plan(analysis: QuestionAnalysis, final_plan: dict[str, Any]) -> ExecutionPlan:
    selected = final_plan.get("final_selected_file_ids", [])
    routes = analysis.provisional_routes or ["document_qa"]
    primary = routes[0]
    return ExecutionPlan(
        index=analysis.index,
        primary_route=primary,
        sub_routes=routes,
        execution_order=list_unique(routes + ["answer_formatting"]),
        candidate_file_ids=selected,
        candidate_search_record_ids=[],
        required_tools=[],
        requires_llm=True,
        requires_vision_model="image_ocr" in routes,
        requires_python_execution=False,
        answer_format_hint="source selection only; answer generation not implemented",
        plan_confidence=float(final_plan.get("selection_confidence", 0.0) or 0.0),
        plan_reason=final_plan.get("selection_status", ""),
        selector_source=final_plan.get("selector_mode", ""),
        selector_error=";".join(final_plan.get("errors", [])),
    )


def explicit_file_metric(analysis: QuestionAnalysis, candidates: list[dict[str, Any]], final_file_ids: list[str], files_by_id: dict[str, FileRecord]) -> dict[str, Any]:
    hints = explicit_file_hints(analysis.question_normalized)
    if not hints:
        return {"explicit_file_hit": ""}
    candidate_ids = [row["candidate_file_id"] for row in candidates]
    def matches(file_id: str) -> bool:
        file = files_by_id[file_id]
        return any(file_matches_explicit_hint(file, hint)[0] or file_matches_explicit_hint(file, hint)[1] for hint in hints)
    return {
        "exact_file_hit_at_1": any(matches(fid) for fid in candidate_ids[:1]),
        "exact_file_hit_at_5": any(matches(fid) for fid in candidate_ids[:5]),
        "exact_file_hit_at_10": any(matches(fid) for fid in candidate_ids[:10]),
        "final_selection_exact_file_hit": any(matches(fid) for fid in final_file_ids),
        "explicit_file_hit": any(matches(fid) for fid in final_file_ids),
    }


def project_metric(analysis: QuestionAnalysis, candidates: list[dict[str, Any]], final_file_ids: list[str], files_by_id: dict[str, FileRecord], files: list[FileRecord]) -> dict[str, Any]:
    projects = project_candidates(analysis.question_normalized, files)
    if not projects:
        return {"project_hit": "", "wrong_project_selected": ""}
    candidate_ids = [row["candidate_file_id"] for row in candidates]
    hit1 = bool(candidate_ids[:1] and files_by_id[candidate_ids[0]].project_name in projects)
    hit5 = any(files_by_id[fid].project_name in projects for fid in candidate_ids[:5])
    final_hit = any(files_by_id[fid].project_name in projects for fid in final_file_ids)
    wrong = any(files_by_id[fid].project_name not in projects and files_by_id[fid].project_name != "社内管理" for fid in final_file_ids)
    return {"project_hit_at_1": hit1, "project_hit_at_5": hit5, "project_hit": final_hit, "wrong_project_selected": wrong}


def pair_metric(analysis: QuestionAnalysis, final_file_ids: list[str], files_by_id: dict[str, FileRecord]) -> dict[str, Any]:
    versions = version_hints(analysis.question_normalized)
    if not versions:
        return {"pair_coverage": ""}
    selected = [files_by_id[fid] for fid in final_file_ids]
    coverage = len(selected) >= 2 or any(file.version_label for file in selected)
    return {"pair_coverage": coverage}


def compute_metrics(comparison_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(field: str) -> float | None:
        values = [row[field] for row in comparison_rows if row.get(field) not in ("", None)]
        if not values:
            return None
        return round(sum(bool(value) for value in values) / len(values), 4)
    return {
        "question_count": len(comparison_rows),
        "exact_file_hit_at_1": rate("exact_file_hit_at_1"),
        "exact_file_hit_at_5": rate("exact_file_hit_at_5"),
        "exact_file_hit_at_10": rate("exact_file_hit_at_10"),
        "final_selection_exact_file_hit": rate("final_selection_exact_file_hit"),
        "project_hit_rate": rate("project_hit"),
        "wrong_project_selection_rate": rate("wrong_project_selected"),
        "pair_coverage_rate": rate("pair_coverage"),
        "content_verification_success_count": sum(1 for row in comparison_rows if row.get("content_verification_success")),
        "additional_search_count": sum(int(row.get("additional_search_count") or 0) for row in comparison_rows),
        "ambiguous_count": sum(1 for row in comparison_rows if row.get("selection_status") == "ambiguous"),
        "not_found_count": sum(1 for row in comparison_rows if row.get("selection_status") == "not_found"),
    }


def write_review(output_dir: Path, metrics: dict[str, Any], comparison_rows: list[dict[str, Any]]) -> None:
    improved = [row for row in comparison_rows if row.get("improved_over_heuristic")]
    worsened = [row for row in comparison_rows if row.get("worse_than_heuristic")]
    bad = [row for row in comparison_rows if row.get("wrong_project_selected") is True or row.get("selection_status") in {"ambiguous", "not_found"}]
    lines = [
        "# Source Selection Review",
        "",
        "## Processing Success",
        f"- questions: {metrics['question_count']}",
        f"- content verification success count: {metrics['content_verification_success_count']}",
        f"- additional search count: {metrics['additional_search_count']}",
        "",
        "## Selection Accuracy",
        f"- Exact File Hit@1: {metrics['exact_file_hit_at_1']}",
        f"- Exact File Hit@5: {metrics['exact_file_hit_at_5']}",
        f"- Exact File Hit@10: {metrics['exact_file_hit_at_10']}",
        f"- Final Selection Exact File Hit: {metrics['final_selection_exact_file_hit']}",
        f"- Project Hit Rate: {metrics['project_hit_rate']}",
        f"- Wrong Project Selection Rate: {metrics['wrong_project_selection_rate']}",
        f"- Pair Coverage Rate: {metrics['pair_coverage_rate']}",
        "",
        "## Representative Improved Cases",
    ]
    lines += [f"- q{row['question_id']}: {row['question_type']}" for row in improved[:5]] or ["- none detected by automatic metrics"]
    lines += ["", "## Representative Worsened Or Risky Cases"]
    lines += [f"- q{row['question_id']}: status={row['selection_status']} wrong_project={row['wrong_project_selected']}" for row in (worsened + bad)[:8]] or ["- none detected by automatic metrics"]
    lines += ["", "## Notes", "- This report evaluates source selection only. It does not use valid answers or generate final answers."]
    (output_dir / "source_selection_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_source_selection_planning(
    analyses: list[QuestionAnalysis],
    files: list[FileRecord],
    search_records: list[SearchRecord],
    profiles: list[CompactFileProfile],
    output_dir: Path,
    client: OpenRouterClient | None,
    planner_model: str,
    selector_model: str,
    top_n: int,
    selector_candidate_limit: int,
    max_additional_searches: int,
    question_ids: list[int] | None = None,
    limit: int = 0,
) -> PlanningResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_analyses = select_analysis_subset(analyses, question_ids or [], limit, output_dir)
    files_by_id = {file.file_id: file for file in files}
    profiles_by_file = {profile.file_id: profile for profile in profiles}
    search_records_by_file: dict[str, list[SearchRecord]] = defaultdict(list)
    for record in search_records:
        search_records_by_file[record.file_id].append(record)

    heuristic_plans: list[dict[str, Any]] = []
    llm_plans: list[dict[str, Any]] = []
    deterministic_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    verification_rows: list[dict[str, Any]] = []
    additional_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    source_selection_results: list[dict[str, Any]] = []
    source_candidate_rows: list[dict[str, Any]] = []
    source_set_rows: list[dict[str, Any]] = []
    planner_meta_rows: list[dict[str, Any]] = []
    selector_meta_rows: list[dict[str, Any]] = []

    for analysis in selected_analyses:
        heuristic_plan = build_heuristic_source_plan(analysis, files)
        heuristic_plans.append(heuristic_plan)
        source_plan, planner_meta = call_source_planner(analysis, files, client, planner_model)
        llm_plans.append(source_plan)
        planner_meta_rows.append(planner_meta)

        candidates_by_requirement: dict[str, list[dict[str, Any]]] = {}
        for requirement in source_plan["source_requirements"]:
            req_candidates = deterministic_candidates_for_requirement(analysis, requirement, files, profiles_by_file, top_n)
            candidates_by_requirement[requirement["requirement_id"]] = req_candidates
            deterministic_rows.extend(req_candidates)

        selections, selector_meta = call_candidate_selector(
            analysis,
            source_plan,
            candidates_by_requirement,
            profiles_by_file,
            client,
            selector_model,
            selector_candidate_limit,
        )
        selector_meta_rows.append(selector_meta)
        selection_rows.extend(selections)

        final_file_ids: list[str] = []
        content_verified_ids: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        additional_count = 0
        for requirement in source_plan["source_requirements"]:
            selection = next((row for row in selections if row["requirement_id"] == requirement["requirement_id"]), None)
            if not selection:
                errors.append(f"selection_missing:{requirement['requirement_id']}")
                continue
            selected_ids = list_unique(selection.get("selected_file_ids", []), 8)
            req_verifications = []
            for file_id in selected_ids:
                verification = verify_content(analysis, requirement, file_id, search_records_by_file)
                verification_rows.append(verification)
                req_verifications.append(verification)
                content_verified_ids.append(file_id)
            if selected_ids and any(row["information_present"] for row in req_verifications):
                final_file_ids.extend(selected_ids)
            else:
                logs, new_ids, new_verifications = additional_search(
                    analysis,
                    requirement,
                    selection.get("missing_information", []),
                    files,
                    profiles_by_file,
                    search_records_by_file,
                    set(selected_ids),
                    max_additional_searches,
                    top_n,
                )
                additional_rows.extend(logs)
                verification_rows.extend(new_verifications)
                additional_count += len(logs)
                final_file_ids.extend(new_ids)
                content_verified_ids.extend(new_ids)
                if not new_ids and selection.get("selection_status") == "selected":
                    warnings.append(f"content_not_verified:{requirement['requirement_id']}")

        final_file_ids = list_unique(final_file_ids, 12)
        selection_status = "selected" if final_file_ids else "not_found"
        if any(row.get("selection_status") == "ambiguous" for row in selections) and not final_file_ids:
            selection_status = "ambiguous"
        confidence_values = [float(row.get("confidence", 0.0) or 0.0) for row in selections]
        final_plan = {
            "question_id": analysis.index,
            "question": analysis.question_normalized,
            "planner_mode": source_plan.get("planner_mode", ""),
            "selector_mode": selector_meta.get("selector_mode", ""),
            "source_requirements": source_plan["source_requirements"],
            "operations": source_plan["operations"],
            "llm_selected_file_ids": list_unique([fid for row in selections for fid in row.get("selected_file_ids", [])], 12),
            "content_verified_file_ids": list_unique(content_verified_ids, 12),
            "final_selected_file_ids": final_file_ids,
            "selection_status": selection_status,
            "selection_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
            "additional_search_count": additional_count,
            "warnings": warnings + source_plan.get("warnings", []),
            "errors": errors,
        }
        source_selection_result = resolve_source_selection(
            analysis,
            source_plan,
            candidates_by_requirement,
            final_file_ids,
            files_by_id,
            profiles_by_file,
            selection_status,
        )
        source_selection_results.append(source_selection_result)
        source_candidate_rows.extend(source_selection_result["source_candidates"])
        source_set_rows.extend(source_selection_result["source_set_candidates"])
        # Preserve the existing selected files while making the source contract explicit for downstream executors.
        final_plan["source_selection_result"] = {
            "resolved": source_selection_result["resolved"],
            "selected_source_ids": source_selection_result["selected_source_ids"],
            "selected_source_set_id": source_selection_result["selected_source_set_id"],
            "source_relation": source_selection_result["source_relation"],
            "selection_method": source_selection_result["selection_method"],
            "downstream_input_contract": source_selection_result["downstream_input_contract"],
        }
        final_rows.append(final_plan)

        heuristic_candidates = []
        for req in heuristic_plan["source_requirements"]:
            heuristic_candidates.extend(deterministic_candidates_for_requirement(analysis, req, files, profiles_by_file, 10))
        all_q_candidates = [row for rows in candidates_by_requirement.values() for row in rows]
        explicit_metrics = explicit_file_metric(analysis, all_q_candidates, final_file_ids, files_by_id)
        project_metrics = project_metric(analysis, all_q_candidates, final_file_ids, files_by_id, files)
        pair_metrics = pair_metric(analysis, final_file_ids, files_by_id)
        heuristic_top = list_unique([row["source_path"] for row in heuristic_candidates[:5]], 5)
        final_paths = [masked_path(files_by_id[fid].raw_path) for fid in final_file_ids if fid in files_by_id]
        llm_paths = [masked_path(files_by_id[fid].raw_path) for fid in final_plan["llm_selected_file_ids"] if fid in files_by_id]
        verified_paths = [masked_path(files_by_id[fid].raw_path) for fid in final_plan["content_verified_file_ids"] if fid in files_by_id]
        improved = bool(explicit_metrics.get("final_selection_exact_file_hit") and not any(path in heuristic_top for path in final_paths))
        worse = bool(explicit_metrics.get("explicit_file_hit") is False and explicit_file_hints(analysis.question_normalized))
        comparison_rows.append(
            {
                "question_id": analysis.index,
                "question": analysis.question_normalized,
                "question_type": ",".join(classify_question_types(analysis)),
                "planner_mode": final_plan["planner_mode"],
                "selector_mode": final_plan["selector_mode"],
                "source_requirement_count": len(source_plan["source_requirements"]),
                "heuristic_candidate_paths": " | ".join(heuristic_top),
                "llm_selected_paths": " | ".join(llm_paths),
                "content_verified_paths": " | ".join(verified_paths),
                "final_selected_paths": " | ".join(final_paths),
                "selection_status": selection_status,
                "selection_confidence": final_plan["selection_confidence"],
                "additional_search_count": additional_count,
                "explicit_file_hit": explicit_metrics.get("explicit_file_hit", ""),
                "exact_file_hit_at_1": explicit_metrics.get("exact_file_hit_at_1", ""),
                "exact_file_hit_at_5": explicit_metrics.get("exact_file_hit_at_5", ""),
                "exact_file_hit_at_10": explicit_metrics.get("exact_file_hit_at_10", ""),
                "final_selection_exact_file_hit": explicit_metrics.get("final_selection_exact_file_hit", ""),
                "project_hit": project_metrics.get("project_hit", ""),
                "project_hit_at_1": project_metrics.get("project_hit_at_1", ""),
                "project_hit_at_5": project_metrics.get("project_hit_at_5", ""),
                "pair_coverage": pair_metrics.get("pair_coverage", ""),
                "wrong_project_selected": project_metrics.get("wrong_project_selected", ""),
                "content_verification_success": any(row.get("information_present") for row in verification_rows if row["question_id"] == analysis.index),
                "improved_over_heuristic": improved,
                "worse_than_heuristic": worse,
                "warnings": " | ".join(final_plan["warnings"]),
                "errors": " | ".join(final_plan["errors"]),
            }
        )

    write_jsonl(output_dir / "question_analysis.jsonl", [to_dict(item) for item in selected_analyses])
    write_jsonl(output_dir / "heuristic_source_requirements.jsonl", heuristic_plans)
    write_jsonl(output_dir / "llm_source_requirements.jsonl", llm_plans)
    write_jsonl(output_dir / "deterministic_candidates.jsonl", deterministic_rows)
    write_jsonl(output_dir / "candidate_selections.jsonl", selection_rows)
    write_jsonl(output_dir / "content_verification.jsonl", verification_rows)
    write_jsonl(output_dir / "additional_searches.jsonl", additional_rows)
    write_jsonl(output_dir / "final_source_plans.jsonl", final_rows)
    write_jsonl(output_dir / "source_selection_results.jsonl", source_selection_results)
    write_jsonl(output_dir / "source_candidates.jsonl", source_candidate_rows)
    write_jsonl(output_dir / "source_set_candidates.jsonl", source_set_rows)
    write_jsonl(
        output_dir / "source_relation_evidence.jsonl",
        [
            {
                "question_id": row["question_id"],
                "selected_source_set_id": row["selected_source_set_id"],
                "source_relation": row["source_relation"],
                "source_relation_evidence": row["source_relation_evidence"],
                "project_scope_evidence": row["project_scope_evidence"],
                "version_scope_evidence": row["version_scope_evidence"],
                "resolved": row["resolved"],
                "ambiguity_detected": row["ambiguity_detected"],
            }
            for row in source_selection_results
        ],
    )
    write_csv(
        output_dir / "source_selection_verification.csv",
        [
            {
                "question_id": row["question_id"],
                "resolved": row["resolved"],
                "selected_source_count": len(row["selected_source_ids"]),
                "selected_document_roles": ";".join(row["selected_document_roles"]),
                "source_relation": row["source_relation"],
                "relation_evidence": ";".join(row["source_relation_evidence"]),
                "ambiguity_detected": row["ambiguity_detected"],
                "selection_method": row["selection_method"],
                "downstream_executor": ";".join(row["downstream_executor"]),
            }
            for row in source_selection_results
        ],
        [
            "question_id", "resolved", "selected_source_count", "selected_document_roles",
            "source_relation", "relation_evidence", "ambiguity_detected", "selection_method",
            "downstream_executor",
        ],
    )
    llm_calls = []
    if client is not None:
        llm_calls.extend(client.calls)
    write_jsonl(output_dir / "llm_calls.jsonl", llm_calls)
    comparison_fields = [
        "question_id",
        "question",
        "question_type",
        "planner_mode",
        "selector_mode",
        "source_requirement_count",
        "heuristic_candidate_paths",
        "llm_selected_paths",
        "content_verified_paths",
        "final_selected_paths",
        "selection_status",
        "selection_confidence",
        "additional_search_count",
        "explicit_file_hit",
        "project_hit",
        "pair_coverage",
        "wrong_project_selected",
        "warnings",
        "errors",
    ]
    write_csv(output_dir / "source_selection_comparison.csv", [{field: row.get(field, "") for field in comparison_fields} for row in comparison_rows], comparison_fields)
    metrics = compute_metrics(comparison_rows)
    metrics.update(
        {
            "planner_api_call_count": sum(1 for row in planner_meta_rows if row.get("api_called")),
            "selector_api_call_count": sum(1 for row in selector_meta_rows if row.get("api_called")),
            "planner_fallback_count": sum(1 for row in planner_meta_rows if row.get("fallback_used")),
            "selector_fallback_count": sum(1 for row in selector_meta_rows if row.get("fallback_used")),
            "planner_parse_success_rate": round(sum(1 for row in planner_meta_rows if row.get("parse_success")) / len(planner_meta_rows), 4) if planner_meta_rows else None,
            "selector_parse_success_rate": round(sum(1 for row in selector_meta_rows if row.get("parse_success")) / len(selector_meta_rows), 4) if selector_meta_rows else None,
        }
    )
    write_json(output_dir / "source_selection_metrics.json", metrics)
    write_review(output_dir, metrics, comparison_rows)

    legacy_candidates = make_legacy_candidate_rows(selected_analyses, deterministic_rows)
    legacy_plans = [make_execution_plan(analysis, final) for analysis, final in zip(selected_analyses, final_rows)]
    write_jsonl(output_dir / "candidate_files.jsonl", [to_dict(item) for item in legacy_candidates])
    write_jsonl(output_dir / "execution_plans.jsonl", [to_dict(item) for item in legacy_plans])
    return PlanningResult(
        analyses=selected_analyses,
        candidates=legacy_candidates,
        plans=legacy_plans,
        stats={
            "metrics": metrics,
            "planner_meta": planner_meta_rows,
            "selector_meta": selector_meta_rows,
            "final_source_plans": final_rows,
            "comparison_rows": comparison_rows,
            "llm_call_count": len(llm_calls),
        },
    )
