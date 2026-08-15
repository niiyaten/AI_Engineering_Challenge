from __future__ import annotations

from rag_competition.format_executor import merge_logical_format_spans


def item(file_id, paragraph, run, text, order):
    return {"file_id": file_id, "text": text, "source_order": order, "location": {"paragraph_index": paragraph, "run_index": run}}


def main():
    bold_a = item("f", 1, 0, "30", 0)
    bold_b = item("f", 1, 1, "分単位", 1)
    normal = item("f", 1, 1, "分", 1)
    bold_c = item("f", 1, 2, "単位", 2)
    paragraph_two = item("f", 2, 0, "次段落", 3)
    combined = merge_logical_format_spans([bold_a, bold_b], [bold_a, bold_b])
    assert [row["text"] for row in combined] == ["30分単位"]
    separated = merge_logical_format_spans([bold_a, bold_c], [bold_a, normal, bold_c])
    assert [row["text"] for row in separated] == ["30", "単位"]
    cross_paragraph = merge_logical_format_spans([bold_a, paragraph_two], [bold_a, paragraph_two])
    assert [row["text"] for row in cross_paragraph] == ["30", "次段落"]
    empty = item("f", 1, 1, "", 1)
    empty_merge = merge_logical_format_spans([bold_a, empty, bold_c], [bold_a, empty, bold_c])
    assert [row["text"] for row in empty_merge] == ["30単位"]
    combo_a = item("f", 1, 0, "25,000", 0)
    combo_b = item("f", 1, 1, "円／時間", 1)
    assert merge_logical_format_spans([combo_a, combo_b], [combo_a, combo_b])[0]["text"] == "25,000円／時間"
    print("logical_span_unit_tests=5 passed")


if __name__ == "__main__":
    main()
