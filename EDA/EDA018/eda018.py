from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


# eda018.py は「プロジェクト直下 / EDA / EDA018 / eda018.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_SHARE_DIR = BASE_DIR / "data" / "raw" / "share"
RAW_DRIVE_DIR = RAW_SHARE_DIR / "share" / "共有ドライブ"
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda018_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda018.log"


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


def output_paths(raw_path: Path) -> tuple[Path, Path, Path]:
    """raw/shareからの相対構造を保ったMarkdown/JSON/assets出力先を返す。"""
    rel = raw_path.relative_to(RAW_SHARE_DIR)
    output_base = PROCESSED_SHARE_DIR / normalize_text(rel.as_posix())
    output_base.parent.mkdir(parents=True, exist_ok=True)
    md_path = output_base.with_suffix(output_base.suffix + ".md")
    json_path = output_base.with_suffix(output_base.suffix + ".structure.json")
    assets_dir = output_base.with_suffix(output_base.suffix + ".assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    return md_path, json_path, assets_dir


def source_text(source: Any) -> str:
    """Notebookのsource配列または文字列を1つの文字列へ変換する。"""
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return normalize_text(source)


def safe_ext(mime_type: str) -> str:
    """MIME typeから保存用拡張子を推定する。"""
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/svg+xml": ".svg",
        "text/html": ".html",
        "text/plain": ".txt",
    }
    return mapping.get(mime_type, ".bin")


def output_text_and_assets(outputs: list[dict[str, Any]], assets_dir: Path, cell_index: int) -> tuple[list[dict[str, Any]], list[str]]:
    """Notebookセル出力をテキスト化し、画像などはassetsに保存する。"""
    records = []
    markdown_lines = []
    for output_index, output in enumerate(outputs, start=1):
        output_type = output.get("output_type", "")
        record: dict[str, Any] = {"output_index": output_index, "output_type": output_type, "text": "", "assets": []}
        if "text" in output:
            text = source_text(output.get("text", ""))
            record["text"] = text
            markdown_lines.append(text)
        data = output.get("data") or {}
        for mime_type, value in data.items():
            if mime_type.startswith("image/"):
                raw = "".join(value) if isinstance(value, list) else str(value)
                ext = safe_ext(mime_type)
                asset_path = assets_dir / f"cell{cell_index:03d}_output{output_index:03d}{ext}"
                if mime_type == "image/svg+xml":
                    asset_path.write_text(raw, encoding="utf-8")
                else:
                    asset_path.write_bytes(base64.b64decode(raw))
                record["assets"].append({"mime_type": mime_type, "path": relative(asset_path), "bytes": asset_path.stat().st_size})
            elif mime_type in {"text/plain", "text/html"}:
                text = source_text(value)
                record["text"] = (record["text"] + "\n" + text).strip()
                markdown_lines.append(text)
        if output.get("ename") or output.get("evalue"):
            err = f"{output.get('ename', '')}: {output.get('evalue', '')}".strip(": ")
            record["text"] = (record["text"] + "\n" + err).strip()
            markdown_lines.append(err)
        records.append(record)
    return records, markdown_lines


def process_notebook(path: Path) -> dict[str, Any]:
    """Notebookをセル単位Markdownと構造JSONへ変換する。"""
    notebook = json.loads(path.read_text(encoding="utf-8"))
    md_path, json_path, assets_dir = output_paths(path)
    cells = []
    image_asset_count = 0
    output_count = 0
    md_lines = [
        f"# Notebook Markdown: {path.name}",
        "",
        "## Source",
        f"- raw_path: `{normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix())}`",
        f"- source_sha1: `{file_sha1(path)}`",
        f"- nbformat: {notebook.get('nbformat', '')}.{notebook.get('nbformat_minor', '')}",
        "",
        "## Cells",
    ]
    for cell_index, cell in enumerate(notebook.get("cells", []), start=1):
        cell_type = cell.get("cell_type", "")
        source = source_text(cell.get("source", ""))
        outputs, output_markdown = output_text_and_assets(cell.get("outputs", []) or [], assets_dir, cell_index)
        output_count += len(outputs)
        image_asset_count += sum(len(output.get("assets", [])) for output in outputs)
        execution_count = cell.get("execution_count")
        cells.append(
            {
                "cell_index": cell_index,
                "cell_type": cell_type,
                "execution_count": execution_count,
                "source": source,
                "source_line_count": len(source.splitlines()),
                "outputs": outputs,
            }
        )
        md_lines.extend(["", f"### Cell {cell_index}: {cell_type}", ""])
        if cell_type == "code":
            md_lines.extend(["```python", source.rstrip(), "```"])
        else:
            md_lines.append(source.rstrip())
        if output_markdown:
            md_lines.extend(["", "#### Output", ""])
            for text in output_markdown[:5]:
                md_lines.append("```text")
                md_lines.append(text.rstrip()[:3000])
                md_lines.append("```")

    record = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "processed_markdown_path": relative(md_path),
        "processed_structure_path": relative(json_path),
        "assets_dir": relative(assets_dir),
        "file_name": path.name,
        "file_type": "ipynb",
        "source_sha1": file_sha1(path),
        "nbformat": notebook.get("nbformat", ""),
        "nbformat_minor": notebook.get("nbformat_minor", ""),
        "cell_count": len(cells),
        "code_cell_count": sum(1 for cell in cells if cell["cell_type"] == "code"),
        "markdown_cell_count": sum(1 for cell in cells if cell["cell_type"] == "markdown"),
        "output_count": output_count,
        "image_asset_count": image_asset_count,
        "metadata": notebook.get("metadata", {}),
        "cells": cells,
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")
    return record


def process_file(path: Path) -> dict[str, Any]:
    """1つのNotebookを処理し、変換ログ行を返す。"""
    row = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "status": "",
        "error_type": "",
        "error_message": "",
        "processed_markdown_path": "",
        "processed_structure_path": "",
        "cell_count": "",
        "code_cell_count": "",
        "markdown_cell_count": "",
        "output_count": "",
        "image_asset_count": "",
    }
    try:
        record = process_notebook(path)
        row.update(
            {
                "status": "ok",
                "processed_markdown_path": record["processed_markdown_path"],
                "processed_structure_path": record["processed_structure_path"],
                "cell_count": record["cell_count"],
                "code_cell_count": record["code_cell_count"],
                "markdown_cell_count": record["markdown_cell_count"],
                "output_count": record["output_count"],
                "image_asset_count": record["image_asset_count"],
            }
        )
    except Exception as exc:  # noqa: BLE001
        row["status"] = "error"
        row["error_type"] = exc.__class__.__name__
        row["error_message"] = str(exc)[:1000]
        logging.exception("failed: %s", path)
    return row


def collect_targets() -> list[Path]:
    """共有ドライブ配下からNotebookを集める。"""
    return sorted(RAW_DRIVE_DIR.rglob("*.ipynb"), key=lambda p: normalize_text(p.as_posix()).lower())


def write_report(log_rows: list[dict[str, Any]]) -> None:
    """EDA018の処理結果をMarkdownレポートに保存する。"""
    ok_rows = [row for row in log_rows if row["status"] == "ok"]
    error_rows = [row for row in log_rows if row["status"] != "ok"]
    status_rows = [
        {"status": status, "count": sum(1 for row in log_rows if row["status"] == status)}
        for status in sorted({row["status"] for row in log_rows})
    ]
    totals = {
        "notebook_count": len(ok_rows),
        "cell_count": sum(int(row["cell_count"] or 0) for row in ok_rows),
        "code_cell_count": sum(int(row["code_cell_count"] or 0) for row in ok_rows),
        "markdown_cell_count": sum(int(row["markdown_cell_count"] or 0) for row in ok_rows),
        "output_count": sum(int(row["output_count"] or 0) for row in ok_rows),
        "image_asset_count": sum(int(row["image_asset_count"] or 0) for row in ok_rows),
    }
    lines = [
        "# EDA018: Notebook前処理",
        "",
        "## 目的",
        "",
        "Notebookを実行せずにセル単位Markdownと構造JSONへ変換し、分析手順、コード、出力、図を検索できるようにする。",
        "",
        "## 出力",
        "",
        "- Markdown/JSON: `data/processed/share/**/*.ipynb.md`, `*.ipynb.structure.json`",
        "- 出力画像: `data/processed/share/**/*.ipynb.assets/*`",
        f"- 変換ログ: `{relative(TABLE_DIR / 'notebook_conversion_log.csv')}`",
        "",
        "## 処理結果",
        "",
        "凡例: `status` は処理状態、`count` は該当Notebookファイル数を表します。",
        "",
        markdown_table(status_rows),
        "",
        "## 抽出総数",
        "",
        "凡例: 各項目は成功したNotebookから抽出した合計件数を表します。",
        "",
        markdown_table([totals]),
        "",
        "## エラー",
        "",
        "凡例: `raw_relative_path` は元ファイル、`error_type` と `error_message` は失敗理由を表します。",
        "",
        markdown_table(error_rows),
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(log_rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA018",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Convert Notebook files into cell-level Markdown and structure JSON.",
        "target_count": len(log_rows),
        "outputs": {
            "report": relative(REPORT_PATH),
            "conversion_log": relative(TABLE_DIR / "notebook_conversion_log.csv"),
            "processed_root": relative(PROCESSED_SHARE_DIR),
        },
        "repro_steps": ["uv run python EDA/EDA018/eda018.py"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    return argparse.ArgumentParser(description="Convert notebooks into preprocessing artifacts.").parse_args()


def main() -> None:
    """EDA018を実行する。"""
    parse_args()
    setup()
    log_rows = [process_file(path) for path in collect_targets()]
    save_csv(log_rows, TABLE_DIR / "notebook_conversion_log.csv")
    write_report(log_rows)
    write_manifest(log_rows)
    ok_count = sum(1 for row in log_rows if row["status"] == "ok")
    print(f"targets={len(log_rows)} ok={ok_count} errors={len(log_rows) - ok_count}")
    print(f"report={relative(REPORT_PATH)}")


if __name__ == "__main__":
    main()
