from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# EDA025は、valid 30問で「わかりません」を出さないLLMパイプラインを検証する実験。
BASE_DIR = Path(__file__).resolve().parents[2]
API_KEY_PATH = BASE_DIR / ".apikey"
EMBEDDING_RECORDS_PATH = BASE_DIR / "data" / "processed" / "embedding" / "embedding_records.jsonl"
QUESTIONS_VALID_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_valid.csv"
QUESTION_ROUTES_PATH = BASE_DIR / "EDA" / "EDA011" / "tables" / "question_routes.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
PROMPT_DIR = OUTPUT_DIR / "prompts"
REPORT_PATH = OUTPUT_DIR / "eda025_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LLM_VALID_LOG_PATH = TABLE_DIR / "valid_no_unknown_answer_log.csv"
ROUTE_SUMMARY_PATH = TABLE_DIR / "valid_no_unknown_route_summary.csv"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b:free"


def setup() -> None:
    """出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)


def compact_text(value: Any) -> str:
    """CSV、Markdown、API入力で扱いやすいように空白を整える。"""
    text = unicodedata.normalize("NFC", "" if value is None else str(value))
    text = html.unescape(text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_markup(value: Any) -> str:
    """Word由来MarkdownのHTMLタグやコメントをLLM入力前に落とす。"""
    text = compact_text(value)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_match(value: Any) -> str:
    """評価用に表記揺れを軽く吸収する。"""
    text = unicodedata.normalize("NFKC", strip_markup(value)).lower()
    text = text.replace("，", ",").replace("、", ",")
    text = re.sub(r"[「」『』【】\[\]\(\)（）\s]", "", text)
    return text


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


def tokenize(text: str) -> list[str]:
    """日本語と英数字が混ざる質問・文書を、BM25用トークンへ変換する。"""
    text = unicodedata.normalize("NFKC", strip_markup(text)).lower()
    tokens: list[str] = []
    for term in re.findall(r"[a-z0-9_./:-]+|[一-龥ぁ-んァ-ヶー]+", text):
        if len(term) <= 1:
            tokens.append(term)
            continue
        tokens.append(term)
        if re.search(r"[一-龥ぁ-んァ-ヶー]", term):
            tokens.extend(term[i : i + 2] for i in range(len(term) - 1))
            if len(term) >= 3:
                tokens.extend(term[i : i + 3] for i in range(len(term) - 2))
    return [token for token in tokens if token.strip()]


class BM25Index:
    """LLMへ渡す根拠候補を探すためのBM25インデックス。"""

    def __init__(self, records: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.records = records
        self.k1 = k1
        self.b = b
        self.doc_tf: list[Counter[str]] = []
        self.doc_len: list[int] = []
        self.df: Counter[str] = Counter()
        for record in records:
            text = "\n".join(
                [
                    record.get("text_for_embedding", ""),
                    record.get("source_path", ""),
                    record.get("record_type", ""),
                    str(record.get("metadata", {}).get("file_type", "")),
                ]
            )
            tokens = tokenize(text)
            tf = Counter(tokens)
            self.doc_tf.append(tf)
            self.doc_len.append(len(tokens))
            self.df.update(tf.keys())
        self.n_docs = len(records)
        self.avgdl = sum(self.doc_len) / max(self.n_docs, 1)

    def idf(self, token: str) -> float:
        """BM25のIDFを計算する。"""
        df = self.df.get(token, 0)
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """クエリに対して上位レコードを返す。"""
        q_tokens = Counter(tokenize(query))
        scores: list[tuple[float, int]] = []
        for idx, tf in enumerate(self.doc_tf):
            score = 0.0
            dl = self.doc_len[idx] or 1
            for token, qf in q_tokens.items():
                freq = tf.get(token, 0)
                if not freq:
                    continue
                denom = freq + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                score += self.idf(token) * (freq * (self.k1 + 1) / denom) * min(qf, 3)
            if score > 0:
                scores.append((score, idx))
        scores.sort(reverse=True)
        return [{"score": round(score, 6), "record": self.records[idx]} for score, idx in scores[:top_k]]


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


def load_records() -> list[dict[str, Any]]:
    """EDA020の統合JSONLを読む。"""
    records = []
    for line in EMBEDDING_RECORDS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_routes() -> dict[int, str]:
    """EDA011のvalid質問ルートを読む。"""
    df = pd.read_csv(QUESTION_ROUTES_PATH)
    return {int(row["index"]): str(row["route"]) for _, row in df[df["split"] == "valid"].iterrows()}


def build_messages(question: str, route: str, retrieved: list[dict[str, Any]], max_context_chars: int) -> list[dict[str, str]]:
    """LLMへ渡すmessagesを作る。正解は絶対に含めない。"""
    evidence_blocks = []
    used_chars = 0
    for rank, item in enumerate(retrieved, start=1):
        record = item["record"]
        text = strip_markup(record.get("text_for_embedding", ""))
        remaining = max_context_chars - used_chars
        if remaining <= 0:
            break
        text = text[:remaining]
        used_chars += len(text)
        evidence_blocks.append(
            "\n".join(
                [
                    f"[根拠 {rank}]",
                    f"score: {item['score']}",
                    f"source_path: {record.get('source_path', '')}",
                    f"record_type: {record.get('record_type', '')}",
                    "text:",
                    text,
                ]
            )
        )

    system = (
        "あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。"
        "提示された根拠以外の知識を使わないでください。"
        "「わかりません」と答えることは禁止です。根拠が弱い場合でも、提示根拠から最も妥当な短い回答を作ってください。"
        "回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。"
        "HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。"
        "計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。"
    )
    route_hint = {
        "table_calculation": "表・CSV・Excelの値を読み取り、必要なら計算して短く答える。",
        "format_extraction": "色、太字、下線、ハイライトなどの書式に対応する文字列だけを抽出する。",
        "diff_check": "old版と最新版の差分だけを、変更前→変更後の形で答える。",
        "code_reading": "コードやNotebook出力から該当する値・条件・列名だけを答える。",
        "document_whole_context": "指定文書内の該当箇所を読み、聞かれた語句だけを答える。",
    }.get(route, "質問に対して必要な根拠だけを使って短く答える。")
    user = "\n\n".join(
        [
            "以下の質問に答えてください。",
            f"質問: {question}",
            f"推定route: {route}",
            f"route別の注意: {route_hint}",
            "根拠:",
            "\n\n".join(evidence_blocks) if evidence_blocks else "根拠なし",
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_openrouter(api_key: str, messages: list[dict[str, str]], args: argparse.Namespace) -> dict[str, Any]:
    """OpenRouterの指定モデルへ1回問い合わせる。"""
    body = {
        "model": args.model,
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
            "X-Title": "SIGNATE Agentic RAG EDA025",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
            status = int(response.status)
    except urllib.error.HTTPError as exc:
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
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return strip_markup(content or "")


def safe_error_message(payload: dict[str, Any]) -> str:
    """APIキーを含めず、エラー概要だけを保存する。"""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if choices:
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        if message.get("content") is None:
            return f"content is null; finish_reason={choice.get('finish_reason', '')}; native_finish_reason={choice.get('native_finish_reason', '')}"[:500]
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        parts = [compact_text(error.get("message", ""))]
        metadata = error.get("metadata")
        if isinstance(metadata, dict) and metadata.get("raw"):
            parts.append(compact_text(metadata.get("raw", "")))
        return " | ".join(part for part in parts if part)[:500]
    return compact_text(payload)[:500]


def is_unknown_answer(answer: str) -> bool:
    """提出候補として避けたい空回答や不明回答を判定する。"""
    text = normalize_for_match(answer)
    return not text or text in {"わかりません", "不明", "不明です", "根拠不足", "判断できません"}


def fallback_answer_from_retrieved(question: str, retrieved: list[dict[str, Any]], max_chars: int) -> str:
    """LLMが不明回答になった場合、検索根拠から必ず短い代替回答を作る。"""
    q_tokens = set(tokenize(question))
    candidates: list[tuple[float, str]] = []
    for rank, item in enumerate(retrieved, start=1):
        text = strip_markup(item["record"].get("text_for_embedding", ""))
        for line in re.split(r"[\n。]", text):
            line = strip_markup(line)
            if len(line) < 2 or len(line) > 240:
                continue
            if line.startswith(("元パス:", "ファイル名:", "source_path:", "record_id:", "record_type:")):
                continue
            overlap = len(q_tokens & set(tokenize(line)))
            numeric_bonus = 1 if re.search(r"\d", line) else 0
            score = overlap + numeric_bonus + 1.0 / rank
            if score > 0:
                candidates.append((score, line))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1][:max_chars]
    if retrieved:
        return strip_markup(retrieved[0]["record"].get("text_for_embedding", ""))[:max_chars]
    return "該当なし"


def score_prediction(prediction: str, answer: str) -> dict[str, Any]:
    """valid正解との簡易評価を返す。"""
    pred = normalize_for_match(prediction)
    gold = normalize_for_match(answer)
    pred_tokens = set(tokenize(prediction))
    gold_tokens = set(tokenize(answer))
    overlap = len(pred_tokens & gold_tokens)
    return {
        "exact_match": int(bool(gold) and pred == gold),
        "contains_gold": int(bool(gold) and gold in pred),
        "contained_by_gold": int(bool(pred) and pred in gold),
        "token_recall": round(overlap / max(len(gold_tokens), 1), 4),
    }


def answer_in_context(answer: str, retrieved: list[dict[str, Any]]) -> bool:
    """正解文字列が検索上位contextに含まれるかを見る。"""
    gold = normalize_for_match(answer)
    evidence = normalize_for_match("\n".join(item["record"].get("text_for_embedding", "") for item in retrieved))
    return bool(gold) and gold in evidence


def write_prompt_debug(index: int, messages: list[dict[str, str]]) -> Path:
    """正解を含まないプロンプト確認用Markdownを保存する。"""
    path = PROMPT_DIR / f"valid_{index:03d}_prompt.md"
    lines = [f"# valid_{index:03d} prompt"]
    for message in messages:
        lines.extend(["", f"## {message['role']}", "", message["content"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_valid_llm(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """valid 30問すべてに指定LLMで回答する。"""
    api_key = read_api_key()
    questions = pd.read_csv(QUESTIONS_VALID_PATH)
    routes = load_routes()
    records = load_records()
    index = BM25Index(records)
    rows: list[dict[str, Any]] = []

    for _, qrow in questions.sort_values("index").iterrows():
        q_index = int(qrow["index"])
        question = str(qrow["question"])
        gold = str(qrow["answer"])
        route = routes.get(q_index, "")
        query = f"{question}\nroute:{route}"
        retrieved = index.search(query, args.top_k)
        messages = build_messages(question, route, retrieved, args.max_context_chars)
        prompt_path = write_prompt_debug(q_index, messages)
        result = call_openrouter(api_key, messages, args)
        answer = extract_answer(result["payload"]) if result["ok"] else ""
        error_message = "" if answer else safe_error_message(result["payload"])
        raw_llm_answer = answer
        answer_source = "llm"
        if is_unknown_answer(answer):
            answer = fallback_answer_from_retrieved(question, retrieved, args.max_answer_chars)
            answer_source = "retrieval_fallback"
        score = score_prediction(answer, gold)
        top_record = retrieved[0]["record"] if retrieved else {}
        rows.append(
            {
                "index": q_index,
                "route": route,
                "question": question,
                "gold_answer": gold,
                "llm_answer": answer[: args.max_answer_chars],
                "raw_llm_answer": raw_llm_answer[: args.max_answer_chars],
                "answer_source": answer_source,
                "model": args.model,
                "status": result["status"],
                "elapsed_sec": result["elapsed_sec"],
                "answer_in_topk_context": int(answer_in_context(gold, retrieved)),
                "top1_record_type": top_record.get("record_type", ""),
                "top1_source_path": top_record.get("source_path", ""),
                "top1_score": retrieved[0]["score"] if retrieved else 0,
                "prompt_path": relative(prompt_path),
                "error_message": error_message,
                **score,
            }
        )
        time.sleep(args.sleep_sec)

    route_summary = []
    for route in sorted(set(row["route"] for row in rows)):
        items = [row for row in rows if row["route"] == route]
        route_summary.append(
            {
                "route": route,
                "question_count": len(items),
                "exact_match_count": sum(row["exact_match"] for row in items),
                "contains_gold_count": sum(row["contains_gold"] for row in items),
                "answer_in_topk_context_count": sum(row["answer_in_topk_context"] for row in items),
                "avg_token_recall": round(sum(row["token_recall"] for row in items) / max(len(items), 1), 4),
                "success_status_200_count": sum(1 for row in items if int(row["status"]) == 200),
            }
        )
    return rows, route_summary


def write_report(rows: list[dict[str, Any]], route_summary: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """EDA025のレポートを保存する。"""
    status_counts = Counter(str(row["status"]) for row in rows)
    summary_rows = [
        {"metric": "valid_question_count", "value": len(rows)},
        {"metric": "http_200_count", "value": sum(1 for row in rows if int(row["status"]) == 200)},
        {"metric": "exact_match_count", "value": sum(row["exact_match"] for row in rows)},
        {"metric": "contains_gold_count", "value": sum(row["contains_gold"] for row in rows)},
        {"metric": "answer_in_topk_context_count", "value": sum(row["answer_in_topk_context"] for row in rows)},
        {"metric": "avg_token_recall", "value": round(sum(row["token_recall"] for row in rows) / max(len(rows), 1), 4)},
        {"metric": "unknown_answer_count", "value": sum(1 for row in rows if is_unknown_answer(row["llm_answer"]))},
        {"metric": "retrieval_fallback_count", "value": sum(1 for row in rows if row["answer_source"] == "retrieval_fallback")},
    ]
    sample_rows = [
        {
            "index": row["index"],
            "route": row["route"],
            "gold_answer": row["gold_answer"],
            "llm_answer": row["llm_answer"][:160],
            "answer_source": row["answer_source"],
            "exact_match": row["exact_match"],
            "contains_gold": row["contains_gold"],
        }
        for row in rows
    ]
    lines = [
        "# EDA025: valid 30問 no-unknown LLM回答生成",
        "",
        "## 目的",
        "",
        "EDA024でLLM回答の改善が見えた一方で `わかりません` が残ったため、valid 30問で不明回答を出さないパイプラインを検証する。",
        "",
        "## 出力",
        "",
        f"- answer_log: `{relative(LLM_VALID_LOG_PATH)}`",
        f"- route_summary: `{relative(ROUTE_SUMMARY_PATH)}`",
        f"- prompt_debug: `{relative(PROMPT_DIR)}`",
        "",
        "## 実行設定",
        "",
        f"- model: `{args.model}`",
        f"- top_k: {args.top_k}",
        f"- max_context_chars: {args.max_context_chars}",
        f"- max_tokens: {args.max_tokens}",
        f"- temperature: {args.temperature}",
        "",
        "## 全体指標",
        "",
        "凡例: `metric` は診断指標、`value` は値を表します。",
        "",
        markdown_table(summary_rows),
        "",
        "## route別診断",
        "",
        "凡例: `route` は質問ルート、`question_count` はvalid質問数、`exact_match_count` は正規化完全一致数、`contains_gold_count` は予測文に正解が含まれた件数、`answer_in_topk_context_count` は上位検索根拠に正解文字列が含まれた件数、`avg_token_recall` は正解語句トークンの回収率平均、`success_status_200_count` はHTTP 200件数です。",
        "",
        markdown_table(route_summary),
        "",
        "## HTTP status別件数",
        "",
        "凡例: `status` はOpenRouterのHTTPステータス、`count` は件数を表します。",
        "",
        markdown_table([{"status": key, "count": value} for key, value in sorted(status_counts.items())]),
        "",
        "## 質問別結果",
        "",
        "凡例: `index` はvalid質問番号、`route` は処理ルート、`gold_answer` は正解、`llm_answer` は最終回答、`answer_source` はLLM回答か検索フォールバックか、`exact_match` は正規化完全一致、`contains_gold` は回答に正解文字列が含まれるかを表します。",
        "",
        markdown_table(sample_rows, max_rows=30),
        "",
        "## 注意点",
        "",
        "- valid正解はプロンプトには入れていない。正解は実行後の評価だけに使った。",
        "- `わかりません` または空回答の場合は、検索上位根拠から本文行を選んでフォールバックした。",
        "- 不明回答をなくす実験なので、精度よりも提出時の空振り回避を優先している。",
        "- APIキーは `.apikey` から読み込み、成果物には保存しない。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(args: argparse.Namespace, rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA025",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Run no-unknown OpenRouter LLM pipeline on all valid questions.",
        "parameters": {
            "model": args.model,
            "top_k": args.top_k,
            "max_context_chars": args.max_context_chars,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        },
        "inputs": {
            "embedding_records": relative(EMBEDDING_RECORDS_PATH),
            "questions_valid": relative(QUESTIONS_VALID_PATH),
            "question_routes": relative(QUESTION_ROUTES_PATH),
            "api_key": ".apikey (not stored)",
        },
        "outputs": {
            "answer_log": relative(LLM_VALID_LOG_PATH),
            "route_summary": relative(ROUTE_SUMMARY_PATH),
            "report": relative(REPORT_PATH),
        },
        "valid_question_count": len(rows),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Run no-unknown OpenRouter LLM pipeline on valid questions.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model id")
    parser.add_argument("--top-k", type=int, default=12, help="LLMへ渡す検索根拠数")
    parser.add_argument("--max-context-chars", type=int, default=24000, help="LLMへ渡す根拠本文の最大文字数")
    parser.add_argument("--max-answer-chars", type=int, default=900, help="ログに保存する回答の最大文字数")
    parser.add_argument("--max-tokens", type=int, default=900, help="OpenRouter max_tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=120, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.5, help="API呼び出し間隔秒")
    return parser.parse_args()


def main() -> None:
    """EDA025を実行する。"""
    args = parse_args()
    setup()
    rows, route_summary = run_valid_llm(args)
    save_csv(rows, LLM_VALID_LOG_PATH)
    save_csv(route_summary, ROUTE_SUMMARY_PATH)
    write_report(rows, route_summary, args)
    write_manifest(args, rows)
    print(
        " ".join(
            [
                f"valid={len(rows)}",
                f"http200={sum(1 for row in rows if int(row['status']) == 200)}",
                f"exact={sum(row['exact_match'] for row in rows)}",
                f"contains_gold={sum(row['contains_gold'] for row in rows)}",
                f"unknown={sum(1 for row in rows if is_unknown_answer(row['llm_answer']))}",
                f"fallback={sum(1 for row in rows if row['answer_source'] == 'retrieval_fallback')}",
                f"report={relative(REPORT_PATH)}",
            ]
        )
    )


if __name__ == "__main__":
    main()
