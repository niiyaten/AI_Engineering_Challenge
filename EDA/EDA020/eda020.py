from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


# eda020.py は「プロジェクト直下 / EDA / EDA020 / eda020.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"
EMBEDDING_DIR = BASE_DIR / "data" / "processed" / "embedding"
EMBEDDING_RECORDS_PATH = EMBEDDING_DIR / "embedding_records.jsonl"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda020_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda020.log"


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    EMBEDDING_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def normalize_text(value: Any) -> str:
    """Windows上の濁点表記揺れをNFCへ寄せる。"""
    return unicodedata.normalize("NFC", "" if value is None else str(value))


def relative(path: Path) -> str:
    """プロジェクト相対パスを返す。"""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def compact_text(value: Any) -> str:
    """検索用テキストの空白を整える。"""
    text = normalize_text(value)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def markdown_table(rows: list[dict[str, Any]], max_rows: int = 30) -> str:
    """追加依存なしでMarkdown表を作る。"""
    if not rows:
        return "該当データはありません。"
    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:max_rows]:
        vals = []
        for col in columns:
            text = normalize_text(row.get(col, "")).replace("|", "\\|").replace("\n", " ")
            vals.append(text[:500])
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Excelでも読みやすいUTF-8 BOM付きCSVを保存する。"""
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns = list(dict.fromkeys(col for row in rows for col in row.keys()))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def record_id(record_type: str, source_path: str, key: str) -> str:
    """同じ入力から同じIDが作られるようにする。"""
    digest = hashlib.sha1(f"{record_type}|{source_path}|{key}".encode("utf-8")).hexdigest()[:16]
    return f"{record_type}_{digest}"


def make_record(record_type: str, source_path: str, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """統合JSONLの1レコードを作る。"""
    key = json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str)
    return {
        "record_id": record_id(record_type, source_path, key),
        "record_type": record_type,
        "source_path": normalize_text(source_path),
        "text_for_embedding": compact_text(text),
        "metadata": metadata,
    }


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """長い本文を検索しやすい文字数に分割する。"""
    text = compact_text(text)
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def load_json(path: Path) -> dict[str, Any]:
    """UTF-8 JSONを読む。"""
    return json.loads(path.read_text(encoding="utf-8"))


def read_markdown(path_text: str) -> str:
    """processed Markdownがあれば読む。"""
    if not path_text:
        return ""
    path = BASE_DIR / path_text
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def add_metadata_record(records: list[dict[str, Any]], doc: dict[str, Any], json_path: Path) -> None:
    """ファイル単位メタデータを検索対象に入れる。"""
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    file_type = normalize_text(doc.get("file_type", ""))
    text = "\n".join(
        [
            f"ファイル名: {doc.get('file_name', '')}",
            f"元パス: {source_path}",
            f"ファイル種別: {file_type}",
        ]
    )
    records.append(
        make_record(
            "metadata",
            source_path,
            text,
            {
                "file_type": file_type,
                "structure_json_path": relative(json_path),
                "processed_markdown_path": doc.get("processed_markdown_path", ""),
            },
        )
    )


def records_from_docx(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """Word構造JSONから段落・表レコードを作る。"""
    records: list[dict[str, Any]] = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    heading_path: list[str] = []
    for block in doc.get("blocks", []):
        block_type = block.get("block_type")
        text = compact_text(block.get("markdown") or block.get("text", ""))
        if not text:
            continue
        style = normalize_text(block.get("style", ""))
        match = re.search(r"Heading\s+(\d+)", style, flags=re.IGNORECASE)
        if match:
            level = int(match.group(1))
            heading_path = heading_path[: max(level - 1, 0)] + [compact_text(block.get("text", ""))]
        record_type = "docx_table" if block_type == "table" else "docx_paragraph"
        records.append(
            make_record(
                record_type,
                source_path,
                text,
                {
                    "file_type": "docx",
                    "block_index": block.get("block_index"),
                    "heading_path": " > ".join(heading_path),
                    "structure_json_path": relative(json_path),
                    "processed_markdown_path": doc.get("processed_markdown_path", ""),
                },
            )
        )
    return records


def records_from_tabular(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """CSV/TSV/Excel構造JSONから表検索レコードを作る。"""
    records: list[dict[str, Any]] = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    file_type = normalize_text(doc.get("file_type", ""))
    if file_type == "xlsx":
        for sheet in doc.get("sheets", []):
            profile = sheet.get("profile", {})
            cols = ", ".join(profile.get("columns", [])[:80])
            sample = markdown_table(profile.get("sample_rows", []), max_rows=8)
            text = "\n".join(
                [
                    f"Excelファイル: {doc.get('file_name', '')}",
                    f"シート: {sheet.get('sheet_name', '')}",
                    f"使用範囲: {sheet.get('dimension', '')}",
                    f"列: {cols}",
                    f"グラフ数: {sheet.get('chart_count', 0)}",
                    "サンプル:",
                    sample,
                ]
            )
            records.append(
                make_record(
                    "xlsx_sheet",
                    source_path,
                    text,
                    {
                        "file_type": "xlsx",
                        "sheet_name": sheet.get("sheet_name", ""),
                        "exported_csv_path": sheet.get("exported_csv_path", ""),
                        "structure_json_path": relative(json_path),
                    },
                )
            )
            for chart in sheet.get("charts", []):
                records.append(
                    make_record(
                        "xlsx_chart",
                        source_path,
                        json.dumps(chart, ensure_ascii=False),
                        {
                            "file_type": "xlsx",
                            "sheet_name": sheet.get("sheet_name", ""),
                            "chart_index": chart.get("chart_index"),
                            "structure_json_path": relative(json_path),
                        },
                    )
                )
    elif file_type in {"csv", "tsv"}:
        cols = ", ".join(doc.get("columns", [])[:120])
        sample = markdown_table(doc.get("sample_rows", []), max_rows=8)
        text = "\n".join(
            [
                f"表ファイル: {doc.get('file_name', '')}",
                f"形式: {file_type}",
                f"行数: {doc.get('row_count', '')}",
                f"列数: {doc.get('column_count', '')}",
                f"列: {cols}",
                "サンプル:",
                sample,
            ]
        )
        records.append(
            make_record(
                "table_file",
                source_path,
                text,
                {
                    "file_type": file_type,
                    "normalized_csv_path": doc.get("normalized_csv_path", ""),
                    "structure_json_path": relative(json_path),
                },
            )
        )
    return records


def records_from_pptx(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """PowerPoint構造JSONからスライド単位レコードを作る。"""
    records: list[dict[str, Any]] = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    for slide in doc.get("slides", []):
        parts = [f"Slide {slide.get('slide_number')}"]
        for shape in slide.get("shapes", []):
            if shape.get("text"):
                parts.append(shape["text"])
            if shape.get("table"):
                parts.append(table_from_cells(shape["table"].get("cells", [])))
            if shape.get("chart"):
                parts.append("Chart: " + json.dumps(shape["chart"], ensure_ascii=False, default=str))
            if shape.get("image"):
                parts.append("Image: " + normalize_text(shape["image"].get("image_path", "")))
        if slide.get("notes"):
            parts.append("Notes: " + normalize_text(slide.get("notes", "")))
        text = "\n".join(part for part in parts if compact_text(part))
        records.append(
            make_record(
                "pptx_slide",
                source_path,
                text,
                {
                    "file_type": "pptx",
                    "slide_number": slide.get("slide_number"),
                    "structure_json_path": relative(json_path),
                    "processed_markdown_path": doc.get("processed_markdown_path", ""),
                },
            )
        )
    return records


def table_from_cells(cells: list[list[Any]]) -> str:
    """行列データをMarkdown表風テキストにする。"""
    if not cells:
        return ""
    rows = [{f"col_{i + 1}": val for i, val in enumerate(row)} for row in cells]
    return markdown_table(rows, max_rows=20)


def records_from_pdf(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """PDF構造JSONからページ単位レコードを作る。"""
    records = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    for page in doc.get("pages", []):
        if not compact_text(page.get("text", "")):
            continue
        records.append(
            make_record(
                "pdf_page",
                source_path,
                page.get("text", ""),
                {
                    "file_type": "pdf",
                    "page_number": page.get("page_number"),
                    "structure_json_path": relative(json_path),
                    "processed_markdown_path": doc.get("processed_markdown_path", ""),
                },
            )
        )
    return records


def records_from_python(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """Python構造JSONとMarkdownからコード読解用レコードを作る。"""
    records = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    summary = "\n".join(
        [
            f"Pythonファイル: {doc.get('file_name', '')}",
            f"行数: {doc.get('line_count', '')}",
            "imports: " + ", ".join(row.get("module", "") or row.get("name", "") for row in doc.get("imports", [])[:80]),
            "functions: " + ", ".join(fn.get("name", "") for fn in doc.get("functions", [])[:80]),
            "file_operations: " + json.dumps(doc.get("file_operations", [])[:30], ensure_ascii=False, default=str),
        ]
    )
    records.append(make_record("python_summary", source_path, summary, {"file_type": "py", "structure_json_path": relative(json_path)}))
    for fn in doc.get("functions", []):
        text = f"関数: {fn.get('name')}\n行: {fn.get('lineno')}-{fn.get('end_lineno')}\n引数: {', '.join(fn.get('args', []))}\n説明: {fn.get('docstring', '')}"
        records.append(
            make_record(
                "python_function",
                source_path,
                text,
                {"file_type": "py", "function": fn.get("name"), "lineno": fn.get("lineno"), "structure_json_path": relative(json_path)},
            )
        )
    markdown = read_markdown(doc.get("processed_markdown_path", ""))
    for i, chunk in enumerate(chunk_text(markdown, args.max_chars, args.overlap), start=1):
        records.append(
            make_record(
                "python_code_chunk",
                source_path,
                chunk,
                {"file_type": "py", "chunk_index": i, "structure_json_path": relative(json_path), "processed_markdown_path": doc.get("processed_markdown_path", "")},
            )
        )
    return records


def records_from_notebook(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """Notebook構造JSONからセル単位レコードを作る。"""
    records = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    for cell in doc.get("cells", []):
        parts = [
            f"Notebook: {doc.get('file_name', '')}",
            f"Cell {cell.get('cell_index')}: {cell.get('cell_type')}",
            normalize_text(cell.get("source", "")),
        ]
        for output in cell.get("outputs", [])[:5]:
            if output.get("text"):
                parts.append("Output: " + normalize_text(output.get("text", ""))[:3000])
            for asset in output.get("assets", []):
                parts.append("Asset: " + normalize_text(asset.get("path", "")))
        records.append(
            make_record(
                "notebook_cell",
                source_path,
                "\n".join(parts),
                {
                    "file_type": "ipynb",
                    "cell_index": cell.get("cell_index"),
                    "cell_type": cell.get("cell_type"),
                    "structure_json_path": relative(json_path),
                    "processed_markdown_path": doc.get("processed_markdown_path", ""),
                },
            )
        )
    return records


def records_from_markdown(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """既存Markdown構造JSONからチャンクレコードを作る。"""
    records = []
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    markdown = read_markdown(doc.get("processed_markdown_path", ""))
    for i, chunk in enumerate(chunk_text(markdown, args.max_chars, args.overlap), start=1):
        records.append(
            make_record(
                "markdown_chunk",
                source_path,
                chunk,
                {
                    "file_type": "md",
                    "chunk_index": i,
                    "structure_json_path": relative(json_path),
                    "processed_markdown_path": doc.get("processed_markdown_path", ""),
                },
            )
        )
    return records


def records_from_generic(doc: dict[str, Any], json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """未分類の構造JSONはMarkdownをチャンク化して拾う。"""
    source_path = normalize_text(doc.get("raw_relative_path", ""))
    markdown = read_markdown(doc.get("processed_markdown_path", ""))
    records = []
    for i, chunk in enumerate(chunk_text(markdown, args.max_chars, args.overlap), start=1):
        records.append(
            make_record(
                "generic_chunk",
                source_path,
                chunk,
                {
                    "file_type": doc.get("file_type", ""),
                    "chunk_index": i,
                    "structure_json_path": relative(json_path),
                    "processed_markdown_path": doc.get("processed_markdown_path", ""),
                },
            )
        )
    return records


def records_from_structure_json(json_path: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    """構造JSONをファイル種別ごとの検索レコードへ変換する。"""
    doc = load_json(json_path)
    records: list[dict[str, Any]] = []
    add_metadata_record(records, doc, json_path)
    file_type = normalize_text(doc.get("file_type", ""))
    if file_type == "docx":
        records.extend(records_from_docx(doc, json_path, args))
    elif file_type in {"xlsx", "csv", "tsv"}:
        records.extend(records_from_tabular(doc, json_path, args))
    elif file_type == "pptx":
        records.extend(records_from_pptx(doc, json_path, args))
    elif file_type == "pdf":
        records.extend(records_from_pdf(doc, json_path, args))
    elif file_type == "py":
        records.extend(records_from_python(doc, json_path, args))
    elif file_type == "ipynb":
        records.extend(records_from_notebook(doc, json_path, args))
    elif file_type == "md":
        records.extend(records_from_markdown(doc, json_path, args))
    else:
        records.extend(records_from_generic(doc, json_path, args))
    return records


def carry_over_image_records(existing_path: Path) -> list[dict[str, Any]]:
    """EDA013で作成したraw画像説明レコードを、再統合時にも残す。"""
    if not existing_path.exists():
        return []
    records = []
    for line in existing_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("record_type") == "image" and normalize_text(record.get("source_path", "")).startswith("data/raw/"):
            records.append(record)
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """1行1レコードのJSONLを保存する。"""
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def write_report(records: list[dict[str, Any]], error_rows: list[dict[str, Any]]) -> None:
    """EDA020の統合結果をMarkdownレポートへ保存する。"""
    type_rows = [
        {"record_type": key, "count": value}
        for key, value in sorted(Counter(record["record_type"] for record in records).items())
    ]
    file_type_rows = [
        {"file_type": key, "count": value}
        for key, value in sorted(Counter(record["metadata"].get("file_type", "") for record in records).items())
    ]
    empty_count = sum(1 for record in records if not compact_text(record.get("text_for_embedding", "")))
    duplicate_ids = len(records) - len({record["record_id"] for record in records})
    lines = [
        "# EDA020: 統合embedding_records作成",
        "",
        "## 目的",
        "",
        "EDA012からEDA019までで作成したMarkdown/JSON/assetsを、検索、BM25、embedding、LLM入力で共通利用できるJSONLへ統合する。",
        "",
        "## 出力",
        "",
        f"- embedding_records: `{relative(EMBEDDING_RECORDS_PATH)}`",
        f"- record_summary: `{relative(TABLE_DIR / 'embedding_record_summary.csv')}`",
        f"- integration_errors: `{relative(TABLE_DIR / 'integration_errors.csv')}`",
        "",
        "## 品質確認",
        "",
        f"- 総レコード数: {len(records)}",
        f"- 空テキストレコード数: {empty_count}",
        f"- record_id重複数: {duplicate_ids}",
        f"- 統合エラー数: {len(error_rows)}",
        "",
        "## record_type別件数",
        "",
        "凡例: `record_type` は検索単位の種類、`count` は件数を表します。",
        "",
        markdown_table(type_rows, max_rows=80),
        "",
        "## file_type別件数",
        "",
        "凡例: `file_type` は元ファイル形式、`count` は該当レコード数を表します。",
        "",
        markdown_table(file_type_rows, max_rows=80),
        "",
        "## 統合エラー",
        "",
        "凡例: `structure_json_path` は読み込み対象、`error_type` と `error_message` は失敗理由です。",
        "",
        markdown_table(error_rows, max_rows=40),
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(args: argparse.Namespace, records: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA020",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Integrate processed Markdown/JSON artifacts into a unified embedding_records.jsonl.",
        "parameters": {"max_chars": args.max_chars, "overlap": args.overlap},
        "record_count": len(records),
        "outputs": {
            "embedding_records": relative(EMBEDDING_RECORDS_PATH),
            "report": relative(REPORT_PATH),
            "tables": relative(TABLE_DIR),
        },
        "repro_steps": ["uv run python EDA/EDA020/eda020.py"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Integrate processed artifacts into embedding_records.jsonl.")
    parser.add_argument("--max-chars", type=int, default=1600, help="長文チャンクの最大文字数")
    parser.add_argument("--overlap", type=int, default=160, help="長文チャンクの重なり文字数")
    return parser.parse_args()


def main() -> None:
    """EDA020を実行する。"""
    args = parse_args()
    setup()
    carried_images = carry_over_image_records(EMBEDDING_RECORDS_PATH)
    records: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    for json_path in sorted(PROCESSED_SHARE_DIR.rglob("*.structure.json"), key=lambda p: normalize_text(p.as_posix()).lower()):
        try:
            records.extend(records_from_structure_json(json_path, args))
        except Exception as exc:  # noqa: BLE001
            error_rows.append(
                {
                    "structure_json_path": relative(json_path),
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc)[:1000],
                }
            )
            logging.exception("failed: %s", json_path)
    # raw画像のVision説明はprocessed/share由来ではないため、EDA013の結果を維持する。
    existing_ids = {record["record_id"] for record in records}
    for record in carried_images:
        if record.get("record_id") not in existing_ids:
            records.append(record)

    write_jsonl(records, EMBEDDING_RECORDS_PATH)
    type_rows = [
        {
            "record_type": key,
            "count": value,
            "empty_text_count": sum(1 for r in records if r["record_type"] == key and not compact_text(r.get("text_for_embedding", ""))),
        }
        for key, value in sorted(Counter(record["record_type"] for record in records).items())
    ]
    save_csv(type_rows, TABLE_DIR / "embedding_record_summary.csv")
    save_csv(error_rows, TABLE_DIR / "integration_errors.csv")
    write_report(records, error_rows)
    write_manifest(args, records)
    print(f"records={len(records)} errors={len(error_rows)} output={relative(EMBEDDING_RECORDS_PATH)}")


if __name__ == "__main__":
    main()
