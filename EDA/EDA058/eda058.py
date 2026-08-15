from __future__ import annotations

import ast
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EDA_DIR = ROOT / "EDA" / "EDA058"
TABLE_DIR = EDA_DIR / "tables"
PRED_DIR = EDA_DIR / "predictions"

BASE_PREDICTIONS = ROOT / "EDA" / "EDA057" / "predictions" / "eda057_cross_project_predictions.csv"
QUESTIONS_TEST = ROOT / "data" / "raw" / "share" / "share" / "質問回答" / "questions_test.csv"

FINAL_REPORT = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ" / "プロジェクト" / "青葉与信マネジメント株式会社" / "06.報告書" / "青葉与信マネジメント株式会社_最終報告.pptx.md"
LEADERBOARD_CSV = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ" / "プロジェクト" / "青葉与信マネジメント株式会社" / "04.分析" / "analysis_outputs" / "experiments" / "leaderboard.csv.data.csv"
LEADERBOARD_MD = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ" / "プロジェクト" / "青葉与信マネジメント株式会社" / "04.分析" / "analysis_outputs" / "experiments" / "leaderboard.csv.md"


def rel(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.relative_to(ROOT))
    except ValueError:
        return str(path_obj)


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)


def parse_paths(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []

    # CSVログにはPython list表記、JSON配列、pipe区切りが混在するため、順に安全に解釈する。
    for parser in (ast.literal_eval, json.loads):
        try:
            parsed = parser(text)
            if isinstance(parsed, list):
                return [str(v) for v in parsed if str(v).strip()]
        except Exception:
            pass
    if " | " in text:
        return [part.strip() for part in text.split(" | ") if part.strip()]
    if "\n" in text:
        return [part.strip() for part in text.splitlines() if part.strip()]
    return [text]


def unique_join(paths: list[str], limit: int = 10) -> str:
    seen: list[str] = []
    for path in paths:
        if path and path not in seen:
            seen.append(path)
    if len(seen) > limit:
        return " | ".join(seen[:limit]) + f" | ...(+{len(seen) - limit})"
    return " | ".join(seen)


def build_model_diff_answer() -> tuple[str, pd.DataFrame, dict[str, Any]]:
    leaderboard = pd.read_csv(LEADERBOARD_CSV)
    leaderboard = leaderboard.sort_values("primary_value", ascending=False).reset_index(drop=True)
    top2 = leaderboard.head(2).copy()

    # 上位2件で異なる設定項目だけを抽出し、回答は設定差分に絞る。
    config_cols = ["model_type", "n_estimators", "use_date_features", "random_state", "test_size", "task_type"]
    diffs: dict[str, list[Any]] = {}
    for col in config_cols:
        values = top2[col].tolist()
        if len(set(map(str, values))) > 1:
            diffs[col] = values

    if diffs == {"n_estimators": ["500", "300"]}:
        answer = "n_estimatorsが500と300で異なります。"
    else:
        parts = [f"{col}={values[0]}と{values[1]}" for col, values in diffs.items()]
        answer = "、".join(parts) + "が異なります。"

    evidence = {
        "top1": top2.iloc[0].to_dict(),
        "top2": top2.iloc[1].to_dict(),
        "diffs": diffs,
        "source_paths": [rel(FINAL_REPORT), rel(LEADERBOARD_CSV), rel(LEADERBOARD_MD)],
    }
    return answer, top2, evidence


def add_provenance(
    provenance: dict[int, dict[str, Any]],
    index: int,
    stage: str,
    source_paths: list[str],
    confidence: str,
    note: str,
    evidence: str = "",
    override: bool = False,
) -> None:
    if index in provenance and not override:
        return
    provenance[index] = {
        "source_stage": stage,
        "source_paths": source_paths,
        "source_confidence": confidence,
        "source_note": note,
        "evidence": evidence,
    }


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def collect_route_provenance(final_predictions: pd.DataFrame, model_diff_evidence: dict[str, Any]) -> dict[int, dict[str, Any]]:
    provenance: dict[int, dict[str, Any]] = {}

    # EDA058で今回確定した回答。
    add_provenance(
        provenance,
        62,
        "EDA058_model_diff",
        model_diff_evidence["source_paths"],
        "high",
        "最終報告のモデル比較表とleaderboard.csv上位2行の設定差分",
        json.dumps(model_diff_evidence["diffs"], ensure_ascii=False),
        override=True,
    )

    # EDA057はevidence_jsonだけなので、利用ファイルを明示的に補う。
    eda057_sources = {
        38: [
            "EDA/EDA051/tables/contract_terms_inventory.csv",
            "data/processed/share/share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md",
            "data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.md",
        ],
        46: [
            "EDA/EDA051/tables/contract_terms_inventory.csv",
            "EDA/EDA051/tables/role_assignment_inventory.csv",
            "EDA/EDA049/tables/seat_coordinate_table.csv",
        ],
        79: [
            "data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/02.計画/スケジュール.xlsx",
            "data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx.md",
            "data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/会議録/会議録_2025-09-30.docx.md",
            "data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx.md",
        ],
    }
    eda057 = load_csv(ROOT / "EDA" / "EDA057" / "tables" / "eda057_route_results.csv")
    for _, row in eda057.iterrows():
        index = int(row["index"])
        add_provenance(
            provenance,
            index,
            f"EDA057_{row['route']}",
            eda057_sources.get(index, []),
            "medium" if bool(row.get("needs_review", False)) else "high",
            "EDA057個別routeで採用",
            str(row.get("evidence_json", "")),
        )

    # 直近の個別routeログ。採用済み行だけをソース元として使う。
    route_logs = [
        ("EDA056", ROOT / "EDA" / "EDA056" / "tables" / "eda056_route_results.csv", "source_paths", "candidate_answer"),
        ("EDA055", ROOT / "EDA" / "EDA055" / "tables" / "eda055_route_results.csv", "source_paths", "candidate_answer"),
        ("EDA054", ROOT / "EDA" / "EDA054" / "tables" / "eda054_candidate_answers.csv", "source_paths", "adopted_answer"),
        ("EDA053_safe", ROOT / "EDA" / "EDA053" / "tables" / "eda053_safe_adoption_log.csv", "evidence", "candidate_answer"),
        ("EDA052", ROOT / "EDA" / "EDA052" / "tables" / "no_text_pdf_question_probe.csv", "evidence", "candidate_answer"),
        ("EDA050", ROOT / "EDA" / "EDA050" / "tables" / "meeting_action_question_probe.csv", "evidence", "candidate_answer"),
    ]
    for stage, path, source_col, answer_col in route_logs:
        df = load_csv(path)
        if df.empty or "index" not in df.columns:
            continue
        for _, row in df.iterrows():
            index = int(row["index"])
            if "adopted" in row and not bool(row["adopted"]):
                continue
            paths = parse_paths(row.get(source_col))
            note = f"{stage}の採用ログ"
            add_provenance(provenance, index, stage, paths, "medium", note, str(row.get(answer_col, "")))

    # EDA038からEDA046までのroute結果は、improved/adopted列とsource_pathsがあるものを使う。
    result_logs = [
        ("EDA046", ROOT / "EDA" / "EDA046" / "tables" / "test_all_remaining_routes_result.csv"),
        ("EDA044", ROOT / "EDA" / "EDA044" / "tables" / "test_format_table_image_result.csv"),
        ("EDA043", ROOT / "EDA" / "EDA043" / "tables" / "test_compressed_context_retry_result.csv"),
        ("EDA042", ROOT / "EDA" / "EDA042" / "tables" / "test_document_retry_result.csv"),
        ("EDA041", ROOT / "EDA" / "EDA041" / "tables" / "test_document_search_route_result.csv"),
        ("EDA040", ROOT / "EDA" / "EDA040" / "tables" / "test_table_route_result.csv"),
        ("EDA039", ROOT / "EDA" / "EDA039" / "tables" / "test_format_route_result.csv"),
        ("EDA038", ROOT / "EDA" / "EDA038" / "tables" / "test_diff_route_result.csv"),
        ("EDA037", ROOT / "EDA" / "EDA037" / "tables" / "test_unhandled_route_candidates.csv"),
        ("EDA036", ROOT / "EDA" / "EDA036" / "tables" / "test_openrouter_structured_answer_log.csv"),
        ("EDA035", ROOT / "EDA" / "EDA035" / "tables" / "test_unknown_reduction_log.csv"),
    ]
    for stage, path in result_logs:
        df = load_csv(path)
        if df.empty or "index" not in df.columns:
            continue
        for _, row in df.iterrows():
            index = int(row["index"])
            adopted = any(bool(row.get(col, False)) for col in ["adopted", "llm_adopted", "adopted_by_eda041", "adopted_by_eda044", "adopted_by_eda046"])
            improved = any(bool(row.get(col, False)) for col in row.index if str(col).startswith("improved_by_"))
            if not (adopted or improved):
                continue
            paths = parse_paths(row.get("source_paths")) or parse_paths(row.get("used_paths"))
            add_provenance(provenance, index, stage, paths, "medium", f"{stage}の改善ログ", str(row.get("evidence", "")))

    # それでもない行は、EDA034の採用ステージとtop1、またはEDA021の検索上位を補助ソースにする。
    eda034 = load_csv(ROOT / "EDA" / "EDA034" / "tables" / "test_pipeline_answer_log.csv")
    for _, row in eda034.iterrows():
        add_provenance(
            provenance,
            int(row["index"]),
            f"EDA034_{row.get('source_stage', '')}",
            parse_paths(row.get("top1_source_path")),
            str(row.get("confidence", "low")),
            "EDA034の最終回答ログ。top1_source_pathを補助根拠として記録",
            str(row.get("notes", "")),
        )

    retrieval = load_csv(ROOT / "EDA" / "EDA021" / "tables" / "test_rag_retrieval.csv")
    retrieval_paths_by_index: dict[int, list[str]] = {}
    if not retrieval.empty:
        for index, group in retrieval.groupby("index"):
            paths = group.sort_values("rank")["source_path"].dropna().astype(str).head(5).tolist()
            retrieval_paths_by_index[int(index)] = paths
            add_provenance(
                provenance,
                int(index),
                "EDA021_bm25_top_sources",
                paths,
                "low",
                "個別採用ログがないためBM25検索上位ソースを補助的に記録",
                "",
            )

    # 採用ログはあるがsource_pathsが空の行は、回答を変えずにBM25上位ソースで補助する。
    for _, row in final_predictions.iterrows():
        index = int(row["index"])
        if row["answer"] == "わかりません":
            continue
        current = provenance.get(index, {})
        if current and current.get("source_paths"):
            continue
        paths = retrieval_paths_by_index.get(index, [])
        if paths:
            add_provenance(
                provenance,
                index,
                "EDA021_bm25_top_sources_fallback",
                paths,
                "low",
                "採用ログのsource_pathsが空だったため、BM25検索上位ソースを補助根拠として記録",
                "",
                override=True,
            )

    # unknown行は「回答根拠未確定」と明示しつつ、診断ログの候補ソースがあれば残す。
    diagnostics = load_csv(ROOT / "EDA" / "EDA048" / "tables" / "remaining_unknown_diagnosis.csv")
    diag_by_index = {int(row["index"]): row for _, row in diagnostics.iterrows()} if not diagnostics.empty else {}
    for _, row in final_predictions.iterrows():
        index = int(row["index"])
        if row["answer"] == "わかりません":
            diag = diag_by_index.get(index)
            paths = parse_paths(diag.get("used_paths")) if diag is not None else []
            add_provenance(
                provenance,
                index,
                "unknown_diagnostic_sources",
                paths,
                "none",
                "最終回答はわかりません。候補ソースは診断用であり、回答根拠として未確定",
                "",
                override=True,
            )
    return provenance


def build_source_audit(final_predictions: pd.DataFrame, questions: pd.DataFrame, provenance: dict[int, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    merged = questions.merge(final_predictions, on="index", how="left")
    for _, row in merged.sort_values("index").iterrows():
        index = int(row["index"])
        prov = provenance.get(index, {})
        paths = prov.get("source_paths", [])
        rows.append(
            {
                "index": index,
                "question": row["question"],
                "answer": row["answer"],
                "answer_status": "unknown" if row["answer"] == "わかりません" else "answered",
                "source_stage": prov.get("source_stage", ""),
                "source_confidence": prov.get("source_confidence", ""),
                "source_paths": unique_join(paths),
                "source_count": len(parse_paths(paths) if isinstance(paths, str) else paths),
                "source_note": prov.get("source_note", ""),
                "evidence": prov.get("evidence", ""),
            }
        )
    return pd.DataFrame(rows)


def build_question_answer_source_lines(source_audit: pd.DataFrame) -> list[str]:
    """質問、回答、参照ファイルをMarkdownで照合しやすい形に整える。"""
    lines = [
        "## 質問・回答・参照ファイル一覧",
        "",
        "以下はEDA058提出回答を変更せず、質問文と参照ファイルを併記した一覧である。",
        "",
        "凡例: `質問` はtestの質問文、`回答` はEDA058の提出回答、`参照ファイル` は回答生成または検索で参照したファイルを表す。`わかりません` の行では、参照ファイルは回答根拠ではなく診断時の候補である。",
        "",
    ]
    for _, row in source_audit.sort_values("index").iterrows():
        paths = parse_paths(row.get("source_paths"))
        lines.extend(
            [
                f"### index {int(row['index'])}",
                "",
                f"- 質問: {row['question']}",
                f"- 回答: {row['answer']}",
                "- 参照ファイル:",
            ]
        )
        if paths:
            lines.extend(f"  - `{path}`" for path in paths)
        else:
            lines.append("  - 参照ファイル未確定")
        lines.append("")
    return lines


def write_report(route_result: pd.DataFrame, source_audit: pd.DataFrame, unknown_count: int) -> None:
    source_summary = (
        source_audit.groupby(["answer_status", "source_confidence"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["answer_status", "source_confidence"])
    )
    lines = [
        "# EDA058 モデル比較差分とソース元精査",
        "",
        "## 目的",
        "",
        "座席表以外で残っていた index 62 を処理し、その後、最終回答100件について回答を変更せずにソース元を整理した。",
        "",
        "## index 62",
        "",
        route_result.assign(source_paths=route_result["source_paths"].str.replace(" | ", "<br>", regex=False)).to_markdown(index=False),
        "",
        "凡例: `index` は質問ID、`answer` は採用回答、`source_paths` は回答根拠、`evidence` は上位2件の設定差分を表す。",
        "",
        "## ソース元台帳サマリ",
        "",
        source_summary.to_markdown(index=False),
        "",
        "凡例: `answer_status` は回答済み/未回答、`source_confidence` はソース元の確度、`count` は該当件数を表す。",
        "",
        "## 注意",
        "",
        "- ソース元台帳は回答を変更せず、EDA058提出CSVの回答に対して根拠ファイルを紐づけたもの。",
        "- `low` は個別routeの採用ログがなく、BM25検索上位またはEDA034 top1を補助根拠として記録した行。",
        "- `none` は最終回答が `わかりません` の行であり、候補ソースは回答根拠として未確定。",
        "",
        f"最終提出候補の `わかりません` 件数: {unknown_count}",
        "",
        "詳細100行は `EDA/EDA058/tables/answer_source_audit.csv` に保存した。",
        "",
        "## 提出結果メモ",
        "",
        "| 提出ファイル | SIGNATEスコア |",
        "|:---|---:|",
        "| `eda058_model_diff_submission.zip` | -0.26666666666666666 |",
        "",
        "凡例: `提出ファイル` はSIGNATEへ提出したzip、`SIGNATEスコア` は提出後に表示された評価値を表す。",
        "",
    ]
    lines.extend(build_question_answer_source_lines(source_audit))
    (EDA_DIR / "eda058_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    predictions = pd.read_csv(BASE_PREDICTIONS, header=None, names=["index", "answer"])
    questions = pd.read_csv(QUESTIONS_TEST)

    answer62, top2, evidence62 = build_model_diff_answer()
    predictions.loc[predictions["index"].eq(62), "answer"] = answer62

    route_result = pd.DataFrame(
        [
            {
                "index": 62,
                "question": questions.loc[questions["index"].eq(62), "question"].iloc[0],
                "answer": answer62,
                "route": "aoba_credit_model_diff_top2",
                "source_paths": unique_join(evidence62["source_paths"]),
                "evidence": json.dumps(evidence62["diffs"], ensure_ascii=False),
            }
        ]
    )
    route_result.to_csv(TABLE_DIR / "eda058_route_results.csv", index=False, encoding="utf-8-sig")
    top2.to_csv(TABLE_DIR / "aoba_credit_leaderboard_top2.csv", index=False, encoding="utf-8-sig")

    provenance = collect_route_provenance(predictions, evidence62)
    source_audit = build_source_audit(predictions, questions, provenance)
    source_audit.to_csv(TABLE_DIR / "answer_source_audit.csv", index=False, encoding="utf-8-sig")

    output_csv = PRED_DIR / "eda058_model_diff_predictions.csv"
    output_zip = PRED_DIR / "eda058_model_diff_submission.zip"
    predictions.to_csv(output_csv, index=False, header=False, encoding="utf-8")
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(output_csv, arcname="predictions.csv")

    unknown_count = int(predictions["answer"].eq("わかりません").sum())
    write_report(route_result, source_audit, unknown_count)
    manifest = {
        "eda": "EDA058",
        "purpose": "座席表以外の残件index 62を処理し、最終回答100件のソース元を精査",
        "base_predictions": rel(BASE_PREDICTIONS),
        "output_csv": rel(output_csv),
        "output_zip": rel(output_zip),
        "source_audit": rel(TABLE_DIR / "answer_source_audit.csv"),
        "unknown_count": unknown_count,
        "unknown_indices": predictions.loc[predictions["answer"].eq("わかりません"), "index"].tolist(),
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
