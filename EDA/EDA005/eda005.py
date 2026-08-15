from __future__ import annotations

import argparse
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

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda005.py は「プロジェクト直下 / EDA / EDA005 / eda005.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
SUBMISSION_DIR = OUTPUT_DIR / "submission"
REPORT_PATH = OUTPUT_DIR / "eda005_report.md"
LOG_PATH = OUTPUT_DIR / "eda005.log"

EDA002_CHUNKS = BASE_DIR / "EDA" / "EDA002" / "texts" / "text_chunks.jsonl"
EDA004_CHUNKS = BASE_DIR / "EDA" / "EDA004" / "texts" / "text_chunks.jsonl"
QUESTION_DIR = RAW_DIR / "share" / "share" / "質問回答"
SAMPLE_SUBMIT_PATH = RAW_DIR / "sample_submit" / "配布データ" / "predictions.csv"

DEFAULT_TOP_K = 10
PREVIEW_LENGTH = 300
MIN_ANSWER_SCORE = 25.0


# =============================================================================
# 基本ユーティリティ
# =============================================================================


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

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
    """BM25用に、全角半角・大文字小文字・空白揺れを抑える。"""
    text = normalize_display_text(text)
    text = unicodedata.normalize("NFKC", text).lower()
    return text.replace("\u3000", " ")


def clean_preview(text: Any, max_len: int = PREVIEW_LENGTH) -> str:
    """ログで読みやすい短い本文プレビューを作る。"""
    text = re.sub(r"\s+", " ", normalize_display_text(text)).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def save_csv(df: pd.DataFrame, path: Path, header: bool = True) -> None:
    """提出ファイル以外はExcelでも開きやすいようにUTF-8 BOM付きで保存する。"""
    df.to_csv(path, index=False, header=header, encoding="utf-8-sig")


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
                raise ValueError(f"JSONLの読み込みに失敗しました: {path} line={line_no}") from exc
    return records


def load_questions() -> tuple[pd.DataFrame, pd.DataFrame]:
    """valid/test質問CSVを読み込む。"""
    valid_df = pd.read_csv(QUESTION_DIR / "questions_valid.csv")
    test_df = pd.read_csv(QUESTION_DIR / "questions_test.csv")
    return valid_df, test_df


def load_sample_submit() -> pd.DataFrame:
    """sample_submitの列構造を読み込む。ヘッダーなしの2列形式を前提にする。"""
    return pd.read_csv(SAMPLE_SUBMIT_PATH, header=None, names=["index", "answer"])


def chunk_text(chunk: dict[str, Any]) -> str:
    """EDA002とEDA004で異なる本文キーを吸収する。"""
    return str(chunk.get("text") or chunk.get("chunk_text") or "")


def load_unified_chunks() -> list[dict[str, Any]]:
    """EDA002とEDA004の検索用チャンクを統合する。"""
    chunks: list[dict[str, Any]] = []
    for source_name, path in [("EDA002", EDA002_CHUNKS), ("EDA004", EDA004_CHUNKS)]:
        for record in read_jsonl(path):
            text = chunk_text(record)
            if not text.strip():
                continue
            normalized = dict(record)
            normalized["source_eda"] = source_name
            normalized["text"] = text
            normalized.setdefault("chunk_id", f"{source_name}_{len(chunks):06d}")
            normalized.setdefault("extension", "")
            normalized.setdefault("relative_path", "")
            normalized.setdefault("file_name", "")
            normalized.setdefault("project_name", "")
            normalized.setdefault("major_folder", "")
            chunks.append(normalized)
    logging.info("Loaded unified chunks: %s", len(chunks))
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
    grams = char_ngrams(norm)
    return words + grams


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
# ルール/テンプレ回答
# =============================================================================


def question_tags(question: str) -> str:
    """回答ログ用に、質問が要求する処理を粗く分類する。"""
    q = normalize_for_search(question)
    tags: list[str] = []
    patterns = {
        "計算": ["合計", "平均", "最も高い", "最も低い", "差額", "税額", "何日", "何件", "算出"],
        "書式": ["太字", "赤字", "下線", "マーカー", "ハイライト", "黄色"],
        "画像": ["画像", "グラフ", "figure", ".png"],
        "差分": ["比較", "旧版", "最新版", "変更"],
        "表": ["excel", "xlsx", "セル", "シート", "pivot", "フィルター"],
        "コード": [".py", "コード", "modeling", "パラメータ"],
    }
    for tag, keys in patterns.items():
        if any(key in q for key in keys):
            tags.append(tag)
    return ", ".join(tags) if tags else "検索"


def is_weak_question(question: str) -> bool:
    """ルール回答では危険な質問タイプを判定する。"""
    tags = question_tags(question)
    return any(tag in tags for tag in ["画像", "差分"]) or "書式" in tags


def split_candidate_units(text: str) -> list[str]:
    """上位チャンク本文を、回答候補にしやすい短い単位へ分割する。"""
    lines: list[str] = []
    for raw in re.split(r"[\n。]", text):
        line = re.sub(r"\s+", " ", normalize_display_text(raw)).strip()
        if not line:
            continue
        if line.startswith(("# source_path", "# file_name", "# extension")):
            continue
        if len(line) < 3:
            continue
        lines.append(line)
    return lines


def content_tokens(text: str) -> set[str]:
    """回答候補行との重なりを見るため、短すぎるトークンを除く。"""
    stop = {
        "について", "ください", "ですか", "ますか", "どれ", "どの", "もの", "こと",
        "ファイル", "プロジェクト", "案件", "答えて", "教えて", "すべて",
    }
    tokens = set()
    for token in TOKEN_WORD_PATTERN.findall(normalize_for_search(text)):
        if len(token) <= 1:
            continue
        if token in stop:
            continue
        tokens.add(token)
    return tokens


def choose_answer_from_hits(question: str, hits: list[SearchHit], min_score: float) -> tuple[str, str]:
    """検索上位チャンクから、質問語と重なる短い行を回答として選ぶ。"""
    if not hits or hits[0].score < min_score:
        return "わかりません", "low_score_or_no_hit"
    if is_weak_question(question):
        return "わかりません", "unsupported_question_type"

    q_tokens = content_tokens(question)
    best_line = ""
    best_score = -1.0

    for hit in hits[:5]:
        for line in split_candidate_units(chunk_text(hit.chunk)):
            line_tokens = content_tokens(line)
            overlap = len(q_tokens & line_tokens)
            numeric_bonus = 1 if re.search(r"\d", line) else 0
            path_bonus = 0.2 if hit.rank == 1 else 0
            score = overlap * 2 + numeric_bonus + path_bonus - len(line) / 500
            if score > best_score:
                best_score = score
                best_line = line

    if not best_line or best_score <= 0:
        return "わかりません", "no_candidate_line"

    # 提出回答は最大1000トークン制約があるため、初回はかなり短めに切る。
    answer = best_line
    prefixes = ["row_", "paragraph_", "slide_", "##", "- "]
    for prefix in prefixes:
        answer = re.sub(rf"^{re.escape(prefix)}\d*[:_ -]*", "", answer).strip()
    if len(answer) > 180:
        answer = answer[:180].rstrip() + "..."
    return answer, "template_line_overlap"


def compact_for_match(text: Any) -> str:
    """valid評価用に、空白・一部記号を除去する。"""
    text = normalize_for_search(text)
    text = text.replace(",", "").replace("，", "")
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[\"'`『』「」\[\]（）(){}]", "", text)


def valid_answer_hit(answer: Any, predicted: str) -> bool:
    """validで、テンプレ回答に正解語句が含まれるかを簡易確認する。"""
    true_compact = compact_for_match(answer)
    pred_compact = compact_for_match(predicted)
    return bool(true_compact and true_compact in pred_compact)


def build_answers(
    questions_df: pd.DataFrame,
    retriever: BM25Retriever,
    top_k: int,
    min_score: float,
    has_answer: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """質問ごとに検索し、テンプレ回答と検索ログを作る。"""
    answer_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []

    for _, row in questions_df.iterrows():
        q_index = int(row["index"])
        question = str(row["question"])
        true_answer = row.get("answer", "") if has_answer else ""
        hits = retriever.search(question, top_k=top_k)
        predicted, reason = choose_answer_from_hits(question, hits, min_score)
        top1 = hits[0] if hits else None

        answer_row: dict[str, Any] = {
            "index": q_index,
            "question": question,
            "answer": predicted,
            "generation_reason": reason,
            "question_tags": question_tags(question),
            "top1_score": round(top1.score, 4) if top1 else 0.0,
            "top1_source_eda": top1.chunk.get("source_eda", "") if top1 else "",
            "top1_extension": top1.chunk.get("extension", "") if top1 else "",
            "top1_relative_path": top1.chunk.get("relative_path", "") if top1 else "",
            "top1_preview": clean_preview(chunk_text(top1.chunk)) if top1 else "",
        }
        if has_answer:
            answer_row["true_answer"] = true_answer
            answer_row["template_exact_contains_answer"] = valid_answer_hit(true_answer, predicted)
        answer_rows.append(answer_row)

        for hit in hits:
            retrieval_rows.append(
                {
                    "index": q_index,
                    "rank": hit.rank,
                    "score": round(hit.score, 4),
                    "question": question,
                    "source_eda": hit.chunk.get("source_eda", ""),
                    "extension": hit.chunk.get("extension", ""),
                    "project_name": hit.chunk.get("project_name", ""),
                    "major_folder": hit.chunk.get("major_folder", ""),
                    "relative_path": hit.chunk.get("relative_path", ""),
                    "chunk_id": hit.chunk.get("chunk_id", ""),
                    "preview": clean_preview(chunk_text(hit.chunk)),
                }
            )

    return pd.DataFrame(answer_rows), pd.DataFrame(retrieval_rows)


def create_submission(test_answers: pd.DataFrame, sample_submit: pd.DataFrame) -> tuple[Path, Path]:
    """sample_submitの順序に合わせてpredictions.csvとzipを作る。"""
    merged = sample_submit[["index"]].merge(test_answers[["index", "answer"]], on="index", how="left")
    merged["answer"] = merged["answer"].fillna("わかりません")
    predictions_path = SUBMISSION_DIR / "predictions.csv"
    zip_path = SUBMISSION_DIR / "eda005_bm25_template_submission.zip"
    # sample_submitと同じくヘッダーなしで保存する。
    merged.to_csv(predictions_path, index=False, header=False, encoding="utf-8-sig")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(predictions_path, arcname="predictions.csv")
    return predictions_path, zip_path


def make_report(
    chunks: list[dict[str, Any]],
    valid_answers: pd.DataFrame,
    test_answers: pd.DataFrame,
    predictions_path: Path,
    zip_path: Path,
    top_k: int,
    min_score: float,
) -> None:
    """EDA005のMarkdownレポートを生成する。"""
    source_counts = pd.Series([c.get("source_eda", "") for c in chunks]).value_counts().rename_axis("source_eda").reset_index(name="chunk_count")
    extension_counts = pd.Series([c.get("extension", "") for c in chunks]).value_counts().rename_axis("extension").reset_index(name="chunk_count")
    reason_counts = test_answers["generation_reason"].value_counts().rename_axis("generation_reason").reset_index(name="test_count")
    tag_counts = test_answers["question_tags"].value_counts().rename_axis("question_tags").reset_index(name="test_count")

    valid_exact = 0.0
    if "template_exact_contains_answer" in valid_answers.columns and len(valid_answers) > 0:
        valid_exact = float(valid_answers["template_exact_contains_answer"].mean())

    lines: list[str] = []
    lines.append("# EDA005: 統合BM25検索とテンプレ回答による提出候補作成")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append(
        "EDA003ではEDA002由来チャンクだけを使った検索ベースラインを作成し、"
        "EDA004ではOffice文書とPDFの抽出対象を広げました。"
        "次の段階として、EDA002とEDA004の検索用チャンクを統合し、test質問100件に対する提出候補を作成します。"
    )
    lines.append("")
    lines.append(
        "本来は検索した根拠をLLMへ渡して回答生成する構成が自然ですが、今回の初回提出候補ではLLM APIやローカルLLMを使いません。"
        "理由は、外部送信なしで提出形式、全問処理、検索ログ、回答ログの再現性を先に確認するためです。"
        "また、このPCにOllamaが未導入であり、OpenRouterなどの外部API利用は今後検討段階のため、"
        "まずはBM25検索とルール/テンプレ回答で安全に一周させます。"
    )
    lines.append("")
    lines.append("このEDA005はスコア最大化ではなく、提出パイプラインの動作確認を主目的とします。")
    lines.append("")
    lines.append("## 手法")
    lines.append("")
    lines.append(f"- 入力チャンク: `EDA002/texts/text_chunks.jsonl` と `EDA004/texts/text_chunks.jsonl`")
    lines.append(f"- 検索方式: 簡易BM25")
    lines.append(f"- 検索上位件数: Top {top_k}")
    lines.append(f"- 回答生成: 上位チャンク内で質問語と重なる行を選ぶテンプレ方式")
    lines.append(f"- 低スコア閾値: {min_score}")
    lines.append("- 画像、差分、書式などテンプレ回答が危険な質問は `わかりません` を返す")
    lines.append("")
    lines.append("## 全体サマリ")
    lines.append("")
    lines.append(f"- 統合チャンク数: {len(chunks)}")
    lines.append(f"- valid質問数: {len(valid_answers)}")
    lines.append(f"- test質問数: {len(test_answers)}")
    lines.append(f"- validでテンプレ回答が正解全文を含んだ割合: {valid_exact:.4f}")
    lines.append(f"- 提出候補CSV: `{predictions_path.relative_to(BASE_DIR).as_posix()}`")
    lines.append(f"- 提出候補zip: `{zip_path.relative_to(BASE_DIR).as_posix()}`")
    lines.append("")
    lines.append("## チャンク内訳")
    lines.append("")
    lines.append(df_to_markdown(source_counts))
    lines.append("")
    lines.append("凡例: `source_eda` はチャンクの由来、`chunk_count` は統合検索に使ったチャンク数を表します。")
    lines.append("")
    lines.append(df_to_markdown(extension_counts))
    lines.append("")
    lines.append("凡例: `extension` は元ファイルの拡張子、`chunk_count` はその拡張子由来のチャンク数を表します。")
    lines.append("")
    lines.append("## test回答生成理由")
    lines.append("")
    lines.append(df_to_markdown(reason_counts))
    lines.append("")
    lines.append("凡例: `generation_reason` はテンプレ回答の生成理由、`test_count` はtest質問内の件数を表します。")
    lines.append("")
    lines.append("## test質問タイプ")
    lines.append("")
    lines.append(df_to_markdown(tag_counts))
    lines.append("")
    lines.append("凡例: `question_tags` は質問文から推定した処理タイプ、`test_count` はtest質問内の件数を表します。")
    lines.append("")
    lines.append("## valid回答サンプル")
    lines.append("")
    lines.append(df_to_markdown(valid_answers[["index", "question", "true_answer", "answer", "generation_reason", "top1_relative_path"]].head(15)))
    lines.append("")
    lines.append("## 注意点")
    lines.append("")
    lines.append("- この提出候補はLLMを使わないため、文章読解や複数資料照合はかなり弱いです。")
    lines.append("- 計算、画像、差分、細かな書式抽出は今後の専用処理で改善する前提です。")
    lines.append("- `わかりません` が多くても、まず提出形式と再実行可能な生成手順を確認する目的です。")
    lines.append("- SIGNATEへの提出はこのスクリプトでは行っていません。")
    lines.append("")
    lines.append("## 次にやること")
    lines.append("")
    lines.append("1. validで検索上位に正解根拠があるがテンプレ回答が外れている問題を確認する。")
    lines.append("2. CSV/XLSXの計算問題をpandas/openpyxlで直接処理するルールを追加する。")
    lines.append("3. OpenRouterやOllamaを使う場合は、回答生成部分だけ差し替え、モデル名とプロンプトをログに保存する。")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_eda_summary() -> None:
    """EDA総括にEDA005の概要を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    marker = "## 現時点の総合判断"
    if "## EDA005の要点" in text:
        return
    addition = """
## EDA005の要点

EDA005では、EDA002とEDA004の検索用チャンクを統合し、LLMを使わない `BM25検索 + ルール/テンプレ回答` で提出候補を作成しました。  
この方針にした理由は、LLM APIやローカルLLMを導入する前に、外部送信なしで提出形式、全問処理、検索ログ、回答ログの再現性を確認するためです。OllamaはこのPCに未導入であり、OpenRouterなどの外部API利用は今後検討段階としました。

本EDAはスコア最大化ではなく、提出パイプラインを一度通すためのベースラインです。画像、差分、書式、複雑な計算が必要な質問では `わかりません` を返す場合があります。提出候補は `EDA/EDA005/submission/predictions.csv` と `EDA/EDA005/submission/eda005_bm25_template_submission.zip` に保存します。

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA005: BM25 + template submission baseline.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--min-answer-score", type=float, default=MIN_ANSWER_SCORE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()

    valid_df, test_df = load_questions()
    sample_submit = load_sample_submit()
    chunks = load_unified_chunks()
    retriever = BM25Retriever(chunks)

    valid_answers, valid_retrieval = build_answers(valid_df, retriever, args.top_k, args.min_answer_score, has_answer=True)
    test_answers, test_retrieval = build_answers(test_df, retriever, args.top_k, args.min_answer_score, has_answer=False)

    save_csv(valid_answers, TABLE_DIR / "valid_answer_log.csv")
    save_csv(valid_retrieval, TABLE_DIR / "valid_retrieval_log.csv")
    save_csv(test_answers, TABLE_DIR / "test_answer_log.csv")
    save_csv(test_retrieval, TABLE_DIR / "test_retrieval_log.csv")

    predictions_path, zip_path = create_submission(test_answers, sample_submit)
    make_report(chunks, valid_answers, test_answers, predictions_path, zip_path, args.top_k, args.min_answer_score)
    update_eda_summary()

    print(f"EDA005 finished: {REPORT_PATH}")
    print(f"predictions: {predictions_path}")
    print(f"zip: {zip_path}")


if __name__ == "__main__":
    main()
