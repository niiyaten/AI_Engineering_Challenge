# EDA011: パイプライン棚卸し統合

## 目的・背景

EDA011は、軽量な棚卸し・設計タスクを1つにまとめた統合EDAです。  
文書全体LLM候補、表計算、書式、画像/OCR、差分、全問ルーティング、成果物マップ、回答ポリシー、提出用チェックリストを、提出用パイプラインへつなげるために整理します。

## 実行方法

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python EDA\EDA011\eda011_pipeline_inventory.py
```

## 主な結果

| サブテーマ | 主な結果 |
|---|---:|
| 文書全体LLM候補 | 4 |
| 表計算質問 | 24 |
| CSV/XLSX系文書 | 48 |
| 書式質問 | 19 |
| 書式メタデータあり文書 | 44 |
| 画像ファイル | 54 |
| 画像質問 | 4 |
| 差分質問 | 10 |
| 版違い文書候補 | 8 |
| ルーティング対象質問 | 130 |
| 提出用チェックリスト項目 | 8 |

凡例: `サブテーマ` はEDA011内で整理した処理領域、`主な結果` は対象件数を表します。

## 主な成果物

| パス | 内容 |
|---|---|
| `EDA/EDA011/eda011_pipeline_inventory.py` | 統合棚卸しスクリプト |
| `EDA/EDA011/tables/whole_doc_llm_candidates.csv` | 文書全体LLM候補 |
| `EDA/EDA011/tables/table_question_inventory.csv` | 表計算質問の棚卸し |
| `EDA/EDA011/tables/tabular_document_inventory.csv` | CSV/XLSX系文書の棚卸し |
| `EDA/EDA011/tables/format_question_inventory.csv` | 書式質問の棚卸し |
| `EDA/EDA011/tables/image_file_inventory.csv` | 画像ファイル棚卸し |
| `EDA/EDA011/tables/diff_question_inventory.csv` | 差分質問の棚卸し |
| `EDA/EDA011/tables/question_routes.csv` | valid/test全問の処理ルート |
| `EDA/EDA011/tables/submission_pipeline_checklist.csv` | 提出用パイプライン設計チェックリスト |
| `EDA/EDA011/reports/` | 各サブテーマの詳細レポート |

凡例: `パス` は成果物の位置、`内容` はそのファイルで確認できる情報を表します。

## 次に使う場面

次は、`question_routes.csv` を起点に、`table_calculation`、`document_whole_context`、`format_extraction` などのルート別実回答生成を実装します。
