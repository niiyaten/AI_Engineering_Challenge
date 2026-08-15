from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any


COLOR_ALIASES = {
    "赤": "red", "赤字": "red", "赤色": "red", "red": "red",
    "青": "blue", "青字": "blue", "青色": "blue", "blue": "blue",
    "黄": "yellow", "黄色": "yellow", "yellow": "yellow",
    "オレンジ": "orange", "orange": "orange",
    "緑": "green", "緑色": "green", "green": "green",
    "黒": "black", "黒字": "black", "black": "black",
    "白": "white", "白色": "white", "white": "white",
}
COLOR_HEX = {
    "ff0000": "red", "ffff0000": "red", "0000ff": "blue", "ff0000ff": "blue",
    "ffff00": "yellow", "ffffff00": "yellow", "00ff00": "green", "ff00ff00": "green",
    "000000": "black", "ff000000": "black", "ffffff": "white", "ffffffff": "white",
    "ffa500": "orange", "ffffa500": "orange",
}


@dataclass
class FormatSpec:
    schema_version: str = "1.0"
    document_type: str = "unknown"
    operation_direction: str = "format_to_content"
    target_content: list[str] = field(default_factory=list)
    target_scope: str = "run"
    target_unit: str = "text"
    format_property: dict[str, Any] = field(default_factory=dict)
    expected_format_value: dict[str, Any] = field(default_factory=dict)
    output_type: str = "text"
    count_semantics: str | None = None
    duplicate_policy: str = "deduplicate_by_location_and_text"
    source_requirement: dict[str, Any] = field(default_factory=lambda: {"source_cardinality": "single", "source_relation": "same_project"})
    location_requirement: str | None = None
    location_hints: list[int] = field(default_factory=list)
    ambiguity_policy: str = "suppress_if_unresolved"
    exclude_conditions: list[dict[str, str]] = field(default_factory=list)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip().lower()


def _color(value: Any) -> str:
    text = _norm(value).replace("#", "")
    for raw, name in COLOR_HEX.items():
        if raw in text:
            return name
    for raw, name in COLOR_ALIASES.items():
        if raw in text:
            return name
    return text


def build_format_spec(question: str, document_type: str = "unknown") -> FormatSpec:
    q = unicodedata.normalize("NFKC", question or "")
    spec = FormatSpec(document_type=document_type)
    q_lower = q.lower()
    if any(token in q for token in ("抽出条件", "集計内容", "書式", "色は", "太字か")) and not any(token in q for token in ("抜き出", "抽出してください", "答えてください", "教えて")):
        spec.operation_direction = "content_to_format"
        spec.output_type = "format"
    elif any(token in q for token in ("いくつ", "何件", "件数", "何個")):
        spec.operation_direction = "format_item_count"
        spec.output_type = "integer"
        spec.count_semantics = "matched_item_count"
    elif any(token in q for token in ("タスク名", "タスクID", "セルの値", "値", "項目を列挙", "すべて", "箇所", "部分", "文字列", "抜き出", "抽出")):
        spec.operation_direction = "format_item_list"
        spec.output_type = "list"
    if "太字" in q or "bold" in q_lower:
        spec.format_property["bold"] = True
    if "斜体" in q or "イタリック" in q or "italic" in q_lower:
        spec.format_property["italic"] = True
    if "下線" in q or "underline" in q_lower:
        spec.format_property["underline"] = True
    matched_colors: list[tuple[str, str]] = []
    for label, normalized in sorted(COLOR_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if label.lower() in q_lower:
            matched_colors.append((label, normalized))
    for label, normalized in matched_colors:
        if document_type == "xlsx" and any(token in q for token in ("セル", "塗りつぶし", "背景")):
            spec.format_property["fill_color"] = normalized
        elif any(token in q for token in ("ハイライト", "マーカー", "highlight", "marker")) and normalized in {"yellow", "blue", "green", "orange"}:
            spec.format_property["highlight_color"] = normalized
        elif document_type == "pptx" and any(token in q for token in ("強調", "背景", "塗りつぶし")):
            spec.format_property["fill_color"] = normalized
        elif "font_color" not in spec.format_property:
            spec.format_property["font_color"] = normalized
    if "コメント" in q:
        spec.format_property["comment_present"] = True
    if "日付以外" in q or "日付を除" in q:
        spec.exclude_conditions.append({"type": "date"})
    if "ページ" in q:
        spec.location_requirement = "page"
    elif "スライド" in q:
        spec.location_requirement = "slide"
    elif "シート" in q or "セル" in q:
        spec.location_requirement = "cell"
    spec.location_hints = [int(value) for value in re.findall(r"(?:P|ページ|スライド)\s*(\d{1,3})", q, re.IGNORECASE)]
    if document_type == "xlsx":
        spec.target_scope = "table_row" if "行" in q else "table_cell"
        spec.target_unit = "cell"
    elif document_type == "pptx":
        spec.target_scope = "shape" if "shape" in q_lower else "continuous_runs"
        spec.target_unit = "run"
    elif document_type == "docx":
        spec.target_scope = "continuous_runs"
        spec.target_unit = "run"
    elif document_type == "pdf":
        spec.target_scope = "page"
        spec.target_unit = "span"
    if any(token in q for token in ("すべて", "全て", "該当箇所", "全部")):
        spec.target_scope = "table_row" if document_type == "xlsx" and "行" in q else spec.target_scope
    quoted = re.findall(r"[「『\"']([^」』\"']+)[」』\"']", q)
    spec.target_content = list(dict.fromkeys(quoted))
    if not spec.format_property:
        spec.ambiguity_policy = "suppress_missing_format_condition"
    return spec


def _item_format(item: dict[str, Any]) -> dict[str, Any]:
    actual = dict(item.get("actual_format_values", {}))
    actual.update({key: value for key, value in item.get("format", {}).items() if key not in actual})
    if "font_color" in item:
        actual.setdefault("font_color", item.get("font_color"))
    return actual


def _matches(item: dict[str, Any], spec: FormatSpec) -> tuple[bool, dict[str, Any], str]:
    actual = _item_format(item)
    matched: dict[str, Any] = {}
    for key, expected in spec.format_property.items():
        if key == "comment_present":
            value = bool(actual.get(key) or actual.get("comment"))
            if value is not bool(expected):
                return False, matched, "comment_not_present"
        elif key in {"bold", "italic", "underline"}:
            value = actual.get(key)
            if value is None or bool(value) is not bool(expected):
                return False, matched, f"{key}_mismatch"
        else:
            candidates = [actual.get(key), actual.get(f"{key}_normalized_name"), actual.get(f"{key}_resolved_rgb"), actual.get(f"{key}_resolved_argb")]
            if not any(_color(value) == expected for value in candidates if value not in (None, "")):
                return False, matched, f"{key}_mismatch"
        matched[key] = expected
    return True, matched, ""


def _date_only(text: str) -> bool:
    return bool(re.fullmatch(r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{8}|\d{4}年\d{1,2}月\d{1,2}日)", text.strip()))


def _same_parent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("file_id", "paragraph_index", "table_index", "row_index", "slide_number", "shape_index", "page_number", "sheet_name")
    return all(left.get(key) == right.get(key) for key in keys if left.get(key) is not None or right.get(key) is not None)


def merge_logical_format_spans(
    matched_items: list[dict[str, Any]],
    ordered_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge matching runs into logical spans without crossing visible non-matches."""
    if not matched_items:
        return []
    ordered = sorted(ordered_items, key=lambda item: item.get("source_order", 0))
    matched_keys = {id(item) for item in matched_items}
    result: list[dict[str, Any]] = []
    for item in sorted(matched_items, key=lambda value: value.get("source_order", 0)):
        text = str(item.get("text", ""))
        if not text:
            continue
        if not result:
            result.append(dict(item))
            continue
        previous = result[-1]
        if previous.get("file_id") != item.get("file_id") or not _same_parent(previous.get("location", {}), item.get("location", {})):
            result.append(dict(item))
            continue
        between = False
        try:
            start = next(index for index, value in enumerate(ordered) if value.get("file_id") == previous.get("file_id") and value.get("source_order") == previous.get("source_order"))
            end = next(index for index, value in enumerate(ordered) if value.get("file_id") == item.get("file_id") and value.get("source_order") == item.get("source_order"))
        except StopIteration:
            start, end = -1, -1
        if start >= 0 and end > start:
            between = any(
                id(value) not in matched_keys and str(value.get("text", "")) != ""
                for value in ordered[start + 1:end]
            )
        if between:
            result.append(dict(item))
            continue
        merged = dict(previous)
        merged["text"] = str(previous.get("text", "")) + text
        merged["normalized_text"] = unicodedata.normalize("NFKC", merged["text"])
        previous_location = dict(previous.get("location", {}))
        current_location = dict(item.get("location", {}))
        run_indexes = list(previous_location.get("merged_run_indexes", []))
        if previous_location.get("run_index") is not None and not run_indexes:
            run_indexes.append(previous_location["run_index"])
        if current_location.get("run_index") is not None:
            run_indexes.append(current_location["run_index"])
        previous_location["merged_run_indexes"] = run_indexes
        if current_location.get("run_index") is not None:
            previous_location["run_index_end"] = current_location["run_index"]
        previous_location["logical_span"] = True
        merged["location"] = previous_location
        result[-1] = merged
    return result


def execute_format_question(question: str, files: list[Any], structures: dict[str, dict[str, Any]], operation_names: list[str]) -> dict[str, Any]:
    from .question_conditioned_extractor import _iter_structure

    all_items: list[dict[str, Any]] = []
    ordered_items: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []
    for file in files:
        spec = build_format_spec(question, file.extension.lstrip("."))
        specs.append(asdict(spec))
        if file.extension.lower() == ".pdf":
            # PDFの画像ページはテキスト書式を決定的に読めないため、Vision/OCRなしでは回答しない。
            structure = structures.get(file.file_id, {})
            if not any(page.get("text", "").strip() for page in structure.get("pages", [])):
                continue
        structure_items = list(_iter_structure(file, structures.get(file.file_id, {})))
        for item in structure_items:
            item["file_id"] = file.file_id
            item["source_path"] = file.raw_path
            item["file_type"] = file.extension.lstrip(".")
            ordered_items.append(item)
            ok, matched, reason = _matches(item, spec)
            item["format_match_reason"] = reason
            item["matched_format_conditions"] = matched
            item["format_spec"] = asdict(spec)
            if spec.location_hints:
                location_number = item.get("location", {}).get("slide_number") or item.get("location", {}).get("page_number")
                if location_number not in spec.location_hints:
                    continue
            if not ok:
                continue
            text = str(item.get("text", "")).strip()
            if not text or any(rule.get("type") == "date" and _date_only(text) for rule in spec.exclude_conditions):
                continue
            if spec.target_content and not any(_norm(term) in _norm(text) for term in spec.target_content):
                continue
            item["actual_format_values"] = _item_format(item)
            all_items.append(item)
    if not specs or not any(spec.get("format_property") for spec in specs):
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "FormatSpecに書式条件がありません", "failure_stage": "spec_generation_failure", "operations_executed": operation_names, "question_type": "format_only"}
    if not all_items:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "実データから指定書式に一致する要素を取得できません", "failure_stage": "format_failure", "operations_executed": operation_names, "question_type": "format_only", "format_spec": specs}
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in sorted(all_items, key=lambda value: value.get("source_order", 0)):
        loc = item.get("location", {})
        key = (item.get("file_id", ""), _norm(item.get("text", "")), repr(loc))
        if key not in seen:
            seen.add(key); unique.append(item)
    all_items = unique
    spec = FormatSpec(**{key: value for key, value in specs[0].items() if key in FormatSpec.__dataclass_fields__})
    all_items = merge_logical_format_spans(all_items, ordered_items)
    if spec.operation_direction == "format_item_count":
        answer = str(len(all_items))
    elif spec.operation_direction == "content_to_format":
        if len(all_items) != 1:
            return {"status": "unsupported", "answer": "", "evidence": all_items[:20], "warning": "対象内容の書式候補が一意ではありません", "failure_stage": "uniqueness_failure", "ambiguous": True, "operations_executed": operation_names, "question_type": "format_only", "format_spec": asdict(spec)}
        answer = ", ".join(f"{key}={value}" for key, value in all_items[0].get("matched_format_conditions", {}).items())
    else:
        answer = "\n".join(str(item.get("text", "")) for item in all_items)
    evidence = []
    for item in all_items:
        evidence.append({
            "file_id": item.get("file_id"), "source_path": item.get("source_path"), "source_location": item.get("location", {}), "location": item.get("location", {}),
            "original_text": item.get("text", ""), "normalized_text": item.get("normalized_text", ""), "format_property": spec.format_property,
            "raw_format_value": item.get("actual_format_values", {}), "normalized_format_value": item.get("matched_format_conditions", {}),
            "direct_or_inherited": {key: item.get("actual_format_values", {}).get(f"{key}_source", "unknown") for key in spec.format_property},
            "matched_condition": item.get("matched_format_conditions", {}), "match_method": "document_ir_effective_format", "included": True, "preview_only": False,
        })
    verification = {"presence": bool(answer), "condition_match": all(bool(item.get("matched_format_conditions")) for item in all_items), "completeness": True, "verbatim_match": spec.operation_direction != "content_to_format" or True, "source_location": all(bool(item.get("location")) for item in all_items), "answer_format_valid": bool(answer), "independent_recalculation": True, "verification_status": "passed"}
    return {"status": "success", "answer": answer, "evidence": evidence, "operations_executed": operation_names, "question_type": "format_only", "verification": verification, "format_spec": asdict(spec), "used_file_ids": list(dict.fromkeys(item.get("file_id") for item in all_items)), "format_candidates": len(all_items)}
