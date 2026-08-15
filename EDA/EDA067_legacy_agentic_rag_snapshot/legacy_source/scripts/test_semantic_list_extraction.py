from __future__ import annotations

from pathlib import Path
import json
import tempfile

from rag_competition.semantic_executor import _derive_list_items, _list_image_relevance, build_list_spec


def table_candidates(headers: list[str], rows: list[list[str]]) -> list[dict]:
    return [
        {
            "candidate_id": f"row_{index}",
            "element_type": "table_row",
            "row_index": index,
            "text": " | ".join(row),
            "metadata": {"headers": headers, "cells": row},
            "file_id": "synthetic",
            "source_path": "synthetic.xlsx",
            "source_order": index,
        }
        for index, row in enumerate(rows)
    ]


def run() -> None:
    checks: list[tuple[str, bool]] = []
    q = "未完了のタスクIDをすべて挙げてください"
    spec = build_list_spec(q)
    included, excluded, error = _derive_list_items(q, spec, table_candidates(["ID", "状態"], [["ID", "状態"], ["T1", "未完了"], ["T2", "完了"]]))
    checks.append(("status_filter", [item["item_value"] for item in included] == ["T1"] and not error))

    bullet = [
        {"candidate_id": "b1", "element_type": "paragraph", "text": "- Alpha", "source_order": 1},
        {"candidate_id": "b2", "element_type": "paragraph", "text": "- Beta", "source_order": 2},
        {"candidate_id": "b3", "element_type": "paragraph", "text": "注記", "source_order": 3},
    ]
    included, _, error = _derive_list_items("項目をすべて抽出してください", build_list_spec("項目をすべて抽出してください"), bullet)
    checks.append(("bullet_order", [item["item_value"] for item in included] == ["Alpha", "Beta"] and not error))

    duplicate = table_candidates(["ID"], [["ID"], ["Alpha"], ["Alpha"]])
    included, excluded, error = _derive_list_items("項目をすべて一覧にしてください", build_list_spec("項目をすべて一覧にしてください"), duplicate)
    checks.append(("deduplicate", len(included) == 1 and any(item.get("exclusion_reason") == "duplicate_item" for item in excluded)))

    fake_file = type("File", (), {"file_id": "synthetic", "raw_path": "synthetic.docx"})()
    with tempfile.TemporaryDirectory() as temp_dir:
        structure_path = Path(temp_dir) / "structure.json"
        structure_path.write_text(json.dumps({"images": [{"id": "logo", "type": "logo", "alt_text": "company logo", "repeated": True}]}), encoding="utf-8")
        extraction = type("E", (), {"extracted_path": str(structure_path), "status": "success"})()
        audit = _list_image_relevance("項目を一覧にしてください", [fake_file], {"synthetic": extraction}, Path("."))
        checks.append(("irrelevant_image_does_not_block", audit[0]["relevance_class"] == "decorative_or_irrelevant" and not audit[0]["blocks_completeness"]))
        structure_path.write_text(json.dumps({"images": [{"id": "table", "type": "image", "nearby_text": "課題一覧"}]}), encoding="utf-8")
        audit = _list_image_relevance("課題一覧を抽出してください", [fake_file], {"synthetic": extraction}, Path("."))
        checks.append(("relevant_image_is_recorded", audit[0]["relevance_class"] == "possibly_relevant"))

    print("semantic_list_unit_tests=%d passed=%d failed=%d" % (len(checks), sum(ok for _, ok in checks), sum(not ok for _, ok in checks)))
    for name, ok in checks:
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
    if not all(ok for _, ok in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
