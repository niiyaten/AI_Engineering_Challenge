from __future__ import annotations

import argparse
import json
import logging
import math
import re
import unicodedata
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda006.py は「プロジェクト直下 / EDA / EDA006 / eda006.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda006_report.md"
LOG_PATH = OUTPUT_DIR / "eda006.log"

EDA002_CHUNKS = BASE_DIR / "EDA" / "EDA002" / "texts" / "text_chunks.jsonl"
EDA004_CHUNKS = BASE_DIR / "EDA" / "EDA004" / "texts" / "text_chunks.jsonl"
QUESTION_PATH = RAW_DIR / "share" / "share" / "質問回答" / "questions_valid.csv"

DEFAULT_TOP_K = 10
PREVIEW_LENGTH = 360


# =============================================================================
# 基本ユーティリティ
# =============================================================================


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    logging.captureWarnings(True)
    warnings.simplefilter("always")
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


_HASH_U_PATTERN = re.compile(r"#U([0-9a-fA-F]{4})")


def decode_hash_u_text(text: str) -> str:
    """#U5171 のように展開された日本語パスを通常の日本語へ戻す。"""

    def repl(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return unicodedata.normalize("NFC", _HASH_U_PATTERN.sub(repl, str(text)))


def normalize_display_text(text: Any) -> str:
    """表示用にUnicode表記揺れを軽く整える。"""
    return unicodedata.normalize("NFC", decode_hash_u_text(str(text)))


def normalize_for_search(text: Any) -> str:
    """検索・照合用に全角半角、大文字小文字、空白揺れを抑える。"""
    text = normalize_display_text(text)
    text = unicodedata.normalize("NFKC", text).lower()
    return text.replace("\u3000", " ")


def compact_for_match(text: Any) -> str:
    """正解語句の簡易照合用に、空白・一部記号を除去する。"""
    text = normalize_for_search(text)
    text = text.replace(",", "").replace("，", "")
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[\"'`『』「」\[\]（）(){}]", "", text)


def clean_preview(text: Any, max_len: int = PREVIEW_LENGTH) -> str:
    """CSV/Markdownレポートで読みやすい短い本文プレビューを作る。"""
    text = re.sub(r"\s+", " ", normalize_display_text(text)).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """JSONLファイルを読み込む。"""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL読み込み失敗: {path} line={line_no}") from exc
    return records


def chunk_text(chunk: dict[str, Any]) -> str:
    """EDA002とEDA004で異なる本文キーを吸収する。"""
    return str(chunk.get("text") or chunk.get("chunk_text") or "")


def load_unified_chunks() -> list[dict[str, Any]]:
    """EDA002とEDA004の検索用チャンクを統合する。"""
    chunks: list[dict[str, Any]] = []
    for source_eda, path in [("EDA002", EDA002_CHUNKS), ("EDA004", EDA004_CHUNKS)]:
        for record in read_jsonl(path):
            text = chunk_text(record)
            if not text.strip():
                continue
            normalized = dict(record)
            normalized["source_eda"] = source_eda
            normalized["text"] = text
            normalized.setdefault("chunk_id", f"{source_eda}_{len(chunks):06d}")
            normalized.setdefault("extension", "")
            normalized.setdefault("relative_path", "")
            normalized.setdefault("file_name", "")
            normalized.setdefault("project_name", "")
            normalized.setdefault("major_folder", "")
            chunks.append(normalized)
    return chunks


# =============================================================================
# BM25検索
# =============================================================================


TOKEN_WORD_PATTERN = re.compile(r"[a-z0-9_]+|[一-龥々〆ヵヶぁ-んァ-ヴー]+")
EXT_PATTERN = re.compile(r"\.(md|csv|json|py|ipynb|xlsx|xlsm|docx|pptx|pdf|png|jpg|jpeg)\b", re.IGNORECASE)


def detect_extensions(text: Any) -> list[str]:
    """質問文に明示された拡張子を抽出する。"""
    found = ["." + m.group(1).lower() for m in EXT_PATTERN.finditer(str(text))]
    return list(dict.fromkeys(found))


def char_ngrams(text: str, n_values: tuple[int, ...] = (2, 3)) -> list[str]:
    """日本語検索のため、空白を除いた文字n-gramを作る。"""
    compact = re.sub(r"\s+", "", text)
    compact = re.sub(r"[^a-z0-9_一-龥々〆ヵヶぁ-んァ-ヴー]+", "", compact)
    grams: list[str] = []
    for n in n_values:
        if len(compact) < n:
            continue
        grams.extend(compact[i : i + n] for i in range(len(compact) - n + 1))
    return grams


def tokenize(text: Any) -> list[str]:
    """日本語形態素解析器なしで動かすための簡易トークナイザ。"""
    norm = normalize_for_search(text)
    words = TOKEN_WORD_PATTERN.findall(norm)
    return words + char_ngrams(norm)


@dataclass
class SearchHit:
    rank: int
    score: float
    chunk: dict[str, Any]


class BM25Retriever:
    """外部検索サービスなしで動く、簡易BM25検索器。"""

    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_lens: list[int] = []
        self.inverted_index: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.df: Counter[str] = Counter()
        self.avg_doc_len = 0.0
        self._build()

    def _indexed_text(self, chunk: dict[str, Any]) -> str:
        metadata_parts = [
            chunk.get("relative_path", ""),
            chunk.get("relative_path", ""),
            chunk.get("file_name", ""),
            chunk.get("file_name", ""),
            chunk.get("extension", ""),
            chunk.get("project_name", ""),
            chunk.get("project_name", ""),
            chunk.get("major_folder", ""),
        ]
        return "\n".join(str(part) for part in metadata_parts if part) + "\n" + chunk_text(chunk)

    def _build(self) -> None:
        for doc_idx, chunk in enumerate(self.chunks):
            counts = Counter(tokenize(self._indexed_text(chunk)))
            doc_len = sum(counts.values())
            self.doc_lens.append(max(doc_len, 1))
            for token, tf in counts.items():
                self.df[token] += 1
                self.inverted_index[token].append((doc_idx, tf))
        self.avg_doc_len = sum(self.doc_lens) / max(len(self.doc_lens), 1)

    def _metadata_bonus(self, question: str, chunk: dict[str, Any]) -> float:
        """拡張子・ファイル名・案件名が質問に明示されている場合、軽くスコア補正する。"""
        q_norm = normalize_for_search(question)
        extension = normalize_for_search(chunk.get("extension", ""))
        file_name = normalize_for_search(chunk.get("file_name", ""))
        project_name = normalize_for_search(chunk.get("project_name", ""))
        relative_path = normalize_for_search(chunk.get("relative_path", ""))

        bonus = 1.0
        mentioned_exts = detect_extensions(question)
        if mentioned_exts:
            bonus *= 1.35 if extension in mentioned_exts else 0.82
        if file_name and file_name in q_norm:
            bonus *= 1.45
        if project_name and project_name in q_norm:
            bonus *= 1.20
        if relative_path and any(part and part in q_norm for part in relative_path.split("/")[-3:]):
            bonus *= 1.10
        return bonus

    def search(self, question: str, top_k: int) -> list[SearchHit]:
        query_counts = Counter(tokenize(question))
        scores: defaultdict[int, float] = defaultdict(float)
        n_docs = len(self.chunks)

        for token, qtf in query_counts.items():
            postings = self.inverted_index.get(token)
            if not postings:
                continue
            df = self.df[token]
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            q_weight = 1.0 + math.log1p(qtf) * 0.10
            for doc_idx, tf in postings:
                doc_len = self.doc_lens[doc_idx]
                denom = tf + self.k1 * (1.0 - self.b + self.b * doc_len / max(self.avg_doc_len, 1e-9))
                scores[doc_idx] += idf * ((tf * (self.k1 + 1.0)) / denom) * q_weight

        adjusted = [
            (doc_idx, score * self._metadata_bonus(question, self.chunks[doc_idx]))
            for doc_idx, score in scores.items()
        ]
        adjusted.sort(key=lambda x: x[1], reverse=True)
        return [
            SearchHit(rank=rank, score=score, chunk=self.chunks[doc_idx])
            for rank, (doc_idx, score) in enumerate(adjusted[:top_k], start=1)
        ]


# =============================================================================
# valid診断
# =============================================================================


def answer_terms(answer: Any) -> list[str]:
    """valid正解を、根拠チャンク照合に使う語句へ分割する。"""
    text = normalize_display_text(answer)
    if not text or text.lower() == "nan":
        return []
    raw_terms = [text]
    raw_terms.extend(re.split(r"[、,，/・\n]+", text))
    terms: list[str] = []
    for term in raw_terms:
        term = term.strip()
        if not term:
            continue
        compact = compact_for_match(term)
        if len(compact) <= 1 and not re.search(r"\d", compact):
            continue
        terms.append(term)
    return list(dict.fromkeys(terms))


def answer_coverage(answer: Any, hits: list[SearchHit], top_k: int) -> tuple[bool, float, str]:
    """TopK根拠に正解語句が含まれるかを簡易評価する。"""
    joined = "\n".join(
        str(hit.chunk.get("relative_path", "")) + "\n" + chunk_text(hit.chunk)
        for hit in hits[:top_k]
    )
    joined_compact = compact_for_match(joined)
    answer_compact = compact_for_match(answer)
    exact_hit = bool(answer_compact and answer_compact in joined_compact)
    terms = answer_terms(answer)
    compact_terms = [compact_for_match(term) for term in terms]
    matched = [
        term for term, compact in zip(terms, compact_terms)
        if compact and compact in joined_compact
    ]
    coverage = len(matched) / len(compact_terms) if compact_terms else 0.0
    return exact_hit or coverage >= 0.80, round(coverage, 4), "、".join(matched)


def required_capability(question: str) -> str:
    """質問に答えるために必要そうな汎用能力を推定する。"""
    q = normalize_for_search(question)
    caps: list[str] = []
    patterns = {
        "table_tool": ["合計", "平均", "最も高い", "最も低い", "差額", "税額", "算出", "xlsx", "csv", "pivot", "フィルター"],
        "format_extraction": ["太字", "赤字", "下線", "マーカー", "ハイライト", "黄色", "色"],
        "image_ocr": ["画像", "グラフ", "figure", ".png"],
        "diff_tool": ["比較", "旧版", "最新版", "変更", "old"],
        "code_reading": [".py", "コード", "modeling", "パラメータ", "sparse_output"],
        "document_qa": ["提案書", "契約書", "報告書", "会議録", "スケジュール"],
    }
    for cap, keys in patterns.items():
        if any(key in q for key in keys):
            caps.append(cap)
    return ", ".join(caps) if caps else "document_qa"


def readiness_label(question: str, answer_hit_top5: bool, answer_hit_top10: bool, top1_score: float) -> tuple[str, str, str]:
    """LLMへ渡す前の文脈品質を粗く判定する。"""
    caps = required_capability(question)
    cap_set = set(caps.split(", "))

    if "image_ocr" in cap_set:
        return "needs_image_ocr", "画像やグラフの読み取りが必要", "OCRまたは画像理解の抽出器を追加する"
    if "diff_tool" in cap_set:
        return "needs_diff_tool", "old/new比較が必要", "ファイル差分をスライド・段落単位で比較する"
    if "format_extraction" in cap_set:
        return "needs_format_extraction", "色・マーカー・下線などの書式情報が必要", "Word/PPTの書式メタ情報をRAG向けに正規化する"
    if "table_tool" in cap_set and not answer_hit_top10:
        return "needs_table_tool", "表の直接集計やフィルター条件確認が必要", "CSV/XLSXをpandas/openpyxlで直接処理する"
    if answer_hit_top5:
        return "ready_for_llm", "Top5に正解語句があり、LLM抽出で改善できる可能性が高い", "LLM向けMarkdownコンテキストを作る"
    if answer_hit_top10:
        return "needs_context_rerank", "Top10には正解語句があるが上位文脈が弱い", "検索結果の再ランキングとコンテキスト整形を行う"
    if top1_score <= 0:
        return "needs_better_retrieval", "検索結果がほぼ得られていない", "検索クエリ拡張やメタデータ検索を改善する"
    return "needs_better_retrieval", "Top10に正解語句がなく根拠候補が不足", "抽出対象と検索重みを見直す"


def diagnose_valid(valid_df: pd.DataFrame, retriever: BM25Retriever, top_k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """valid 30問について、検索根拠がLLMに渡せる状態かを診断する。"""
    rows: list[dict[str, Any]] = []
    hit_rows: list[dict[str, Any]] = []
    for _, row in valid_df.iterrows():
        q_index = int(row["index"])
        question = str(row["question"])
        answer = str(row["answer"])
        hits = retriever.search(question, top_k=top_k)
        top1 = hits[0] if hits else None
        answer_hit_top5, coverage5, matched5 = answer_coverage(answer, hits, min(5, top_k))
        answer_hit_top10, coverage10, matched10 = answer_coverage(answer, hits, top_k)
        label, missing_piece, recommended_next_step = readiness_label(
            question,
            answer_hit_top5=answer_hit_top5,
            answer_hit_top10=answer_hit_top10,
            top1_score=top1.score if top1 else 0.0,
        )

        rows.append(
            {
                "index": q_index,
                "question": question,
                "answer": answer,
                "required_capability": required_capability(question),
                "context_quality_for_llm": label,
                "missing_piece": missing_piece,
                "recommended_next_step": recommended_next_step,
                "answer_hit_top5": answer_hit_top5,
                "answer_term_coverage_top5": coverage5,
                "matched_answer_terms_top5": matched5,
                "answer_hit_top10": answer_hit_top10,
                "answer_term_coverage_top10": coverage10,
                "matched_answer_terms_top10": matched10,
                "top1_score": round(top1.score, 4) if top1 else 0.0,
                "top1_source_eda": top1.chunk.get("source_eda", "") if top1 else "",
                "top1_extension": top1.chunk.get("extension", "") if top1 else "",
                "top1_relative_path": top1.chunk.get("relative_path", "") if top1 else "",
                "top1_preview": clean_preview(chunk_text(top1.chunk)) if top1 else "",
                "top5_paths": " || ".join(str(hit.chunk.get("relative_path", "")) for hit in hits[:5]),
            }
        )

        for hit in hits:
            hit_rows.append(
                {
                    "index": q_index,
                    "rank": hit.rank,
                    "score": round(hit.score, 4),
                    "question": question,
                    "answer": answer,
                    "source_eda": hit.chunk.get("source_eda", ""),
                    "extension": hit.chunk.get("extension", ""),
                    "project_name": hit.chunk.get("project_name", ""),
                    "major_folder": hit.chunk.get("major_folder", ""),
                    "relative_path": hit.chunk.get("relative_path", ""),
                    "chunk_id": hit.chunk.get("chunk_id", ""),
                    "preview": clean_preview(chunk_text(hit.chunk)),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(hit_rows)


def make_summary_tables(diagnosis: pd.DataFrame, chunks: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    """診断結果を集計する。"""
    readiness_counts = (
        diagnosis["context_quality_for_llm"].value_counts()
        .rename_axis("context_quality_for_llm")
        .reset_index(name="question_count")
    )
    capability_counts = (
        diagnosis["required_capability"].value_counts()
        .rename_axis("required_capability")
        .reset_index(name="question_count")
    )
    next_action_priority = (
        diagnosis.groupby(["recommended_next_step", "context_quality_for_llm"], as_index=False)
        .agg(
            question_count=("index", "count"),
            answer_hit_top5_rate=("answer_hit_top5", "mean"),
            mean_top1_score=("top1_score", "mean"),
        )
        .sort_values(["question_count", "answer_hit_top5_rate"], ascending=[False, True])
    )
    next_action_priority["answer_hit_top5_rate"] = next_action_priority["answer_hit_top5_rate"].round(4)
    next_action_priority["mean_top1_score"] = next_action_priority["mean_top1_score"].round(4)
    chunk_source_counts = (
        pd.Series([c.get("source_eda", "") for c in chunks])
        .value_counts()
        .rename_axis("source_eda")
        .reset_index(name="chunk_count")
    )
    chunk_extension_counts = (
        pd.Series([c.get("extension", "") for c in chunks])
        .value_counts()
        .rename_axis("extension")
        .reset_index(name="chunk_count")
    )
    return {
        "readiness_counts": readiness_counts,
        "capability_counts": capability_counts,
        "next_action_priority": next_action_priority,
        "chunk_source_counts": chunk_source_counts,
        "chunk_extension_counts": chunk_extension_counts,
    }


def write_report(diagnosis: pd.DataFrame, summaries: dict[str, pd.DataFrame], top_k: int) -> None:
    """EDA006のMarkdownレポートを作成する。"""
    ready_count = int((diagnosis["context_quality_for_llm"] == "ready_for_llm").sum())
    hit5_rate = float(diagnosis["answer_hit_top5"].mean()) if len(diagnosis) else 0.0
    hit10_rate = float(diagnosis["answer_hit_top10"].mean()) if len(diagnosis) else 0.0

    lines: list[str] = []
    lines.append("# EDA006: validを用いたLLM導入前RAG診断")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append(
        "EDA005では、EDA002とEDA004の検索用チャンクを統合し、BM25検索とテンプレ回答で提出候補を作成しました。"
        "提出形式は確認できましたが、スコアは低く、回答品質を改善するには検索・抽出・表計算・書式・画像・差分のどこが不足しているかを切り分ける必要があります。"
    )
    lines.append("")
    lines.append(
        "EDA006では、valid 30問を使って、将来LLMに渡す前のRAGパイプラインを診断します。"
        "ここでvalid正解を見る目的は、個別回答をハードコードすることではなく、検索TopKに必要な根拠が入っているか、"
        "LLMに渡せる文脈になっているか、どの汎用処理を追加すべきかを評価することです。"
    )
    lines.append("")
    lines.append("## 手法")
    lines.append("")
    lines.append("- EDA002とEDA004の検索用チャンクを統合する")
    lines.append(f"- valid質問ごとにBM25でTop {top_k}を取得する")
    lines.append("- valid正解語句がTop5/Top10に含まれるかを簡易照合する")
    lines.append("- 質問文から必要能力を分類する")
    lines.append("- `ready_for_llm` または不足カテゴリに分類し、次アクションを決める")
    lines.append("")
    lines.append("## 全体サマリ")
    lines.append("")
    lines.append(f"- valid質問数: {len(diagnosis)}")
    lines.append(f"- ready_for_llm件数: {ready_count}")
    lines.append(f"- answer_hit_top5率: {hit5_rate:.4f}")
    lines.append(f"- answer_hit_top10率: {hit10_rate:.4f}")
    lines.append("")
    lines.append("## LLM文脈品質の分類")
    lines.append("")
    lines.append(df_to_markdown(summaries["readiness_counts"]))
    lines.append("")
    lines.append("凡例: `context_quality_for_llm` はLLMへ渡す前の文脈品質、`question_count` はvalid内の件数を表します。")
    lines.append("")
    lines.append("## 必要能力の分類")
    lines.append("")
    lines.append(df_to_markdown(summaries["capability_counts"]))
    lines.append("")
    lines.append("凡例: `required_capability` は質問に答えるために必要そうな汎用能力、`question_count` はvalid内の件数を表します。")
    lines.append("")
    lines.append("## 次アクション優先度")
    lines.append("")
    lines.append(df_to_markdown(summaries["next_action_priority"]))
    lines.append("")
    lines.append("凡例: `recommended_next_step` は次に作るべき汎用処理、`answer_hit_top5_rate` は該当グループでTop5に正解語句が含まれた割合、`mean_top1_score` は検索Top1スコア平均を表します。")
    lines.append("")
    lines.append("## valid診断サンプル")
    lines.append("")
    sample_cols = [
        "index", "question", "answer", "required_capability", "context_quality_for_llm",
        "answer_hit_top5", "top1_relative_path", "recommended_next_step",
    ]
    lines.append(df_to_markdown(diagnosis[sample_cols], max_rows=30))
    lines.append("")
    lines.append("## 考察")
    lines.append("")
    lines.append(
        "`ready_for_llm` は、検索Top5に正解語句が含まれており、次にLLM向けMarkdownコンテキストを整形すれば改善しやすい候補です。"
        "一方で、画像、差分、書式、表計算が必要な問題は、LLMだけを追加しても根拠不足や誤答になりやすいため、専用の抽出・計算ツールが必要です。"
    )
    lines.append("")
    lines.append(
        "EDA007では、今回の診断結果をもとに、LLMへ渡す根拠を読みやすくするMarkdownコンテキスト生成を作るのが自然です。"
        "ただし、表計算や画像読み取りが多い場合は、それらの専用ツールを先に作る選択肢もあります。"
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_eda_summary(diagnosis: pd.DataFrame) -> None:
    """EDA総括にEDA006の概要を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    if "## EDA006の要点" in text:
        return
    marker = "## 現時点の総合判断"
    ready_count = int((diagnosis["context_quality_for_llm"] == "ready_for_llm").sum())
    hit5_rate = float(diagnosis["answer_hit_top5"].mean()) if len(diagnosis) else 0.0
    addition = f"""
## EDA006の要点

EDA006では、valid 30問を使って、将来LLMに渡す前のRAGパイプラインを診断しました。valid正解は個別回答のハードコードではなく、検索TopKに必要な根拠が含まれているか、LLMに渡せる文脈になっているかを測るために使っています。

診断結果では、`ready_for_llm` は {ready_count} 件、Top5に正解語句が含まれた割合は {hit5_rate:.4f} でした。今後は、LLM向けMarkdownコンテキスト生成、CSV/XLSXの直接集計、Word/PPTの書式抽出、画像・差分対応を、validでの失敗タイプに応じて追加していく方針です。

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA006: valid readiness diagnosis before LLM answer generation.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()

    valid_df = pd.read_csv(QUESTION_PATH)
    chunks = load_unified_chunks()
    retriever = BM25Retriever(chunks)
    diagnosis, retrieval = diagnose_valid(valid_df, retriever, top_k=args.top_k)
    summaries = make_summary_tables(diagnosis, chunks)

    save_csv(diagnosis, TABLE_DIR / "valid_llm_readiness.csv")
    save_csv(retrieval, TABLE_DIR / "valid_top_sources.csv")
    for name, df in summaries.items():
        save_csv(df, TABLE_DIR / f"{name}.csv")

    write_report(diagnosis, summaries, top_k=args.top_k)
    update_eda_summary(diagnosis)

    print(f"EDA006 finished: {REPORT_PATH}")
    print(f"tables: {TABLE_DIR}")


if __name__ == "__main__":
    main()
