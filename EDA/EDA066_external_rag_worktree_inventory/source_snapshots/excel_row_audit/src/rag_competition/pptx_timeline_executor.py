"""決定的なPPTX工程表から週と活動を対応付けるExecutor。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(value: str) -> str:
    return re.sub(r"[\s\n\r\t・（）()、,，。.]", "", unicodedata.normalize("NFKC", value or "")).replace("の", "")


def is_pptx_timeline_question(question: str) -> bool:
    text = question or ""
    return ("週目" in text or re.search(r"\bW\d+\b", text, re.I) is not None) and any(token in text for token in ("スケジュール", "実施予定", "予定"))


def _week_headers(shapes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    headers = []
    for shape in shapes:
        text = str(shape.get("text", "")).strip()
        match = re.fullmatch(r"(?:W\s*(\d+)|(?:第\s*)?(\d+)\s*週目?)", text, re.I)
        if not match:
            match = re.fullmatch(r"W(\d+)", text, re.I)
        if match and int(shape.get("width", 0)) > 0:
            headers.append({**shape, "week": int(match.group(1) or match.group(2))})
    headers.sort(key=lambda item: int(item["left"]))
    if len(headers) < 2 or len({item["week"] for item in headers}) != len(headers):
        return []
    return headers


def _timeline_slide(structure: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    candidates = []
    for slide in structure.get("slides", []):
        shapes = list(slide.get("shapes", []))
        headers = _week_headers(shapes)
        if headers and any("スケジュール" in str(shape.get("text", "")) for shape in shapes):
            candidates.append((slide, headers))
    return candidates[0] if len(candidates) == 1 else (None, [])


def _activity_rows(shapes: list[dict[str, Any]], header_left: int) -> list[dict[str, Any]]:
    rows = []
    for shape in shapes:
        text = str(shape.get("text", "")).strip()
        if not text or int(shape.get("left", 0)) >= header_left:
            continue
        if re.fullmatch(r"(?:W|第)?\s*\d+\s*週?目?", text, re.I):
            continue
        if "スケジュール" in text or "主要活動" in text or "フェーズ" == text:
            continue
        if int(shape.get("top", 0)) <= 0 or int(shape.get("height", 0)) <= 0:
            continue
        rows.append(shape)
    return rows


def _marker_for_row(shapes: list[dict[str, Any]], row: dict[str, Any], header_left: int) -> list[dict[str, Any]]:
    center = int(row["top"]) + int(row["height"]) / 2
    matches = []
    for shape in shapes:
        if str(shape.get("text", "")).strip() or int(shape.get("left", 0)) < header_left:
            continue
        width, height = int(shape.get("width", 0)), int(shape.get("height", 0))
        if width <= 0 or height < 0:
            continue
        shape_center = int(shape.get("top", 0)) + height / 2
        if abs(shape_center - center) > max(int(row["height"]) * 0.75, 20):
            continue
        # 背景行の横長矩形は活動の期間マーカーではない。
        if width > 5000000 and "LINE" not in str(shape.get("shape_type", "")):
            continue
        matches.append(shape)
    # 線を持つ工程表では、同じ位置のグリッドセルより線を優先する。
    # 線がない工程表だけ矩形マーカーを候補に残す。
    line_matches = [item for item in matches if "LINE" in str(item.get("shape_type", ""))]
    return line_matches or matches


def _weeks_for_marker(marker: dict[str, Any], headers: list[dict[str, Any]]) -> list[int]:
    start = int(marker["left"])
    end = start + int(marker["width"])
    return [item["week"] for item in headers if start < int(item["left"]) + int(item["width"]) and end > int(item["left"])]


def execute_pptx_timeline_lookup(question: str, selected_files: list[Any], extraction_by_file: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if len(selected_files) != 1 or getattr(selected_files[0], "extension", "").lower() != ".pptx":
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_source_not_unique"}
    file = selected_files[0]
    structure = extraction_by_file.get(file.file_id, {}).get("structure", extraction_by_file.get(file.file_id, {}))
    slide, headers = _timeline_slide(structure)
    if slide is None:
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_slide_not_unique"}
    shapes = list(slide["shapes"])
    rows = _activity_rows(shapes, min(int(item["left"]) for item in headers))
    question_normalized = _norm(question)
    requested_week = re.search(r"(?:第)?\s*(\d+)\s*週目", question, re.I)
    selected: list[tuple[dict[str, Any], dict[str, Any], list[int]]] = []
    for row in rows:
        markers = _marker_for_row(shapes, row, min(int(item["left"]) for item in headers))
        if len(markers) != 1:
            continue
        weeks = _weeks_for_marker(markers[0], headers)
        if not weeks:
            continue
        if requested_week:
            if int(requested_week.group(1)) in weeks:
                selected.append((row, markers[0], weeks))
        elif _norm(str(row["text"])) in question_normalized:
            selected.append((row, markers[0], weeks))
    if len(selected) != 1:
        return {"status": "unsupported", "answer": "", "evidence": [], "failure_stage": "timeline_row_or_marker_not_unique", "ambiguous": len(selected) > 1}
    row, marker, weeks = selected[0]
    answer = str(row["text"]).splitlines()[0].strip() if requested_week else f"第{min(weeks)}週目"
    evidence = {
        "source_path": getattr(file, "raw_path", ""), "file_id": file.file_id,
        "location": {"slide_number": slide["slide_number"], "activity_shape_index": row["shape_index"], "marker_shape_index": marker["shape_index"]},
        "timeline_headers": [{"week": item["week"], "shape_index": item["shape_index"], "left": item["left"], "width": item["width"]} for item in headers],
        "activity_text": row["text"], "activity_bounds": {key: row[key] for key in ("left", "top", "width", "height")},
        "marker_bounds": {key: marker[key] for key in ("left", "top", "width", "height")}, "overlapping_weeks": weeks,
        "answer_value": answer,
    }
    verification = {"presence": True, "condition_match": True, "source_location": True, "uniqueness": True, "timeline_headers_unique": True, "marker_overlap_verified": True, "answer_format_valid": True}
    return {"status": "success", "answer": answer, "evidence": [evidence], "verification": verification, "operations_executed": ["pptx_timeline_lookup"], "question_type": "pptx_timeline"}
