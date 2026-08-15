"""PPTX工程表の活動と週見出しを座標から決定的に対応付ける。"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def _normalize_text(value: str) -> str:
    """表記ゆれだけを除き、質問と活動名を安全に照合する。"""
    normalized = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"[\s\n\r\t・（）()、,，。.]", "", normalized).replace("の", "")


def is_pptx_timeline_question(question: str) -> bool:
    """週と活動の位置対応を明示する質問だけをこのRouteへ送る。"""
    text = question or ""
    has_week = "週目" in text or re.search(r"\bW\s*\d+\b", text, re.I) is not None
    return has_week and any(token in text for token in ("スケジュール", "実施予定", "予定"))


def _load_structure(extraction: Any, project_root: Path) -> dict[str, Any]:
    """既存ExtractorのExtractionResultから保存済み構造IRを読む。"""
    if extraction is None or getattr(extraction, "status", "") != "success":
        return {}
    extracted_path = getattr(extraction, "extracted_path", "")
    if not extracted_path:
        return {}
    path = Path(extracted_path)
    if not path.is_absolute():
        path = project_root / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _shape_box(shape: dict[str, Any]) -> dict[str, int]:
    return {key: int(shape.get(key, 0)) for key in ("left", "top", "width", "height")}


def _week_headers(shapes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    headers: list[dict[str, Any]] = []
    for shape in shapes:
        text = str(shape.get("text", "")).strip()
        match = re.fullmatch(r"(?:W\s*(\d+)|(?:第\s*)?(\d+)\s*週目?)", text, re.I)
        if match is None or int(shape.get("width", 0)) <= 0:
            continue
        headers.append({**shape, "week": int(match.group(1) or match.group(2))})
    headers.sort(key=lambda item: int(item["left"]))
    if len(headers) < 2 or len({item["week"] for item in headers}) != len(headers):
        return []
    return headers


def _timeline_candidates(structure: dict[str, Any]) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    candidates: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for slide in structure.get("slides", []):
        shapes = list(slide.get("shapes", []))
        headers = _week_headers(shapes)
        if headers and any("スケジュール" in str(shape.get("text", "")) for shape in shapes):
            candidates.append((slide, headers))
    return candidates


def _activity_rows(shapes: list[dict[str, Any]], header_left: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shape in shapes:
        text = str(shape.get("text", "")).strip()
        if not text or int(shape.get("left", 0)) >= header_left:
            continue
        if re.fullmatch(r"(?:W|第)?\s*\d+\s*週?目?", text, re.I):
            continue
        if "スケジュール" in text or text in {"主要活動", "フェーズ"}:
            continue
        if int(shape.get("height", 0)) <= 0:
            continue
        rows.append(shape)
    return rows


def _markers_for_row(shapes: list[dict[str, Any]], row: dict[str, Any], header_left: int) -> list[dict[str, Any]]:
    """同じ高さにある無文字図形を候補にし、線を優先する。"""
    row_center = int(row["top"]) + int(row["height"]) / 2
    matches: list[dict[str, Any]] = []
    for shape in shapes:
        if str(shape.get("text", "")).strip() or int(shape.get("left", 0)) < header_left:
            continue
        width, height = int(shape.get("width", 0)), int(shape.get("height", 0))
        if width <= 0 or height < 0:
            continue
        if abs((int(shape.get("top", 0)) + height / 2) - row_center) > max(int(row["height"]) * 0.75, 20):
            continue
        if width > 5_000_000 and "LINE" not in str(shape.get("shape_type", "")):
            continue
        matches.append(shape)
    line_matches = [item for item in matches if "LINE" in str(item.get("shape_type", ""))]
    return line_matches or matches


def _overlapping_weeks(marker: dict[str, Any], headers: list[dict[str, Any]]) -> list[int]:
    start = int(marker["left"])
    end = start + int(marker["width"])
    return [
        item["week"]
        for item in headers
        if start < int(item["left"]) + int(item["width"]) and end > int(item["left"])
    ]


def execute_pptx_timeline_lookup(
    question: str,
    selected_files: list[Any],
    extraction_by_file: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """活動名と週のどちらが質問条件かを判断して一意な位置対応を返す。"""
    if len(selected_files) != 1 or getattr(selected_files[0], "extension", "").lower() != ".pptx":
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_source_not_unique"}
    source = selected_files[0]
    structure = _load_structure(extraction_by_file.get(source.file_id), project_root)
    if not structure:
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_extraction_unavailable"}
    candidates = _timeline_candidates(structure)
    if len(candidates) != 1:
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_slide_not_unique", "ambiguous": len(candidates) > 1}
    slide, headers = candidates[0]
    shapes = list(slide.get("shapes", []))
    header_left = min(int(item["left"]) for item in headers)
    rows = _activity_rows(shapes, header_left)
    requested_week = re.search(r"(?:第\s*)?(\d+)\s*週目", question, re.I)
    normalized_question = _normalize_text(question)
    selected: list[tuple[dict[str, Any], dict[str, Any], list[int]]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        markers = _markers_for_row(shapes, row, header_left)
        if len(markers) != 1:
            excluded.append({"activity_shape_index": row.get("shape_index"), "reason": "marker_not_unique"})
            continue
        weeks = _overlapping_weeks(markers[0], headers)
        if not weeks:
            excluded.append({"activity_shape_index": row.get("shape_index"), "reason": "marker_has_no_week_overlap"})
            continue
        matches = int(requested_week.group(1)) in weeks if requested_week else _normalize_text(str(row["text"])) in normalized_question
        if matches:
            selected.append((row, markers[0], weeks))
        else:
            excluded.append({"activity_shape_index": row.get("shape_index"), "reason": "question_condition_not_matched"})
    if len(selected) != 1:
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_row_or_marker_not_unique", "ambiguous": len(selected) > 1}
    row, marker, weeks = selected[0]
    answer = str(row["text"]).splitlines()[0].strip() if requested_week else f"第{min(weeks)}週目"
    evidence = {
        "source_file": getattr(source, "raw_path", ""),
        "source_file_hash": getattr(source, "sha1", ""),
        "file_id": source.file_id,
        "slide_number": slide.get("slide_number"),
        "location": {
            "slide_number": slide.get("slide_number"),
            "activity_shape_index": row.get("shape_index"),
            "marker_shape_index": marker.get("shape_index"),
        },
        "slide_size": structure.get("slide_size", {}),
        "timeline_region": {"header_left": header_left, "header_count": len(headers)},
        "week_header_candidates": [{"shape_index": item.get("shape_index"), "week": item["week"], "box": _shape_box(item)} for item in headers],
        "selected_week_headers": [item["week"] for item in headers],
        "activity_candidates": [{"shape_index": item.get("shape_index"), "text": item.get("text", ""), "box": _shape_box(item)} for item in rows],
        "selected_activity": {"shape_index": row.get("shape_index"), "text": row.get("text", ""), "box": _shape_box(row)},
        "marker_candidates": [{"shape_index": marker.get("shape_index"), "box": _shape_box(marker)}],
        "selected_markers": [marker.get("shape_index")],
        "marker_shape_ids": [marker.get("shape_index")],
        "marker_boxes": [_shape_box(marker)],
        "coordinate_transform": "pptx_emu_identity",
        "alignment_rule": "marker_vertical_center_within_activity_row_tolerance",
        "overlap_rule": "strict_horizontal_interval_overlap",
        "matched_week": min(weeks),
        "matched_activity": str(row["text"]).splitlines()[0].strip(),
        "excluded_candidates": excluded,
        "ambiguity": False,
        "confidence": 1.0,
        "answer_raw": answer,
        "answer_normalized": answer,
    }
    verification = {
        "presence": True,
        "condition_match": True,
        "source_location": True,
        "uniqueness": True,
        "timeline_headers_unique": True,
        "marker_overlap_verified": True,
        "answer_format_valid": True,
    }
    return {
        "status": "success",
        "answer": answer,
        "evidence": [evidence],
        "verification": verification,
        "operations_executed": ["pptx_timeline_lookup"],
        "question_type": "pptx_timeline",
    }
