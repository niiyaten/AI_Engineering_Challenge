from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any

from .schemas import CompactFileProfile, FileRecord


ROLE_HINTS = {
    "contract": ("contract", "契約", "契約書"),
    "proposal": ("proposal", "提案", "提案書"),
    "schedule": ("schedule", "スケジュール", "日程", "wbs"),
    "task_list": ("task", "タスク", "課題管理"),
    "meeting_minutes": ("meeting", "議事録", "会議"),
    "report": ("report", "報告", "最終報告"),
    "management": ("management", "社内管理", "管理"),
    "analysis": ("analysis", "分析", "notebook", "モデル"),
    "reference_document": ("reference", "参照", "定義", "共通"),
}


def normalize_entity(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = re.sub(r"\s+", "", text).lower()
    return text


def _entity_list(value: str) -> list[str]:
    text = value or ""
    parts = re.split(r"[/|,、;]", text)
    return [part.strip() for part in parts if part.strip()]


def infer_role(file: FileRecord, profile: CompactFileProfile | None) -> tuple[str, list[str]]:
    """Infer a business role from path, filename, and extracted profile hints."""
    evidence = [file.file_name, file.major_folder, file.document_kind]
    if profile:
        evidence.extend([profile.summary, *profile.keywords, *profile.record_type_counts.keys()])
    text = " ".join(evidence).lower()
    if file.document_kind in ROLE_HINTS:
        return file.document_kind, [f"inventory.document_kind:{file.document_kind}"]
    for role, hints in ROLE_HINTS.items():
        matched = [hint for hint in hints if hint.lower() in text]
        if matched:
            return role, [f"text_hint:{hint}" for hint in matched]
    return "unknown", []


def build_source_selection_spec(analysis: Any, source_plan: dict[str, Any]) -> dict[str, Any]:
    requirements = source_plan.get("source_requirements", [])
    roles = []
    file_types = []
    cardinality = "single_source"
    relation = "same_project"
    for req in requirements:
        roles.extend(req.get("document_roles", []))
        file_types.extend(req.get("required_file_types", []))
        if req.get("multiple_files_required"):
            cardinality = "multiple_required_sources"
        raw_cardinality = str(req.get("source_cardinality", ""))
        if raw_cardinality in {"multiple", "all_matching", "pair"}:
            cardinality = "multiple_required_sources"
        raw_relation = str(req.get("source_relation", ""))
        if raw_relation:
            relation = {
                "cross_project": "independent_sources",
                "aggregate_sources": "master_then_detail",
                "shared_resource": "shared_reference",
                "referenced_resource": "summary_then_source",
                "version_pair": "previous_and_current_version",
                "same_project": "same_project",
            }.get(raw_relation, raw_relation)
    project_scope = list(dict.fromkeys(project for req in requirements for project in req.get("project_candidates", []) if project))
    if len(project_scope) > 1:
        cardinality = "multiple_required_sources"
    return {
        "question_scope": analysis.question_normalized,
        "required_document_roles": list(dict.fromkeys(roles)),
        "optional_document_roles": [],
        "forbidden_document_roles": [],
        "required_file_types": list(dict.fromkeys(file_types)),
        "source_cardinality": cardinality,
        "minimum_sources": 2 if cardinality == "multiple_required_sources" else 1,
        "maximum_sources": 12,
        "source_relation": relation,
        "relation_direction": "question_to_source",
        "project_scope": project_scope,
        "time_scope": [value for req in requirements for value in req.get("date_hints", [])],
        "version_scope": [value for req in requirements for value in req.get("version_hints", [])],
        "shared_source_allowed": True,
        "cross_project_source_allowed": bool(getattr(analysis, "needs_cross_project", False)),
        "relation_requirements": ["project_scope", "document_role", "content_requirement"],
        "expected_downstream_executor": list(getattr(analysis, "provisional_routes", []) or []),
        "ambiguity_policy": "suppress_if_multiple_minimal_source_sets",
    }


def _candidate(
    question_id: int,
    file: FileRecord,
    profile: CompactFileProfile | None,
    selected: bool,
    score: float,
    exclusion_reason: str = "",
) -> dict[str, Any]:
    role, role_evidence = infer_role(file, profile)
    entities = [file.project_name] if file.project_name else []
    if profile:
        entities.extend(_entity_list(profile.summary)[:8])
    return {
        "source_candidate_id": f"source_{file.file_id}",
        "question_id": question_id,
        "source_file": file.raw_path,
        "document_type": file.extension.lstrip("."),
        "document_role": role,
        "role_evidence": role_evidence,
        "title": file.file_name,
        "headings": list(profile.record_type_counts.keys()) if profile else [],
        "project_entities": list(dict.fromkeys(entities)),
        "document_date": file.date_hints,
        "document_version": file.version_label,
        "time_scope": file.date_hints,
        "project_scope_match": bool(file.project_name),
        "document_role_match": bool(role != "unknown"),
        "content_requirement_match": bool(profile and profile.summary),
        "candidate_rank": None,
        "included": selected,
        "selection_score": round(score, 4),
        "exclusion_reason": exclusion_reason,
    }


def resolve_source_selection(
    analysis: Any,
    source_plan: dict[str, Any],
    candidates_by_requirement: dict[str, list[dict[str, Any]]],
    final_file_ids: list[str],
    files_by_id: dict[str, FileRecord],
    profiles_by_file: dict[str, CompactFileProfile],
    selection_status: str,
) -> dict[str, Any]:
    """Create a conservative, evidence-bearing source set without changing execution."""
    spec = build_source_selection_spec(analysis, source_plan)
    all_candidate_ids = []
    source_candidates = []
    selected_set = set(final_file_ids)
    for rows in candidates_by_requirement.values():
        for rank, row in enumerate(rows, start=1):
            file = files_by_id.get(row.get("candidate_file_id"))
            if not file:
                continue
            candidate = _candidate(
                analysis.index,
                file,
                profiles_by_file.get(file.file_id),
                file.file_id in selected_set,
                float(row.get("deterministic_score", 0.0)),
                "" if file.file_id in selected_set else "not_selected_by_existing_source_selector",
            )
            candidate["candidate_rank"] = rank
            source_candidates.append(candidate)
            all_candidate_ids.append(candidate["source_candidate_id"])
    deduped = {row["source_candidate_id"]: row for row in source_candidates}
    source_candidates = list(deduped.values())
    selected = [row for row in source_candidates if row["included"]]
    projects = {normalize_entity(str(value)) for value in spec.get("project_scope", []) if value}
    selected_projects = {normalize_entity(str(row["project_entities"][0])) for row in selected if row["project_entities"]}
    roles = {row["document_role"] for row in selected}
    required_roles = set(spec.get("required_document_roles", [])) - {"unknown"}
    same_project = len(selected_projects) <= 1 and (not projects or selected_projects & projects)
    role_covered = not required_roles or bool(roles & required_roles)
    unique = bool(selected) and selection_status == "selected" and same_project and role_covered
    relation = "same_project" if same_project else "independent_sources"
    source_set_id = f"source_set_q{analysis.index}" if unique else ""
    relation_evidence = []
    if same_project:
        relation_evidence.append("selected_sources_share_normalized_project_entity")
    if role_covered:
        relation_evidence.append("selected_source_role_matches_requirement")
    source_set = {
        "source_set_candidate_id": source_set_id or f"source_set_candidate_q{analysis.index}",
        "member_source_candidate_ids": [row["source_candidate_id"] for row in selected],
        "primary_source": selected[0]["source_candidate_id"] if selected else "",
        "secondary_sources": [row["source_candidate_id"] for row in selected[1:]],
        "reference_sources": [],
        "source_relation": relation,
        "relation_evidence": relation_evidence,
        "required_roles_covered": sorted(required_roles & roles) if required_roles else sorted(roles),
        "missing_requirements": [] if unique else ["unique_verified_source_set"],
        "conflicting_requirements": [],
        "set_score": round(sum(float(row["selection_score"]) for row in selected), 4),
        "included": unique,
        "exclusion_reason": "" if unique else "source_relation_or_role_not_verified",
    }
    return {
        "question_id": analysis.index,
        "source_selection_spec": spec,
        "source_candidates": source_candidates,
        "source_set_candidates": [source_set],
        "selected_source_ids": [row["source_candidate_id"] for row in selected] if unique else [],
        "selected_source_set_id": source_set_id,
        "primary_source": source_set["primary_source"] if unique else "",
        "secondary_sources": source_set["secondary_sources"] if unique else [],
        "reference_sources": [],
        "selected_document_roles": sorted(roles),
        "source_relation": relation,
        "source_relation_evidence": relation_evidence,
        "project_scope_evidence": sorted(projects),
        "version_scope_evidence": spec.get("version_scope", []),
        "excluded_sources": [row["source_candidate_id"] for row in source_candidates if not row["included"]],
        "exclusion_reasons": {row["source_candidate_id"]: row["exclusion_reason"] for row in source_candidates if not row["included"]},
        "selection_method": "deterministic_metadata_resolution",
        "deterministic_or_llm": "deterministic",
        "ambiguity_detected": not unique and bool(selected),
        "conflicts": [],
        "resolved": unique,
        "downstream_executor": spec.get("expected_downstream_executor", []),
        "downstream_input_contract": {"selected_file_ids": final_file_ids if unique else [], "source_set_id": source_set_id},
    }
