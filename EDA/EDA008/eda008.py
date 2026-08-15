from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda008.py は「プロジェクト直下 / EDA / EDA008 / eda008.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
EDA007_DIR = BASE_DIR / "EDA" / "EDA007"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
PROMPT_DIR = OUTPUT_DIR / "prompts"
REPORT_PATH = OUTPUT_DIR / "eda008_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda008.log"

CONTEXT_QUALITY_PATH = EDA007_DIR / "tables" / "context_quality.csv"
CONTEXT_DIR = EDA007_DIR / "contexts"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4.1-mini"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 256
API_KEY_FILE = BASE_DIR / ".apikey"
FREE_MODEL_CANDIDATES = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-20b:free",
    "poolside/laguna-xs-2.1:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def relative(path: Path) -> str:
    """manifestやレポートでプロジェクト相対パスを表示する。"""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha1(path: Path) -> str:
    """入力成果物の追跡用にSHA1を計算する。"""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """Excelでも開きやすいようにUTF-8 BOM付きでCSV保存する。"""
    df.to_csv(path, index=False, encoding="utf-8-sig")


def df_to_markdown(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """tabulateに依存せずDataFrameをMarkdown表に変換する。"""
    if df.empty:
        return "該当データはありません。"
    view = df if max_rows is None else df.head(max_rows)
    columns = [str(col) for col in view.columns]

    def fmt(value: Any) -> str:
        if pd.isna(value):
            text = ""
        else:
            text = str(value)
        return text.replace("\n", " ").replace("\r", " ").replace("|", "\\|")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in view.columns) + " |")
    return "\n".join(lines)


def build_messages(context: str) -> list[dict[str, str]]:
    """OpenRouterへ渡すチャットメッセージを作る。"""
    system = (
        "あなたは提供された根拠だけを使って質問に答えるRAG回答器です。\n"
        "外部知識は使わないでください。\n"
        "根拠にない場合は「わかりません」と答えてください。\n"
        "回答は日本語で、質問が求める値だけを簡潔に答えてください。\n"
        "説明や根拠の引用は不要です。"
    )
    user = (
        "以下のMarkdownには、質問、検証用の正解、診断情報、検索された根拠があります。\n"
        "回答生成ではValidation Answerを見てはいけません。Validation Answerは評価用情報です。\n"
        "QuestionとRetrieved Evidenceだけを使って、最終回答だけを出してください。\n\n"
        f"{strip_validation_answer(context)}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def strip_validation_answer(context: str) -> str:
    """LLM入力からValidation Answer節を取り除き、valid正解の混入を防ぐ。"""
    return re.sub(
        r"\n## Validation Answer\n.*?(?=\n## Diagnosis\n)",
        "\n## Validation Answer\n[hidden for generation]\n",
        context,
        flags=re.DOTALL,
    )


def call_openrouter(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int,
    reasoning_enabled: bool,
) -> tuple[str, dict[str, Any]]:
    """OpenRouter Chat Completions APIを呼ぶ。"""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # gpt-oss系など、OpenRouter側で推論トークンを扱えるモデルを検証するための任意設定。
    if reasoning_enabled:
        payload["reasoning"] = {"enabled": True}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost/signate-agentic-rag",
            "X-Title": "SIGNATE Agentic RAG EDA008",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTPError {exc.code}: {detail[:1000]}") from exc
    elapsed = time.time() - started
    choice = data["choices"][0]
    message = choice["message"]
    answer = str(message.get("content") or "").strip()
    meta = {
        "elapsed_sec": round(elapsed, 3),
        "usage": data.get("usage", {}),
        "response_id": data.get("id", ""),
        "provider": data.get("provider", ""),
        "finish_reason": choice.get("finish_reason", ""),
    }
    return answer, meta


def compact_for_match(text: Any) -> str:
    """valid正解との簡易照合用に、空白・一部記号を除去する。"""
    text = str(text).lower()
    text = text.replace(",", "").replace("，", "")
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[\"'`『』「」\[\]（）(){}]", "", text)


def answer_contains_true(predicted: str, true_answer: str) -> bool:
    """LLM回答にvalid正解が含まれるかを簡易確認する。"""
    true_compact = compact_for_match(true_answer)
    pred_compact = compact_for_match(predicted)
    return bool(true_compact and true_compact in pred_compact)


def model_candidates(args: argparse.Namespace) -> list[str]:
    """単一モデルか無料モデル候補リストかを、実行引数から決める。"""
    if args.free_model_fallback:
        return FREE_MODEL_CANDIDATES
    return [args.model]


def run_generation(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    """ready_for_llmのvalidコンテキストに対してLLM回答生成を行う。"""
    quality = pd.read_csv(CONTEXT_QUALITY_PATH)
    targets = quality[quality["context_quality_for_llm"] == "ready_for_llm"].copy()
    if args.limit is not None:
        targets = targets.head(args.limit)

    api_key, api_key_source = load_api_key()
    do_call = bool(api_key) and not args.dry_run

    answer_rows: list[dict[str, Any]] = []
    call_rows: list[dict[str, Any]] = []

    for _, row in targets.sort_values("index").iterrows():
        q_index = int(row["index"])
        context_path = BASE_DIR / str(row["context_path"])
        context = context_path.read_text(encoding="utf-8")
        messages = build_messages(context)
        prompt_path = PROMPT_DIR / f"valid_{q_index:03d}_prompt.json"
        candidates = model_candidates(args)
        prompt_payload = {
            "model": candidates[0],
            "model_candidates": candidates,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "messages": messages,
        }
        # 実APIへ送る任意パラメータも、再現できるよう保存プロンプトに含める。
        if args.reasoning_enabled:
            prompt_payload["reasoning"] = {"enabled": True}
        prompt_path.write_text(json.dumps(prompt_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        status = "dry_run"
        predicted = ""
        selected_model = candidates[0]
        error_message = ""
        elapsed_sec = 0.0
        usage_json = "{}"
        response_id = ""

        if do_call:
            for candidate_model in candidates:
                selected_model = candidate_model
                try:
                    predicted, meta = call_openrouter(
                        api_key=api_key,
                        model=candidate_model,
                        messages=messages,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                        timeout=args.timeout,
                        reasoning_enabled=args.reasoning_enabled,
                    )
                    if not predicted:
                        provider = str(meta.get("provider", ""))
                        finish_reason = str(meta.get("finish_reason", ""))
                        raise RuntimeError(f"empty_content provider={provider} finish_reason={finish_reason}")
                    status = "ok"
                    elapsed_sec = float(meta.get("elapsed_sec", 0.0))
                    usage_json = json.dumps(meta.get("usage", {}), ensure_ascii=False)
                    response_id = str(meta.get("response_id", ""))
                    error_message = ""
                except Exception as exc:  # noqa: BLE001 - API検証ではエラーをログに残して継続する。
                    status = "error"
                    error_message = str(exc)
                    logging.exception("LLM call failed for valid_%03d model=%s", q_index, candidate_model)
                call_rows.append(
                    {
                        "index": q_index,
                        "model": candidate_model,
                        "status": status,
                        "api_key_source": api_key_source if api_key else "",
                        "temperature": args.temperature,
                        "max_tokens": args.max_tokens,
                        "elapsed_sec": elapsed_sec if status == "ok" else 0.0,
                        "usage_json": usage_json if status == "ok" else "{}",
                        "response_id": response_id if status == "ok" else "",
                        "context_path": relative(context_path),
                        "prompt_path": relative(prompt_path),
                        "error_message": error_message,
                    }
                )
                if status == "ok":
                    break
        elif not api_key:
            status = "missing_api_key"
            call_rows.append(
                {
                    "index": q_index,
                    "model": selected_model,
                    "status": status,
                    "api_key_source": "",
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "elapsed_sec": elapsed_sec,
                    "usage_json": usage_json,
                    "response_id": response_id,
                    "context_path": relative(context_path),
                    "prompt_path": relative(prompt_path),
                    "error_message": error_message,
                }
            )
        else:
            call_rows.append(
                {
                    "index": q_index,
                    "model": selected_model,
                    "status": status,
                    "api_key_source": api_key_source if api_key else "",
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "elapsed_sec": elapsed_sec,
                    "usage_json": usage_json,
                    "response_id": response_id,
                    "context_path": relative(context_path),
                    "prompt_path": relative(prompt_path),
                    "error_message": error_message,
                }
            )

        true_answer = extract_validation_answer(context)
        answer_rows.append(
            {
                "index": q_index,
                "context_path": relative(context_path),
                "prompt_path": relative(prompt_path),
                "model": selected_model,
                "model_candidates": " | ".join(candidates),
                "status": status,
                "api_key_source": api_key_source if api_key else "",
                "true_answer": true_answer,
                "llm_answer": predicted,
                "contains_true_answer": answer_contains_true(predicted, true_answer) if predicted else False,
                "error_message": error_message,
            }
        )
    return pd.DataFrame(answer_rows), pd.DataFrame(call_rows)


def load_api_key() -> tuple[str, str]:
    """OpenRouter APIキーを環境変数、なければプロジェクト直下の.apikeyから読む。"""
    env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env_key:
        return env_key, "env:OPENROUTER_API_KEY"
    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key, ".apikey"
    return "", ""


def extract_validation_answer(context: str) -> str:
    """評価用にコンテキスト内のValidation Answerを取り出す。LLM入力には渡さない。"""
    match = re.search(r"\n## Validation Answer\n(.*?)(?=\n## Diagnosis\n)", context, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def write_manifest(args: argparse.Namespace, answer_path: Path, call_path: Path) -> None:
    """提出用コード化に備え、入力・出力・パラメータを追跡できるmanifestを保存する。"""
    inputs = [CONTEXT_QUALITY_PATH]
    manifest = {
        "eda": "EDA008",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Generate answers for ready_for_llm validation contexts through OpenRouter.",
        "parameters": {
            "model": args.model,
            "free_model_fallback": args.free_model_fallback,
            "model_candidates": model_candidates(args),
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "reasoning_enabled": args.reasoning_enabled,
            "dry_run": args.dry_run,
            "limit": args.limit,
        },
        "inputs": [
            {"path": relative(path), "sha1": file_sha1(path), "bytes": path.stat().st_size}
            for path in inputs
            if path.exists()
        ],
        "outputs": {
            "answer_log": relative(answer_path),
            "call_log": relative(call_path),
            "prompt_dir": relative(PROMPT_DIR),
            "report": relative(REPORT_PATH),
        },
        "secret_handling": "API key is read from OPENROUTER_API_KEY or project-local .apikey and is not written to logs.",
        "repro_steps": [
            "uv run python EDA/EDA007/eda007.py",
            "set OPENROUTER_API_KEY in environment or put the key in project-local .apikey",
            "uv run python EDA/EDA008/eda008.py --model <model>",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(answer_df: pd.DataFrame, call_df: pd.DataFrame, args: argparse.Namespace) -> None:
    """EDA008のMarkdownレポートを生成する。"""
    ok_count = int((answer_df["status"] == "ok").sum()) if not answer_df.empty else 0
    exact_rate = 0.0
    if ok_count:
        exact_rate = float(answer_df.loc[answer_df["status"] == "ok", "contains_true_answer"].mean())
    status_counts = answer_df["status"].value_counts().rename_axis("status").reset_index(name="count") if not answer_df.empty else pd.DataFrame()

    lines: list[str] = []
    lines.append("# EDA008: OpenRouter LLM回答生成の最小検証")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append(
        "EDA007で作成した `ready_for_llm` のMarkdownコンテキストを使い、"
        "OpenRouter経由でLLM回答生成を試します。対象はvalidのうち、EDA006で検索根拠が比較的そろっていると判断した問題のみです。"
    )
    lines.append("")
    lines.append(
        "APIキーは環境変数 `OPENROUTER_API_KEY`、またはプロジェクト直下の `.apikey` から読み込み、"
        "コード、CSV、ログ、manifestには保存しません。"
        "LLM入力からはValidation Answer節を隠し、QuestionとRetrieved Evidenceだけで回答させます。"
    )
    lines.append("")
    lines.append("## 実行設定")
    lines.append("")
    lines.append(f"- model: `{args.model}`")
    lines.append(f"- free_model_fallback: {args.free_model_fallback}")
    if args.free_model_fallback:
        lines.append(f"- model_candidates: {', '.join(model_candidates(args))}")
    lines.append(f"- temperature: {args.temperature}")
    lines.append(f"- max_tokens: {args.max_tokens}")
    lines.append(f"- reasoning_enabled: {args.reasoning_enabled}")
    lines.append(f"- dry_run: {args.dry_run}")
    lines.append(f"- limit: {args.limit}")
    lines.append("")
    lines.append("## 結果サマリ")
    lines.append("")
    lines.append(f"- 対象件数: {len(answer_df)}")
    lines.append(f"- API成功件数: {ok_count}")
    lines.append(f"- valid正解全文を含んだ割合: {exact_rate:.4f}")
    lines.append("")
    lines.append("## ステータス内訳")
    lines.append("")
    lines.append(df_to_markdown(status_counts))
    lines.append("")
    lines.append("凡例: `status` はLLM呼び出し状態、`count` は件数を表します。")
    lines.append("")
    lines.append("## 回答サンプル")
    lines.append("")
    sample_cols = ["index", "status", "true_answer", "llm_answer", "contains_true_answer", "error_message"]
    lines.append(df_to_markdown(answer_df[sample_cols], max_rows=20))
    lines.append("")
    lines.append("## API試行ログ")
    lines.append("")
    call_cols = ["index", "model", "status", "elapsed_sec", "error_message"]
    lines.append(df_to_markdown(call_df[call_cols], max_rows=30))
    lines.append("")
    lines.append("凡例: `model` は試行したOpenRouterモデルID、`status` はAPI呼び出し状態、`elapsed_sec` は成功時の処理秒数、`error_message` は失敗時の内容を表します。")
    lines.append("")
    lines.append("## 次にやること")
    lines.append("")
    lines.append("1. モデルを比較し、ready_for_llmのvalid一致率を確認する。")
    lines.append("2. プロンプトで回答形式をさらに制御する。")
    lines.append("3. testに適用する前に、CSV/XLSX直接集計などLLM以外の不足処理を追加する。")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_eda_summary(answer_df: pd.DataFrame, args: argparse.Namespace) -> None:
    """EDA総括にEDA008の概要を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    if "## EDA008の要点" in text:
        return
    marker = "## 現時点の総合判断"
    ok_count = int((answer_df["status"] == "ok").sum()) if not answer_df.empty else 0
    exact_rate = 0.0
    if ok_count:
        exact_rate = float(answer_df.loc[answer_df["status"] == "ok", "contains_true_answer"].mean())
    addition = f"""
## EDA008の要点

EDA008では、EDA007で作成した `ready_for_llm` のvalid Markdownコンテキストを使い、OpenRouter経由のLLM回答生成を検証する仕組みを作りました。モデルは `{args.model}`、temperatureは {args.temperature}、max_tokensは {args.max_tokens} です。APIキーは環境変数 `OPENROUTER_API_KEY`、またはプロジェクト直下の `.apikey` から読み、ログには保存しません。

実行結果は対象 {len(answer_df)} 件、API成功 {ok_count} 件、valid正解全文を含んだ割合は {exact_rate:.4f} でした。

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA008: OpenRouter LLM answer generation for ready contexts.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reasoning-enabled", action="store_true")
    parser.add_argument("--free-model-fallback", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()
    answer_df, call_df = run_generation(args)
    answer_path = TABLE_DIR / "llm_valid_answers.csv"
    call_path = TABLE_DIR / "llm_call_log.csv"
    save_csv(answer_df, answer_path)
    save_csv(call_df, call_path)
    write_report(answer_df, call_df, args)
    write_manifest(args, answer_path, call_path)
    update_eda_summary(answer_df, args)
    print(f"EDA008 finished: {REPORT_PATH}")
    print(f"answers: {answer_path}")
    print(f"calls: {call_path}")


if __name__ == "__main__":
    main()
