from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd


# EDA027補助検証として、OpenRouter無料モデルの到達可否を少数リクエストで確認する。
BASE_DIR = Path(__file__).resolve().parents[2]
EDA027_PATH = BASE_DIR / "EDA" / "EDA027" / "eda027.py"
OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda027_model_probe_report.md"
FREE_MODELS_PATH = TABLE_DIR / "openrouter_free_models.csv"
PROBE_LOG_PATH = TABLE_DIR / "model_probe_log.csv"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

PRIORITY_MODELS = [
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]


def load_eda027_module() -> Any:
    """EDA027のRAGプロンプト作成とAPI呼び出し関数を再利用する。"""
    spec = importlib.util.spec_from_file_location("eda027_module", EDA027_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"EDA027を読み込めません: {EDA027_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setup() -> None:
    """出力先ディレクトリを作る。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Excelで確認しやすいUTF-8 BOM付きCSVを保存する。"""
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns = list(dict.fromkeys(col for row in rows for col in row.keys()))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def fetch_free_models(api_key: str, timeout_sec: int) -> tuple[list[dict[str, Any]], str]:
    """OpenRouterの現在のモデル一覧から無料モデルを抽出する。"""
    request = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return [], f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')[:300]}"
    except Exception as exc:
        return [], str(exc)

    rows: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        model_id = str(item.get("id", ""))
        if not model_id.endswith(":free"):
            continue
        rows.append(
            {
                "id": model_id,
                "name": item.get("name", ""),
                "context_length": item.get("context_length", ""),
                "created": item.get("created", ""),
            }
        )
    rows.sort(key=lambda row: row["id"])
    return rows, ""


def choose_models(discovered: list[dict[str, Any]], limit: int) -> list[str]:
    """優先モデルを先頭にし、現在見える無料モデルを追加する。"""
    discovered_ids = [str(row["id"]) for row in discovered]
    chosen: list[str] = []
    for model in PRIORITY_MODELS:
        if model not in chosen:
            chosen.append(model)
    for model in discovered_ids:
        if model not in chosen:
            chosen.append(model)
        if len(chosen) >= limit:
            break
    return chosen[:limit]


def markdown_table(rows: list[dict[str, Any]], max_rows: int = 20) -> str:
    """レポート用の簡易Markdown表を作る。"""
    if not rows:
        return "該当データはありません。"
    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:max_rows]:
        values = [str(row.get(col, "")).replace("|", "\\|").replace("\n", " ")[:300] for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_probe_context(eda027: Any, question_index: int, top_k: int, max_context_chars: int) -> tuple[str, str, list[dict[str, Any]], list[dict[str, str]]]:
    """test質問1件について、EDA027と同じ検索contextを作る。"""
    questions = pd.read_csv(eda027.QUESTIONS_TEST_PATH)
    routes = eda027.load_routes()
    qrow = questions[questions["index"] == question_index].iloc[0]
    question = str(qrow["question"])
    route = routes.get(question_index, "")
    records = eda027.load_records()
    index = eda027.BM25Index(records)
    retrieved = index.search(f"{question}\nroute:{route}", top_k)
    messages = eda027.build_messages(question, route, retrieved, max_context_chars)
    return question, route, retrieved, messages


def probe_models(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """候補モデルへ1問ずつ問い合わせ、HTTP statusと回答有無を記録する。"""
    eda027 = load_eda027_module()
    api_key = eda027.read_api_key()
    discovered, model_list_error = fetch_free_models(api_key, args.timeout_sec)
    save_csv(discovered, FREE_MODELS_PATH)

    question, route, retrieved, messages = build_probe_context(
        eda027,
        question_index=args.question_index,
        top_k=args.top_k,
        max_context_chars=args.max_context_chars,
    )
    probe_args_base = {
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "timeout_sec": args.timeout_sec,
    }
    rows: list[dict[str, Any]] = []
    for model in choose_models(discovered, args.model_limit):
        call_args = SimpleNamespace(model=model, **probe_args_base)
        started = time.time()
        result = eda027.call_openrouter(api_key, messages, call_args)
        answer = eda027.extract_answer(result["payload"]) if result["ok"] else ""
        error_message = "" if answer else eda027.safe_error_message(result["payload"])
        rows.append(
            {
                "model": model,
                "status": result["status"],
                "elapsed_sec": result["elapsed_sec"],
                "answer": answer[:300],
                "is_unknown": int(eda027.is_unknown_answer(answer)),
                "error_message": error_message,
                "question_index": args.question_index,
                "route": route,
                "top1_source_path": retrieved[0]["record"].get("source_path", "") if retrieved else "",
                "wall_sec": round(time.time() - started, 3),
            }
        )
        time.sleep(args.sleep_sec)
    save_csv(rows, PROBE_LOG_PATH)
    return rows, discovered, model_list_error


def write_report(rows: list[dict[str, Any]], discovered: list[dict[str, Any]], model_list_error: str, args: argparse.Namespace) -> None:
    """モデル確認結果をMarkdownで保存する。"""
    status_rows = []
    for status in sorted({str(row["status"]) for row in rows}):
        status_rows.append({"status": status, "count": sum(1 for row in rows if str(row["status"]) == status)})
    lines = [
        "# EDA027補助: OpenRouter無料モデル疎通確認",
        "",
        "## 目的",
        "",
        "EDA027でtest 100問のほとんどがHTTP 429になったため、120Bや他の無料モデルでも同じ制限に当たるかを少数リクエストで確認する。",
        "",
        "## 実行設定",
        "",
        f"- question_index: {args.question_index}",
        f"- model_limit: {args.model_limit}",
        f"- max_tokens: {args.max_tokens}",
        f"- top_k: {args.top_k}",
        "",
        "## 現在取得できた無料モデル数",
        "",
        f"- free_model_count: {len(discovered)}",
        f"- model_list_error: {model_list_error or 'なし'}",
        "",
        "## HTTP status別件数",
        "",
        "凡例: `status` はOpenRouterのHTTPステータス、`count` は件数です。",
        "",
        markdown_table(status_rows),
        "",
        "## モデル別結果",
        "",
        "凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`answer` は返答、`is_unknown` は不明回答判定、`error_message` はAPIエラー概要です。",
        "",
        markdown_table(rows, max_rows=args.model_limit),
        "",
        "## 注意点",
        "",
        "- このEDAはモデル可用性の確認であり、SIGNATEへの提出は行っていない。",
        "- APIキーは `.apikey` から読み込み、成果物には保存しない。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Probe OpenRouter free models with one RAG question.")
    parser.add_argument("--question-index", type=int, default=0, help="疎通確認に使うtest質問index")
    parser.add_argument("--model-limit", type=int, default=8, help="確認するモデル数")
    parser.add_argument("--top-k", type=int, default=8, help="LLMへ渡す検索根拠数")
    parser.add_argument("--max-context-chars", type=int, default=12000, help="LLMへ渡す根拠本文の最大文字数")
    parser.add_argument("--max-tokens", type=int, default=300, help="OpenRouter max_tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=90, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.0, help="API呼び出し間隔秒")
    return parser.parse_args()


def main() -> None:
    """EDA027補助のモデル疎通確認を実行する。"""
    args = parse_args()
    setup()
    rows, discovered, model_list_error = probe_models(args)
    write_report(rows, discovered, model_list_error, args)
    http200 = sum(1 for row in rows if int(row["status"]) == 200)
    print(
        f"models={len(rows)} http200={http200} free_models={len(discovered)} "
        f"log={PROBE_LOG_PATH.relative_to(BASE_DIR)} report={REPORT_PATH.relative_to(BASE_DIR)}"
    )


if __name__ == "__main__":
    main()
