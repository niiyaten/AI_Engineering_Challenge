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
RAW_DIR = OUT_DIR / "raw_responses"
PRED_DIR = OUT_DIR / "predictions"
INPUT_RESULT = BASE_DIR / "EDA" / "EDA041" / "tables" / "test_document_search_route_result.csv"
INPUT_ATTEMPT = BASE_DIR / "EDA" / "EDA041" / "tables" / "test_document_search_route_attempt_log.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda042_document_retry_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = [
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]


def normalize_text(value: object) -> str:
    """回答整形とログ判定のため、欠損と表記揺れを吸収する。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出回答からHTMLやMarkdown記号、余分な改行を除く。"""
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


def acceptable_answer(answer: str) -> bool:
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 320:
        return False
    bad_markers = [
        "color=",
        "</span>",
        "```",
        "申し訳",
        "根拠文脈",
        "json",
        "情報不足",
        "情報が不足",
        "見つかりません",
        "確認できません",
        "不足しています",
    ]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def parse_json_answer(content: str) -> str:
    """JSON形式で返った回答からanswerだけを取り出す。"""
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


def build_prompt(question: str, contexts: str) -> str:
    """空contentを避けるため、JSONでanswerだけを返す指示にする。"""
    return f"""以下の根拠だけを使って質問に答えてください。

必ず次のJSONだけを返してください。説明文やMarkdownは不要です。
{{"answer":"ここに短い回答"}}

制約:
- 根拠が薄い場合でも "わかりません" は使わない。
- 数値、氏名、ID、ページ番号、金額、日付は根拠の表記を優先する。
- 計算が必要なら計算する。
- answerは320文字以内にする。

質問:
{question}

根拠:
{contexts[:18000]}
"""


def call_openrouter(
    model: str,
    api_key: str,
    question: str,
    contexts: str,
    max_tokens: int,
    timeout: int,
    reasoning_disabled: bool,
) -> tuple[str, dict[str, Any]]:
    """OpenRouterへ再試行し、raw response診断に必要な情報を返す。"""
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "JSONだけを返す日本語QAエンジンです。"},
            {"role": "user", "content": build_prompt(question, contexts)},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if reasoning_disabled:
        body["reasoning"] = {"enabled": False}
    else:
        body["reasoning"] = {"enabled": True}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.local/agentic-rag-eda042",
            "X-Title": "SIGNATE Agentic RAG EDA042",
        },
        method="POST",
    )
    meta: dict[str, Any] = {
        "model": model,
        "status": "",
        "finish_reason": "",
        "message_keys": [],
        "content_length": 0,
        "reasoning_present": False,
        "raw": None,
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_text = resp.read().decode("utf-8", errors="replace")
        payload = json.loads(raw_text)
        meta["raw"] = payload
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {}) or {}
        content = normalize_text(message.get("content", ""))
        meta["status"] = "http_200"
        meta["finish_reason"] = choice.get("finish_reason", "")
        meta["message_keys"] = sorted(message.keys())
        meta["content_length"] = len(content)
        meta["reasoning_present"] = bool(message.get("reasoning") or message.get("reasoning_details"))
        return parse_json_answer(content), meta
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:1000]
        meta["status"] = f"http_{exc.code}"
        meta["raw"] = {"error_body": body_text}
        return "", meta
    except Exception as exc:
        meta["status"] = f"error:{type(exc).__name__}"
        meta["raw"] = {"error": str(exc)}
        return "", meta


def write_raw_response(index: int, attempt_no: int, meta: dict[str, Any]) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"index_{index:03d}_attempt_{attempt_no:02d}.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return relative(path)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda042"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, retry_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[
        result_df["answer_before_eda042"].eq(UNKNOWN)
        & result_df["answer_after_eda042"].ne(UNKNOWN)
    ]
    status_summary = (
        retry_df.groupby(["status", "finish_reason"], as_index=False)
        .agg(count=("index", "count"), adopted=("adopted_by_eda042", "sum"), empty_content=("content_empty", "sum"))
        .sort_values(["adopted", "count"], ascending=[False, False])
    )
    view = retry_df[
        [
            "index",
            "route",
            "subtype",
            "question",
            "answer",
            "adopted_by_eda042",
            "status",
            "finish_reason",
            "content_length",
            "message_keys",
            "reasoning_present",
            "raw_response_path",
        ]
    ]
    report = f"""# EDA042: EDA041空contentの再試行

## 背景と目的

EDA041ではOpenRouter 20Bへの36件の問い合わせがすべてHTTP 200だったが、33件で `content` が空だった。
EDA042では、この33件だけを対象に、`max_tokens` を増やし、JSON回答を強制し、raw responseを保存して原因を確認した。

## 実行条件

- 入力result: `{relative(INPUT_RESULT)}`
- 入力attempt: `{relative(INPUT_ATTEMPT)}`
- 対象: EDA041で非採用、かつ `llm_answer` が空の行
- モデル候補: `{", ".join(args.models)}`
- max_tokens: {args.max_tokens}
- reasoning disabled: {args.disable_reasoning}

## 結果

- test件数: {len(result_df)}
- EDA041時点の非 `わかりません`: {int((result_df["answer_before_eda042"] != UNKNOWN).sum())}
- EDA042対象件数: {int(len(retry_df))}
- EDA042で追加採用した件数: {int(len(improved))}
- EDA042後の非 `わかりません`: {int((result_df["answer_after_eda042"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## status別集計

凡例: `status` はHTTP/API状態、`finish_reason` はOpenRouter応答の終了理由、`count` は試行件数、`adopted` は提出回答に採用した件数、`empty_content` はcontentが空だった件数を表す。

{status_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `answer` は再試行で得た回答、`message_keys` はOpenRouterのmessageに含まれるキー、`reasoning_present` はreasoning系フィールド有無、`raw_response_path` はraw response保存先を表す。

{view.to_markdown(index=False)}

## 注意点

raw responseはAPI診断用であり、提出には `answer_after_eda042` のみを使う。
JSON強制とtoken増量で改善するか、または無料モデル側のcontent生成制限が残るかを確認する目的のEDAである。
"""
    (OUT_DIR / "eda042_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    parser.add_argument("--disable-reasoning", action="store_true", default=False)
    parser.add_argument("--target-limit", type=int, default=0)
    parser.add_argument("--reuse-existing", action="store_true", help="既存のretry logを使い、APIを呼ばず採用判定だけ再計算する")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api_key = read_openrouter_key()
    if not api_key and not args.reuse_existing:
        raise RuntimeError("OpenRouter API key was not found in .apikey or environment")

    result_df = pd.read_csv(INPUT_RESULT)
    attempt_df = pd.read_csv(INPUT_ATTEMPT)
    empty_attempt = attempt_df[
        attempt_df["adopted_by_eda041"].eq(False)
        & attempt_df["llm_answer"].fillna("").astype(str).str.strip().eq("")
    ].copy()
    if args.target_limit > 0:
        empty_attempt = empty_attempt.head(args.target_limit)

    answer_map = {
        int(row["index"]): compact_answer(row.get("answer_after_eda041", ""))
        for _, row in result_df.iterrows()
    }
    retry_rows: list[dict[str, Any]] = []
    existing_retry_path = TABLE_DIR / "test_document_retry_attempt_log.csv"
    if args.reuse_existing and existing_retry_path.exists():
        existing_retry = pd.read_csv(existing_retry_path)
        if args.target_limit > 0:
            existing_retry = existing_retry.head(args.target_limit)
        for _, row in existing_retry.iterrows():
            index = int(row["index"])
            answer = compact_answer(row.get("answer", ""))
            adopted = acceptable_answer(answer)
            if adopted:
                answer_map[index] = answer
            retry_row = row.to_dict()
            retry_row["answer"] = answer
            retry_row["adopted_by_eda042"] = adopted
            retry_row["content_empty"] = int(not bool(int(row.get("content_length", 0) or 0)))
            retry_rows.append(retry_row)
    else:
        for _, row in empty_attempt.sort_values("index").iterrows():
            index = int(row["index"])
            contexts = normalize_text(row.get("contexts", ""))
            answer = ""
            chosen_meta: dict[str, Any] | None = None
            raw_paths: list[str] = []
            attempt_no = 0
            for model in args.models:
                attempt_no += 1
                candidate, meta = call_openrouter(
                    model=model,
                    api_key=api_key,
                    question=normalize_text(row.get("question", "")),
                    contexts=contexts,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout_sec,
                    reasoning_disabled=args.disable_reasoning,
                )
                raw_paths.append(write_raw_response(index, attempt_no, meta))
                if chosen_meta is None or meta.get("status") == "http_200":
                    chosen_meta = meta
                if acceptable_answer(candidate):
                    answer = candidate
                    chosen_meta = meta
                    break
                time.sleep(args.sleep_sec)
            if chosen_meta is None:
                chosen_meta = {"status": "not_attempted", "finish_reason": "", "message_keys": [], "content_length": 0, "reasoning_present": False}
            adopted = acceptable_answer(answer)
            if adopted:
                answer_map[index] = answer
            retry_rows.append(
                {
                    "index": index,
                    "route": row.get("route", ""),
                    "subtype": row.get("subtype", ""),
                    "question": row.get("question", ""),
                    "answer": answer,
                    "adopted_by_eda042": adopted,
                    "status": chosen_meta.get("status", ""),
                    "finish_reason": chosen_meta.get("finish_reason", ""),
                    "message_keys": json.dumps(chosen_meta.get("message_keys", []), ensure_ascii=False),
                    "content_length": int(chosen_meta.get("content_length", 0) or 0),
                    "content_empty": int(not bool(chosen_meta.get("content_length", 0))),
                    "reasoning_present": bool(chosen_meta.get("reasoning_present", False)),
                    "model_used": chosen_meta.get("model", ""),
                    "raw_response_path": " | ".join(raw_paths),
                    "context_count": row.get("context_count", 0),
                }
            )

    output_rows: list[dict[str, Any]] = []
    for _, row in result_df.sort_values("index").iterrows():
        before = compact_answer(row.get("answer_after_eda041", ""))
        if not before:
            before = UNKNOWN
        after = answer_map.get(int(row["index"]), before)
        out = row.to_dict()
        out["answer_before_eda042"] = before
        out["answer_after_eda042"] = after
        out["improved_by_eda042"] = before == UNKNOWN and after != UNKNOWN
        output_rows.append(out)

    out_df = pd.DataFrame(output_rows)
    retry_df = pd.DataFrame(retry_rows)
    if retry_df.empty:
        retry_df = pd.DataFrame(
            columns=[
                "index",
                "route",
                "subtype",
                "question",
                "answer",
                "adopted_by_eda042",
                "status",
                "finish_reason",
                "message_keys",
                "content_length",
                "content_empty",
                "reasoning_present",
                "model_used",
                "raw_response_path",
                "context_count",
            ]
        )
    out_df.to_csv(TABLE_DIR / "test_document_retry_result.csv", index=False, encoding="utf-8-sig")
    retry_df.to_csv(TABLE_DIR / "test_document_retry_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(out_df)
    write_report(out_df, retry_df, args)
    manifest = {
        "eda": "EDA042",
        "input_result": relative(INPUT_RESULT),
        "input_attempt": relative(INPUT_ATTEMPT),
        "target_count": int(len(retry_df)),
        "before_non_unknown_count": int((out_df["answer_before_eda042"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(out_df["improved_by_eda042"].sum()),
        "after_non_unknown_count": int((out_df["answer_after_eda042"] != UNKNOWN).sum()),
        "outputs": [
            relative(TABLE_DIR / "test_document_retry_result.csv"),
            relative(TABLE_DIR / "test_document_retry_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda042_report.md"),
            relative(RAW_DIR),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
