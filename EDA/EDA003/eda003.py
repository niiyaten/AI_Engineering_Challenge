from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import unicodedata
import warnings
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

# GUIがない環境でも画像保存できるようにする。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda003.py は「プロジェクト直下 / EDA / EDA003 / eda003.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda003_report.md"
LOG_PATH = OUTPUT_DIR / "eda003.log"

# EDA002の成果物を優先して利用する。
CHUNK_PATH_CANDIDATES = [
    BASE_DIR / "EDA" / "EDA002" / "texts" / "text_chunks.jsonl",
    PROCESSED_DIR / "text_baseline" / "text_chunks.jsonl",
]

QUESTION_DIR_CANDIDATES = [
    RAW_DIR / "share" / "質問回答",
    RAW_DIR / "share" / "share" / "質問回答",
    DATA_DIR / "interim" / "share" / "share" / "質問回答",
    DATA_DIR / "interim" / "share" / "質問回答",
    BASE_DIR / "share" / "質問回答",
    BASE_DIR / "share" / "share" / "質問回答",
]

SHARE_ZIP_CANDIDATES = [
    RAW_DIR / "share.zip",
    DATA_DIR / "share.zip",
    BASE_DIR / "share.zip",
    BASE_DIR.parent / "share.zip",
]

TARGET_EXTENSIONS = {".md", ".csv", ".json", ".py", ".ipynb"}
SUPPORTED_QUESTION_EXTENSIONS = TARGET_EXTENSIONS
KNOWN_EXTENSIONS = {
    ".md", ".csv", ".json", ".py", ".ipynb",
    ".xlsx", ".xlsm", ".docx", ".pptx", ".pdf", ".png", ".jpg", ".jpeg",
}

DEFAULT_TOP_K = 10
PREVIEW_LENGTH = 280

# =============================================================================
# 基本ユーティリティ
# =============================================================================


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    logging.captureWarnings(True)
    logging.getLogger("matplotlib.category").setLevel(logging.ERROR)
    warnings.simplefilter("always")
    warnings.filterwarnings("ignore", message="Glyph .* missing from font.*")
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


_HASH_U_PATTERN = re.compile(r"#U([0-9a-fA-F]{4})")


def decode_hash_u_text(text: str) -> str:
    """#U5171 のように展開された日本語パスを通常の日本語へ戻す。"""

    def repl(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return unicodedata.normalize("NFC", _HASH_U_PATTERN.sub(repl, str(text)))


def normalize_display_text(text: Any) -> str:
    """表示・検索前処理用に、Unicode表記揺れを軽く整える。"""
    return unicodedata.normalize("NFC", decode_hash_u_text(str(text)))


def normalize_for_search(text: Any) -> str:
    """BM25用に、全角半角・大文字小文字・空白揺れを抑える。"""
    text = normalize_display_text(text)
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("\u3000", " ")
    return text


def compact_for_match(text: Any) -> str:
    """回答文字列と本文の簡易照合用に、空白・一部記号を除去する。"""
    text = normalize_for_search(text)
    # 金額や数値は 4,394,250 と 4394250 の揺れが出やすいためカンマを落とす。
    text = text.replace(",", "").replace("，", "")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[\"'`『』「」\[\]（）(){}]", "", text)
    return text


def clean_preview(text: Any, max_len: int = PREVIEW_LENGTH) -> str:
    """CSV/Markdownレポートで読みやすい短い本文プレビューを作る。"""
    text = normalize_display_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """Excelでも開きやすいようにUTF-8 BOM付きでCSV保存する。"""
    df.to_csv(path, index=False, encoding="utf-8-sig")


def display_path(path: Path) -> str:
    """レポートでは環境依存の絶対パスではなく、可能な限りプロジェクト相対パスで表示する。"""
    try:
        return str(path.resolve().relative_to(BASE_DIR.resolve()))
    except ValueError:
        if path.name in {"share.zip", "sample_submit.zip", "evaluation.zip"}:
            return path.name
        return str(path)


def display_source(source: str) -> str:
    """質問データの読み込み元表示を、できるだけ環境非依存にする。"""
    prefix = "zip: "
    if source.startswith(prefix):
        raw_path = Path(source[len(prefix):])
        return prefix + display_path(raw_path)
    dir_prefix = "directory: "
    if source.startswith(dir_prefix):
        raw_path = Path(source[len(dir_prefix):])
        return dir_prefix + display_path(raw_path)
    return source


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
                raise ValueError(f"JSONLの読み込みに失敗しました: {path} line={line_no}") from exc
    return records


def find_existing_path(candidates: list[Path], label: str) -> Path:
    """候補パスのうち、最初に存在するものを返す。"""
    for path in candidates:
        if path.exists():
            return path
    msg = f"{label} が見つかりません。確認した候補:\n" + "\n".join(f"- {p}" for p in candidates)
    raise FileNotFoundError(msg)


# =============================================================================
# 質問データ読み込み
# =============================================================================


def find_questions_from_directory() -> tuple[Path | None, Path | None]:
    """展開済みフォルダから valid/test 質問CSVを探す。"""
    for qdir in QUESTION_DIR_CANDIDATES:
        valid_path = qdir / "questions_valid.csv"
        test_path = qdir / "questions_test.csv"
        if valid_path.exists() and test_path.exists():
            return valid_path, test_path
    return None, None


def read_questions_from_zip(zip_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """share.zip内の質問CSVを、zipを展開せずに読み込む。"""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        valid_name = next((n for n in names if n.endswith("questions_valid.csv")), None)
        test_name = next((n for n in names if n.endswith("questions_test.csv")), None)
        if valid_name is None or test_name is None:
            raise FileNotFoundError(f"{zip_path} 内に questions_valid.csv / questions_test.csv が見つかりません。")
        with zf.open(valid_name) as f:
            valid_df = pd.read_csv(f)
        with zf.open(test_name) as f:
            test_df = pd.read_csv(f)
    return valid_df, test_df


def load_questions() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """valid/test質問を読み込む。展開済みフォルダを優先し、なければshare.zipを読む。"""
    valid_path, test_path = find_questions_from_directory()
    if valid_path is not None and test_path is not None:
        valid_df = pd.read_csv(valid_path)
        test_df = pd.read_csv(test_path)
        return valid_df, test_df, f"directory: {valid_path.parent}"

    zip_path = find_existing_path(SHARE_ZIP_CANDIDATES, "share.zip")
    valid_df, test_df = read_questions_from_zip(zip_path)
    return valid_df, test_df, f"zip: {zip_path}"


# =============================================================================
# 質問の簡易分類
# =============================================================================


EXT_PATTERN = re.compile(r"\.(md|csv|json|py|ipynb|xlsx|xlsm|docx|pptx|pdf|png|jpg|jpeg)\b", re.IGNORECASE)


def detect_extensions(text: Any) -> list[str]:
    """質問文に明示された拡張子を抽出する。"""
    found = ["." + m.group(1).lower() for m in EXT_PATTERN.finditer(str(text))]
    # 順序を保持して重複を落とす。
    return list(dict.fromkeys(found))


def classify_question_support(question: str) -> str:
    """EDA002由来インデックスで検索しやすい質問かを、拡張子・キーワードから粗く分類する。"""
    q = normalize_for_search(question)
    exts = detect_extensions(question)
    if exts:
        if any(ext in SUPPORTED_QUESTION_EXTENSIONS for ext in exts):
            if all(ext in SUPPORTED_QUESTION_EXTENSIONS for ext in exts):
                return "EDA002対象形式を明示"
            return "対象形式と対象外形式が混在"
        return "EDA002対象外形式を明示"

    unsupported_keywords = [
        "提案書", "契約書", "報告書", "スケジュール", "パワーポイント", "powerpoint",
        "excel", "エクセル", "pdf", "画像", "グラフ", "図", "黄色", "赤字", "太字",
        "下線", "ハイライト", "セル", "スライド", "ページ",
    ]
    if any(keyword in q for keyword in unsupported_keywords):
        return "対象外形式の可能性が高い"

    structured_keywords = ["列", "カラム", "json", "コード", "notebook", "モデル", "特徴量", "評価指標", "相関"]
    if any(keyword in q for keyword in structured_keywords):
        return "EDA002対象形式で拾える可能性あり"

    return "形式不明"


def detect_question_needs(question: str) -> str:
    """質問に含まれる処理要求を簡易タグ化する。"""
    q = normalize_for_search(question)
    tags: list[str] = []
    patterns = {
        "差分比較": ["比較", "更新内容", "旧版", "old", "最新版", "変更"],
        "書式抽出": ["太字", "赤字", "下線", "黄色", "オレンジ", "ハイライト"],
        "表・セル": ["セル", "列", "行", "シート", "pivot", "ピボット", "スケジュール"],
        "コード読解": [".py", "コード", "関数", "パラメータ", "条件"],
        "Notebook読解": [".ipynb", "notebook", "ノートブック"],
        "CSV/JSON読解": [".csv", ".json", "metrics", "leaderboard", "カラム"],
        "画像・グラフ": ["画像", "グラフ", "figure", ".png", "ヒストグラム"],
        "計算・集計": ["合計", "差額", "平均", "小数", "税込", "税額", "何日", "何件"],
    }
    for tag, keywords in patterns.items():
        if any(keyword in q for keyword in keywords):
            tags.append(tag)
    return ", ".join(tags) if tags else "未分類"


# =============================================================================
# BM25検索器
# =============================================================================


TOKEN_WORD_PATTERN = re.compile(r"[a-z0-9_]+|[一-龥々〆ヵヶぁ-んァ-ヴー]+")


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
    grams = char_ngrams(norm)
    return words + grams


@dataclass
class SearchHit:
    rank: int
    score: float
    chunk: dict[str, Any]


class BM25Retriever:
    """外部ライブラリなしで動く、簡易BM25検索器。"""

    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_lens: list[int] = []
        self.inverted_index: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.df: Counter[str] = Counter()
        self.avg_doc_len = 0.0
        self._build()

    def _metadata_text(self, chunk: dict[str, Any]) -> str:
        """パス・ファイル名・案件名は検索上重要なので、本文に重みづけして加える。"""
        metadata_parts = [
            chunk.get("relative_path", ""),
            chunk.get("relative_path", ""),
            chunk.get("file_name", ""),
            chunk.get("file_name", ""),
            chunk.get("extension", ""),
            chunk.get("project_name", ""),
            chunk.get("project_name", ""),
            chunk.get("major_folder", ""),
            chunk.get("area", ""),
        ]
        return "\n".join(str(part) for part in metadata_parts if part)

    def _indexed_text(self, chunk: dict[str, Any]) -> str:
        return self._metadata_text(chunk) + "\n" + str(chunk.get("text", ""))

    def _build(self) -> None:
        for doc_idx, chunk in enumerate(self.chunks):
            tokens = tokenize(self._indexed_text(chunk))
            counts = Counter(tokens)
            doc_len = sum(counts.values())
            self.doc_lens.append(max(doc_len, 1))
            for token, tf in counts.items():
                self.df[token] += 1
                self.inverted_index[token].append((doc_idx, tf))
        self.avg_doc_len = sum(self.doc_lens) / max(len(self.doc_lens), 1)
        logging.info("BM25 index built: chunks=%s vocab=%s avg_doc_len=%.2f", len(self.chunks), len(self.df), self.avg_doc_len)

    def _metadata_bonus(self, question: str, chunk: dict[str, Any]) -> float:
        """拡張子・ファイル名・案件名が質問に明示されている場合、軽くスコアを補正する。"""
        q_norm = normalize_for_search(question)
        relative_path = normalize_for_search(chunk.get("relative_path", ""))
        file_name = normalize_for_search(chunk.get("file_name", ""))
        project_name = normalize_for_search(chunk.get("project_name", ""))
        extension = normalize_for_search(chunk.get("extension", ""))

        bonus = 1.0
        mentioned_exts = detect_extensions(question)
        if mentioned_exts:
            if extension in mentioned_exts:
                bonus *= 1.35
            else:
                bonus *= 0.80

        # 質問にファイル名がそのまま含まれている場合はかなり重要。
        if file_name and file_name in q_norm:
            bonus *= 1.50

        # パス断片やプロジェクト名が含まれる場合も有利にする。
        if project_name and project_name in q_norm:
            bonus *= 1.20
        if relative_path and any(part and part in q_norm for part in relative_path.split("/")[-3:]):
            bonus *= 1.10
        return bonus

    def search(self, question: str, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
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

        if not scores:
            return []

        adjusted: list[tuple[int, float]] = []
        for doc_idx, score in scores.items():
            chunk = self.chunks[doc_idx]
            adjusted_score = score * self._metadata_bonus(question, chunk)
            adjusted.append((doc_idx, adjusted_score))

        adjusted.sort(key=lambda x: x[1], reverse=True)
        hits: list[SearchHit] = []
        for rank, (doc_idx, score) in enumerate(adjusted[:top_k], start=1):
            hits.append(SearchHit(rank=rank, score=score, chunk=self.chunks[doc_idx]))
        return hits


# =============================================================================
# 評価補助
# =============================================================================


def split_answer_terms(answer: Any) -> list[str]:
    """valid回答を、完全一致以外の緩い照合に使うための要素へ分割する。"""
    text = normalize_display_text(answer)
    if not text or text.lower() == "nan":
        return []

    # 日付や金額などは分割しすぎると意味が壊れるため、まず全体を候補に残す。
    raw_terms = [text]
    raw_terms.extend(re.split(r"[、,，/・\n]+", text))

    terms: list[str] = []
    for term in raw_terms:
        term = term.strip()
        if not term:
            continue
        compact = compact_for_match(term)
        # 1文字だけの一般語はノイズになりやすい。ただし数値や記号付きIDは残す。
        if len(compact) <= 1 and not re.search(r"\d", compact):
            continue
        terms.append(term)

    # 順序保持で重複除去。
    return list(dict.fromkeys(terms))


def answer_match_metrics(answer: Any, hits: list[SearchHit], top_k: int) -> dict[str, Any]:
    """valid回答が検索上位チャンクに含まれるかを、簡易的に確認する。"""
    answer_compact = compact_for_match(answer)
    terms = split_answer_terms(answer)
    term_compacts = [compact_for_match(term) for term in terms]
    term_compacts = [t for t in term_compacts if t]

    joined = "\n".join(
        str(hit.chunk.get("relative_path", "")) + "\n" + str(hit.chunk.get("text", ""))
        for hit in hits[:top_k]
    )
    joined_compact = compact_for_match(joined)

    exact_hit = bool(answer_compact and answer_compact in joined_compact)
    if term_compacts:
        matched_terms = [term for term, term_compact in zip(terms, term_compacts) if term_compact in joined_compact]
        term_coverage = len(matched_terms) / len(term_compacts)
    else:
        matched_terms = []
        term_coverage = 0.0

    loose_hit = exact_hit or term_coverage >= 0.80
    return {
        f"answer_exact_hit_top{top_k}": exact_hit,
        f"answer_term_coverage_top{top_k}": round(term_coverage, 4),
        f"answer_loose_hit_top{top_k}": loose_hit,
        f"matched_answer_terms_top{top_k}": "、".join(matched_terms),
    }


def build_result_rows(
    questions_df: pd.DataFrame,
    retriever: BM25Retriever,
    top_k: int,
    has_answer: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """質問ごとの検索結果サマリと、上位チャンクのlong tableを作る。"""
    summary_rows: list[dict[str, Any]] = []
    hit_rows: list[dict[str, Any]] = []

    for _, row in questions_df.iterrows():
        q_index = int(row.get("index", len(summary_rows)))
        question = str(row.get("question", ""))
        answer = row.get("answer", "") if has_answer else ""
        hits = retriever.search(question, top_k=top_k)

        support_category = classify_question_support(question)
        needs = detect_question_needs(question)
        mentioned_exts = detect_extensions(question)
        top1 = hits[0] if hits else None

        summary: dict[str, Any] = {
            "index": q_index,
            "question": question,
            "answer": answer,
            "support_category": support_category,
            "question_needs": needs,
            "mentioned_extensions": ", ".join(mentioned_exts),
            "top1_score": round(top1.score, 4) if top1 else 0.0,
            "top1_extension": top1.chunk.get("extension", "") if top1 else "",
            "top1_project_name": top1.chunk.get("project_name", "") if top1 else "",
            "top1_major_folder": top1.chunk.get("major_folder", "") if top1 else "",
            "top1_relative_path": top1.chunk.get("relative_path", "") if top1 else "",
            "top1_preview": clean_preview(top1.chunk.get("text", "")) if top1 else "",
        }
        if has_answer:
            for k in (1, 3, 5, top_k):
                summary.update(answer_match_metrics(answer, hits, min(k, top_k)))
        summary_rows.append(summary)

        for hit in hits:
            chunk = hit.chunk
            hit_rows.append(
                {
                    "index": q_index,
                    "rank": hit.rank,
                    "score": round(hit.score, 4),
                    "question": question,
                    "answer": answer,
                    "extension": chunk.get("extension", ""),
                    "project_name": chunk.get("project_name", ""),
                    "major_folder": chunk.get("major_folder", ""),
                    "relative_path": chunk.get("relative_path", ""),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "chunk_index": chunk.get("chunk_index", ""),
                    "preview": clean_preview(chunk.get("text", "")),
                }
            )

    return pd.DataFrame(summary_rows), pd.DataFrame(hit_rows)


# =============================================================================
# 集計・可視化
# =============================================================================


def create_retrieval_summaries(valid_summary: pd.DataFrame, valid_hits: pd.DataFrame, chunks: list[dict[str, Any]], top_k: int) -> dict[str, pd.DataFrame]:
    """レポート用の集計テーブルを作る。"""
    rows: list[dict[str, Any]] = []
    for k in (1, 3, 5, top_k):
        loose_col = f"answer_loose_hit_top{k}"
        exact_col = f"answer_exact_hit_top{k}"
        coverage_col = f"answer_term_coverage_top{k}"
        if loose_col in valid_summary.columns:
            rows.append(
                {
                    "top_k": k,
                    "loose_hit_count": int(valid_summary[loose_col].sum()),
                    "loose_hit_rate": round(float(valid_summary[loose_col].mean()), 4),
                    "exact_hit_count": int(valid_summary[exact_col].sum()),
                    "exact_hit_rate": round(float(valid_summary[exact_col].mean()), 4),
                    "mean_term_coverage": round(float(valid_summary[coverage_col].mean()), 4),
                }
            )
    hit_summary = pd.DataFrame(rows)

    support_summary = (
        valid_summary.groupby("support_category", dropna=False)
        .agg(
            question_count=("index", "count"),
            top5_loose_hit_rate=("answer_loose_hit_top5", "mean"),
            mean_top1_score=("top1_score", "mean"),
        )
        .reset_index()
    )
    support_summary["top5_loose_hit_rate"] = support_summary["top5_loose_hit_rate"].round(4)
    support_summary["mean_top1_score"] = support_summary["mean_top1_score"].round(4)

    top_result_extension_counts = (
        valid_summary["top1_extension"].value_counts(dropna=False).rename_axis("extension").reset_index(name="top1_count")
    )

    chunk_extension_counts = pd.Series([c.get("extension", "") for c in chunks]).value_counts(dropna=False).rename_axis("extension").reset_index(name="chunk_count")

    no_hit_cases = valid_summary[~valid_summary.get("answer_loose_hit_top5", False)].copy()
    keep_cols = [
        "index", "question", "answer", "support_category", "question_needs", "mentioned_extensions",
        "top1_score", "top1_extension", "top1_relative_path", "top1_preview",
    ]
    no_hit_cases = no_hit_cases[[c for c in keep_cols if c in no_hit_cases.columns]]

    return {
        "retrieval_hit_summary": hit_summary,
        "question_support_summary": support_summary,
        "top_result_extension_counts": top_result_extension_counts,
        "chunk_extension_counts": chunk_extension_counts,
        "no_hit_cases": no_hit_cases,
    }


def plot_outputs(summaries: dict[str, pd.DataFrame], valid_summary: pd.DataFrame) -> None:
    """レポート用の図を保存する。"""
    hit_summary = summaries["retrieval_hit_summary"]
    if not hit_summary.empty:
        plt.figure(figsize=(7, 4))
        plt.bar(hit_summary["top_k"].astype(str), hit_summary["loose_hit_rate"])
        plt.ylim(0, 1)
        plt.title("Valid質問: 上位Kチャンク内の回答語句ヒット率")
        plt.xlabel("Top K")
        plt.ylabel("Loose hit rate")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "01_valid_hit_rates.png", dpi=160)
        plt.close()

    ext_counts = summaries["top_result_extension_counts"]
    if not ext_counts.empty:
        plt.figure(figsize=(7, 4))
        plt.bar(ext_counts["extension"].astype(str), ext_counts["top1_count"])
        plt.title("Valid質問: Top1検索結果の拡張子分布")
        plt.xlabel("extension")
        plt.ylabel("count")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "02_top_result_extension_counts.png", dpi=160)
        plt.close()

    support = summaries["question_support_summary"].sort_values("question_count", ascending=False)
    if not support.empty:
        plt.figure(figsize=(9, 4))
        plt.bar(support["support_category"], support["question_count"])
        plt.title("Valid質問: EDA002インデックスでの対応しやすさ分類")
        plt.xlabel("category")
        plt.ylabel("question count")
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "03_question_support_categories.png", dpi=160)
        plt.close()

    if "top1_score" in valid_summary.columns and not valid_summary.empty:
        plt.figure(figsize=(7, 4))
        plt.hist(valid_summary["top1_score"].astype(float), bins=12)
        plt.title("Valid質問: Top1 BM25スコア分布")
        plt.xlabel("top1 score")
        plt.ylabel("question count")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "04_top1_score_distribution.png", dpi=160)
        plt.close()


# =============================================================================
# Markdownレポート
# =============================================================================


def df_to_md(df: pd.DataFrame, max_rows: int = 20) -> str:
    """tabulate依存を避けるため、簡易Markdownテーブルを自前生成する。"""
    if df is None or df.empty:
        return "該当データなし。"

    show_df = df.head(max_rows).copy()
    for col in show_df.columns:
        show_df[col] = show_df[col].map(lambda x: clean_preview(x, 120))

    headers = list(show_df.columns)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, row in show_df.iterrows():
        vals = [str(row[col]).replace("|", "｜") for col in headers]
        lines.append("| " + " | ".join(vals) + " |")
    if len(df) > max_rows:
        lines.append(f"\n※先頭{max_rows}行のみ表示。全{len(df)}行。")
    return "\n".join(lines)


def write_report(
    chunks_path: Path,
    question_source: str,
    chunks: list[dict[str, Any]],
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    valid_summary: pd.DataFrame,
    valid_hits: pd.DataFrame,
    test_hits: pd.DataFrame,
    summaries: dict[str, pd.DataFrame],
    top_k: int,
) -> None:
    """EDA003のMarkdownレポートを生成する。"""
    hit_summary = summaries["retrieval_hit_summary"]
    support_summary = summaries["question_support_summary"]
    no_hit_cases = summaries["no_hit_cases"]
    chunk_extension_counts = summaries["chunk_extension_counts"]
    top_result_extension_counts = summaries["top_result_extension_counts"]

    top5_hit_rate = None
    if not hit_summary.empty and 5 in set(hit_summary["top_k"]):
        top5_hit_rate = float(hit_summary.loc[hit_summary["top_k"] == 5, "loose_hit_rate"].iloc[0])

    example_cols = [
        "index", "question", "answer", "answer_loose_hit_top5", "answer_term_coverage_top5",
        "support_category", "top1_extension", "top1_relative_path", "top1_preview",
    ]
    example_df = valid_summary[[c for c in example_cols if c in valid_summary.columns]].head(10)

    report = f"""# EDA003: EDA002テキストチャンクを用いた検索ベースライン

## 目的・背景

### 背景

EDA002では、`.md`, `.csv`, `.json`, `.py`, `.ipynb` を対象に、RAGの初期インデックスへ投入しやすいテキストチャンクを作成した。これにより、Markdown文書、CSVの概要、JSON設定、Pythonコード、Notebookセル由来の情報については、機械的に検索できる状態になった。

一方で、テキスト抽出ができていることと、質問に対して必要な根拠チャンクを検索できることは別問題である。RAGでは、回答生成の前段階で正しい根拠を検索できなければ、LLMに渡す文脈が不足し、最終回答の精度も上がらない。そのため、回答生成に進む前に、まず検索部分だけを切り出して性能と失敗傾向を確認する必要がある。

### 本EDAの目的

EDA003では、EDA002で作成した `text_chunks.jsonl` を用いて、valid質問に対する検索ベースラインを作成する。検索器には外部ライブラリに依存しない簡易BM25を用い、各質問に対して上位{top_k}件のチャンクを取得する。

本EDAの主目的は、最終回答を生成することではなく、以下を確認することである。

- EDA002対象形式のチャンクだけで、valid質問の根拠候補をどの程度拾えるか
- Top1 / Top3 / Top5 / Top{top_k} の検索結果に、正解語句が含まれる割合はどの程度か
- `.md`, `.csv`, `.json`, `.py`, `.ipynb` のうち、検索上位に出やすい形式はどれか
- 対象外形式、書式情報、画像、Excelセルなどが必要な質問でどの程度失敗するか
- 次に優先して抽出器を作るべきファイル形式は何か

### 注意点

ここで算出しているヒット率は、valid回答文字列が上位チャンク内に含まれるかを簡易的に見たものであり、SIGNATEの正式評価スコアではない。回答が本文に明示されていない計算問題や、表記揺れが大きい問題では、実際の回答可能性と一致しない場合がある。ただし、検索ベースラインの弱点を把握する指標としては有用である。

## 入力データ

| 項目 | 内容 |
|---|---|
| チャンク入力 | `{display_path(chunks_path)}` |
| 質問データ | `{display_source(question_source)}` |
| チャンク数 | {len(chunks)} |
| valid質問数 | {len(valid_df)} |
| test質問数 | {len(test_df)} |
| 検索方式 | 簡易BM25（パス・ファイル名・案件名を補助的に重み付け） |
| 検索上位件数 | Top {top_k} |

## インデックス対象チャンクの拡張子分布

{df_to_md(chunk_extension_counts)}

## Valid検索ヒット率

{df_to_md(hit_summary)}

## Valid質問の対応しやすさ分類

{df_to_md(support_summary)}

## Top1検索結果の拡張子分布

{df_to_md(top_result_extension_counts)}

## Valid検索結果サンプル

{df_to_md(example_df, max_rows=10)}

## Top5で正解語句を拾えなかったValid質問

{df_to_md(no_hit_cases, max_rows=15)}

## 考察

EDA002由来のテキストチャンクを使うことで、コード、Notebook、JSON、CSV概要、Markdownに関する質問では、検索候補を一定程度取得できる。特に、質問文に `.py`, `.ipynb`, `.json`, `.csv`, `.md` などのファイル名や拡張子が明示されている場合は、パス情報と本文情報を組み合わせたBM25検索が有効に働きやすい。

一方で、本コンペの質問には、PowerPoint、Word、Excel、PDF、画像、書式情報、セル色、グラフ読み取り、旧版と最新版の差分比較などを必要とするものが多く含まれる。これらはEDA002の対象外であるため、今回の検索ベースラインだけでは根拠チャンクを取得できない。Top5で正解語句を拾えない質問の多くは、検索方式そのものよりも、インデックス対象に必要ファイル形式が含まれていないことが主因である可能性が高い。

また、CSVについてはサマリとサンプルをチャンク化しているため、列名やデータ概要の検索には使えるが、特定条件での行抽出や集計には不十分である。今後は、CSVを単なるテキストチャンクとして扱うだけでなく、質問に応じてpandasで直接検索・集計する処理を組み込む必要がある。

## 次にやるべきこと

1. EDA004では、`.docx`, `.pptx`, `.xlsx`, `.pdf` の本文抽出と、書式・セル色などのメタ情報抽出を扱う。
2. 検索評価では、valid質問を「対象形式で回答可能」「対象外形式が必要」「計算・集計が必要」に分けて確認する。
3. `.csv` と `.xlsx` は、RAGチャンク検索とは別に、表データ検索・集計ツールとして扱う方針を検討する。
4. 差分比較、画像・グラフ読み取り、書式抽出は、通常のテキストRAGとは別系統のAgentツールとして設計する。

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `tables/valid_retrieval_results.csv` | valid質問ごとの検索結果サマリ |
| `tables/valid_top_chunks.csv` | valid質問ごとの上位チャンク一覧 |
| `tables/test_top_chunks.csv` | test質問ごとの上位チャンク一覧 |
| `tables/retrieval_hit_summary.csv` | TopK別の簡易ヒット率 |
| `tables/question_support_summary.csv` | 質問分類別のヒット率 |
| `tables/no_hit_cases.csv` | Top5で正解語句を拾えなかったvalid質問 |
| `figures/01_valid_hit_rates.png` | TopK別ヒット率 |
| `figures/02_top_result_extension_counts.png` | Top1拡張子分布 |
| `figures/03_question_support_categories.png` | 質問分類分布 |
| `figures/04_top1_score_distribution.png` | Top1スコア分布 |
"""

    REPORT_PATH.write_text(report, encoding="utf-8")

    required_phrases = [
        "## 目的・背景",
        "### 背景",
        "### 本EDAの目的",
        "## Valid検索ヒット率",
        "## Top5で正解語句を拾えなかったValid質問",
        "## 考察",
        "## 次にやるべきこと",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in report]
    if missing:
        raise RuntimeError(f"eda003_report.md に必須章が不足しています: {missing}")

    if top5_hit_rate is not None:
        logging.info("Top5 loose hit rate: %.4f", top5_hit_rate)


# =============================================================================
# メイン処理
# =============================================================================


def main(top_k: int = DEFAULT_TOP_K) -> None:
    setup()

    chunks_path = find_existing_path(CHUNK_PATH_CANDIDATES, "EDA002の text_chunks.jsonl")
    chunks = read_jsonl(chunks_path)
    if not chunks:
        raise ValueError(f"チャンクが空です: {chunks_path}")

    valid_df, test_df, question_source = load_questions()
    required_valid_cols = {"index", "question", "answer"}
    required_test_cols = {"index", "question"}
    if not required_valid_cols.issubset(set(valid_df.columns)):
        raise ValueError(f"questions_valid.csv に必要列がありません: {required_valid_cols}")
    if not required_test_cols.issubset(set(test_df.columns)):
        raise ValueError(f"questions_test.csv に必要列がありません: {required_test_cols}")

    logging.info("chunks_path=%s", chunks_path)
    logging.info("question_source=%s", question_source)
    logging.info("valid_questions=%s test_questions=%s", len(valid_df), len(test_df))

    retriever = BM25Retriever(chunks)

    valid_summary, valid_hits = build_result_rows(valid_df, retriever, top_k=top_k, has_answer=True)
    test_summary, test_hits = build_result_rows(test_df, retriever, top_k=top_k, has_answer=False)

    summaries = create_retrieval_summaries(valid_summary, valid_hits, chunks, top_k=top_k)

    save_csv(valid_summary, TABLE_DIR / "valid_retrieval_results.csv")
    save_csv(valid_hits, TABLE_DIR / "valid_top_chunks.csv")
    save_csv(test_summary, TABLE_DIR / "test_retrieval_results.csv")
    save_csv(test_hits, TABLE_DIR / "test_top_chunks.csv")
    for name, df in summaries.items():
        save_csv(df, TABLE_DIR / f"{name}.csv")

    index_stats = pd.DataFrame(
        [
            {
                "chunks_path": str(chunks_path),
                "question_source": question_source,
                "chunk_count": len(chunks),
                "valid_question_count": len(valid_df),
                "test_question_count": len(test_df),
                "top_k": top_k,
                "target_extensions": ", ".join(sorted(TARGET_EXTENSIONS)),
            }
        ]
    )
    save_csv(index_stats, TABLE_DIR / "retrieval_index_stats.csv")

    plot_outputs(summaries, valid_summary)
    write_report(
        chunks_path=chunks_path,
        question_source=question_source,
        chunks=chunks,
        valid_df=valid_df,
        test_df=test_df,
        valid_summary=valid_summary,
        valid_hits=valid_hits,
        test_hits=test_hits,
        summaries=summaries,
        top_k=top_k,
    )

    print(f"EDA003 finished: {REPORT_PATH}")
    print(f"tables: {TABLE_DIR}")
    print(f"figures: {FIG_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EDA003: EDA002テキストチャンクを用いた検索ベースライン")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="質問ごとに取得する上位チャンク数")
    args = parser.parse_args()
    main(top_k=args.top_k)
