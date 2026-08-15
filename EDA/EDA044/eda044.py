from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
RAW_DIR = OUT_DIR / "raw_responses"
PRED_DIR = OUT_DIR / "predictions"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
INPUT_RESULT = BASE_DIR / "EDA" / "EDA043" / "tables" / "test_compressed_context_retry_result.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda044_format_table_image_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = ["openai/gpt-oss-20b:free"]

PROJECT_ALIASES: dict[str, list[str]] = {
    "かえで": ["かえで", "恒一会"],
    "ひがし丘": ["ひがし丘", "蒼泉会"],
    "みなみ野": ["みなみ野", "蒼樹会", "MINAMINO"],
    "東都": ["東都", "TOTO"],
    "青嶺": ["青嶺", "AOMINE"],
    "青潮": ["青潮", "AOSHIO"],
    "青葉バイオ": ["青葉バイオ", "AOBM"],
    "青葉与信": ["青葉与信", "AYM", "青葉"],
    "白峰": ["白峰", "SHR"],
    "京橋": ["京橋", "KSS", "京ソ"],
}


def normalize_text(value: object) -> str:
    """検索と回答判定のため、欠損と表記揺れを正規化する。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出回答に不要なHTML、Markdown記号、改行を残さない。"""
    text = normalize_text(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"\s*\n\s*", "、", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip(" 、")


def relative(path: Path | str | None) -> str:
    if path is None:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def read_csv_safe(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:
        return None


def read_openrouter_key() -> str:
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


def project_keywords(question: str) -> list[str]:
    q = normalize_text(question)
    for keys in PROJECT_ALIASES.values():
        if any(key in q for key in keys):
            return keys
    return []


def find_paths(*keywords: str, suffix: str | None = None) -> list[Path]:
    """processed配下から、パスにキーワードをすべて含むファイルを探す。"""
    keys = [normalize_text(k).lower() for k in keywords if k]
    results: list[Path] = []
    for path in PROCESSED_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if suffix and not normalize_text(path.name).lower().endswith(suffix.lower()):
            continue
        haystack = normalize_text(str(path)).lower().replace("\\", "/")
        if all(key in haystack for key in keys):
            results.append(path)
    return sorted(results, key=lambda p: normalize_text(str(p)))


def col_num(coordinate: str) -> int:
    match = re.match(r"([A-Z]+)", coordinate.upper())
    if not match:
        return 0
    value = 0
    for ch in match.group(1):
        value = value * 26 + ord(ch) - ord("A") + 1
    return value


def row_num(coordinate: str) -> int:
    match = re.search(r"(\d+)", coordinate)
    return int(match.group(1)) if match else 0


def row_context(df: pd.DataFrame, excel_row: int, excel_col: int, max_fields: int = 12) -> str:
    """Excel上のセル位置から、同じ行の値を短い文脈にする。"""
    idx = excel_row - 2
    if idx < 0 or idx >= len(df):
        return ""
    values = []
    for col, value in df.iloc[idx].items():
        text = compact_answer(value)
        if text:
            values.append(f"{col}={text}")
        if len(values) >= max_fields:
            break
    cell_value = ""
    if 0 <= excel_col - 1 < len(df.columns):
        cell_value = compact_answer(df.iloc[idx, excel_col - 1])
    return f"cell_value={cell_value} | " + " | ".join(values)


def yellow_records_for_workbook(path: Path) -> list[str]:
    """Excel structure.jsonから黄色セルとRED形式セルの文脈を抽出する。"""
    yellow = {"FFFFFF00", "FFFFEB9C", "FFFFF2CC", "FFFFFF99"}
    obj = load_json(path)
    records: list[str] = []
    for sheet in obj.get("sheets", []):
        csv_path = Path(sheet.get("exported_csv_path", ""))
        df = read_csv_safe(csv_path) if csv_path.exists() else None
        for cell in sheet.get("styled_cells", []):
            fill = normalize_text(cell.get("fill_color", "")).upper()
            number_format = normalize_text(cell.get("number_format", ""))
            if fill not in yellow and "RED" not in number_format.upper():
                continue
            coord = normalize_text(cell.get("coordinate", ""))
            context = ""
            if df is not None:
                context = row_context(df, row_num(coord), col_num(coord))
            records.append(
                f"{relative(path)} | sheet={sheet.get('sheet_name')} | cell={coord} | "
                f"fill={fill} | number_format={number_format} | {context}"
            )
    return records


def styled_text_records(path: Path) -> list[str]:
    """PPTX/DOCX structure.jsonから太字・下線・イタリックのrunを抽出する。"""
    obj = load_json(path)
    records: list[str] = []

    def keep(run: dict[str, Any]) -> bool:
        return bool(run.get("bold") and run.get("underline") and run.get("italic"))

    if obj.get("file_type") == "pptx":
        for slide in obj.get("slides", []):
            for shape in slide.get("shapes", []):
                frame = shape.get("text_frame") or {}
                for para in frame.get("paragraphs", []):
                    for run in para.get("runs", []):
                        if keep(run):
                            records.append(
                                f"{relative(path)} | slide={slide.get('slide_number')} | text={compact_answer(run.get('text',''))} | "
                                f"paragraph={compact_answer(para.get('text',''))}"
                            )
    else:
        for i, para in enumerate(obj.get("paragraphs", []) + obj.get("blocks", []), start=1):
            runs = para.get("runs", []) if isinstance(para, dict) else []
            for run in runs:
                if keep(run):
                    records.append(
                        f"{relative(path)} | paragraph={i} | text={compact_answer(run.get('text',''))} | "
                        f"paragraph={compact_answer(para.get('text',''))}"
                    )
    return records


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def local_answer(index: int, question: str) -> tuple[str, str, list[str], str]:
    """誤答リスクが低いものだけローカルで回答する。"""
    if index == 97:
        path = find_paths("青葉バイオ", "train.xlsx.sheets", "train.csv", suffix=".csv")
        if path:
            df = read_csv_safe(path[0])
            if df is not None and "MonthlyIncome" in df.columns:
                vals = numeric_series(df["MonthlyIncome"]).dropna()
                if len(vals) >= 2:
                    return str(int(abs(vals.iloc[0] - vals.iloc[1]))), "local_yellow_first_two_abs_diff", [relative(path[0])], vals.head(5).to_string()
    return "", "llm_needed", [], ""


def candidate_context(index: int, question: str, route: str) -> tuple[str, list[str], str]:
    """route別にLLMへ渡す候補文脈を作る。"""
    q = normalize_text(question)
    lines: list[str] = []
    sources: list[str] = []

    if route == "format_extraction":
        for key in project_keywords(q)[:1] or [""]:
            for path in find_paths(key, suffix=".xlsx.structure.json"):
                recs = yellow_records_for_workbook(path)
                if recs:
                    lines.extend(recs[:80])
                    sources.append(relative(path))
            for path in find_paths(key, suffix=".pptx.structure.json") + find_paths(key, suffix=".docx.structure.json"):
                recs = styled_text_records(path)
                if recs:
                    lines.extend(recs[:40])
                    sources.append(relative(path))

    if route == "table_calculation":
        keys = project_keywords(q)
        for key in keys[:1] or [""]:
            for hint in ["train", "スケジュール", "最終報告", "契約", "決裁"]:
                for path in find_paths(key, hint, suffix=".csv")[:8]:
                    df = read_csv_safe(path)
                    if df is None:
                        continue
                    text = df.head(40).to_csv(index=False)
                    lines.append(f"# {relative(path)}\n{text[:3000]}")
                    sources.append(relative(path))
                for path in find_paths(key, hint, suffix=".md")[:6]:
                    snippets = []
                    terms = question_terms(q)
                    for raw in read_text(path).splitlines():
                        clean = compact_answer(raw)
                        if clean and sum(1 for term in terms if term.lower() in clean.lower()):
                            snippets.append(clean)
                    if snippets:
                        lines.append(f"# {relative(path)}\n" + "\n".join(snippets[:40]))
                        sources.append(relative(path))
        if "APR" in q or "社内管理" in q:
            for path in find_paths("社内管理", suffix=".md")[:4]:
                lines.append(f"# {relative(path)}\n" + "\n".join(read_text(path).splitlines()[:120]))
                sources.append(relative(path))

    if route == "image_ocr":
        for key in project_keywords(q)[:1] or ["青潮"]:
            for path in find_paths(key, "基礎分析", suffix=".md") + find_paths(key, "基礎分析", suffix=".structure.json"):
                text = read_text(path)
                terms = question_terms(q)
                snippets = []
                for raw in text.splitlines():
                    clean = compact_answer(raw)
                    if clean and (any(term.lower() in clean.lower() for term in terms) or "image_path" in clean or "chart" in clean.lower()):
                        snippets.append(clean)
                lines.append(f"# {relative(path)}\n" + "\n".join(snippets[:80]))
                sources.append(relative(path))
            for path in find_paths(key, "train.xlsx", suffix=".structure.json") + find_paths(key, "train.xlsx.sheets", suffix=".csv"):
                try:
                    if path.suffix == ".json":
                        lines.append(f"# {relative(path)}\n" + read_text(path)[:4000])
                    else:
                        df = read_csv_safe(path)
                        if df is not None:
                            lines.append(f"# {relative(path)}\n" + df.head(25).to_csv(index=False)[:3000])
                    sources.append(relative(path))
                except Exception:
                    pass

    context = "\n".join(dict.fromkeys(lines))
    if len(context) > 12000:
        context = context[:12000]
    return context, list(dict.fromkeys(sources)), "context_built" if context.strip() else "no_context"


def question_terms(question: str) -> list[str]:
    q = normalize_text(question)
    terms = re.findall(r"[A-Za-z0-9_./+-]+|[一-龥ぁ-んァ-ンー]{2,}", q)
    stop = {"について", "ください", "答えて", "すべて", "案件", "資料", "ファイル", "おいて", "教えて", "場合", "答え"}
    out: list[str] = []
    for term in terms:
        if term and term not in stop and not term.isdigit() and term not in out:
            out.append(term)
    return out[:20]


def acceptable_answer(answer: str) -> bool:
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 320:
        return False
    bad = ["color=", "</span>", "```", "申し訳", "根拠", "json", "情報不足", "情報が不足", "不明", "見つかりません", "確認できません", "不足しています"]
    return not any(x.lower() in answer.lower() for x in bad)


def parse_json_answer(content: str) -> str:
    text = normalize_text(content).strip()
    if not text:
        return ""
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return compact_answer(obj.get("answer", ""))
    except Exception:
        pass
    return compact_answer(text)


def build_prompt(question: str, context: str) -> str:
    return f"""根拠候補だけを使い、質問の答えを短く返してください。

出力は必ずJSONのみ:
{{"answer":"短い回答"}}

ルール:
- 計算が必要なら計算する。
- 座標、セル値、条件、列名、ページ、金額、IDを省略しない。
- わかりません、情報不足、確認できません、などの不明回答は禁止。
- answerは320文字以内。

質問:
{question}

根拠候補:
{context}
"""


def call_openrouter(model: str, api_key: str, question: str, context: str, max_tokens: int, timeout: int) -> tuple[str, dict[str, Any]]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "短いJSONだけを返す日本語QAエンジンです。"},
            {"role": "user", "content": build_prompt(question, context)},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning": {"enabled": True},
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.local/agentic-rag-eda044",
            "X-Title": "SIGNATE Agentic RAG EDA044",
        },
        method="POST",
    )
    meta: dict[str, Any] = {"model": model, "status": "", "finish_reason": "", "content_length": 0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "raw": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        meta["raw"] = payload
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {}) or {}
        usage = payload.get("usage", {}) or {}
        details = usage.get("completion_tokens_details", {}) or {}
        content = normalize_text(message.get("content", ""))
        meta["status"] = "http_200"
        meta["finish_reason"] = choice.get("finish_reason", "")
        meta["content_length"] = len(content)
        meta["prompt_tokens"] = int(usage.get("prompt_tokens", 0) or 0)
        meta["completion_tokens"] = int(usage.get("completion_tokens", 0) or 0)
        meta["reasoning_tokens"] = int(details.get("reasoning_tokens", 0) or 0)
        return parse_json_answer(content), meta
    except urllib.error.HTTPError as exc:
        meta["status"] = f"http_{exc.code}"
        meta["raw"] = {"error_body": exc.read().decode("utf-8", errors="replace")[:1000]}
        return "", meta
    except Exception as exc:
        meta["status"] = f"error:{type(exc).__name__}"
        meta["raw"] = {"error": str(exc)}
        return "", meta


def write_raw_response(index: int, meta: dict[str, Any]) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"index_{index:03d}.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return relative(path)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda044"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, attempt_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[result_df["answer_before_eda044"].eq(UNKNOWN) & result_df["answer_after_eda044"].ne(UNKNOWN)]
    route_summary = attempt_df.groupby(["route", "subtype", "status"], as_index=False).agg(count=("index", "count"), adopted=("adopted_by_eda044", "sum"))
    view = attempt_df[["index", "route", "subtype", "question", "local_answer", "llm_answer", "answer_after_eda044", "adopted_by_eda044", "method", "status", "finish_reason", "used_paths"]]
    report = f"""# EDA044: format/table/image routeの一括処理

## 背景と目的

EDA043後に残った `format_extraction`、`table_calculation`、`image_ocr` をまとめて処理した。
書式はExcel/PPTX/DOCXのstructure JSON、表計算はCSV/Markdown、画像系は画像周辺メタデータと元データを候補文脈として使った。

## 結果

- 入力: `{relative(INPUT_RESULT)}`
- 対象件数: {len(attempt_df)}
- EDA043時点の非 `わかりません`: {int((result_df["answer_before_eda044"] != UNKNOWN).sum())}
- EDA044で追加採用した件数: {len(improved)}
- EDA044後の非 `わかりません`: {int((result_df["answer_after_eda044"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## route別集計

凡例: `route` は質問ルート、`subtype` は処理サブタイプ、`status` はローカルまたはAPI状態、`count` は件数、`adopted` は提出回答に採用した件数を表す。

{route_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `local_answer` はローカル計算回答、`llm_answer` はOpenRouter回答、`used_paths` は根拠ファイルを表す。

{view.to_markdown(index=False)}
"""
    (OUT_DIR / "eda044_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    api_key = read_openrouter_key()
    if not api_key:
        raise RuntimeError("OpenRouter API key was not found")

    base_df = pd.read_csv(INPUT_RESULT)
    target_routes = {"format_extraction", "table_calculation", "image_ocr"}
    target_df = base_df[base_df["answer_after_eda043"].eq(UNKNOWN) & base_df["route"].isin(target_routes)].copy()
    answer_map = {int(row["index"]): compact_answer(row.get("answer_after_eda043", "")) for _, row in base_df.iterrows()}
    attempt_rows: list[dict[str, Any]] = []

    for _, row in target_df.sort_values("index").iterrows():
        index = int(row["index"])
        route = normalize_text(row.get("route", ""))
        subtype = normalize_text(row.get("subtype", ""))
        question = normalize_text(row.get("question", ""))
        loc_answer, loc_method, loc_sources, loc_evidence = local_answer(index, question)
        context, sources, context_status = candidate_context(index, question, route)
        sources = list(dict.fromkeys(loc_sources + sources))
        llm_answer = ""
        status = "local_answer" if acceptable_answer(loc_answer) else context_status
        finish_reason = ""
        raw_path = ""
        method = loc_method
        if not acceptable_answer(loc_answer) and context:
            for model in args.models:
                candidate, meta = call_openrouter(model, api_key, question, context, args.max_tokens, args.timeout_sec)
                raw_path = write_raw_response(index, meta)
                status = meta.get("status", "")
                finish_reason = meta.get("finish_reason", "")
                if acceptable_answer(candidate):
                    llm_answer = candidate
                    method = "openrouter_compressed_candidate"
                    break
                time.sleep(args.sleep_sec)
        candidate_answer = loc_answer if acceptable_answer(loc_answer) else llm_answer
        adopted = acceptable_answer(candidate_answer)
        if adopted:
            answer_map[index] = candidate_answer
        attempt_rows.append(
            {
                "index": index,
                "route": route,
                "subtype": subtype,
                "question": question,
                "local_answer": loc_answer,
                "llm_answer": llm_answer,
                "answer_after_eda044": answer_map.get(index, UNKNOWN),
                "adopted_by_eda044": adopted,
                "method": method,
                "status": status,
                "finish_reason": finish_reason,
                "used_paths": " | ".join(sources[:12]),
                "evidence": (loc_evidence + "\n" + context)[:12000],
                "raw_response_path": raw_path,
            }
        )

    output_rows: list[dict[str, Any]] = []
    for _, row in base_df.sort_values("index").iterrows():
        before = compact_answer(row.get("answer_after_eda043", ""))
        if not before:
            before = UNKNOWN
        after = answer_map.get(int(row["index"]), before)
        out = row.to_dict()
        out["answer_before_eda044"] = before
        out["answer_after_eda044"] = after
        out["improved_by_eda044"] = before == UNKNOWN and after != UNKNOWN
        output_rows.append(out)

    result_df = pd.DataFrame(output_rows)
    attempt_df = pd.DataFrame(attempt_rows)
    result_df.to_csv(TABLE_DIR / "test_format_table_image_result.csv", index=False, encoding="utf-8-sig")
    attempt_df.to_csv(TABLE_DIR / "test_format_table_image_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, attempt_df, args)
    manifest = {
        "eda": "EDA044",
        "input": relative(INPUT_RESULT),
        "target_count": int(len(attempt_df)),
        "before_non_unknown_count": int((result_df["answer_before_eda044"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved_by_eda044"].sum()),
        "after_non_unknown_count": int((result_df["answer_after_eda044"] != UNKNOWN).sum()),
        "outputs": [
            relative(TABLE_DIR / "test_format_table_image_result.csv"),
            relative(TABLE_DIR / "test_format_table_image_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda044_report.md"),
            relative(RAW_DIR),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
