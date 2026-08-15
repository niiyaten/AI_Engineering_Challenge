from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import unicodedata
import warnings
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import matplotlib

# GUIがない環境でも画像保存できるようにする。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda002.py は「プロジェクト直下 / EDA / EDA002 / eda002.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
TEXT_DIR = OUTPUT_DIR / "texts"
REPORT_PATH = OUTPUT_DIR / "eda002_report.md"
LOG_PATH = OUTPUT_DIR / "eda002.log"

PROCESSED_TEXT_DIR = PROCESSED_DIR / "text_baseline"

# EDA002で対象にする、比較的そのまま読める形式。
TARGET_EXTENSIONS = {".md", ".csv", ".json", ".py", ".ipynb"}

# zipを展開済みの場合に優先して探す場所。
DATASET_SEARCH_BASES = [
    RAW_DIR,
    INTERIM_DIR,
    DATA_DIR,
    BASE_DIR,
]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
}

# CSVは巨大なtrain.csvを全文インデックス化すると重くなるため、初期値では概要＋一部サンプルにする。
DEFAULT_CSV_FULL_MAX_ROWS = 200
DEFAULT_CSV_FULL_MAX_CELLS = 20_000
DEFAULT_CSV_SAMPLE_ROWS = 20

DEFAULT_CHUNK_SIZE = 1_200
DEFAULT_CHUNK_OVERLAP = 200

# Notebookは実行ログや巨大な表出力を含みやすいため、初期RAGでは出力本文を制限する。
DEFAULT_IPYNB_MAX_OUTPUT_CHARS_PER_CELL = 2_000
DEFAULT_IPYNB_MAX_TOTAL_OUTPUT_CHARS = 50_000
DEFAULT_IPYNB_MAX_SOURCE_CHARS_PER_CELL = 20_000

TEXT_PREVIEW_LENGTH = 500


# =============================================================================
# 基本ユーティリティ
# =============================================================================


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_TEXT_DIR.mkdir(parents=True, exist_ok=True)

    logging.captureWarnings(True)
    warnings.simplefilter("always")
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


_HASH_U_PATTERN = re.compile(r"#U([0-9a-fA-F]{4})")


def decode_hash_u_text(text: str) -> str:
    """#U5171 のように展開された日本語パスを通常の日本語へ戻す。"""

    def repl(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return unicodedata.normalize("NFC", _HASH_U_PATTERN.sub(repl, str(text)))


def normalize_text(text: str) -> str:
    """日本語ファイル名の濁点揺れを抑えるため、NFCに正規化する。"""
    return decode_hash_u_text(str(text))


def safe_relative_to(path: Path, base: Path) -> str:
    """baseからの相対パスを返す。外側にある場合は絶対パスを返す。"""
    try:
        return normalize_text(path.relative_to(base).as_posix())
    except ValueError:
        return normalize_text(path.as_posix())


def is_excluded_path(path: Path) -> bool:
    """探索対象から除外すべきフォルダ配下かどうかを判定する。"""
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def iter_files(root: Path) -> Iterable[Path]:
    """root配下のファイルを再帰的に列挙する。"""
    for path in root.rglob("*"):
        if is_excluded_path(path):
            continue
        if path.is_file() and path.name != ".extracted":
            yield path


def iter_dirs(root: Path) -> Iterable[Path]:
    """root配下のフォルダを再帰的に列挙する。"""
    if not root.exists():
        return
    for path in root.rglob("*"):
        if is_excluded_path(path):
            continue
        if path.is_dir():
            yield path


def find_named_dirs(search_bases: list[Path], decoded_name: str) -> list[Path]:
    """指定した日本語フォルダ名に一致するフォルダを探す。"""
    hits: list[Path] = []
    seen: set[Path] = set()

    for base in search_bases:
        if not base.exists():
            continue
        for path in iter_dirs(base):
            if path in seen:
                continue
            if normalize_text(path.name) == decoded_name:
                hits.append(path)
                seen.add(path)
    return hits


def choose_best_path(paths: list[Path]) -> Path:
    """候補が複数ある場合、プロジェクト内のraw/interimを優先して選ぶ。"""
    if not paths:
        raise FileNotFoundError("候補パスが空です。")

    def score(path: Path) -> tuple[int, int]:
        text = path.as_posix()
        if "/data/raw/" in text:
            priority = 0
        elif "/data/interim/" in text:
            priority = 1
        else:
            priority = 2
        return (priority, len(path.parts))

    return sorted(paths, key=score)[0]


def find_drive_root() -> Path:
    """展開済みデータから `共有ドライブ` フォルダを探す。"""
    hits = find_named_dirs(DATASET_SEARCH_BASES, "共有ドライブ")
    if not hits:
        message = (
            "展開済みの `共有ドライブ` フォルダが見つかりません。\n"
            "share.zipを展開し、例えば `data/raw/share/共有ドライブ` または "
            "`data/interim/share/share/共有ドライブ` になるように配置してください。"
        )
        raise FileNotFoundError(message)
    drive_root = choose_best_path(hits)
    logging.info("Use drive_root: %s", drive_root)
    return drive_root


def classify_shared_drive_path(rel_path: str) -> dict[str, str]:
    """共有ドライブ内のパスから、案件名・大分類フォルダなどを推定する。"""
    parts = Path(rel_path).parts
    parts_nfc = [normalize_text(p) for p in parts]

    project_name = ""
    major_folder = ""
    area = ""

    if "共有ドライブ" in parts_nfc:
        idx = parts_nfc.index("共有ドライブ")
        if len(parts_nfc) > idx + 1:
            area = parts_nfc[idx + 1]

    if "プロジェクト" in parts_nfc:
        idx = parts_nfc.index("プロジェクト")
        if len(parts_nfc) > idx + 1:
            project_name = parts_nfc[idx + 1]
        if len(parts_nfc) > idx + 2:
            major_folder = parts_nfc[idx + 2]
    elif "社内管理" in parts_nfc:
        area = "社内管理"
        idx = parts_nfc.index("社内管理")
        if len(parts_nfc) > idx + 1:
            major_folder = parts_nfc[idx + 1]

    return {"area": area, "project_name": project_name, "major_folder": major_folder}


def make_stable_id(text: str, prefix: str) -> str:
    """パスやチャンクから、再実行しても変わりにくいIDを作る。"""
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def df_to_markdown(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """tabulateに依存しない簡易Markdown表を作る。"""
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "該当データなし"

    cols = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(map(str, cols)) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, row in df.iterrows():
        values = []
        for col in cols:
            value = row[col]
            text = "" if pd.isna(value) else str(value)
            text = text.replace("\n", " ").replace("|", "\\|")
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


# =============================================================================
# ファイル読み取り
# =============================================================================


def read_text_with_fallback(path: Path) -> tuple[str, str]:
    """複数エンコーディングを試してテキストファイルを読む。"""
    encodings = ["utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1"]
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            text = path.read_text(encoding=encoding)
            return text, encoding
        except UnicodeDecodeError as exc:
            last_error = exc
        except OSError as exc:
            last_error = exc
            break

    if last_error is not None:
        raise last_error
    raise UnicodeDecodeError("unknown", b"", 0, 1, "failed to read text")


def extract_markdown(path: Path) -> dict[str, Any]:
    """Markdownをそのまま本文として抽出する。"""
    text, encoding = read_text_with_fallback(path)
    heading_count = len(re.findall(r"(?m)^#{1,6}\s+", text))
    return {
        "text": text,
        "extraction_method": "markdown_raw_text",
        "encoding": encoding,
        "row_count": None,
        "column_count": None,
        "extra": {"heading_count": heading_count},
    }


def extract_plain_code(path: Path) -> dict[str, Any]:
    """Pythonコードをそのまま本文として抽出する。"""
    text, encoding = read_text_with_fallback(path)
    function_count = len(re.findall(r"(?m)^\s*def\s+\w+\s*\(", text))
    class_count = len(re.findall(r"(?m)^\s*class\s+\w+", text))
    import_count = len(re.findall(r"(?m)^\s*(import|from)\s+", text))
    return {
        "text": text,
        "extraction_method": "python_raw_text",
        "encoding": encoding,
        "row_count": None,
        "column_count": None,
        "extra": {
            "function_count": function_count,
            "class_count": class_count,
            "import_count": import_count,
        },
    }


def sniff_csv_separator(path: Path, encoding: str) -> str:
    """CSVの区切り文字を簡易推定する。"""
    sample = path.read_text(encoding=encoding, errors="replace")[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";", "|"])
        return dialect.delimiter
    except csv.Error:
        return ","


def series_to_short_text(series: pd.Series, max_items: int = 20) -> str:
    """列名や型などのSeriesを短い文字列にする。"""
    values = [str(v) for v in series.tolist()]
    shown = values[:max_items]
    suffix = "" if len(values) <= max_items else f" ... (+{len(values) - max_items})"
    return ", ".join(shown) + suffix


def extract_csv(
    path: Path,
    *,
    csv_full_max_rows: int,
    csv_full_max_cells: int,
    csv_sample_rows: int,
) -> dict[str, Any]:
    """CSVを読み、RAG向けのテキスト表現を作る。"""
    # まずエンコーディングだけ判定する。
    _, encoding = read_text_with_fallback(path)
    sep = sniff_csv_separator(path, encoding)

    df = pd.read_csv(path, encoding=encoding, sep=sep)
    row_count = len(df)
    column_count = len(df.columns)
    cell_count = row_count * max(column_count, 1)

    lines: list[str] = []
    lines.append(f"# CSVファイル: {normalize_text(path.name)}")
    lines.append("")
    lines.append(f"- 行数: {row_count}")
    lines.append(f"- 列数: {column_count}")
    lines.append(f"- 区切り文字: {repr(sep)}")
    lines.append(f"- 列名: {', '.join(map(str, df.columns.tolist()))}")
    lines.append("")
    lines.append("## dtypes")
    lines.append(df.dtypes.astype(str).rename("dtype").to_csv(header=True))
    lines.append("")

    null_counts = df.isna().sum()
    nonzero_nulls = null_counts[null_counts > 0].sort_values(ascending=False)
    lines.append("## 欠損数")
    if nonzero_nulls.empty:
        lines.append("欠損値なし、またはpandas読み込み上は欠損値なし。")
    else:
        lines.append(nonzero_nulls.rename("missing_count").to_csv(header=True))
    lines.append("")

    if row_count <= csv_full_max_rows and cell_count <= csv_full_max_cells:
        lines.append("## 全データ")
        lines.append(df.to_csv(index=False))
        csv_mode = "full"
    else:
        lines.append("## 先頭サンプル")
        lines.append(df.head(csv_sample_rows).to_csv(index=False))
        lines.append("")
        lines.append("## 末尾サンプル")
        lines.append(df.tail(csv_sample_rows).to_csv(index=False))
        csv_mode = "summary_sample"

        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            lines.append("")
            lines.append("## 数値列の要約統計")
            lines.append(numeric_df.describe().T.to_csv())

        object_cols = df.select_dtypes(include="object").columns.tolist()
        if object_cols:
            lines.append("")
            lines.append("## 文字列列の代表値")
            for col in object_cols[:20]:
                value_counts = df[col].astype(str).value_counts(dropna=False).head(10)
                lines.append(f"### {col}")
                lines.append(value_counts.rename("count").to_csv(header=True))

    text = "\n".join(lines)
    return {
        "text": text,
        "extraction_method": f"csv_{csv_mode}",
        "encoding": encoding,
        "row_count": row_count,
        "column_count": column_count,
        "extra": {
            "separator": sep,
            "cell_count": cell_count,
            "columns": df.columns.tolist(),
            "csv_mode": csv_mode,
        },
    }


def extract_json(path: Path) -> dict[str, Any]:
    """JSONを整形済みテキストとして抽出する。"""
    text_raw, encoding = read_text_with_fallback(path)
    obj = json.loads(text_raw)
    pretty = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)

    if isinstance(obj, dict):
        top_level_type = "dict"
        top_level_keys = list(obj.keys())
        item_count = len(obj)
    elif isinstance(obj, list):
        top_level_type = "list"
        top_level_keys = []
        item_count = len(obj)
    else:
        top_level_type = type(obj).__name__
        top_level_keys = []
        item_count = None

    lines = [
        f"# JSONファイル: {normalize_text(path.name)}",
        "",
        f"- top_level_type: {top_level_type}",
        f"- item_count: {item_count}",
    ]
    if top_level_keys:
        lines.append(f"- top_level_keys: {', '.join(map(str, top_level_keys))}")
    lines.extend(["", "## pretty_json", pretty])

    return {
        "text": "\n".join(lines),
        "extraction_method": "json_pretty_text",
        "encoding": encoding,
        "row_count": item_count,
        "column_count": None,
        "extra": {
            "top_level_type": top_level_type,
            "top_level_keys": top_level_keys,
        },
    }


_DATA_IMAGE_MARKDOWN_PATTERN = re.compile(
    r"!\[([^\]]*)\]\(data:image/[^;\s)]+;base64,[^)]+\)",
    flags=re.IGNORECASE | re.DOTALL,
)
_DATA_IMAGE_SRC_PATTERN = re.compile(
    r"src=(['\"])data:image/[^'\"]+\1",
    flags=re.IGNORECASE | re.DOTALL,
)


def sanitize_notebook_source(text: str, *, max_chars: int) -> tuple[str, dict[str, Any]]:
    """Notebookのsourceから、埋め込み画像Base64など検索ノイズになりやすい巨大要素を除去する。"""
    original_length = len(str(text))
    image_markdown_count = len(_DATA_IMAGE_MARKDOWN_PATTERN.findall(str(text)))
    image_src_count = len(_DATA_IMAGE_SRC_PATTERN.findall(str(text)))

    cleaned = _DATA_IMAGE_MARKDOWN_PATTERN.sub(
        "![embedded-image-omitted](data:image/...;base64 omitted)",
        str(text),
    )
    cleaned = _DATA_IMAGE_SRC_PATTERN.sub('src="data:image/...;base64 omitted"', cleaned)
    cleaned, was_truncated, _ = truncate_text(cleaned, max_chars)

    return cleaned, {
        "source_original_length": original_length,
        "source_cleaned_length": len(cleaned),
        "source_was_truncated": was_truncated,
        "embedded_markdown_image_count": image_markdown_count,
        "embedded_src_image_count": image_src_count,
    }


def truncate_text(text: str, max_chars: int) -> tuple[str, bool, int]:
    """長すぎるテキストを指定文字数で切り、切り詰め有無と元文字数を返す。"""
    text = str(text)
    original_length = len(text)
    if max_chars < 0 or original_length <= max_chars:
        return text, False, original_length
    suffix = f"\n...[truncated: original_length={original_length}, kept={max_chars}]"
    return text[:max_chars] + suffix, True, original_length


def output_to_text(output: dict[str, Any], *, max_chars: int) -> tuple[str, dict[str, Any]]:
    """Notebookセルのoutputsをテキスト化する。画像などの巨大データは除外し、長文は切り詰める。"""
    output_type = output.get("output_type", "")
    parts: list[str] = []
    skipped_mime_keys: list[str] = []

    if output_type == "stream":
        text = output.get("text", "")
        if isinstance(text, list):
            text = "".join(map(str, text))
        parts.append(str(text))
    elif output_type in {"execute_result", "display_data"}:
        data = output.get("data", {})
        # 検索に使えそうなテキスト系MIMEだけを採用する。
        for key in ["text/plain", "text/markdown", "text/html"]:
            if key in data:
                value = data[key]
                if isinstance(value, list):
                    value = "".join(map(str, value))
                parts.append(f"[{key}]\n{value}")
        skipped_mime_keys = [
            str(key)
            for key in data.keys()
            if key not in {"text/plain", "text/markdown", "text/html"}
        ]
    elif output_type == "error":
        ename = output.get("ename", "")
        evalue = output.get("evalue", "")
        traceback = output.get("traceback", [])
        parts.append(f"[error] {ename}: {evalue}")
        if traceback:
            parts.append("\n".join(map(str, traceback[:20])))

    raw_text = "\n".join(part for part in parts if part).strip()
    truncated_text, was_truncated, original_length = truncate_text(raw_text, max_chars)
    stats = {
        "output_type": output_type,
        "original_length": original_length,
        "included_length": len(truncated_text),
        "was_truncated": was_truncated,
        "skipped_mime_keys": skipped_mime_keys,
    }
    return truncated_text.strip(), stats

def extract_ipynb(
    path: Path,
    *,
    ipynb_max_output_chars_per_cell: int,
    ipynb_max_total_output_chars: int,
    ipynb_max_source_chars_per_cell: int,
) -> dict[str, Any]:
    """Jupyter NotebookのMarkdown・コード・テキスト出力を抽出する。"""
    text_raw, encoding = read_text_with_fallback(path)
    nb = json.loads(text_raw)
    cells = nb.get("cells", [])

    lines: list[str] = [f"# Notebook: {normalize_text(path.name)}", ""]
    cell_type_counts: Counter[str] = Counter()
    output_text_count = 0
    output_truncated_count = 0
    output_original_total_length = 0
    output_included_total_length = 0
    total_output_budget_used = 0
    skipped_output_count = 0
    skipped_mime_counter: Counter[str] = Counter()
    source_truncated_count = 0
    embedded_image_omitted_count = 0
    source_original_total_length = 0
    source_cleaned_total_length = 0

    for idx, cell in enumerate(cells):
        cell_type = str(cell.get("cell_type", "unknown"))
        cell_type_counts[cell_type] += 1
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(map(str, source))
        source, source_stats = sanitize_notebook_source(
            str(source).strip(),
            max_chars=ipynb_max_source_chars_per_cell,
        )
        source_truncated_count += int(bool(source_stats["source_was_truncated"]))
        embedded_image_omitted_count += int(source_stats["embedded_markdown_image_count"])
        embedded_image_omitted_count += int(source_stats["embedded_src_image_count"])
        source_original_total_length += int(source_stats["source_original_length"])
        source_cleaned_total_length += int(source_stats["source_cleaned_length"])

        lines.append(f"## cell_{idx:03d} [{cell_type}]")
        if source:
            lines.append(source)
        else:
            lines.append("[empty source]")

        outputs = cell.get("outputs", []) or []
        output_texts: list[str] = []
        for output in outputs:
            remaining_budget = ipynb_max_total_output_chars - total_output_budget_used
            if remaining_budget <= 0:
                skipped_output_count += 1
                continue

            max_chars = min(ipynb_max_output_chars_per_cell, remaining_budget)
            output_text, stats = output_to_text(output, max_chars=max_chars)
            for mime_key in stats.get("skipped_mime_keys", []):
                skipped_mime_counter[mime_key] += 1
            output_original_total_length += int(stats.get("original_length", 0))
            output_included_total_length += int(stats.get("included_length", 0))
            if stats.get("was_truncated"):
                output_truncated_count += 1
            if output_text:
                output_text_count += 1
                total_output_budget_used += len(output_text)
                output_texts.append(output_text)

        if output_texts:
            lines.append("")
            lines.append("### outputs_limited")
            lines.append("\n\n".join(output_texts))
        if skipped_output_count and total_output_budget_used >= ipynb_max_total_output_chars:
            # Notebook全体の出力上限に到達したことを本文にも残す。
            lines.append("")
            lines.append(
                f"[notebook output budget reached: max_total_output_chars={ipynb_max_total_output_chars}]"
            )
        lines.append("")

    return {
        "text": "\n".join(lines),
        "extraction_method": "ipynb_cells_text_limited_outputs",
        "encoding": encoding,
        "row_count": len(cells),
        "column_count": None,
        "extra": {
            "cell_count": len(cells),
            "cell_type_counts": dict(cell_type_counts),
            "output_text_count": output_text_count,
            "output_truncated_count": output_truncated_count,
            "output_skipped_count_by_total_budget": skipped_output_count,
            "output_original_total_length": output_original_total_length,
            "output_included_total_length": output_included_total_length,
            "ipynb_max_output_chars_per_cell": ipynb_max_output_chars_per_cell,
            "ipynb_max_total_output_chars": ipynb_max_total_output_chars,
            "ipynb_max_source_chars_per_cell": ipynb_max_source_chars_per_cell,
            "source_truncated_count": source_truncated_count,
            "embedded_image_omitted_count": embedded_image_omitted_count,
            "source_original_total_length": source_original_total_length,
            "source_cleaned_total_length": source_cleaned_total_length,
            "skipped_mime_counts": dict(skipped_mime_counter),
        },
    }

def extract_file(
    path: Path,
    *,
    csv_full_max_rows: int,
    csv_full_max_cells: int,
    csv_sample_rows: int,
    ipynb_max_output_chars_per_cell: int,
    ipynb_max_total_output_chars: int,
    ipynb_max_source_chars_per_cell: int,
) -> dict[str, Any]:
    """拡張子に応じてテキストを抽出する。"""
    ext = path.suffix.lower()
    if ext == ".md":
        return extract_markdown(path)
    if ext == ".py":
        return extract_plain_code(path)
    if ext == ".csv":
        return extract_csv(
            path,
            csv_full_max_rows=csv_full_max_rows,
            csv_full_max_cells=csv_full_max_cells,
            csv_sample_rows=csv_sample_rows,
        )
    if ext == ".json":
        return extract_json(path)
    if ext == ".ipynb":
        return extract_ipynb(
            path,
            ipynb_max_output_chars_per_cell=ipynb_max_output_chars_per_cell,
            ipynb_max_total_output_chars=ipynb_max_total_output_chars,
            ipynb_max_source_chars_per_cell=ipynb_max_source_chars_per_cell,
        )
    raise ValueError(f"対象外の拡張子です: {ext}")


# =============================================================================
# インベントリ・チャンク作成
# =============================================================================


def build_target_file_inventory(drive_root: Path) -> pd.DataFrame:
    """EDA002対象拡張子のファイル一覧を作る。"""
    rows: list[dict[str, Any]] = []
    for path in iter_files(drive_root):
        ext = path.suffix.lower()
        if ext not in TARGET_EXTENSIONS:
            continue

        rel_actual = path.relative_to(drive_root).as_posix()
        rel_display = normalize_text(rel_actual)
        info = classify_shared_drive_path(f"共有ドライブ/{rel_display}")
        size = path.stat().st_size
        document_id = make_stable_id(rel_display, "doc")

        rows.append(
            {
                "document_id": document_id,
                "relative_path": rel_display,
                "actual_relative_path": rel_actual,
                "file_name": normalize_text(path.name),
                "extension": ext,
                "size_bytes": size,
                "size_kb": round(size / 1024, 2),
                "area": info["area"],
                "project_name": info["project_name"],
                "major_folder": info["major_folder"],
                "source_path": safe_relative_to(path, BASE_DIR),
                "absolute_path": path.as_posix(),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise FileNotFoundError(f"対象拡張子のファイルが見つかりません: {TARGET_EXTENSIONS}")
    return df.sort_values(["extension", "area", "project_name", "relative_path"]).reset_index(drop=True)


def normalize_extracted_text(text: str) -> str:
    """抽出テキストを検索しやすいように軽く整える。"""
    text = unicodedata.normalize("NFC", str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 連続空行を少し詰める。表やコードの改行は残す。
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def make_document_text(metadata: dict[str, Any], extracted_text: str) -> str:
    """本文の先頭に検索用メタ情報を付ける。"""
    header_lines = [
        f"# source_path: {metadata['relative_path']}",
        f"# file_name: {metadata['file_name']}",
        f"# extension: {metadata['extension']}",
        f"# area: {metadata.get('area', '')}",
        f"# project_name: {metadata.get('project_name', '')}",
        f"# major_folder: {metadata.get('major_folder', '')}",
        "",
    ]
    return "\n".join(header_lines) + extracted_text


def split_text_into_chunks(text: str, *, chunk_size: int, chunk_overlap: int) -> list[dict[str, Any]]:
    """文字数ベースでテキストをチャンク化する。"""
    if chunk_size <= 0:
        raise ValueError("chunk_sizeは1以上にしてください。")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlapは0以上にしてください。")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlapはchunk_sizeより小さくしてください。")

    text = text.strip()
    if not text:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # 途中で切れる場合は、近い改行位置で切る。
        if end < text_length:
            window = text[start:end]
            newline_pos = max(window.rfind("\n\n"), window.rfind("\n"))
            if newline_pos >= int(chunk_size * 0.6):
                end = start + newline_pos

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"chunk_index": len(chunks), "start_char": start, "end_char": end, "text": chunk_text})

        if end >= text_length:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """JSON Lines形式で保存する。"""
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_extraction(
    inventory_df: pd.DataFrame,
    *,
    csv_full_max_rows: int,
    csv_full_max_cells: int,
    csv_sample_rows: int,
    ipynb_max_output_chars_per_cell: int,
    ipynb_max_total_output_chars: int,
    ipynb_max_source_chars_per_cell: int,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """対象ファイルを抽出し、文書JSONLとチャンクJSONLを作る。"""
    documents: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for _, meta_row in inventory_df.iterrows():
        metadata = meta_row.to_dict()
        path = Path(str(metadata["absolute_path"]))
        document_id = str(metadata["document_id"])

        try:
            extracted = extract_file(
                path,
                csv_full_max_rows=csv_full_max_rows,
                csv_full_max_cells=csv_full_max_cells,
                csv_sample_rows=csv_sample_rows,
                ipynb_max_output_chars_per_cell=ipynb_max_output_chars_per_cell,
                ipynb_max_total_output_chars=ipynb_max_total_output_chars,
                ipynb_max_source_chars_per_cell=ipynb_max_source_chars_per_cell,
            )
            extracted_text = normalize_extracted_text(str(extracted["text"]))
            document_text = make_document_text(metadata, extracted_text)
            text_hash = hashlib.sha1(document_text.encode("utf-8", errors="ignore")).hexdigest()

            doc_record = {
                "document_id": document_id,
                "relative_path": metadata["relative_path"],
                "file_name": metadata["file_name"],
                "extension": metadata["extension"],
                "area": metadata["area"],
                "project_name": metadata["project_name"],
                "major_folder": metadata["major_folder"],
                "source_path": metadata["source_path"],
                "size_bytes": int(metadata["size_bytes"]),
                "extraction_method": extracted["extraction_method"],
                "encoding": extracted["encoding"],
                "row_count": extracted["row_count"],
                "column_count": extracted["column_count"],
                "text_length": len(document_text),
                "line_count": document_text.count("\n") + 1 if document_text else 0,
                "text_hash_sha1": text_hash,
                "extra": extracted.get("extra", {}),
                "text": document_text,
            }
            documents.append(doc_record)

            file_chunks = split_text_into_chunks(
                document_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            for chunk in file_chunks:
                chunk_id = f"{document_id}_chunk_{chunk['chunk_index']:04d}"
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "chunk_index": chunk["chunk_index"],
                        "relative_path": metadata["relative_path"],
                        "file_name": metadata["file_name"],
                        "extension": metadata["extension"],
                        "area": metadata["area"],
                        "project_name": metadata["project_name"],
                        "major_folder": metadata["major_folder"],
                        "start_char": chunk["start_char"],
                        "end_char": chunk["end_char"],
                        "text_length": len(chunk["text"]),
                        "text": chunk["text"],
                    }
                )

        except Exception as exc:  # noqa: BLE001 - EDAでは失敗ログを残して次へ進む。
            logging.exception("Failed to extract: %s", path)
            errors.append(
                {
                    "document_id": document_id,
                    "relative_path": metadata["relative_path"],
                    "file_name": metadata["file_name"],
                    "extension": metadata["extension"],
                    "source_path": metadata["source_path"],
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )

    documents_path = TEXT_DIR / "extracted_documents.jsonl"
    chunks_path = TEXT_DIR / "text_chunks.jsonl"
    processed_documents_path = PROCESSED_TEXT_DIR / "extracted_documents.jsonl"
    processed_chunks_path = PROCESSED_TEXT_DIR / "text_chunks.jsonl"

    write_jsonl(documents_path, documents)
    write_jsonl(chunks_path, chunks)
    write_jsonl(processed_documents_path, documents)
    write_jsonl(processed_chunks_path, chunks)

    doc_df = pd.DataFrame(
        [
            {k: v for k, v in doc.items() if k not in {"text", "extra"}}
            | {
                "text_preview": str(doc["text"])[:TEXT_PREVIEW_LENGTH].replace("\n", " "),
                "extra_json": json.dumps(doc.get("extra", {}), ensure_ascii=False),
            }
            for doc in documents
        ]
    )
    chunk_df = pd.DataFrame([{k: v for k, v in chunk.items() if k != "text"} for chunk in chunks])
    error_df = pd.DataFrame(errors)

    return doc_df, chunk_df, error_df


# =============================================================================
# 集計・レポート
# =============================================================================


def make_summary_tables(
    inventory_df: pd.DataFrame,
    doc_df: pd.DataFrame,
    chunk_df: pd.DataFrame,
    error_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """EDA002の確認用集計表を作る。"""
    target_extension_counts = (
        inventory_df.groupby("extension", dropna=False)
        .agg(file_count=("relative_path", "count"), total_size_kb=("size_kb", "sum"))
        .reset_index()
        .sort_values("file_count", ascending=False)
    )

    target_project_counts = (
        inventory_df.groupby(["area", "project_name", "major_folder"], dropna=False)
        .agg(file_count=("relative_path", "count"), total_size_kb=("size_kb", "sum"))
        .reset_index()
        .sort_values(["area", "project_name", "file_count"], ascending=[True, True, False])
    )

    if not doc_df.empty:
        extraction_summary = (
            doc_df.groupby(["extension", "extraction_method"], dropna=False)
            .agg(
                extracted_files=("relative_path", "count"),
                total_text_length=("text_length", "sum"),
                mean_text_length=("text_length", "mean"),
                total_line_count=("line_count", "sum"),
            )
            .reset_index()
            .sort_values(["extension", "extracted_files"], ascending=[True, False])
        )
        extraction_summary["mean_text_length"] = extraction_summary["mean_text_length"].round(1)
    else:
        extraction_summary = pd.DataFrame()

    if not chunk_df.empty:
        chunk_summary = (
            chunk_df.groupby("extension", dropna=False)
            .agg(
                chunk_count=("chunk_id", "count"),
                mean_chunk_length=("text_length", "mean"),
                max_chunk_length=("text_length", "max"),
            )
            .reset_index()
            .sort_values("chunk_count", ascending=False)
        )
        chunk_summary["mean_chunk_length"] = chunk_summary["mean_chunk_length"].round(1)
    else:
        chunk_summary = pd.DataFrame()

    extraction_status = target_extension_counts.copy()
    if not doc_df.empty:
        extracted_by_ext = doc_df.groupby("extension").size().rename("success_count").reset_index()
    else:
        extracted_by_ext = pd.DataFrame(columns=["extension", "success_count"])
    if not error_df.empty:
        error_by_ext = error_df.groupby("extension").size().rename("error_count").reset_index()
    else:
        error_by_ext = pd.DataFrame(columns=["extension", "error_count"])
    extraction_status = extraction_status.merge(extracted_by_ext, on="extension", how="left")
    extraction_status = extraction_status.merge(error_by_ext, on="extension", how="left")
    extraction_status[["success_count", "error_count"]] = extraction_status[["success_count", "error_count"]].fillna(0).astype(int)
    extraction_status["success_rate"] = (extraction_status["success_count"] / extraction_status["file_count"]).round(3)

    # 確認しやすいよう、各拡張子からテキストが長いものを数件出す。
    sample_documents = pd.DataFrame()
    if not doc_df.empty:
        sample_documents = (
            doc_df.sort_values(["extension", "text_length"], ascending=[True, False])
            .groupby("extension", group_keys=False)
            .head(5)[
                [
                    "document_id",
                    "extension",
                    "relative_path",
                    "extraction_method",
                    "text_length",
                    "text_preview",
                ]
            ]
            .reset_index(drop=True)
        )

    file_text_length_ranking = pd.DataFrame()
    if not doc_df.empty:
        file_text_length_ranking = (
            doc_df[
                [
                    "document_id",
                    "extension",
                    "relative_path",
                    "extraction_method",
                    "size_bytes",
                    "text_length",
                    "line_count",
                ]
            ]
            .sort_values("text_length", ascending=False)
            .reset_index(drop=True)
        )
        total_text_length = file_text_length_ranking["text_length"].sum()
        if total_text_length > 0:
            file_text_length_ranking["text_length_share"] = (
                file_text_length_ranking["text_length"] / total_text_length
            ).round(4)

    file_chunk_count_ranking = pd.DataFrame()
    if not chunk_df.empty:
        file_chunk_count_ranking = (
            chunk_df.groupby(["document_id", "extension", "relative_path"], dropna=False)
            .agg(
                chunk_count=("chunk_id", "count"),
                mean_chunk_length=("text_length", "mean"),
                max_chunk_length=("text_length", "max"),
            )
            .reset_index()
            .sort_values("chunk_count", ascending=False)
        )
        file_chunk_count_ranking["mean_chunk_length"] = file_chunk_count_ranking["mean_chunk_length"].round(1)
        total_chunk_count = file_chunk_count_ranking["chunk_count"].sum()
        if total_chunk_count > 0:
            file_chunk_count_ranking["chunk_share"] = (
                file_chunk_count_ranking["chunk_count"] / total_chunk_count
            ).round(4)

    return {
        "target_file_inventory": inventory_df.drop(columns=["absolute_path"]),
        "target_extension_counts": target_extension_counts,
        "target_project_counts": target_project_counts,
        "extraction_status": extraction_status,
        "extraction_summary": extraction_summary,
        "extracted_documents_preview": doc_df,
        "chunk_summary": chunk_summary,
        "text_chunks_preview": chunk_df.head(5000),
        "extraction_errors": error_df,
        "sample_documents": sample_documents,
        "file_text_length_ranking": file_text_length_ranking,
        "file_chunk_count_ranking": file_chunk_count_ranking,
    }


def save_tables(tables: dict[str, pd.DataFrame]) -> None:
    """集計表をCSVで保存する。"""
    for name, df in tables.items():
        df.to_csv(TABLE_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")


def plot_extension_counts(df: pd.DataFrame) -> None:
    """対象拡張子の件数を棒グラフで保存する。"""
    if df.empty:
        return
    plot_df = df.sort_values("file_count", ascending=True)
    plt.figure(figsize=(8, 4))
    plt.barh(plot_df["extension"], plot_df["file_count"])
    plt.title("EDA002 target file counts by extension")
    plt.xlabel("file_count")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "01_target_extension_counts.png", dpi=150)
    plt.close()


def plot_text_lengths(doc_df: pd.DataFrame) -> None:
    """抽出テキスト長の分布を保存する。"""
    if doc_df.empty:
        return
    plt.figure(figsize=(9, 5))
    for ext, sub in doc_df.groupby("extension"):
        plt.hist(sub["text_length"], bins=30, alpha=0.5, label=ext)
    plt.title("Extracted text length distribution")
    plt.xlabel("text_length")
    plt.ylabel("file_count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "02_text_length_distribution.png", dpi=150)
    plt.close()


def plot_chunk_counts(chunk_summary: pd.DataFrame) -> None:
    """拡張子別チャンク件数を保存する。"""
    if chunk_summary.empty:
        return
    plot_df = chunk_summary.sort_values("chunk_count", ascending=True)
    plt.figure(figsize=(8, 4))
    plt.barh(plot_df["extension"], plot_df["chunk_count"])
    plt.title("Text chunk counts by extension")
    plt.xlabel("chunk_count")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "03_chunk_counts_by_extension.png", dpi=150)
    plt.close()


def plot_file_text_length_top(file_text_length_ranking: pd.DataFrame) -> None:
    """抽出テキスト量が多いファイル上位を保存する。"""
    if file_text_length_ranking.empty:
        return
    plot_df = file_text_length_ranking.head(15).copy()
    plot_df["label"] = plot_df["relative_path"].astype(str).str[-60:]
    plot_df = plot_df.sort_values("text_length", ascending=True)
    plt.figure(figsize=(10, 6))
    plt.barh(plot_df["label"], plot_df["text_length"])
    plt.title("Top extracted text length files")
    plt.xlabel("text_length")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_top_text_length_files.png", dpi=150)
    plt.close()


def plot_file_chunk_count_top(file_chunk_count_ranking: pd.DataFrame) -> None:
    """チャンク数が多いファイル上位を保存する。"""
    if file_chunk_count_ranking.empty:
        return
    plot_df = file_chunk_count_ranking.head(15).copy()
    plot_df["label"] = plot_df["relative_path"].astype(str).str[-60:]
    plot_df = plot_df.sort_values("chunk_count", ascending=True)
    plt.figure(figsize=(10, 6))
    plt.barh(plot_df["label"], plot_df["chunk_count"])
    plt.title("Top chunk count files")
    plt.xlabel("chunk_count")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "05_top_chunk_count_files.png", dpi=150)
    plt.close()


def make_report(
    drive_root: Path,
    tables: dict[str, pd.DataFrame],
    *,
    chunk_size: int,
    chunk_overlap: int,
    ipynb_max_output_chars_per_cell: int,
    ipynb_max_total_output_chars: int,
    ipynb_max_source_chars_per_cell: int,
) -> None:
    """EDA002のMarkdownレポートを作る。"""
    inventory_df = tables["target_file_inventory"]
    extraction_status = tables["extraction_status"]
    extraction_summary = tables["extraction_summary"]
    chunk_summary = tables["chunk_summary"]
    error_df = tables["extraction_errors"]
    sample_documents = tables["sample_documents"]
    file_text_length_ranking = tables["file_text_length_ranking"]
    file_chunk_count_ranking = tables["file_chunk_count_ranking"]

    total_files = len(inventory_df)
    success_count = int(extraction_status["success_count"].sum()) if not extraction_status.empty else 0
    error_count = int(extraction_status["error_count"].sum()) if not extraction_status.empty else 0
    total_chunks = int(chunk_summary["chunk_count"].sum()) if not chunk_summary.empty else 0
    total_text_length = int(extraction_summary["total_text_length"].sum()) if not extraction_summary.empty else 0

    lines: list[str] = []
    lines.append("# EDA002: 直接読めるテキスト系ファイルの抽出ベースライン")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append("### 背景")
    lines.append("")
    lines.append(
        "本コンペティションでは、架空企業の共有ドライブに蓄積された案件資料を対象に、"
        "社内から寄せられる質問へ根拠に基づいて回答するRAGシステムの構築が求められる。"
        "対象資料は単一形式ではなく、文書、表、コード、Notebook、画像を含む資料などが混在しているため、"
        "最初から全ファイル形式を同じ方法で処理すると、抽出品質や検索ノイズの問題を切り分けにくい。"
    )
    lines.append("")
    lines.append(
        "EDA001では、共有ドライブ全体のファイル構成、案件フォルダ、拡張子の分布、質問データの概要を整理し、"
        "本コンペで扱うデータの全体像を確認した。その結果、RAGの初期インデックスを作るうえでは、"
        "まず機械的に本文を取り出しやすいファイル形式から処理を始めるのが妥当と判断した。"
    )
    lines.append("")
    lines.append("### 本EDAの目的")
    lines.append("")
    lines.append(
        "EDA002では、比較的そのまま読み取りやすい `.md`, `.csv`, `.json`, `.py`, `.ipynb` を対象に、"
        "テキスト抽出のベースラインを作成する。これらはMarkdown文書、表形式データ、設定ファイル、"
        "分析コード、分析Notebookに相当し、案件の背景、分析条件、特徴量、評価指標、出力結果などを含む可能性が高い。"
    )
    lines.append("")
    lines.append(
        "本EDAの主目的は、対象ファイルをRAGの初期検索対象として利用できる状態にすることである。"
        "具体的には、各ファイルから本文を抽出し、ファイルパス・案件名・大分類フォルダなどのメタ情報を付与したうえで、"
        "後続の検索処理で扱いやすいチャンク単位に分割する。"
    )
    lines.append("")
    lines.append("### 確認観点")
    lines.append("")
    lines.append(
        "本EDAでは、単に抽出処理が成功したかだけでなく、抽出後のテキストがRAGに投入しやすい品質になっているかを確認する。"
        "確認観点は、抽出失敗の有無、抽出文字数、行数、チャンク数、ファイル形式ごとの偏り、"
        "ファイル別のテキスト量ランキング、抽出本文サンプルの妥当性である。"
    )
    lines.append("")
    lines.append(
        "特に `.ipynb` は、実行ログ、表出力、画像のBase64埋め込みによって本文が過剰に肥大化しやすい。"
        "また、大容量CSVは全文を単純にチャンク化すると検索インデックスを圧迫し、必要な行や列を探しにくくなる。"
        "そのため、本EDAではNotebook出力の上限設定、埋め込み画像Base64の除外、CSVの概要抽出を行い、"
        "初期検索に使いやすい軽量なテキスト表現を作る。"
    )
    lines.append("")
    lines.append("### 後続工程での位置づけ")
    lines.append("")
    lines.append(
        "ここで作成する `extracted_documents.jsonl` と `text_chunks.jsonl` は、後続の検索ベースライン、"
        "質問に対する候補文書検索、ファイル形式別の追加抽出方針検討に利用する。"
        "EDA002の段階では回答生成までは行わず、RAGの土台となるテキスト化処理の安定性と偏りを確認する。"
    )
    lines.append("")
    lines.append("## 入力データ")
    lines.append("")
    lines.append(f"- 共有ドライブ: `{safe_relative_to(drive_root, BASE_DIR)}`")
    lines.append(f"- 対象拡張子: `{', '.join(sorted(TARGET_EXTENSIONS))}`")
    lines.append(f"- チャンクサイズ: {chunk_size} 文字")
    lines.append(f"- チャンクオーバーラップ: {chunk_overlap} 文字")
    lines.append(f"- Notebook出力上限: 1出力あたり {ipynb_max_output_chars_per_cell} 文字")
    lines.append(f"- Notebook出力上限: 1Notebookあたり {ipynb_max_total_output_chars} 文字")
    lines.append(f"- Notebook source上限: 1セルあたり {ipynb_max_source_chars_per_cell} 文字")
    lines.append("")
    lines.append("## 出力ファイル")
    lines.append("")
    lines.append("- `EDA/EDA002/texts/extracted_documents.jsonl`: 1ファイル1レコードの抽出本文")
    lines.append("- `EDA/EDA002/texts/text_chunks.jsonl`: 検索インデックス投入用のチャンク")
    lines.append("- `data/processed/text_baseline/extracted_documents.jsonl`: 後続処理向けコピー")
    lines.append("- `data/processed/text_baseline/text_chunks.jsonl`: 後続処理向けコピー")
    lines.append("- `EDA/EDA002/tables/*.csv`: 棚卸し・成功率・プレビュー・エラー・ファイル別ランキング")
    lines.append("")
    lines.append("## 全体サマリ")
    lines.append("")
    lines.append(f"- 対象ファイル数: {total_files}")
    lines.append(f"- 抽出成功: {success_count}")
    lines.append(f"- 抽出失敗: {error_count}")
    lines.append(f"- 作成チャンク数: {total_chunks}")
    lines.append(f"- 抽出テキスト総文字数: {total_text_length}")
    lines.append("")
    lines.append("## 拡張子別の抽出状況")
    lines.append("")
    lines.append(df_to_markdown(extraction_status))
    lines.append("")
    lines.append("## 抽出方法別サマリ")
    lines.append("")
    lines.append(df_to_markdown(extraction_summary))
    lines.append("")
    lines.append("## チャンク数サマリ")
    lines.append("")
    lines.append(df_to_markdown(chunk_summary))
    lines.append("")
    lines.append("## ファイル別テキスト量ランキング")
    lines.append("")
    lines.append(df_to_markdown(file_text_length_ranking.head(20)))
    lines.append("")
    lines.append("## ファイル別チャンク数ランキング")
    lines.append("")
    lines.append(df_to_markdown(file_chunk_count_ranking.head(20)))
    lines.append("")
    lines.append("## 抽出本文サンプル")
    lines.append("")
    lines.append(df_to_markdown(sample_documents, max_rows=15))
    lines.append("")
    lines.append("## 考察")
    lines.append("")
    lines.append(
        "対象とした5種類の拡張子については、抽出失敗の有無、抽出テキスト量、チャンク数を確認することで、"
        "初期RAGインデックスへの投入可否を判断できる状態になった。Markdown、CSV、JSON、Pythonコード、Notebookは"
        "少なくとも機械的なテキスト化が可能であり、後続の検索ベースラインに利用できる見込みがある。"
    )
    lines.append("")
    lines.append(
        "一方で、Notebookは実行出力や長大なログ、Markdownセル内の埋め込み画像Base64を含みやすく、"
        "抽出テキスト量とチャンク数が過剰になりやすい。そのため、本版ではNotebookの出力本文に上限を設け、"
        "埋め込み画像Base64をプレースホルダ化し、Markdownセル・コードセル・限定されたテキスト出力を中心に抽出する方針とした。"
        "これにより、検索結果がNotebook由来のノイズに偏るリスクを下げる。"
    )
    lines.append("")
    lines.append(
        "CSVについては、大容量ファイルを全文テキスト化せず、列名、型、欠損、先頭・末尾サンプル、要約統計を抽出している。"
        "これは初期検索には有効だが、特定条件の行抽出や集計が必要な質問では、テキスト検索だけでなくpandas等による"
        "直接検索・集計処理を組み合わせる必要がある。"
    )
    lines.append("")
    lines.append(
        "以上より、EDA002はテキスト抽出ベースラインとしては有効である。ただし、検索精度を確認する段階では、"
        "ファイル別テキスト量ランキングとチャンク数ランキングを参照し、特定ファイルが検索結果を支配していないかを継続的に確認する。"
    )
    lines.append("")
    lines.append("## 抽出失敗")
    lines.append("")
    if error_df.empty:
        lines.append("抽出失敗はありません。")
    else:
        lines.append(df_to_markdown(error_df, max_rows=30))
    lines.append("")
    lines.append("## 次にやること")
    lines.append("")
    lines.append("1. `text_chunks.jsonl` を使い、キーワード検索またはベクトル検索の最小構成を作る。")
    lines.append("2. valid質問30件について、今回のテキスト抽出だけで答えられる問題を切り分ける。")
    lines.append("3. Notebook由来チャンクがまだ多い場合は、Notebook出力上限やチャンク設計をさらに調整する。")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")




def validate_report_artifact() -> None:
    """生成したMarkdown成果物に必要な章が含まれるか確認する。"""
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    required_sections = [
        "## 目的・背景",
        "### 背景",
        "### 本EDAの目的",
        "### 確認観点",
        "### 後続工程での位置づけ",
        "## 全体サマリ",
        "## ファイル別テキスト量ランキング",
        "## ファイル別チャンク数ランキング",
        "## 考察",
    ]
    missing = [section for section in required_sections if section not in report_text]
    if missing:
        raise RuntimeError(f"eda002_report.mdに必要な章が不足しています: {missing}")

# =============================================================================
# main
# =============================================================================


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA002: text baseline extraction for simple file formats.")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--csv-full-max-rows", type=int, default=DEFAULT_CSV_FULL_MAX_ROWS)
    parser.add_argument("--csv-full-max-cells", type=int, default=DEFAULT_CSV_FULL_MAX_CELLS)
    parser.add_argument("--csv-sample-rows", type=int, default=DEFAULT_CSV_SAMPLE_ROWS)
    parser.add_argument("--ipynb-max-output-chars-per-cell", type=int, default=DEFAULT_IPYNB_MAX_OUTPUT_CHARS_PER_CELL)
    parser.add_argument("--ipynb-max-total-output-chars", type=int, default=DEFAULT_IPYNB_MAX_TOTAL_OUTPUT_CHARS)
    parser.add_argument("--ipynb-max-source-chars-per-cell", type=int, default=DEFAULT_IPYNB_MAX_SOURCE_CHARS_PER_CELL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()

    drive_root = find_drive_root()
    inventory_df = build_target_file_inventory(drive_root)

    doc_df, chunk_df, error_df = run_extraction(
        inventory_df,
        csv_full_max_rows=args.csv_full_max_rows,
        csv_full_max_cells=args.csv_full_max_cells,
        csv_sample_rows=args.csv_sample_rows,
        ipynb_max_output_chars_per_cell=args.ipynb_max_output_chars_per_cell,
        ipynb_max_total_output_chars=args.ipynb_max_total_output_chars,
        ipynb_max_source_chars_per_cell=args.ipynb_max_source_chars_per_cell,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    tables = make_summary_tables(inventory_df, doc_df, chunk_df, error_df)
    save_tables(tables)
    plot_extension_counts(tables["target_extension_counts"])
    plot_text_lengths(doc_df)
    plot_chunk_counts(tables["chunk_summary"])
    plot_file_text_length_top(tables["file_text_length_ranking"])
    plot_file_chunk_count_top(tables["file_chunk_count_ranking"])
    make_report(
        drive_root,
        tables,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        ipynb_max_output_chars_per_cell=args.ipynb_max_output_chars_per_cell,
        ipynb_max_total_output_chars=args.ipynb_max_total_output_chars,
        ipynb_max_source_chars_per_cell=args.ipynb_max_source_chars_per_cell,
    )
    validate_report_artifact()

    print(f"EDA002 finished: {REPORT_PATH}")
    print(f"tables: {TABLE_DIR}")
    print(f"texts: {TEXT_DIR}")
    print(f"processed copy: {PROCESSED_TEXT_DIR}")


if __name__ == "__main__":
    main()
