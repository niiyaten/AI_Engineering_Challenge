from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
RAW_DIR = OUT_DIR / "raw_responses"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"

INVENTORY_PATH = TABLE_DIR / "image_asset_inventory.csv"
RESULT_PATH = TABLE_DIR / "image_to_text_results.csv"
JSONL_PATH = OUT_DIR / "image_to_text_records.jsonl"
CONTEXT_MD_PATH = OUT_DIR / "image_to_text_context.md"

MODEL_CANDIDATES = [
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
]

PRIORITY_TERMS = [
    "座席表",
    "基礎分析",
    "グラフ",
    "chart",
    "報告資料",
    "最終報告",
    "pptx.assets",
    "docx.assets",
]


def normalize_text(value: object) -> str:
    """パスや回答を比較しやすくするために文字種をそろえる。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value)).replace("\r\n", "\n").replace("\r", "\n")


def compact_text(value: object) -> str:
    """CSVやMarkdownに保存しやすい短い文字列へ整える。"""
    text = normalize_text(value)
    text = text.replace("```json", "").replace("```", "")
    text = " ".join(text.split())
    return text.strip()


def truthy(value: object) -> bool:
    """CSVから読み直した真偽値をPythonのboolへ戻す。"""
    return normalize_text(value).lower() in {"true", "1", "yes"}


def relative(path: Path | str | None) -> str:
    if path is None:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path)


def read_openrouter_key() -> str:
    """プロジェクトローカルの.apikeyからOpenRouterキーを読む。"""
    key_file = BASE_DIR / ".apikey"
    if key_file.exists():
        for raw in key_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip().lower() in {"openrouter", "openrouter_api_key"}:
                return value.strip().strip('"').strip("'")
    return os.environ.get("OPENROUTER_API_KEY", "")


def image_metadata(path: Path) -> dict[str, Any]:
    """画像の基本情報を取得する。読み取れない画像はサイズ0として記録する。"""
    meta: dict[str, Any] = {
        "image_path": relative(path),
        "suffix": path.suffix.lower(),
        "bytes": path.stat().st_size,
        "width": 0,
        "height": 0,
        "mode": "",
        "priority_score": priority_score(path),
    }
    try:
        with Image.open(path) as img:
            meta["width"] = int(img.width)
            meta["height"] = int(img.height)
            meta["mode"] = str(img.mode)
    except Exception as exc:
        meta["read_error"] = f"{type(exc).__name__}: {exc}"
    return meta


def priority_score(path: Path) -> int:
    """質問に効きそうな画像を先に処理するための簡易スコアを付ける。"""
    text = normalize_text(str(path)).lower()
    score = 0
    for term in PRIORITY_TERMS:
        if normalize_text(term).lower() in text:
            score += 10
    if "座席表" in text:
        score += 50
    if "青潮" in text:
        score += 35
    if "青潮" in text and "基礎分析" in text:
        score += 40
    if "notebooks" in text:
        score += 2
    return score


def build_inventory() -> pd.DataFrame:
    """processed配下の画像を一覧化する。"""
    paths: list[Path] = []
    for suffix in ("*.png", "*.jpg", "*.jpeg"):
        paths.extend(PROCESSED_ROOT.rglob(suffix))
    rows = [image_metadata(path) for path in sorted(set(paths), key=lambda p: normalize_text(str(p)))]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["priority_score", "bytes"], ascending=[False, False]).reset_index(drop=True)
    return df


def image_data_url(path: Path) -> str:
    """OpenRouterのVision入力に渡すdata URLを作る。"""
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def build_prompt(path: Path) -> str:
    return f"""この画像を、RAGの根拠データとして後で検索できるように文字起こししてください。

出力はJSONのみ:
{{
  "image_summary": "何の画像かを1文で説明",
  "visible_text": ["画像内に見える文字をできるだけ原文のまま列挙"],
  "tables": ["表があれば行列構造を短く記述"],
  "charts": ["グラフがあれば系列名、軸、凡例、読み取れる値を記述"],
  "seating_or_spatial_relations": ["座席表や配置図なら人名、EXT、左右、向かい、上下の関係を記述"],
  "answer_relevant_notes": ["SIGNATE RAG質問に効きそうな事実を箇条書き"]
}}

注意:
- 推測で名前や数値を作らない。
- 手順説明や思考過程は書かない。
- 読みにくい箇所は「判読困難」と明記する。
- グラフでは色、x値、y値、凡例を重視する。
- 座席表では人名、EXT、右側、左側、向かいの関係を重視する。

image_path: {relative(path)}
"""


def call_openrouter_vision(model: str, api_key: str, path: Path, max_tokens: int, timeout: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """画像をVisionモデルへ送り、JSON風の文字起こしを受け取る。"""
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_prompt(path)},
                    {"type": "image_url", "image_url": {"url": image_data_url(path)}},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.local/agentic-rag-eda047",
            "X-Title": "SIGNATE Agentic RAG EDA047",
        },
        method="POST",
    )
    meta: dict[str, Any] = {
        "model": model,
        "status": "",
        "finish_reason": "",
        "content_length": 0,
        "raw": None,
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        meta["raw"] = payload
        choice = payload.get("choices", [{}])[0]
        content = normalize_text((choice.get("message") or {}).get("content", ""))
        meta["status"] = "http_200"
        meta["finish_reason"] = choice.get("finish_reason", "")
        meta["content_length"] = len(content)
        return parse_json_or_text(content), meta
    except urllib.error.HTTPError as exc:
        meta["status"] = f"http_{exc.code}"
        meta["raw"] = {"error_body": exc.read().decode("utf-8", errors="replace")[:2000]}
        return {}, meta
    except Exception as exc:
        meta["status"] = f"error:{type(exc).__name__}"
        meta["raw"] = {"error": str(exc)}
        return {}, meta


def parse_json_or_text(content: str) -> dict[str, Any]:
    """モデル出力がJSONでない場合も後で読めるようtextとして保存する。"""
    text = normalize_text(content).strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"image_summary": "", "visible_text": [], "tables": [], "charts": [], "seating_or_spatial_relations": [], "answer_relevant_notes": [compact_text(text)]}


def write_raw_response(image_id: int, meta: dict[str, Any]) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"image_{image_id:03d}.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return relative(path)


def record_to_search_text(record: dict[str, Any]) -> str:
    """JSONレコードをembeddingやBM25に渡しやすい1本のテキストへ変換する。"""
    fields = [
        record.get("image_summary", ""),
        " ".join(map(str, record.get("visible_text", []) or [])),
        " ".join(map(str, record.get("tables", []) or [])),
        " ".join(map(str, record.get("charts", []) or [])),
        " ".join(map(str, record.get("seating_or_spatial_relations", []) or [])),
        " ".join(map(str, record.get("answer_relevant_notes", []) or [])),
    ]
    return compact_text(" ".join(fields))


def write_outputs(inventory_df: pd.DataFrame, result_df: pd.DataFrame, args: argparse.Namespace) -> None:
    """CSV、JSONL、Markdownレポートをまとめて保存する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    inventory_df.to_csv(INVENTORY_PATH, index=False, encoding="utf-8-sig")
    result_df.to_csv(RESULT_PATH, index=False, encoding="utf-8-sig")

    with JSONL_PATH.open("w", encoding="utf-8") as f:
        for _, row in result_df.iterrows():
            record = json.loads(row["record_json"])
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    adopted = int(result_df["success"].sum()) if not result_df.empty else 0
    status_summary = result_df.groupby(["status", "model"], as_index=False).size() if not result_df.empty else pd.DataFrame()
    preview_cols = ["image_id", "image_path", "model", "status", "success", "search_text"]
    preview = result_df[preview_cols].head(30) if not result_df.empty else pd.DataFrame(columns=preview_cols)
    context_rows = []
    for _, row in result_df[result_df["success"]].iterrows():
        context_rows.append(f"## image_id={row['image_id']} source={row['image_path']}\n{row['search_text']}\n")

    report = f"""# EDA047: image to text 前処理

## 背景と目的

EDA046では画像そのものを読まないrouteをまとめて作る。一方で、座席表の位置関係やグラフ画像の系列値はMarkdown/structure JSONだけでは不足しやすい。
EDA047では、processed配下の画像アセットをOpenRouterのVision対応無料モデルに送り、RAGで検索可能なJSONLとMarkdown文脈へ変換する。

## 実施内容

- 画像台帳: `{relative(INVENTORY_PATH)}`
- image-to-text結果: `{relative(RESULT_PATH)}`
- JSONL: `{relative(JSONL_PATH)}`
- Markdown文脈: `{relative(CONTEXT_MD_PATH)}`
- 総画像数: {len(inventory_df)}
- 今回処理数: {len(result_df)}
- 成功件数: {adopted}
- モデル候補: `{", ".join(args.models)}`

## ステータス集計

凡例: `status` はOpenRouter/API状態、`model` は使用モデル、`size` は件数を表す。

{status_summary.to_markdown(index=False) if not status_summary.empty else "結果なし"}

## プレビュー

凡例: `image_path` は対象画像、`success` は検索用テキストが作れたか、`search_text` はRAG投入用の要約テキストを表す。

{preview.to_markdown(index=False)}
"""
    (OUT_DIR / "eda047_report.md").write_text(report, encoding="utf-8")
    CONTEXT_MD_PATH.write_text("# Image To Text Context\n\n" + "\n".join(context_rows), encoding="utf-8")

    manifest = {
        "eda": "EDA047",
        "total_image_count": int(len(inventory_df)),
        "processed_image_count": int(len(result_df)),
        "success_count": adopted,
        "outputs": [
            relative(INVENTORY_PATH),
            relative(RESULT_PATH),
            relative(JSONL_PATH),
            relative(CONTEXT_MD_PATH),
            relative(OUT_DIR / "eda047_report.md"),
            relative(RAW_DIR),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--sleep-sec", type=float, default=4.0)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-api", action="store_true")
    parser.add_argument("--merge-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    api_key = read_openrouter_key()
    if not api_key and not args.no_api:
        raise RuntimeError("OpenRouter API key was not found in .apikey or environment")

    inventory_df = build_inventory()
    target_df = inventory_df.copy()
    if not args.all:
        target_df = target_df.head(args.limit)

    existing_success: dict[str, dict[str, Any]] = {}
    if args.merge_existing and RESULT_PATH.exists():
        previous_df = pd.read_csv(RESULT_PATH, encoding="utf-8-sig")
        for _, previous_row in previous_df.iterrows():
            if truthy(previous_row.get("success")):
                existing_success[normalize_text(previous_row.get("image_path"))] = previous_row.to_dict()

    rows: list[dict[str, Any]] = []
    for image_id, row in enumerate(target_df.itertuples(index=False), start=1):
        path = BASE_DIR / row.image_path
        record: dict[str, Any] = {
            "image_id": image_id,
            "image_path": row.image_path,
            "width": int(row.width),
            "height": int(row.height),
            "bytes": int(row.bytes),
            "image_summary": "",
            "visible_text": [],
            "tables": [],
            "charts": [],
            "seating_or_spatial_relations": [],
            "answer_relevant_notes": [],
        }
        model_used = ""
        status = "no_api"
        finish_reason = ""
        raw_path = ""
        success = False

        if not args.no_api:
            for model in args.models:
                model_used = model
                extracted, meta = call_openrouter_vision(model, api_key, path, args.max_tokens, args.timeout_sec)
                raw_path = write_raw_response(image_id, meta)
                status = normalize_text(meta.get("status", ""))
                finish_reason = normalize_text(meta.get("finish_reason", ""))
                if extracted:
                    record.update(extracted)
                    success = bool(record_to_search_text(record))
                    if success:
                        break
                time.sleep(args.sleep_sec)

        search_text = record_to_search_text(record)
        result_row = {
            "image_id": image_id,
            "image_path": row.image_path,
            "width": row.width,
            "height": row.height,
            "bytes": row.bytes,
            "priority_score": row.priority_score,
            "model": model_used,
            "status": status,
            "finish_reason": finish_reason,
            "success": success,
            "search_text": search_text,
            "record_json": json.dumps(record, ensure_ascii=False),
            "raw_response_path": raw_path,
        }
        previous_success = existing_success.get(normalize_text(row.image_path))
        if args.merge_existing and not success and previous_success:
            # Vision APIは同じ画像でも空contentを返すことがあるため、成功済みの抽出結果を保持する。
            result_row = dict(previous_success)
            result_row["image_id"] = image_id
            result_row["image_path"] = row.image_path
            result_row["status"] = f"{previous_success.get('status', '')}|reused_previous_success"
            result_row["success"] = True
        rows.append(result_row)
        # 無料APIは途中で止まりやすいため、1画像ごとに成果物を更新する。
        write_outputs(inventory_df, pd.DataFrame(rows), args)
        time.sleep(args.sleep_sec)

    result_df = pd.DataFrame(rows)
    write_outputs(inventory_df, result_df, args)


if __name__ == "__main__":
    main()
