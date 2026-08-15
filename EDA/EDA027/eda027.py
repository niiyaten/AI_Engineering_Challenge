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
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# EDA027は、test 100問で「わかりません」を許す従来方針のLLM提出候補を作る実験。
BASE_DIR = Path(__file__).resolve().parents[2]
API_KEY_PATH = BASE_DIR / ".apikey"
EMBEDDING_RECORDS_PATH = BASE_DIR / "data" / "processed" / "embedding" / "embedding_records.jsonl"
QUESTIONS_TEST_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_test.csv"
QUESTION_ROUTES_PATH = BASE_DIR / "EDA" / "EDA011" / "tables" / "question_routes.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
PROMPT_DIR = OUTPUT_DIR / "prompts"
PRED_DIR = OUTPUT_DIR / "predictions"
REPORT_PATH = OUTPUT_DIR / "eda027_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LLM_TEST_LOG_PATH = TABLE_DIR / "test_unknown_allowed_answer_log.csv"
ROUTE_SUMMARY_PATH = TABLE_DIR / "test_unknown_allowed_route_summary.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-3.5-flash"


def setup() -> None:
    """出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)


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


def safe_label(value: Any) -> str:
    """ファイル名に使える短いラベルへ変換する。"""
    label = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_").lower()
    return label or "unknown"


def output_zip_path(args: argparse.Namespace) -> Path:
    """providerとmodelが分かる提出zip名を返す。"""
    return PRED_DIR / f"eda027_{safe_label(args.provider)}_{safe_label(args.model)}_unknown_allowed_submission.zip"


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


def read_api_key(provider: str) -> str:
    """ローカルの.apikeyからprovider別のAPIキーを読む。成果物には保存しない。"""
    if not API_KEY_PATH.exists():
        raise FileNotFoundError(f"{relative(API_KEY_PATH)} が見つかりません。")
    key_map: dict[str, str] = {}
    unnamed_values: list[str] = []
    for line in API_KEY_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, value = line.split("=", 1)
            normalized_name = normalize_key_name(name)
            cleaned_value = value.strip().strip('"').strip("'")
            if cleaned_value:
                key_map[normalized_name] = cleaned_value
            continue
        unnamed_values.append(line.strip().strip('"').strip("'"))

    provider_key_candidates = {
        "gemini": ["gemini", "gemini_api_key", "google_api_key"],
        "openrouter": ["openrouter", "openrouter_api_key"],
    }.get(provider, [provider])
    for key_name in provider_key_candidates:
        if key_map.get(key_name):
            return key_map[key_name]
    if provider == "openrouter" and unnamed_values:
        return unnamed_values[0]
    raise ValueError(f".apikey に {provider} 用APIキーが見つかりません。")


def normalize_key_name(value: str) -> str:
    """APIキー名の表記揺れを吸収する。"""
    return re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKC", value).strip().lower()).strip("_")


def load_records() -> list[dict[str, Any]]:
    """EDA020の統合JSONLを読む。"""
    records = []
    for line in EMBEDDING_RECORDS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_routes() -> dict[int, str]:
    """EDA011のtest質問ルートを読む。"""
    df = pd.read_csv(QUESTION_ROUTES_PATH)
    return {int(row["index"]): str(row["route"]) for _, row in df[df["split"] == "test"].iterrows()}


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
        "根拠から判断できない場合は、無理に推測せず「わかりません」と答えてください。"
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
            "X-Title": "SIGNATE Agentic RAG EDA027",
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


def call_gemini(api_key: str, messages: list[dict[str, str]], args: argparse.Namespace) -> dict[str, Any]:
    """Gemini Interactions APIへ1回問い合わせる。"""
    system = "\n\n".join(message["content"] for message in messages if message["role"] == "system")
    user = "\n\n".join(message["content"] for message in messages if message["role"] != "system")
    body = {
        "model": args.model,
        "system_instruction": system,
        "input": user,
        "generation_config": {
            "temperature": args.temperature,
            "max_output_tokens": args.max_tokens,
        },
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        GEMINI_INTERACTIONS_URL,
        data=data,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
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


def call_llm(api_key: str, messages: list[dict[str, str]], args: argparse.Namespace) -> dict[str, Any]:
    """providerに応じてLLM APIを呼び分ける。"""
    if args.provider == "gemini":
        return call_gemini(api_key, messages, args)
    return call_openrouter(api_key, messages, args)


def extract_answer(payload: dict[str, Any], provider: str) -> str:
    """provider別の応答から回答本文を取り出す。"""
    if provider == "gemini":
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return strip_markup(output_text)
        candidates = payload.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return strip_markup("\n".join(part.get("text", "") for part in parts if isinstance(part, dict)))
        return strip_markup(collect_text_fields(payload))

    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return strip_markup(content or "")


def collect_text_fields(value: Any) -> str:
    """Gemini応答の形が変わっても、textフィールドを控えめに拾う。"""
    texts: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"text", "output_text"} and isinstance(child, str):
                texts.append(child)
            else:
                texts.append(collect_text_fields(child))
    elif isinstance(value, list):
        texts.extend(collect_text_fields(item) for item in value)
    return "\n".join(text for text in texts if text)


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
    """診断用に空回答や不明回答を判定する。"""
    text = normalize_for_match(answer)
    return not text or text in {"わかりません", "不明", "不明です", "根拠不足", "判断できません"}


def write_prompt_debug(index: int, messages: list[dict[str, str]]) -> Path:
    """正解を含まないプロンプト確認用Markdownを保存する。"""
    path = PROMPT_DIR / f"test_{index:03d}_prompt.md"
    lines = [f"# test_{index:03d} prompt"]
    for message in messages:
        lines.extend(["", f"## {message['role']}", "", message["content"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_test_llm(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """test 100問すべてに指定LLMで回答する。"""
    api_key = read_api_key(args.provider)
    questions = pd.read_csv(QUESTIONS_TEST_PATH)
    routes = load_routes()
    records = load_records()
    index = BM25Index(records)
    rows: list[dict[str, Any]] = []

    for _, qrow in questions.sort_values("index").iterrows():
        q_index = int(qrow["index"])
        question = str(qrow["question"])
        route = routes.get(q_index, "")
        query = f"{question}\nroute:{route}"
        retrieved = index.search(query, args.top_k)
        messages = build_messages(question, route, retrieved, args.max_context_chars)
        prompt_path = write_prompt_debug(q_index, messages)
        result = call_llm(api_key, messages, args)
        answer = extract_answer(result["payload"], args.provider) if result["ok"] else ""
        error_message = "" if answer else safe_error_message(result["payload"])
        raw_llm_answer = answer
        answer_source = "llm"
        # 提出CSVの空欄は避けるが、根拠不足時に検索断片で無理に埋めることはしない。
        if not strip_markup(answer):
            answer = "わかりません"
            answer_source = "empty_or_error_to_unknown"
        top_record = retrieved[0]["record"] if retrieved else {}
        rows.append(
            {
                "index": q_index,
                "route": route,
                "question": question,
                "answer": answer[: args.max_answer_chars],
                "raw_llm_answer": raw_llm_answer[: args.max_answer_chars],
                "answer_source": answer_source,
                "provider": args.provider,
                "model": args.model,
                "status": result["status"],
                "elapsed_sec": result["elapsed_sec"],
                "top1_record_type": top_record.get("record_type", ""),
                "top1_source_path": top_record.get("source_path", ""),
                "top1_score": retrieved[0]["score"] if retrieved else 0,
                "prompt_path": relative(prompt_path),
                "error_message": error_message,
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
                "success_status_200_count": sum(1 for row in items if int(row["status"]) == 200),
                "unknown_answer_count": sum(1 for row in items if is_unknown_answer(row["answer"])),
                "empty_or_error_to_unknown_count": sum(1 for row in items if row["answer_source"] == "empty_or_error_to_unknown"),
            }
        )
    return rows, route_summary


def write_report(rows: list[dict[str, Any]], route_summary: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """EDA027のレポートを保存する。"""
    status_counts = Counter(str(row["status"]) for row in rows)
    summary_rows = [
        {"metric": "test_question_count", "value": len(rows)},
        {"metric": "http_200_count", "value": sum(1 for row in rows if int(row["status"]) == 200)},
        {"metric": "unknown_answer_count", "value": sum(1 for row in rows if is_unknown_answer(row["answer"]))},
        {"metric": "empty_or_error_to_unknown_count", "value": sum(1 for row in rows if row["answer_source"] == "empty_or_error_to_unknown")},
        {"metric": "max_answer_length", "value": max((len(str(row["answer"])) for row in rows), default=0)},
    ]
    sample_rows = [
        {
            "index": row["index"],
            "route": row["route"],
            "answer": row["answer"][:160],
            "answer_source": row["answer_source"],
            "status": row["status"],
        }
        for row in rows
    ]
    lines = [
        "# EDA027: test 100問 unknown-allowed LLM提出候補",
        "",
        "## 目的",
        "",
        "EDA025でno-unknown方針が悪化したため、従来の `わかりません` を許す方針でtest 100問にLLM回答を実行し、提出形式zipを作成する。",
        "",
        "## 出力",
        "",
        f"- answer_log: `{relative(LLM_TEST_LOG_PATH)}`",
        f"- route_summary: `{relative(ROUTE_SUMMARY_PATH)}`",
        f"- predictions_csv: `{relative(PREDICTIONS_PATH)}`",
        f"- submission_zip: `{relative(output_zip_path(args))}`",
        f"- prompt_debug: `{relative(PROMPT_DIR)}`",
        "",
        "## 実行設定",
        "",
        f"- provider: `{args.provider}`",
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
        "凡例: `route` は質問ルート、`question_count` はtest質問数、`success_status_200_count` はHTTP 200件数、`unknown_answer_count` は不明回答数、`empty_or_error_to_unknown_count` はAPI失敗または空回答を `わかりません` にした件数です。",
        "",
        markdown_table(route_summary),
        "",
        "## HTTP status別件数",
        "",
        "凡例: `status` はLLM APIのHTTPステータス、`count` は件数を表します。",
        "",
        markdown_table([{"status": key, "count": value} for key, value in sorted(status_counts.items())]),
        "",
        "## 質問別結果",
        "",
        "凡例: `index` はtest質問番号、`route` は処理ルート、`answer` は最終回答、`answer_source` はLLM回答か空回答補完か、`status` はLLM APIのHTTPステータスを表します。",
        "",
        markdown_table(sample_rows, max_rows=30),
        "",
        "## 注意点",
        "",
        "- 根拠から判断できない場合は `わかりません` を許す。",
        "- API失敗または空回答の場合は、提出CSVの空欄を避けるため `わかりません` を入れる。",
        "- EDA025で悪化した検索断片フォールバックは使わない。",
        "- SIGNATEへの実提出は行っていない。",
        "- APIキーは `.apikey` から読み込み、成果物には保存しない。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_predictions(rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """提出形式のpredictions.csvとzipを保存する。"""
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in sorted(rows, key=lambda item: int(item["index"])):
            answer = re.sub(r"\s*\n\s*", " ", strip_markup(row["answer"]))
            writer.writerow([row["index"], answer])
    zip_path = output_zip_path(args)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_manifest(args: argparse.Namespace, rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA027",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Run unknown-allowed LLM pipeline on all test questions and create submission zip.",
        "parameters": {
            "provider": args.provider,
            "model": args.model,
            "top_k": args.top_k,
            "max_context_chars": args.max_context_chars,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        },
        "inputs": {
            "embedding_records": relative(EMBEDDING_RECORDS_PATH),
            "questions_test": relative(QUESTIONS_TEST_PATH),
            "question_routes": relative(QUESTION_ROUTES_PATH),
            "api_key": ".apikey (not stored)",
        },
        "outputs": {
            "answer_log": relative(LLM_TEST_LOG_PATH),
            "route_summary": relative(ROUTE_SUMMARY_PATH),
            "predictions_csv": relative(PREDICTIONS_PATH),
            "submission_zip": relative(output_zip_path(args)),
            "report": relative(REPORT_PATH),
        },
        "test_question_count": len(rows),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Run unknown-allowed LLM pipeline on test questions.")
    parser.add_argument("--provider", choices=["gemini", "openrouter"], default=DEFAULT_PROVIDER, help="LLM provider")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model id")
    parser.add_argument("--top-k", type=int, default=12, help="LLMへ渡す検索根拠数")
    parser.add_argument("--max-context-chars", type=int, default=24000, help="LLMへ渡す根拠本文の最大文字数")
    parser.add_argument("--max-answer-chars", type=int, default=900, help="ログに保存する回答の最大文字数")
    parser.add_argument("--max-tokens", type=int, default=900, help="最大出力トークン数")
    parser.add_argument("--temperature", type=float, default=0.0, help="OpenRouter temperature")
    parser.add_argument("--timeout-sec", type=int, default=120, help="APIタイムアウト秒")
    parser.add_argument("--sleep-sec", type=float, default=1.5, help="API呼び出し間隔秒")
    return parser.parse_args()


def main() -> None:
    """EDA027を実行する。"""
    args = parse_args()
    setup()
    rows, route_summary = run_test_llm(args)
    save_csv(rows, LLM_TEST_LOG_PATH)
    save_csv(route_summary, ROUTE_SUMMARY_PATH)
    write_predictions(rows, args)
    write_report(rows, route_summary, args)
    write_manifest(args, rows)
    print(
        " ".join(
            [
                f"test={len(rows)}",
                f"http200={sum(1 for row in rows if int(row['status']) == 200)}",
                f"unknown={sum(1 for row in rows if is_unknown_answer(row['answer']))}",
                f"empty_or_error_to_unknown={sum(1 for row in rows if row['answer_source'] == 'empty_or_error_to_unknown')}",
                f"zip={relative(output_zip_path(args))}",
                f"report={relative(REPORT_PATH)}",
            ]
        )
    )


if __name__ == "__main__":
    main()
