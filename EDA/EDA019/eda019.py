from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


# eda019.py は「プロジェクト直下 / EDA / EDA019 / eda019.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_SHARE_DIR = BASE_DIR / "data" / "raw" / "share"
RAW_DRIVE_DIR = RAW_SHARE_DIR / "share" / "共有ドライブ"
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda019_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda019.log"


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
    md_path = PROCESSED_SHARE_DIR / normalize_text(rel.as_posix())
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = md_path.with_suffix(md_path.suffix + ".structure.json")
    return md_path, json_path


def read_markdown(path: Path) -> tuple[str, str]:
    """複数エンコーディングを試してMarkdownを読む。"""
    last_error = ""
    for encoding in ["utf-8", "utf-8-sig", "cp932"]:
        try:
            return path.read_text(encoding=encoding), encoding
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
    raise RuntimeError(last_error)


def quality_flags(text: str) -> list[str]:
    """Markdown本文の簡易品質チェックを行う。"""
    flags = []
    if not text.strip():
        flags.append("empty")
    if "\ufffd" in text:
        flags.append("replacement_character")
    if "\x00" in text:
        flags.append("nul_character")
    if len(text.strip()) < 20:
        flags.append("very_short")
    if text.count("�") >= 3:
        flags.append("many_mojibake_markers")
    return flags


def process_markdown(path: Path) -> dict[str, Any]:
    """Markdownを品質確認し、そのままprocessedへ保存する。"""
    text, encoding = read_markdown(path)
    md_path, json_path = output_paths(path)
    md_path.write_text(text, encoding="utf-8")
    headings = re.findall(r"^(#{1,6})\s+(.+)$", text, flags=re.MULTILINE)
    links = re.findall(r"\[[^\]]+\]\([^)]+\)", text)
    flags = quality_flags(text)
    record = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "processed_markdown_path": relative(md_path),
        "processed_structure_path": relative(json_path),
        "file_name": path.name,
        "file_type": "md",
        "source_sha1": file_sha1(path),
        "encoding": encoding,
        "char_count": len(text),
        "line_count": len(text.splitlines()),
        "heading_count": len(headings),
        "link_count": len(links),
        "quality_flags": flags,
        "headings": [{"level": len(level), "text": heading.strip()} for level, heading in headings],
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def process_file(path: Path) -> dict[str, Any]:
    """1つのMarkdownを処理し、変換ログ行を返す。"""
    row = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "status": "",
        "error_type": "",
        "error_message": "",
        "processed_markdown_path": "",
        "processed_structure_path": "",
        "char_count": "",
        "line_count": "",
        "heading_count": "",
        "quality_flags": "",
    }
    try:
        record = process_markdown(path)
        row.update(
            {
                "status": "ok" if not record["quality_flags"] else "warning",
                "processed_markdown_path": record["processed_markdown_path"],
                "processed_structure_path": record["processed_structure_path"],
                "char_count": record["char_count"],
                "line_count": record["line_count"],
                "heading_count": record["heading_count"],
                "quality_flags": ",".join(record["quality_flags"]),
            }
        )
    except Exception as exc:  # noqa: BLE001
        row["status"] = "error"
        row["error_type"] = exc.__class__.__name__
        row["error_message"] = str(exc)[:1000]
        logging.exception("failed: %s", path)
    return row


def collect_targets() -> list[Path]:
    """共有ドライブ配下からMarkdownを集める。"""
    return sorted(RAW_DRIVE_DIR.rglob("*.md"), key=lambda p: normalize_text(p.as_posix()).lower())


def write_report(log_rows: list[dict[str, Any]]) -> None:
    """EDA019の処理結果をMarkdownレポートに保存する。"""
    status_rows = [
        {"status": status, "count": sum(1 for row in log_rows if row["status"] == status)}
        for status in sorted({row["status"] for row in log_rows})
    ]
    warning_rows = [row for row in log_rows if row["status"] == "warning"]
    error_rows = [row for row in log_rows if row["status"] == "error"]
    lines = [
        "# EDA019: Markdown品質確認と保存",
        "",
        "## 目的",
        "",
        "既存Markdownを再変換せず、文字化けや空ファイルなどを簡易確認したうえで、`data/processed/share` へ同じ内容で保存する。",
        "",
        "## 出力",
        "",
        "- Markdown: `data/processed/share/**/*.md`",
        "- 構造JSON: `data/processed/share/**/*.md.structure.json`",
        f"- 変換ログ: `{relative(TABLE_DIR / 'markdown_quality_log.csv')}`",
        "",
        "## 処理結果",
        "",
        "凡例: `status` は品質確認状態、`count` は該当Markdownファイル数を表します。",
        "",
        markdown_table(status_rows),
        "",
        "## 警告",
        "",
        "凡例: `quality_flags` は検出した品質警告、`char_count` は文字数、`heading_count` はMarkdown見出し数を表します。",
        "",
        markdown_table(warning_rows),
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
        "eda": "EDA019",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Validate existing Markdown files and copy them into processed share.",
        "target_count": len(log_rows),
        "outputs": {
            "report": relative(REPORT_PATH),
            "quality_log": relative(TABLE_DIR / "markdown_quality_log.csv"),
            "processed_root": relative(PROCESSED_SHARE_DIR),
        },
        "repro_steps": ["uv run python EDA/EDA019/eda019.py"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    return argparse.ArgumentParser(description="Validate and copy Markdown files into processed artifacts.").parse_args()


def main() -> None:
    """EDA019を実行する。"""
    parse_args()
    setup()
    log_rows = [process_file(path) for path in collect_targets()]
    save_csv(log_rows, TABLE_DIR / "markdown_quality_log.csv")
    write_report(log_rows)
    write_manifest(log_rows)
    ok_count = sum(1 for row in log_rows if row["status"] == "ok")
    warn_count = sum(1 for row in log_rows if row["status"] == "warning")
    err_count = sum(1 for row in log_rows if row["status"] == "error")
    print(f"targets={len(log_rows)} ok={ok_count} warnings={warn_count} errors={err_count}")
    print(f"report={relative(REPORT_PATH)}")


if __name__ == "__main__":
    main()
