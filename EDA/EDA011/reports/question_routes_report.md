# EDA011: 質問ルーティング設計

最終パイプラインの入口として、valid/test全問に処理ルートを付与しました。

| split | route | question_count |
| --- | --- | --- |
| test | code_reading | 3 |
| test | diff_check | 9 |
| test | document_whole_context | 14 |
| test | fallback_bm25_llm | 37 |
| test | format_extraction | 17 |
| test | image_ocr | 3 |
| test | table_calculation | 17 |
| valid | code_reading | 4 |
| valid | diff_check | 1 |
| valid | document_whole_context | 7 |
| valid | fallback_bm25_llm | 8 |
| valid | format_extraction | 2 |

凡例: `split` はvalid/test、`route` は推定処理ルート、`question_count` は質問数を表します。
