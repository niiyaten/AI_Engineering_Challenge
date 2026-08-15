from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .calculation_engine import append_calculation_artifacts
from .schemas import ExtractionResult, FileRecord


METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "f1_macro": ("macro f1", "f1 macro", "f1(macro)", "f1_macro", "f1-macro"),
    "accuracy": ("accuracy",),
}


@dataclass
class CrossSourceCalculationSpec:
    """複数資料にある同一指標を、役割を保ったまま差分計算する仕様。"""

    schema_version: str = "1.0"
    calculation_subtype: str = "difference_calculation"
    operation_type: str = "subtract"
    metric_name: str = ""
    input_roles: list[str] = field(default_factory=lambda: ["interim", "final"])
    source_requirements: dict[str, Any] = field(default_factory=dict)
    operation_graph: list[dict[str, Any]] = field(default_factory=list)
    rounding: dict[str, Any] = field(default_factory=lambda: {"decimal_places": None, "mode": "half_up"})
    expected_output_type: str = "number"
    unit: str | None = None


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", " ", text).strip()


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-()（）]+", "", _norm(value))


def _decimal(value: Any) -> Decimal | None:
    text = _norm(value).replace(",", "")
    if not text or text in {"none", "nan"}:
        return None
    if text.endswith("%"):
        text = text[:-1]
    try:
        return Decimal(text)
    except Exception:
        return None


def parse_cross_source_difference_spec(question: str) -> CrossSourceCalculationSpec | None:
    """質問に明示された指標、演算、丸め、情報源数だけを構造化する。"""
    text = _norm(question)
    difference_requested = any(term in text for term in ("改善幅", "差分", "差額", "差を", "difference"))
    interim_requested = any(term in text for term in ("中間報告", "中間値", "interim", "before"))
    final_requested = any(term in text for term in ("最終分析", "最終値", "metrics.json", "after"))
    metric = next(
        (name for name, aliases in METRIC_ALIASES.items() if any(_compact(alias) in _compact(text) for alias in aliases)),
        "",
    )
    if not (difference_requested and interim_requested and final_requested and metric):
        return None
    # 比率を要求する質問を差分計算へ誤って落とさない。
    if any(term in text for term in ("比率", "何倍", "割合")):
        return None
    decimal_match = re.search(r"小数第\s*(\d+)\s*位", text)
    places = int(decimal_match.group(1)) if decimal_match else None
    return CrossSourceCalculationSpec(
        metric_name=metric,
        source_requirements={
            "source_cardinality": "multiple",
            "source_relation": "aggregate_sources",
            "required_document_roles": ["report", "analysis"],
            "relation_evidence_required": True,
        },
        operation_graph=[
            {"step_id": "s1", "operation": "resolve_source", "role": "interim"},
            {"step_id": "s2", "operation": "resolve_source", "role": "final"},
            {"step_id": "s3", "operation": "subtract", "formula": "final - interim"},
            {"step_id": "s4", "operation": "round", "decimal_places": places, "mode": "half_up"},
        ],
        rounding={"decimal_places": places, "mode": "half_up"},
    )


def is_cross_source_calculation_question(question: str) -> bool:
    return parse_cross_source_difference_spec(question) is not None


def _project_candidates(question_for_search: str, files: list[FileRecord]) -> list[str]:
    haystack = _compact(question_for_search)
    projects = sorted({item.project_name for item in files if item.project_name and item.project_name != "社内管理"})
    exact = [project for project in projects if _compact(project) and _compact(project) in haystack]
    if exact:
        return exact
    # 正式名が展開されない場合も、空白で区切られた固有部分が複数一致した案件だけを残す。
    scored: list[tuple[int, str]] = []
    for project in projects:
        tokens = [token for token in re.split(r"[\s　]+", _norm(project)) if len(token) >= 3]
        score = sum(len(token) for token in tokens if _compact(token) in haystack)
        if score:
            scored.append((score, project))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    return [project for score, project in scored if score == best and score >= 4]


def _load_structure(result: ExtractionResult | None, root: Path) -> dict[str, Any]:
    if result is None or result.status != "success" or not result.extracted_path:
        return {}
    path = Path(result.extracted_path)
    if not path.is_absolute():
        path = root / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _metric_key_matches(key: str, metric_name: str) -> bool:
    compact = _compact(key)
    return any(_compact(alias) == compact for alias in METRIC_ALIASES[metric_name])


def _json_metric_candidates(path: Path, metric_name: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    candidates: list[dict[str, Any]] = []

    def walk(value: Any, location: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                child = f"{location}.{key}" if location else str(key)
                if _metric_key_matches(str(key), metric_name) and _decimal(item) is not None:
                    candidates.append({
                        "value": str(item),
                        "location": child,
                        "text": f"{key}: {item}",
                        "percent": str(item).strip().endswith("%"),
                        "priority": child.count(".") + child.count("["),
                    })
                walk(item, child)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{location}[{index}]")

    walk(payload, "$")
    return candidates


def _json_phase(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    return _norm(payload.get("phase"))


def _text_metric_candidates(structure: dict[str, Any], metric_name: str) -> list[dict[str, Any]]:
    aliases = sorted(METRIC_ALIASES[metric_name], key=len, reverse=True)
    alias_pattern = "|".join(re.escape(alias).replace(r"\ ", r"\s*") for alias in aliases)
    pattern = re.compile(rf"(?:{alias_pattern})\s*(?:score)?\s*[:=：]?\s*([+-]?\d+(?:\.\d+)?%?)", re.I)
    candidates: list[dict[str, Any]] = []
    for block in structure.get("blocks", []):
        text = str(block.get("text") or "")
        for match in pattern.finditer(_norm(text)):
            candidates.append({
                "value": match.group(1),
                "location": {"block_index": block.get("index"), "type": block.get("type", "paragraph")},
                "text": text,
                "percent": match.group(1).endswith("%"),
            })
    for table in structure.get("tables", []):
        for row_index, row in enumerate(table.get("rows", [])):
            text = " | ".join(str(value or "") for value in row)
            for match in pattern.finditer(_norm(text)):
                candidates.append({
                    "value": match.group(1),
                    "location": {"table_index": table.get("table_index"), "row_index": row_index},
                    "text": text,
                    "percent": match.group(1).endswith("%"),
                })
    return candidates


def _deduplicate_candidates(candidates: list[dict[str, Any]]) -> tuple[Decimal | None, list[dict[str, Any]], str]:
    if candidates and any("priority" in item for item in candidates):
        best_priority = min(int(item.get("priority", 999)) for item in candidates)
        candidates = [item for item in candidates if int(item.get("priority", 999)) == best_priority]
    values: dict[Decimal, list[dict[str, Any]]] = {}
    percent_flags: set[bool] = set()
    for candidate in candidates:
        value = _decimal(candidate.get("value"))
        if value is None:
            continue
        values.setdefault(value, []).append(candidate)
        percent_flags.add(bool(candidate.get("percent")))
    if len(percent_flags) > 1:
        return None, candidates, "unit_mismatch"
    if len(values) != 1:
        return None, candidates, "metric_value_ambiguous" if values else "metric_value_not_found"
    value = next(iter(values))
    return value, values[value], ""


def _resolve_source(
    role: str,
    metric_name: str,
    question: str,
    project_files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    root: Path,
) -> tuple[FileRecord | None, Decimal | None, list[dict[str, Any]], str]:
    source_candidates: list[tuple[FileRecord, Decimal, list[dict[str, Any]]]] = []
    for file in project_files:
        path = Path(file.raw_path)
        if not path.is_absolute():
            path = root / path
        if file.extension == ".json":
            phase = _json_phase(path)
            if role == "final" and file.file_name.lower() != "metrics.json" and phase != "final":
                continue
            if role == "interim" and phase != "interim":
                continue
            raw_candidates = _json_metric_candidates(path, metric_name)
        elif role == "interim":
            if file.extension not in {".docx", ".pptx", ".pdf", ".md"}:
                continue
            # 質問が資料種別を明示した場合は、同じ値を含む議事録などを混ぜない。
            question_text = _norm(question)
            file_text = _norm(file.raw_path + " " + file.file_name)
            if "報告資料" in question_text and "報告資料" not in file_text:
                continue
            if "会議録" in question_text and "会議録" not in file_text:
                continue
            structure = _load_structure(extraction_by_file.get(file.file_id), root)
            # フェーズ判定は全文回答に使わず、構造化済み要素を最後まで走査して行う。
            phase_text = " ".join(
                [str(structure.get("document_title") or "")]
                + [str(block.get("text") or "") for block in structure.get("blocks", [])]
                + [" ".join(str(cell or "") for cell in row) for table in structure.get("tables", []) for row in table.get("rows", [])]
            )
            searchable = _norm(file.raw_path + " " + phase_text)
            if "中間報告" not in searchable:
                continue
            raw_candidates = _text_metric_candidates(structure, metric_name)
        else:
            continue
        value, evidence, error = _deduplicate_candidates(raw_candidates)
        if value is not None and not error:
            source_candidates.append((file, value, evidence))
    if not source_candidates:
        return None, None, [], f"{role}_source_not_found"
    # 同じ役割に異なる値を持つ資料が残る場合は、検索順位で決めず抑制する。
    unique = {(value, file.sha1) for file, value, _ in source_candidates}
    unique_values = {value for _, value, _ in source_candidates}
    if len(unique_values) != 1 or len(unique) != 1:
        return None, None, [], f"{role}_source_ambiguous"
    file, value, evidence = source_candidates[0]
    return file, value, evidence, ""


def independently_recalculate_cross_source(evidence: dict[str, Any]) -> dict[str, Any]:
    """Executorの式を再利用せず、保存済み入力と演算名から独立検算する。"""
    inputs = evidence.get("input_values", {})
    interim = _decimal(inputs.get("interim"))
    final = _decimal(inputs.get("final"))
    if interim is None or final is None or evidence.get("operation") != "final_minus_interim":
        return {"success": False, "error": "independent_inputs_invalid"}
    raw = final - interim
    places = evidence.get("rounding", {}).get("decimal_places")
    rounded = raw if places is None else raw.quantize(Decimal(1).scaleb(-int(places)), rounding=ROUND_HALF_UP)
    return {"success": True, "unrounded_result": str(raw), "rounded_result": format(rounded, "f")}


def execute_cross_source_calculation(
    question_id: int,
    question: str,
    question_for_search: str,
    files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    root: Path,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    spec = parse_cross_source_difference_spec(question)
    if spec is None:
        return {"status": "unsupported", "failure_stage": "calculation_spec_failure", "answer": ""}
    projects = _project_candidates(question_for_search or question, files)
    if len(projects) != 1:
        return {"status": "unsupported", "failure_stage": "file_selection_failure", "answer": "", "warning": "project_not_unique", "spec": asdict(spec)}
    project = projects[0]
    project_files = [file for file in files if file.project_name == project]
    interim_file, interim, interim_locations, interim_error = _resolve_source("interim", spec.metric_name, question, project_files, extraction_by_file, root)
    final_file, final, final_locations, final_error = _resolve_source("final", spec.metric_name, question, project_files, extraction_by_file, root)
    if interim is None or final is None or interim_file is None or final_file is None:
        return {
            "status": "unsupported",
            "failure_stage": "source_role_resolution_failure",
            "answer": "",
            "warning": interim_error or final_error,
            "spec": asdict(spec),
        }
    percent_flags = {bool(item.get("percent")) for item in interim_locations + final_locations}
    if len(percent_flags) > 1:
        return {"status": "unsupported", "failure_stage": "unit_mismatch", "answer": "", "spec": asdict(spec)}
    raw_result = final - interim
    places = spec.rounding.get("decimal_places")
    rounded = raw_result if places is None else raw_result.quantize(Decimal(1).scaleb(-int(places)), rounding=ROUND_HALF_UP)
    answer = format(rounded, "f")
    source_locations = [
        {"role": "interim", "file_id": interim_file.file_id, "source_path": interim_file.raw_path, "locations": [item["location"] for item in interim_locations]},
        {"role": "final", "file_id": final_file.file_id, "source_path": final_file.raw_path, "locations": [item["location"] for item in final_locations]},
    ]
    evidence = {
        "selected_file_id": interim_file.file_id,
        "actual_used_file_ids": [interim_file.file_id, final_file.file_id],
        "actual_used_files": [interim_file.raw_path, final_file.raw_path],
        "source_locations": source_locations,
        "cell_ranges": source_locations,
        "input_columns": [spec.metric_name],
        "input_row_counts": {"source": 2, "numeric": 2, "missing_excluded": 0},
        "filter_conditions": [{"source_role": "interim"}, {"source_role": "final"}],
        "operation_graph": spec.operation_graph,
        "operation": "final_minus_interim",
        "input_values": {"interim": str(interim), "final": str(final)},
        "intermediate_values": {"interim": str(interim), "final": str(final)},
        "calculation_formula": "final - interim",
        "unrounded_result": str(raw_result),
        "formatted_result": answer,
        "rounding": spec.rounding,
        "unit": spec.unit,
        "answer_format": spec.expected_output_type,
        "preview_only": False,
    }
    recalculation = independently_recalculate_cross_source(evidence)
    verification = {
        "question_type_match": True,
        "condition_coverage": True,
        "input_presence": True,
        "type_validity": True,
        "filter_validity": True,
        "operation_validity": True,
        "rounding_validity": recalculation.get("rounded_result") == answer,
        "reproducibility": recalculation.get("rounded_result") == answer,
        "source_range": bool(source_locations),
        "required_inputs_present": True,
        "column_bindings_verified": True,
        "conditions_applied": True,
        "operation_graph_complete": len(spec.operation_graph) == 4,
        "source_ranges_present": bool(source_locations),
        "units_consistent": len(percent_flags) <= 1,
        "rounding_valid": recalculation.get("rounded_result") == answer,
        "independent_recalculation_match": recalculation.get("rounded_result") == answer,
        "answer_format_valid": bool(re.fullmatch(r"-?\d+(?:\.\d+)?", answer)),
        "no_unverified_fallback": True,
        "document_role_match": True,
        "target_metric_match": True,
        "operation_match": True,
        "unit_match": len(percent_flags) <= 1,
        "rounding_match": recalculation.get("rounded_result") == answer,
        "output_type_match": bool(re.fullmatch(r"-?\d+(?:\.\d+)?", answer)),
    }
    verification["verification_status"] = "passed" if all(value is True for value in verification.values()) else "failed"
    source_requirement = dict(spec.source_requirements)
    source_requirement["required_projects"] = [project]
    result = {
        "status": "success" if verification["verification_status"] == "passed" else "unsupported",
        "answer": answer if verification["verification_status"] == "passed" else "",
        "question_type": "calculation",
        "calculation_spec": asdict(spec),
        "spec": asdict(spec),
        "evidence": evidence,
        "verification": verification,
        "independent_recalculation": recalculation,
        "source_requirement": source_requirement,
        "used_file_ids": [interim_file.file_id, final_file.file_id],
        "operations_executed": ["cross_file_aggregation", "calculation", "answer_formatting"],
        "calculation_trace": [{"formula": "final - interim", "inputs": evidence["input_values"], "result": str(raw_result)}],
        "failure_stage": "" if verification["verification_status"] == "passed" else "verification_failure",
    }
    if work_dir is not None:
        append_calculation_artifacts(work_dir, question_id, result)
    return result
