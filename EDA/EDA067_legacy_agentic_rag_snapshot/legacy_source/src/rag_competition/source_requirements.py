from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict
from typing import Any

from .schemas import FileRecord, SourceRequirement


FILE_NAME_PATTERN = re.compile(r"[^\s、。]+\.(?:docx|pptx|xlsx|pdf|csv|tsv|py|ipynb)", re.IGNORECASE)


def _normalize(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def infer_source_requirement(
    question: str,
    *,
    required_projects: list[str] | None = None,
    required_document_roles: list[str] | None = None,
    required_file_types: list[str] | None = None,
) -> SourceRequirement:
    """質問の明示表現から、必要な情報源数と関係を保守的に推定する。"""
    text = _normalize(question)
    lower = text.lower()
    explicit_names = list(dict.fromkeys(match.group(0).strip("()[]{}『』「」") for match in FILE_NAME_PATTERN.finditer(text)))
    version_terms = re.findall(r"(?:old|new|v\d+|r\d+|rev\d+|旧版|新版|変更前|変更後)", lower, re.IGNORECASE)

    # 異なる役割の資料にある値を用いる計算は、単一資料として扱わない。
    source_markers = sum(
        bool(re.search(pattern, text, re.IGNORECASE))
        for pattern in (r"中間報告|中間値|interim|before", r"最終分析|最終値|metrics\.json|after")
    )
    cross_source_calculation = source_markers >= 2 and any(term in text for term in ("改善幅", "差分", "差額", "差を"))

    if cross_source_calculation:
        cardinality, relation = "multiple", "aggregate_sources"
    elif re.search(r"(?:^|[^A-Za-z0-9])M\d+\s*資料", text, re.IGNORECASE):
        cardinality, relation = "all_matching", "same_project"
    elif any(term in text for term in ("全案件", "各案件", "案件横断", "全社", "横断集計")):
        cardinality, relation = "all_matching", "cross_project"
    elif len(version_terms) >= 2 or (version_terms and any(term in text for term in ("版間", "差分", "比較"))):
        cardinality, relation = "pair", "version_pair"
    elif any(term in text for term in ("複数資料", "複数ファイル", "照合", "突合", "合算", "集約")):
        cardinality, relation = "multiple", "aggregate_sources"
    elif len(explicit_names) > 1:
        cardinality, relation = "multiple", "referenced_resource"
    else:
        cardinality = "single"
        relation = "same_project" if required_projects else "unknown"

    return SourceRequirement(
        source_cardinality=cardinality,
        source_relation=relation,
        required_projects=list(dict.fromkeys(required_projects or [])),
        required_document_roles=list(dict.fromkeys(required_document_roles or [])),
        required_file_types=list(dict.fromkeys(required_file_types or [])),
        explicit_file_names=explicit_names,
        version_constraints=list(dict.fromkeys(version_terms)),
    )


def source_requirement_dict(requirement: SourceRequirement) -> dict[str, Any]:
    return asdict(requirement)


def verify_selected_sources(
    requirement: SourceRequirement | dict[str, Any],
    selected_files: list[FileRecord],
    *,
    content_verified_file_ids: set[str] | None = None,
) -> dict[str, Any]:
    """選択ファイル数と案件関係がSourceRequirementを満たすか検証する。"""
    data = asdict(requirement) if isinstance(requirement, SourceRequirement) else dict(requirement)
    cardinality = str(data.get("source_cardinality") or "single")
    relation = str(data.get("source_relation") or "unknown")
    required_projects = {_normalize(value) for value in data.get("required_projects", []) if _normalize(value)}
    explicit_names = {_normalize(name).lower() for name in data.get("explicit_file_names", [])}
    verified_content = content_verified_file_ids or set()
    count = len(selected_files)
    cardinality_match = {
        "single": count == 1,
        "pair": count == 2,
        "multiple": count >= 2,
        "all_matching": count >= 1,
    }.get(cardinality, False)

    source_rows: list[dict[str, Any]] = []
    for file in selected_files:
        same_project = bool(required_projects and _normalize(file.project_name) in required_projects)
        explicitly_referenced = _normalize(file.file_name).lower() in explicit_names
        content_verified = file.file_id in verified_content
        relation_evidence = "same_project" if same_project else "explicitly_referenced" if explicitly_referenced else "content_verified" if content_verified else ""
        source_rows.append(
            {
                "file_id": file.file_id,
                "source_path": file.raw_path,
                "question_project": sorted(required_projects),
                "file_project": file.project_name,
                "file_role": file.document_kind,
                "source_relation": relation,
                "project_relation_verified": bool(relation_evidence),
                "relation_evidence": relation_evidence,
            }
        )

    relation_match = bool(source_rows) and all(row["project_relation_verified"] for row in source_rows)
    return {
        "source_cardinality_match": cardinality_match,
        "source_relation_match": relation_match,
        "source_cardinality": cardinality,
        "source_relation": relation,
        "selected_file_count": count,
        "sources": source_rows,
        "verification_status": "passed" if cardinality_match and relation_match else "failed",
    }
