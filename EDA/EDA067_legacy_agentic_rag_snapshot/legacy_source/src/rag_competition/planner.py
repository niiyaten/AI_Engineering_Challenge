from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .io_utils import write_jsonl
from .llm_client import OpenRouterClient
from .schemas import CandidateFile, CompactFileProfile, ExecutionPlan, FileRecord, QuestionAnalysis, SearchRecord, to_dict
from .search import BM25Index, tokenize


ROUTE_TOOL_MAP = {
    "document_qa": ["text_search", "llm_answering"],
    "table_lookup": ["table_reader"],
    "calculation": ["table_reader", "python_calculation_later"],
    "format_extraction": ["structure_json_reader"],
    "diff_comparison": ["version_pairing", "diff_reader"],
    "image_ocr": ["image_metadata", "vision_later"],
    "code_execution": ["static_code_reader"],
    "cross_file_aggregation": ["cross_file_table"],
    "location_lookup": ["document_reader", "location_reader"],
}

SUPPORTED_FILE_TYPES = {"docx", "pptx", "xlsx", "pdf", "png", "jpg", "jpeg", "csv", "tsv", "json", "py", "ipynb", "md", "txt"}


def list_strings(value: object, allowed: set[str] | None = None, limit: int = 20) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for raw in value:
        text = str(raw).strip().lstrip(".").lower()
        if not text:
            continue
        if allowed is not None and text not in allowed:
            continue
        if text not in items:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def llm_source_plan(analysis: QuestionAnalysis, files: list[FileRecord], client: OpenRouterClient | None) -> QuestionAnalysis:
    if client is None:
        return analysis
    project_names = sorted({file.project_name for file in files if file.project_name})[:80]
    extension_counts = Counter(file.extension.lstrip(".") for file in files if file.extension)
    folder_counts = Counter(file.major_folder for file in files if file.major_folder)
    prompt = f"""質問の参照元候補を探す前に、質問の処理方針をJSONで計画してください。
質問: {analysis.question_normalized}
ルールベース暫定route: {analysis.provisional_routes}
ルールベース必要ファイル形式: {analysis.required_file_types}
資料内の案件・会社候補: {project_names}
拡張子分布: {dict(extension_counts)}
フォルダ種別分布: {dict(folder_counts)}

JSONだけで返してください。
形式:
{{
  "provisional_routes": ["document_qa"],
  "required_file_types": ["docx"],
  "document_hints": ["提案書"],
  "identifier_hints": [],
  "date_hints": [],
  "project_candidates": [],
  "needs_multiple_files": false,
  "needs_cross_project": false,
  "reason": "短い理由"
}}
"""
    result = client.call_json("source_planner", prompt)
    if not result.success:
        analysis.planner_source = "heuristic_fallback"
        analysis.planner_error = result.error
        return analysis

    parsed = result.parsed_json
    routes = list_strings(parsed.get("provisional_routes"), set(ROUTE_TOOL_MAP), limit=8)
    file_types = list_strings(parsed.get("required_file_types"), SUPPORTED_FILE_TYPES, limit=12)
    if routes:
        analysis.provisional_routes = routes
    if file_types:
        analysis.required_file_types = file_types
    for attr in ("document_hints", "identifier_hints", "date_hints", "project_candidates"):
        values = list_strings(parsed.get(attr), None, limit=20)
        if values:
            setattr(analysis, attr, values)
    if isinstance(parsed.get("needs_multiple_files"), bool):
        analysis.needs_multiple_files = parsed["needs_multiple_files"]
    if isinstance(parsed.get("needs_cross_project"), bool):
        analysis.needs_cross_project = parsed["needs_cross_project"]
    analysis.planner_source = "llm"
    analysis.planner_error = ""
    return analysis


def project_candidates(question: str, files: list[FileRecord]) -> list[str]:
    projects = sorted({file.project_name for file in files if file.project_name and file.project_name != "社内管理"}, key=len, reverse=True)
    return [project for project in projects if project in question]


def keyword_terms(question: str) -> list[str]:
    terms = [term for term in tokenize(question) if len(term) >= 2]
    return list(dict.fromkeys(terms))[:40]


def route_document_kind_score(routes: list[str], file: FileRecord) -> float:
    score = 0.0
    if "diff_comparison" in routes and file.version_label:
        score += 2.0
    if "format_extraction" in routes and file.extension in {".docx", ".pptx", ".xlsx"}:
        score += 2.5
    if ("table_lookup" in routes or "calculation" in routes) and file.extension in {".xlsx", ".csv", ".tsv"}:
        score += 3.0
    if "image_ocr" in routes and file.extension in {".png", ".jpg", ".jpeg", ".pdf", ".pptx", ".docx"}:
        score += 2.0
    if "code_execution" in routes and file.extension in {".py", ".ipynb"}:
        score += 3.0
    if "document_qa" in routes and file.extension in {".docx", ".pptx", ".pdf", ".md"}:
        score += 1.5
    return score


def build_file_search_scores(question: str, search_records: list[SearchRecord], top_k: int = 80) -> dict[str, tuple[float, list[str], list[str]]]:
    index = BM25Index(search_records)
    scores: dict[str, float] = defaultdict(float)
    terms: dict[str, list[str]] = defaultdict(list)
    record_ids: dict[str, list[str]] = defaultdict(list)
    for hit in index.search(question, top_k=top_k):
        scores[hit.record.file_id] += hit.score
        record_ids[hit.record.file_id].append(hit.record.record_id)
        for term in hit.matched_terms:
            if term not in terms[hit.record.file_id]:
                terms[hit.record.file_id].append(term)
    return {file_id: (score, terms[file_id], record_ids[file_id]) for file_id, score in scores.items()}


def candidate_files_for_question(
    analysis: QuestionAnalysis,
    files: list[FileRecord],
    search_records: list[SearchRecord],
    top_n: int = 12,
) -> tuple[QuestionAnalysis, list[CandidateFile], dict[str, list[str]]]:
    """質問解析と検索結果を組み合わせ、候補ファイルを上位順に返す。"""
    search_question = analysis.question_for_search or analysis.question_normalized
    analysis.project_candidates = project_candidates(search_question, files)
    terms = keyword_terms(search_question)
    content_scores = build_file_search_scores(search_question, search_records)
    candidate_record_ids: dict[str, list[str]] = {}
    candidates: list[CandidateFile] = []
    for file in files:
        breakdown: dict[str, float] = {}
        matched: list[str] = []
        if analysis.project_candidates and file.project_name in analysis.project_candidates:
            breakdown["project_match"] = 6.0
            matched.append(file.project_name)
        elif not analysis.project_candidates and file.project_name and any(term in file.raw_path for term in terms):
            breakdown["path_term_match"] = 2.0
        if any(hint and hint in file.file_name for hint in analysis.document_hints):
            breakdown["document_hint_match"] = 8.0
            matched.extend([hint for hint in analysis.document_hints if hint in file.file_name])
        if file.extension.lstrip(".") in analysis.required_file_types:
            breakdown["required_file_type_match"] = 3.0
            matched.append(file.extension)
        kind_score = route_document_kind_score(analysis.provisional_routes, file)
        if kind_score:
            breakdown["route_kind_match"] = kind_score
        if analysis.date_hints and any(date in file.raw_path for date in analysis.date_hints):
            breakdown["date_hint_match"] = 3.0
            matched.extend(analysis.date_hints)
        if analysis.identifier_hints and any(hint in file.raw_path for hint in analysis.identifier_hints):
            breakdown["identifier_path_match"] = 2.0
            matched.extend([hint for hint in analysis.identifier_hints if hint in file.raw_path])
        content_score, content_terms, record_ids = content_scores.get(file.file_id, (0.0, [], []))
        if content_score:
            breakdown["content_bm25"] = min(content_score / 8.0, 8.0)
            matched.extend(content_terms[:8])
            candidate_record_ids[file.file_id] = record_ids[:8]
        score = sum(breakdown.values())
        if score <= 0:
            continue
        candidates.append(
            CandidateFile(
                index=analysis.index,
                file_id=file.file_id,
                raw_path=file.raw_path,
                rank=0,
                score=round(score, 4),
                score_breakdown=breakdown,
                matched_terms=list(dict.fromkeys(matched))[:20],
                candidate_reason=", ".join(breakdown.keys()),
                confidence=min(score / 20.0, 1.0),
            )
        )
    # 検索スコア同点時の順位を入力列挙順から切り離す。
    candidates.sort(key=lambda item: (-item.score, item.raw_path.casefold(), item.file_id))
    for rank, candidate in enumerate(candidates[:top_n], start=1):
        candidate.rank = rank
    return analysis, candidates[:top_n], candidate_record_ids


def llm_select_candidates(
    analysis: QuestionAnalysis,
    candidates: list[CandidateFile],
    profiles_by_file: dict[str, CompactFileProfile],
    client: OpenRouterClient | None,
) -> tuple[list[CandidateFile], str, str]:
    if client is None or not candidates:
        return candidates, "heuristic", ""
    candidate_payload = []
    for candidate in candidates[:12]:
        profile = profiles_by_file.get(candidate.file_id)
        candidate_payload.append(
            {
                "file_id": candidate.file_id,
                "raw_path": candidate.raw_path,
                "score": candidate.score,
                "reason": candidate.candidate_reason,
                "profile": profile.summary[:800] if profile else "",
            }
        )
    prompt = f"""次の質問に答えるために参照すべきファイル候補を選んでください。
質問: {analysis.question_normalized}
暫定route: {analysis.provisional_routes}
候補:
{json.dumps(candidate_payload, ensure_ascii=False)}

JSONだけで返してください。
形式:
{{"selected_file_ids":["file_x"],"primary_route":"document_qa","sub_routes":["document_qa"],"execution_order":["document_qa"],"reason":"短い理由"}}
"""
    result = client.call_json("candidate_selector", prompt)
    if not result.success:
        return candidates, "heuristic_fallback", result.error
    selected_ids = result.parsed_json.get("selected_file_ids") or []
    if not isinstance(selected_ids, list) or not selected_ids:
        return candidates, "llm_empty_fallback", ""
    selected_set = {str(value) for value in selected_ids}
    selected = [candidate for candidate in candidates if candidate.file_id in selected_set]
    rest = [candidate for candidate in candidates if candidate.file_id not in selected_set]
    ordered = selected + rest
    for rank, candidate in enumerate(ordered, start=1):
        candidate.rank = rank
        candidate.selector_source = "llm"
    return ordered, "llm", ""


def build_execution_plan(
    analysis: QuestionAnalysis,
    candidates: list[CandidateFile],
    candidate_record_ids: dict[str, list[str]],
    selector_source: str,
    selector_error: str = "",
) -> ExecutionPlan:
    routes = list(dict.fromkeys(analysis.provisional_routes))
    primary = routes[0] if routes else "document_qa"
    if len(routes) == 1 and primary == "calculation":
        sub_routes = ["table_lookup", "calculation"]
    elif primary == "diff_comparison":
        sub_routes = ["diff_comparison", "answer_formatting"]
    else:
        sub_routes = routes
    execution_order = list(dict.fromkeys(sub_routes + ["answer_formatting"]))
    file_ids = [candidate.file_id for candidate in candidates[:8]]
    record_ids: list[str] = []
    for file_id in file_ids:
        record_ids.extend(candidate_record_ids.get(file_id, [])[:4])
    tools: list[str] = []
    for route in sub_routes:
        tools.extend(ROUTE_TOOL_MAP.get(route, []))
    reason = "候補ファイルの拡張子、パス、本文検索スコアから計画を作成"
    return ExecutionPlan(
        index=analysis.index,
        primary_route=primary,
        sub_routes=sub_routes,
        execution_order=execution_order,
        candidate_file_ids=file_ids,
        candidate_search_record_ids=list(dict.fromkeys(record_ids))[:20],
        required_tools=list(dict.fromkeys(tools)),
        requires_llm=True,
        requires_vision_model="image_ocr" in sub_routes,
        requires_python_execution=False,
        answer_format_hint="質問文の指定に従う",
        plan_confidence=candidates[0].confidence if candidates else 0.0,
        plan_reason=reason,
        selector_source=selector_source,
        selector_error=selector_error,
    )


def plan_all(
    analyses: list[QuestionAnalysis],
    files: list[FileRecord],
    search_records: list[SearchRecord],
    profiles: list[CompactFileProfile],
    output_dir: Path,
    client: OpenRouterClient | None = None,
    top_n: int = 12,
) -> tuple[list[QuestionAnalysis], list[CandidateFile], list[ExecutionPlan]]:
    profiles_by_file = {profile.file_id: profile for profile in profiles}
    updated_analyses: list[QuestionAnalysis] = []
    all_candidates: list[CandidateFile] = []
    plans: list[ExecutionPlan] = []
    for analysis in analyses:
        planned = llm_source_plan(analysis, files, client)
        updated, candidates, candidate_record_ids = candidate_files_for_question(planned, files, search_records, top_n=top_n)
        candidates, selector_source, selector_error = llm_select_candidates(updated, candidates, profiles_by_file, client)
        plan = build_execution_plan(updated, candidates, candidate_record_ids, selector_source, selector_error)
        updated_analyses.append(updated)
        all_candidates.extend(candidates)
        plans.append(plan)

    write_jsonl(output_dir / "question_analysis.jsonl", [to_dict(item) for item in updated_analyses])
    write_jsonl(output_dir / "candidate_files.jsonl", [to_dict(item) for item in all_candidates])
    write_jsonl(output_dir / "execution_plans.jsonl", [to_dict(item) for item in plans])
    return updated_analyses, all_candidates, plans
