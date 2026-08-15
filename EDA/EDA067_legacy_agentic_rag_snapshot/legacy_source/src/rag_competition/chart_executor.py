"""Deterministic readers for native Excel ChartEx series metadata."""

from __future__ import annotations

import re
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from openpyxl import load_workbook

from .schemas import FileRecord


_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_DOC_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_DRAWING_NS = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
_CHART_EX_NS = "{http://schemas.microsoft.com/office/drawing/2014/chartex}"
_GRAPH = "\u30b0\u30e9\u30d5"


def _normalize(value: object) -> str:
    return re.sub(r"[\s_\-]+", "", str(value or "")).casefold()


def _resolve_part(base_part: str, target: str) -> str:
    """Resolve an OOXML relationship target without relying on archive order."""
    return posixpath.normpath(str(PurePosixPath(base_part).parent.joinpath(target)).replace("\\", "/"))


def _relationships(archive: zipfile.ZipFile, rel_path: str) -> dict[str, str]:
    if rel_path not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read(rel_path))
    return {
        item.attrib["Id"]: item.attrib["Target"]
        for item in root.findall(f"{_REL_NS}Relationship")
        if item.attrib.get("Id") and item.attrib.get("Target")
    }


def _sheet_matches_question(question: str, sheet_names: list[str]) -> list[str]:
    normalized_question = _normalize(question)
    matches: list[str] = []
    for sheet_name in sheet_names:
        normalized_name = _normalize(sheet_name)
        if not normalized_name:
            continue
        if normalized_name.isascii() and normalized_name.isalnum():
            pattern = rf"(?<![a-z0-9]){re.escape(normalized_name)}(?![a-z0-9]|\.(?:xlsx|xlsm|csv|tsv))"
            if re.search(pattern, normalized_question):
                matches.append(sheet_name)
        elif normalized_name in normalized_question:
            matches.append(sheet_name)
    return matches


def _requested_graph_number(question: str) -> int | None:
    values = {int(value) for value in re.findall(_GRAPH + r"\s*(\d+)", question)}
    return next(iter(values)) if len(values) == 1 else None


def is_chart_series_question(question: str) -> bool:
    """Recognize a request for a chart's source column, not rendered values."""
    text = str(question or "")
    return _GRAPH in text and ("\u30ab\u30e9\u30e0" in text or "\u53ef\u8996\u5316" in text or "column" in text.casefold())


def _workbook_sheets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = _relationships(archive, "xl/_rels/workbook.xml.rels")
    sheets: dict[str, str] = {}
    for sheet in workbook.findall(f".//{_MAIN_NS}sheet"):
        name = sheet.attrib.get("name", "")
        target = relationships.get(sheet.attrib.get(f"{_DOC_REL_NS}id", ""))
        if name and target:
            sheets[name] = _resolve_part("xl/workbook.xml", target)
    return sheets


def _chart_part_for_object(archive: zipfile.ZipFile, sheet_part: str, graph_number: int) -> tuple[str, dict[str, Any]] | None:
    sheet_root = ET.fromstring(archive.read(sheet_part))
    drawing = sheet_root.find(f"{_MAIN_NS}drawing")
    if drawing is None:
        return None
    sheet_rels = _relationships(archive, f"{PurePosixPath(sheet_part).parent}/_rels/{PurePosixPath(sheet_part).name}.rels")
    drawing_target = sheet_rels.get(drawing.attrib.get(f"{_DOC_REL_NS}id", ""))
    if not drawing_target:
        return None
    drawing_part = _resolve_part(sheet_part, drawing_target)
    drawing_rels = _relationships(archive, f"{PurePosixPath(drawing_part).parent}/_rels/{PurePosixPath(drawing_part).name}.rels")
    drawing_root = ET.fromstring(archive.read(drawing_part))
    candidates: list[tuple[str, dict[str, Any]]] = []
    anchors = drawing_root.findall(f"{_DRAWING_NS}twoCellAnchor") + drawing_root.findall(f"{_DRAWING_NS}oneCellAnchor")
    for anchor in anchors:
        frame = anchor.find(f".//{_DRAWING_NS}graphicFrame")
        if frame is None:
            continue
        name_node = frame.find(f".//{_DRAWING_NS}cNvPr")
        object_name = name_node.attrib.get("name", "") if name_node is not None else ""
        match = re.fullmatch(_GRAPH + r"\s*(\d+)", object_name.strip())
        chart = frame.find(f".//{_CHART_EX_NS}chart")
        if not match or int(match.group(1)) != graph_number or chart is None:
            continue
        target = drawing_rels.get(chart.attrib.get(f"{_DOC_REL_NS}id", ""))
        if not target:
            continue
        anchor_from = anchor.find(f"{_DRAWING_NS}from")
        candidates.append((
            _resolve_part(drawing_part, target),
            {
                "drawing_part": drawing_part,
                "object_name": object_name,
                "anchor_from": {
                    "row": int(anchor_from.findtext(f"{_DRAWING_NS}row", "0")) + 1 if anchor_from is not None else None,
                    "column": int(anchor_from.findtext(f"{_DRAWING_NS}col", "0")) + 1 if anchor_from is not None else None,
                },
            },
        ))
    return candidates[0] if len(candidates) == 1 else None


def _defined_name_reference(archive: zipfile.ZipFile, name: str) -> tuple[str, str] | None:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    matches = [node.text or "" for node in workbook.findall(f".//{_MAIN_NS}definedName") if node.attrib.get("name") == name]
    if len(matches) != 1:
        return None
    match = re.fullmatch(r"(?:'([^']+)'|([^!]+))!\$?([A-Z]+)\$?(\d+)", matches[0].strip())
    if not match:
        return None
    return (match.group(1) or match.group(2), f"{match.group(3)}{match.group(4)}")


def _unsupported(reason: str) -> dict[str, Any]:
    return {
        "status": "unsupported", "answer": "", "evidence": [], "warning": reason,
        "failure_stage": "chart_structure_resolution", "operations_executed": ["chart_series_lookup"],
        "question_type": "chart_inspection", "verification": {},
    }


def execute_chart_series_lookup(question: str, files: list[FileRecord], project_root: Path) -> dict[str, Any] | None:
    """Return a chart source header only when every OOXML link is unique."""
    if not is_chart_series_question(question):
        return None
    candidates = [item for item in files if item.extension.lower() in {".xlsx", ".xlsm"}]
    graph_number = _requested_graph_number(question)
    if len(candidates) != 1 or graph_number is None:
        return _unsupported("chart_source_or_number_not_unique")
    file = candidates[0]
    path = project_root / file.raw_path
    if not path.exists():
        return _unsupported("chart_workbook_missing")
    try:
        with zipfile.ZipFile(path) as archive:
            sheets = _workbook_sheets(archive)
            named_sheets = _sheet_matches_question(question, list(sheets))
            if len(named_sheets) != 1:
                return _unsupported("chart_sheet_not_unique")
            sheet_name = named_sheets[0]
            chart_result = _chart_part_for_object(archive, sheets[sheet_name], graph_number)
            if chart_result is None:
                return _unsupported("chart_object_not_unique_or_not_native")
            chart_part, chart_location = chart_result
            chart_root = ET.fromstring(archive.read(chart_part))
            series = chart_root.findall(f".//{_CHART_EX_NS}series")
            if len(series) != 1:
                return _unsupported("chart_series_not_unique")
            series_name = series[0].findtext(f".//{_CHART_EX_NS}txData/{_CHART_EX_NS}v", "").strip()
            defined_name = series[0].findtext(f".//{_CHART_EX_NS}txData/{_CHART_EX_NS}f", "").strip()
            reference = _defined_name_reference(archive, defined_name)
            if not series_name or reference is None:
                return _unsupported("chart_series_reference_missing")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, ET.ParseError):
        return _unsupported("chart_package_read_failure")
    source_sheet, source_cell = reference
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True, data_only=False)
        source_value = workbook[source_sheet][source_cell].value
    except (OSError, ValueError, KeyError):
        return _unsupported("chart_source_header_read_failure")
    finally:
        if workbook is not None:
            workbook.close()
    if _normalize(source_value) != _normalize(series_name):
        return _unsupported("chart_series_header_mismatch")
    source_range = f"{source_sheet}!{source_cell}"
    evidence = {
        "file_id": file.file_id, "source_path": file.raw_path,
        "location": {"sheet": sheet_name, "chart": chart_location["object_name"], "chart_part": chart_part},
        "sheet_name": sheet_name, "chart_name": chart_location["object_name"], "chart_part": chart_part,
        "chart_anchor": chart_location["anchor_from"], "series_name": series_name, "defined_name": defined_name,
        "source_sheet": source_sheet, "source_cell": source_cell, "source_range": source_range,
        "source_header_value": source_value, "preview_only": False,
    }
    verification = {
        "presence": True, "condition_match": True, "source_location": True, "series_reference": True,
        "header_match": True, "uniqueness": True, "answer_format_valid": True, "verification_status": "passed",
    }
    return {
        "status": "success", "answer": str(source_value), "evidence": [evidence],
        "operations_executed": ["chart_series_lookup", "answer_formatting"],
        "question_type": "chart_inspection", "verification": verification,
    }
