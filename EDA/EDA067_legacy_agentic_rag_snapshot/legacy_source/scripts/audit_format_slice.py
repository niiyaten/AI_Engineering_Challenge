from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text or "")).strip()


def classify(question: str) -> str:
    q = norm(question).lower()
    has_format = any(token in q for token in ("太字", "斜体", "イタリック", "下線", "ハイライト", "黄色", "赤で強調", "赤字", "文字色", "コメント", "マーカー"))
    has_document = any(token in q for token in ("docx", "pptx", "pdf", "提案書", "報告書", "報告資料", "契約書", "会議録", "ページ", "スライド"))
    if has_format and has_document:
        return "format_only"
    if any(token in q for token in ("タスクid", "アクションid", "マイルストーン", "そのまま抜き出", "すべて挙げ")):
        return "identifier_verbatim"
    if any(token in q for token in ("何ページ", "どのページ", "何枚", "どのスライド")):
        return "location_lookup"
    if has_document:
        return "semantic_document_lookup"
    return "unsupported_document"


def is_document_question(question: str) -> bool:
    """文書12問を、質問文の資料・位置・文書構造語から機械的に拾う。"""
    q = norm(question)
    return any(token in q for token in ("最終報告", "提案書", "契約書", "中間報告", "会議録", "PL", "P7", "ipynb", "metrics.json", "タスクID", "残余リスク", "API化"))


def raw_format_counts(path: Path, condition: dict[str, object]) -> dict[str, int]:
    counts = Counter(total_raw_text_elements=0, raw_bold_count=0, raw_italic_count=0, raw_underline_count=0, raw_red_font_count=0, raw_yellow_highlight_count=0, raw_combined_condition_count=0)
    if not path.exists() or path.suffix.lower() not in {".docx", ".pptx"}:
        return dict(counts)
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        return dict(counts)
    with archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            try:
                root = ElementTree.fromstring(archive.read(name))
            except ElementTree.ParseError:
                continue
            if path.suffix.lower() == ".docx":
                counts["total_raw_text_elements"] += sum(bool(node.text and node.text.strip()) for node in root.findall(".//w:t", NS))
                counts["raw_yellow_highlight_count"] += sum(
                    str(node.attrib.get(f"{{{NS['w']}}}val", node.attrib.get("val", ""))).lower() in {"yellow", "ffff00"}
                    for node in root.findall(".//w:highlight", NS)
                )
                for run in root.findall(".//w:r", NS):
                    if not run.findall(".//w:t", NS):
                        continue
                    props = run.find("w:rPr", NS)
                    bold = props is not None and props.find("w:b", NS) is not None
                    italic = props is not None and props.find("w:i", NS) is not None
                    underline = props is not None and props.find("w:u", NS) is not None
                    color = props.find("w:color", NS) if props is not None else None
                    highlight = props.find("w:highlight", NS) if props is not None else None
                    red = color is not None and str(color.attrib.get("val", "")).lower() in {"ff0000", "red"}
                    yellow = highlight is not None and str(highlight.attrib.get("val", "")).lower() in {"yellow", "ffff00"}
                    counts["raw_bold_count"] += int(bold); counts["raw_italic_count"] += int(italic); counts["raw_underline_count"] += int(underline)
                    counts["raw_red_font_count"] += int(red); counts["raw_yellow_highlight_count"] += int(yellow)
                    if any(value is not None for value in condition.values()) and all(condition.get(key) is None or value for key, value in (("bold", bold), ("italic", italic), ("underline", underline))):
                        if (not condition.get("font_color") or red) and (not condition.get("highlight_color") or yellow): counts["raw_combined_condition_count"] += 1
            else:
                counts["total_raw_text_elements"] += sum(bool(node.text and node.text.strip()) for node in root.findall(".//a:t", NS))
                for run in root.findall(".//a:r", NS):
                    props = run.find("a:rPr", NS)
                    bold = props is not None and props.attrib.get("b", "").lower() == "1"
                    italic = props is not None and props.attrib.get("i", "").lower() == "1"
                    underline = props is not None and props.attrib.get("u", "").lower() not in {"", "none"}
                    counts["raw_bold_count"] += int(bold); counts["raw_italic_count"] += int(italic); counts["raw_underline_count"] += int(underline)
    return dict(counts)


def ir_format_counts(structure: dict, condition: dict[str, object]) -> dict[str, int]:
    counts = Counter(total_ir_text_elements=0, ir_bold_count=0, ir_italic_count=0, ir_underline_count=0, ir_red_font_count=0, ir_yellow_highlight_count=0, ir_combined_condition_count=0)
    runs = []
    for block in structure.get("blocks", []): runs.extend(block.get("runs", []))
    for slide in structure.get("slides", []):
        for shape in slide.get("shapes", []): runs.extend(shape.get("runs", []))
    counts["total_ir_text_elements"] = sum(bool(item.get("text", "").strip()) for item in runs)
    for item in runs:
        bold = item.get("bold") is True; italic = item.get("italic") is True; underline = item.get("underline") is True
        color = str(item.get("font_color", "")).lower(); highlight = str(item.get("highlight_color", "")).lower()
        red = color in {"red", "ff0000", "#ff0000"}; yellow = "yellow" in highlight or highlight in {"ffff00", "#ffff00"}
        counts["ir_bold_count"] += int(bold); counts["ir_italic_count"] += int(italic); counts["ir_underline_count"] += int(underline)
        counts["ir_red_font_count"] += int(red); counts["ir_yellow_highlight_count"] += int(yellow)
        if any(value is not None for value in condition.values()) and all(condition.get(key) is None or value for key, value in (("bold", bold), ("italic", italic), ("underline", underline))):
            if (not condition.get("font_color") or red) and (not condition.get("highlight_color") or yellow): counts["ir_combined_condition_count"] += 1
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--run-id", required=True); parser.add_argument("--project-root", type=Path, default=Path(".")); args = parser.parse_args()
    root = args.project_root.resolve(); run_dir = root / "data" / "work" / args.run_id; output_dir = root / "data" / "output" / args.run_id / "analysis"; output_dir.mkdir(parents=True, exist_ok=True)
    analysis_rows = jsonl(run_dir / "planning" / "question_analysis.jsonl")
    question_path = next((path for path in (root / "data" / "raw").rglob("questions_valid.csv") if "output" not in path.parts), None)
    raw_questions = {int(row["index"]): row["question"] for row in rows(question_path)} if question_path else {}
    analyses = []
    for item in analysis_rows:
        question_id = int(item["index"])
        original = raw_questions.get(question_id, item.get("question_original", ""))
        normalized = norm(original)
        analyses.append({**item, "question_original": original, "question_normalized": normalized, "question_term_expanded": "", "encoding_warning": ""})
    diagnostics = {int(row["question_id"]): row for row in rows(output_dir / "document_question_diagnostics.csv")}
    records = {row["file_id"]: row for row in rows(run_dir / "inventory" / "file_records.csv")}
    structures = {path.stem: json.load(path.open(encoding="utf-8")) for path in (run_dir / "extracted" / "extracted").glob("*.json")}
    reclass = []; format_rows = []
    for analysis in analyses:
        qid = int(analysis["index"]); before = diagnostics.get(qid, {}).get("subtype", ""); normalized = analysis.get("question_normalized", ""); subtype = classify(normalized)
        if qid not in diagnostics and not is_document_question(normalized):
            continue
        reclass.append({"question_id": qid, "question_original": analysis.get("question_original", ""), "question_normalized": normalized, "question_term_expanded": analysis.get("question_term_expanded", ""), "before_subtype": before, "after_subtype": subtype, "subtype_changed": str(before != subtype).lower(), "change_reason": "raw_question_normalization_and_explicit_format_cues", "encoding_warning": analysis.get("encoding_warning", "")})
        if subtype != "format_only": continue
        diag = diagnostics.get(qid, {}); ids = [item.strip() for item in diag.get("actual_used_file_ids", "").split("|") if item.strip()]
        condition = {}; 
        if "太字" in normalized: condition["bold"] = True
        if "斜体" in normalized or "イタリック" in normalized: condition["italic"] = True
        if "下線" in normalized: condition["underline"] = True
        if "黄色" in normalized or "ハイライト" in normalized: condition["highlight_color"] = "yellow"
        if "赤で強調" in normalized or "赤字" in normalized: condition["font_color"] = "red"
        for file_id in ids:
            record = records.get(file_id, {}); path = root / record.get("raw_path", ""); structure = structures.get(file_id, {}); raw = raw_format_counts(path, condition); ir = ir_format_counts(structure, condition)
            if condition.get("highlight_color") == "yellow":
                raw["raw_combined_condition_count"] = raw.get("raw_yellow_highlight_count", 0)
            format_rows.append({"question_id": qid, "source_path": record.get("raw_path", ""), "file_type": record.get("extension", ""), **raw, **ir, "reconstructed_item_count": diag.get("reconstructed_item_count", ""), "primary_cause": "matched" if raw.get("raw_combined_condition_count", 0) == ir.get("ir_combined_condition_count", 0) else "lost_during_extraction"})
    for name, data in (("question_representation_audit.csv", reclass), ("document_subtype_reclassification.csv", reclass), ("format_raw_ir_summary.csv", format_rows)):
        fields = list(data[0]) if data else ["question_id"]
        with (output_dir / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(data)
    counts = Counter(row["after_subtype"] for row in reclass)
    with (output_dir / "document_subtype_reclassification_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["subtype", "question_count"]); writer.writeheader(); writer.writerows({"subtype": key, "question_count": value} for key, value in sorted(counts.items()))
    print(json.dumps({"question_count": len(reclass), "subtype_counts": dict(counts), "format_question_count": counts.get("format_only", 0), "format_file_count": len(format_rows)}, ensure_ascii=False))


if __name__ == "__main__": main()
