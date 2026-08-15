from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# EDA022は、EDA021で作ったRAG検索結果をLLM回答生成へ接続する実験。
BASE_DIR = Path(__file__).resolve().parents[2]
API_KEY_PATH = BASE_DIR / ".apikey"
QUESTIONS_TEST_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_test.csv"
EDA021_RETRIEVAL_PATH = BASE_DIR / "EDA" / "EDA021" / "tables" / "test_rag_retrieval.csv"
EDA021_PREDICTIONS_PATH = BASE_DIR / "EDA" / "EDA021" / "predictions" / "predictions.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
PRED_DIR = OUTPUT_DIR / "predictions"
REPORT_PATH = OUTPUT_DIR / "eda022_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LLM_LOG_PATH = TABLE_DIR / "llm_answer_log.csv"
HYBRID_PREDICTIONS_PATH = PRED_DIR / "predictions_hybrid.csv"
ZIP_PATH = PRED_DIR / "eda022_llm_hybrid_submission.zip"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODELS = [
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]


def setup() -> None:
    """出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)


def compact_text(value: Any) -> str:
    """CSVやLLM入力で扱いやすいように空白を整える。"""
    text = "" if value is None else str(value)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def relative(path: Path) -> str:
    """プロジェクト相対パスを返す。"""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def markdown_escape(value: Any) -> str:
    """Markdown表で崩れやすい文字を逃がす。"""
    return compact_text(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], max_rows: int = 30) -> str:
    """追加依存なしでMarkdown表を作る。"""
    if not rows:
        return "該当データはありません。"
    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(markdown_escape(row.get(col, ""))[:500] for col in columns) + " |")
    return "\n".join(lines)


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Excelでも読みやすいUTF-8 BOM付きCSVを保存する。"""
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns = list(dict.fromkeys(col for row in rows for col in row.keys()))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_api_key() -> str:
    """ローカルの.apikeyからOpenRouter APIキーを読む。成果物には保存しない。"""
    if not API_KEY_PATH.exists():
        raise FileNotFoundError(f"{relative(API_KEY_PATH)} が見つかりません。")
    raw = API_KEY_PATH.read_text(encoding="utf-8").strip()
    if "=" in raw:
        raw = raw.split("=", 1)[1].strip()
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        raise ValueError(".apikey が空です。")
    return raw


def load_questions() -> pd.DataFrame:
    """test質問を読み込む。"""
    return pd.read_csv(QUESTIONS_TEST_PATH)


def load_baseline_predictions() -> dict[int, str]:
    """EDA021の提出形式CSVをフォールバック回答として読む。"""
    rows = {}
    with EDA021_PREDICTIONS_PATH.open(encoding="utf-8-sig", newline="") as f:
        for index, answer in csv.reader(f):
            rows[int(index)] = answer
    return rows


def load_retrieval_by_index(top_k: int) -> dict[int, list[dict[str, Any]]]:
    """EDA021の検索ログを質問indexごとにまとめる。"""
    df = pd.read_csv(EDA021_RETRIEVAL_PATH)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for _, row in df.sort_values(["index", "rank"]).iterrows():
        index = int(row["index"])
        if len(grouped[index]) >= top_k:
            continue
        grouped[index].append(
            {
                "rank": int(row["rank"]),
                "score": row["score"],
                "record_type": row.get("record_type", ""),
                "source_path": row.get("source_path", ""),
                "text_preview": compact_text(row.get("text_preview", "")),
            }
        )
    return grouped


def select_indices(questions: pd.DataFrame, args: argparse.Namespace) -> list[int]:
    """LLMへ投げる質問indexを決める。"""
    all_indices = [int(value) for value in questions["index"].tolist()]
    if args.indices:
        requested = []
        for part in args.indices.split(","):
            part = part.strip()
            if part:
                requested.append(int(part))
        return [idx for idx in requested if idx in set(all_indices)]
    if args.all:
        return all_indices
    return all_indices[: args.limit]


def build_prompt(question: str, route: str, baseline_answer: str, retrieved: list[dict[str, Any]], max_context_chars: int) -> list[dict[str, str]]:
    """OpenRouterのchat completionへ渡すmessagesを作る。"""
    evidence_blocks = []
    used_chars = 0
    for item in retrieved:
        text = item["text_preview"]
        remaining = max_context_chars - used_chars
        if remaining <= 0:
            break
        text = text[:remaining]
        used_chars += len(text)
        evidence_blocks.append(
            "\n".join(
                [
                    f"[根拠 {item['rank']}]",
                    f"source_path: {item['source_path']}",
                    f"record_type: {item['record_type']}",
                    f"score: {item['score']}",
                    "text:",
                    text,
                ]
            )
        )

    system = (
        "あなたは社内共有ドライブから質問に答えるRAG回答器です。"
        "必ず提示された根拠だけを使って日本語で答えてください。"
        "根拠にない情報は推測せず、足りない場合は「わかりません」と答えてください。"
        "提出用なので、前置き、根拠番号、ファイルパスの説明は不要です。"
        "数値計算が必要で、根拠に必要な値が揃っている場合は計算して答えてください。"
    )
    user = "\n\n".join(
        [
            "以下の質問に、簡潔かつ具体的に答えてください。",
            f"質問: {question}",
            f"推定route: {route}",
            f"EDA021の抽出型回答: {baseline_answer}",
            "根拠:",
            "\n\n".join(evidence_blocks) if evidence_blocks else "根拠なし",
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_openrouter(api_key: str, model: str, messages: list[dict[str, str]], args: argparse.Namespace) -> dict[str, Any]:
    """OpenRouterへ1回問い合わせる。"""
    body = {
        "model": model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.jp/",
            "X-Title": "SIGNATE Agentic RAG EDA022",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        payload = {}
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"message": str(exc)}}
        return {"ok": False, "status": int(exc.code), "payload": payload, "elapsed_sec": round(time.time() - started, 3)}
    except Exception as exc:
        return {"ok": False, "status": 0, "payload": {"error": {"message": str(exc)}}, "elapsed_sec": round(time.time() - started, 3)}
    return {"ok": True, "status": status, "payload": payload, "elapsed_sec": round(time.time() - started, 3)}


def extract_answer(payload: dict[str, Any]) -> str:
    """OpenRouter応答から回答本文を取り出す。"""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        texts = [part.get("text", "") for part in content if isinstance(part, dict)]
        content = "\n".join(texts)
    return compact_text(content or "")


def safe_error_message(payload: dict[str, Any]) -> str:
    """APIキーなどを含めず、エラー概要だけを残す。"""
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return compact_text(error.get("message", ""))[:500]
    return compact_text(payload)[:500]


def run_llm(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """選択した質問にLLM回答生成を実行し、全100件のhybrid予測を作る。"""
    api_key = read_api_key()
    questions = load_questions()
    baseline = load_baseline_predictions()
    retrieval = load_retrieval_by_index(args.top_k)
    target_indices = select_indices(questions, args)
    model_candidates = [model.strip() for model in args.models.split(",") if model.strip()]

    llm_logs: list[dict[str, Any]] = []
    llm_answers: dict[int, str] = {}
    route_by_index = {}
    for items in retrieval.values():
        if items:
            pass

    retrieval_df = pd.read_csv(EDA021_RETRIEVAL_PATH)
    route_lookup = {
        int(row["index"]): str(row.get("route", ""))
        for _, row in retrieval_df[retrieval_df["rank"] == 1].iterrows()
    }

    for index in target_indices:
        row = questions[questions["index"] == index].iloc[0]
        question = str(row["question"])
        route = route_lookup.get(index, "")
        route_by_index[index] = route
        messages = build_prompt(
            question=question,
            route=route,
            baseline_answer=baseline.get(index, ""),
            retrieved=retrieval.get(index, []),
            max_context_chars=args.max_context_chars,
        )

        final_answer = ""
        final_status = 0
        final_error = ""
        used_model = ""
        elapsed_sec = 0.0
        for model in model_candidates:
            result = call_openrouter(api_key, model, messages, args)
            final_status = result["status"]
            elapsed_sec = result["elapsed_sec"]
            answer = extract_answer(result["payload"]) if result["ok"] else ""
            if result["ok"] and answer:
                final_answer = answer[: args.max_answer_chars]
                used_model = model
                final_error = ""
                break
            used_model = model
            final_error = safe_error_message(result["payload"])
            if final_status not in {429, 500, 502, 503, 504}:
                break
            time.sleep(args.retry_sleep_sec)

        if final_answer:
            llm_answers[index] = final_answer
            answer_source = "llm"
        else:
            answer_source = "baseline_fallback"
            final_answer = baseline.get(index, "わかりません")

        llm_logs.append(
            {
                "index": index,
                "question": question,
                "route": route,
                "answer_source": answer_source,
                "model": used_model,
                "status": final_status,
                "elapsed_sec": elapsed_sec,
                "llm_answer": final_answer if answer_source == "llm" else "",
                "fallback_answer": baseline.get(index, ""),
                "error_message": final_error,
            }
        )
        time.sleep(args.sleep_sec)

    hybrid_rows = []
    for _, row in questions.sort_values("index").iterrows():
        index = int(row["index"])
        answer = llm_answers.get(index, baseline.get(index, "わかりません"))
        answer = re.sub(r"\s*\n\s*", " ", compact_text(answer))
        hybrid_rows.append(
            {
                "index": index,
                "answer": answer,
                "answer_source": "llm" if index in llm_answers else "baseline_eda021",
            }
        )
    return llm_logs, hybrid_rows


def write_predictions(hybrid_rows: list[dict[str, Any]]) -> None:
    """hybrid予測を提出形式CSVとzipで保存する。"""
    with HYBRID_PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in hybrid_rows:
            writer.writerow([row["index"], row["answer"]])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(HYBRID_PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(llm_logs: list[dict[str, Any]], hybrid_rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """EDA022のレポートを保存する。"""
    source_counts = Counter(row["answer_source"] for row in hybrid_rows)
    call_counts = Counter(row["answer_source"] for row in llm_logs)
    model_counts = Counter(row["model"] for row in llm_logs if row.get("model"))
    status_counts = Counter(str(row["status"]) for row in llm_logs)
    answer_lengths = [len(str(row["answer"])) for row in hybrid_rows]
    summary_rows = [
        {"metric": "llm_call_targets", "value": len(llm_logs)},
        {"metric": "llm_success_count", "value": call_counts.get("llm", 0)},
        {"metric": "llm_failed_fallback_count", "value": call_counts.get("baseline_fallback", 0)},
        {"metric": "hybrid_prediction_count", "value": len(hybrid_rows)},
        {"metric": "hybrid_llm_answers", "value": source_counts.get("llm", 0)},
        {"metric": "hybrid_baseline_answers", "value": source_counts.get("baseline_eda021", 0)},
        {"metric": "empty_answer_count", "value": sum(1 for row in hybrid_rows if not str(row["answer"]).strip())},
        {"metric": "max_answer_length", "value": max(answer_lengths) if answer_lengths else 0},
    ]
    lines = [
        "# EDA022: OpenRouter LLM回答生成",
        "",
        "## 目的",
        "",
        "EDA021で保存したRAG検索結果をOpenRouterのLLMへ渡し、抽出型回答からLLM生成回答へ発展できるかを確認する。",
        "",
        "## 出力",
        "",
        f"- llm_answer_log: `{relative(LLM_LOG_PATH)}`",
        f"- hybrid_predictions_csv: `{relative(HYBRID_PREDICTIONS_PATH)}`",
        f"- hybrid_submission_zip: `{relative(ZIP_PATH)}`",
        "",
        "## 実行設定",
        "",
        f"- models: `{args.models}`",
        f"- top_k: {args.top_k}",
        f"- max_context_chars: {args.max_context_chars}",
        f"- max_tokens: {args.max_tokens}",
        f"- temperature: {args.temperature}",
        "",
        "## 出力検証",
        "",
        "凡例: `metric` は検証項目、`value` は値を表します。",
        "",
        markdown_table(summary_rows),
        "",
        "## model別呼び出し件数",
        "",
        "凡例: `model` はOpenRouterモデル名、`count` は最終的に試行した件数を表します。",
        "",
        markdown_table([{"model": key, "count": value} for key, value in sorted(model_counts.items())]),
        "",
        "## HTTP status別件数",
        "",
        "凡例: `status` はOpenRouterのHTTPステータス、`count` は件数を表します。",
        "",
        markdown_table([{"status": key, "count": value} for key, value in sorted(status_counts.items())]),
        "",
        "## 注意点",
        "",
        "- APIキーは `.apikey` から読み込むだけで、レポートやCSVには保存しない。",
        "- LLMが失敗した質問はEDA021の回答へフォールバックするため、zipは常に100行の提出形式になる。",
        "- このEDAはLLM接続と回答改善の実験であり、SIGNATEへの実提出は行っていない。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(args: argparse.Namespace, llm_logs: list[dict[str, Any]], hybrid_rows: list[dict[str, Any]]) -> None:
    """再現に必要な入出力だけを記録する。"""
    manifest = {
        "eda": "EDA022",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Generate LLM answers from EDA021 RAG contexts via OpenRouter.",
        "parameters": {
            "models": args.models,
            "top_k": args.top_k,
            "limit": args.limit,
            "all": args.all,
            "indices": args.indices,
            "max_context_chars": args.max_context_chars,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        },
        "inputs": {
            "questions_test": relative(QUESTIONS_TEST_PATH),
            "eda021_retrieval": relative(EDA021_RETRIEVAL_PATH),
            "eda021_predictions": relative(EDA021_PREDICTIONS_PATH),
            "api_key": ".apikey (not stored)",
        },
        "outputs": {
            "llm_answer_log": relative(LLM_LOG_PATH),
            "hybrid_predictions": relative(HYBRID_PREDICTIONS_PATH),
            "hybrid_submission_zip": relative(ZIP_PATH),
            "report": relative(REPORT_PATH),
        },
        "llm_log_count": len(llm_logs),
        "prediction_count": len(hybrid_rows),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Generate LLM answers using EDA021 RAG retrieval contexts.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="カンマ区切りのOpenRouterモデル候補")
    parser.add_argument("--top-k", type=int, default=6, help="LLMへ渡す検索根拠数")
    parser.add_argument("--limit", type=int, default=10, help="--all未指定時にLLMへ投げる先頭件数")
    parser.add_argument("--indices", default="", help="LLMへ投げるindexをカンマ区切りで指定する")
    parser.add_argument("--all", action="store_true", help="test 100問すべてをLLMへ投げる")
    parser.add_argument("--max-context-chars", type=int, default=12000, help="LLMへ渡す根拠本文の最大文字数")
    parser.add_argument("--max-answer-chars", type=int, default=900, help="回答の最大文字数")
    parser.add_argument("--max-tokens", type=int, default=700, help="OpenRouter max_tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=90, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.0, help="API呼び出し間隔秒")
    parser.add_argument("--retry-sleep-sec", type=float, default=3.0, help="モデルフォールバック前の待機秒")
    return parser.parse_args()


def main() -> None:
    """EDA022を実行する。"""
    args = parse_args()
    setup()
    llm_logs, hybrid_rows = run_llm(args)
    save_csv(llm_logs, LLM_LOG_PATH)
    write_predictions(hybrid_rows)
    write_report(llm_logs, hybrid_rows, args)
    write_manifest(args, llm_logs, hybrid_rows)
    success_count = sum(1 for row in llm_logs if row["answer_source"] == "llm")
    print(
        " ".join(
            [
                f"llm_targets={len(llm_logs)}",
                f"llm_success={success_count}",
                f"hybrid_predictions={len(hybrid_rows)}",
                f"zip={relative(ZIP_PATH)}",
            ]
        )
    )


if __name__ == "__main__":
    main()
