from __future__ import annotations

from collections import defaultdict
from typing import Any


def reconstruct_items(items: list[dict[str, Any]], spec: Any) -> list[dict[str, Any]]:
    if not items:
        return []
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in sorted(items, key=lambda row: (row.get("source_order", 0), row.get("item_id", ""))):
        location = item.get("location", {})
        location_keys = ("paragraph_index", "table_index", "row_index", "column_index", "slide_number", "shape_index", "page_number", "block_index")
        if getattr(spec, "output_scope", "") == "table_row":
            location_keys = tuple(key for key in location_keys if key != "column_index")
        parent = tuple((key, location.get(key)) for key in location_keys if key in location)
        grouped[(item.get("file_id"), parent)].append(item)
    result: list[dict[str, Any]] = []
    for group in grouped.values():
        group.sort(key=lambda row: row.get("source_order", 0))
        if spec.output_scope in {"run", "table_cell"}:
            result.extend(group)
            continue
        current: list[dict[str, Any]] = []
        for item in group:
            if current and item.get("source_order", 0) != current[-1].get("source_order", 0) + 1:
                result.append(_combine(current)); current = []
            current.append(item)
        if current:
            result.append(_combine(current))
    return sorted(result, key=lambda row: row.get("source_order", 0))


def _combine(items: list[dict[str, Any]]) -> dict[str, Any]:
    first = dict(items[0])
    first["item_id"] = "reconstructed_" + "_".join(str(item.get("item_id", "")) for item in items)
    first["text"] = "".join(str(item.get("text", "")) for item in items)
    first["normalized_text"] = "".join(str(item.get("normalized_text", item.get("text", ""))) for item in items)
    first["run_indexes"] = [index for item in items for index in item.get("run_indexes", [])]
    first["matched_format_conditions"] = {key: all(item.get("matched_format_conditions", {}).get(key, False) for item in items) for key in ("bold", "italic", "underline")}
    first["reconstructed_from"] = [item.get("item_id") for item in items]
    return first
