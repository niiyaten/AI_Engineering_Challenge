from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


# eda017.py は「プロジェクト直下 / EDA / EDA017 / eda017.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_SHARE_DIR = BASE_DIR / "data" / "raw" / "share"
RAW_DRIVE_DIR = RAW_SHARE_DIR / "share" / "共有ドライブ"
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda017_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda017.log"


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


def read_python(path: Path) -> tuple[str, str]:
    """複数エンコーディングを試してPythonソースを読む。"""
    last_error = ""
    for encoding in ["utf-8", "utf-8-sig", "cp932"]:
        try:
            return path.read_text(encoding=encoding), encoding
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
    raise RuntimeError(last_error)


def dotted_name(node: ast.AST) -> str:
    """関数呼び出しなどを dotted name として表現する。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return dotted_name(node.func)
    return ""


def string_literal(value: ast.AST) -> str:
    """ASTノードから文字列リテラルだけを取り出す。"""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return ""


def imports_from_tree(tree: ast.AST) -> list[dict[str, Any]]:
    """import文を抽出する。"""
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                rows.append({"module": alias.name, "name": "", "asname": alias.asname or ""})
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                rows.append({"module": node.module or "", "name": alias.name, "asname": alias.asname or ""})
    return rows


def definitions_from_tree(tree: ast.AST) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """関数定義とクラス定義を抽出する。"""
    functions = []
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, "end_lineno", None),
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node) or "",
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
            )
        elif isinstance(node, ast.ClassDef):
            classes.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, "end_lineno", None),
                    "bases": [dotted_name(base) for base in node.bases],
                    "docstring": ast.get_docstring(node) or "",
                }
            )
    return functions, classes


def calls_and_files_from_tree(tree: ast.AST) -> tuple[list[str], list[dict[str, Any]]]:
    """関数呼び出しとファイル入出力らしき呼び出しを抽出する。"""
    calls = []
    file_ops = []
    file_related = [
        "open",
        "Path",
        "read_text",
        "write_text",
        "read_csv",
        "to_csv",
        "read_excel",
        "to_excel",
        "savefig",
        "dump",
        "dumps",
        "load",
        "loads",
        "joblib.dump",
        "joblib.load",
    ]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = dotted_name(node.func)
        if name:
            calls.append(name)
        args = [string_literal(arg) for arg in node.args if string_literal(arg)]
        keywords = {kw.arg: string_literal(kw.value) for kw in node.keywords if kw.arg and string_literal(kw.value)}
        if any(token in name for token in file_related) or args or keywords:
            file_ops.append(
                {
                    "lineno": getattr(node, "lineno", None),
                    "call": name,
                    "string_args": args,
                    "string_keywords": keywords,
                }
            )
    return sorted(set(calls)), file_ops


def process_python(path: Path) -> dict[str, Any]:
    """PythonファイルをMarkdownと構造JSONへ変換する。"""
    source, encoding = read_python(path)
    md_path, json_path = output_paths(path)
    tree = ast.parse(source)
    imports = imports_from_tree(tree)
    functions, classes = definitions_from_tree(tree)
    calls, file_ops = calls_and_files_from_tree(tree)
    lines = source.splitlines()
    record = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "processed_markdown_path": relative(md_path),
        "processed_structure_path": relative(json_path),
        "file_name": path.name,
        "file_type": "py",
        "source_sha1": file_sha1(path),
        "encoding": encoding,
        "line_count": len(lines),
        "char_count": len(source),
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "calls": calls,
        "file_operations": file_ops,
        "has_main_guard": "__name__" in source and "__main__" in source,
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# Python Source: {path.name}",
        "",
        "## Source",
        f"- raw_path: `{record['raw_relative_path']}`",
        f"- source_sha1: `{record['source_sha1']}`",
        f"- line_count: {record['line_count']}",
        f"- function_count: {len(functions)}",
        f"- class_count: {len(classes)}",
        f"- has_main_guard: {record['has_main_guard']}",
        "",
        "## Imports",
        "",
        markdown_table(imports, max_rows=80),
        "",
        "凡例: `module` はimport元、`name` はfrom importの対象、`asname` は別名を表します。",
        "",
        "## Functions",
        "",
        markdown_table(
            [{"name": f["name"], "lineno": f["lineno"], "args": ", ".join(f["args"]), "docstring": f["docstring"][:120]} for f in functions],
            max_rows=80,
        ),
        "",
        "凡例: `name` は関数名、`lineno` は開始行、`args` は引数、`docstring` は先頭説明を表します。",
        "",
        "## File Operations",
        "",
        markdown_table(file_ops, max_rows=80),
        "",
        "凡例: `call` は呼び出し名、`string_args` と `string_keywords` はファイルパス候補を含む文字列引数です。",
        "",
        "## Code",
        "",
        "```python",
        source,
        "```",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return record


def process_file(path: Path) -> dict[str, Any]:
    """1つのPythonファイルを処理し、変換ログ行を返す。"""
    row = {
        "raw_relative_path": normalize_text(path.relative_to(RAW_SHARE_DIR).as_posix()),
        "status": "",
        "error_type": "",
        "error_message": "",
        "processed_markdown_path": "",
        "processed_structure_path": "",
        "line_count": "",
        "function_count": "",
        "class_count": "",
        "file_operation_count": "",
    }
    try:
        record = process_python(path)
        row.update(
            {
                "status": "ok",
                "processed_markdown_path": record["processed_markdown_path"],
                "processed_structure_path": record["processed_structure_path"],
                "line_count": record["line_count"],
                "function_count": len(record["functions"]),
                "class_count": len(record["classes"]),
                "file_operation_count": len(record["file_operations"]),
            }
        )
    except Exception as exc:  # noqa: BLE001
        row["status"] = "error"
        row["error_type"] = exc.__class__.__name__
        row["error_message"] = str(exc)[:1000]
        logging.exception("failed: %s", path)
    return row


def collect_targets() -> list[Path]:
    """共有ドライブ配下からPythonファイルを集める。"""
    return sorted(RAW_DRIVE_DIR.rglob("*.py"), key=lambda p: normalize_text(p.as_posix()).lower())


def write_report(log_rows: list[dict[str, Any]]) -> None:
    """EDA017の処理結果をMarkdownレポートに保存する。"""
    ok_rows = [row for row in log_rows if row["status"] == "ok"]
    error_rows = [row for row in log_rows if row["status"] != "ok"]
    status_rows = [
        {"status": status, "count": sum(1 for row in log_rows if row["status"] == status)}
        for status in sorted({row["status"] for row in log_rows})
    ]
    totals = {
        "python_file_count": len(ok_rows),
        "line_count": sum(int(row["line_count"] or 0) for row in ok_rows),
        "function_count": sum(int(row["function_count"] or 0) for row in ok_rows),
        "class_count": sum(int(row["class_count"] or 0) for row in ok_rows),
        "file_operation_count": sum(int(row["file_operation_count"] or 0) for row in ok_rows),
    }
    lines = [
        "# EDA017: Pythonプログラム前処理",
        "",
        "## 目的",
        "",
        "Pythonプログラムを実行せずに静的解析し、分析手順、使用ライブラリ、関数、入出力候補を検索できるMarkdown/JSONへ変換する。",
        "",
        "## 出力",
        "",
        "- Markdown/JSON: `data/processed/share/**/*.py.md`, `*.py.structure.json`",
        f"- 変換ログ: `{relative(TABLE_DIR / 'python_conversion_log.csv')}`",
        "",
        "## 処理結果",
        "",
        "凡例: `status` は処理状態、`count` は該当Pythonファイル数を表します。",
        "",
        markdown_table(status_rows),
        "",
        "## 抽出総数",
        "",
        "凡例: 各項目は成功したPythonファイルから抽出した合計件数を表します。",
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
        "eda": "EDA017",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Convert Python programs into Markdown and AST-based structure JSON.",
        "target_count": len(log_rows),
        "outputs": {
            "report": relative(REPORT_PATH),
            "conversion_log": relative(TABLE_DIR / "python_conversion_log.csv"),
            "processed_root": relative(PROCESSED_SHARE_DIR),
        },
        "repro_steps": ["uv run python EDA/EDA017/eda017.py"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    return argparse.ArgumentParser(description="Convert Python files into preprocessing artifacts.").parse_args()


def main() -> None:
    """EDA017を実行する。"""
    parse_args()
    setup()
    log_rows = [process_file(path) for path in collect_targets()]
    save_csv(log_rows, TABLE_DIR / "python_conversion_log.csv")
    write_report(log_rows)
    write_manifest(log_rows)
    ok_count = sum(1 for row in log_rows if row["status"] == "ok")
    print(f"targets={len(log_rows)} ok={ok_count} errors={len(log_rows) - ok_count}")
    print(f"report={relative(REPORT_PATH)}")


if __name__ == "__main__":
    main()
