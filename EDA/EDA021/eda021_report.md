# EDA021: test 100問ローカルRAG

## 目的

EDA020の統合JSONLを使い、test 100問に対してローカルBM25検索と抽出型回答生成を実行し、提出形式の `predictions.csv` とzipを作る。

## 出力

- predictions_csv: `EDA/EDA021/predictions/predictions.csv`
- submission_zip: `EDA/EDA021/predictions/eda021_local_rag_submission.zip`
- retrieval_log: `EDA/EDA021/tables/test_rag_retrieval.csv`
- contexts: `EDA/EDA021/contexts`

## 実行設定

- top_k: 8
- max_answer_chars: 900
- LLM API: 未使用

## 出力検証

凡例: `metric` は検証項目、`value` は値を表します。

| metric | value |
| --- | --- |
| prediction_count | 100 |
| empty_answer_count | 0 |
| unknown_answer_count | 0 |
| max_answer_length | 900 |
| min_answer_length | 7 |

## 提出結果

- `eda021_local_rag_submission.zip` のSIGNATEスコア: `-1`

この提出は参加登録と提出形式確認としては通ったが、ローカルBM25検索と抽出型回答だけでは回答品質が不十分だった。
特に、表計算、差分、書式、画像数値抽出を専用処理せずに本文行抽出で答えているため、正答に届かない質問が多いと考えられる。

## route別件数

凡例: `route` はEDA011で推定した処理ルート、`count` はtest質問数を表します。

| route | count |
| --- | --- |
| code_reading | 3 |
| diff_check | 9 |
| document_whole_context | 14 |
| fallback_bm25_llm | 37 |
| format_extraction | 17 |
| image_ocr | 3 |
| table_calculation | 17 |

## answer_method別件数

凡例: `answer_method` は回答生成方法、`count` は件数を表します。

| answer_method | count |
| --- | --- |
| best_line_extractive | 75 |
| multi_line_extractive | 24 |
| top_snippet_low_confidence | 1 |

## 注意点

- このEDAは提出形式確認を兼ねたローカルRAGであり、GPT-OSS-120bなどのLLM回答生成はまだ使っていない。
- 表計算、差分、書式、画像数値抽出は専用処理を未実装のため、抽出型回答では誤る可能性がある。
- 実提出前には、少なくともvalidでroute別の回答精度を確認する必要がある。
