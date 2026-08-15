from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import unicodedata
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

# =============================================================================
# パス設定
# =============================================================================

# eda012.py は「プロジェクト直下 / EDA / EDA012 / eda012.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_SHARE_DIR = BASE_DIR / "data" / "raw" / "share"
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda012_report.md"
LOG_PATH = OUTPUT_DIR / "eda012.log"


@dataclass
class RunStyle:
    """Word runの再現に必要な基本書式。"""

    text: str
    bold: bool
    italic: bool
    underline: bool
    font_color: str
    highlight: str
    font_name: str
    font_size_pt: float | None


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_SHARE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def normalize_path_text(text: Any) -> str:
    """Windows上の濁点表記揺れなどをNFCへ寄せる。"""
    return unicodedata.normalize("NFC", str(text))


def file_sha1(path: Path) -> str:
    """変換元ファイルの追跡用にSHA1を計算する。"""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def markdown_escape(text: Any) -> str:
    """Markdownの表や装飾を壊しやすい文字を最小限だけエスケープする。"""
    value = str(text)
    value = value.replace("\\", "\\\\")
    value = value.replace("|", "\\|")
    return value


def html_escape(text: Any) -> str:
    """HTMLタグ内に入れるテキストを安全にする。"""
    value = str(text)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def safe_attr(text: Any) -> str:
    """Markdown内HTML属性に入れる値を安全にする。"""
    return html_escape(text).replace("\n", " ").replace("\r", " ")


def text_or_empty(value: Any) -> str:
    """Noneを空文字にする。"""
    return "" if value is None else str(value)


def run_style(run: Any) -> RunStyle:
    """Word runから再現用の書式情報を取り出す。"""
    font = run.font
    color = ""
    if font.color is not None and font.color.rgb is not None:
        color = f"#{font.color.rgb}"
    highlight = ""
    if font.highlight_color is not None:
        highlight = str(font.highlight_color)
    font_size_pt = None
    if font.size is not None:
        font_size_pt = round(font.size.pt, 2)
    return RunStyle(
        text=text_or_empty(run.text),
        bold=bool(run.bold),
        italic=bool(run.italic),
        underline=bool(run.underline),
        font_color=color,
        highlight=highlight,
        font_name=text_or_empty(font.name),
        font_size_pt=font_size_pt,
    )


def styled_run_to_markdown(style: RunStyle) -> str:
    """Word runを、MarkdownとHTMLを併用した再現可能な表現へ変換する。"""
    text = html_escape(style.text)
    if not text:
        return ""
    if style.bold:
        text = f"**{text}**"
    if style.italic:
        text = f"*{text}*"
    if style.underline:
        text = f"<u>{text}</u>"
    attrs: list[str] = []
    if style.font_color:
        attrs.append(f'data-font-color="{safe_attr(style.font_color)}"')
        attrs.append(f'style="color:{safe_attr(style.font_color)}"')
    if style.highlight:
        attrs.append(f'data-highlight="{safe_attr(style.highlight)}"')
        text = f"<mark {' '.join(attrs)}>{text}</mark>"
    elif attrs:
        text = f"<span {' '.join(attrs)}>{text}</span>"
    if style.font_name or style.font_size_pt is not None:
        text = (
            f'<span data-font-name="{safe_attr(style.font_name)}" '
            f'data-font-size-pt="{safe_attr(style.font_size_pt or "")}">{text}</span>'
        )
    return text


def paragraph_to_record(paragraph: Paragraph, block_index: int) -> dict[str, Any]:
    """段落をMarkdown表示用と再現用JSONの両方へ変換する。"""
    styles = [run_style(run) for run in paragraph.runs]
    markdown = "".join(styled_run_to_markdown(style) for style in styles)
    plain_text = "".join(style.text for style in styles)
    return {
        "block_index": block_index,
        "block_type": "paragraph",
        "style": text_or_empty(paragraph.style.name if paragraph.style else ""),
        "text": plain_text,
        "markdown": markdown,
        "runs": [asdict(style) for style in styles],
    }


def cell_to_text(cell: Any) -> str:
    """表セル内の段落を1つの文字列にまとめる。"""
    return "\n".join(paragraph.text for paragraph in cell.paragraphs).strip()


def table_to_record(table: Table, block_index: int) -> dict[str, Any]:
    """Word表をMarkdown表と再現用JSONへ変換する。"""
    rows: list[list[str]] = []
    for row in table.rows:
        rows.append([cell_to_text(cell) for cell in row.cells])

    markdown_lines: list[str] = []
    if rows:
        header = [markdown_escape(cell) for cell in rows[0]]
        markdown_lines.append("| " + " | ".join(header) + " |")
        markdown_lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in rows[1:]:
            markdown_lines.append("| " + " | ".join(markdown_escape(cell) for cell in row) + " |")

    return {
        "block_index": block_index,
        "block_type": "table",
        "row_count": len(rows),
        "column_count": max((len(row) for row in rows), default=0),
        "cells": rows,
        "markdown": "\n".join(markdown_lines),
    }


def iter_block_items(document: DocxDocument) -> Iterable[Paragraph | Table]:
    """Word本文内の段落と表を、出現順に走査する。"""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def extract_images(document: DocxDocument, assets_dir: Path) -> list[dict[str, Any]]:
    """Word内の画像パーツをassetsへ保存し、再現用メタデータを返す。"""
    assets_dir.mkdir(parents=True, exist_ok=True)
    images: list[dict[str, Any]] = []
    for rel_id, rel in document.part.rels.items():
        if "image" not in rel.reltype:
            continue
        target_part = rel.target_part
        extension = Path(target_part.partname).suffix or ".bin"
        image_name = f"{rel_id}{extension}"
        image_path = assets_dir / image_name
        image_path.write_bytes(target_part.blob)
        images.append(
            {
                "rel_id": rel_id,
                "partname": str(target_part.partname),
                "output_path": image_path.relative_to(BASE_DIR).as_posix(),
                "bytes": image_path.stat().st_size,
            }
        )
    return images


def processed_paths(raw_docx_path: Path) -> tuple[Path, Path, Path]:
    """raw/shareからの相対構造をdata/processed/share配下に再現した出力先を返す。"""
    rel = raw_docx_path.relative_to(RAW_SHARE_DIR)
    output_base = PROCESSED_SHARE_DIR / normalize_path_text(rel.as_posix())
    md_path = output_base.with_suffix(output_base.suffix + ".md")
    json_path = output_base.with_suffix(output_base.suffix + ".structure.json")
    assets_dir = output_base.with_suffix(output_base.suffix + ".assets")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    return md_path, json_path, assets_dir


def markdown_document(record: dict[str, Any]) -> str:
    """抽出済みレコードからLLM可読なMarkdown本文を作る。"""
    lines: list[str] = [
        f"# Word Markdown: {record['file_name']}",
        "",
        "## Source",
        f"- raw_path: `{record['raw_relative_path']}`",
        f"- source_sha1: `{record['source_sha1']}`",
        f"- paragraph_count: {record['paragraph_count']}",
        f"- table_count: {record['table_count']}",
        f"- image_count: {record['image_count']}",
        "",
        "## Body",
        "",
    ]
    for block in record["blocks"]:
        if block["block_type"] == "paragraph":
            style = block.get("style", "")
            lines.append(f"<!-- block_index={block['block_index']} type=paragraph style={safe_attr(style)} -->")
            markdown = block.get("markdown", "")
            if style.lower().startswith("heading"):
                level_match = re.search(r"(\d+)", style)
                level = min(max(int(level_match.group(1)) if level_match else 2, 2), 6)
                lines.append(f"{'#' * level} {markdown}")
            else:
                lines.append(markdown)
            lines.append("")
        elif block["block_type"] == "table":
            lines.append(f"<!-- block_index={block['block_index']} type=table rows={block['row_count']} cols={block['column_count']} -->")
            lines.append(block.get("markdown", ""))
            lines.append("")
    if record["images"]:
        lines.append("## Extracted Images")
        lines.append("")
        for image in record["images"]:
            lines.append(f"- `{image['output_path']}` ({image['bytes']} bytes)")
    return "\n".join(lines).rstrip() + "\n"


def convert_docx(raw_docx_path: Path) -> dict[str, Any]:
    """1つのdocxをMarkdownと再現用JSONへ変換する。"""
    md_path, json_path, assets_dir = processed_paths(raw_docx_path)
    document = Document(raw_docx_path)
    blocks: list[dict[str, Any]] = []
    paragraph_count = 0
    table_count = 0
    for block_index, block in enumerate(iter_block_items(document), start=1):
        if isinstance(block, Paragraph):
            paragraph_count += 1
            blocks.append(paragraph_to_record(block, block_index))
        elif isinstance(block, Table):
            table_count += 1
            blocks.append(table_to_record(block, block_index))

    images = extract_images(document, assets_dir)
    record = {
        "raw_relative_path": raw_docx_path.relative_to(RAW_SHARE_DIR).as_posix(),
        "processed_markdown_path": md_path.relative_to(BASE_DIR).as_posix(),
        "processed_structure_path": json_path.relative_to(BASE_DIR).as_posix(),
        "file_name": raw_docx_path.name,
        "source_sha1": file_sha1(raw_docx_path),
        "paragraph_count": paragraph_count,
        "table_count": table_count,
        "image_count": len(images),
        "blocks": blocks,
        "images": images,
    }
    md_path.write_text(markdown_document(record), encoding="utf-8")
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "raw_relative_path": record["raw_relative_path"],
        "status": "ok",
        "processed_markdown_path": record["processed_markdown_path"],
        "processed_structure_path": record["processed_structure_path"],
        "paragraph_count": paragraph_count,
        "table_count": table_count,
        "image_count": len(images),
        "markdown_bytes": md_path.stat().st_size,
        "structure_bytes": json_path.stat().st_size,
        "error_type": "",
        "error_message": "",
    }


def should_skip_docx(path: Path) -> bool:
    """Office一時ファイルを除外する。"""
    return path.name.startswith("~$")


def clean_output_if_requested(enabled: bool) -> None:
    """必要な場合だけ、今回の出力先を作り直す。"""
    if enabled and PROCESSED_SHARE_DIR.exists():
        shutil.rmtree(PROCESSED_SHARE_DIR)
    PROCESSED_SHARE_DIR.mkdir(parents=True, exist_ok=True)


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Excelで開きやすいUTF-8 BOM付きCSVを保存する。"""
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def write_report(rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """EDA012のMarkdownレポートを保存する。"""
    ok_count = sum(row["status"] == "ok" for row in rows)
    error_rows = [row for row in rows if row["status"] != "ok"]
    total_images = sum(int(row.get("image_count") or 0) for row in rows)
    total_tables = sum(int(row.get("table_count") or 0) for row in rows)
    lines = [
        "# EDA012: Word文書の再現可能Markdown化",
        "",
        "## 目的・背景",
        "",
        "`data/raw/share` 配下のWord文書を、`data/processed/share` 配下に同じディレクトリ構成でMarkdown化します。",
        "太字、斜体、下線、文字色、ハイライト、段落スタイル、表、画像メタデータは、Markdown表示だけでなく `.structure.json` にも保存します。",
        "これにより、LLMにはMarkdownを渡し、必要に応じてJSONからWordに近い構造を再構成できるようにします。",
        "",
        "## 実行設定",
        "",
        f"- source_root: `{RAW_SHARE_DIR.relative_to(BASE_DIR).as_posix()}`",
        f"- processed_root: `{PROCESSED_SHARE_DIR.relative_to(BASE_DIR).as_posix()}`",
        f"- clean_output: {args.clean_output}",
        "",
        "## 結果",
        "",
        f"- 対象Wordファイル数: {len(rows)}",
        f"- 変換成功: {ok_count}",
        f"- 変換失敗: {len(error_rows)}",
        f"- 抽出表数: {total_tables}",
        f"- 抽出画像数: {total_images}",
        "",
        "## 失敗ファイル",
        "",
    ]
    if error_rows:
        lines.extend(["| raw_relative_path | error_type | error_message |", "|---|---|---|"])
        for row in error_rows:
            error_message = str(row["error_message"]).replace("|", "\\|")
            lines.append(f"| `{row['raw_relative_path']}` | {row['error_type']} | {error_message} |")
    else:
        lines.append("失敗ファイルはありません。")
    lines.extend(
        [
            "",
            "凡例: `raw_relative_path` は `data/raw/share` からの相対パス、`error_type` は例外種別、`error_message` は失敗理由を表します。",
            "",
            "## 主な出力",
            "",
            "| パス | 内容 |",
            "|---|---|",
            "| `data/processed/share/**/*.docx.md` | LLM入力向けMarkdown |",
            "| `data/processed/share/**/*.docx.structure.json` | Word再構成用の段落・run・表・画像メタデータ |",
            "| `EDA/EDA012/tables/docx_markdown_conversion_log.csv` | 変換ログ |",
            "",
            "凡例: `パス` は出力先、`内容` はそのファイルが持つ情報を表します。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_eda_summary(rows: list[dict[str, Any]]) -> None:
    """EDA総括へEDA012の要点を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    if "## EDA012の要点" in text:
        return
    ok_count = sum(row["status"] == "ok" for row in rows)
    error_count = len(rows) - ok_count
    marker = "## 未解決の重要点"
    addition = f"""
## EDA012の要点

EDA012では、`data/raw/share` 配下のWord文書を、`data/processed/share` 配下に同じディレクトリ構成でMarkdown化しました。太字、斜体、下線、文字色、ハイライト、段落スタイル、表、画像メタデータは、LLM向けMarkdownだけでなく `.structure.json` にも保存しています。

対象Wordファイルは {len(rows)} 件、変換成功は {ok_count} 件、変換失敗は {error_count} 件でした。出力は `data/processed/share/**/*.docx.md` と `data/processed/share/**/*.docx.structure.json` です。

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA012: convert raw/share docx files to reproducible markdown.")
    parser.add_argument("--clean-output", action="store_true", help="data/processed/share を作り直す。")
    parser.add_argument("--limit", type=int, default=None, help="デバッグ用に先頭N件だけ処理する。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()
    clean_output_if_requested(args.clean_output)

    docx_paths = [
        path
        for path in sorted(RAW_SHARE_DIR.rglob("*.docx"))
        if path.is_file() and not should_skip_docx(path)
    ]
    if args.limit is not None:
        docx_paths = docx_paths[: args.limit]

    rows: list[dict[str, Any]] = []
    for path in docx_paths:
        rel = path.relative_to(RAW_SHARE_DIR).as_posix()
        try:
            rows.append(convert_docx(path))
            logging.info("converted %s", rel)
        except (zipfile.BadZipFile, Exception) as exc:  # noqa: BLE001 - 変換失敗もログ化して継続する。
            rows.append(
                {
                    "raw_relative_path": rel,
                    "status": "error",
                    "processed_markdown_path": "",
                    "processed_structure_path": "",
                    "paragraph_count": 0,
                    "table_count": 0,
                    "image_count": 0,
                    "markdown_bytes": 0,
                    "structure_bytes": 0,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            logging.exception("failed %s", rel)

    save_csv(rows, TABLE_DIR / "docx_markdown_conversion_log.csv")
    write_report(rows, args)
    update_eda_summary(rows)
    print(f"EDA012 finished: {REPORT_PATH}")
    print(f"log: {TABLE_DIR / 'docx_markdown_conversion_log.csv'}")
    print(f"processed_root: {PROCESSED_SHARE_DIR}")


if __name__ == "__main__":
    main()
