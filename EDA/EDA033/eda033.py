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
INPUT_PATH = BASE_DIR / "EDA" / "EDA032" / "tables" / "structured_candidate_answers.csv"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODELS = [
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
]


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = re.sub(r"<[^>]+>", "", text)
    return text


def compact(value: object) -> str:
    text = normalize_text(value)
    text = text.replace("¥", "").replace("￥", "").replace(":", "：")
    text = re.sub(r"\s+", "", text)
    return text


def strip_markup(value: object) -> str:
    text = normalize_text(value)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("**", "").replace("`", "").strip()


def answer_matches(predicted: str, gold: str) -> bool:
    p = compact(predicted)
    g = compact(gold)
    if not p or not g:
        return False
    if p == g or p in g or g in p:
        return True
    p_nums = {x.replace(",", "") for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", p)}
    g_nums = {x.replace(",", "") for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", g)}
    if p_nums and p_nums == g_nums:
        return True
    parts = [part for part in re.split(r"[、,，/]", g) if part]
    return len(parts) >= 2 and all(part in p for part in parts)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def read_api_key(provider: str = "OpenRouter") -> str:
    """環境変数または.apikeyからAPIキーを読む。キー本文は保存しない。"""
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


def parse_models(raw: str) -> list[str]:
    models: list[str] = []
    for item in raw.split(","):
        item = item.strip()
        if item and item not in models:
            models.append(item)
    return models


def build_messages(row: pd.Series) -> list[dict[str, str]]:
    """EDA032の候補を、LLMが提出用回答へ整形しやすい形にする。"""
    system = (
        "あなたは構造化データから作られた回答候補を、提出用の短い最終回答に整えるアシスタントです。"
        "提示された候補、根拠、信頼度だけを使ってください。"
        "外部知識や推測で候補にない値を足さないでください。"
        "回答は最終回答だけにし、説明、根拠番号、ファイルパス、HTMLタグ、Markdown装飾は含めないでください。"
        "候補が複数項目の場合は、候補内の順序をできるだけ保ち、日本語の読点「、」で区切ってください。"
    )
    user = "\n".join(
        [
            "以下の質問に対する最終回答だけを返してください。",
            "",
            f"質問: {row['question']}",
            f"route: {row['route']}",
            f"候補生成方法: {row['method']}",
            f"候補信頼度: {row['confidence']}",
            f"回答候補: {row['candidate_answer']}",
            f"補足: {row.get('notes', '')}",
            "根拠抜粋:",
            str(row.get("evidence", ""))[:3000],
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
            "X-Title": "SIGNATE Agentic RAG EDA033",
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
    return strip_markup(content or "")


def safe_error_message(payload: dict[str, Any]) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        msg = error.get("message") or json.dumps(error, ensure_ascii=False)
    else:
        msg = json.dumps(payload, ensure_ascii=False)
    return strip_markup(msg)[:700]


def write_report(result_df: pd.DataFrame, attempt_df: pd.DataFrame, models: list[str], args: argparse.Namespace) -> None:
    status_summary = attempt_df.groupby("status", as_index=False).size().rename(columns={"size": "count"})
    model_summary = attempt_df.groupby(["model", "status"], as_index=False).size().rename(columns={"size": "count"})
    route_summary = (
        result_df.groupby("route", as_index=False)
        .agg(count=("index", "count"), llm_match_count=("llm_match", "sum"), candidate_match_count=("candidate_match", "sum"))
        .sort_values(["llm_match_count", "candidate_match_count"], ascending=[False, False])
    )
    view = result_df[["index", "route", "selected_model", "status", "llm_answer", "candidate_answer", "gold_answer", "llm_match", "candidate_match"]]
    report = f"""# EDA033: EDA032候補をLLMで最終回答へ整形

## 背景と目的

EDA032では、validで正解できていなかった25件に対して、構造化データから回答候補を一括生成した。
EDA033では、その候補をOpenRouter LLMへ渡し、提出用の短い回答へ整形したときにvalid goldへどれだけ近づくかを確認する。

goldはプロンプトに含めず、評価にのみ使う。

## 実行設定

- 入力: `EDA/EDA032/tables/structured_candidate_answers.csv`
- 対象: 25件
- モデル候補: `{", ".join(models)}`
- max_tokens: {args.max_tokens}
- temperature: {args.temperature}
- sleep_sec: {args.sleep_sec}

## 結果

- 対象件数: {len(result_df)}
- LLM回答取得件数: {int(result_df["llm_answer"].astype(bool).sum())}
- LLM回答のgold類似件数: {int(result_df["llm_match"].sum())}
- EDA032候補のgold類似件数: {int(result_df["candidate_match"].sum())}

## route別結果

凡例: `count` は対象件数、`llm_match_count` はLLM回答のgold類似件数、`candidate_match_count` はEDA032候補のgold類似件数を表す。

{route_summary.to_markdown(index=False)}

## 質問別結果

凡例: `selected_model` は採用した回答のモデル、`status` はHTTPステータス、`llm_answer` はLLM整形後の回答、`candidate_answer` はEDA032候補、`gold_answer` はvalid正解、`llm_match` はLLM回答のgold類似判定、`candidate_match` はEDA032候補のgold類似判定を表す。

{view.to_markdown(index=False)}

## HTTPステータス別試行数

凡例: `status` はOpenRouter HTTPステータス、`count` は試行回数を表す。

{status_summary.to_markdown(index=False)}

## モデル別試行数

凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`count` は試行回数を表す。

{model_summary.to_markdown(index=False)}

## 所感

EDA032候補が十分に正しい場合、LLMは最終回答の整形役として使える。
一方で、候補が既に提出形式に近い場合、LLMを通すことで表記が変わるリスクもある。
提出用パイプラインでは、routeごとに「ローカル候補を直接採用するか」「LLM整形を通すか」をvalidで比較して決める。
"""
    (OUT_DIR / "eda033_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EDA033: Use OpenRouter LLM to finalize EDA032 structured candidates.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="カンマ区切りのOpenRouterモデル候補")
    parser.add_argument("--max-model-attempts", type=int, default=4, help="1問あたり最大モデル試行数")
    parser.add_argument("--max-tokens", type=int, default=600, help="OpenRouter max_tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=120, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.0, help="API呼び出し間隔秒")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)

    api_key = read_api_key("OpenRouter")
    models = parse_models(args.models)
    source_df = pd.read_csv(INPUT_PATH)

    result_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []

    for _, row in source_df.sort_values("index").iterrows():
        index = int(row["index"])
        messages = build_messages(row)
        (PROMPT_DIR / f"valid_{index:03d}_prompt.json").write_text(
            json.dumps({"messages": messages, "gold_answer_not_included": True}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        selected: dict[str, Any] | None = None
        for model in models[: args.max_model_attempts]:
            response = call_openrouter(api_key, model, messages, args)
            answer = extract_answer(response["payload"]) if response["ok"] else ""
            error_message = "" if response["ok"] else safe_error_message(response["payload"])
            attempt = {
                "index": index,
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

        if selected is None:
            selected = {"model": "", "status": 0, "answer": "", "ok": False, "elapsed_sec": 0, "error_message": "all attempts failed"}

        llm_answer = str(selected.get("answer", ""))
        gold_answer = str(row["gold_answer"])
        candidate_answer = str(row["candidate_answer"])
        result_rows.append(
            {
                "index": index,
                "route": row["route"],
                "question": row["question"],
                "selected_model": selected.get("model", ""),
                "status": selected.get("status", 0),
                "llm_answer": llm_answer,
                "candidate_answer": candidate_answer,
                "gold_answer": gold_answer,
                "llm_match": answer_matches(llm_answer, gold_answer),
                "candidate_match": bool(row["candidate_match"]),
                "candidate_method": row["method"],
                "candidate_confidence": row["confidence"],
            }
        )
        time.sleep(args.sleep_sec)

    result_df = pd.DataFrame(result_rows)
    attempt_df = pd.DataFrame(attempt_rows)
    result_df.to_csv(TABLE_DIR / "llm_structured_candidate_answer_log.csv", index=False, encoding="utf-8-sig")
    attempt_df.to_csv(TABLE_DIR / "llm_structured_candidate_attempt_log.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "eda": "EDA033",
        "inputs": [relative(INPUT_PATH)],
        "outputs": [
            "EDA/EDA033/tables/llm_structured_candidate_answer_log.csv",
            "EDA/EDA033/tables/llm_structured_candidate_attempt_log.csv",
            "EDA/EDA033/prompts/valid_XXX_prompt.json",
            "EDA/EDA033/eda033_report.md",
        ],
        "models": models,
        "target_count": int(len(result_df)),
        "llm_answer_count": int(result_df["llm_answer"].astype(bool).sum()),
        "llm_match_count": int(result_df["llm_match"].sum()),
        "candidate_match_count": int(result_df["candidate_match"].sum()),
        "secret_handling": "API key is read from .apikey or environment variable and is not stored.",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result_df, attempt_df, models, args)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
