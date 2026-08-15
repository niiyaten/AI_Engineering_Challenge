from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"

RESULT_046 = BASE_DIR / "EDA" / "EDA046" / "tables" / "test_all_remaining_routes_result.csv"
ATTEMPT_046 = BASE_DIR / "EDA" / "EDA046" / "tables" / "test_all_remaining_routes_attempt_log.csv"
GAP_045 = BASE_DIR / "EDA" / "EDA045" / "tables" / "remaining_route_gap_inventory.csv"
IMAGE_047 = BASE_DIR / "EDA" / "EDA047" / "tables" / "image_to_text_results.csv"

UNKNOWN = "\u308f\u304b\u308a\u307e\u305b\u3093"


def norm(value: object) -> str:
    """表記ゆれを吸収して、判定しやすい文字列へそろえる。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def is_unknown(value: object) -> bool:
    """提出回答として未回答扱いにする値かどうかを判定する。"""
    text = norm(value)
    return text == UNKNOWN or "情報が不足" in text or text == ""


def load_csv(path: Path) -> pd.DataFrame:
    """UTF-8 BOM付き/なしのCSVを文字列として読み込む。"""
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")


def classify_reason(row: pd.Series) -> dict[str, str]:
    """残件ごとに、なぜ個別routeでも解けなかったかを人間が読める分類へ落とす。"""
    question = norm(row.get("question"))
    route = norm(row.get("route"))
    new_route = norm(row.get("new_route_candidate"))
    finish_reason = norm(row.get("finish_reason"))
    status = norm(row.get("status"))
    used_paths = norm(row.get("used_paths"))

    if "座席" in question or "FM" in question or "右側" in question or "向かい" in question:
        return {
            "failure_family": "spatial_image",
            "why_unknown": "座席表画像の人名/EXTだけでなく、左右・向かいを座標として読む必要がある。EDA047でも座席表は再実行時に空contentで安定しなかった。",
            "next_action": "座席表画像をVisionで再試行し、成功時の結果を保持したうえで、人名・EXT・x/y座標の表に変換する。PPTX shape座標から座席表を復元できるかも確認する。",
            "eda048_priority": "high",
        }
    if "グラフ" in question or "x=3" in question:
        return {
            "failure_family": "chart_value",
            "why_unknown": "画像説明だけでは小数第5位の値を読めない。元Notebook/CSVまたは生成コードから系列値を再計算する必要がある。",
            "next_action": "Notebookの該当セルと元CSVを結合し、グラフ番号、系列色、x値からy値を計算するrouteを作る。Visionは図の特定補助に限定する。",
            "eda048_priority": "high",
        }
    if "回帰係数" in question or "予測値" in question or "F1" in question:
        return {
            "failure_family": "model_formula_recompute",
            "why_unknown": "係数表、標準化表、対象行、閾値探索を正しく接続する必要があり、文脈LLMだけでは計算式が確定しない。",
            "next_action": "Excelの回帰分析シート、標準化シート、trainシートを直接読み、係数名と対象列を対応させてPythonで再計算する。",
            "eda048_priority": "high",
        }
    if "APR" in question or "契約金額" in question or "着手金" in question or "1タスク" in question:
        return {
            "failure_family": "cross_project_structured_aggregation",
            "why_unknown": "複数案件の契約書、社内管理基準、計画表、担当者情報を横断して正規化する必要がある。検索文脈では比較対象の全件性が保証できない。",
            "next_action": "全案件の契約条件・略称・金額・担当者・工数を1つの正規化テーブルにし、質問ごとに集計式を実行する。",
            "eda048_priority": "high",
        }
    if "会議ID" in question or "アクションID" in question or "コメント" in question or "チェックポイント" in question:
        return {
            "failure_family": "meeting_action_structure",
            "why_unknown": "PDF/Word会議録の本文検索だけでは、会議ID、ページ、アクションID、コメント、完了状態の対応が構造化されていない。",
            "next_action": "会議録/報告資料をページ単位・表単位で再抽出し、meeting_id、date、page、action_id、status、comment_textを持つ台帳を作る。",
            "eda048_priority": "high",
        }
    if "黄色" in question or "ハイライト" in question or "Sheet2" in question:
        return {
            "failure_family": "spreadsheet_format_semantics",
            "why_unknown": "セル色は抽出済みでも、その色が何の条件・集計を意味するかが表構造と結びついていない。",
            "next_action": "openpyxlで色付きセルの座標、周辺見出し、同じ行/列の値、数式をまとめ、条件候補をローカルで推定する。",
            "eda048_priority": "medium",
        }
    if "old" in question or "最新版" in question or "変更" in question or "比較" in question:
        return {
            "failure_family": "semantic_diff",
            "why_unknown": "文字列差分は取れているが、案件遂行に関連する変更だけを抽出する意味フィルタが弱い。Excel差分では状態変更の除外条件も必要。",
            "next_action": "old/newをスライド・シート・セクション単位で対応付け、数値/期日/体制/条件/モデル設定だけを差分候補としてLLMに渡す。",
            "eda048_priority": "medium",
        }
    if "PL案" in question or "別契約" in question:
        return {
            "failure_family": "pptx_table_or_clause_lookup",
            "why_unknown": "PowerPoint内の表・図形テキストの読み順や略称解決が弱く、該当するスケジュール/条項をピンポイントで拾えていない。",
            "next_action": "PPTX shapeの座標、表セル、スライド番号を保持した検索レコードを作り、略称から対象ファイルを絞る。",
            "eda048_priority": "medium",
        }
    return {
        "failure_family": "retrieval_or_context_gap",
        "why_unknown": f"route={route}, new_route={new_route}, status={status}, finish_reason={finish_reason}。抽出文脈だけでは根拠が確定しない。used_paths={used_paths[:200]}",
        "next_action": "対象ファイルの構造化粒度を上げ、LLMへ渡す前にローカル候補を1つ以上作る。",
        "eda048_priority": "medium",
    }


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    result = load_csv(RESULT_046)
    attempt = load_csv(ATTEMPT_046)
    gap = load_csv(GAP_045)
    image = load_csv(IMAGE_047)

    result["is_unknown_after_eda046"] = result["answer_after_eda046"].map(is_unknown)
    remaining = result[result["is_unknown_after_eda046"]].copy()

    # EDA045の新route候補とEDA046のAPI状態を付与する。
    remaining = remaining.merge(
        gap[["index", "new_route_candidate", "why_existing_route_is_insufficient", "recommended_next_action"]],
        on="index",
        how="left",
    )
    remaining = remaining.merge(
        attempt[["index", "status", "finish_reason", "llm_answer", "used_paths", "context_chars"]],
        on="index",
        how="left",
        suffixes=("", "_attempt"),
    )

    diagnoses: list[dict[str, str]] = []
    for _, row in remaining.iterrows():
        diagnoses.append(classify_reason(row))
    diagnosis_df = pd.concat([remaining.reset_index(drop=True), pd.DataFrame(diagnoses)], axis=1)

    family_summary = (
        diagnosis_df.groupby(["failure_family", "eda048_priority"], as_index=False)
        .size()
        .sort_values(["eda048_priority", "size", "failure_family"], ascending=[True, False, True])
    )

    image_success = int(image["success"].map(lambda x: norm(x).lower() == "true").sum()) if not image.empty else 0
    image_processed = int(len(image))

    diagnosis_path = TABLE_DIR / "remaining_unknown_diagnosis.csv"
    summary_path = TABLE_DIR / "remaining_unknown_family_summary.csv"
    diagnosis_df.to_csv(diagnosis_path, index=False, encoding="utf-8-sig")
    family_summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    report = f"""# EDA048: EDA046後に `わかりません` が残る理由の整理

## 背景と目的

EDA046では、EDA045で分類した残件20件に個別routeを作り、OpenRouter 20Bで短答化した。
その結果、4件は追加採用できたが、16件はまだ `わかりません` のままだった。

EDA048では、この16件について「個別routeを作ってもなぜ解けなかったか」を分類し、次に作るべき処理を決める。

## 入力

- EDA046結果: `{RESULT_046.relative_to(BASE_DIR).as_posix()}`
- EDA046 attempt log: `{ATTEMPT_046.relative_to(BASE_DIR).as_posix()}`
- EDA045 gap inventory: `{GAP_045.relative_to(BASE_DIR).as_posix()}`
- EDA047 image-to-text結果: `{IMAGE_047.relative_to(BASE_DIR).as_posix()}`

## 結果

- EDA046後の `わかりません`: {len(diagnosis_df)}件
- EDA047画像処理: {image_processed}件中{image_success}件成功

## 残件の失敗ファミリー

凡例: `failure_family` は失敗の種類、`eda048_priority` は次に実装する優先度、`size` は件数を表す。

{family_summary.to_markdown(index=False)}

## 残件別の診断

凡例: `index` はtest質問番号、`new_route_candidate` はEDA045で提案したroute、`why_unknown` は残った理由、`next_action` は次に作る処理を表す。

{diagnosis_df[["index", "route", "new_route_candidate", "question", "failure_family", "why_unknown", "next_action"]].to_markdown(index=False)}

## 考察

個別routeを作っても残った理由は、LLMの回答能力よりも、LLMへ渡す前の根拠候補がまだ計算可能・比較可能な形になっていないことが大きい。
特に、会議録/アクションID、座席表、横断契約集計、回帰係数再計算は、Markdown検索ではなく専用の構造化テーブルを先に作る必要がある。

EDA047の再実行で画像説明は5件まで増えたが、座席表はまだ安定して読めていない。
座席表質問はVisionの文章説明だけでなく、PPTX shape座標または画像からの座標テーブル化が必要。

## 次にやるべきこと

1. EDA049: 会議録/アクションID台帳を作る。
2. EDA050: 座席表を人名、EXT、POD、x/y座標のテーブルにする。
3. EDA051: 全案件の契約条件、金額、略称、担当者、工数を正規化した横断テーブルを作る。
4. EDA052: Excelの色付きセルと周辺見出し、数式、集計対象を結びつける。
5. EDA053: 回帰係数、標準化、対象行、閾値探索をローカルで再計算する。
6. EDA054: old/new差分をスライド、シート、セクション単位で対応付け、案件遂行に関係する差分だけを抽出する。
"""
    report_path = OUT_DIR / "eda048_report.md"
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "eda": "EDA048",
        "remaining_unknown_count": int(len(diagnosis_df)),
        "image047_processed_count": image_processed,
        "image047_success_count": image_success,
        "outputs": [
            diagnosis_path.relative_to(BASE_DIR).as_posix(),
            summary_path.relative_to(BASE_DIR).as_posix(),
            report_path.relative_to(BASE_DIR).as_posix(),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
