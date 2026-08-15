from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda010.py は「プロジェクト直下 / EDA / EDA010 / eda010.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
CONTEXT_DIR = OUTPUT_DIR / "contexts"
REPORT_PATH = OUTPUT_DIR / "eda010_report.md"

EDA002_DOCS = BASE_DIR / "EDA" / "EDA002" / "texts" / "extracted_documents.jsonl"
EDA004_DOCS = BASE_DIR / "EDA" / "EDA004" / "texts" / "extracted_documents.jsonl"
EDA009_COMPARISON = BASE_DIR / "EDA" / "EDA009" / "tables" / "valid_guided_retrieval_comparison.csv"

DEFAULT_CHAR_LIMIT = 24000
PREVIEW_LENGTH = 220


def setup() -> None:
    """出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


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
    """表で確認しやすい短い本文プレビューを作る。"""
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


def load_documents() -> dict[str, dict[str, Any]]:
    """EDA002とEDA004の文書単位抽出結果を、相対パスで引ける辞書にする。"""
    docs: dict[str, dict[str, Any]] = {}
    for source_eda, path in [("EDA002", EDA002_DOCS), ("EDA004", EDA004_DOCS)]:
        for record in read_jsonl(path):
            relative_path = normalize_display_text(record.get("relative_path", ""))
            text = str(record.get("text") or "")
            if not relative_path or not text.strip():
                continue
            normalized = dict(record)
            normalized["source_eda"] = source_eda
            normalized["relative_path"] = relative_path
            normalized["text"] = text
            docs[relative_path] = normalized
    return docs


def answer_hit(answer: Any, text: str) -> bool:
    """文書全体にvalid正解語句が含まれるかを簡易判定する。"""
    answer_compact = compact_for_match(answer)
    text_compact = compact_for_match(text)
    return bool(answer_compact and answer_compact in text_compact)


def make_context(row: pd.Series, doc: dict[str, Any], text: str) -> str:
    """LLMに渡す文書単位Markdownコンテキストを作る。"""
    return "\n".join(
        [
            f"# valid_{int(row['index']):03d} Whole Document Context",
            "",
            "## Question",
            str(row["question"]),
            "",
            "## Target Document",
            f"- relative_path: {doc.get('relative_path', '')}",
            f"- source_eda: {doc.get('source_eda', '')}",
            f"- extension: {doc.get('extension', '')}",
            f"- project_name: {doc.get('project_name', '')}",
            f"- major_folder: {doc.get('major_folder', '')}",
            "",
            "## Document Text",
            "```text",
            text,
            "```",
            "",
        ]
    )


def evaluate(args: argparse.Namespace) -> pd.DataFrame:
    """EDA009で対象文書を選べた質問について、文書全体コンテキストの有効性を確認する。"""
    docs = load_documents()
    comparison = pd.read_csv(EDA009_COMPARISON)
    targets = comparison[
        (comparison["document_hints"].fillna("").astype(str).str.len() > 0)
        & (comparison["capabilities"].fillna("").astype(str).str.contains("document_qa"))
    ].copy()

    rows: list[dict[str, Any]] = []
    for _, row in targets.iterrows():
        q_index = int(row["index"])
        target_path = normalize_display_text(row.get("guided_top1_path", ""))
        doc = docs.get(target_path)
        context_path = CONTEXT_DIR / f"valid_{q_index:03d}_whole_document_context.md"
        found = doc is not None
        text = str(doc.get("text", "")) if doc else ""
        clipped = len(text) > args.char_limit
        context_text = text[: args.char_limit] if clipped else text
        if found:
            context_path.write_text(make_context(row, doc, context_text), encoding="utf-8")

        rows.append(
            {
                "index": q_index,
                "question": row["question"],
                "answer": row["answer"],
                "document_hints": row.get("document_hints", ""),
                "capabilities": row.get("capabilities", ""),
                "target_document_path": target_path,
                "document_found": found,
                "source_eda": doc.get("source_eda", "") if doc else "",
                "extension": doc.get("extension", "") if doc else "",
                "document_chars": len(text),
                "context_chars": len(context_text),
                "clipped_by_char_limit": clipped,
                "answer_hit_whole_document": answer_hit(row["answer"], text) if found else False,
                "answer_hit_context": answer_hit(row["answer"], context_text) if found else False,
                "context_path": context_path.relative_to(BASE_DIR).as_posix() if found else "",
                "document_preview": clean_preview(text),
            }
        )
    return pd.DataFrame(rows)


def make_summary(result: pd.DataFrame) -> pd.DataFrame:
    """文書単位コンテキスト化の集計表を作る。"""
    if result.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {"metric": "target_questions", "value": len(result)},
            {"metric": "document_found", "value": int(result["document_found"].sum())},
            {"metric": "answer_hit_whole_document", "value": int(result["answer_hit_whole_document"].sum())},
            {"metric": "answer_hit_context", "value": int(result["answer_hit_context"].sum())},
            {"metric": "clipped_by_char_limit", "value": int(result["clipped_by_char_limit"].sum())},
            {"metric": "mean_document_chars", "value": round(float(result["document_chars"].mean()), 1)},
            {"metric": "max_document_chars", "value": int(result["document_chars"].max())},
        ]
    )


def write_report(result: pd.DataFrame, summary: pd.DataFrame, args: argparse.Namespace) -> None:
    """EDA010のMarkdownレポートを保存する。"""
    valid_002 = result[result["index"] == 2]
    lines: list[str] = []
    lines.append("# EDA010: 文書単位LLMコンテキストの検証")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append(
        "EDA009で対象文書を推定できた質問について、チャンクTopKではなく文書全体をLLM向けMarkdownにした場合に、"
        "正解語句が文書内に含まれるか、無料LLMへ渡せる長さかを確認します。ここではLLM APIは呼びません。"
    )
    lines.append("")
    lines.append("## 実行設定")
    lines.append("")
    lines.append(f"- char_limit: {args.char_limit}")
    lines.append("- 入力: `EDA/EDA009/tables/valid_guided_retrieval_comparison.csv`")
    lines.append("- 文書本文: `EDA/EDA002/texts/extracted_documents.jsonl`, `EDA/EDA004/texts/extracted_documents.jsonl`")
    lines.append("")
    lines.append("## 集計")
    lines.append("")
    lines.append(df_to_markdown(summary))
    lines.append("")
    lines.append("凡例: `metric` は集計指標、`value` は対象質問または文書単位での件数・文字数を表します。")
    lines.append("")
    lines.append("## valid_002の確認")
    lines.append("")
    if valid_002.empty:
        lines.append("valid_002 は対象外でした。")
    else:
        cols = [
            "index",
            "answer",
            "target_document_path",
            "document_chars",
            "answer_hit_whole_document",
            "answer_hit_context",
            "context_path",
        ]
        lines.append(df_to_markdown(valid_002[cols]))
        lines.append("")
        lines.append("凡例: `target_document_path` はEDA009で選ばれた文書、`answer_hit_whole_document` は文書全体に正解語句が含まれるか、`answer_hit_context` は文字数上限後のLLM入力に正解語句が含まれるかを表します。")
    lines.append("")
    lines.append("## 対象質問一覧")
    lines.append("")
    cols = [
        "index",
        "document_hints",
        "answer",
        "document_found",
        "document_chars",
        "answer_hit_context",
        "target_document_path",
    ]
    lines.append(df_to_markdown(result[cols], max_rows=30))
    lines.append("")
    lines.append("凡例: `document_hints` は質問から検出した対象文書名、`document_found` は文書単位本文を取得できたか、`document_chars` は文書本文の文字数を表します。")
    lines.append("")
    lines.append("## 考察")
    lines.append("")
    lines.append("- 文書指定があるdocument_qaでは、チャンクTopKより文書全体コンテキストの方が根拠漏れを減らせる可能性があります。")
    lines.append("- ただし、文書全体が長すぎる場合は、章・スライド単位の再ランキングが必要です。")
    lines.append("- 表計算、書式、画像、差分が必要な質問は、文書全体をLLMに渡すだけでは不十分です。")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_eda_summary(result: pd.DataFrame, summary: pd.DataFrame) -> None:
    """EDA総括にEDA010の概要を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    if "## EDA010の要点" in text:
        return
    marker = "## 最終構成の方針"
    metrics = summary.set_index("metric")["value"].to_dict() if not summary.empty else {}
    addition = f"""
## EDA010の要点

EDA010では、EDA009で対象文書を推定できたdocument_qa質問について、チャンクTopKではなく文書全体をLLM向けMarkdownにする検証を行いました。LLM APIは呼ばず、対象文書を取得できるか、文書全体または文字数上限内にvalid正解語句が含まれるかを確認しています。

対象質問は {metrics.get('target_questions', 0)} 件、文書本文を取得できた質問は {metrics.get('document_found', 0)} 件、文書全体に正解語句が含まれた質問は {metrics.get('answer_hit_whole_document', 0)} 件、文字数上限後のコンテキストに正解語句が含まれた質問は {metrics.get('answer_hit_context', 0)} 件でした。文書単位コンテキストは `EDA/EDA010/contexts/` に保存しています。

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA010: whole document context validation.")
    parser.add_argument("--char-limit", type=int, default=DEFAULT_CHAR_LIMIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()
    result = evaluate(args)
    summary = make_summary(result)
    save_csv(result, TABLE_DIR / "whole_document_context_eval.csv")
    save_csv(summary, TABLE_DIR / "whole_document_context_summary.csv")
    write_report(result, summary, args)
    update_eda_summary(result, summary)
    print(f"EDA010 finished: {REPORT_PATH}")
    print(f"eval: {TABLE_DIR / 'whole_document_context_eval.csv'}")


if __name__ == "__main__":
    main()
