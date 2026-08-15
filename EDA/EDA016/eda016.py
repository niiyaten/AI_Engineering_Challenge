from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


# eda016.py は「プロジェクト直下 / EDA / EDA016 / eda016.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_SHARE_DIR = BASE_DIR / "data" / "raw" / "share"
RAW_DRIVE_DIR = RAW_SHARE_DIR / "share" / "共有ドライブ"
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda016_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda016.log"


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_SHARE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def normalize_text(value: Any) -> str:
    """Windows上の濁点表記揺れなどをNFCへ寄せる。"""
    return unicodedata.normalize("NFC", "" if value is None else str(value))


def relative(path: Path) -> str:
    """プロジェクト相対パスを返す。"""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha1(path: Path) -> str:
    """入力ファイルの追跡用にSHA1を計算する。"""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def markdown_escape(value: Any) -> str:
    """Markdown表を壊しやすい文字だけを逃がす。"""
    text = normalize_text(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


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
        lines.append("| " + " | ".join(markdown_escape(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def output_paths(raw_path: Path) -> tuple[Path, Path]:
    """raw/shareからの相対構造を保ったMarkdown/JSON出力先を返す。"""
    rel = raw_path.relative_to(RAW_SHARE_DIR)
    output_base = PROCESSED_SHARE_DIR / normalize_text(rel.as_posix())
    output_base.parent.mkdir(parents=True, exist_ok=True)
    md_path = output_base.with_suffix(output_base.suffix + ".md")
    json_path = output_base.with_suffix(output_base.suffix + ".structure.json")
    return md_path, json_path


def clean_page_text(text: str) -> str:
    """PDF抽出テキストの過剰な空白だけを整える。"""
    lines = [line.rstrip() for line in normalize_text(text).splitlines()]
    cleaned = "\n".join(line for line in lines if line.strip())
    return cleaned.strip()


def process_pdf(path: Path) -> dict[str, Any]:
    """PDFをページ単位Markdownと構造JSONへ変換する。"""
    reader = PdfReader(str(path))
    md_path, json_path = output_paths(path)
    pages = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = clean_page_text(page.extract_text() or "")
        mediabox = page.mediabox
        pages.append(
            {
                "page_number": page_index,
                "text": text,
                "char_count": len(text),
                "width": float(mediabox.width),
                "height": float(mediabox.height),
                "rotation": int(page.get("/Rotate", 0) or 0),
            }
        )

    metadata = {str(key): normalize_text(value) for key, value in (reader.metadata or {}).items()}
    record = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "processed_markdown_path": relative(md_path),
        "processed_structure_path": relative(json_path),
        "file_name": path.name,
        "file_type": "pdf",
        "source_sha1": file_sha1(path),
        "page_count": len(pages),
        "metadata": metadata,
        "pages": pages,
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# PDF Markdown: {path.name}",
        "",
        "## Source",
        f"- raw_path: `{record['raw_relative_path']}`",
        f"- source_sha1: `{record['source_sha1']}`",
        f"- page_count: {record['page_count']}",
        "",
        "## Pages",
    ]
    for page in pages:
        lines.extend(["", f"### Page {page['page_number']}", "", page["text"] or "[no text extracted]"])
    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return record


def process_file(path: Path) -> dict[str, Any]:
    """1つのPDFを処理し、変換ログ行を返す。"""
    row = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "status": "",
        "error_type": "",
        "error_message": "",
        "processed_markdown_path": "",
        "processed_structure_path": "",
        "page_count": "",
        "total_char_count": "",
    }
    try:
        record = process_pdf(path)
        row.update(
            {
                "status": "ok",
                "processed_markdown_path": record["processed_markdown_path"],
                "processed_structure_path": record["processed_structure_path"],
                "page_count": record["page_count"],
                "total_char_count": sum(page["char_count"] for page in record["pages"]),
            }
        )
    except Exception as exc:  # noqa: BLE001
        row["status"] = "error"
        row["error_type"] = exc.__class__.__name__
        row["error_message"] = str(exc)[:1000]
        logging.exception("failed: %s", path)
    return row


def collect_targets() -> list[Path]:
    """共有ドライブ配下からPDFを集める。"""
    return sorted(RAW_DRIVE_DIR.rglob("*.pdf"), key=lambda p: normalize_text(p.as_posix()).lower())


def write_report(log_rows: list[dict[str, Any]]) -> None:
    """EDA016の処理結果をMarkdownレポートに保存する。"""
    ok_rows = [row for row in log_rows if row["status"] == "ok"]
    error_rows = [row for row in log_rows if row["status"] != "ok"]
    status_rows = [
        {"status": status, "count": sum(1 for row in log_rows if row["status"] == status)}
        for status in sorted({row["status"] for row in log_rows})
    ]
    total_pages = sum(int(row["page_count"] or 0) for row in ok_rows)
    total_chars = sum(int(row["total_char_count"] or 0) for row in ok_rows)
    lines = [
        "# EDA016: PDF前処理",
        "",
        "## 目的",
        "",
        "PDFをページ単位Markdownと構造JSONへ変換し、会議録、報告資料、提案書、報告書をページ番号付きで検索できるようにする。",
        "",
        "## 出力",
        "",
        "- Markdown/JSON: `data/processed/share/**/*.pdf.md`, `*.pdf.structure.json`",
        f"- 変換ログ: `{relative(TABLE_DIR / 'pdf_conversion_log.csv')}`",
        "",
        "## 処理結果",
        "",
        "凡例: `status` は処理状態、`count` は該当PDFファイル数を表します。",
        "",
        markdown_table(status_rows),
        "",
        "## 抽出総数",
        "",
        "凡例: `pdf_count` は成功PDF数、`page_count` は抽出ページ総数、`total_char_count` は抽出文字数の合計です。",
        "",
        markdown_table([{"pdf_count": len(ok_rows), "page_count": total_pages, "total_char_count": total_chars}]),
        "",
        "## エラー",
        "",
        "凡例: `raw_relative_path` は元ファイル、`error_type` と `error_message` は失敗理由を表します。",
        "",
        markdown_table(error_rows),
        "",
        "## 注意点",
        "",
        "- このEDAではPDFを画像レンダリングしてOCRする処理は行っていない。",
        "- 表や段組みの抽出順が崩れる可能性があるため、ページ番号をJSONに保持する。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(log_rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA016",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Convert PDF files into page-level Markdown and structure JSON.",
        "target_count": len(log_rows),
        "outputs": {
            "report": relative(REPORT_PATH),
            "conversion_log": relative(TABLE_DIR / "pdf_conversion_log.csv"),
            "processed_root": relative(PROCESSED_SHARE_DIR),
        },
        "repro_steps": ["uv run python EDA/EDA016/eda016.py"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    return argparse.ArgumentParser(description="Convert PDF files into preprocessing artifacts.").parse_args()


def main() -> None:
    """EDA016を実行する。"""
    parse_args()
    setup()
    log_rows = [process_file(path) for path in collect_targets()]
    save_csv(log_rows, TABLE_DIR / "pdf_conversion_log.csv")
    write_report(log_rows)
    write_manifest(log_rows)
    ok_count = sum(1 for row in log_rows if row["status"] == "ok")
    print(f"targets={len(log_rows)} ok={ok_count} errors={len(log_rows) - ok_count}")
    print(f"report={relative(REPORT_PATH)}")


if __name__ == "__main__":
    main()
