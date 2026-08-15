from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# EDA023は、test提出前にvalidでRAGの失敗要因を診断するための実験。
BASE_DIR = Path(__file__).resolve().parents[2]
EMBEDDING_RECORDS_PATH = BASE_DIR / "data" / "processed" / "embedding" / "embedding_records.jsonl"
QUESTIONS_VALID_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_valid.csv"
QUESTION_ROUTES_PATH = BASE_DIR / "EDA" / "EDA011" / "tables" / "question_routes.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
CONTEXT_DIR = OUTPUT_DIR / "contexts"
REPORT_PATH = OUTPUT_DIR / "eda023_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
VALID_DIAG_PATH = TABLE_DIR / "valid_local_rag_diagnosis.csv"
ROUTE_SUMMARY_PATH = TABLE_DIR / "valid_route_summary.csv"


def setup() -> None:
    """出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def compact_text(value: Any) -> str:
    """比較やログで扱いやすいように空白を整える。"""
    text = unicodedata.normalize("NFC", "" if value is None else str(value))
    text = html.unescape(text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_markup(value: Any) -> str:
    """Word由来MarkdownのHTMLタグやコメントを、回答用に落とす。"""
    text = compact_text(value)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_match(value: Any) -> str:
    """厳密一致ではなく、表記揺れを少し吸収して比較する。"""
    text = unicodedata.normalize("NFKC", strip_markup(value)).lower()
    text = text.replace("，", ",").replace("、", ",")
    text = re.sub(r"[「」『』【】\[\]\(\)（）\s]", "", text)
    text = text.replace("円", "円").replace("ドル", "ドル")
    return text


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
    """外部依存なしでvalid診断用のBM25検索を行う。"""

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


def useful_line(line: str) -> bool:
    """回答候補として使いやすい行だけを残す。"""
    line = strip_markup(line)
    if len(line) < 2 or len(line) > 500:
        return False
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
    if line.startswith("| ---") or line.startswith("```") or line.startswith("#"):
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
        for raw_line in compact_text(record.get("text_for_embedding", "")).splitlines():
            line = strip_markup(raw_line)
            if not useful_line(line):
                continue
            line_tokens = set(tokenize(line))
            overlap = len(q_tokens & line_tokens)
            if overlap > 0:
                rows.append((overlap + source_bonus, line))
    rows.sort(reverse=True)
    unique = []
    seen = set()
    for score, line in rows:
        key = normalize_for_match(line)
        if key in seen:
            continue
        seen.add(key)
        unique.append((score, line))
    return unique


def extract_numeric_difference(question: str, retrieved: list[dict[str, Any]]) -> tuple[str, str]:
    """「AとBの差」系の質問で、近い根拠文から数値差を計算する。"""
    if not any(token in question for token in ["差", "差額", "少なく", "改善幅"]):
        return "", ""
    evidence = "\n".join(strip_markup(item["record"].get("text_for_embedding", "")) for item in retrieved[:8])
    if "ML" in question or "機械学習" in question:
        ml_match = re.search(r"(?:ML|機械学習)[^。。\n]{0,80}?([0-9][0-9,]*(?:\.\d+)?)\s*ドル", evidence, flags=re.IGNORECASE)
        de_match = re.search(r"データエンジニア[^。。\n]{0,80}?([0-9][0-9,]*(?:\.\d+)?)\s*ドル", evidence)
        if ml_match and de_match:
            ml_value = float(ml_match.group(1).replace(",", ""))
            de_value = float(de_match.group(1).replace(",", ""))
            diff = abs(ml_value - de_value)
            return f"{diff:,.0f}ドル", f"numeric_difference: {ml_value:g} - {de_value:g}"
    return "", ""


def generate_answer(question: str, retrieved: list[dict[str, Any]], max_chars: int) -> tuple[str, str]:
    """valid診断用に、検索根拠から短い抽出型回答を作る。"""
    if not retrieved:
        return "わかりません", "no_retrieval"
    numeric_answer, method = extract_numeric_difference(question, retrieved)
    if numeric_answer:
        return numeric_answer[:max_chars], method

    lines = candidate_lines(question, retrieved)
    if not lines:
        snippet = strip_markup(retrieved[0]["record"].get("text_for_embedding", ""))
        return (snippet[:max_chars] if snippet else "わかりません"), "top_snippet_low_confidence"
    if any(token in question for token in ["すべて", "挙げて", "列挙", "変更", "抜き出"]):
        return "、".join(line for _, line in lines[:5])[:max_chars], "multi_line_extractive"
    return lines[0][1][:max_chars], "best_line_extractive"


def answer_in_context(answer: str, retrieved: list[dict[str, Any]]) -> bool:
    """正解文字列が検索上位contextに含まれるかを見る。"""
    gold = normalize_for_match(answer)
    evidence = normalize_for_match("\n".join(item["record"].get("text_for_embedding", "") for item in retrieved))
    if not gold:
        return False
    return gold in evidence


def score_prediction(prediction: str, answer: str) -> dict[str, Any]:
    """valid診断用の簡易評価を返す。"""
    pred = normalize_for_match(prediction)
    gold = normalize_for_match(answer)
    exact = int(pred == gold)
    contains_gold = int(bool(gold) and gold in pred)
    contained_by_gold = int(bool(pred) and pred in gold)
    pred_tokens = set(tokenize(prediction))
    gold_tokens = set(tokenize(answer))
    overlap = len(pred_tokens & gold_tokens)
    denom = max(len(gold_tokens), 1)
    return {
        "exact_match": exact,
        "contains_gold": contains_gold,
        "contained_by_gold": contained_by_gold,
        "token_recall": round(overlap / denom, 4),
    }


def diagnose_failure(row: dict[str, Any]) -> str:
    """検索と回答生成のどちらが主因らしいかを分類する。"""
    if row["exact_match"]:
        return "exact_match"
    if row["contains_gold"]:
        return "too_verbose_or_extra_text"
    if row["answer_in_topk_context"]:
        return "answer_extraction_or_calculation_failed"
    if row["top1_same_project_or_source"]:
        return "near_source_but_missing_answer"
    return "retrieval_failed"


def write_context(index: int, question: str, answer: str, prediction: str, retrieved: list[dict[str, Any]]) -> Path:
    """各valid質問の検索根拠をMarkdownで保存する。"""
    path = CONTEXT_DIR / f"valid_{index:03d}_context.md"
    lines = [
        f"# valid_{index:03d}",
        "",
        "## Question",
        question,
        "",
        "## Gold Answer",
        answer,
        "",
        "## Predicted Answer",
        prediction,
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
                strip_markup(record.get("text_for_embedding", ""))[:3000],
                "```",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_valid_diagnosis(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """valid 30問にローカルRAGをかけ、正解と比較する。"""
    records = load_records()
    routes = load_routes()
    index = BM25Index(records)
    questions = pd.read_csv(QUESTIONS_VALID_PATH)
    rows = []
    for _, qrow in questions.iterrows():
        q_index = int(qrow["index"])
        question = str(qrow["question"])
        gold = str(qrow["answer"])
        route = routes.get(q_index, "")
        query = f"{question}\nroute:{route}"
        retrieved = index.search(query, args.top_k)
        prediction, method = generate_answer(question, retrieved, args.max_answer_chars)
        context_path = write_context(q_index, question, gold, prediction, retrieved)
        top_record = retrieved[0]["record"] if retrieved else {}
        score = score_prediction(prediction, gold)
        row = {
            "index": q_index,
            "route": route,
            "question": question,
            "gold_answer": gold,
            "predicted_answer": prediction,
            "answer_method": method,
            "top1_record_type": top_record.get("record_type", ""),
            "top1_source_path": top_record.get("source_path", ""),
            "top1_score": retrieved[0]["score"] if retrieved else 0,
            "answer_in_topk_context": int(answer_in_context(gold, retrieved)),
            "top1_same_project_or_source": int(any(token in str(top_record.get("source_path", "")) for token in tokenize(question)[:20])),
            "context_path": relative(context_path),
            **score,
        }
        row["failure_type"] = diagnose_failure(row)
        rows.append(row)

    route_summary = []
    for route, items in defaultdict(list, {route: [row for row in rows if row["route"] == route] for route in sorted(set(row["route"] for row in rows))}).items():
        route_summary.append(
            {
                "route": route,
                "question_count": len(items),
                "exact_match_count": sum(row["exact_match"] for row in items),
                "contains_gold_count": sum(row["contains_gold"] for row in items),
                "answer_in_topk_context_count": sum(row["answer_in_topk_context"] for row in items),
                "avg_token_recall": round(sum(row["token_recall"] for row in items) / max(len(items), 1), 4),
            }
        )
    return rows, route_summary


def write_report(rows: list[dict[str, Any]], route_summary: list[dict[str, Any]], args: argparse.Namespace) -> None:
    """EDA023の診断レポートを保存する。"""
    failure_counts = Counter(row["failure_type"] for row in rows)
    summary_rows = [
        {"metric": "valid_question_count", "value": len(rows)},
        {"metric": "exact_match_count", "value": sum(row["exact_match"] for row in rows)},
        {"metric": "contains_gold_count", "value": sum(row["contains_gold"] for row in rows)},
        {"metric": "answer_in_topk_context_count", "value": sum(row["answer_in_topk_context"] for row in rows)},
        {"metric": "avg_token_recall", "value": round(sum(row["token_recall"] for row in rows) / max(len(rows), 1), 4)},
    ]
    sample_rows = [
        {
            "index": row["index"],
            "route": row["route"],
            "gold_answer": row["gold_answer"],
            "predicted_answer": row["predicted_answer"][:120],
            "failure_type": row["failure_type"],
        }
        for row in rows
    ]
    lines = [
        "# EDA023: validローカルRAG診断",
        "",
        "## 目的",
        "",
        "test提出前にvalid 30問でRAGを検証し、検索失敗と回答抽出・計算失敗を分けて確認する。",
        "",
        "## 出力",
        "",
        f"- diagnosis: `{relative(VALID_DIAG_PATH)}`",
        f"- route_summary: `{relative(ROUTE_SUMMARY_PATH)}`",
        f"- contexts: `{relative(CONTEXT_DIR)}`",
        "",
        "## 実行設定",
        "",
        f"- top_k: {args.top_k}",
        f"- max_answer_chars: {args.max_answer_chars}",
        "- LLM API: 未使用",
        "",
        "## 全体指標",
        "",
        "凡例: `metric` は診断指標、`value` は値を表します。",
        "",
        markdown_table(summary_rows),
        "",
        "## route別診断",
        "",
        "凡例: `route` は質問ルート、`question_count` はvalid質問数、`exact_match_count` は正規化完全一致数、`contains_gold_count` は予測文に正解が含まれた件数、`answer_in_topk_context_count` は上位検索根拠に正解文字列が含まれた件数、`avg_token_recall` は正解語句トークンの回収率平均です。",
        "",
        markdown_table(route_summary),
        "",
        "## failure_type別件数",
        "",
        "凡例: `failure_type` は失敗分類、`count` は該当件数を表します。",
        "",
        markdown_table([{"failure_type": key, "count": value} for key, value in sorted(failure_counts.items())]),
        "",
        "## 質問別サンプル",
        "",
        "凡例: `index` はvalid質問番号、`route` は処理ルート、`gold_answer` は正解、`predicted_answer` はローカルRAG回答、`failure_type` は診断分類です。",
        "",
        markdown_table(sample_rows, max_rows=30),
        "",
        "## 所見",
        "",
        "- EDA021で見えたタグ混入は、回答生成前のHTML/Markdown除去で抑制できる。",
        "- ただし、正解が検索上位contextに存在していても、差額計算、書式抽出、表集計は本文行抽出だけでは外しやすい。",
        "- 次はroute別に、表計算、書式抽出、差分比較、コード/Notebook値抽出の専用処理をvalidで改善する。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(args: argparse.Namespace, rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA023",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Diagnose local RAG on valid questions before further test submissions.",
        "parameters": {"top_k": args.top_k, "max_answer_chars": args.max_answer_chars},
        "inputs": {
            "embedding_records": relative(EMBEDDING_RECORDS_PATH),
            "questions_valid": relative(QUESTIONS_VALID_PATH),
            "question_routes": relative(QUESTION_ROUTES_PATH),
        },
        "outputs": {
            "diagnosis": relative(VALID_DIAG_PATH),
            "route_summary": relative(ROUTE_SUMMARY_PATH),
            "report": relative(REPORT_PATH),
        },
        "valid_question_count": len(rows),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="Diagnose local RAG on valid questions.")
    parser.add_argument("--top-k", type=int, default=8, help="質問ごとの取得レコード数")
    parser.add_argument("--max-answer-chars", type=int, default=900, help="回答の最大文字数")
    return parser.parse_args()


def main() -> None:
    """EDA023を実行する。"""
    args = parse_args()
    setup()
    rows, route_summary = run_valid_diagnosis(args)
    save_csv(rows, VALID_DIAG_PATH)
    save_csv(route_summary, ROUTE_SUMMARY_PATH)
    write_report(rows, route_summary, args)
    write_manifest(args, rows)
    print(
        " ".join(
            [
                f"valid={len(rows)}",
                f"exact={sum(row['exact_match'] for row in rows)}",
                f"contains_gold={sum(row['contains_gold'] for row in rows)}",
                f"answer_in_topk={sum(row['answer_in_topk_context'] for row in rows)}",
                f"report={relative(REPORT_PATH)}",
            ]
        )
    )


if __name__ == "__main__":
    main()
