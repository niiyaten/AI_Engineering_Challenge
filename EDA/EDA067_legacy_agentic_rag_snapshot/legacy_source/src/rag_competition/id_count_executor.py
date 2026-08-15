from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .cross_source_calculation import _project_candidates
from .schemas import ExtractionResult, FileRecord
from .source_requirements import verify_selected_sources
from .table_executor import load_table_data


ID_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "milestone_id": ("マイルストーンid", "ms id", "milestone id"),
    "task_id": ("タスクid", "task id"),
    "action_id": ("アクションid", "action id"),
    "project_id": ("案件id", "project id"),
    "customer_id": ("顧客id", "customer id"),
    "record_id": ("レコードid", "record id"),
    "ticket_id": ("チケットid", "ticket id"),
    "issue_id": ("課題id", "issue id"),
}

INVALID_VALUES = {"", "-", "nan", "none", "null", "n/a", "na", "未設定", "未発行", "該当なし"}


@dataclass
class CountSpec:
    """質問が要求する件数、情報源、重複処理を明示する実行仕様。"""

    schema_version: str = "1.0"
    operation_type: str = "id_count"
    count_semantics: str = "unique_count"
    source_requirements: dict[str, Any] = field(default_factory=dict)
    target_id_types: list[str] = field(default_factory=list)
    source_roles: list[str] = field(default_factory=list)
    selected_files: list[str] = field(default_factory=list)
    selected_tables: list[str] = field(default_factory=list)
    selected_columns: list[str] = field(default_factory=list)
    filters: list[dict[str, Any]] = field(default_factory=list)
    duplicate_policy: dict[str, str] = field(default_factory=lambda: {
        "within_source": "deduplicate",
        "across_sources": "deduplicate",
        "across_id_types": "keep_separate",
    })
    invalid_value_policy: dict[str, bool] = field(default_factory=lambda: {
        "exclude_null": True,
        "exclude_blank": True,
        "exclude_headers": True,
        "exclude_placeholders": True,
        "exclude_examples": True,
        "exclude_subtotals": True,
    })
    normalization: dict[str, bool] = field(default_factory=lambda: {
        "trim_whitespace": True,
        "normalize_case": False,
        "normalize_full_width": True,
    })
    excluded_file_types: list[str] = field(default_factory=list)
    aggregation: str = "unique_count"
    expected_output_type: str = "integer"
    ambiguity_reason: str = ""


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip()


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-:：・/]+", "", _norm(value).lower())


def normalize_id(value: Any) -> str | None:
    """重複判定に必要な範囲だけ正規化し、異なるIDの過剰な統合を避ける。"""
    text = _norm(value)
    if _compact(text) in {_compact(item) for item in INVALID_VALUES}:
        return None
    if re.fullmatch(r"[+-]?\d+\.0+", text):
        text = text.split(".", 1)[0]
    return text


def _detect_id_types(text: str) -> list[str]:
    compact = _compact(text)
    return [name for name, aliases in ID_TYPE_ALIASES.items() if any(_compact(alias) in compact for alias in aliases)]


def _extract_filter(text: str) -> list[dict[str, Any]]:
    patterns = (
        r"([一-龥々ぁ-んァ-ヶーA-Za-z]{1,20})さんが担当者に含まれる",
        r"([一-龥々ぁ-んァ-ヶーA-Za-z]{2,30})が担当する(?:タスク|案件|項目)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = re.sub(r"さん$", "", _norm(match.group(1)))
            value = re.split(r"(?:において|のplan|の計画|では|で)[、,]?", value, flags=re.IGNORECASE)[-1]
            value = value.strip("、, ")
            return [{"field_role": "assignee", "operator": "contains", "value": value}]
    return []


def build_count_spec(question: str) -> CountSpec | None:
    text = _norm(question)
    asks_count = any(term in text.lower() for term in ("いくつ", "何件", "件数", "発行数", "何個", "count", "nunique"))
    if not asks_count:
        return None
    id_types = _detect_id_types(text)
    issued = "発行" in text
    filters = _extract_filter(text)
    role_resolution_required = bool(filters) and "さん" not in text and "担当する" in text
    all_sources = len(id_types) > 1 or role_resolution_required or "複数資料" in text or "複数ファイル" in text
    if id_types:
        if issued:
            semantics = "issued_id_count"
        elif any(term in text for term in ("重複を含", "出現回数", "延べ")):
            semantics = "occurrence_count"
        elif any(term in text for term in ("空白でない", "非null", "非NULL")):
            semantics = "non_null_count"
        elif "行数" in text:
            semantics = "row_count"
        else:
            semantics = "unique_count_by_id_type" if len(id_types) > 1 else "unique_count"
    else:
        # IDを対象にしない件数質問はこのSliceでは分類だけ行い、専用の文書処理へ委ねる。
        semantics = "document_count" if any(term in text for term in ("項目", "文書", "資料")) else "occurrence_count"
    lower = text.lower()
    excludes_markdown = "以外" in text and any(term in lower for term in ("マークダウン", "markdown", ".md", "mdファイル"))
    excluded = [".md"] if excludes_markdown else []
    source_requirement = {
        "source_cardinality": "all_matching" if all_sources else "single",
        "source_relation": "referenced_resource" if role_resolution_required else "aggregate_sources" if all_sources else "same_project",
        "required_document_roles": ["schedule"] if id_types == ["task_id"] else [],
        "required_file_types": ["xlsx", "csv"] if id_types == ["task_id"] else [],
        "relation_evidence_required": True,
    }
    spec = CountSpec(
        count_semantics=semantics,
        source_requirements=source_requirement,
        target_id_types=id_types,
        source_roles=list(source_requirement["required_document_roles"]),
        filters=filters,
        excluded_file_types=excluded,
        aggregation="sum_type_counts" if len(id_types) > 1 else "unique_count",
    )
    if semantics in {"occurrence_count", "non_null_count", "row_count"}:
        spec.duplicate_policy = {"within_source": "preserve", "across_sources": "preserve", "across_id_types": "keep_separate"}
        spec.aggregation = semantics
    if not id_types:
        spec.ambiguity_reason = "count_target_is_not_an_identifier"
    return spec


def is_id_count_question(question: str) -> bool:
    spec = build_count_spec(question)
    return bool(spec and spec.target_id_types)


def _column_id_type(column: str) -> str | None:
    compact = _compact(column)
    exact = [name for name, aliases in ID_TYPE_ALIASES.items() if any(_compact(alias) == compact for alias in aliases)]
    if len(exact) == 1:
        return exact[0]
    # 英語の単なる id 列や連番列は、業務IDの根拠がないため採用しない。
    return None


def _assignee_columns(columns: list[str]) -> list[str]:
    aliases = ("担当者", "担当", "owner", "assignee", "責任者")
    return [column for column in columns if any(_compact(alias) == _compact(column) for alias in aliases)]


def _load_structure(result: ExtractionResult | None, root: Path) -> dict[str, Any]:
    if not result or result.status != "success" or not result.extracted_path:
        return {}
    path = Path(result.extracted_path)
    if not path.is_absolute():
        path = root / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _table_records(
    file: FileRecord,
    extraction: ExtractionResult,
    root: Path,
    target_types: set[str],
    filters: list[dict[str, Any]],
    resolved_filter_values: list[str] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tables = load_table_data(file, extraction, root)
    filter_values = [str(item["value"]) for item in filters] + list(resolved_filter_values or [])
    # 役割名で質問された場合は、同じWorkbookの体制表から氏名へ決定的に展開する。
    for table in tables:
        role_columns = [column for column in table.columns if _compact(column) in {_compact(value) for value in ("役割", "role", "職種", "主担当領域")}]
        person_columns = [column for column in table.columns if _compact(column) in {_compact(value) for value in ("氏名", "担当者", "name", "メンバー")}]
        if len(role_columns) == 1 and len(person_columns) == 1:
            for row in table.rows:
                role = _norm(row.get(role_columns[0], ""))
                for requested in list(filter_values):
                    if _norm(requested) and _norm(requested) in role:
                        person = _norm(row.get(person_columns[0], ""))
                        if person and person not in filter_values:
                            filter_values.append(person)
    for table in tables:
        id_columns = [(column, _column_id_type(column)) for column in table.columns]
        id_columns = [(column, kind) for column, kind in id_columns if kind in target_types]
        if not id_columns:
            continue
        assignees = _assignee_columns(table.columns)
        if filters and len(assignees) != 1:
            continue
        for row in table.rows:
            if filters:
                actual = _norm(row.get(assignees[0], ""))
                if not any(_norm(value) in actual for value in filter_values):
                    continue
            for column, id_type in id_columns:
                raw = row.get(column)
                normalized = normalize_id(raw)
                if normalized is None or _compact(raw) == _compact(column):
                    continue
                records.append({
                    "file_id": file.file_id,
                    "source_path": file.raw_path,
                    "file_type": file.extension.lstrip("."),
                    "sheet_name": table.sheet_name,
                    "table_index": None,
                    "row_index": row.get("__row_number__"),
                    "column": column,
                    "cell_reference": f"{table.sheet_name}!{column}[{row.get('__row_number__')}]",
                    "id_type": id_type,
                    "raw_id": str(raw),
                    "normalized_id": normalized,
                    "filter_values": {name: row.get(name) for name in assignees},
                })
    return records


def _role_person_candidates(structure: dict[str, Any], requested_roles: list[str]) -> list[str]:
    """段落やshapeの体制記述から、役割と氏名の明示対応だけを取得する。"""
    texts = [str(block.get("text") or "") for block in structure.get("blocks", [])]
    for slide in structure.get("slides", []):
        texts.extend(str(shape.get("text") or "") for shape in slide.get("shapes", []))
    names: list[str] = []
    person_pattern = r"([一-龥々]{1,10}[ \u3000]+[一-龥々]{1,10})"
    for role in requested_roles:
        role_pattern = re.escape(_norm(role))
        for text in texts:
            patterns_and_texts = [
                (rf"{role_pattern}\s*(?:[:：─\-]|\n)\s*{person_pattern}", _norm(text)),
            ]
            # 「氏名 ─ 役割」の逆順は同一行だけで判定し、隣の箇条書きとの誤結合を防ぐ。
            patterns_and_texts.extend(
                (rf"^{person_pattern}\s*(?:[:：─\-])\s*{role_pattern}(?:\s|$)", _norm(line))
                for line in str(text).splitlines()
            )
            for pattern, target_text in patterns_and_texts:
                match = re.search(pattern, target_text)
                if match:
                    name = _norm(match.group(1))
                    if name and name not in names:
                        names.append(name)
    return names


def _document_table_records(file: FileRecord, structure: dict[str, Any], target_types: set[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tables: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for table in structure.get("tables", []):
        tables.append((table, {"table_index": table.get("table_index")}))
    for slide in structure.get("slides", []):
        for table_index, rows in enumerate(slide.get("tables", [])):
            tables.append(({"rows": rows}, {"slide_number": slide.get("slide_number"), "table_index": table_index}))
    for table, location in tables:
        rows = table.get("rows", [])
        if len(rows) < 2:
            continue
        headers = [_norm(value) for value in rows[0]]
        id_columns = [(index, _column_id_type(header)) for index, header in enumerate(headers)]
        id_columns = [(index, kind) for index, kind in id_columns if kind in target_types]
        # 会議録の ID / Action 表は、Action列とA系IDの組合せをアクションIDとして扱う。
        if "action_id" in target_types and not id_columns:
            action_headers = {_compact(value) for value in headers}
            id_positions = [index for index, value in enumerate(headers) if _compact(value) == "id"]
            if len(id_positions) == 1 and any(value in action_headers for value in ("action", "アクション", "対応内容")):
                id_columns = [(id_positions[0], "action_id")]
        for row_index, row in enumerate(rows[1:], start=1):
            for column_index, id_type in id_columns:
                raw = row[column_index] if column_index < len(row) else ""
                normalized = normalize_id(raw)
                if normalized is None:
                    continue
                records.append({
                    "file_id": file.file_id,
                    "source_path": file.raw_path,
                    "file_type": file.extension.lstrip("."),
                    **location,
                    "row_index": row_index,
                    "column_index": column_index,
                    "column": headers[column_index],
                    "id_type": id_type,
                    "raw_id": str(raw),
                    "normalized_id": normalized,
                })
    return records


def verify_count_evidence(evidence: dict[str, Any], spec: CountSpec) -> dict[str, Any]:
    per_type = evidence.get("per_type_counts", {})
    required_types = set(spec.target_id_types)
    selected_types = set(per_type)
    if spec.count_semantics in {"occurrence_count", "non_null_count"}:
        recomputed = len(evidence.get("raw_values", []))
    elif spec.count_semantics == "row_count":
        recomputed = len({(item.get("file_id"), item.get("location_key")) for item in evidence.get("raw_values", [])})
    else:
        recomputed = sum(int(per_type[name]) for name in spec.target_id_types if name in per_type)
    checks = {
        "required_sources_present": bool(evidence.get("actual_used_file_ids")),
        "target_id_types_resolved": required_types == selected_types,
        "selected_columns_verified": bool(evidence.get("selected_columns")),
        "excluded_file_types_respected": not any(Path(path).suffix.lower() in spec.excluded_file_types for path in evidence.get("actual_used_files", [])),
        "raw_values_recorded": bool(evidence.get("raw_values")),
        "normalization_recorded": bool(evidence.get("normalization")),
        "invalid_values_removed": evidence.get("invalid_value_count") is not None,
        "duplicate_policy_applied": evidence.get("duplicate_policy") == spec.duplicate_policy,
        "per_type_counts_present": required_types == selected_types,
        "cross_source_counts_present": evidence.get("cross_source_duplicate_count") is not None,
        "final_count_reproducible": recomputed == evidence.get("final_count"),
        "answer_format_valid": isinstance(evidence.get("final_count"), int) and evidence.get("final_count", -1) >= 0,
        "no_sum_of_id_values": evidence.get("calculation_formula") != "sum(id)",
    }
    checks["verification_status"] = "passed" if all(checks.values()) else "failed"
    return checks


def execute_id_count(
    question_id: int,
    question: str,
    question_for_search: str,
    files: list[FileRecord],
    extractions: dict[str, ExtractionResult],
    root: Path,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    spec = build_count_spec(question)
    if not spec or not spec.target_id_types:
        return {"status": "unsupported", "failure_stage": "count_spec_failure", "warning": "ID件数の対象種類を確定できません"}
    projects = _project_candidates(question_for_search, files)
    if len(projects) != 1:
        return {"status": "unsupported", "failure_stage": "file_selection_failure", "warning": "対象案件を一意に確定できません", "count_spec": asdict(spec)}
    project_files = sorted(
        (item for item in files if item.project_name == projects[0] and item.extension not in spec.excluded_file_types and not item.is_temp_office_file),
        key=lambda item: (item.raw_path.casefold(), item.file_id),
    )
    target_types = set(spec.target_id_types)
    requested_roles = [str(item["value"]) for item in spec.filters if item.get("field_role") == "assignee"]
    resolved_filter_values: list[str] = []
    role_source_ids: list[str] = []
    if requested_roles:
        role_name_sources: dict[str, list[str]] = {}
        for file in project_files:
            names = _role_person_candidates(_load_structure(extractions.get(file.file_id), root), requested_roles)
            for name in names:
                role_name_sources.setdefault(name, []).append(file.file_id)
        if len(role_name_sources) > 1:
            return {"status": "unsupported", "failure_stage": "filter_resolution_failure", "warning": "役割に対応する担当者が複数あり一意に確定できません", "count_spec": asdict(spec)}
        if role_name_sources:
            resolved_filter_values = list(role_name_sources)
            source_candidates = [item for item in project_files if item.file_id in next(iter(role_name_sources.values()))]
            role_priority = {"contract": 0, "proposal": 1, "report": 2}
            source_candidates.sort(key=lambda item: (role_priority.get(item.document_kind, 9), 0 if item.version_label in {"final", ""} else 1, item.raw_path))
            role_source_ids = [source_candidates[0].file_id]
    records: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for file in project_files:
        extraction = extractions.get(file.file_id)
        if not extraction or extraction.status != "success":
            continue
        file_records: list[dict[str, Any]] = []
        if file.extension in {".xlsx", ".csv", ".tsv"}:
            file_records = _table_records(file, extraction, root, target_types, spec.filters, resolved_filter_values)
        elif not spec.filters and file.extension in {".docx", ".pptx", ".pdf"}:
            file_records = _document_table_records(file, _load_structure(extraction, root), target_types)
        if file_records:
            candidates.append({"file_id": file.file_id, "source_path": file.raw_path, "record_count": len(file_records), "document_role": file.document_kind})
            records.extend(file_records)
    found_types = {item["id_type"] for item in records}
    if found_types != target_types:
        return {"status": "unsupported", "failure_stage": "id_type_resolution_failure", "warning": "質問対象のID種類をすべて解決できません", "count_spec": asdict(spec), "record_candidates": records, "candidate_files": candidates}
    used_ids = sorted({item["file_id"] for item in records} | set(role_source_ids))
    used_files = [item for item in project_files if item.file_id in used_ids]
    spec.selected_files = [item.raw_path for item in used_files]
    spec.selected_tables = sorted({str(item.get("sheet_name") or f"table:{item.get('table_index')}") for item in records})
    spec.selected_columns = sorted({item["column"] for item in records})
    spec.source_requirements["required_projects"] = projects
    source_verification = verify_selected_sources(spec.source_requirements, used_files, content_verified_file_ids=set(used_ids))
    if source_verification["verification_status"] != "passed":
        return {"status": "unsupported", "failure_stage": "source_relation_failure", "warning": "情報源数または案件関係を検証できません", "count_spec": asdict(spec), "record_candidates": records, "source_verification": source_verification}
    unique_keys = {(item["id_type"], item["normalized_id"]) for item in records}
    if spec.count_semantics in {"occurrence_count", "non_null_count"}:
        per_type = {id_type: sum(item["id_type"] == id_type for item in records) for id_type in spec.target_id_types}
    elif spec.count_semantics == "row_count":
        per_type = {id_type: len({(item["file_id"], item.get("sheet_name"), item.get("table_index"), item.get("row_index")) for item in records if item["id_type"] == id_type}) for id_type in spec.target_id_types}
    else:
        per_type = {id_type: len({value for kind, value in unique_keys if kind == id_type}) for id_type in spec.target_id_types}
    final_count = sum(per_type.values())
    raw_counts = {id_type: sum(item["id_type"] == id_type for item in records) for id_type in spec.target_id_types}
    evidence = {
        "actual_used_file_ids": used_ids,
        "actual_used_files": [item.raw_path for item in used_files],
        "selected_tables": spec.selected_tables,
        "selected_columns": spec.selected_columns,
        "source_locations": [{key: item.get(key) for key in ("file_id", "sheet_name", "slide_number", "table_index", "row_index", "column", "cell_reference")} for item in records],
        "raw_values": [{"id_type": item["id_type"], "raw_id": item["raw_id"], "normalized_id": item["normalized_id"], "file_id": item["file_id"], "location_key": f"{item.get('sheet_name')}:{item.get('table_index')}:{item.get('row_index')}"} for item in records],
        "raw_counts": raw_counts,
        "invalid_value_count": 0,
        "duplicate_count_before": len(records),
        "duplicate_count_after": len(unique_keys),
        "cross_source_duplicate_count": len(records) - len(unique_keys),
        "per_type_counts": per_type,
        "final_count": final_count,
        "count_semantics": spec.count_semantics,
        "normalization": spec.normalization,
        "duplicate_policy": spec.duplicate_policy,
        "invalid_value_policy": spec.invalid_value_policy,
        "filters": spec.filters,
        "resolved_filter_values": resolved_filter_values,
        "calculation_formula": "sum(unique_count((id_type, normalized_id)) per id_type)",
        "cell_ranges": [{"file_id": item["file_id"], "location": item.get("cell_reference") or {"slide_number": item.get("slide_number"), "table_index": item.get("table_index"), "row_index": item.get("row_index")}} for item in records],
        "preview_only": False,
    }
    verification = verify_count_evidence(evidence, spec)
    result = {
        "status": "success" if verification["verification_status"] == "passed" else "unsupported",
        "failure_stage": "" if verification["verification_status"] == "passed" else "verification_failure",
        "answer": str(final_count) if verification["verification_status"] == "passed" else "",
        "question_type": "id_count",
        "count_spec": asdict(spec),
        "source_requirement": spec.source_requirements,
        "used_file_ids": used_ids,
        "record_candidates": records,
        "evidence": evidence,
        "verification": verification,
        "source_verification": source_verification,
        "operations_executed": ["table_lookup", "table_filter", "table_aggregation", "calculation", "answer_formatting"],
    }
    if work_dir:
        work_dir.mkdir(parents=True, exist_ok=True)
        for name, row in {
            "count_specs.jsonl": {"question_id": question_id, "count_spec": asdict(spec)},
            "id_count_execution_evidence.jsonl": {"question_id": question_id, "evidence": evidence},
            "id_count_verification.jsonl": {"question_id": question_id, "verification": verification},
        }.items():
            with (work_dir / name).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return result


def independently_recalculate_count(evidence: dict[str, Any]) -> int | None:
    """Executorの集計関数を使わず、保存されたID値だけから検算する。"""
    values = evidence.get("raw_values")
    if not isinstance(values, list):
        return None
    semantics = evidence.get("count_semantics", "unique_count")
    valid = [item for item in values if item.get("id_type") and item.get("normalized_id")]
    if semantics in {"occurrence_count", "non_null_count"}:
        return len(valid)
    if semantics == "row_count":
        return len({(str(item.get("file_id")), str(item.get("location_key"))) for item in valid})
    return len({(str(item.get("id_type")), str(item.get("normalized_id"))) for item in valid})
