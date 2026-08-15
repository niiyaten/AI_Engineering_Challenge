# EDA011: 提出用パイプライン設計チェックリスト

EDA011の統合棚卸しを、提出用コードへ落とすためのチェックリストにまとめました。

## 実行結果インデックス

| task | candidate_count | table_questions | tabular_docs | format_questions | format_docs | image_files | image_questions | diff_questions | version_docs | routed_questions | artifact_count | valid_questions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| whole_doc_llm_candidates | 4.0 |  |  |  |  |  |  |  |  |  |  |  |
| table_question_inventory |  | 24.0 |  |  |  |  |  |  |  |  |  |  |
| tabular_document_inventory |  |  | 48.0 |  |  |  |  |  |  |  |  |  |
| format_inventory |  |  |  | 19.0 | 44.0 |  |  |  |  |  |  |  |
| image_inventory |  |  |  |  |  | 54.0 | 4.0 |  |  |  |  |  |
| diff_inventory |  |  |  |  |  |  |  | 10.0 | 8.0 |  |  |  |
| question_routes |  |  |  |  |  |  |  |  |  | 130.0 |  |  |
| pipeline_artifact_map |  |  |  |  |  |  |  |  |  |  | 7.0 |  |
| answer_policy |  |  |  |  |  |  |  |  |  |  |  | 30.0 |

凡例: `task` は統合EDA内のサブテーマ、それ以外の列は各サブテーマの主要件数を表します。

## 提出用チェックリスト

| step | status | source |
| --- | --- | --- |
| extract_files | done | EDA002/EDA004 |
| query_route | prototype_done | EDA011/question_routes.csv |
| whole_doc_context | prototype_done | EDA010/EDA011 |
| table_calculation | inventory_done | EDA011 table inventory |
| format_extraction | inventory_done | EDA011 format inventory |
| image_ocr | needs_model_or_ocr | EDA011 image inventory |
| diff_check | inventory_done | EDA011 diff inventory |
| submission_generation | not_started | EDA005 baseline only |

凡例: `step` は提出パイプラインの工程、`status` は現状、`source` は根拠となるEDAを表します。
