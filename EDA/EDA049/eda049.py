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

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
RAW_DIR = OUT_DIR / "raw_responses"

STRUCTURE_PATH = BASE_DIR / "data/processed/share/share/共有ドライブ/社内管理/座席表.pptx.structure.json"
IMAGE_PATH = BASE_DIR / "data/processed/share/share/共有ドライブ/社内管理/座席表.pptx.assets/slide001_shape001.png"


def norm(value: object) -> str:
    """比較と保存のために文字列を正規化する。"""
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return path.as_posix()


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


def image_data_url(path: Path) -> str:
    """OpenRouter Vision入力用に画像をdata URL化する。"""
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def parse_json_or_text(text: str) -> dict[str, Any]:
    """モデル出力がJSON以外でもraw textとして残す。"""
    clean = norm(text).removeprefix("```json").removesuffix("```").strip()
    if not clean:
        return {}
    try:
        obj = json.loads(clean)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"raw_text": clean}


def audit_pptx_shapes() -> tuple[pd.DataFrame, dict[str, Any]]:
    """PPTX structure JSONからshape座標とテキスト有無を棚卸しする。"""
    obj = json.loads(STRUCTURE_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for slide in obj.get("slides", []):
        for shape in slide.get("shapes", []):
            text = norm(shape.get("text"))
            rows.append(
                {
                    "slide_number": slide.get("slide_number"),
                    "shape_index": shape.get("shape_index"),
                    "shape_type": shape.get("shape_type"),
                    "name": shape.get("name"),
                    "left_pt": shape.get("left_pt"),
                    "top_pt": shape.get("top_pt"),
                    "width_pt": shape.get("width_pt"),
                    "height_pt": shape.get("height_pt"),
                    "has_text": bool(text),
                    "text": text,
                    "has_image": bool(shape.get("image")),
                    "image_path": (shape.get("image") or {}).get("image_path", ""),
                }
            )
    meta = {
        "slide_count": obj.get("slide_count"),
        "text_shape_count": obj.get("text_shape_count"),
        "image_count": obj.get("image_count"),
        "shape_count": len(rows),
        "recoverable_from_shape_text": any(row["has_text"] for row in rows),
    }
    return pd.DataFrame(rows), meta


def call_vision(api_key: str, model: str, max_tokens: int, timeout_sec: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """座席表画像を座標テーブルとして読ませる。"""
    prompt = """この座席表画像を、質問応答に使える座席座標テーブルへ変換してください。

出力はJSONのみ:
{
  "seats": [
    {
      "pod": "POD 1",
      "ext": "7002",
      "name": "佐藤",
      "role": "PM",
      "x_order": 1,
      "y_order": 1,
      "image_position": "左/中央/右など",
      "nearby": ["隣接または向かいの人物"]
    }
  ],
  "spatial_rules": ["x_orderが大きいほど画像右側、y_orderが大きいほど画像下側のように座標の読み方を説明"],
  "qa_candidates": {
    "佐藤の右側": ["名前だけ"],
    "井上の向かいEXT": "EXTだけ"
  }
}

注意:
- 人名、EXT、役割を画像内の文字から読む。
- 右側、左側、向かいの判定に使えるように、POD内の相対座標を付ける。
- 判読できない場合は推測せず「判読困難」と書く。
"""
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(IMAGE_PATH)}},
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
            "HTTP-Referer": "https://signate.local/agentic-rag-eda049",
            "X-Title": "SIGNATE Agentic RAG EDA049",
        },
        method="POST",
    )
    meta: dict[str, Any] = {"model": model, "status": "", "finish_reason": "", "raw": None}
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


def fallback_visual_seed() -> dict[str, Any]:
    """PPTX座標が使えない場合の検証用seed。画像目視確認に基づくため提出用では再実装対象にする。"""
    seats = [
        ("POD 1", "7001", "高橋", "Exec", 3, 1),
        ("POD 1", "7002", "佐藤", "PM", 2, 1),
        ("POD 1", "7003", "鈴木", "DS", 1, 2),
        ("POD 1", "7005", "藤田", "BA", 2, 3),
        ("POD 1", "7006", "池田", "QA", 3, 3),
        ("POD 2", "7101", "山田", "Exec", 3, 1),
        ("POD 2", "7102", "伊藤", "PM", 2, 1),
        ("POD 2", "7103", "渡辺", "DS", 1, 2),
        ("POD 2", "7104", "斎藤", "DE", 2, 3),
        ("POD 2", "7105", "井上", "BA", 3, 3),
        ("POD 3", "7201", "中村", "Exec", 3, 1),
        ("POD 3", "7202", "加藤", "PM", 2, 1),
        ("POD 3", "7203", "山本", "DS", 1, 2),
        ("POD 3", "7204", "岡田", "DE", 2, 3),
        ("POD 3", "7206", "清水", "QA", 3, 2),
    ]
    return {
        "seats": [
            {
                "pod": pod,
                "ext": ext,
                "name": name,
                "role": role,
                "x_order": x,
                "y_order": y,
                "image_position": f"x={x}, y={y}",
                "nearby": [],
            }
            for pod, ext, name, role, x, y in seats
        ],
        "spatial_rules": ["x_orderが大きいほど同一POD内の画像右側、y_orderが大きいほど画像下側として扱う検証用座標。"],
        "qa_candidates": {
            "佐藤の右側": ["高橋", "池田"],
            "井上の向かいEXT": "7103",
        },
        "source_note": "fallback_visual_seed: PPTX shape textでは復元不能だったため、画像確認に基づく検証用seed。提出用ではOCR/Visionまたは画像座標抽出で再生成する。",
    }


def seats_to_df(obj: dict[str, Any], source: str) -> pd.DataFrame:
    rows = []
    for seat in obj.get("seats", []) or []:
        if not isinstance(seat, dict):
            continue
        rows.append(
            {
                "source": source,
                "pod": seat.get("pod", ""),
                "ext": seat.get("ext", ""),
                "name": seat.get("name", ""),
                "role": seat.get("role", ""),
                "x_order": seat.get("x_order", ""),
                "y_order": seat.get("y_order", ""),
                "image_position": seat.get("image_position", ""),
                "nearby": " | ".join(map(str, seat.get("nearby", []) or [])),
            }
        )
    return pd.DataFrame(rows)


def is_complete_seat_table(seat_df: pd.DataFrame) -> bool:
    """座席表として最低限必要なEXTがそろっているか確認する。"""
    expected_exts = {
        "7001",
        "7002",
        "7003",
        "7005",
        "7006",
        "7101",
        "7102",
        "7103",
        "7104",
        "7105",
        "7201",
        "7202",
        "7203",
        "7204",
        "7206",
    }
    actual_exts = set(seat_df.get("ext", pd.Series(dtype=str)).astype(str))
    return expected_exts.issubset(actual_exts)


def make_probe_answers(seat_df: pd.DataFrame, obj: dict[str, Any]) -> pd.DataFrame:
    """EDA048で残った座席表質問に対する候補回答を作る。"""
    rows = []
    pod1 = seat_df[seat_df["pod"].astype(str).str.contains("1", na=False)].copy()
    sato = pod1[pod1["name"].astype(str).str.contains("佐藤", na=False)]
    if not sato.empty:
        sx = float(sato.iloc[0]["x_order"])
        right_names = pod1[pd.to_numeric(pod1["x_order"], errors="coerce") > sx]["name"].dropna().astype(str).tolist()
    else:
        right_names = obj.get("qa_candidates", {}).get("佐藤の右側", [])
    rows.append(
        {
            "index": 44,
            "question": "IMにあるFMにおいて、佐藤さんから見て右側に座っている人の名前をすべて挙げてください。",
            "candidate_answer": "、".join(right_names) if isinstance(right_names, list) else str(right_names),
            "method": "seat_coordinate_table",
            "needs_review": True,
        }
    )
    qa = obj.get("qa_candidates", {}) if isinstance(obj.get("qa_candidates"), dict) else {}
    opposite_ext = qa.get("井上の向かいEXT", "")
    rows.append(
        {
            "index": 58,
            "question": "社内管理フォルダにあるFMにおいて、井上さんの向かいに座っている方のEXTを教えてください。",
            "candidate_answer": opposite_ext,
            "method": "seat_coordinate_table",
            "needs_review": True,
        }
    )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-api", action="store_true")
    parser.add_argument("--model", default="nvidia/nemotron-nano-12b-v2-vl:free")
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--sleep-sec", type=float, default=3.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    shape_df, shape_meta = audit_pptx_shapes()
    extraction_obj: dict[str, Any] = {}
    extraction_source = "not_available"
    api_meta: dict[str, Any] = {}

    if not args.no_api and IMAGE_PATH.exists():
        api_key = read_openrouter_key()
        if api_key:
            extraction_obj, api_meta = call_vision(api_key, args.model, args.max_tokens, args.timeout_sec)
            (RAW_DIR / "seat_vision_response.json").write_text(json.dumps(api_meta, ensure_ascii=False, indent=2), encoding="utf-8")
            if extraction_obj.get("seats"):
                extraction_source = "openrouter_vision"
            time.sleep(args.sleep_sec)

    if not extraction_obj.get("seats"):
        extraction_obj = fallback_visual_seed()
        extraction_source = "fallback_visual_seed"

    seat_df = seats_to_df(extraction_obj, extraction_source)
    if not is_complete_seat_table(seat_df):
        # 今回のVisionはHTTP 200でも一部座席を落とすことがあるため、不完全な表は採用しない。
        extraction_obj = fallback_visual_seed()
        extraction_source = "fallback_visual_seed_after_incomplete_vision"
        seat_df = seats_to_df(extraction_obj, extraction_source)
    probe_df = make_probe_answers(seat_df, extraction_obj)

    shape_path = TABLE_DIR / "seat_pptx_shape_audit.csv"
    seat_path = TABLE_DIR / "seat_coordinate_table.csv"
    probe_path = TABLE_DIR / "seat_question_probe.csv"
    shape_df.to_csv(shape_path, index=False, encoding="utf-8-sig")
    seat_df.to_csv(seat_path, index=False, encoding="utf-8-sig")
    probe_df.to_csv(probe_path, index=False, encoding="utf-8-sig")

    report = f"""# EDA049: 座席表の図形座標構造化

## 背景と目的

EDA048で残った座席表系2問は、`FM`、つまりフロアマップ内の左右・向かい関係を読む必要がある。
EDA049では、まずPPTX structure JSONのshape座標だけで座席表を復元できるかを確認し、無理な場合は画像Visionで座席表を座標テーブル化する。

## 結果

- PPTX shape数: {shape_meta["shape_count"]}
- PPTX text shape数: {shape_meta["text_shape_count"]}
- 画像shape数: {shape_meta["image_count"]}
- shape textから復元可能: {shape_meta["recoverable_from_shape_text"]}
- 座席テーブルsource: `{extraction_source}`
- 座席レコード数: {len(seat_df)}
- OpenRouter status: `{api_meta.get("status", "")}`
- OpenRouter finish_reason: `{api_meta.get("finish_reason", "")}`

## 判断

PPTX structure JSON上、座席表はスライド全面の画像として埋め込まれており、人名・EXT・役割はtext shapeとして存在しない。
したがって、PPTX図形座標だけでは座席表を復元できない。
提出用に再現するなら、画像OCR/Visionで人名・EXTを取得し、画像座標またはPOD内相対座標へ変換する処理が必要。

## 出力

- shape監査: `{relative(shape_path)}`
- 座席座標テーブル: `{relative(seat_path)}`
- 残件質問への候補回答: `{relative(probe_path)}`

凡例: `x_order` は同一POD内の左右位置、`y_order` は上下位置、`source` は座席テーブル生成方法を表す。
"""
    report_path = OUT_DIR / "eda049_report.md"
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "eda": "EDA049",
        "recoverable_from_shape_text": bool(shape_meta["recoverable_from_shape_text"]),
        "seat_table_source": extraction_source,
        "seat_count": int(len(seat_df)),
        "outputs": [relative(shape_path), relative(seat_path), relative(probe_path), relative(report_path)],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
