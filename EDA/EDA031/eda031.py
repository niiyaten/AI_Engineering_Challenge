from __future__ import annotations

import argparse
import json
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
PROMPT_DIR = OUT_DIR / "prompts"
API_KEY_PATH = BASE_DIR / ".apikey"
EDA030_RESULTS_PATH = BASE_DIR / "EDA" / "EDA030" / "tables" / "table_valid_calculation_results.csv"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

DEFAULT_MODELS = [
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
]


def normalize_text(value: object) -> str:
    """比較や検索のため、文字幅と記号の表記ゆれを小さくする。"""
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace('"', "").replace("'", "")
    text = re.sub(r"\s+", "", text)
    return text


def strip_markup(value: object) -> str:
    """LLM回答に混ざるHTMLやMarkdown風の装飾を落とす。"""
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("`", "")
    return text.strip()


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def read_api_key(provider: str = "OpenRouter") -> str:
    """環境変数または.apikeyからAPIキーを読む。キー本文は成果物に保存しない。"""
    env_name = f"{provider.upper()}_API_KEY"
    env_key = os.environ.get(env_name, "").strip()
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


def parse_models(raw_models: str) -> list[str]:
    """カンマ区切りのモデル候補を重複なしのリストにする。"""
    models: list[str] = []
    for model in raw_models.split(","):
        model = model.strip()
        if model and model not in models:
            models.append(model)
    return models


def fetch_free_models(api_key: str, limit: int, timeout_sec: int) -> tuple[list[str], str]:
    """OpenRouterのモデル一覧から無料候補を追加で取る。失敗しても本処理は続ける。"""
    if limit <= 0:
        return [], "disabled"
    request = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.jp/",
            "X-Title": "SIGNATE Agentic RAG EDA031",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return [], f"failed: {exc}"

    models: list[str] = []
    for item in payload.get("data", []):
        model_id = str(item.get("id", ""))
        if not model_id.endswith(":free"):
            continue
        # 画像専用モデルや特殊モデルを避け、テキスト回答に使いやすい候補を優先する。
        if any(skip in model_id.lower() for skip in ["image", "vision", "omni", "tts", "embed"]):
            continue
        models.append(model_id)
        if len(models) >= limit:
            break
    return models, "ok"


def is_similar_answer(predicted: str, gold: str) -> bool:
    """提出評価の完全一致より少し緩く、単位や空白の差を許して近さを見る。"""
    p = normalize_text(predicted)
    g = normalize_text(gold)
    if not p or not g:
        return False
    if p == g or p in g or g in p:
        return True

    p_numbers = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", p)
    g_numbers = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", g)
    if p_numbers and g_numbers:
        p_norm = {n.replace(",", "") for n in p_numbers}
        g_norm = {n.replace(",", "") for n in g_numbers}
        if p_norm == g_norm:
            return True

    gold_parts = [part for part in re.split(r"[、,，/]", g) if part]
    if len(gold_parts) >= 2 and all(part in p for part in gold_parts):
        return True
    return False


def build_messages(row: pd.Series) -> list[dict[str, str]]:
    """EDA030の計算結果を、LLMが最終回答へ整形しやすいプロンプトにする。"""
    system = (
        "あなたは表計算結果を提出用の短い最終回答へ整えるアシスタントです。"
        "提示された質問、計算結果、計算メモ、根拠ファイルだけを使ってください。"
        "外部知識や推測を足さないでください。"
        "回答は最終回答だけにし、説明、根拠番号、ファイルパス、前置き、HTMLタグ、Markdown装飾は含めないでください。"
        "計算結果に要確認メモがある場合も、質問に直接答える値だけを短く返してください。"
    )
    user = "\n".join(
        [
            "以下の質問に、提出用の最終回答だけで答えてください。",
            "",
            f"質問: {row['question']}",
            f"計算サブタイプ: {row['implemented_subtype']}",
            f"ローカル計算結果: {row['predicted_answer']}",
            f"計算メモ: {row['detail']}",
            f"要確認フラグ: {row['needs_review']}",
            f"根拠ファイル: {row['source_paths']}",
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_openrouter(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout_sec: int,
) -> dict[str, Any]:
    """OpenRouter Chat Completions APIを1回呼ぶ。HTTPエラーもログ化できる形で返す。"""
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_CHAT_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.jp/",
            "X-Title": "SIGNATE Agentic RAG EDA031",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "status": int(response.status), "payload": payload, "elapsed_sec": round(time.time() - started, 3)}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"message": str(exc)}}
        return {"ok": False, "status": int(exc.code), "payload": payload, "elapsed_sec": round(time.time() - started, 3)}
    except Exception as exc:
        return {
            "ok": False,
            "status": 0,
            "payload": {"error": {"message": str(exc)}},
            "elapsed_sec": round(time.time() - started, 3),
        }


def extract_answer(payload: dict[str, Any]) -> str:
    """OpenRouter応答からassistant本文を取り出す。"""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return strip_markup(content or "")


def safe_error_message(payload: dict[str, Any]) -> str:
    """APIエラーをCSVに保存できる短い文字列へ整える。"""
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("code") or json.dumps(error, ensure_ascii=False)
    else:
        message = json.dumps(payload, ensure_ascii=False)
    return strip_markup(message)[:700]


def write_report(
    result_df: pd.DataFrame,
    attempt_df: pd.DataFrame,
    models: list[str],
    free_model_fetch_status: str,
    args: argparse.Namespace,
) -> None:
    """EDA031の結果をMarkdownで保存する。"""
    status_summary = attempt_df.groupby("status", as_index=False).size().rename(columns={"size": "count"})
    model_summary = attempt_df.groupby(["model", "status"], as_index=False).size().rename(columns={"size": "count"})
    answer_view = result_df[
        [
            "index",
            "selected_model",
            "status",
            "llm_answer",
            "computed_answer",
            "gold_answer",
            "similar_to_gold",
            "similar_to_computed",
        ]
    ].copy()
    report = f"""# EDA031: 表計算結果をLLMで最終回答へ整形する検証

## 背景と目的

EDA030では、validの表計算系7件に対して、pandas/openpyxlで計算できるかを確認した。
EDA031では、その計算結果をOpenRouter LLMへ渡し、LLMが提出用の短い回答へ整形できるかを検証する。

重要な点として、validの `gold_answer` はプロンプトには含めない。goldは実行後の評価にだけ使う。

## 実行設定

- 入力: `EDA/EDA030/tables/table_valid_calculation_results.csv`
- 対象: EDA030の表計算7件
- モデル候補: `{", ".join(models)}`
- OpenRouter無料モデル追加取得: `{free_model_fetch_status}`
- max_tokens: {args.max_tokens}
- temperature: {args.temperature}
- sleep_sec: {args.sleep_sec}

## 結果

- 対象質問数: {len(result_df)}
- LLM回答取得数: {int(result_df["llm_answer"].astype(bool).sum())}
- goldに近い回答数: {int(result_df["similar_to_gold"].sum())}
- EDA030の計算回答に近い回答数: {int(result_df["similar_to_computed"].sum())}

## 質問別結果

凡例: `selected_model` は最終的に採用した回答のモデル、`status` はHTTPステータス、`llm_answer` はLLMの回答、`computed_answer` はEDA030のローカル計算結果、`gold_answer` はvalid正解、`similar_to_gold` は表記ゆれを少し許したgold類似判定、`similar_to_computed` はローカル計算結果との類似判定を表す。

{answer_view.to_markdown(index=False)}

## HTTPステータス別試行数

凡例: `status` はOpenRouterのHTTPステータス、`count` は試行回数を表す。`0` はHTTP応答前の接続エラーやタイムアウトを表す。

{status_summary.to_markdown(index=False)}

## モデル別試行数

凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`count` は試行回数を表す。

{model_summary.to_markdown(index=False)}

## 所感

この実験は、表計算そのものをLLMに任せるのではなく、ローカル計算で得た値をLLMに最終回答として整形させる構成の検証である。
goldに近い回答が増える場合、提出用パイプラインでは `table_calculation` routeだけ先にローカル計算し、その結果をLLMへ渡す方針が有効と判断できる。
一方、LLMが計算済み回答を崩す、余計な説明を足す、またはAPI制限で失敗する場合は、表計算routeではLLMを使わずローカル計算結果を直接採用する方が安定する。
"""
    (OUT_DIR / "eda031_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="EDA031: Send EDA030 table calculation results to OpenRouter LLMs.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="カンマ区切りのOpenRouterモデル候補")
    parser.add_argument("--append-free-models", type=int, default=4, help="OpenRouterモデル一覧から追加する無料モデル数")
    parser.add_argument("--max-tokens", type=int, default=500, help="OpenRouter max_tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=120, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.5, help="API呼び出し間隔秒")
    parser.add_argument("--max-model-attempts", type=int, default=8, help="1問あたり最大で試すモデル数")
    return parser.parse_args()


def main() -> None:
    """EDA031を実行する。"""
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)

    api_key = read_api_key("OpenRouter")
    models = parse_models(args.models)
    free_models, free_status = fetch_free_models(api_key, args.append_free_models, args.timeout_sec)
    for model in free_models:
        if model not in models:
            models.append(model)

    source_df = pd.read_csv(EDA030_RESULTS_PATH)
    attempt_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    for _, row in source_df.sort_values("index").iterrows():
        index = int(row["index"])
        messages = build_messages(row)
        (PROMPT_DIR / f"valid_{index:03d}_prompt.json").write_text(
            json.dumps({"messages": messages, "gold_answer_not_included": True}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        selected: dict[str, Any] | None = None
        for model in models[: args.max_model_attempts]:
            response = call_openrouter(api_key, model, messages, args.max_tokens, args.temperature, args.timeout_sec)
            answer = extract_answer(response["payload"]) if response["ok"] else ""
            error_message = "" if response["ok"] else safe_error_message(response["payload"])
            row_log = {
                "index": index,
                "model": model,
                "status": response["status"],
                "ok": response["ok"],
                "elapsed_sec": response["elapsed_sec"],
                "answer": answer,
                "error_message": error_message,
            }
            attempt_rows.append(row_log)
            if response["ok"] and answer:
                selected = row_log
                break
            time.sleep(args.sleep_sec)

        if selected is None:
            selected = {
                "index": index,
                "model": "",
                "status": 0,
                "ok": False,
                "elapsed_sec": 0,
                "answer": "",
                "error_message": "all model attempts failed or returned empty answer",
            }

        llm_answer = str(selected.get("answer", ""))
        computed_answer = str(row["predicted_answer"])
        gold_answer = str(row["gold_answer"])
        result_rows.append(
            {
                "index": index,
                "question": row["question"],
                "implemented_subtype": row["implemented_subtype"],
                "selected_model": selected.get("model", ""),
                "status": selected.get("status", 0),
                "llm_answer": llm_answer,
                "computed_answer": computed_answer,
                "gold_answer": gold_answer,
                "similar_to_gold": is_similar_answer(llm_answer, gold_answer),
                "similar_to_computed": is_similar_answer(llm_answer, computed_answer),
                "eda030_answer_match": bool(row["answer_match"]),
                "eda030_needs_review": bool(row["needs_review"]),
            }
        )
        time.sleep(args.sleep_sec)

    result_df = pd.DataFrame(result_rows)
    attempt_df = pd.DataFrame(attempt_rows)
    result_df.to_csv(TABLE_DIR / "llm_table_answer_log.csv", index=False, encoding="utf-8-sig")
    attempt_df.to_csv(TABLE_DIR / "llm_table_attempt_log.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "eda": "EDA031",
        "purpose": "Send EDA030 table calculation results to OpenRouter LLMs and compare answers to valid gold.",
        "inputs": [relative(EDA030_RESULTS_PATH)],
        "outputs": [
            "EDA/EDA031/tables/llm_table_answer_log.csv",
            "EDA/EDA031/tables/llm_table_attempt_log.csv",
            "EDA/EDA031/prompts/valid_XXX_prompt.json",
            "EDA/EDA031/eda031_report.md",
        ],
        "models": models,
        "free_model_fetch_status": free_status,
        "question_count": int(len(result_df)),
        "llm_answer_count": int(result_df["llm_answer"].astype(bool).sum()),
        "similar_to_gold_count": int(result_df["similar_to_gold"].sum()),
        "similar_to_computed_count": int(result_df["similar_to_computed"].sum()),
        "secret_handling": "API key is read from .apikey or environment variable and is not stored.",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result_df, attempt_df, models, free_status, args)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
