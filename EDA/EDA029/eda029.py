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


# EDA029は、EDA028で正解以外だったvalid質問の原因データ種別と改善対象を整理する。
BASE_DIR = Path(__file__).resolve().parents[2]
EDA028_CLASSIFIED_PATH = BASE_DIR / "EDA" / "EDA028" / "tables" / "eda024_valid_answer_classification.csv"

OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda029_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

SOURCE_DIAGNOSIS_PATH = TABLE_DIR / "eda024_failure_source_diagnosis.csv"
SOURCE_TYPE_SUMMARY_PATH = TABLE_DIR / "source_type_summary.csv"
FAILURE_AREA_SUMMARY_PATH = TABLE_DIR / "failure_area_summary.csv"
NEXT_FIX_SUMMARY_PATH = TABLE_DIR / "next_fix_summary.csv"
SOURCE_BY_OUTCOME_PATH = TABLE_DIR / "source_type_by_outcome_summary.csv"


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


def infer_source_type(row: dict[str, Any]) -> str:
    """質問文とrouteから、答えるのに必要な主データ種別を推定する。"""
    question = compact_text(row.get("question", "")).lower()
    path = compact_text(row.get("top1_source_path", "")).lower()
    route = compact_text(row.get("route", ""))

    if route == "diff_check":
        return "pptx_or_docx_versions"
    if route == "code_reading":
        return "py_or_ipynb"
    if route == "image_ocr" or re.search(r"\.(png|jpg|jpeg)", question + " " + path):
        return "image"
    if "pivot" in question or "pivottable" in question:
        return "xlsx_pivot"
    if re.search(r"\.xlsx|excel|フィルター|ハイライト|色|書式", question + " " + path):
        return "xlsx"
    if re.search(r"\.csv|train\.csv|データ", question):
        return "csv"
    if re.search(r"\.ipynb|notebook|nb01", question):
        return "ipynb"
    if re.search(r"\.py|modeling\.py|コード", question):
        return "py"
    if re.search(r"\.pptx|提案書|最終報告|報告書|p[0-9]", question + " " + path):
        return "pptx"
    if re.search(r"\.docx|資料|m02|カラム説明|契約書", question + " " + path):
        return "docx"
    if ".pdf" in question + " " + path:
        return "pdf"
    if route == "table_calculation":
        return "mixed_tabular"
    return "mixed_document"


def infer_failure_area(row: dict[str, Any], source_type: str) -> str:
    """どの工程の改善が必要かを推定する。"""
    route = compact_text(row.get("route", ""))
    outcome = compact_text(row.get("broad_bucket", ""))
    diagnostic = compact_text(row.get("diagnostic_bucket", ""))
    answer_in_context = str(row.get("answer_in_topk_context", "0")) == "1"

    if outcome == "near_correct":
        return "answer_formatting"
    if route == "table_calculation":
        return "calculation"
    if route == "format_extraction":
        return "format_metadata_extraction"
    if route == "diff_check":
        return "diff_pipeline"
    if route == "code_reading":
        return "code_retrieval_or_output_extraction"
    if route == "image_ocr":
        return "image_value_extraction"
    if diagnostic == "unknown_answer" and not answer_in_context:
        return "target_retrieval"
    if answer_in_context:
        return "answer_extraction"
    if source_type in {"xlsx", "xlsx_pivot", "csv", "mixed_tabular"}:
        return "tabular_source_selection"
    return "target_retrieval"


def infer_next_fix(row: dict[str, Any], source_type: str, failure_area: str) -> str:
    """原因分類から次に実装すべき修正を返す。"""
    if failure_area == "answer_formatting":
        return "normalize_final_answer"
    if failure_area == "calculation":
        if source_type == "xlsx_pivot":
            return "read_xlsx_pivot_or_recompute_from_sheet"
        if source_type == "csv":
            return "implement_pandas_csv_calculation"
        return "implement_tabular_calculation_router"
    if failure_area == "format_metadata_extraction":
        return "query_structure_json_format_runs"
    if failure_area == "diff_pipeline":
        return "compare_old_new_documents"
    if failure_area == "code_retrieval_or_output_extraction":
        return "target_py_ipynb_by_filename_then_extract"
    if failure_area == "image_value_extraction":
        return "extract_image_values_or_use_source_data"
    if failure_area == "answer_extraction":
        return "tighten_answer_extraction_prompt"
    if failure_area == "target_retrieval":
        return "improve_project_document_targeting"
    if failure_area == "tabular_source_selection":
        return "improve_tabular_file_targeting"
    return "inspect_case_manually"


def diagnose_reason(row: dict[str, Any], source_type: str, failure_area: str) -> str:
    """人間が読みやすい短い理由を作る。"""
    outcome = row.get("broad_bucket", "")
    route = row.get("route", "")
    top1 = row.get("top1_source_path", "")
    if outcome == "near_correct":
        return "回答は近いが、単位、表記、余計な語、または一部不足を整える必要がある。"
    if route == "table_calculation":
        return f"表データの対象特定または計算処理が必要。現在のTop1根拠は {top1}"
    if route == "format_extraction":
        return "マーカー、ハイライト、色などの書式情報をstructure JSONから直接読む必要がある。"
    if route == "diff_check":
        return "old/new文書の比較ロジックが未実装で、検索根拠だけでは差分を確定できない。"
    if route == "code_reading":
        return f"対象コード/Notebookの特定が弱い。現在のTop1根拠は {top1}"
    if failure_area == "target_retrieval":
        return f"対象文書の検索がずれている可能性が高い。現在のTop1根拠は {top1}"
    return "回答抽出または対象資料の特定を改善する必要がある。"


def load_diagnosis_rows() -> list[dict[str, Any]]:
    """EDA028分類表から、正解以外の質問を原因データ種別つきで整理する。"""
    df = pd.read_csv(EDA028_CLASSIFIED_PATH)
    rows: list[dict[str, Any]] = []
    for _, raw_row in df.sort_values("index").iterrows():
        row = {key: raw_row.get(key, "") for key in df.columns}
        if row.get("broad_bucket") == "correct":
            continue
        source_type = infer_source_type(row)
        failure_area = infer_failure_area(row, source_type)
        next_fix = infer_next_fix(row, source_type, failure_area)
        rows.append(
            {
                "index": int(row.get("index", 0)),
                "route": row.get("route", ""),
                "outcome": row.get("broad_bucket", ""),
                "diagnostic_bucket": row.get("diagnostic_bucket", ""),
                "required_source_type": source_type,
                "failure_area": failure_area,
                "next_fix": next_fix,
                "question": row.get("question", ""),
                "gold_answer": row.get("gold_answer", ""),
                "llm_answer": row.get("llm_answer", ""),
                "top1_record_type": row.get("top1_record_type", ""),
                "top1_source_path": row.get("top1_source_path", ""),
                "diagnosis_reason": diagnose_reason(row, source_type, failure_area),
            }
        )
    return rows


def summarize_counts(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """指定列の件数を集計する。"""
    counts = Counter(row[key] for row in rows)
    return [{key: name, "count": count} for name, count in counts.most_common()]


def summarize_pair(rows: list[dict[str, Any]], key1: str, key2: str) -> list[dict[str, Any]]:
    """2列の組み合わせ件数を集計する。"""
    counts = Counter((row[key1], row[key2]) for row in rows)
    return [{key1: left, key2: right, "count": count} for (left, right), count in counts.most_common()]


def write_report(
    rows: list[dict[str, Any]],
    source_summary: list[dict[str, Any]],
    failure_summary: list[dict[str, Any]],
    next_fix_summary: list[dict[str, Any]],
    source_by_outcome: list[dict[str, Any]],
) -> None:
    """EDA029のレポートを保存する。"""
    status_rows = [
        {"metric": "diagnosis_target_count", "value": len(rows)},
        {"metric": "unknown_count", "value": sum(1 for row in rows if row["outcome"] == "unknown")},
        {"metric": "wrong_count", "value": sum(1 for row in rows if row["outcome"] == "wrong")},
        {"metric": "near_correct_count", "value": sum(1 for row in rows if row["outcome"] == "near_correct")},
    ]
    detail_rows = [
        {
            "index": row["index"],
            "route": row["route"],
            "outcome": row["outcome"],
            "required_source_type": row["required_source_type"],
            "failure_area": row["failure_area"],
            "next_fix": row["next_fix"],
            "gold_answer": row["gold_answer"],
            "llm_answer": row["llm_answer"],
        }
        for row in rows
    ]
    lines = [
        "# EDA029: 不明・誤答・近似正解の原因データ種別診断",
        "",
        "## 目的",
        "",
        "EDA028で `correct` ではなかったvalid質問を対象に、必要な元データ種別、失敗領域、次に直すべき処理を分類する。これにより、CSVだけを見直すべきか、Excel、PowerPoint、Word、コード、画像、差分処理を見直すべきかを判断する。",
        "",
        "## 入力",
        "",
        f"- EDA028分類表: `{relative(EDA028_CLASSIFIED_PATH)}`",
        "",
        "## 出力",
        "",
        f"- 質問別原因診断: `{relative(SOURCE_DIAGNOSIS_PATH)}`",
        f"- データ種別別集計: `{relative(SOURCE_TYPE_SUMMARY_PATH)}`",
        f"- 失敗領域別集計: `{relative(FAILURE_AREA_SUMMARY_PATH)}`",
        f"- 次修正別集計: `{relative(NEXT_FIX_SUMMARY_PATH)}`",
        f"- outcome別データ種別集計: `{relative(SOURCE_BY_OUTCOME_PATH)}`",
        "",
        "## 全体指標",
        "",
        "凡例: `metric` は診断指標、`value` は値を表します。",
        "",
        markdown_table(status_rows),
        "",
        "## 必要データ種別別集計",
        "",
        "凡例: `required_source_type` は回答に必要な主なデータ種別、`count` は件数を表します。",
        "",
        markdown_table(source_summary),
        "",
        "## 失敗領域別集計",
        "",
        "凡例: `failure_area` は改善が必要な処理領域、`count` は件数を表します。",
        "",
        markdown_table(failure_summary),
        "",
        "## 次修正別集計",
        "",
        "凡例: `next_fix` は次に実装・改善すべき処理、`count` は件数を表します。",
        "",
        markdown_table(next_fix_summary),
        "",
        "## outcome別データ種別",
        "",
        "凡例: `outcome` はEDA028の分類、`required_source_type` は必要データ種別、`count` は件数を表します。",
        "",
        markdown_table(source_by_outcome),
        "",
        "## 質問別原因診断",
        "",
        "凡例: `index` はvalid質問番号、`route` は質問系統、`outcome` はEDA028分類、`required_source_type` は必要データ種別、`failure_area` は失敗領域、`next_fix` は次修正、`gold_answer` は正解、`llm_answer` はEDA024回答を表します。",
        "",
        markdown_table(detail_rows, max_rows=30),
        "",
        "## 結論",
        "",
        "- 正解以外25件のうち、表データ系の改善対象が最も多い。",
        "- `table_calculation` はCSV、Excel、PivotTable、複数文書横断集計が混在しており、単にCSV抽出だけを直せばよい状態ではない。",
        "- 書式抽出はPowerPoint、Excel、Word/docxのstructure JSONを直接読む処理が必要である。",
        "- 差分比較とコード読解は、検索根拠の増量ではなく、old/new比較やファイル名指定検索を実装する必要がある。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, Any]]) -> None:
    """再現用の実行条件を保存する。"""
    manifest = {
        "eda": "EDA029",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Diagnose source type and failure area for non-correct EDA024 valid answers.",
        "inputs": {
            "eda028_classified": relative(EDA028_CLASSIFIED_PATH),
        },
        "outputs": {
            "source_diagnosis": relative(SOURCE_DIAGNOSIS_PATH),
            "source_type_summary": relative(SOURCE_TYPE_SUMMARY_PATH),
            "failure_area_summary": relative(FAILURE_AREA_SUMMARY_PATH),
            "next_fix_summary": relative(NEXT_FIX_SUMMARY_PATH),
            "report": relative(REPORT_PATH),
        },
        "diagnosis_target_count": len(rows),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """EDA029を実行する。"""
    setup()
    rows = load_diagnosis_rows()
    source_summary = summarize_counts(rows, "required_source_type")
    failure_summary = summarize_counts(rows, "failure_area")
    next_fix_summary = summarize_counts(rows, "next_fix")
    source_by_outcome = summarize_pair(rows, "outcome", "required_source_type")

    save_csv(rows, SOURCE_DIAGNOSIS_PATH)
    save_csv(source_summary, SOURCE_TYPE_SUMMARY_PATH)
    save_csv(failure_summary, FAILURE_AREA_SUMMARY_PATH)
    save_csv(next_fix_summary, NEXT_FIX_SUMMARY_PATH)
    save_csv(source_by_outcome, SOURCE_BY_OUTCOME_PATH)
    write_report(rows, source_summary, failure_summary, next_fix_summary, source_by_outcome)
    write_manifest(rows)

    print(
        " ".join(
            [
                f"targets={len(rows)}",
                f"top_source={source_summary[0]['required_source_type'] if source_summary else ''}",
                f"top_failure={failure_summary[0]['failure_area'] if failure_summary else ''}",
                f"report={relative(REPORT_PATH)}",
            ]
        )
    )


if __name__ == "__main__":
    main()
