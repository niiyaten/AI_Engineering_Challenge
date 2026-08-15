from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
INPUT_RESULT = BASE_DIR / "EDA" / "EDA044" / "tables" / "test_format_table_image_result.csv"
UNKNOWN = "わかりません"


def route_gap(question: str, route: str, subtype: str) -> tuple[str, str, str]:
    """残件質問を、既存routeでは足りない処理単位へ分類する。"""
    q = str(question)
    if any(x in q for x in ["CT", "ES", "内線", "主担当者"]):
        return (
            "contract_alias_contact_lookup",
            "契約書や社内用語の略称からCT/ESなどの役割を解決し、人物名や内線へつなぐroute",
            "社内用語集、契約書、体制表、座席/連絡先情報を結合して検索する",
        )
    if any(x in q for x in ["FM", "IM", "座って", "向かい", "右側"]):
        return (
            "seating_chart_spatial_ocr",
            "座席表画像から位置関係と氏名/EXTを読むroute",
            "座席表画像をVision/OCRに送り、座席座標とラベルを構造化する",
        )
    if any(x in q for x in ["会議ID", "会議録", "コメント", "アクションID", "チェックポイント"]):
        return (
            "meeting_action_status_lookup",
            "会議録、報告資料、アクションID、チェックポイントを横断するroute",
            "会議ID/日付/アクションIDをキーに会議録と報告資料を結合する",
        )
    if any(x in q for x in ["回帰係数", "予測値", "F1 スコア", "閾値"]):
        return (
            "model_formula_recompute",
            "Notebook/コード/報告書の係数や閾値を取り出してrawデータで再計算するroute",
            "係数表、実装コード、train.csvを結合してpandasで再計算する",
        )
    if any(x in q for x in ["APR", "契約金額", "固定金額", "1行あたり", "想定工数", "担当タスク数"]):
        return (
            "cross_project_contract_aggregation",
            "複数案件の契約条件、APR、工数、データ行数を横断集計するroute",
            "全案件の契約書/最終報告/スケジュール/社内管理基準を正規化して集計する",
        )
    if "スケジュール_r1" in q or "比較" in q or "設定差分" in q:
        return (
            "structured_diff_semantic_filter",
            "old/new差分から案件遂行に関係する変更だけを抽出するroute",
            "PPTX/XLSX/Notebookを構造単位で比較し、状態変更や設定差分を分類する",
        )
    if any(x in q for x in ["黄色", "ハイライト", "相関係数"]):
        return (
            "spreadsheet_format_semantic_context",
            "セル色や表示形式から、条件・集計対象・意味を復元するroute",
            "styled_cellsと同じ行/列/周辺表を結合し、色の意味を推定する",
        )
    if "グラフ" in q or "折れ線" in q:
        return (
            "chart_value_extraction",
            "画像またはExcelグラフから系列名と座標値を読むroute",
            "元データ、chart XML、画像OCR/Visionを組み合わせて値を抽出する",
        )
    if "別契約" in q or "第何週" in q:
        return (
            "proposal_operation_clause_lookup",
            "提案書/契約書内の運用条項やスケジュール項目を抽出するroute",
            "PPTXスライド構造と契約条項をキーワードではなく節単位で検索する",
        )
    return (
        f"existing_route_needs_refinement:{route}/{subtype}",
        "既存routeの文脈抽出・採用条件を改善する対象",
        "個別ログを確認して文脈圧縮または根拠抽出を改善する",
    )


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT_RESULT)
    rem = df[df["answer_after_eda044"].eq(UNKNOWN)].copy()
    rows = []
    for _, row in rem.sort_values("index").iterrows():
        new_route, reason, next_action = route_gap(row["question"], row["route"], row["subtype"])
        rows.append(
            {
                "index": int(row["index"]),
                "old_route": row["route"],
                "old_subtype": row["subtype"],
                "new_route_candidate": new_route,
                "question": row["question"],
                "why_existing_route_is_insufficient": reason,
                "recommended_next_action": next_action,
            }
        )
    gap_df = pd.DataFrame(rows)
    summary = (
        gap_df.groupby("new_route_candidate", as_index=False)
        .agg(
            count=("index", "count"),
            indices=("index", lambda x: ",".join(map(str, x))),
            recommended_next_action=("recommended_next_action", "first"),
        )
        .sort_values(["count", "new_route_candidate"], ascending=[False, True])
    )
    gap_df.to_csv(TABLE_DIR / "remaining_route_gap_inventory.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(TABLE_DIR / "remaining_route_gap_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# EDA045: 残件20件の未route化棚卸し

## 背景と目的

EDA044提出スコアは `-0.3` まで改善したが、残り20件には既存route名では表現しきれていない質問が残っている。
EDA045では、回答生成は行わず、残件を新しく作るべきroute候補へ分類した。

## 結果

- 入力: `EDA/EDA044/tables/test_format_table_image_result.csv`
- 残件: {len(gap_df)}件
- 新route候補数: {gap_df["new_route_candidate"].nunique()}件

## 新route候補別集計

凡例: `new_route_candidate` は新設すべきroute候補、`count` は件数、`indices` は対象質問ID、`recommended_next_action` は次に実装すべき処理を表す。

{summary.to_markdown(index=False)}

## 質問別分類

凡例: `old_route`/`old_subtype` はこれまでの分類、`new_route_candidate` は新しく必要な処理単位、`why_existing_route_is_insufficient` は既存routeで足りない理由を表す。

{gap_df.to_markdown(index=False)}

## 次の方針

優先度は、件数と正解可能性の両方で判断する。
最初に作るべきrouteは `contract_alias_contact_lookup`、`meeting_action_status_lookup`、`model_formula_recompute`、`cross_project_contract_aggregation` のいずれかである。
スコア改善だけを狙うなら、誤答リスクが高い画像・座席表より、表計算と契約横断集計を先に処理する方がよい。
"""
    (OUT_DIR / "eda045_report.md").write_text(report, encoding="utf-8")
    manifest = {
        "eda": "EDA045",
        "input": "EDA/EDA044/tables/test_format_table_image_result.csv",
        "remaining_count": int(len(gap_df)),
        "new_route_candidate_count": int(gap_df["new_route_candidate"].nunique()),
        "outputs": [
            "EDA/EDA045/tables/remaining_route_gap_inventory.csv",
            "EDA/EDA045/tables/remaining_route_gap_summary.csv",
            "EDA/EDA045/eda045_report.md",
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
