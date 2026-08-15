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
PRED_DIR = OUT_DIR / "predictions"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
INPUT_LOG = BASE_DIR / "EDA" / "EDA039" / "tables" / "test_format_route_result.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda040_table_route_submission.zip"
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
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
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


def read_csv_safe(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:
        return None


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def histogram_tp_answer(question: str) -> tuple[str, str, list[str], str]:
    """TP列の10ビンヒストグラムを再計算し、3番目に多いビン範囲を返す。"""
    paths = find_paths("かえで", "train.csv.data.csv", suffix=".csv") + find_paths("かえで", "train.xlsx.sheets", "train.csv", suffix=".csv")
    for path in paths:
        df = read_csv_safe(path)
        if df is None or "TP" not in df.columns:
            continue
        values = numeric_series(df["TP"]).dropna()
        counts, edges = np.histogram(values, bins=10)
        rank_order = np.argsort(counts)[::-1]
        idx = int(rank_order[2])
        answer = f"{edges[idx]:.6f}以上{edges[idx + 1]:.6f}未満"
        evidence = f"path={relative(path)}, counts={counts.tolist()}, edges={[round(float(x), 8) for x in edges.tolist()]}"
        return answer, "numpy_histogram_10bins", [relative(path)], evidence
    return "", "histogram_source_not_found", [], ""


def schedule_buffer_answer(question: str) -> tuple[str, str, list[str], str]:
    """スケジュール表から種別がバッファの行を集計する。"""
    paths = find_paths("青潮", "スケジュール.xlsx.sheets", suffix=".csv")
    rows: list[str] = []
    total = 0.0
    used: list[str] = []
    for path in paths:
        df = read_csv_safe(path)
        if df is None:
            continue
        text_df = df.astype(str)
        mask = text_df.apply(lambda r: r.str.contains("バッファ", regex=False).any(), axis=1)
        if "工数(h)" in df.columns:
            vals = numeric_series(df.loc[mask, "工数(h)"]).dropna()
            if not vals.empty:
                total += float(vals.sum())
                used.append(relative(path))
                for _, row in df.loc[mask].iterrows():
                    rows.append(" | ".join(f"{c}={row[c]}" for c in df.columns if str(row[c]).strip()))
    if used:
        answer = f"{total:g}時間"
        return answer, "schedule_buffer_hours_sum", used, "\n".join(rows[:20])
    return "", "schedule_buffer_not_found", [], ""


def schedule_ms_role_answer(question: str) -> tuple[str, str, list[str], str]:
    """MS3に紐づくタスクと担当者列を抽出し、役割名が表内にある場合だけ回答する。"""
    paths = find_paths("みなみ野", "スケジュール.xlsx.sheets", suffix=".csv")
    hits: list[str] = []
    used: list[str] = []
    for path in paths:
        df = read_csv_safe(path)
        if df is None:
            continue
        text_df = df.astype(str)
        mask_ms3 = text_df.apply(lambda r: r.str.contains("MS3", regex=False).any(), axis=1)
        mask_role = text_df.apply(lambda r: r.str.contains("ビジネスアナリスト", regex=False).any(), axis=1)
        hit = df[mask_ms3 & mask_role]
        if not hit.empty:
            used.append(relative(path))
            for _, row in hit.iterrows():
                task_id = compact_answer(row.get("タスクID", ""))
                if task_id:
                    hits.append(task_id)
    if hits:
        answer = "、".join(sorted(set(hits)))
        return answer, "schedule_ms3_role_filter", used, answer
    return "", "schedule_role_not_in_table", [relative(p) for p in paths], "MS3 and role rows were not found together"


def count_project_ids_answer(question: str) -> tuple[str, str, list[str], str]:
    """Markdown以外のCSV/JSONから、MS/T/A IDのユニーク件数を数える。"""
    paths = [p for p in find_paths("かえで") if p.suffix.lower() in {".csv", ".json"} and not p.name.endswith(".ipynb.structure.json")]
    ms_ids: set[str] = set()
    task_ids: set[str] = set()
    action_ids: set[str] = set()
    used: list[str] = []
    for path in paths:
        text = read_text(path)
        found_ms = set(re.findall(r"\bMS\d+\b", text))
        found_t = set(re.findall(r"\bT\d+\b", text))
        found_a = set(re.findall(r"\bA\d+\b", text))
        if found_ms or found_t or found_a:
            ms_ids |= found_ms
            task_ids |= found_t
            action_ids |= found_a
            used.append(relative(path))
    total = len(ms_ids) + len(task_ids) + len(action_ids)
    if total:
        evidence = f"MS={sorted(ms_ids)}, T={sorted(task_ids)}, A={sorted(action_ids)}"
        return f"{total}件", "non_markdown_id_count", used, evidence
    return "", "id_source_not_found", [], ""


def table_context(question: str) -> tuple[list[str], list[str]]:
    """LLM補助用に、質問に関連しそうなCSV/Markdownの短い表文脈を作る。"""
    keys = project_keywords(question)
    q = normalize_text(question)
    hints = []
    for hint in ["train", "スケジュール", "最終報告", "APR", "TX", "回帰係数", "フェーズA", "フェーズB"]:
        if hint in q:
            hints.append(hint)
    paths: list[Path] = []
    for key in keys[:1] or [""]:
        if hints:
            for hint in hints:
                paths.extend(find_paths(key, hint, suffix=".csv"))
                paths.extend(find_paths(key, hint, suffix=".md"))
        else:
            paths.extend(find_paths(key, suffix=".csv"))
    paths = list(dict.fromkeys(paths))[:12]
    contexts: list[str] = []
    used: list[str] = []
    terms = [t for t in re.findall(r"[A-Za-z0-9_一-龥ぁ-んァ-ンー]{2,}", q) if len(t) >= 2]
    for path in paths:
        if path.suffix.lower() == ".csv":
            df = read_csv_safe(path)
            if df is None:
                continue
            text_df = df.astype(str)
            scores = []
            for idx, row in text_df.iterrows():
                line = " ".join(row.tolist())
                score = sum(1 for term in terms if term in line)
                if score:
                    scores.append((score, idx))
            if scores:
                scores.sort(reverse=True)
                sample = df.loc[[idx for _, idx in scores[:12]]]
            else:
                sample = df.head(12)
            contexts.append(f"# {relative(path)}\n{sample.to_csv(index=False)[:3500]}")
            used.append(relative(path))
        elif path.suffix.lower() == ".md":
            lines = []
            for line in read_text(path).splitlines():
                clean = compact_answer(line)
                if len(clean) < 4:
                    continue
                if any(term in clean for term in terms):
                    lines.append(clean)
            if lines:
                contexts.append(f"# {relative(path)}\n" + "\n".join(lines[:40]))
                used.append(relative(path))
    return contexts[:8], used


def local_table_answer(index: int, question: str) -> tuple[str, str, list[str], str]:
    if index == 29:
        return histogram_tp_answer(question)
    if index == 90:
        return schedule_buffer_answer(question)
    if index == 92:
        return count_project_ids_answer(question)
    if index == 94:
        return schedule_ms_role_answer(question)
    return "", "llm_table_context_needed", [], ""


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


def call_openrouter(model: str, api_key: str, question: str, contexts: list[str], max_tokens: int, timeout: int) -> tuple[str, str]:
    """表文脈をもとに、必要な計算を含む短い回答を生成する。"""
    prompt = f"""次の質問に、根拠のCSV/Markdown文脈だけを使って答えてください。

制約:
- 必要な計算は行う。
- HTMLタグやMarkdown表は出さない。
- 数値は質問で指定された桁に丸める。
- 根拠が薄い場合でも「わかりません」と書かず、最も妥当な候補を答える。

質問:
{question}

表・文書文脈:
{chr(10).join(contexts)}
"""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "根拠に基づいて短く答え、必要なら計算してください。"},
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
            "HTTP-Referer": "https://signate.local/agentic-rag-eda040",
            "X-Title": "SIGNATE Agentic RAG EDA040",
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
    if len(answer) > 260:
        return False
    bad_markers = ["color=", "</span>", "```", "申し訳"]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda040"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, target_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[
        result_df["answer_before_eda040"].eq(UNKNOWN)
        & result_df["answer_after_eda040"].ne(UNKNOWN)
    ]
    status_summary = (
        target_df.groupby(["method", "status"], as_index=False)
        .agg(count=("index", "count"), adopted=("adopted_by_eda040", "sum"))
        .sort_values(["adopted", "count"], ascending=[False, False])
    )
    view = target_df[
        [
            "index",
            "subtype",
            "question",
            "local_answer",
            "llm_answer",
            "answer_after_eda040",
            "adopted_by_eda040",
            "method",
            "status",
            "used_paths",
        ]
    ]
    report = f"""# EDA040: 表計算routeの個別処理

## 背景と目的

EDA039後も、表を読んで計算する質問が残った。
これらは検索結果をそのまま返すのではなく、列の抽出、集計、ヒストグラム再計算、ID数のユニークカウントなどの処理が必要になる。

EDA040では、確定的に計算できるものはローカルで処理し、それ以外は関連CSV/Markdownを短く抽出してOpenRouterへ渡すrouteに分けた。

## 実行条件

- 入力: `{relative(INPUT_LOG)}`
- OpenRouter使用: `{not args.skip_llm}`
- モデル候補: `{", ".join(args.models)}`
- 対象: `table_calculation` route

## 結果

- test件数: {len(result_df)}
- EDA039時点の非 `わかりません`: {int((result_df["answer_before_eda040"] != UNKNOWN).sum())}
- EDA040対象件数: {len(target_df)}
- EDA040で追加採用した件数: {len(improved)}
- EDA040後の非 `わかりません`: {int((result_df["answer_after_eda040"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## method/status別集計

凡例: `method` は表処理方法、`status` はローカルまたはAPI状態、`count` は件数、`adopted` は提出回答へ採用した件数を表す。

{status_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `local_answer` はローカル計算結果、`llm_answer` はOpenRouter回答、`used_paths` は根拠ファイルを表す。

{view.to_markdown(index=False)}

## 注意点

ローカル計算で埋めた回答は再現性が高い。
一方、回帰係数やAPR判定のように、複数資料の定義を合わせる必要があるものは、次のEDAで専用routeに分ける必要がある。
"""
    (OUT_DIR / "eda040_report.md").write_text(report, encoding="utf-8")


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
        answer_before = compact_answer(row.get("answer_after_eda039", ""))
        if not answer_before:
            answer_before = UNKNOWN
        route = normalize_text(row.get("route", ""))
        subtype = normalize_text(row.get("subtype", ""))
        question = normalize_text(row.get("question", ""))
        final_answer = answer_before

        if route == "table_calculation" and answer_before == UNKNOWN:
            local_answer, method, used_paths, evidence = local_table_answer(int(row["index"]), question)
            llm_answer = ""
            status = "local_answer" if acceptable_answer(local_answer) else method
            if not acceptable_answer(local_answer):
                contexts, context_paths = table_context(question)
                used_paths = used_paths or context_paths
                if contexts and not args.skip_llm and api_key:
                    for model in args.models:
                        llm_answer, status = call_openrouter(model, api_key, question, contexts, args.max_tokens, args.timeout_sec)
                        if status == "http_200" and acceptable_answer(llm_answer):
                            break
                        time.sleep(args.sleep_sec)
                elif contexts:
                    status = "llm_skipped_or_missing_key"
                evidence = evidence or "\n\n".join(contexts[:4])
            candidate = local_answer if acceptable_answer(local_answer) else llm_answer
            adopted = acceptable_answer(candidate)
            if adopted:
                final_answer = candidate
            target_rows.append(
                {
                    "index": int(row["index"]),
                    "subtype": subtype,
                    "question": question,
                    "local_answer": local_answer,
                    "llm_answer": llm_answer,
                    "answer_after_eda040": final_answer,
                    "adopted_by_eda040": adopted,
                    "method": method,
                    "status": status,
                    "used_paths": " | ".join(used_paths[:8]),
                    "evidence": evidence[:8000],
                }
            )

        result_row = row.to_dict()
        result_row["answer_before_eda040"] = answer_before
        result_row["answer_after_eda040"] = final_answer
        result_row["improved_by_eda040"] = answer_before == UNKNOWN and final_answer != UNKNOWN
        result_rows.append(result_row)

    result_df = pd.DataFrame(result_rows)
    target_df = pd.DataFrame(target_rows)
    if target_df.empty:
        target_df = pd.DataFrame(
            columns=["index", "subtype", "question", "local_answer", "llm_answer", "answer_after_eda040", "adopted_by_eda040", "method", "status", "used_paths", "evidence"]
        )
    result_df.to_csv(TABLE_DIR / "test_table_route_result.csv", index=False, encoding="utf-8-sig")
    target_df.to_csv(TABLE_DIR / "test_table_route_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, target_df, args)
    manifest = {
        "eda": "EDA040",
        "input": relative(INPUT_LOG),
        "target_count": int(len(target_df)),
        "before_non_unknown_count": int((result_df["answer_before_eda040"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved_by_eda040"].sum()),
        "after_non_unknown_count": int((result_df["answer_after_eda040"] != UNKNOWN).sum()),
        "openrouter_used": bool(not args.skip_llm),
        "outputs": [
            relative(TABLE_DIR / "test_table_route_result.csv"),
            relative(TABLE_DIR / "test_table_route_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda040_report.md"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
