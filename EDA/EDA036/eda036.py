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
PROMPT_DIR = OUT_DIR / "prompts"
PRED_DIR = OUT_DIR / "predictions"

API_KEY_PATH = BASE_DIR / ".apikey"
EDA035_LOG = BASE_DIR / "EDA" / "EDA035" / "tables" / "test_unknown_reduction_log.csv"
EDA035_PRED = BASE_DIR / "EDA" / "EDA035" / "predictions" / "predictions.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda036_openrouter_structured_test_submission.zip"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
UNKNOWN = "わかりません"

DEFAULT_MODELS = [
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
]


def normalize_text(value: object) -> str:
    """検索、比較、ログ出力で表記ゆれが出にくいように文字列を正規化する。"""
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = re.sub(r"<[^>]+>", "", text)
    return text


def compact_answer(value: object) -> str:
    """提出CSVに入れる回答を1行の短い文字列へ整える。"""
    text = normalize_text(value)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"\s*\n\s*", "、", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip(" 、")


def relative(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path)


def parse_models(raw: str) -> list[str]:
    models: list[str] = []
    for item in raw.split(","):
        model = item.strip()
        if model and model not in models:
            models.append(model)
    return models


def read_api_key(provider: str = "OpenRouter") -> str:
    """環境変数または.apikeyからAPIキーを読む。キー本文はログに保存しない。"""
    env_key = os.environ.get(f"{provider.upper()}_API_KEY", "").strip()
    if env_key:
        return env_key
    if not API_KEY_PATH.exists():
        raise FileNotFoundError(f"{relative(API_KEY_PATH)} が見つかりません。")
    wanted = provider.lower()
    for line in API_KEY_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            name, value = stripped.split("=", 1)
        elif ":" in stripped:
            name, value = stripped.split(":", 1)
        else:
            name, value = provider, stripped
        if name.strip().lower() == wanted:
            key = value.strip().strip('"').strip("'")
            if key:
                return key
    raise ValueError(f".apikey に {provider} 用APIキーが見つかりません。")


def load_eda035_predictions() -> pd.DataFrame:
    pred = pd.read_csv(EDA035_PRED, header=None, names=["index", "eda035_answer"])
    pred["index"] = pred["index"].astype(int)
    pred["eda035_answer"] = pred["eda035_answer"].map(compact_answer)
    return pred


def build_context_row(row: pd.Series) -> dict[str, Any]:
    """EDA035の候補と採用回答を、LLMに渡す構造化コンテキストへ変換する。"""
    answer_after = compact_answer(row.get("answer_after", ""))
    candidate = compact_answer(row.get("candidate_answer", ""))
    evidence = normalize_text(row.get("evidence", ""))[:3500]

    # EDA035で採用済みの回答も、LLMに整形確認させるため候補として扱う。
    if not candidate and answer_after and answer_after != UNKNOWN:
        candidate = answer_after

    has_candidate = bool(candidate and candidate != UNKNOWN)
    has_evidence = bool(evidence)
    target_for_llm = has_candidate or has_evidence

    return {
        "index": int(row["index"]),
        "route": normalize_text(row.get("route", "")),
        "question": normalize_text(row.get("question", "")),
        "eda035_answer": answer_after,
        "candidate_answer": candidate,
        "method": normalize_text(row.get("method", "")),
        "confidence": normalize_text(row.get("confidence", "")),
        "subtype": normalize_text(row.get("subtype", "")),
        "needs_review": bool(row.get("needs_review", False)),
        "source_paths": normalize_text(row.get("source_paths", "")),
        "evidence": evidence,
        "target_for_llm": target_for_llm,
    }


def build_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    """構造化候補をOpenRouterへ渡し、短い最終回答だけを返させる。"""
    system = (
        "あなたは社内資料RAGの最終回答を作るアシスタントです。"
        "提示された質問、回答候補、根拠抜粋だけを使ってください。"
        "候補や根拠にない値を外部知識で補わないでください。"
        "回答は最終回答だけにし、説明、根拠番号、ファイルパス、HTMLタグ、Markdown装飾は含めないでください。"
        "候補が十分でない場合だけ「わかりません」と返してください。"
    )
    user = "\n".join(
        [
            "以下の質問に対する提出用の短い最終回答だけを返してください。",
            "",
            f"質問: {row['question']}",
            f"route: {row['route']}",
            f"subtype: {row['subtype']}",
            f"候補生成方法: {row['method']}",
            f"候補信頼度: {row['confidence']}",
            f"needs_review: {row['needs_review']}",
            f"EDA035回答: {row['eda035_answer']}",
            f"回答候補: {row['candidate_answer']}",
            f"参照元: {row['source_paths']}",
            "根拠抜粋:",
            row["evidence"],
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_openrouter(api_key: str, model: str, messages: list[dict[str, str]], args: argparse.Namespace) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    request = urllib.request.Request(
        OPENROUTER_CHAT_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.jp/",
            "X-Title": "SIGNATE Agentic RAG EDA036",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "status": int(response.status), "payload": payload, "elapsed_sec": round(time.time() - started, 3)}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"message": str(exc)}}
        return {"ok": False, "status": int(exc.code), "payload": payload, "elapsed_sec": round(time.time() - started, 3)}
    except Exception as exc:
        return {"ok": False, "status": 0, "payload": {"error": {"message": str(exc)}}, "elapsed_sec": round(time.time() - started, 3)}


def extract_answer(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return compact_answer(content or "")


def safe_error_message(payload: dict[str, Any]) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        msg = error.get("message") or json.dumps(error, ensure_ascii=False)
    else:
        msg = json.dumps(payload, ensure_ascii=False)
    return compact_answer(msg)[:700]


def is_adoptable_llm_answer(answer: str) -> bool:
    """LLM回答を提出候補へ反映してよいか、明らかな崩れだけを除外する。"""
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 220:
        return False
    bad_markers = ["color=", "</span>", "```", "根拠", "ファイル", "質問:"]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def load_cached_attempts() -> dict[int, list[dict[str, Any]]]:
    """タイムアウト後の再集計でAPIを再送しないように、既存attemptログを再利用する。"""
    path = TABLE_DIR / "test_openrouter_structured_attempt_log.csv"
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        df = pd.read_csv(path)
    except Exception:
        return {}
    cached: dict[int, list[dict[str, Any]]] = {}
    for _, row in df.iterrows():
        index = int(row["index"])
        cached.setdefault(index, []).append(
            {
                "index": index,
                "model": normalize_text(row.get("model", "")),
                "status": int(row.get("status", 0) or 0),
                "ok": bool(row.get("ok", False)),
                "elapsed_sec": float(row.get("elapsed_sec", 0) or 0),
                "answer": compact_answer(row.get("answer", "")),
                "error_message": compact_answer(row.get("error_message", "")),
            }
        )
    return cached


def write_submission(result_df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in result_df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["final_answer"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, attempt_df: pd.DataFrame, args: argparse.Namespace, models: list[str]) -> None:
    status_summary = attempt_df.groupby("status", as_index=False).size().rename(columns={"size": "count"}) if not attempt_df.empty else pd.DataFrame()
    model_summary = attempt_df.groupby(["model", "status"], as_index=False).size().rename(columns={"size": "count"}) if not attempt_df.empty else pd.DataFrame()
    route_summary = (
        result_df.groupby("route", as_index=False)
        .agg(
            count=("index", "count"),
            target_count=("target_for_llm", "sum"),
            llm_answer_count=("llm_answer", lambda s: int(s.astype(str).ne("").sum())),
            llm_adopted_count=("llm_adopted", "sum"),
            final_non_unknown=("final_answer", lambda s: int(s.astype(str).ne(UNKNOWN).sum())),
        )
        .sort_values(["llm_adopted_count", "final_non_unknown", "count"], ascending=[False, False, False])
    )
    view_cols = [
        "index",
        "route",
        "subtype",
        "question",
        "eda035_answer",
        "candidate_answer",
        "llm_answer",
        "final_answer",
        "selected_model",
        "status",
        "llm_adopted",
    ]
    target_view = result_df[result_df["target_for_llm"].eq(True)][view_cols]
    report = f"""# EDA036: test構造化候補のOpenRouter確認

## 背景と目的

EDA035では、validで効いた構造化処理をtestへ適用し、非 `わかりません` 回答を31件まで増やした。
EDA036では、Excel、Word、CSV、コード、スケジュールなどの構造化候補をOpenRouterへ渡し、LLMが提出用の短い回答へ整形できるかを確認する。

このEDAでもSIGNATE提出は行わない。OpenRouter APIキーは `.apikey` または環境変数から読み、成果物には保存しない。

## 実行設定

- 入力: `{relative(EDA035_LOG)}`
- モデル候補: `{", ".join(models)}`
- max_tokens: {args.max_tokens}
- temperature: {args.temperature}
- max_questions: {args.max_questions}
- sleep_sec: {args.sleep_sec}

## 結果

- test件数: {len(result_df)}
- EDA035時点の非 `わかりません`: {int(result_df["eda035_answer"].astype(str).ne(UNKNOWN).sum())}
- OpenRouter対象件数: {int(result_df["target_for_llm"].sum())}
- OpenRouter回答取得件数: {int(result_df["llm_answer"].astype(str).ne("").sum())}
- LLM回答を最終回答へ採用した件数: {int(result_df["llm_adopted"].sum())}
- EDA036後の非 `わかりません`: {int(result_df["final_answer"].astype(str).ne(UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## HTTPステータス集計

凡例: `status` はOpenRouterのHTTPステータス、`count` は試行回数を表す。

{status_summary.to_markdown(index=False) if not status_summary.empty else "試行なし"}

## モデル別ステータス集計

凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`count` は試行回数を表す。

{model_summary.to_markdown(index=False) if not model_summary.empty else "試行なし"}

## route別集計

凡例: `count` はtest件数、`target_count` はOpenRouterへ送った件数、`llm_answer_count` はLLM回答が空でなかった件数、`llm_adopted_count` は最終回答へ採用した件数、`final_non_unknown` はEDA036後の非不明回答件数を表す。

{route_summary.to_markdown(index=False)}

## OpenRouter対象別ログ

凡例: `eda035_answer` はEDA035時点の回答、`candidate_answer` は構造化候補、`llm_answer` はOpenRouter回答、`final_answer` は提出CSVへ入れた回答、`llm_adopted` はLLM回答を採用したかを表す。

{target_view.to_markdown(index=False)}
"""
    (OUT_DIR / "eda036_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EDA036: Send structured test candidates to OpenRouter and build a checked submission candidate.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="カンマ区切りのOpenRouterモデル候補")
    parser.add_argument("--max-model-attempts", type=int, default=2, help="1問あたり最大モデル試行数")
    parser.add_argument("--max-questions", type=int, default=45, help="OpenRouterへ送る最大質問数。0以下なら制限なし")
    parser.add_argument("--max-tokens", type=int, default=300, help="OpenRouter max_tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=90, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.0, help="API呼び出し間隔秒")
    parser.add_argument("--skip-llm", action="store_true", help="OpenRouterを呼ばず、対象抽出と提出形式だけ確認する")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    models = parse_models(args.models)[: args.max_model_attempts]
    log_df = pd.read_csv(EDA035_LOG)
    pred_df = load_eda035_predictions()
    merged = log_df.merge(pred_df, on="index", how="left")

    context_rows = [build_context_row(row) for _, row in merged.sort_values("index").iterrows()]
    target_indices = [row["index"] for row in context_rows if row["target_for_llm"]]
    if args.max_questions > 0:
        target_indices = target_indices[: args.max_questions]

    api_key = "" if args.skip_llm else read_api_key("OpenRouter")
    cached_attempts = load_cached_attempts()
    result_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []

    for row in context_rows:
        selected: dict[str, Any] = {"model": "", "status": 0, "answer": "", "ok": False, "error_message": ""}
        should_call = row["index"] in target_indices and not args.skip_llm
        if should_call:
            messages = build_messages(row)
            (PROMPT_DIR / f"test_{row['index']:03d}_prompt.json").write_text(
                json.dumps({"messages": messages, "gold_answer_not_included": True}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            cached_for_index = cached_attempts.get(row["index"], [])
            if cached_for_index:
                for attempt in cached_for_index:
                    attempt_rows.append(attempt)
                    if attempt.get("ok") and compact_answer(attempt.get("answer", "")):
                        selected = attempt
                        break
            for model in ([] if selected.get("answer") or cached_for_index else models):
                response = call_openrouter(api_key, model, messages, args)
                answer = extract_answer(response["payload"]) if response["ok"] else ""
                error_message = "" if response["ok"] else safe_error_message(response["payload"])
                attempt = {
                    "index": row["index"],
                    "model": model,
                    "status": response["status"],
                    "ok": response["ok"],
                    "elapsed_sec": response["elapsed_sec"],
                    "answer": answer,
                    "error_message": error_message,
                }
                attempt_rows.append(attempt)
                if response["ok"] and answer:
                    selected = attempt
                    break
                time.sleep(args.sleep_sec)

        llm_answer = compact_answer(selected.get("answer", ""))
        eda035_answer = compact_answer(row["eda035_answer"])
        # 既にローカル構造化処理で採用済みの回答は、LLMの短縮や表記崩れで上書きしない。
        llm_adopted = eda035_answer == UNKNOWN and is_adoptable_llm_answer(llm_answer)
        final_answer = llm_answer if llm_adopted else eda035_answer
        if not final_answer:
            final_answer = UNKNOWN

        result_rows.append(
            {
                **row,
                "selected_model": selected.get("model", ""),
                "status": int(selected.get("status", 0) or 0),
                "ok": bool(selected.get("ok", False)),
                "llm_answer": llm_answer,
                "llm_error_message": selected.get("error_message", ""),
                "llm_adopted": llm_adopted,
                "final_answer": final_answer,
            }
        )
        if should_call:
            time.sleep(args.sleep_sec)

    result_df = pd.DataFrame(result_rows)
    attempt_df = pd.DataFrame(attempt_rows)
    result_df.to_csv(TABLE_DIR / "test_openrouter_structured_answer_log.csv", index=False, encoding="utf-8-sig")
    attempt_df.to_csv(TABLE_DIR / "test_openrouter_structured_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, attempt_df, args, models)

    manifest = {
        "eda": "EDA036",
        "input": relative(EDA035_LOG),
        "test_count": int(len(result_df)),
        "openrouter_target_count": int(result_df["target_for_llm"].sum()),
        "openrouter_called_count": int(attempt_df["index"].nunique()) if not attempt_df.empty else 0,
        "llm_answer_count": int(result_df["llm_answer"].astype(str).ne("").sum()),
        "llm_adopted_count": int(result_df["llm_adopted"].sum()),
        "before_non_unknown_count": int(result_df["eda035_answer"].astype(str).ne(UNKNOWN).sum()),
        "after_non_unknown_count": int(result_df["final_answer"].astype(str).ne(UNKNOWN).sum()),
        "models": models,
        "outputs": [
            relative(TABLE_DIR / "test_openrouter_structured_answer_log.csv"),
            relative(TABLE_DIR / "test_openrouter_structured_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda036_report.md"),
        ],
        "secret_handling": "API key is read from .apikey or environment variable and is not stored.",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
