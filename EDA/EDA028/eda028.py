from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# EDA028は、EDA024のvalid LLM結果を質問系統ごとに失敗分析する。
BASE_DIR = Path(__file__).resolve().parents[2]
EDA024_LOG_PATH = BASE_DIR / "EDA" / "EDA024" / "tables" / "valid_llm_answer_log.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda028_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

CLASSIFIED_PATH = TABLE_DIR / "eda024_valid_answer_classification.csv"
ROUTE_SUMMARY_PATH = TABLE_DIR / "eda024_route_classification_summary.csv"
BUCKET_SUMMARY_PATH = TABLE_DIR / "eda024_bucket_summary.csv"
ACTION_SUMMARY_PATH = TABLE_DIR / "eda024_next_action_summary.csv"


def setup() -> None:
    """出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def compact_text(value: Any) -> str:
    """CSVやMarkdownで読みやすいように空白を整える。"""
    text = unicodedata.normalize("NFC", "" if value is None else str(value))
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_match(value: Any) -> str:
    """不明回答の判定用に表記揺れを軽く吸収する。"""
    text = unicodedata.normalize("NFKC", compact_text(value)).lower()
    text = re.sub(r"<[^>]+>", " ", text)
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


def markdown_table(rows: list[dict[str, Any]], max_rows: int = 40) -> str:
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
    """Excelでも開きやすいUTF-8 BOM付きCSVを保存する。"""
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns = list(dict.fromkeys(col for row in rows for col in row.keys()))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def to_int(value: Any) -> int:
    """CSV由来の0/1値を安全にintへ変換する。"""
    try:
        return int(float(str(value)))
    except Exception:
        return 0


def to_float(value: Any) -> float:
    """CSV由来の小数値を安全にfloatへ変換する。"""
    try:
        return float(str(value))
    except Exception:
        return 0.0


def is_unknown_answer(answer: str) -> bool:
    """LLMが不明として返した回答を判定する。"""
    text = normalize_for_match(answer)
    if not text:
        return True
    unknown_terms = {
        "わかりません",
        "分かりません",
        "不明",
        "不明です",
        "根拠不足",
        "判断できません",
        "該当なし",
        "確認できません",
    }
    return text in {normalize_for_match(term) for term in unknown_terms}


def classify_answer(row: dict[str, Any]) -> dict[str, str]:
    """EDA024の1行を、正解・不明・誤答と改善方針に分類する。"""
    exact = to_int(row.get("exact_match"))
    contains_gold = to_int(row.get("contains_gold"))
    contained_by_gold = to_int(row.get("contained_by_gold"))
    answer_in_context = to_int(row.get("answer_in_topk_context"))
    token_recall = to_float(row.get("token_recall"))
    answer = compact_text(row.get("llm_answer", ""))
    route = str(row.get("route", ""))

    if exact:
        broad_bucket = "correct"
        diagnostic_bucket = "correct_exact"
        next_action = "keep"
    elif is_unknown_answer(answer):
        broad_bucket = "unknown"
        diagnostic_bucket = "unknown_answer"
        next_action = next_action_for_route(route, answer_in_context, is_unknown=True)
    else:
        if contains_gold or contained_by_gold:
            broad_bucket = "near_correct"
            diagnostic_bucket = "partial_or_over_answer"
            next_action = "tighten_final_answer_format"
        elif is_numeric_or_currency_near(row):
            broad_bucket = "near_correct"
            diagnostic_bucket = "format_normalization_needed"
            next_action = "normalize_units_and_symbols"
        elif answer_in_context:
            broad_bucket = "wrong"
            diagnostic_bucket = "answer_extraction_error"
            next_action = "improve_prompt_or_extractor"
        elif token_recall > 0:
            broad_bucket = "wrong"
            diagnostic_bucket = "weak_overlap_wrong"
            next_action = next_action_for_route(route, answer_in_context, is_unknown=False)
        else:
            broad_bucket = "wrong"
            diagnostic_bucket = "wrong_evidence_or_missing_process"
            next_action = next_action_for_route(route, answer_in_context, is_unknown=False)

    return {
        "broad_bucket": broad_bucket,
        "diagnostic_bucket": diagnostic_bucket,
        "next_action": next_action,
    }


def next_action_for_route(route: str, answer_in_context: int, is_unknown: bool) -> str:
    """質問系統ごとの次の改善方向を返す。"""
    if route == "table_calculation":
        return "implement_local_table_calculation"
    if route == "format_extraction":
        return "use_format_metadata_json"
    if route == "diff_check":
        return "build_document_diff_pipeline"
    if route == "code_reading":
        return "improve_code_notebook_retrieval"
    if route == "image_ocr":
        return "improve_image_or_source_data_extraction"
    if route == "document_whole_context":
        return "tighten_document_selection" if not answer_in_context else "tighten_final_answer_format"
    if is_unknown:
        return "improve_retrieval_context"
    return "improve_retrieval_or_route"


def only_digits(value: Any) -> str:
    """金額記号や単位を落として数字だけを取り出す。"""
    return re.sub(r"\D", "", unicodedata.normalize("NFKC", compact_text(value)))


def is_numeric_or_currency_near(row: dict[str, Any]) -> bool:
    """円記号、カンマ、単位違いだけなら近似正解として扱う。"""
    gold_digits = only_digits(row.get("gold_answer", ""))
    answer_digits = only_digits(row.get("llm_answer", ""))
    if not gold_digits or not answer_digits:
        return False
    return gold_digits == answer_digits


def load_and_classify() -> list[dict[str, Any]]:
    """EDA024のvalidログを読み、分類列を追加する。"""
    df = pd.read_csv(EDA024_LOG_PATH)
    rows: list[dict[str, Any]] = []
    for _, row in df.sort_values("index").iterrows():
        record = {key: row.get(key, "") for key in df.columns}
        classification = classify_answer(record)
        rows.append(
            {
                "index": int(record.get("index", 0)),
                "route": record.get("route", ""),
                "broad_bucket": classification["broad_bucket"],
                "diagnostic_bucket": classification["diagnostic_bucket"],
                "next_action": classification["next_action"],
                "question": record.get("question", ""),
                "gold_answer": record.get("gold_answer", ""),
                "llm_answer": record.get("llm_answer", ""),
                "exact_match": to_int(record.get("exact_match")),
                "contains_gold": to_int(record.get("contains_gold")),
                "contained_by_gold": to_int(record.get("contained_by_gold")),
                "answer_in_topk_context": to_int(record.get("answer_in_topk_context")),
                "token_recall": round(to_float(record.get("token_recall")), 4),
                "top1_record_type": record.get("top1_record_type", ""),
                "top1_source_path": record.get("top1_source_path", ""),
                "error_message": compact_text(record.get("error_message", ""))[:300],
            }
        )
    return rows


def summarize_by_route(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """質問系統ごとに正解・不明・誤答を集計する。"""
    summary_rows: list[dict[str, Any]] = []
    for route in sorted({row["route"] for row in rows}):
        items = [row for row in rows if row["route"] == route]
        bucket_counts = Counter(row["broad_bucket"] for row in items)
        diagnostic_counts = Counter(row["diagnostic_bucket"] for row in items)
        summary_rows.append(
            {
                "route": route,
                "question_count": len(items),
                "correct_count": bucket_counts.get("correct", 0),
                "near_correct_count": bucket_counts.get("near_correct", 0),
                "unknown_count": bucket_counts.get("unknown", 0),
                "wrong_count": bucket_counts.get("wrong", 0),
                "partial_or_over_answer_count": diagnostic_counts.get("partial_or_over_answer", 0),
                "answer_extraction_error_count": diagnostic_counts.get("answer_extraction_error", 0),
                "wrong_evidence_or_missing_process_count": diagnostic_counts.get("wrong_evidence_or_missing_process", 0),
                "answer_in_topk_context_count": sum(int(row["answer_in_topk_context"]) for row in items),
                "avg_token_recall": round(sum(float(row["token_recall"]) for row in items) / max(len(items), 1), 4),
            }
        )
    return summary_rows


def summarize_counts(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """指定列の件数を集計する。"""
    counts = Counter(row[key] for row in rows)
    return [{key: name, "count": count} for name, count in counts.most_common()]


def write_report(
    rows: list[dict[str, Any]],
    route_summary: list[dict[str, Any]],
    bucket_summary: list[dict[str, Any]],
    action_summary: list[dict[str, Any]],
) -> None:
    """EDA028の診断レポートを保存する。"""
    correct_count = sum(1 for row in rows if row["broad_bucket"] == "correct")
    near_correct_count = sum(1 for row in rows if row["broad_bucket"] == "near_correct")
    unknown_count = sum(1 for row in rows if row["broad_bucket"] == "unknown")
    wrong_count = sum(1 for row in rows if row["broad_bucket"] == "wrong")
    partial_count = sum(1 for row in rows if row["diagnostic_bucket"] == "partial_or_over_answer")
    status_rows = [
        {"metric": "valid_question_count", "value": len(rows)},
        {"metric": "correct_count", "value": correct_count},
        {"metric": "near_correct_count", "value": near_correct_count},
        {"metric": "correct_or_near_correct_count", "value": correct_count + near_correct_count},
        {"metric": "unknown_count", "value": unknown_count},
        {"metric": "wrong_count", "value": wrong_count},
        {"metric": "partial_or_over_answer_count", "value": partial_count},
        {"metric": "answer_in_topk_context_count", "value": sum(int(row["answer_in_topk_context"]) for row in rows)},
    ]
    question_rows = [
        {
            "index": row["index"],
            "route": row["route"],
            "broad_bucket": row["broad_bucket"],
            "diagnostic_bucket": row["diagnostic_bucket"],
            "next_action": row["next_action"],
            "gold_answer": row["gold_answer"],
            "llm_answer": row["llm_answer"],
        }
        for row in rows
    ]
    lines = [
        "# EDA028: EDA024 valid回答の質問系統別分類",
        "",
        "## 目的",
        "",
        "EDA024のvalid 30問について、正解したもの、`わかりません` になったもの、間違ったものを質問系統ごとに分類する。valid正解は分類評価にのみ使い、回答生成には使わない。",
        "",
        "## 入力",
        "",
        f"- EDA024回答ログ: `{relative(EDA024_LOG_PATH)}`",
        "",
        "## 出力",
        "",
        f"- 質問別分類: `{relative(CLASSIFIED_PATH)}`",
        f"- route別集計: `{relative(ROUTE_SUMMARY_PATH)}`",
        f"- bucket別集計: `{relative(BUCKET_SUMMARY_PATH)}`",
        f"- next_action別集計: `{relative(ACTION_SUMMARY_PATH)}`",
        "",
        "## 全体指標",
        "",
        "凡例: `metric` は診断指標、`value` は値を表します。",
        "",
        markdown_table(status_rows),
        "",
        "## route別分類",
        "",
        "凡例: `route` は質問系統、`question_count` はvalid質問数、`correct_count` は完全一致数、`near_correct_count` は表記・単位・過不足はあるが近い回答数、`unknown_count` は不明回答数、`wrong_count` は近似正解でも不明でもない回答数を表します。",
        "",
        markdown_table(route_summary),
        "",
        "## 診断bucket別件数",
        "",
        "凡例: `diagnostic_bucket` は回答失敗の診断分類、`count` は件数を表します。",
        "",
        markdown_table(bucket_summary),
        "",
        "## 次アクション別件数",
        "",
        "凡例: `next_action` は次に優先する改善作業、`count` は該当質問数を表します。",
        "",
        markdown_table(action_summary),
        "",
        "## 質問別分類",
        "",
        "凡例: `index` はvalid質問番号、`route` は質問系統、`broad_bucket` は `correct`、`near_correct`、`unknown`、`wrong` の大分類、`diagnostic_bucket` は詳細分類、`next_action` は改善方針、`gold_answer` は正解、`llm_answer` はEDA024のLLM回答を表します。",
        "",
        markdown_table(question_rows, max_rows=30),
        "",
        "## 結論",
        "",
        f"- EDA024の完全一致は{correct_count}件、近似正解は{near_correct_count}件、不明回答は{unknown_count}件、明確な誤答は{wrong_count}件だった。",
        f"- 完全一致と近似正解を合わせると{correct_count + near_correct_count}件で、完全一致だけを見るよりEDA024の有効性は少し高い。",
        f"- 近似正解{near_correct_count}件のうち{partial_count}件は、正解語句を含むが余計な語がある、または単位などが不足した回答だった。",
        "- `document_whole_context` と `fallback_bm25_llm` は完全一致が出ており、文書選択と回答形式を整える余地がある。",
        "- `table_calculation`、`format_extraction`、`diff_check`、`code_reading` は完全一致がなく、LLMへ投げる前のroute別処理が必要である。",
        "- 次に優先するのは、`table_calculation` のローカル計算、`format_extraction` の書式JSON利用、`diff_check` の文書差分処理である。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA028",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Classify EDA024 valid answers by route and outcome bucket.",
        "inputs": {
            "eda024_answer_log": relative(EDA024_LOG_PATH),
        },
        "outputs": {
            "classified": relative(CLASSIFIED_PATH),
            "route_summary": relative(ROUTE_SUMMARY_PATH),
            "bucket_summary": relative(BUCKET_SUMMARY_PATH),
            "action_summary": relative(ACTION_SUMMARY_PATH),
            "report": relative(REPORT_PATH),
        },
        "valid_question_count": len(rows),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """EDA028を実行する。"""
    setup()
    rows = load_and_classify()
    route_summary = summarize_by_route(rows)
    bucket_summary = summarize_counts(rows, "diagnostic_bucket")
    action_summary = summarize_counts(rows, "next_action")

    save_csv(rows, CLASSIFIED_PATH)
    save_csv(route_summary, ROUTE_SUMMARY_PATH)
    save_csv(bucket_summary, BUCKET_SUMMARY_PATH)
    save_csv(action_summary, ACTION_SUMMARY_PATH)
    write_report(rows, route_summary, bucket_summary, action_summary)
    write_manifest(rows)

    print(
        " ".join(
            [
                f"valid={len(rows)}",
                f"correct={sum(1 for row in rows if row['broad_bucket'] == 'correct')}",
                f"near_correct={sum(1 for row in rows if row['broad_bucket'] == 'near_correct')}",
                f"unknown={sum(1 for row in rows if row['broad_bucket'] == 'unknown')}",
                f"wrong={sum(1 for row in rows if row['broad_bucket'] == 'wrong')}",
                f"report={relative(REPORT_PATH)}",
            ]
        )
    )


if __name__ == "__main__":
    main()
