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

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
INPUT_LOG = BASE_DIR / "EDA" / "EDA038" / "tables" / "test_diff_route_result.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda039_format_route_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = [
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]

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
    """検索用に、欠損と全半角の差を吸収する。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出回答に不要なタグや改行を入れないための整形を行う。"""
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def project_keywords(question: str) -> list[str]:
    q = normalize_text(question)
    for keys in PROJECT_ALIASES.values():
        if any(key in q for key in keys):
            return keys
    return []


def find_paths(*keywords: str, suffix: str | None = None) -> list[Path]:
    """processed配下から、パスに指定キーワードをすべて含むファイルを探す。"""
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


def column_to_number(column: str) -> int:
    """Excel座標の列記号を1始まりの列番号へ変換する。"""
    number = 0
    for char in column.upper():
        if "A" <= char <= "Z":
            number = number * 26 + ord(char) - ord("A") + 1
    return number


def coordinate_to_row_col(coordinate: str) -> tuple[int, int]:
    match = re.match(r"([A-Z]+)(\d+)", coordinate.upper())
    if not match:
        return (0, 0)
    return (int(match.group(2)), column_to_number(match.group(1)))


def read_sheet_df(sheet: dict[str, Any]) -> pd.DataFrame | None:
    csv_path = Path(sheet.get("exported_csv_path", ""))
    if not csv_path.exists():
        return None
    try:
        return pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    except Exception:
        return None


def row_context(df: pd.DataFrame, row_num: int, col_num: int, max_fields: int = 10) -> str:
    """書式付きセルの周辺行から、値の意味を推測しやすい短い文脈を作る。"""
    if row_num <= 1 or row_num - 2 >= len(df) or col_num <= 0 or col_num - 1 >= len(df.columns):
        return ""
    series = df.iloc[row_num - 2]
    fields: list[str] = []
    for col, value in series.items():
        value_text = compact_answer(value)
        if value_text and len(fields) < max_fields:
            fields.append(f"{col}={value_text}")
    return "、".join(fields)


def target_structure_paths(question: str) -> list[Path]:
    """質問文のプロジェクト名とファイル名ヒントから、構造JSONを絞り込む。"""
    keys = project_keywords(question)
    q = normalize_text(question)
    file_hints: list[str] = []
    for hint in ["train.xlsx", "基礎分析.pptx", "基礎分析.docx", "報告資料", "最終報告", "train"]:
        if hint in q:
            file_hints.append(hint)
    suffixes = [".structure.json"]
    paths: list[Path] = []
    for key in keys[:1] or [""]:
        if file_hints:
            for hint in file_hints:
                paths.extend(find_paths(key, hint, suffix=suffixes[0]))
        else:
            paths.extend(find_paths(key, suffix=suffixes[0]))
    return list(dict.fromkeys(paths))


def extract_xlsx_format_records(path: Path, question: str) -> list[str]:
    """Excelのstyled_cellsから、黄色セルや書式付きセルの座標・値・行文脈を抽出する。"""
    obj = load_json(path)
    q = normalize_text(question)
    sheet_hint = re.search(r"Sheet\d+", q)
    yellow_colors = {"FFFFFF00", "FFFFEB9C", "FFFFF2CC", "FFFFFF99"}
    records: list[str] = []
    for sheet in obj.get("sheets", []):
        sheet_name = normalize_text(sheet.get("sheet_name", ""))
        if sheet_hint and sheet_name != sheet_hint.group(0):
            continue
        df = read_sheet_df(sheet)
        for cell in sheet.get("styled_cells", []):
            fill = normalize_text(cell.get("fill_color", "")).upper()
            number_format = normalize_text(cell.get("number_format", ""))
            is_yellow = fill in yellow_colors
            is_red_format = "[RED]" in number_format.upper() or "RED" in number_format.upper()
            has_font_style = bool(cell.get("bold") or cell.get("italic") or cell.get("underline") or cell.get("font_color"))
            if "黄色" in q or "ハイライト" in q:
                if not is_yellow:
                    continue
            elif "RED" in q.upper() or "赤" in q:
                if not is_red_format:
                    continue
            elif not (is_yellow or is_red_format or has_font_style):
                continue
            row_num, col_num = coordinate_to_row_col(normalize_text(cell.get("coordinate", "")))
            value = ""
            context = ""
            if df is not None and row_num > 1 and row_num - 2 < len(df) and col_num - 1 < len(df.columns):
                value = compact_answer(df.iloc[row_num - 2, col_num - 1])
                context = row_context(df, row_num, col_num)
            records.append(
                f"{relative(path)} | sheet={sheet_name} | cell={cell.get('coordinate')} | value={value} | "
                f"fill={fill} | number_format={number_format} | bold={cell.get('bold')} | "
                f"italic={cell.get('italic')} | underline={cell.get('underline')} | row={context}"
            )
    return records


def extract_pptx_docx_format_records(path: Path, question: str) -> list[str]:
    """PowerPoint/Word構造JSONから、太字、下線、イタリック、色付きrunを抽出する。"""
    obj = load_json(path)
    q = normalize_text(question)
    want_bold = "太字" in q
    want_underline = "下線" in q
    want_italic = "イタリック" in q
    records: list[str] = []

    def keep_run(run: dict[str, Any]) -> bool:
        if want_bold and not run.get("bold"):
            return False
        if want_underline and not run.get("underline"):
            return False
        if want_italic and not run.get("italic"):
            return False
        if "黄色" in q or "ハイライト" in q:
            color_text = normalize_text(run.get("highlight_color", "")) + normalize_text(run.get("font_color", ""))
            if "FFFF" not in color_text.upper() and "YELLOW" not in color_text.upper():
                return False
        return bool(run.get("bold") or run.get("underline") or run.get("italic") or run.get("font_color") or run.get("highlight_color"))

    if obj.get("file_type") == "pptx":
        for slide in obj.get("slides", []):
            for shape in slide.get("shapes", []):
                text_frame = shape.get("text_frame") or {}
                for paragraph in text_frame.get("paragraphs", []):
                    for run in paragraph.get("runs", []):
                        text = compact_answer(run.get("text", ""))
                        if text and keep_run(run):
                            records.append(
                                f"{relative(path)} | slide={slide.get('slide_number')} | text={text} | "
                                f"paragraph={compact_answer(paragraph.get('text',''))} | "
                                f"bold={run.get('bold')} | italic={run.get('italic')} | underline={run.get('underline')} | "
                                f"font_color={run.get('font_color','')}"
                            )
    else:
        for para_idx, paragraph in enumerate(obj.get("paragraphs", []), start=1):
            for run in paragraph.get("runs", []):
                text = compact_answer(run.get("text", ""))
                if text and keep_run(run):
                    records.append(
                        f"{relative(path)} | paragraph={para_idx} | text={text} | "
                        f"paragraph_text={compact_answer(paragraph.get('text',''))} | "
                        f"bold={run.get('bold')} | italic={run.get('italic')} | underline={run.get('underline')} | "
                        f"font_color={run.get('font_color','')} | highlight={run.get('highlight_color','')}"
                    )
    return records


def build_format_records(question: str) -> tuple[list[str], list[str]]:
    paths = target_structure_paths(question)
    records: list[str] = []
    used_paths: list[str] = []
    for path in paths:
        try:
            obj = load_json(path)
            file_type = normalize_text(obj.get("file_type", ""))
            if file_type == "xlsx":
                extracted = extract_xlsx_format_records(path, question)
            elif file_type in {"pptx", "docx"}:
                extracted = extract_pptx_docx_format_records(path, question)
            else:
                extracted = []
        except Exception as exc:
            extracted = [f"{relative(path)} | extraction_error={type(exc).__name__}:{exc}"]
        if extracted:
            records.extend(extracted)
            used_paths.append(relative(path))
    return records[:80], used_paths


def read_openrouter_key() -> str:
    """プロジェクトローカルの.apikeyからOpenRouterキーを読む。"""
    key_file = BASE_DIR / ".apikey"
    if not key_file.exists():
        return os.environ.get("OPENROUTER_API_KEY", "")
    for raw in key_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip().lower() in {"openrouter", "openrouter_api_key"}:
            return value.strip().strip('"').strip("'")
    return os.environ.get("OPENROUTER_API_KEY", "")


def call_openrouter(model: str, api_key: str, question: str, records: list[str], max_tokens: int, timeout: int) -> tuple[str, str]:
    """書式抽出レコードを使い、質問に対する短い最終回答を生成する。"""
    prompt = f"""次の質問に、根拠レコードだけを使って日本語で短く答えてください。

制約:
- HTMLタグやMarkdown表は出さない。
- 座標、値、条件、集計対象が問われている場合は省略しない。
- 根拠が薄い場合でも「わかりません」と書かず、最も妥当な候補を答える。
- 余談は書かない。

質問:
{question}

書式抽出レコード:
{chr(10).join(records[:60])}
"""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "根拠に忠実な短い回答だけを返してください。"},
            {"role": "user", "content": prompt},
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
            "HTTP-Referer": "https://signate.local/agentic-rag-eda039",
            "X-Title": "SIGNATE Agentic RAG EDA039",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        message = payload.get("choices", [{}])[0].get("message", {})
        return compact_answer(message.get("content", "")), "http_200"
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:500]
        return "", f"http_{exc.code}:{body_text}"
    except Exception as exc:
        return "", f"error:{type(exc).__name__}:{exc}"


def acceptable_answer(answer: str) -> bool:
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 300:
        return False
    bad_markers = ["color=", "</span>", "```", "申し訳", "根拠レコード"]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda039"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, target_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[
        result_df["answer_before_eda039"].eq(UNKNOWN)
        & result_df["answer_after_eda039"].ne(UNKNOWN)
    ]
    status_summary = (
        target_df.groupby(["status"], as_index=False)
        .agg(count=("index", "count"), adopted=("adopted_by_eda039", "sum"))
        .sort_values(["adopted", "count"], ascending=[False, False])
    )
    view = target_df[
        [
            "index",
            "route",
            "subtype",
            "question",
            "answer_before_eda039",
            "llm_answer",
            "answer_after_eda039",
            "adopted_by_eda039",
            "record_count",
            "used_paths",
            "status",
        ]
    ]
    report = f"""# EDA039: 書式抽出routeの個別処理

## 背景と目的

EDA038後も、黄色ハイライト、太字、下線、イタリックなどの書式を根拠にする質問が残った。
通常の本文検索では、セル色や文字装飾の情報が失われるため、Markdown本文だけでは回答しにくい。

EDA039では、`*.structure.json` に保存した書式メタデータを直接読み、質問に関係するExcel/PowerPoint/Wordの書式レコードを作成した。
そのレコードをOpenRouterの20b系モデルへ渡し、提出用の短い回答へ整形した。

## 実行条件

- 入力: `{relative(INPUT_LOG)}`
- OpenRouter使用: `{not args.skip_llm}`
- モデル候補: `{", ".join(args.models)}`
- 対象: `format_extraction` route、`xlsx_yellow_cell_context` subtype、`format_metadata` subtype

## 結果

- test件数: {len(result_df)}
- EDA038時点の非 `わかりません`: {int((result_df["answer_before_eda039"] != UNKNOWN).sum())}
- EDA039対象件数: {len(target_df)}
- EDA039で追加採用した件数: {len(improved)}
- EDA039後の非 `わかりません`: {int((result_df["answer_after_eda039"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## status別集計

凡例: `status` はAPIまたは抽出状態、`count` は件数、`adopted` は提出回答へ採用した件数を表す。

{status_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `record_count` は書式抽出レコード数、`used_paths` は根拠ファイル、`llm_answer` はOpenRouterの整形回答を表す。

{view.to_markdown(index=False)}

## 注意点

Excelのセル色は比較的安定して抽出できる。
一方で、PowerPointやWord内の図として埋め込まれた黄色ハイライトは、構造JSONに書式として残らないことがある。
その場合は、画像OCRまたは図表抽出routeとして別に扱う必要がある。
"""
    (OUT_DIR / "eda039_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    base_df = pd.read_csv(INPUT_LOG)
    api_key = "" if args.skip_llm else read_openrouter_key()

    result_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    for _, row in base_df.sort_values("index").iterrows():
        answer_before = compact_answer(row.get("answer_after_eda038", ""))
        if not answer_before:
            answer_before = UNKNOWN
        route = normalize_text(row.get("route", ""))
        subtype = normalize_text(row.get("subtype", ""))
        question = normalize_text(row.get("question", ""))
        is_target = route == "format_extraction" or subtype in {"xlsx_yellow_cell_context", "format_metadata"}
        final_answer = answer_before

        if is_target and answer_before == UNKNOWN:
            records, used_paths = build_format_records(question)
            llm_answer = ""
            model_used = ""
            status = "no_format_records" if not records else "local_records"
            if records and not args.skip_llm and api_key:
                for model in args.models:
                    llm_answer, status = call_openrouter(model, api_key, question, records, args.max_tokens, args.timeout_sec)
                    model_used = model
                    if status == "http_200" and acceptable_answer(llm_answer):
                        break
                    time.sleep(args.sleep_sec)
            elif records and not api_key and not args.skip_llm:
                status = "missing_openrouter_key"
            adopted = acceptable_answer(llm_answer)
            if adopted:
                final_answer = llm_answer
            target_rows.append(
                {
                    "index": int(row["index"]),
                    "route": route,
                    "subtype": subtype,
                    "question": question,
                    "answer_before_eda039": answer_before,
                    "llm_answer": llm_answer,
                    "answer_after_eda039": final_answer,
                    "adopted_by_eda039": adopted,
                    "record_count": len(records),
                    "used_paths": " | ".join(used_paths),
                    "status": status,
                    "model_used": model_used,
                    "records": "\n".join(records[:80]),
                }
            )

        result_row = row.to_dict()
        result_row["answer_before_eda039"] = answer_before
        result_row["answer_after_eda039"] = final_answer
        result_row["improved_by_eda039"] = answer_before == UNKNOWN and final_answer != UNKNOWN
        result_rows.append(result_row)

    result_df = pd.DataFrame(result_rows)
    target_df = pd.DataFrame(target_rows)
    if target_df.empty:
        target_df = pd.DataFrame(
            columns=[
                "index",
                "route",
                "subtype",
                "question",
                "answer_before_eda039",
                "llm_answer",
                "answer_after_eda039",
                "adopted_by_eda039",
                "record_count",
                "used_paths",
                "status",
                "model_used",
                "records",
            ]
        )
    result_df.to_csv(TABLE_DIR / "test_format_route_result.csv", index=False, encoding="utf-8-sig")
    target_df.to_csv(TABLE_DIR / "test_format_route_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, target_df, args)
    manifest = {
        "eda": "EDA039",
        "input": relative(INPUT_LOG),
        "target_count": int(len(target_df)),
        "before_non_unknown_count": int((result_df["answer_before_eda039"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved_by_eda039"].sum()),
        "after_non_unknown_count": int((result_df["answer_after_eda039"] != UNKNOWN).sum()),
        "openrouter_used": bool(not args.skip_llm),
        "outputs": [
            relative(TABLE_DIR / "test_format_route_result.csv"),
            relative(TABLE_DIR / "test_format_route_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda039_report.md"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
