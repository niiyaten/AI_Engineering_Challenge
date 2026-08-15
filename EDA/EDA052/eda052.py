from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import fitz
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
RAW_DIR = OUT_DIR / "raw_responses"
RENDER_DIR = OUT_DIR / "rendered_pages"

NO_TEXT_INVENTORY = BASE_DIR / "EDA" / "EDA050" / "tables" / "no_text_pdf_inventory.csv"


def norm(value: object) -> str:
    """検索・保存用に文字列を正規化する。"""
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).replace("\r\n", "\n").replace("\r", "\n").strip()


def compact(value: object, limit: int = 800) -> str:
    return " ".join(norm(value).split())[:limit]


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def safe_name(value: str) -> str:
    """Windowsファイル名に使いやすい短い名前へ変換する。"""
    text = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ヶー]+", "_", norm(value))
    return text.strip("_")[:80] or "pdf"


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


def processed_md_to_raw_pdf(processed_md: Path) -> Path | None:
    """processed Markdownのraw_pathメタデータからraw PDFパスを復元する。"""
    text = processed_md.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"raw_path:\s*`([^`]+)`", text)
    if not m:
        return None
    raw_rel = Path(m.group(1).replace("/", "\\"))
    candidates = [
        BASE_DIR / "data" / "raw" / raw_rel,
        BASE_DIR / "data" / "raw" / "share" / raw_rel,
    ]
    for raw_path in candidates:
        if raw_path.exists():
            return raw_path
    matches = list((BASE_DIR / "data" / "raw").rglob(raw_rel.name))
    return matches[0] if matches else None


def target_documents(no_text_df: pd.DataFrame) -> pd.DataFrame:
    """残件に直接関係するPDFを優先対象にする。"""
    rows = []
    for _, row in no_text_df.iterrows():
        project = norm(row.get("project"))
        source = norm(row.get("source_path"))
        priority = 0
        reason = ""
        if "白峰" in project and "会議録_2025-07-15" in source:
            priority = 100
            reason = "index18: M04進捗サマリ候補"
        elif "みなみ野" in project and "会議録_2025-05-15" in source:
            priority = 90
            reason = "index93: A10候補"
        elif "白峰" in project and "会議録" in source:
            priority = 50
            reason = "白峰会議録OCR補助"
        elif "みなみ野" in project and "会議録" in source:
            priority = 40
            reason = "みなみ野会議録OCR補助"
        if priority:
            item = row.to_dict()
            item["priority"] = priority
            item["target_reason"] = reason
            rows.append(item)
    return pd.DataFrame(rows).sort_values(["priority", "source_path"], ascending=[False, True]).reset_index(drop=True)


def render_pdf_pages(raw_pdf: Path, out_prefix: str, max_pages: int | None = None) -> list[dict[str, Any]]:
    """PDF各ページをPNGにレンダリングする。"""
    rows: list[dict[str, Any]] = []
    doc = fitz.open(raw_pdf)
    page_total = len(doc)
    page_count = min(page_total, max_pages) if max_pages else page_total
    for page_index in range(page_count):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        image_path = RENDER_DIR / f"{out_prefix}_page{page_index + 1:03d}.png"
        pix.save(image_path)
        rows.append(
            {
                "raw_pdf_path": relative(raw_pdf),
                "page": page_index + 1,
                "page_total": page_total,
                "image_path": relative(image_path),
                "width": pix.width,
                "height": pix.height,
                "bytes": image_path.stat().st_size,
            }
        )
    doc.close()
    return rows


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def parse_json_or_text(text: str) -> dict[str, Any]:
    clean = norm(text).removeprefix("```json").removesuffix("```").strip()
    if not clean:
        return {}
    try:
        obj = json.loads(clean)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"visible_text": clean}


def call_openrouter_vision(api_key: str, image_path: Path, model: str, max_tokens: int, timeout_sec: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """PDFページ画像をOCR/構造化する。"""
    prompt = """このPDFページ画像をOCRし、会議録/報告資料として構造化してください。

出力はJSONのみ:
{
  "meeting_id": "M01/M02/M03/M04など。なければ空文字",
  "date": "YYYY-MM-DD。なければ空文字",
  "page_title": "ページの主な見出し",
  "progress_summary": "進捗サマリがあれば原文に近く抽出。なければ空文字",
  "action_items": [
    {"action_id": "A10", "content": "内容", "owner": "担当", "due": "期限", "status": "状態"}
  ],
  "comments": ["コメントや注記があれば原文に近く抽出"],
  "checkpoints": ["チェックポイントや関連タスクIDがあれば抽出"],
  "visible_text": "ページ内の主要テキストを原文に近くまとめる"
}

注意:
- 推測でIDや数値を作らない。
- アクションIDは A01, A10 のような表記を最優先で読む。
- 進捗サマリ、コメント、Status/Open/完了を重視する。
"""
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
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
            "HTTP-Referer": "https://signate.local/agentic-rag-eda052",
            "X-Title": "SIGNATE Agentic RAG EDA052",
        },
        method="POST",
    )
    meta: dict[str, Any] = {"status": "", "finish_reason": "", "content_length": 0, "raw": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        meta["raw"] = payload
        choice = payload.get("choices", [{}])[0]
        content = norm((choice.get("message") or {}).get("content", ""))
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


def record_to_search_text(record: dict[str, Any]) -> str:
    parts = [
        record.get("meeting_id", ""),
        record.get("date", ""),
        record.get("page_title", ""),
        record.get("progress_summary", ""),
        " ".join(json.dumps(x, ensure_ascii=False) for x in record.get("action_items", []) or []),
        " ".join(map(str, record.get("comments", []) or [])),
        " ".join(map(str, record.get("checkpoints", []) or [])),
        record.get("visible_text", ""),
    ]
    return compact(" ".join(map(str, parts)), 2000)


def make_probe_answers(result_df: pd.DataFrame) -> pd.DataFrame:
    """OCR結果から残件候補を作る。"""
    rows = []
    if result_df.empty or "project" not in result_df.columns:
        return pd.DataFrame(
            [
                {
                    "index": 18,
                    "question": "白峰信用リスク評価の会議ID:M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。",
                    "candidate_answer": "",
                    "evidence": "",
                    "needs_review": True,
                },
                {
                    "index": 93,
                    "question": "蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。",
                    "candidate_answer": "",
                    "evidence": "",
                    "needs_review": True,
                },
            ]
        )
    text_col = result_df["search_text"].fillna("") if not result_df.empty else pd.Series(dtype=str)
    record_col = result_df["record_json"].fillna("") if "record_json" in result_df.columns else pd.Series([""] * len(result_df))
    has_progress_summary = record_col.str.contains(r'"progress_summary"\s*:\s*"[^"]+', regex=True, na=False) | text_col.str.contains("進捗|完了\\(今回まで\\)|本日対応済", regex=True, na=False)
    shiramine = result_df[
        result_df["project"].str.contains("白峰", na=False)
        & (
            text_col.str.contains("M04", na=False)
            | result_df["file_name"].str.contains("2025-07-15", na=False)
        )
        & has_progress_summary
    ]
    if shiramine.empty:
        # 白峰M04候補の2025-07-15会議録では、Vision出力がJSON崩れでもpage2に進捗サマリ相当が出ることがある。
        shiramine = result_df[
            result_df["project"].str.contains("白峰", na=False)
            & result_df["file_name"].str.contains("2025-07-15", na=False)
            & result_df["page"].astype(str).eq("2")
            & text_col.str.len().gt(0)
        ]
    rows.append(
        {
            "index": 18,
            "question": "白峰信用リスク評価の会議ID:M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。",
            "candidate_answer": "、".join(map(str, sorted(shiramine["page"].dropna().astype(int).unique()))) if not shiramine.empty else "",
            "evidence": " | ".join(shiramine["image_path"].head(5).tolist()) if not shiramine.empty else "",
            "needs_review": shiramine.empty,
        }
    )
    minamino_a10 = result_df[
        result_df["project"].str.contains("みなみ野", na=False)
        & text_col.str.contains("A10", na=False)
    ]
    rows.append(
        {
            "index": 93,
            "question": "蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。",
            "candidate_answer": " / ".join(minamino_a10["search_text"].head(3).tolist()) if not minamino_a10.empty else "",
            "evidence": " | ".join(minamino_a10["image_path"].head(5).tolist()) if not minamino_a10.empty else "",
            "needs_review": minamino_a10.empty,
        }
    )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--model", default="nvidia/nemotron-nano-12b-v2-vl:free")
    parser.add_argument("--max-tokens", type=int, default=1400)
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--sleep-sec", type=float, default=6.0)
    parser.add_argument("--no-api", action="store_true")
    parser.add_argument("--reuse-results", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    no_text_df = pd.read_csv(NO_TEXT_INVENTORY, encoding="utf-8-sig", dtype=str).fillna("")
    targets = target_documents(no_text_df)

    render_rows: list[dict[str, Any]] = []
    remaining_budget = args.max_pages
    for _, row in targets.iterrows():
        if remaining_budget <= 0:
            break
        md_path = BASE_DIR / row["source_path"]
        raw_pdf = processed_md_to_raw_pdf(md_path)
        if raw_pdf is None:
            continue
        page_limit = min(int(row["no_text_page_count"]), remaining_budget)
        prefix = safe_name(f"{row['project']}_{Path(row['source_path']).stem}")
        rows = render_pdf_pages(raw_pdf, prefix, page_limit)
        for item in rows:
            item.update({"project": row["project"], "source_path": row["source_path"], "file_name": Path(row["source_path"]).name, "target_reason": row["target_reason"]})
        render_rows.extend(rows)
        remaining_budget -= len(rows)

    render_df = pd.DataFrame(render_rows)
    render_path = TABLE_DIR / "rendered_no_text_pdf_pages.csv"
    render_df.to_csv(render_path, index=False, encoding="utf-8-sig")

    result_path = TABLE_DIR / "pdf_page_vision_ocr_results.csv"
    if args.reuse_results and result_path.exists():
        result_df = pd.read_csv(result_path, encoding="utf-8-sig", dtype=str).fillna("")
        probe_df = make_probe_answers(result_df)
        probe_path = TABLE_DIR / "no_text_pdf_question_probe.csv"
        probe_df.to_csv(probe_path, index=False, encoding="utf-8-sig")
        print(json.dumps({"eda": "EDA052", "reuse_results": True, "probe_count": int(len(probe_df))}, ensure_ascii=False, indent=2))
        return

    api_key = read_openrouter_key()
    result_rows: list[dict[str, Any]] = []
    if not args.no_api and api_key:
        for _, row in render_df.iterrows():
            image_path = BASE_DIR / row["image_path"]
            record, meta = call_openrouter_vision(api_key, image_path, args.model, args.max_tokens, args.timeout_sec)
            raw_path = RAW_DIR / f"page_{len(result_rows) + 1:03d}.json"
            raw_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            result_rows.append(
                {
                    **row.to_dict(),
                    "model": args.model,
                    "status": meta.get("status", ""),
                    "finish_reason": meta.get("finish_reason", ""),
                    "success": bool(record),
                    "search_text": record_to_search_text(record),
                    "record_json": json.dumps(record, ensure_ascii=False),
                    "raw_response_path": relative(raw_path),
                }
            )
            result_df = pd.DataFrame(result_rows)
            result_df.to_csv(TABLE_DIR / "pdf_page_vision_ocr_results.csv", index=False, encoding="utf-8-sig")
            time.sleep(args.sleep_sec)

    result_df = pd.DataFrame(result_rows)
    if result_df.empty:
        result_df = render_df.copy()
        result_df["success"] = False
        result_df["search_text"] = ""
        result_df["record_json"] = "{}"
        result_df.to_csv(result_path, index=False, encoding="utf-8-sig")
    else:
        result_df.to_csv(result_path, index=False, encoding="utf-8-sig")

    jsonl_path = OUT_DIR / "pdf_page_vision_ocr_records.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for _, row in result_df.iterrows():
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")

    probe_df = make_probe_answers(result_df)
    probe_path = TABLE_DIR / "no_text_pdf_question_probe.csv"
    probe_df.to_csv(probe_path, index=False, encoding="utf-8-sig")

    report = f"""# EDA052: no text PDFのページ画像OCR/Vision

## 背景と目的

EDA050で、会議録/報告資料のうち14 PDFが `[no text extracted]` だった。
このままでは会議ID、進捗サマリ、アクションIDを検索できない。
EDA052では、残件に直結する白峰M04候補とみなみ野A10候補を優先し、PDFページをPNGへレンダリングしてOpenRouter VisionでOCRする。

## 実施内容

- no text PDF総数: {len(no_text_df)}
- OCR対象PDF候補: {len(targets)}
- 今回レンダリングページ数: {len(render_df)}
- Vision成功ページ数: {int(result_df["success"].astype(bool).sum()) if "success" in result_df else 0}
- モデル: `{args.model}`

## 残件候補

凡例: `candidate_answer` はOCR結果から作った回答候補、`needs_review` は提出採用前の確認要否を表す。

{probe_df.to_markdown(index=False)}

## 出力

- レンダリング台帳: `{render_path.relative_to(BASE_DIR).as_posix()}`
- Vision OCR結果: `{result_path.relative_to(BASE_DIR).as_posix()}`
- JSONL: `{jsonl_path.relative_to(BASE_DIR).as_posix()}`
- 残件候補: `{probe_path.relative_to(BASE_DIR).as_posix()}`

## 注意

OpenRouter Visionはページによって空contentや誤読があり得る。
提出用では、OCR結果をそのまま採用せず、対象ページの画像、raw response、候補回答を確認してから使う。
"""
    report_path = OUT_DIR / "eda052_report.md"
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "eda": "EDA052",
        "no_text_pdf_count": int(len(no_text_df)),
        "target_pdf_count": int(len(targets)),
        "rendered_page_count": int(len(render_df)),
        "vision_success_count": int(result_df["success"].astype(bool).sum()) if "success" in result_df else 0,
        "outputs": [
            render_path.relative_to(BASE_DIR).as_posix(),
            result_path.relative_to(BASE_DIR).as_posix(),
            jsonl_path.relative_to(BASE_DIR).as_posix(),
            probe_path.relative_to(BASE_DIR).as_posix(),
            report_path.relative_to(BASE_DIR).as_posix(),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
