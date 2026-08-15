from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# eda021.py は「プロジェクト直下 / EDA / EDA021 / eda021.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
EMBEDDING_RECORDS_PATH = BASE_DIR / "data" / "processed" / "embedding" / "embedding_records.jsonl"
QUESTIONS_TEST_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_test.csv"
QUESTION_ROUTES_PATH = BASE_DIR / "EDA" / "EDA011" / "tables" / "question_routes.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
CONTEXT_DIR = OUTPUT_DIR / "contexts"
PRED_DIR = OUTPUT_DIR / "predictions"
REPORT_PATH = OUTPUT_DIR / "eda021_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda021.log"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda021_local_rag_submission.zip"


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def normalize_text(value: Any) -> str:
    """検索のために表記をNFC、小文字、半角寄せにする。"""
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    return text.lower()


def compact_text(value: Any) -> str:
    """回答やログ用に空白を整える。"""
    text = unicodedata.normalize("NFC", "" if value is None else str(value))
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
    """Markdown表を壊しやすい文字だけを逃がす。"""
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
    text = normalize_text(text)
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
    """外部依存なしの小規模BM25インデックス。"""

    def __init__(self, records: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.records = records
        self.k1 = k1
        self.b = b
        self.doc_tokens: list[list[str]] = []
        self.doc_tf: list[Counter[str]] = []
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
            self.doc_tokens.append(tokens)
            tf = Counter(tokens)
            self.doc_tf.append(tf)
            self.df.update(tf.keys())
        self.doc_len = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / max(len(self.doc_len), 1)
        self.n_docs = len(records)

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
        results = []
        for score, idx in scores[:top_k]:
            record = self.records[idx]
            results.append({"score": round(score, 6), "record": record})
        return results


def load_records() -> list[dict[str, Any]]:
    """EDA020の統合JSONLを読む。"""
    records = []
    for line in EMBEDDING_RECORDS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_routes() -> dict[int, str]:
    """EDA011のtest質問ルートを読む。"""
    if not QUESTION_ROUTES_PATH.exists():
        return {}
    df = pd.read_csv(QUESTION_ROUTES_PATH)
    routes = {}
    for _, row in df[df["split"] == "test"].iterrows():
        routes[int(row["index"])] = str(row.get("route", ""))
    return routes


def useful_line(line: str) -> bool:
    """回答候補として使いやすい行だけを残す。"""
    line = compact_text(line)
    if len(line) < 6 or len(line) > 500:
        return False
    # 検索には役立つが、回答文に混ぜるとノイズになる管理情報を除外する。
    metadata_prefixes = (
        "元パス:",
        "パス:",
        "ファイル名:",
        "Image:",
        "画像:",
        "raw_path:",
        "processed_path:",
        "source_path:",
        "record_id:",
        "record_type:",
        "- raw_path:",
        "- processed_path:",
        "- source_path:",
    )
    if line.startswith(metadata_prefixes):
        return False
    if line.startswith("| ---") or line.startswith("```"):
        return False
    if line.startswith("#"):
        return False
    if line in {"該当データはありません。", "[no text extracted]"}:
        return False
    return True


def candidate_lines(question: str, retrieved: list[dict[str, Any]]) -> list[tuple[float, str]]:
    """検索結果から、質問トークンに近い行を抽出する。"""
    q_tokens = set(tokenize(question))
    rows: list[tuple[float, str]] = []
    for rank, item in enumerate(retrieved, start=1):
        record = item["record"]
        source_bonus = 1.0 / rank
        for line in compact_text(record.get("text_for_embedding", "")).splitlines():
            line = compact_text(line)
            if not useful_line(line):
                continue
            line_tokens = set(tokenize(line))
            overlap = len(q_tokens & line_tokens)
            score = overlap + source_bonus
            if overlap > 0:
                rows.append((score, line))
    rows.sort(reverse=True)
    unique = []
    seen = set()
    for score, line in rows:
        key = normalize_text(line)
        if key in seen:
            continue
        seen.add(key)
        unique.append((score, line))
    return unique


def extract_parameter_answer(question: str, evidence: str) -> str:
    """パラメータ値を聞く質問に対して、根拠内の name=value を拾う。"""
    params = re.findall(r"(?:パラメータである|parameter\s+|param\s+)([A-Za-z_][A-Za-z0-9_]*)", question)
    params += re.findall(r"([A-Za-z_][A-Za-z0-9_]*)はいくら", question)
    for param in dict.fromkeys(params):
        patterns = [
            rf"{re.escape(param)}\s*[:=]\s*['\"]?([A-Za-z0-9_.+-]+)",
            rf"['\"]{re.escape(param)}['\"]\s*:\s*['\"]?([A-Za-z0-9_.+-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, evidence)
            if match:
                return match.group(1)
    return ""


def fallback_snippet(record: dict[str, Any], max_chars: int) -> str:
    """低信頼時でも、管理情報ではなく本文らしい行を返す。"""
    lines = []
    for line in compact_text(record.get("text_for_embedding", "")).splitlines():
        line = compact_text(line)
        if useful_line(line):
            lines.append(line)
    if lines:
        return "、".join(lines[:5])[:max_chars]
    return compact_text(record.get("text_for_embedding", ""))[:max_chars]


def generate_answer(question: str, retrieved: list[dict[str, Any]], max_chars: int) -> tuple[str, str]:
    """検索根拠から抽出型の回答を作る。"""
    if not retrieved:
        return "わかりません", "no_retrieval"
    top_score = float(retrieved[0]["score"])
    evidence = "\n".join(item["record"].get("text_for_embedding", "") for item in retrieved[:5])
    param_answer = extract_parameter_answer(question, evidence)
    if param_answer:
        return param_answer[:max_chars], "parameter_regex"

    lines = candidate_lines(question, retrieved)
    if not lines or top_score < 1.0:
        snippet = fallback_snippet(retrieved[0]["record"], max_chars)
        if not snippet:
            return "わかりません", "low_score_no_snippet"
        return snippet, "top_snippet_low_confidence"

    if any(token in question for token in ["すべて", "挙げて", "列挙", "変更内容"]):
        selected = [line for _, line in lines[:5]]
        return "、".join(selected)[:max_chars], "multi_line_extractive"

    selected = lines[0][1]
    return selected[:max_chars], "best_line_extractive"


def write_context(index: int, question: str, route: str, answer: str, retrieved: list[dict[str, Any]]) -> Path:
    """各質問のRAGコンテキストをMarkdownで保存する。"""
    path = CONTEXT_DIR / f"test_{index:03d}_context.md"
    lines = [
        f"# test_{index:03d}",
        "",
        "## Question",
        question,
        "",
        "## Route",
        route,
        "",
        "## Generated Answer",
        answer,
        "",
        "## Retrieved Records",
    ]
    for rank, item in enumerate(retrieved, start=1):
        record = item["record"]
        lines.extend(
            [
                "",
                f"### Rank {rank}",
                f"- score: {item['score']}",
                f"- record_id: `{record.get('record_id', '')}`",
                f"- record_type: `{record.get('record_type', '')}`",
                f"- source_path: `{record.get('source_path', '')}`",
                "",
                "```text",
                compact_text(record.get("text_for_embedding", ""))[:3000],
                "```",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_rag(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """test 100問へBM25 RAGを実行する。"""
    records = load_records()
    index = BM25Index(records)
    questions = pd.read_csv(QUESTIONS_TEST_PATH)
    routes = load_routes()
    prediction_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    for _, row in questions.iterrows():
        q_index = int(row["index"])
        question = str(row["question"])
        route = routes.get(q_index, "")
        query = f"{question}\nroute:{route}"
        retrieved = index.search(query, args.top_k)
        answer, answer_method = generate_answer(question, retrieved, args.max_answer_chars)
        context_path = write_context(q_index, question, route, answer, retrieved)
        prediction_rows.append({"index": q_index, "answer": answer})
        for rank, item in enumerate(retrieved, start=1):
            record = item["record"]
            retrieval_rows.append(
                {
                    "index": q_index,
                    "question": question,
                    "route": route,
                    "rank": rank,
                    "score": item["score"],
                    "answer_method": answer_method,
                    "predicted_answer": answer,
                    "record_id": record.get("record_id", ""),
                    "record_type": record.get("record_type", ""),
                    "source_path": record.get("source_path", ""),
                    "context_path": relative(context_path),
                    "text_preview": compact_text(record.get("text_for_embedding", ""))[:500],
                }
            )
    return prediction_rows, retrieval_rows


def write_predictions(prediction_rows: list[dict[str, Any]]) -> None:
    """提出形式のpredictions.csvとzipを作る。"""
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in sorted(prediction_rows, key=lambda r: int(r["index"])):
            answer = re.sub(r"\s*\n\s*", " ", compact_text(row["answer"]))
            writer.writerow([row["index"], answer])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(prediction_rows: list[dict[str, Any]], retrieval_rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """EDA021の実行結果をMarkdownレポートへ保存する。"""
    answer_lengths = [len(str(row["answer"])) for row in prediction_rows]
    route_counts = Counter(row["route"] for row in retrieval_rows if int(row["rank"]) == 1)
    method_counts = Counter(row["answer_method"] for row in retrieval_rows if int(row["rank"]) == 1)
    rows = [
        {"metric": "prediction_count", "value": len(prediction_rows)},
        {"metric": "empty_answer_count", "value": sum(1 for row in prediction_rows if not str(row["answer"]).strip())},
        {"metric": "unknown_answer_count", "value": sum(1 for row in prediction_rows if str(row["answer"]).strip() == "わかりません")},
        {"metric": "max_answer_length", "value": max(answer_lengths) if answer_lengths else 0},
        {"metric": "min_answer_length", "value": min(answer_lengths) if answer_lengths else 0},
    ]
    lines = [
        "# EDA021: test 100問ローカルRAG",
        "",
        "## 目的",
        "",
        "EDA020の統合JSONLを使い、test 100問に対してローカルBM25検索と抽出型回答生成を実行し、提出形式の `predictions.csv` とzipを作る。",
        "",
        "## 出力",
        "",
        f"- predictions_csv: `{relative(PREDICTIONS_PATH)}`",
        f"- submission_zip: `{relative(ZIP_PATH)}`",
        f"- retrieval_log: `{relative(TABLE_DIR / 'test_rag_retrieval.csv')}`",
        f"- contexts: `{relative(CONTEXT_DIR)}`",
        "",
        "## 実行設定",
        "",
        f"- top_k: {args.top_k}",
        f"- max_answer_chars: {args.max_answer_chars}",
        "- LLM API: 未使用",
        "",
        "## 出力検証",
        "",
        "凡例: `metric` は検証項目、`value` は値を表します。",
        "",
        markdown_table(rows),
        "",
        "## route別件数",
        "",
        "凡例: `route` はEDA011で推定した処理ルート、`count` はtest質問数を表します。",
        "",
        markdown_table([{"route": k, "count": v} for k, v in sorted(route_counts.items())], max_rows=30),
        "",
        "## answer_method別件数",
        "",
        "凡例: `answer_method` は回答生成方法、`count` は件数を表します。",
        "",
        markdown_table([{"answer_method": k, "count": v} for k, v in sorted(method_counts.items())], max_rows=30),
        "",
        "## 注意点",
        "",
        "- このEDAは提出形式確認を兼ねたローカルRAGであり、GPT-OSS-120bなどのLLM回答生成はまだ使っていない。",
        "- 表計算、差分、書式、画像数値抽出は専用処理を未実装のため、抽出型回答では誤る可能性がある。",
        "- 実提出前には、少なくともvalidでroute別の回答精度を確認する必要がある。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(args: argparse.Namespace, prediction_rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA021",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Run local BM25 RAG on test questions and create predictions.csv/zip.",
        "parameters": {"top_k": args.top_k, "max_answer_chars": args.max_answer_chars},
        "inputs": {
            "embedding_records": relative(EMBEDDING_RECORDS_PATH),
            "questions_test": relative(QUESTIONS_TEST_PATH),
        },
        "outputs": {
            "predictions_csv": relative(PREDICTIONS_PATH),
            "submission_zip": relative(ZIP_PATH),
            "report": relative(REPORT_PATH),
        },
        "prediction_count": len(prediction_rows),
        "repro_steps": [
            "uv run python EDA/EDA020/eda020.py",
            "uv run python EDA/EDA021/eda021.py",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Run local BM25 RAG for test questions.")
    parser.add_argument("--top-k", type=int, default=8, help="質問ごとの取得レコード数")
    parser.add_argument("--max-answer-chars", type=int, default=900, help="提出回答の最大文字数")
    return parser.parse_args()


def main() -> None:
    """EDA021を実行する。"""
    args = parse_args()
    setup()
    prediction_rows, retrieval_rows = run_rag(args)
    write_predictions(prediction_rows)
    save_csv(retrieval_rows, TABLE_DIR / "test_rag_retrieval.csv")
    write_report(prediction_rows, retrieval_rows, args)
    write_manifest(args, prediction_rows)
    print(f"predictions={len(prediction_rows)} csv={relative(PREDICTIONS_PATH)} zip={relative(ZIP_PATH)}")


if __name__ == "__main__":
    main()
