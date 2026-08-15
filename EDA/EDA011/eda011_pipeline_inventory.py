from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
EDA_DIR = BASE_DIR / "EDA"
OUTPUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_DIR = OUTPUT_DIR / "reports"
RAW_DIR = BASE_DIR / "data" / "raw"
SHARE_DIR = RAW_DIR / "share" / "share" / "共有ドライブ"
QUESTION_DIR = RAW_DIR / "share" / "share" / "質問回答"

EDA002_DOCS = EDA_DIR / "EDA002" / "texts" / "extracted_documents.jsonl"
EDA004_DOCS = EDA_DIR / "EDA004" / "texts" / "extracted_documents.jsonl"
EDA004_CHUNKS = EDA_DIR / "EDA004" / "texts" / "text_chunks.jsonl"
EDA004_SHEETS = EDA_DIR / "EDA004" / "tables" / "sheet_summary.csv"
EDA009_COMPARE = EDA_DIR / "EDA009" / "tables" / "valid_guided_retrieval_comparison.csv"
EDA010_EVAL = EDA_DIR / "EDA010" / "tables" / "whole_document_context_eval.csv"
EDA_SUMMARY = EDA_DIR / "eda_summary.md"


def ensure_dir(path: Path) -> None:
    """EDAごとの出力フォルダを作る。"""
    (path / "tables").mkdir(parents=True, exist_ok=True)


def setup() -> None:
    """統合EDAの出力フォルダを準備する。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def table_path(name: str) -> Path:
    """統合EDA配下のCSV出力先を返す。"""
    return TABLE_DIR / name


def report_path(name: str) -> Path:
    """統合EDA配下のMarkdown出力先を返す。"""
    return REPORT_DIR / name


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """Excelで開きやすいUTF-8 BOM付きCSVで保存する。"""
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """JSONLを読み込む。"""
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def norm(text: Any) -> str:
    """検索用に表記揺れを軽くならす。"""
    return unicodedata.normalize("NFKC", str(text)).lower().replace("\u3000", " ")


def compact(text: Any) -> str:
    """正解照合用に空白と一部記号を落とす。"""
    text = norm(text).replace(",", "").replace("，", "")
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[\"'`『』「」\[\]（）(){}]", "", text)


def md_table(df: pd.DataFrame, max_rows: int = 12) -> str:
    """依存を増やさずMarkdown表を作る。"""
    if df.empty:
        return "該当データはありません。"
    view = df.head(max_rows)
    cols = list(view.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in view.iterrows():
        values = []
        for col in cols:
            value = "" if pd.isna(row[col]) else str(row[col])
            values.append(value.replace("\n", " ").replace("\r", " ").replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(path: Path, title: str, body: str) -> None:
    """Markdownレポートを書き出す。"""
    path.write_text(f"# {title}\n\n{body}".rstrip() + "\n", encoding="utf-8")


def load_questions() -> tuple[pd.DataFrame, pd.DataFrame]:
    """valid/test質問を読み込む。"""
    valid = pd.read_csv(QUESTION_DIR / "questions_valid.csv")
    test = pd.read_csv(QUESTION_DIR / "questions_test.csv")
    return valid, test


def load_docs() -> pd.DataFrame:
    """文書単位抽出結果をDataFrame化する。"""
    rows = []
    for source, path in [("EDA002", EDA002_DOCS), ("EDA004", EDA004_DOCS)]:
        for rec in read_jsonl(path):
            rows.append(
                {
                    "source_eda": source,
                    "relative_path": rec.get("relative_path", ""),
                    "file_name": rec.get("file_name", ""),
                    "extension": rec.get("extension", ""),
                    "project_name": rec.get("project_name", ""),
                    "major_folder": rec.get("major_folder", ""),
                    "text": rec.get("text", ""),
                    "text_chars": len(str(rec.get("text", ""))),
                    "table_count": rec.get("table_count", 0),
                    "slide_count": rec.get("slide_count", 0),
                    "sheet_count": rec.get("sheet_count", 0),
                    "page_count": rec.get("page_count", 0),
                    "highlight_count": rec.get("highlight_count", 0),
                    "styled_run_count": rec.get("styled_run_count", 0),
                }
            )
    return pd.DataFrame(rows)


def question_route(question: str) -> str:
    """質問文から最初に使うべき処理ルートを推定する。"""
    q = norm(question)
    if any(k in q for k in ["画像", "グラフ", "figure", ".png", ".jpg"]):
        return "image_ocr"
    if any(k in q for k in ["太字", "赤字", "下線", "マーカー", "ハイライト", "色", "セル色"]):
        return "format_extraction"
    if any(k in q for k in ["比較", "差分", "旧版", "最新版", "変更"]):
        return "diff_check"
    if any(k in q for k in ["平均", "合計", "件数", "最大", "最小", "税額", "差額", "pivot", "フィルター", "xlsx", "csv"]):
        return "table_calculation"
    if any(k in q for k in ["提案書", "報告書", "報告資料", "会議録", "契約書", "カラム説明"]):
        return "document_whole_context"
    if any(k in q for k in [".py", "コード", "notebook", "ipynb"]):
        return "code_reading"
    return "fallback_bm25_llm"


def run_whole_doc_llm_candidates() -> dict[str, Any]:
    """文書全体コンテキストをLLMへ渡す候補を整理する。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    eval_df = pd.read_csv(EDA010_EVAL)
    targets = eval_df[eval_df["answer_hit_context"] == True].copy()  # noqa: E712
    targets["recommended_model"] = "openai/gpt-oss-20b:free"
    targets["reasoning_enabled"] = True
    save_csv(targets, table_path("whole_doc_llm_candidates.csv"))
    body = (
        "EDA010で文書全体コンテキスト内にvalid正解語句が含まれた質問を、LLM回答検証の候補として整理しました。\n\n"
        f"- 候補件数: {len(targets)}\n"
        "- 推奨モデル: `openai/gpt-oss-20b:free`\n"
        "- 今回は外部API呼び出しは行わず、候補整理に留めています。\n\n"
        "## 候補一覧\n\n"
        + md_table(targets[["index", "answer", "target_document_path", "context_chars", "context_path"]])
        + "\n\n凡例: `index` はvalid質問番号、`answer` はvalid正解、`target_document_path` は対象文書、`context_chars` はLLM入力文字数、`context_path` は生成済みMarkdownを表します。"
    )
    write_report(report_path("whole_doc_llm_candidates_report.md"), "EDA011: 文書全体LLM候補整理", body)
    return {"task": "whole_doc_llm_candidates", "candidate_count": len(targets)}


def run_table_question_inventory(valid: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """表計算が必要そうな質問を棚卸しする。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    rows = []
    for split, df in [("valid", valid), ("test", test)]:
        for _, row in df.iterrows():
            route = question_route(row["question"])
            if route == "table_calculation":
                rows.append({"split": split, "index": row["index"], "question": row["question"], "answer": row.get("answer", ""), "route": route})
    table_questions = pd.DataFrame(rows)
    save_csv(table_questions, table_path("table_question_inventory.csv"))
    body = (
        "平均、合計、件数、最大、最小、PivotTable、フィルター、CSV/XLSXなど、表を直接処理すべき質問をvalid/testから抽出しました。\n\n"
        + md_table(table_questions.groupby("split").size().reset_index(name="question_count"))
        + "\n\n凡例: `split` はvalid/test、`question_count` は表処理候補の質問数を表します。\n\n"
        "## サンプル\n\n"
        + md_table(table_questions[["split", "index", "question"]])
        + "\n\n凡例: `index` は質問番号、`question` は質問文を表します。"
    )
    write_report(report_path("table_question_inventory_report.md"), "EDA011: 表計算質問の棚卸し", body)
    return {"task": "table_question_inventory", "table_questions": len(table_questions)}


def run_tabular_document_inventory(docs: pd.DataFrame) -> dict[str, Any]:
    """CSV/XLSX文書の処理可能性を棚卸しする。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    tabular = docs[docs["extension"].isin([".csv", ".xlsx", ".xlsm"])].copy()
    if EDA004_SHEETS.exists():
        sheets = pd.read_csv(EDA004_SHEETS)
    else:
        sheets = pd.DataFrame()
    save_csv(tabular.drop(columns=["text"], errors="ignore"), table_path("tabular_document_inventory.csv"))
    save_csv(sheets, table_path("xlsx_sheet_inventory.csv"))
    body = (
        "CSV/XLSXをRAGチャンクではなく、pandas/openpyxlで直接処理するための棚卸しを行いました。\n\n"
        f"- CSV/XLSX系文書数: {len(tabular)}\n"
        f"- EDA004 sheet_summary 行数: {len(sheets)}\n\n"
        "## 拡張子別\n\n"
        + md_table(tabular.groupby("extension").size().reset_index(name="file_count"))
        + "\n\n凡例: `extension` は拡張子、`file_count` は文書数を表します。"
    )
    write_report(report_path("tabular_document_inventory_report.md"), "EDA011: 表データ直接処理の準備", body)
    return {"task": "tabular_document_inventory", "tabular_docs": len(tabular)}


def run_format_inventory(docs: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """書式情報が必要な質問と抽出済み書式メタデータを照合する。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    format_docs = docs[(docs["highlight_count"].fillna(0).astype(float) > 0) | (docs["styled_run_count"].fillna(0).astype(float) > 0)].copy()
    q_rows = []
    for split, df in [("valid", valid), ("test", test)]:
        for _, row in df.iterrows():
            if question_route(row["question"]) == "format_extraction":
                q_rows.append({"split": split, "index": row["index"], "question": row["question"], "answer": row.get("answer", "")})
    format_questions = pd.DataFrame(q_rows)
    save_csv(format_docs.drop(columns=["text"], errors="ignore"), table_path("format_document_inventory.csv"))
    save_csv(format_questions, table_path("format_question_inventory.csv"))
    body = (
        "色、太字、下線、ハイライトなど、書式情報が必要な質問と、抽出済み書式メタデータを持つ文書を棚卸ししました。\n\n"
        f"- 書式質問候補: {len(format_questions)}\n"
        f"- 書式メタデータあり文書: {len(format_docs)}\n\n"
        "## 書式質問サンプル\n\n"
        + md_table(format_questions[["split", "index", "question"]])
        + "\n\n凡例: `split` はvalid/test、`index` は質問番号、`question` は質問文を表します。"
    )
    write_report(report_path("format_inventory_report.md"), "EDA011: 書式情報質問の棚卸し", body)
    return {"task": "format_inventory", "format_questions": len(format_questions), "format_docs": len(format_docs)}


def run_image_inventory(valid: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """画像・グラフ質問と画像ファイルを棚卸しする。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    images = []
    for path in SHARE_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            images.append({"relative_path": path.relative_to(SHARE_DIR).as_posix(), "file_name": path.name, "extension": path.suffix.lower(), "size_bytes": path.stat().st_size})
    image_df = pd.DataFrame(images)
    q_rows = []
    for split, df in [("valid", valid), ("test", test)]:
        for _, row in df.iterrows():
            if question_route(row["question"]) == "image_ocr":
                q_rows.append({"split": split, "index": row["index"], "question": row["question"], "answer": row.get("answer", "")})
    image_questions = pd.DataFrame(q_rows)
    save_csv(image_df, table_path("image_file_inventory.csv"))
    save_csv(image_questions, table_path("image_question_inventory.csv"))
    body = (
        "画像・グラフを読む必要がありそうな質問と画像ファイルを棚卸ししました。ここで対象画像を絞ってから、必要に応じてOCRまたは画像理解モデルへ渡します。\n\n"
        f"- 画像ファイル数: {len(image_df)}\n"
        f"- 画像質問候補: {len(image_questions)}\n\n"
        "## 画像質問サンプル\n\n"
        + md_table(image_questions[["split", "index", "question"]])
        + "\n\n凡例: `split` はvalid/test、`index` は質問番号、`question` は質問文を表します。"
    )
    write_report(report_path("image_inventory_report.md"), "EDA011: 画像・グラフ質問の棚卸し", body)
    return {"task": "image_inventory", "image_files": len(image_df), "image_questions": len(image_questions)}


def run_diff_inventory(docs: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """差分・版比較が必要そうな質問と版違いファイル候補を整理する。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    q_rows = []
    for split, df in [("valid", valid), ("test", test)]:
        for _, row in df.iterrows():
            if question_route(row["question"]) == "diff_check":
                q_rows.append({"split": split, "index": row["index"], "question": row["question"], "answer": row.get("answer", "")})
    diff_questions = pd.DataFrame(q_rows)
    version_docs = docs[docs["file_name"].astype(str).str.contains(r"v\d|final|old|new|旧|新版|最新版|差分", case=False, regex=True)].copy()
    save_csv(diff_questions, table_path("diff_question_inventory.csv"))
    save_csv(version_docs.drop(columns=["text"], errors="ignore"), table_path("version_document_candidates.csv"))
    body = (
        "旧版/最新版/変更/差分などの比較が必要な質問と、版違いの可能性がある文書名を整理しました。\n\n"
        f"- 差分質問候補: {len(diff_questions)}\n"
        f"- 版違い文書候補: {len(version_docs)}\n\n"
        "## 版違い文書サンプル\n\n"
        + md_table(version_docs[["relative_path", "extension", "text_chars"]])
        + "\n\n凡例: `relative_path` は文書位置、`extension` は拡張子、`text_chars` は抽出本文の文字数を表します。"
    )
    write_report(report_path("diff_inventory_report.md"), "EDA011: 差分・版比較候補の整理", body)
    return {"task": "diff_inventory", "diff_questions": len(diff_questions), "version_docs": len(version_docs)}


def run_question_routes(valid: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """valid/test全問に処理ルートを付与する。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    rows = []
    for split, df in [("valid", valid), ("test", test)]:
        for _, row in df.iterrows():
            rows.append({"split": split, "index": row["index"], "question": row["question"], "answer": row.get("answer", ""), "route": question_route(row["question"])})
    routed = pd.DataFrame(rows)
    route_counts = routed.groupby(["split", "route"], as_index=False).size().rename(columns={"size": "question_count"})
    save_csv(routed, table_path("question_routes.csv"))
    save_csv(route_counts, table_path("route_counts.csv"))
    body = (
        "最終パイプラインの入口として、valid/test全問に処理ルートを付与しました。\n\n"
        + md_table(route_counts)
        + "\n\n凡例: `split` はvalid/test、`route` は推定処理ルート、`question_count` は質問数を表します。"
    )
    write_report(report_path("question_routes_report.md"), "EDA011: 質問ルーティング設計", body)
    return {"task": "question_routes", "routed_questions": len(routed)}


def run_pipeline_artifact_map() -> dict[str, Any]:
    """既存成果物を最終パイプライン用の入力候補として整理する。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    artifacts = [
        {"component": "text_chunks", "path": "EDA/EDA002/texts/text_chunks.jsonl", "role": "md/csv/json/py/ipynb BM25"},
        {"component": "office_chunks", "path": "EDA/EDA004/texts/text_chunks.jsonl", "role": "docx/pptx/xlsx/pdf BM25"},
        {"component": "whole_doc_contexts", "path": "EDA/EDA010/contexts", "role": "document_whole_context"},
        {"component": "table_inventory", "path": "EDA/EDA011/tables/tabular_document_inventory.csv", "role": "table_calculation"},
        {"component": "format_inventory", "path": "EDA/EDA011/tables/format_document_inventory.csv", "role": "format_extraction"},
        {"component": "image_inventory", "path": "EDA/EDA011/tables/image_file_inventory.csv", "role": "image_ocr"},
        {"component": "question_routes", "path": "EDA/EDA011/tables/question_routes.csv", "role": "router"},
    ]
    df = pd.DataFrame(artifacts)
    save_csv(df, table_path("pipeline_artifact_map.csv"))
    body = (
        "最終パイプラインで参照する中間成果物の対応表を作成しました。\n\n"
        + md_table(df)
        + "\n\n凡例: `component` は部品名、`path` は成果物パス、`role` はパイプライン内での役割を表します。"
    )
    write_report(report_path("pipeline_artifact_map_report.md"), "EDA011: パイプライン成果物マップ", body)
    return {"task": "pipeline_artifact_map", "artifact_count": len(df)}


def run_answer_policy(valid: pd.DataFrame) -> dict[str, Any]:
    """validで回答戦略の安全側ポリシーを設計する。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    routes = pd.read_csv(table_path("question_routes.csv"))
    valid_routes = routes[routes["split"] == "valid"].copy()
    valid_routes["answer_policy"] = valid_routes["route"].map(
        {
            "document_whole_context": "LLMで文書内根拠から短く回答",
            "table_calculation": "pandas/openpyxlで計算結果を回答",
            "format_extraction": "書式メタデータから抽出し、不明ならわかりません",
            "image_ocr": "OCR/画像理解が未実装ならわかりません",
            "diff_check": "版比較が未実装ならわかりません",
            "code_reading": "コード全文または該当関数をLLMへ渡す",
            "fallback_bm25_llm": "BM25根拠が弱い場合はわかりません",
        }
    )
    save_csv(valid_routes, table_path("valid_answer_policy.csv"))
    body = (
        "Incorrectが-1点になることを踏まえ、route別に安全側の回答方針を整理しました。\n\n"
        + md_table(valid_routes.groupby(["route", "answer_policy"], as_index=False).size().rename(columns={"size": "valid_count"}))
        + "\n\n凡例: `route` は処理ルート、`answer_policy` は回答生成方針、`valid_count` はvalid質問数を表します。"
    )
    write_report(report_path("answer_policy_report.md"), "EDA011: 回答ポリシー設計", body)
    return {"task": "answer_policy", "valid_questions": len(valid)}


def run_submission_checklist(results: list[dict[str, Any]]) -> dict[str, Any]:
    """統合棚卸しの結果を提出用再現設計にまとめる。"""
    out = OUTPUT_DIR
    ensure_dir(out)
    result_df = pd.DataFrame(results)
    save_csv(result_df, table_path("pipeline_inventory_result_index.csv"))
    checklist = pd.DataFrame(
        [
            {"step": "extract_files", "status": "done", "source": "EDA002/EDA004"},
            {"step": "query_route", "status": "prototype_done", "source": "EDA011/question_routes.csv"},
            {"step": "whole_doc_context", "status": "prototype_done", "source": "EDA010/EDA011"},
            {"step": "table_calculation", "status": "inventory_done", "source": "EDA011 table inventory"},
            {"step": "format_extraction", "status": "inventory_done", "source": "EDA011 format inventory"},
            {"step": "image_ocr", "status": "needs_model_or_ocr", "source": "EDA011 image inventory"},
            {"step": "diff_check", "status": "inventory_done", "source": "EDA011 diff inventory"},
            {"step": "submission_generation", "status": "not_started", "source": "EDA005 baseline only"},
        ]
    )
    save_csv(checklist, table_path("submission_pipeline_checklist.csv"))
    body = (
        "EDA011の統合棚卸しを、提出用コードへ落とすためのチェックリストにまとめました。\n\n"
        "## 実行結果インデックス\n\n"
        + md_table(result_df)
        + "\n\n凡例: `task` は統合EDA内のサブテーマ、それ以外の列は各サブテーマの主要件数を表します。\n\n"
        "## 提出用チェックリスト\n\n"
        + md_table(checklist)
        + "\n\n凡例: `step` は提出パイプラインの工程、`status` は現状、`source` は根拠となるEDAを表します。"
    )
    write_report(report_path("submission_pipeline_checklist_report.md"), "EDA011: 提出用パイプライン設計チェックリスト", body)
    return {"task": "submission_checklist", "checklist_count": len(checklist)}


def main() -> None:
    setup()
    valid, test = load_questions()
    docs = load_docs()
    results: list[dict[str, Any]] = []
    results.append(run_whole_doc_llm_candidates())
    results.append(run_table_question_inventory(valid, test))
    results.append(run_tabular_document_inventory(docs))
    results.append(run_format_inventory(docs, valid, test))
    results.append(run_image_inventory(valid, test))
    results.append(run_diff_inventory(docs, valid, test))
    results.append(run_question_routes(valid, test))
    results.append(run_pipeline_artifact_map())
    results.append(run_answer_policy(valid))
    results.append(run_submission_checklist(results))
    print("EDA011 integrated pipeline inventory finished")
    for result in results:
        print(result)


if __name__ == "__main__":
    main()
