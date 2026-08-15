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

# eda009.py は「プロジェクト直下 / EDA / EDA009 / eda009.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda009_report.md"
LOG_PATH = OUTPUT_DIR / "eda009.log"

EDA002_CHUNKS = BASE_DIR / "EDA" / "EDA002" / "texts" / "text_chunks.jsonl"
EDA004_CHUNKS = BASE_DIR / "EDA" / "EDA004" / "texts" / "text_chunks.jsonl"
QUESTION_PATH = RAW_DIR / "share" / "share" / "質問回答" / "questions_valid.csv"

DEFAULT_TOP_K = 10
PREVIEW_LENGTH = 300


DOCUMENT_HINTS = {
    "提案書": ["提案書", "00.提案"],
    "報告資料": ["報告資料", "05.会議/報告資料"],
    "報告書": ["報告書", "最終報告書", "報告資料"],
    "会議録": ["会議録", "議事録", "05.会議"],
    "契約書": ["契約書", "01.契約"],
    "スケジュール": ["スケジュール", "02.計画"],
    "計画": ["計画", "02.計画"],
    "README": ["readme", "README"],
    "カラム説明": ["カラム説明"],
}

CAPABILITY_HINTS = {
    "table_calculation": ["平均", "合計", "件数", "最大", "最小", "差額", "税額", "算出", "集計", "csv", "xlsx"],
    "format_extraction": ["色", "太字", "赤字", "下線", "マーカー", "ハイライト", "セル色"],
    "image_ocr": ["画像", "グラフ", "図", "スクリーンショット", "png", "jpg"],
    "diff_check": ["比較", "差分", "旧版", "最新版", "変更"],
    "document_qa": ["提案書", "報告資料", "報告書", "会議録", "契約書", "スケジュール"],
}


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
    """正解語句との簡易照合用に、空白・一部記号を除去する。"""
    text = normalize_for_search(text)
    text = text.replace(",", "").replace("，", "")
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[\"'`『』「」\[\]（）(){}]", "", text)


def clean_preview(text: Any, max_len: int = PREVIEW_LENGTH) -> str:
    """CSVやMarkdownで確認しやすい短い本文プレビューを作る。"""
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
# 質問解析
# =============================================================================


def detect_project(question: str, project_names: list[str]) -> str:
    """質問文に含まれる案件名を、完全一致または短い別名で推定する。"""
    q_norm = normalize_for_search(question)
    best = ""
    for project in project_names:
        p_norm = normalize_for_search(project)
        aliases = [p_norm]
        aliases.extend(part for part in re.split(r"[\s　]+", p_norm) if len(part) >= 3)
        if any(alias and alias in q_norm for alias in aliases):
            if len(project) > len(best):
                best = project
    return best


def detect_document_hints(question: str) -> list[str]:
    """質問文から、提案書や契約書などの対象文書ヒントを抽出する。"""
    q_norm = normalize_for_search(question)
    hits: list[str] = []
    for label, patterns in DOCUMENT_HINTS.items():
        if any(normalize_for_search(pattern) in q_norm for pattern in patterns):
            hits.append(label)
    return hits


def detect_capabilities(question: str) -> list[str]:
    """質問文から、表計算・書式・OCRなど必要処理タイプを推定する。"""
    q_norm = normalize_for_search(question)
    caps: list[str] = []
    for label, patterns in CAPABILITY_HINTS.items():
        if any(normalize_for_search(pattern) in q_norm for pattern in patterns):
            caps.append(label)
    return caps or ["document_qa"]


def parse_question(question: str, project_names: list[str]) -> dict[str, Any]:
    """検索前に使うため、質問文から対象資料と処理タイプを軽く解析する。"""
    doc_hints = detect_document_hints(question)
    caps = detect_capabilities(question)
    return {
        "target_project": detect_project(question, project_names),
        "document_hints": doc_hints,
        "capabilities": caps,
    }


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
    base_score: float
    bonus: float
    chunk: dict[str, Any]


class BM25Retriever:
    """外部検索サービスなしで動く、簡易BM25検索器。"""

    def __init__(self, chunks: list[dict[str, Any]], guided: bool, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.guided = guided
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

    def _base_metadata_bonus(self, question: str, chunk: dict[str, Any]) -> float:
        """拡張子・ファイル名・案件名が質問に明示されている場合、軽くスコア補正する。"""
        q_norm = normalize_for_search(question)
        extension = normalize_for_search(chunk.get("extension", ""))
        file_name = normalize_for_search(chunk.get("file_name", ""))
        project_name = normalize_for_search(chunk.get("project_name", ""))

        bonus = 1.0
        mentioned_exts = detect_extensions(question)
        if mentioned_exts:
            bonus *= 1.35 if extension in mentioned_exts else 0.82
        if file_name and file_name in q_norm:
            bonus *= 1.45
        if project_name and project_name in q_norm:
            bonus *= 1.20
        return bonus

    def _guided_bonus(self, parsed: dict[str, Any], chunk: dict[str, Any]) -> float:
        """質問解析で得た対象文書・案件を使って、候補資料の優先度を調整する。"""
        if not self.guided:
            return 1.0

        relative_path = normalize_for_search(chunk.get("relative_path", ""))
        file_name = normalize_for_search(chunk.get("file_name", ""))
        project_name = str(chunk.get("project_name", ""))
        major_folder = normalize_for_search(chunk.get("major_folder", ""))
        bonus = 1.0

        target_project = parsed.get("target_project", "")
        if target_project:
            bonus *= 1.35 if project_name == target_project else 0.70

        document_hints = parsed.get("document_hints", [])
        if document_hints:
            matched = False
            for hint in document_hints:
                for pattern in DOCUMENT_HINTS.get(hint, []):
                    p_norm = normalize_for_search(pattern)
                    if p_norm and (p_norm in relative_path or p_norm in file_name or p_norm in major_folder):
                        matched = True
            bonus *= 2.20 if matched else 0.55

        caps = set(parsed.get("capabilities", []))
        extension = normalize_for_search(chunk.get("extension", ""))
        if "table_calculation" in caps:
            bonus *= 1.35 if extension in {".csv", ".xlsx", ".xlsm"} else 0.95
        if "format_extraction" in caps:
            bonus *= 1.25 if extension in {".docx", ".pptx", ".xlsx", ".xlsm"} else 0.90
        if "image_ocr" in caps:
            bonus *= 1.40 if extension in {".png", ".jpg", ".jpeg", ".pdf", ".pptx"} else 0.85
        return bonus

    def search(self, question: str, parsed: dict[str, Any], top_k: int) -> list[SearchHit]:
        """BM25にメタデータ補正を掛けて検索する。"""
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

        adjusted: list[tuple[int, float, float, float]] = []
        for doc_idx, base_score in scores.items():
            chunk = self.chunks[doc_idx]
            bonus = self._base_metadata_bonus(question, chunk) * self._guided_bonus(parsed, chunk)
            adjusted.append((doc_idx, base_score * bonus, base_score, bonus))
        adjusted.sort(key=lambda x: x[1], reverse=True)
        return [
            SearchHit(rank=rank, score=score, base_score=base_score, bonus=bonus, chunk=self.chunks[doc_idx])
            for rank, (doc_idx, score, base_score, bonus) in enumerate(adjusted[:top_k], start=1)
        ]


# =============================================================================
# 評価
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


def evaluate(valid_df: pd.DataFrame, chunks: list[dict[str, Any]], top_k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """通常BM25と質問解析つきBM25をvalidで比較する。"""
    project_names = sorted({str(c.get("project_name", "")) for c in chunks if c.get("project_name")})
    baseline = BM25Retriever(chunks, guided=False)
    guided = BM25Retriever(chunks, guided=True)
    rows: list[dict[str, Any]] = []
    hit_rows: list[dict[str, Any]] = []

    for _, row in valid_df.iterrows():
        q_index = int(row["index"])
        question = str(row["question"])
        answer = str(row["answer"])
        parsed = parse_question(question, project_names)
        base_hits = baseline.search(question, parsed, top_k)
        guided_hits = guided.search(question, parsed, top_k)
        base_hit5, base_cov5, base_terms5 = answer_coverage(answer, base_hits, min(5, top_k))
        base_hit10, base_cov10, _ = answer_coverage(answer, base_hits, top_k)
        guided_hit5, guided_cov5, guided_terms5 = answer_coverage(answer, guided_hits, min(5, top_k))
        guided_hit10, guided_cov10, _ = answer_coverage(answer, guided_hits, top_k)
        base_top1 = base_hits[0] if base_hits else None
        guided_top1 = guided_hits[0] if guided_hits else None

        rows.append(
            {
                "index": q_index,
                "question": question,
                "answer": answer,
                "target_project": parsed["target_project"],
                "document_hints": " | ".join(parsed["document_hints"]),
                "capabilities": " | ".join(parsed["capabilities"]),
                "baseline_hit_top5": base_hit5,
                "guided_hit_top5": guided_hit5,
                "hit_top5_delta": int(guided_hit5) - int(base_hit5),
                "baseline_hit_top10": base_hit10,
                "guided_hit_top10": guided_hit10,
                "hit_top10_delta": int(guided_hit10) - int(base_hit10),
                "baseline_coverage_top5": base_cov5,
                "guided_coverage_top5": guided_cov5,
                "baseline_matched_top5": base_terms5,
                "guided_matched_top5": guided_terms5,
                "baseline_top1_path": base_top1.chunk.get("relative_path", "") if base_top1 else "",
                "guided_top1_path": guided_top1.chunk.get("relative_path", "") if guided_top1 else "",
                "baseline_top1_score": round(base_top1.score, 4) if base_top1 else 0.0,
                "guided_top1_score": round(guided_top1.score, 4) if guided_top1 else 0.0,
                "guided_top1_bonus": round(guided_top1.bonus, 4) if guided_top1 else 0.0,
                "baseline_top1_preview": clean_preview(chunk_text(base_top1.chunk)) if base_top1 else "",
                "guided_top1_preview": clean_preview(chunk_text(guided_top1.chunk)) if guided_top1 else "",
            }
        )

        for mode, hits in [("baseline", base_hits), ("guided", guided_hits)]:
            for hit in hits:
                hit_rows.append(
                    {
                        "index": q_index,
                        "mode": mode,
                        "rank": hit.rank,
                        "score": round(hit.score, 4),
                        "base_score": round(hit.base_score, 4),
                        "bonus": round(hit.bonus, 4),
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


def make_summary(comparison: pd.DataFrame, hit_log: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """比較結果を集計する。"""
    overall = pd.DataFrame(
        [
            {
                "metric": "top5_hit_rate",
                "baseline": round(float(comparison["baseline_hit_top5"].mean()), 4),
                "guided": round(float(comparison["guided_hit_top5"].mean()), 4),
                "delta": round(float(comparison["guided_hit_top5"].mean() - comparison["baseline_hit_top5"].mean()), 4),
            },
            {
                "metric": "top10_hit_rate",
                "baseline": round(float(comparison["baseline_hit_top10"].mean()), 4),
                "guided": round(float(comparison["guided_hit_top10"].mean()), 4),
                "delta": round(float(comparison["guided_hit_top10"].mean() - comparison["baseline_hit_top10"].mean()), 4),
            },
        ]
    )
    doc_hint_summary = (
        comparison.assign(has_document_hint=comparison["document_hints"].astype(str).str.len() > 0)
        .groupby("has_document_hint", as_index=False)
        .agg(
            question_count=("index", "count"),
            baseline_top5=("baseline_hit_top5", "mean"),
            guided_top5=("guided_hit_top5", "mean"),
            improved=("hit_top5_delta", lambda s: int((s > 0).sum())),
            worsened=("hit_top5_delta", lambda s: int((s < 0).sum())),
        )
    )
    for col in ["baseline_top5", "guided_top5"]:
        doc_hint_summary[col] = doc_hint_summary[col].round(4)
    top1_modes = (
        hit_log[hit_log["rank"] == 1]
        .groupby(["mode", "extension"], as_index=False)
        .agg(top1_count=("index", "count"))
        .sort_values(["mode", "top1_count"], ascending=[True, False])
    )
    changed = comparison[comparison["baseline_top1_path"] != comparison["guided_top1_path"]].copy()
    changed = changed[
        [
            "index",
            "question",
            "answer",
            "document_hints",
            "baseline_hit_top5",
            "guided_hit_top5",
            "baseline_top1_path",
            "guided_top1_path",
        ]
    ]
    return {
        "overall": overall,
        "doc_hint_summary": doc_hint_summary,
        "top1_modes": top1_modes,
        "changed_top1_cases": changed,
    }


def write_report(comparison: pd.DataFrame, summaries: dict[str, pd.DataFrame], args: argparse.Namespace) -> None:
    """EDA009のMarkdownレポートを保存する。"""
    valid_002 = comparison[comparison["index"] == 2]
    lines: list[str] = []
    lines.append("# EDA009: 質問解析つき検索の検証")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append(
        "EDA008では、LLM API呼び出し自体は成功した一方で、質問が指定する `提案書` ではなく `報告資料` の根拠が上位に入り、回答がずれました。"
        "EDA009ではLLMを呼ばず、検索前に質問解析を行い、対象文書名やフォルダ名を使って根拠候補を優先できるかをvalidで検証します。"
    )
    lines.append("")
    lines.append("## 実行設定")
    lines.append("")
    lines.append(f"- top_k: {args.top_k}")
    lines.append("- 入力チャンク: `EDA/EDA002/texts/text_chunks.jsonl`, `EDA/EDA004/texts/text_chunks.jsonl`")
    lines.append("- 評価質問: `data/raw/share/share/質問回答/questions_valid.csv`")
    lines.append("")
    lines.append("## 全体比較")
    lines.append("")
    lines.append(df_to_markdown(summaries["overall"]))
    lines.append("")
    lines.append("凡例: `metric` は評価指標、`baseline` は通常BM25、`guided` は質問解析つきBM25、`delta` は guided から baseline を引いた値を表します。")
    lines.append("")
    lines.append("## 文書ヒント有無別")
    lines.append("")
    lines.append(df_to_markdown(summaries["doc_hint_summary"]))
    lines.append("")
    lines.append("凡例: `has_document_hint` は質問に提案書や契約書などの文書ヒントが含まれるか、`question_count` は質問数、`baseline_top5` と `guided_top5` はTop5正解語句ヒット率、`improved` と `worsened` はTop5判定が改善または悪化した件数を表します。")
    lines.append("")
    lines.append("## valid_002の確認")
    lines.append("")
    if valid_002.empty:
        lines.append("valid_002 は見つかりませんでした。")
    else:
        cols = [
            "index",
            "question",
            "answer",
            "document_hints",
            "baseline_hit_top5",
            "guided_hit_top5",
            "baseline_top1_path",
            "guided_top1_path",
        ]
        lines.append(df_to_markdown(valid_002[cols]))
        lines.append("")
        lines.append("凡例: `baseline_top1_path` は通常BM25の1位根拠、`guided_top1_path` は質問解析つきBM25の1位根拠を表します。")
    lines.append("")
    lines.append("## Top1が変化したケース")
    lines.append("")
    lines.append(df_to_markdown(summaries["changed_top1_cases"], max_rows=12))
    lines.append("")
    lines.append("凡例: `baseline_top1_path` と `guided_top1_path` は、質問解析によって1位根拠がどう変わったかを表します。")
    lines.append("")
    lines.append("## 考察")
    lines.append("")
    lines.append("- 質問内の文書名を使うことで、LLMへ渡す前の根拠選択を制御できるかを確認する実験です。")
    lines.append("- TopK内に正解語句があるかは簡易評価であり、表計算、書式、画像、差分が必要な質問では実際の回答可能性とずれる場合があります。")
    lines.append("- guidedで悪化するケースがある場合は、文書ヒントの加点を弱めるか、対象プロジェクト一致をより強くする必要があります。")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_eda_summary(comparison: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> None:
    """EDA総括にEDA009の概要を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    if "## EDA009の要点" in text:
        return
    marker = "## 最終構成の方針"
    overall = summaries["overall"].set_index("metric")
    top5_base = overall.loc["top5_hit_rate", "baseline"]
    top5_guided = overall.loc["top5_hit_rate", "guided"]
    top10_base = overall.loc["top10_hit_rate", "baseline"]
    top10_guided = overall.loc["top10_hit_rate", "guided"]
    valid_002 = comparison[comparison["index"] == 2]
    valid_002_note = ""
    if not valid_002.empty:
        row = valid_002.iloc[0]
        valid_002_note = (
            f"valid_002では、通常BM25の1位は `{row['baseline_top1_path']}`、"
            f"質問解析つきBM25の1位は `{row['guided_top1_path']}` でした。"
        )
    addition = f"""
## EDA009の要点

EDA009では、検索前の質問解析と文書名・フォルダ名による候補資料優先を検証しました。対象はvalid 30問で、通常BM25と質問解析つきBM25を比較しています。

Top5正解語句ヒット率は通常BM25が {top5_base}、質問解析つきBM25が {top5_guided} でした。Top10正解語句ヒット率は通常BM25が {top10_base}、質問解析つきBM25が {top10_guided} でした。{valid_002_note}

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA009: query planning and guided retrieval validation.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()
    chunks = load_unified_chunks()
    valid_df = pd.read_csv(QUESTION_PATH)
    comparison, hit_log = evaluate(valid_df, chunks, args.top_k)
    summaries = make_summary(comparison, hit_log)

    save_csv(comparison, TABLE_DIR / "valid_guided_retrieval_comparison.csv")
    save_csv(hit_log, TABLE_DIR / "valid_guided_top_sources.csv")
    for name, df in summaries.items():
        save_csv(df, TABLE_DIR / f"{name}.csv")
    write_report(comparison, summaries, args)
    update_eda_summary(comparison, summaries)

    print(f"EDA009 finished: {REPORT_PATH}")
    print(f"comparison: {TABLE_DIR / 'valid_guided_retrieval_comparison.csv'}")
    print(f"hit_log: {TABLE_DIR / 'valid_guided_top_sources.csv'}")


if __name__ == "__main__":
    main()
