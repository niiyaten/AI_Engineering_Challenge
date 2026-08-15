from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# =============================================================================
# パス設定
# =============================================================================

# eda013.py は「プロジェクト直下 / EDA / EDA013 / eda013.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
EDA011_DIR = BASE_DIR / "EDA" / "EDA011"
EDA012_DIR = BASE_DIR / "EDA" / "EDA012"

RAW_SHARE_ROOT = BASE_DIR / "data" / "raw" / "share" / "share" / "共有ドライブ"
PROCESSED_SHARE_DIR = BASE_DIR / "data" / "processed" / "share"
EMBEDDING_DIR = BASE_DIR / "data" / "processed" / "embedding"
EMBEDDING_RECORDS_PATH = EMBEDDING_DIR / "embedding_records.jsonl"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
PROMPT_DIR = OUTPUT_DIR / "prompts"
REPORT_PATH = OUTPUT_DIR / "eda013_report.md"
LOG_PATH = OUTPUT_DIR / "eda013.log"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

DOCX_CONVERSION_LOG_PATH = EDA012_DIR / "tables" / "docx_markdown_conversion_log.csv"
IMAGE_FILE_INVENTORY_PATH = EDA011_DIR / "tables" / "image_file_inventory.csv"
IMAGE_QUESTION_INVENTORY_PATH = EDA011_DIR / "tables" / "image_question_inventory.csv"
API_KEY_FILE = BASE_DIR / ".apikey"

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# 動的なモデル一覧取得に失敗した場合の候補。実在可否はAPI呼び出し結果で判定する。
FALLBACK_VISION_MODEL_CANDIDATES = [
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen2.5-vl-32b-instruct:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "google/gemini-2.0-flash-exp:free",
]


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    if PROMPT_DIR.exists():
        shutil.rmtree(PROMPT_DIR)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    EMBEDDING_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def relative(path: Path) -> str:
    """レポートやJSONに保存するパスをプロジェクト相対にする。"""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_text(value: Any) -> str:
    """Windows上で起きやすい濁点表記揺れをNFCへ寄せる。"""
    return unicodedata.normalize("NFC", "" if value is None else str(value))


def file_sha1(path: Path) -> str:
    """入力ファイルの追跡用にSHA1を計算する。"""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Excelでも開きやすいようにUTF-8 BOM付きCSVを保存する。"""
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns = list(dict.fromkeys(col for row in rows for col in row.keys()))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def compact_whitespace(text: Any) -> str:
    """検索用テキストに不要な空白を詰める。"""
    value = normalize_text(text)
    value = re.sub(r"\r\n|\r", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def load_api_key() -> tuple[str, str]:
    """OpenRouter APIキーを環境変数、なければプロジェクト直下の.apikeyから読む。"""
    env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env_key:
        return env_key, "env:OPENROUTER_API_KEY"
    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key, ".apikey"
    return "", ""


def load_json(path: Path) -> dict[str, Any]:
    """UTF-8 JSONを辞書として読む。"""
    return json.loads(path.read_text(encoding="utf-8"))


def has_style(block: dict[str, Any], style_name: str) -> bool:
    """段落内runの書式フラグを確認する。"""
    return any(bool(run.get(style_name)) for run in block.get("runs", []))


def style_values(block: dict[str, Any], key: str) -> list[str]:
    """色やハイライトなど、値を持つ書式を重複除去して返す。"""
    values = []
    for run in block.get("runs", []):
        value = normalize_text(run.get(key, "")).strip()
        if value and value not in values:
            values.append(value)
    return values


def heading_level(style: str) -> int | None:
    """WordのHeadingスタイルから階層を取り出す。"""
    match = re.search(r"Heading\s+(\d+)", normalize_text(style), flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def update_heading_path(heading_path: list[str], block: dict[str, Any]) -> list[str]:
    """現在の見出し階層を、段落スタイルに応じて更新する。"""
    level = heading_level(block.get("style", ""))
    if level is None:
        return heading_path
    text = compact_whitespace(block.get("text", ""))
    if not text:
        return heading_path
    next_path = heading_path[: max(level - 1, 0)]
    next_path.append(text)
    return next_path


def make_record_id(prefix: str, source_path: str, extra: str) -> str:
    """同じ入力から同じIDが作られるように短いハッシュIDを作る。"""
    raw = f"{prefix}|{source_path}|{extra}".encode("utf-8")
    digest = hashlib.sha1(raw).hexdigest()[:16]
    return f"{prefix}_{digest}"


def base_record(
    record_type: str,
    source_path: str,
    text_for_embedding: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """embedding_records.jsonlに共通する基本形を作る。"""
    return {
        "record_id": make_record_id(record_type, source_path, json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
        "record_type": record_type,
        "source_path": source_path,
        "text_for_embedding": compact_whitespace(text_for_embedding),
        "metadata": metadata,
    }


def build_doc_records(max_chars: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """EDA012のWord構造JSONから、本文・表・メタデータのembedding候補を作る。"""
    records: list[dict[str, Any]] = []
    ignored_rows: list[dict[str, Any]] = []

    conversion_df = pd.read_csv(DOCX_CONVERSION_LOG_PATH)
    for _, row in conversion_df.iterrows():
        status = normalize_text(row.get("status", ""))
        if status != "ok":
            ignored_rows.append(
                {
                    "raw_relative_path": normalize_text(row.get("raw_relative_path", "")),
                    "reason": "docx_conversion_failed_or_keyed",
                    "error_type": normalize_text(row.get("error_type", "")),
                    "error_message": normalize_text(row.get("error_message", "")),
                }
            )
            continue

        json_path = BASE_DIR / normalize_text(row.get("processed_structure_path", ""))
        if not json_path.exists():
            ignored_rows.append(
                {
                    "raw_relative_path": normalize_text(row.get("raw_relative_path", "")),
                    "reason": "structure_json_missing",
                    "error_type": "",
                    "error_message": relative(json_path),
                }
            )
            continue

        doc = load_json(json_path)
        source_path = normalize_text(doc.get("raw_relative_path", row.get("raw_relative_path", "")))
        markdown_path = normalize_text(doc.get("processed_markdown_path", ""))
        blocks = doc.get("blocks", [])

        metadata = {
            "file_type": "docx",
            "file_name": normalize_text(doc.get("file_name", "")),
            "processed_markdown_path": markdown_path,
            "structure_json_path": relative(json_path),
            "source_sha1": normalize_text(doc.get("source_sha1", "")),
            "paragraph_count": int(doc.get("paragraph_count", 0)),
            "table_count": int(doc.get("table_count", 0)),
            "image_count": int(doc.get("image_count", 0)),
        }
        meta_text = "\n".join(
            [
                f"ファイル名: {metadata['file_name']}",
                f"元ファイル: {source_path}",
                f"段落数: {metadata['paragraph_count']}",
                f"表数: {metadata['table_count']}",
                f"画像数: {metadata['image_count']}",
            ]
        )
        records.append(base_record("metadata", source_path, meta_text, metadata))

        heading_path: list[str] = []
        chunk_blocks: list[dict[str, Any]] = []
        chunk_texts: list[str] = []

        def flush_chunk() -> None:
            """現在ためている段落を1つの本文チャンクとして保存する。"""
            nonlocal chunk_blocks, chunk_texts
            text = compact_whitespace("\n".join(chunk_texts))
            if not text:
                chunk_blocks = []
                chunk_texts = []
                return
            first = chunk_blocks[0]
            last = chunk_blocks[-1]
            style_meta = {
                "has_bold": any(has_style(block, "bold") for block in chunk_blocks),
                "has_italic": any(has_style(block, "italic") for block in chunk_blocks),
                "has_underline": any(has_style(block, "underline") for block in chunk_blocks),
                "font_colors": sorted({color for block in chunk_blocks for color in style_values(block, "font_color")}),
                "highlights": sorted({mark for block in chunk_blocks for mark in style_values(block, "highlight")}),
            }
            records.append(
                base_record(
                    "paragraph",
                    source_path,
                    text,
                    {
                        "file_type": "docx",
                        "processed_markdown_path": markdown_path,
                        "structure_json_path": relative(json_path),
                        "block_start": first.get("block_index"),
                        "block_end": last.get("block_index"),
                        "heading_path": " > ".join(heading_path),
                        **style_meta,
                    },
                )
            )
            chunk_blocks = []
            chunk_texts = []

        for block in blocks:
            block_type = normalize_text(block.get("block_type", ""))
            if block_type == "paragraph":
                next_heading_path = update_heading_path(heading_path, block)
                block_text = compact_whitespace(block.get("markdown") or block.get("text", ""))
                if not block_text:
                    heading_path = next_heading_path
                    continue
                is_heading = next_heading_path != heading_path
                if is_heading:
                    flush_chunk()
                    heading_path = next_heading_path
                if sum(len(t) for t in chunk_texts) + len(block_text) > max_chars:
                    flush_chunk()
                chunk_blocks.append(block)
                chunk_texts.append(block_text)
            elif block_type == "table":
                flush_chunk()
                table_text = compact_whitespace(block.get("markdown", ""))
                if not table_text:
                    continue
                records.append(
                    base_record(
                        "table",
                        source_path,
                        table_text,
                        {
                            "file_type": "docx",
                            "processed_markdown_path": markdown_path,
                            "structure_json_path": relative(json_path),
                            "block_index": block.get("block_index"),
                            "heading_path": " > ".join(heading_path),
                            "row_count": block.get("row_count", 0),
                            "column_count": block.get("column_count", 0),
                        },
                    )
                )
        flush_chunk()
    return records, ignored_rows


def read_image_question_hints() -> list[dict[str, Any]]:
    """画像・グラフに関係する質問を、回答を除いて読む。"""
    if not IMAGE_QUESTION_INVENTORY_PATH.exists():
        return []
    rows = []
    for _, row in pd.read_csv(IMAGE_QUESTION_INVENTORY_PATH).iterrows():
        rows.append(
            {
                "split": normalize_text(row.get("split", "")),
                "index": int(row.get("index", -1)),
                "question": normalize_text(row.get("question", "")),
            }
        )
    return rows


def image_priority(path: Path, question_hints: list[dict[str, Any]]) -> tuple[int, str]:
    """画像質問に近そうな画像を先に処理するための優先度を決める。"""
    text = normalize_text(path.as_posix()).lower()
    file_name = normalize_text(path.name).lower()
    if file_name == "figure_06.png" or "figure_06" in text:
        return (0, text)
    for hint in question_hints:
        question = normalize_text(hint["question"]).lower()
        if file_name and file_name in question:
            return (1, text)
        if "基礎分析" in question and "基礎分析" in text:
            return (2, text)
    if "figures" in text:
        return (3, text)
    return (9, text)


def collect_raw_image_paths(question_hints: list[dict[str, Any]]) -> list[Path]:
    """raw共有ドライブ配下の画像ファイルを集め、優先度順に並べる。"""
    # CSV化したパスは濁点表記の違いでWindows実ファイルと一致しない場合があるため、
    # 実際のファイル走査を正として使う。
    paths = [
        path
        for path in RAW_SHARE_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    ]
    return sorted(paths, key=lambda p: image_priority(p, question_hints))


def collect_embedded_image_paths() -> list[Path]:
    """EDA012でWordから抽出済みの画像アセットを集める。"""
    paths = []
    for path in PROCESSED_SHARE_DIR.rglob("*"):
        if path.is_file() and ".assets" in path.as_posix():
            paths.append(path)
    return sorted(paths, key=lambda p: normalize_text(p.as_posix()).lower())


def image_to_data_url(path: Path) -> tuple[str, str]:
    """OpenRouterへ渡せるdata URLを作る。"""
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}", mime_type


def fetch_free_vision_models(timeout: int) -> tuple[list[str], str]:
    """OpenRouterのモデル一覧から、無料の画像入力対応モデル候補を取得する。"""
    try:
        with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logging.warning("model list fetch failed: %s", exc)
        return FALLBACK_VISION_MODEL_CANDIDATES, f"fallback: {exc}"

    models = []
    for model in data.get("data", []):
        model_id = normalize_text(model.get("id", ""))
        lowered_id = model_id.lower()
        # 画像を受け取れても、安全性判定・音声・画像生成など検索用説明に向かないモデルは除外する。
        if any(token in lowered_id for token in ["safety", "moderation", "lyria", "clip", "image-preview"]):
            continue
        architecture = model.get("architecture") or {}
        input_modalities = [normalize_text(item).lower() for item in architecture.get("input_modalities", [])]
        pricing = model.get("pricing") or {}
        prompt_price = normalize_text(pricing.get("prompt", ""))
        is_free_id = model_id.endswith(":free")
        is_free_price = prompt_price in {"", "0", "0.0", "0.000000"}
        if "image" in input_modalities and (is_free_id or is_free_price):
            models.append(model_id)

    unique_models = list(dict.fromkeys(FALLBACK_VISION_MODEL_CANDIDATES + models))
    return unique_models, "openrouter_models_api"


def is_non_informative_vision_response(content: str) -> bool:
    """安全性判定だけなど、画像説明として使えない応答を判定する。"""
    text = compact_whitespace(content).lower()
    if not text:
        return True
    if len(text) <= 80 and ("safety:" in text or text in {"safe", "user safety: safe"}):
        return True
    return False


def build_image_prompt(path: Path, related_questions: list[dict[str, Any]]) -> str:
    """画像説明モデルへ渡すプロンプトを作る。valid/testの正解は渡さない。"""
    question_lines = []
    for hint in related_questions[:3]:
        question_lines.append(f"- {hint['split']} index={hint['index']}: {hint['question']}")
    question_text = "\n".join(question_lines) if question_lines else "- なし"
    return (
        "この画像を、RAG検索用のテキストに変換してください。\n"
        "日本語で、画像内の文字、グラフのタイトル、軸名、凡例、読み取れる数値、傾向を具体的に書いてください。\n"
        "不明な値は推測せず、不明と書いてください。\n"
        "出力はJSONだけにしてください。キーは ocr_text, chart_description, extracted_values, search_summary, confidence_notes です。\n\n"
        f"画像ファイル名: {path.name}\n"
        f"関連しそうな質問:\n{question_text}"
    )


def related_questions_for_image(path: Path, question_hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ファイル名やパスから、関連しそうな画像質問を紐づける。"""
    related = []
    text = normalize_text(path.as_posix()).lower()
    file_name = normalize_text(path.name).lower()
    for hint in question_hints:
        question = normalize_text(hint["question"]).lower()
        if file_name in question or "figure_06" in file_name and "figure_06" in question:
            related.append(hint)
        elif "基礎分析" in question and "基礎分析" in text:
            related.append(hint)
    return related


def call_openrouter_image_to_text(
    api_key: str,
    model: str,
    image_path: Path,
    related_questions: list[dict[str, Any]],
    timeout: int,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    """OpenRouterのVision対応チャットモデルで画像を説明する。"""
    data_url, mime_type = image_to_data_url(image_path)
    prompt = build_image_prompt(image_path, related_questions)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_CHAT_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost/signate-agentic-rag",
            "X-Title": "SIGNATE Agentic RAG EDA013",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTPError {exc.code}: {detail[:1000]}") from exc
    elapsed = time.time() - started
    message = data["choices"][0]["message"]
    content = normalize_text(message.get("content", "")).strip()
    meta = {
        "elapsed_sec": round(elapsed, 3),
        "usage": data.get("usage", {}),
        "finish_reason": data["choices"][0].get("finish_reason", ""),
        "response_id": data.get("id", ""),
        "mime_type": mime_type,
    }
    return content, meta


def parse_model_json(content: str) -> dict[str, Any]:
    """モデルが返したJSONを取り出す。崩れている場合は全文を要約欄として扱う。"""
    cleaned = content.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    return {
        "ocr_text": "",
        "chart_description": cleaned,
        "extracted_values": [],
        "search_summary": cleaned,
        "confidence_notes": "JSONとしては解析できなかったため、応答全文を説明として保存した。",
    }


def image_record_text(parsed: dict[str, Any], path: Path) -> str:
    """画像説明JSONからembedding用テキストを組み立てる。"""
    parts = [
        f"画像ファイル: {path.name}",
        f"OCR: {parsed.get('ocr_text', '')}",
        f"画像説明: {parsed.get('chart_description', '')}",
        f"読み取り値: {json.dumps(parsed.get('extracted_values', []), ensure_ascii=False)}",
        f"検索用要約: {parsed.get('search_summary', '')}",
        f"注意: {parsed.get('confidence_notes', '')}",
    ]
    return "\n".join(part for part in parts if compact_whitespace(part))


def build_image_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """raw画像と抽出画像をレコード化し、指定件数だけOpenRouterで説明文を付ける。"""
    records: list[dict[str, Any]] = []
    call_rows: list[dict[str, Any]] = []
    question_hints = read_image_question_hints()
    api_key, api_key_source = load_api_key()
    if args.model:
        model_candidates = [args.model]
        model_source = "cli_arg"
    else:
        model_candidates, model_source = fetch_free_vision_models(args.timeout)

    raw_paths = collect_raw_image_paths(question_hints)
    embedded_paths = collect_embedded_image_paths()
    image_items = [("raw_image", path) for path in raw_paths] + [("embedded_docx_image", path) for path in embedded_paths]

    processed_calls = 0
    selected_model = ""
    for image_kind, path in image_items:
        source_path = relative(path)
        suffix = path.suffix.lower()
        related = related_questions_for_image(path, question_hints)
        metadata: dict[str, Any] = {
            "file_type": "image",
            "image_kind": image_kind,
            "image_path": source_path,
            "image_suffix": suffix,
            "size_bytes": path.stat().st_size,
            "sha1": file_sha1(path),
            "related_questions": related,
            "image_to_text_status": "not_started",
            "image_to_text_model": "",
            "image_to_text_model_source": model_source,
            "api_key_source": api_key_source if api_key else "",
            "ocr_text": "",
            "chart_description": "",
            "extracted_values": [],
            "confidence_notes": "",
        }

        should_call = (
            bool(api_key)
            and not args.dry_run
            and suffix in SUPPORTED_IMAGE_SUFFIXES
            and processed_calls < args.image_call_limit
        )
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            metadata["image_to_text_status"] = "skipped_unsupported_format"
            metadata["confidence_notes"] = f"{suffix} は現在のOpenRouter data URL送信対象外。"
        elif not api_key:
            metadata["image_to_text_status"] = "skipped_no_api_key"
        elif args.dry_run:
            metadata["image_to_text_status"] = "dry_run"
        elif processed_calls >= args.image_call_limit:
            metadata["image_to_text_status"] = "skipped_limit"

        text_for_embedding = f"画像ファイル: {path.name}\nパス: {source_path}"
        error_message = ""
        if should_call:
            processed_calls += 1
            last_error = ""
            prompt_path = PROMPT_DIR / f"image_{processed_calls:03d}_{path.stem}.prompt.txt"
            prompt_path.write_text(build_image_prompt(path, related), encoding="utf-8")
            for model in model_candidates[: args.model_try_limit]:
                started = time.time()
                try:
                    content, meta = call_openrouter_image_to_text(
                        api_key=api_key,
                        model=model,
                        image_path=path,
                        related_questions=related,
                        timeout=args.timeout,
                        max_tokens=args.max_tokens,
                    )
                    if is_non_informative_vision_response(content):
                        raise RuntimeError(f"non_informative_vision_response: {content[:200]}")
                    parsed = parse_model_json(content)
                    metadata.update(
                        {
                            "image_to_text_status": "ok",
                            "image_to_text_model": model,
                            "ocr_text": normalize_text(parsed.get("ocr_text", "")),
                            "chart_description": normalize_text(parsed.get("chart_description", "")),
                            "extracted_values": parsed.get("extracted_values", []),
                            "confidence_notes": normalize_text(parsed.get("confidence_notes", "")),
                            "openrouter_usage": meta.get("usage", {}),
                            "openrouter_finish_reason": meta.get("finish_reason", ""),
                            "openrouter_response_id": meta.get("response_id", ""),
                        }
                    )
                    selected_model = selected_model or model
                    text_for_embedding = image_record_text(parsed, path)
                    call_rows.append(
                        {
                            "image_path": source_path,
                            "status": "ok",
                            "model": model,
                            "elapsed_sec": meta.get("elapsed_sec", round(time.time() - started, 3)),
                            "error_message": "",
                            "content_preview": compact_whitespace(content)[:500],
                        }
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    call_rows.append(
                        {
                            "image_path": source_path,
                            "status": "error",
                            "model": model,
                            "elapsed_sec": round(time.time() - started, 3),
                            "error_message": last_error[:1000],
                            "content_preview": "",
                        }
                    )
            if metadata["image_to_text_status"] != "ok":
                error_message = last_error
                metadata["image_to_text_status"] = "failed"
                metadata["image_to_text_error"] = error_message[:1000]

        records.append(base_record("image", source_path, text_for_embedding, metadata))

    model_rows = [
        {
            "rank": i + 1,
            "model": model,
            "source": model_source,
            "selected_first_success": model == selected_model,
        }
        for i, model in enumerate(model_candidates[: max(args.model_try_limit, 10)])
    ]
    return records, call_rows, model_rows


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """1行1レコードのJSONLとして保存する。"""
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """record_type別の件数と空テキスト件数を集計する。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["record_type"]].append(record)
    rows = []
    for record_type, items in sorted(grouped.items()):
        rows.append(
            {
                "record_type": record_type,
                "record_count": len(items),
                "empty_text_count": sum(1 for item in items if not compact_whitespace(item["text_for_embedding"])),
                "short_text_count_lt_20": sum(1 for item in items if len(compact_whitespace(item["text_for_embedding"])) < 20),
                "avg_text_length": round(sum(len(item["text_for_embedding"]) for item in items) / max(len(items), 1), 1),
            }
        )
    return rows


def summarize_files(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ファイル別のレコード件数を集計する。"""
    counter = Counter(record["source_path"] for record in records)
    return [{"source_path": path, "record_count": count} for path, count in counter.most_common()]


def markdown_table(rows: list[dict[str, Any]], max_rows: int = 20) -> str:
    """追加依存なしでレポート用Markdown表を作る。"""
    if not rows:
        return "該当データはありません。"
    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:max_rows]:
        values = []
        for col in columns:
            text = normalize_text(row.get(col, ""))
            text = text.replace("\n", " ").replace("|", "\\|")
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(
    records: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    ignored_rows: list[dict[str, Any]],
    call_rows: list[dict[str, Any]],
    model_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    """EDA013の結果をMarkdownレポートにまとめる。"""
    image_records = [record for record in records if record["record_type"] == "image"]
    ok_images = [record for record in image_records if record["metadata"].get("image_to_text_status") == "ok"]
    image_status_counter = Counter(record["metadata"].get("image_to_text_status", "") for record in image_records)
    representative_rows = []
    for record in ok_images[:5]:
        representative_rows.append(
            {
                "image_path": record["metadata"].get("image_path", ""),
                "model": record["metadata"].get("image_to_text_model", ""),
                "text_preview": compact_whitespace(record["text_for_embedding"])[:240],
            }
        )

    lines = [
        "# EDA013: embedding用標準レコード作成",
        "",
        "## 目的",
        "",
        "EDA012で作成したMarkdown/構造JSONと、EDA011で棚卸しした画像を、BM25・ベクトル検索・LLM入力で共通利用できるJSONLへ正規化した。",
        "画像はバイナリをそのままembeddingせず、OpenRouterの無料Vision候補で説明文へ変換し、検索用テキストとして保存する方針を検証した。",
        "",
        "## 出力",
        "",
        f"- embedding_records: `{relative(EMBEDDING_RECORDS_PATH)}`",
        f"- record_summary: `{relative(TABLE_DIR / 'embedding_record_summary.csv')}`",
        f"- file_summary: `{relative(TABLE_DIR / 'embedding_file_summary.csv')}`",
        f"- image_to_text_calls: `{relative(TABLE_DIR / 'image_to_text_calls.csv')}`",
        f"- ignored_files: `{relative(TABLE_DIR / 'ignored_files.csv')}`",
        "",
        "## 主要結果",
        "",
        f"- 総レコード数: {len(records)}",
        f"- 画像レコード数: {len(image_records)}",
        f"- OpenRouter画像toテキスト成功数: {len(ok_images)}",
        f"- 鍵付き・変換失敗として無視したファイル数: {len(ignored_rows)}",
        f"- 画像API呼び出し上限: {args.image_call_limit}",
        "",
        "## record_type別集計",
        "",
        "凡例: `record_type` はembedding候補の種類、`record_count` は件数、`empty_text_count` は検索テキストが空の件数、`short_text_count_lt_20` は20文字未満の件数、`avg_text_length` は平均文字数。",
        "",
        markdown_table(summary_rows),
        "",
        "## 画像処理ステータス",
        "",
        "凡例: `status` は画像toテキスト処理状態、`count` は画像レコード件数。",
        "",
        markdown_table([{"status": key, "count": value} for key, value in sorted(image_status_counter.items())]),
        "",
        "## OpenRouter無料Visionモデル候補",
        "",
        "凡例: `rank` は候補順、`model` はOpenRouterモデルID、`source` は候補取得元、`selected_first_success` は最初に成功したモデルかを表す。",
        "",
        markdown_table(model_rows, max_rows=20),
        "",
        "## 画像toテキスト代表例",
        "",
        "凡例: `image_path` は処理対象画像、`model` は成功モデル、`text_preview` はembeddingに入れる説明文の先頭部分。",
        "",
        markdown_table(representative_rows, max_rows=5),
        "",
        "## 無視したファイル",
        "",
        "凡例: `raw_relative_path` は元ファイル、`reason` は無視理由、`error_type` と `error_message` は変換時のエラー情報。",
        "",
        markdown_table(ignored_rows, max_rows=20),
        "",
        "## 注意点",
        "",
        "- このEDAではembedding自体は実行していない。次段階で `text_for_embedding` をモデルに渡す。",
        "- JSON構造は再現・根拠追跡用であり、JSON全文をそのままembeddingする前提ではない。",
        "- OpenRouter APIキーは `.apikey` または環境変数から読み、キー本文はログ・成果物に保存しない。",
        "- 外部APIの無料枠・レート制限により、画像toテキストは一部失敗する可能性がある。その場合もレコードに失敗理由を残す。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(args: argparse.Namespace, records: list[dict[str, Any]]) -> None:
    """提出用コード化に備え、入力・出力・パラメータを追跡できるmanifestを保存する。"""
    inputs = [
        DOCX_CONVERSION_LOG_PATH,
        IMAGE_FILE_INVENTORY_PATH,
        IMAGE_QUESTION_INVENTORY_PATH,
    ]
    manifest = {
        "eda": "EDA013",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Build canonical embedding input records from processed Markdown/JSON and image-to-text outputs.",
        "parameters": {
            "max_chars": args.max_chars,
            "image_call_limit": args.image_call_limit,
            "model": args.model,
            "model_try_limit": args.model_try_limit,
            "max_tokens": args.max_tokens,
            "dry_run": args.dry_run,
        },
        "inputs": [
            {"path": relative(path), "sha1": file_sha1(path), "bytes": path.stat().st_size}
            for path in inputs
            if path.exists()
        ],
        "outputs": {
            "embedding_records": relative(EMBEDDING_RECORDS_PATH),
            "report": relative(REPORT_PATH),
            "tables": relative(TABLE_DIR),
        },
        "record_count": len(records),
        "secret_handling": "API key is read from OPENROUTER_API_KEY or project-local .apikey and is not written to logs.",
        "repro_steps": [
            "uv run python EDA/EDA012/eda012.py --clean-output",
            (
                "uv run python EDA/EDA013/eda013.py "
                f"--image-call-limit {args.image_call_limit} "
                f"--model {args.model or '<auto-free-vision-model>'} "
                f"--model-try-limit {args.model_try_limit} "
                f"--max-tokens {args.max_tokens}"
            ),
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Build embedding-ready records and image-to-text records.")
    parser.add_argument("--max-chars", type=int, default=1200, help="1つの本文チャンクに入れる最大文字数")
    parser.add_argument("--image-call-limit", type=int, default=4, help="OpenRouterへ送る画像の最大件数")
    parser.add_argument("--model", default="", help="固定で試すOpenRouter VisionモデルID")
    parser.add_argument("--model-try-limit", type=int, default=6, help="1画像あたり試すモデル候補数")
    parser.add_argument("--max-tokens", type=int, default=700, help="画像説明生成の最大トークン数")
    parser.add_argument("--timeout", type=int, default=90, help="OpenRouter APIのタイムアウト秒数")
    parser.add_argument("--dry-run", action="store_true", help="OpenRouterを呼ばずにレコードだけ作る")
    return parser.parse_args()


def main() -> None:
    """EDA013を実行する。"""
    args = parse_args()
    setup()

    doc_records, ignored_rows = build_doc_records(max_chars=args.max_chars)
    image_records, call_rows, model_rows = build_image_records(args)
    records = doc_records + image_records

    write_jsonl(records, EMBEDDING_RECORDS_PATH)
    summary_rows = summarize_records(records)
    file_rows = summarize_files(records)
    save_csv(summary_rows, TABLE_DIR / "embedding_record_summary.csv")
    save_csv(file_rows, TABLE_DIR / "embedding_file_summary.csv")
    save_csv(ignored_rows, TABLE_DIR / "ignored_files.csv")
    save_csv(call_rows, TABLE_DIR / "image_to_text_calls.csv")
    save_csv(model_rows, TABLE_DIR / "openrouter_vision_model_candidates.csv")
    write_report(records, summary_rows, ignored_rows, call_rows, model_rows, args)
    write_manifest(args, records)

    print(f"records={len(records)}")
    print(f"output={relative(EMBEDDING_RECORDS_PATH)}")
    print(f"report={relative(REPORT_PATH)}")


if __name__ == "__main__":
    main()
