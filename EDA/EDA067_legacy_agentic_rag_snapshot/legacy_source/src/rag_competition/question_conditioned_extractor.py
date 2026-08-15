from __future__ import annotations

import json
import csv
import re
import unicodedata
from pathlib import Path
from typing import Any

from .document_evidence_verifier import verify_document_extraction
from .document_reconstructor import reconstruct_items
from .extraction_spec import normalize_identifier


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).lower()


def _format_matches(item: dict[str, Any], conditions: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = item.get("actual_format_values", {})
    matched: dict[str, Any] = {}
    for key, expected in conditions.items():
        if expected is None:
            continue
        value = actual.get(key)
        if value is None:
            return False, matched
        if isinstance(expected, bool) and bool(value) != expected:
            return False, matched
        if isinstance(expected, str) and expected not in _normalize_color(value):
            return False, matched
        matched[key] = value
    return True, matched


def _normalize_color(value: Any) -> str:
    text = _norm(value)
    if not text:
        return ""
    aliases = {
        "ff0000": "red", "ffff0000": "red", "red": "red",
        "0000ff": "blue", "ff0000ff": "blue", "blue": "blue",
        "ffff00": "yellow", "ffffff00": "yellow", "yellow": "yellow",
        "00ff00": "green", "ff00ff00": "green", "green": "green",
        "000000": "black", "ff000000": "black", "black": "black",
    }
    for raw, name in aliases.items():
        if raw in text:
            return name
    return text


def _identifier_match(text: str, identifier: str) -> bool:
    compact = normalize_identifier(identifier)
    pattern = r"(?<![A-Z0-9])" + r"\s*[-_：:]?\s*".join(re.escape(char) for char in compact) + r"(?![A-Z0-9])"
    return bool(re.search(pattern, unicodedata.normalize("NFKC", text or "").upper()))


def _make_item(file: Any, text: str, location: dict[str, Any], fmt: dict[str, Any], source_order: int, matched_terms: list[str], identifiers: list[str]) -> dict[str, Any]:
    return {"item_id": f"{file.file_id}_{source_order}", "text": text, "normalized_text": unicodedata.normalize("NFKC", text), "file_id": file.file_id, "source_path": file.raw_path, "file_type": file.extension.lstrip("."), "location": location, "page_number": location.get("page_number"), "slide_number": location.get("slide_number"), "paragraph_index": location.get("paragraph_index"), "table_index": location.get("table_index"), "row_index": location.get("row_index"), "column_index": location.get("column_index"), "cell_reference": location.get("cell_reference"), "shape_index": location.get("shape_index"), "run_indexes": [location["run_index"]] if "run_index" in location else [], "comment_id": location.get("comment_id"), "matched_search_terms": matched_terms, "matched_identifier_terms": identifiers, "matched_format_conditions": {}, "actual_format_values": fmt, "source_order": source_order}


def _iter_structure(file: Any, structure: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    order = 0
    if file.extension == ".docx":
        for block in structure.get("blocks", []):
            for run in block.get("runs", []) or [{"text": block.get("text", "")}]:
                text = str(run.get("text", ""))
                if not text: continue
                location = {"paragraph_index": block.get("index"), "run_index": run.get("run_index", 0), "style_name": block.get("style", "")}
                fmt = {"bold": run.get("bold"), "italic": run.get("italic"), "underline": run.get("underline"), "font_color": run.get("font_color", ""), "highlight_color": run.get("highlight_color", ""), "comment_present": bool(run.get("comment_id")), "bold_source": run.get("bold_source", "unknown"), "italic_source": run.get("italic_source", "unknown"), "underline_source": run.get("underline_source", "unknown")}
                output.append(_make_item(file, text, location, fmt, order, [], [])); order += 1
        for table in structure.get("tables", []):
            for row_index, row in enumerate(table.get("rows", [])):
                for column_index, value in enumerate(row):
                    text = str(value or "")
                    if text: output.append(_make_item(file, text, {"table_index": table.get("table_index"), "row_index": row_index, "column_index": column_index}, {}, order, [], [])); order += 1
    elif file.extension == ".pptx":
        for slide in structure.get("slides", []):
            for shape in slide.get("shapes", []) or []:
                for run in shape.get("runs", []) or [{"text": shape.get("text", "")}]:
                    text = str(run.get("text", ""))
                    if not text: continue
                    location = {"slide_number": slide.get("slide_number"), "shape_index": shape.get("shape_index"), "run_index": run.get("run_index", 0)}
                    fmt = {key: (run.get(key) if run.get(key) is not None else False if key in {"bold", "italic", "underline"} else "") for key in ("bold", "italic", "underline", "font_color", "highlight_color", "fill_color", "font_color_normalized_name", "font_color_resolved_rgb", "font_color_resolved_argb", "shape_fill_normalized_name", "shape_fill_rgb")}
                    fmt.update({"bold_source": "explicit" if run.get("bold") is not None else "default", "italic_source": "explicit" if run.get("italic") is not None else "default", "underline_source": "explicit" if run.get("underline") is not None else "default"})
                    output.append(_make_item(file, text, location, fmt, order, [], [])); order += 1
    elif file.extension == ".pdf":
        for page in structure.get("pages", []):
            for block_index, block in enumerate(page.get("blocks", [])):
                for line in block.get("lines", []) or []:
                    for span in line.get("spans", []) or []:
                        text = str(span.get("text", ""))
                        if not text: continue
                        location = {"page_number": page.get("page_number"), "block_index": block_index, "bounding_box": span.get("bbox")}
                        fmt = {"font": span.get("font", ""), "font_size": span.get("size"), "color": span.get("color"), "bold": bool(span.get("flags", 0) & 16), "italic": bool(span.get("flags", 0) & 2)}
                        output.append(_make_item(file, text, location, fmt, order, [], [])); order += 1
    elif file.extension == ".xlsx":
        for sheet in structure.get("sheets", []):
            values: dict[str, str] = {}
            csv_path = Path(str(sheet.get("csv_path", "")))
            if csv_path.is_file():
                with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row_index, row in enumerate(csv.reader(handle), start=1):
                        for column_index, value in enumerate(row, start=1):
                            values[f"{column_index}:{row_index}"] = value
            for style in sheet.get("styled_cells", []):
                coordinate = str(style.get("coordinate", ""))
                match = re.match(r"([A-Z]+)(\d+)", coordinate)
                if not match: continue
                letters, row_number = match.groups(); column_number = 0
                for char in letters: column_number = column_number * 26 + ord(char) - 64
                text = values.get(f"{column_number}:{row_number}", style.get("value", ""))
                if not text and not any(style.get(key) for key in ("bold", "italic", "underline", "fill_color", "font_color", "comment")): continue
                location = {"sheet_name": sheet.get("sheet_name"), "cell_reference": coordinate, "row_index": int(row_number), "column_index": column_number}
                fmt = {"bold": style.get("bold", False), "italic": style.get("italic", False), "underline": style.get("underline", False), "font_color": style.get("font_color", ""), "fill_color": style.get("fill_color", ""), "comment_present": bool(style.get("comment"))}
                output.append(_make_item(file, text, location, fmt, order, [], [])); order += 1
    return output


def extract_conditioned(question: str, spec: Any, files: list[Any], structures: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    scanned = 0
    total = 0
    terms = [_norm(term) for term in spec.search_terms]
    identifiers = [normalize_identifier(term) for term in spec.identifier_terms]
    for file in files:
        source_items = _iter_structure(file, structures.get(file.file_id, {}))
        total += len(source_items); scanned += len(source_items)
        for item in source_items:
            if getattr(spec, "location_hints", None) and item.get("location", {}).get("slide_number") not in spec.location_hints:
                continue
            text = _norm(item["text"])
            term_hits = [term for term in terms if term and term in text]
            id_hits = [term for term in identifiers if term and _identifier_match(item["text"], term)]
            has_text_condition = bool(terms or identifiers)
            text_match = (not has_text_condition) or (all(term in term_hits for term in terms) and all(term in id_hits for term in identifiers)) if spec.match_mode == "all" else (not has_text_condition) or bool(term_hits or id_hits)
            format_ok, matched_format = _format_matches(item, spec.format_conditions)
            if not text_match or not format_ok: continue
            if any(condition.get("type") == "empty" for condition in spec.exclude_conditions) and not text.strip(): continue
            if any(condition.get("type") == "date" for condition in spec.exclude_conditions) and re.fullmatch(r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{8}|\d{1,2}月\d{1,2}日)", item["text"].strip()): continue
            item["matched_search_terms"] = term_hits; item["matched_identifier_terms"] = id_hits; item["matched_format_conditions"] = matched_format
            candidates.append(item)
        if terms and spec.format_conditions and not any(item["file_id"] == file.file_id for item in candidates):
            groups: dict[str, list[dict[str, Any]]] = {}
            for item in source_items:
                loc = item.get("location", {})
                key = "|".join(f"{name}={loc.get(name)}" for name in ("paragraph_index", "slide_number", "shape_index", "table_index", "row_index", "sheet_name") if name in loc)
                groups.setdefault(key, []).append(item)
            for group in groups.values():
                group_text = _norm("".join(str(item.get("text", "")) for item in group))
                if all(term in group_text for term in terms):
                    for item in group:
                        format_ok, matched_format = _format_matches(item, spec.format_conditions)
                        if format_ok:
                            item["matched_search_terms"] = terms; item["matched_format_conditions"] = matched_format; candidates.append(item)
    if spec.target_type == "identifier_record" and (identifiers or terms):
        source_by_file: dict[str, list[dict[str, Any]]] = {}
        for file in files:
            source_by_file[file.file_id] = _iter_structure(file, structures.get(file.file_id, {}))
        expanded: list[dict[str, Any]] = []
        for item in candidates:
            if not item.get("matched_identifier_terms") and not item.get("matched_search_terms"):
                continue
            loc = item.get("location", {})
            siblings = source_by_file.get(item["file_id"], [])
            for sibling in siblings:
                sloc = sibling.get("location", {})
                same_row = loc.get("table_index") is not None and loc.get("table_index") == sloc.get("table_index") and loc.get("row_index") == sloc.get("row_index")
                same_row = same_row or (loc.get("sheet_name") is not None and loc.get("sheet_name") == sloc.get("sheet_name") and loc.get("row_index") == sloc.get("row_index"))
                same_paragraph = loc.get("paragraph_index") is not None and loc.get("paragraph_index") == sloc.get("paragraph_index")
                same_shape = loc.get("shape_index") is not None and loc.get("shape_index") == sloc.get("shape_index") and loc.get("slide_number") == sloc.get("slide_number")
                if same_row or same_paragraph or same_shape:
                    sibling["matched_identifier_terms"] = item.get("matched_identifier_terms", [])
                    sibling["matched_search_terms"] = item.get("matched_search_terms", [])
                    expanded.append(sibling)
        if expanded:
            candidates = expanded
            if any(item.get("location", {}).get("table_index") is not None for item in expanded):
                spec.output_scope = "table_row"
    if getattr(spec, "identifier_output_only", False):
        candidates = [item for item in candidates if re.fullmatch(r"[A-Za-zＡ-Ｚａ-ｚ]{1,8}[\s\-_–—]*\d{1,4}", str(item.get("text", "")).strip())]
        grouped_ids: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
        for item in candidates:
            location = item.get("location", {})
            key = (location.get("file_id", item.get("file_id")), location.get("sheet_name"), location.get("row_index"))
            grouped_ids.setdefault(key, []).append(item)
        candidates = [item for group in grouped_ids.values() for item in group if item.get("location", {}).get("column_index") == min(int(candidate.get("location", {}).get("column_index", 10**6)) for candidate in group)]
    if spec.target_type == "heading":
        candidates = [item for item in candidates if "heading" in str(item.get("location", {}).get("style_name", "")).lower() or str(item.get("text", "")).strip()[:1].isdigit()]
    reconstructed = reconstruct_items(candidates, spec)
    if spec.deduplicate:
        seen: set[str] = set()
        unique_items: list[dict[str, Any]] = []
        for item in reconstructed:
            key = item["normalized_text"]
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)
        reconstructed = unique_items
    if spec.selection_mode == "first": reconstructed = reconstructed[:1]
    question_type = "identifier_verbatim" if spec.target_type == "identifier_record" else "location" if spec.target_type == "location" else "format_only" if any(value is not None for value in spec.format_conditions.values()) else "semantic_document_lookup"
    result = {"schema_version": "1.0", "items": reconstructed, "candidate_count": len(candidates), "matched_count": len(reconstructed), "coverage_status": "complete" if scanned == total else "incomplete", "uniqueness_status": "unique" if len(reconstructed) == 1 else "ambiguous" if len(reconstructed) > 1 else "not_found", "warnings": [], "scanned_count": scanned, "total_count": total, "question_type": question_type}
    if getattr(spec, "identifier_output_only", False) and spec.selection_mode == "all":
        # 識別子一覧は、原文を保持したまま日本語の列挙区切りで整形する。
        answer = "、".join(item["text"] for item in reconstructed)
    else:
        answer = "\n".join(item["text"] for item in reconstructed)
    result["verification"] = verify_document_extraction(answer, reconstructed, spec, scanned, total, question_type)
    result["answer"] = answer if result["verification"]["verification_status"] == "passed" else ""
    return result
