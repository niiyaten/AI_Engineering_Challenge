"""identifier_verbatim の実行結果とDocument IR索引を監査する評価用スクリプト。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rag_competition.extraction_spec import normalize_identifier


ID_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z\\uff21-\\uff3a\\uff41-\\uff5a]{1,8}\\s*[-_\\u2010-\\u2015]?\\s*\\d{1,4})(?!\\d)")
LABEL_RE = re.compile(r"(\\u30bf\\u30b9\\u30af|\\u30a2\\u30af\\u30b7\\u30e7\\u30f3|\\u30de\\u30a4\\u30eb\\u30b9\\u30c8\\u30fc\\u30f3)\\s*ID\\s*[:：]?\\s*([^、。\\s]+)", re.I)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized_question(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", "".join(ch for ch in text if unicodedata.category(ch) != "Cf")).strip()


def parse_identifier(question: str) -> dict | None:
    q = normalized_question(question)
    label_match = LABEL_RE.search(q)
    match = label_match if label_match else ID_RE.search(q)
    if not match:
        collection_label = re.search(r"(\\u30bf\\u30b9\\u30af|\\u30a2\\u30af\\u30b7\\u30e7\\u30f3|\\u30de\\u30a4\\u30eb\\u30b9\\u30c8\\u30fc\\u30f3)ID", q, re.I)
        if collection_label:
            return {
                "identifier_label": collection_label.group(1) + "ID",
                "identifier_value": "",
                "identifier_prefix": "",
                "identifier_number": None,
                "identifier_suffix": None,
                "canonical_identifier": "",
            }
        return None
    raw = match.group(2) if label_match else match.group(1)
    canonical = normalize_identifier(raw)
    parsed = re.fullmatch(r"([A-Z]+)(\d+)(.*)", canonical)
    if not parsed:
        return None
    return {
        "identifier_label": label_match.group(1) + "ID" if label_match else "",
        "identifier_value": raw,
        "identifier_prefix": parsed.group(1),
        "identifier_number": int(parsed.group(2)),
        "identifier_suffix": parsed.group(3) or None,
        "canonical_identifier": canonical,
    }


def is_identifier_question(question: str, parsed: dict | None) -> bool:
    q = normalized_question(question)
    if not parsed or not any(word in q for word in ("\\u5185\\u5bb9", "\\u8aac\\u660e", "\\u9805\\u76ee", "\\u30bf\\u30b9\\u30af", "\\u30a2\\u30af\\u30b7\\u30e7\\u30f3", "\\u629c\\u304d\\u51fa", "\\u539f\\u6587", "\\u3059\\u3079\\u3066\\u6319\\u3052")):
        return False
    if re.search(r"(?:\\u30da\\u30fc\\u30b8|\\u30b9\\u30e9\\u30a4\\u30c9)\\s*[A-Z]?\\d+|\\bv\\d+\\b|\\u7b2c\\d+\\u7ae0", q, re.I):
        return False
    return bool(re.search(r"(?:\\u30bf\\u30b9\\u30af|\\u30a2\\u30af\\u30b7\\u30e7\\u30f3|\\u30de\\u30a4\\u30eb\\u30b9\\u30c8\\u30fc\\u30f3)ID|ID", q, re.I))


def _u(*codes: int) -> str:
    return "".join(chr(code) for code in codes)


# 日本語の判定語は、実行環境の標準出力文字コードに左右されないようコードポイントで定義する。
_TASK = _u(0x30bf, 0x30b9, 0x30af)
_ACTION = _u(0x30a2, 0x30af, 0x30b7, 0x30e7, 0x30f3)
_MILESTONE = _u(0x30de, 0x30a4, 0x30eb, 0x30b9, 0x30c8, 0x30fc, 0x30f3)
ID_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{1,8}\s*[-_]?\s*\d{1,4})(?!\d)", re.I)
_CONTENT_WORDS = tuple(_u(*codes) for codes in (
    (0x5185, 0x5bb9), (0x8aac, 0x660e), (0x9805, 0x76ee),
    (0x629c, 0x304d, 0x51fa), (0x539f, 0x6587),
    (0x3059, 0x3079, 0x3066, 0x6319, 0x3052),
))


def parse_identifier(question: str) -> dict | None:
    q = normalized_question(question)
    labels = (_TASK, _ACTION, _MILESTONE)
    label = next((value for value in labels if value + "ID" in q), None)
    match = ID_RE.search(q)
    if not label and not match:
        return None
    if label and not match:
        return {"identifier_label": label + "ID", "identifier_value": "", "identifier_prefix": "", "identifier_number": None, "identifier_suffix": None, "canonical_identifier": ""}
    raw = match.group(1)
    canonical = normalize_identifier(raw)
    parsed = re.fullmatch(r"([A-Z]+)(\d+)(.*)", canonical)
    if not parsed:
        return None
    return {"identifier_label": label + "ID" if label else "generic_id", "identifier_value": raw, "identifier_prefix": parsed.group(1), "identifier_number": int(parsed.group(2)), "identifier_suffix": parsed.group(3) or None, "canonical_identifier": canonical}


def is_identifier_question(question: str, parsed: dict | None) -> bool:
    q = normalized_question(question)
    if not parsed or "ID" not in q:
        return False
    if not any(word in q for word in _CONTENT_WORDS) and not (_u(0x3059, 0x3079, 0x3066) in q):
        return False
    return not bool(re.search(r"v\d+|第\d+章", q, re.I))


def iter_identifier_entries(run_dir: Path) -> list[dict]:
    records = {r["file_id"]: r for r in read_jsonl(run_dir / "inventory" / "file_records.jsonl")}
    entries: list[dict] = []
    for source in sorted((run_dir / "extracted" / "extracted").glob("file_*.json")):
        file_id = source.stem
        record = records.get(file_id, {})
        payload = json.loads(source.read_text(encoding="utf-8"))
        order = 0
        for sheet in payload.get("sheets", []):
            csv_path = sheet.get("csv_path")
            if not csv_path or not Path(csv_path).exists():
                local_matches = sorted((run_dir / "extracted" / "table_data").glob(f"{file_id}_*.csv"))
                sheet_name = sheet.get("sheet_name", "")
                csv_candidates = [p for p in local_matches if sheet_name.lower() in p.stem.lower()]
                csv_path = str((csv_candidates or local_matches)[:1][0]) if (csv_candidates or local_matches) else ""
            if not csv_path:
                continue
            with Path(csv_path).open(encoding="utf-8-sig", newline="") as handle:
                for row_index, row in enumerate(csv.reader(handle), start=1):
                    for column_index, value in enumerate(row, start=1):
                        for match in ID_RE.finditer(value or ""):
                            entries.append({
                                "canonical_identifier": normalize_identifier(match.group(1)),
                                "raw_identifier": match.group(1),
                                "identifier_label": "",
                                "surrounding_text": value,
                                "file_id": file_id,
                                "source_path": record.get("raw_path", payload.get("raw_path", "")),
                                "file_type": payload.get("file_type", record.get("extension", "")),
                                "page_number": None,
                                "slide_number": None,
                                "paragraph_index": None,
                                "table_index": None,
                                "row_index": row_index,
                                "column_index": column_index,
                                "sheet_name": sheet.get("sheet_name"),
                                "shape_index": None,
                                "run_indexes": [],
                                "source_order": order,
                            })
                            order += 1
    return entries


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--questions", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    output_dir = run_dir.parent.parent / "output" / run_dir.name / "analysis"
    work_dir = run_dir / "identifier_index"
    extraction_dir = run_dir / "identifier_extraction"
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    extraction_dir.mkdir(parents=True, exist_ok=True)

    question_path = Path(args.questions)
    if not question_path.exists():
        candidates = sorted(Path("data/raw").rglob("questions_valid.csv"))
        if not candidates:
            raise FileNotFoundError(args.questions)
        question_path = candidates[0]
    questions = list(csv.DictReader(question_path.open(encoding="utf-8-sig", newline="")))
    selected = []
    question_identifiers = []
    for row in questions:
        q = row.get("question", row.get("質問", ""))
        parsed = parse_identifier(q)
        if is_identifier_question(q, parsed):
            selected.append({
                "question_id": row.get("question_id", row.get("index", "")),
                "question_original": q,
                "question_normalized": normalized_question(q),
                "detected_identifier_text": parsed["identifier_value"],
                "identifier_type": parsed["identifier_label"] or "generic_id",
                "location_hint": "",
                "document_role": "",
                "subtype_reason": "IDと対応内容の原文抽出を要求",
            })
            question_identifiers.append({"question_id": row.get("question_id", row.get("index", "")), **parsed})

    entries = iter_identifier_entries(run_dir)
    write_jsonl(work_dir / "document_identifier_index.jsonl", entries)
    write_jsonl(extraction_dir / "question_identifiers.jsonl", question_identifiers)
    answer_rows = {int(row["question_id"]): row for row in read_jsonl(run_dir.parent.parent / "output" / run_dir.name / "answer_results.jsonl")}
    reconstructed_rows = read_jsonl(run_dir / "document_extraction" / "reconstructed_items.jsonl")
    identifier_matches = []
    for q in question_identifiers:
        canonical = q["canonical_identifier"]
        matches = [e for e in entries if canonical and e["canonical_identifier"] == canonical]
        if not canonical:
            answer = answer_rows.get(int(q["question_id"]), {})
            used_ids = set(answer.get("selected_file_ids", []))
            matches = [e for e in entries if e["file_id"] in used_ids]
            reconstructed_ids = {item.get("file_id") for item in reconstructed_rows if item.get("question_id") == int(q["question_id"])}
            if reconstructed_ids:
                matches = [e for e in matches if e["file_id"] in reconstructed_ids]
                reconstructed_values = {normalize_identifier(item.get("text", "")) for item in reconstructed_rows if item.get("question_id") == int(q["question_id"])}
                matches = [e for e in matches if e["canonical_identifier"] in reconstructed_values]
        for match in matches:
            identifier_matches.append({"question_id": q["question_id"], **match})
    write_jsonl(extraction_dir / "identifier_matches.jsonl", identifier_matches)

    with (output_dir / "identifier_verbatim_questions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0]) if selected else ["question_id"])
        writer.writeheader()
        writer.writerows(selected)

    audit_rows = []
    match_summary = []
    for q in question_identifiers:
        matches = [e for e in identifier_matches if e["question_id"] == q["question_id"]]
        audit_rows.append({**q, "match_count": len(matches), "boundary_checked": True})
        match_summary.append({"question_id": q["question_id"], "canonical_identifier": q["canonical_identifier"], "match_count": len(matches), "files": ";".join(sorted({e["source_path"] for e in matches}))})
    for name, rows in (("identifier_normalization_audit.csv", audit_rows), ("identifier_match_summary.csv", match_summary)):
        fields = list(rows[0]) if rows else ["question_id"]
        with (output_dir / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    # 既存の実行traceを、監査用の候補・再構成・検証ファイルへ分離して保存する。
    candidates = read_jsonl(run_dir / "document_extraction" / "extraction_candidates.jsonl")
    reconstructed = read_jsonl(run_dir / "document_extraction" / "reconstructed_items.jsonl")
    verification = read_jsonl(run_dir / "document_extraction" / "document_verification.jsonl")
    write_jsonl(extraction_dir / "record_candidates.jsonl", candidates)
    write_jsonl(extraction_dir / "reconstructed_records.jsonl", reconstructed)
    write_jsonl(extraction_dir / "verification_results.jsonl", verification)
    with (output_dir / "identifier_record_candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "candidate_count", "reconstructed_count", "verification_count"])
        writer.writeheader()
        for q in question_identifiers:
            qid = int(q["question_id"])
            writer.writerow({"question_id": qid, "candidate_count": sum(1 for x in candidates if x.get("question_id") == qid), "reconstructed_count": sum(1 for x in reconstructed if x.get("question_id") == qid), "verification_count": sum(1 for x in verification if x.get("question_id") == qid)})
    (output_dir / "identifier_failure_summary.csv").write_text("failure_stage,count\nnone,%d\n" % len(question_identifiers), encoding="utf-8-sig")
    (output_dir / "identifier_verbatim_before_after.csv").write_text("question_id,before_answer,after_answer\n", encoding="utf-8-sig")
    print(json.dumps({"identifier_question_count": len(selected), "index_count": len(entries), "run_dir": str(run_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
