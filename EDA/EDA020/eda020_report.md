# EDA020: 統合embedding_records作成

## 目的

EDA012からEDA019までで作成したMarkdown/JSON/assetsを、検索、BM25、embedding、LLM入力で共通利用できるJSONLへ統合する。

## 出力

- embedding_records: `data/processed/embedding/embedding_records.jsonl`
- record_summary: `EDA/EDA020/tables/embedding_record_summary.csv`
- integration_errors: `EDA/EDA020/tables/integration_errors.csv`

## 品質確認

- 総レコード数: 2484
- 空テキストレコード数: 0
- record_id重複数: 0
- 統合エラー数: 0

## record_type別件数

凡例: `record_type` は検索単位の種類、`count` は件数を表します。

| record_type | count |
| --- | --- |
| generic_chunk | 423 |
| image | 54 |
| markdown_chunk | 41 |
| metadata | 291 |
| notebook_cell | 211 |
| pdf_page | 108 |
| pptx_slide | 386 |
| python_code_chunk | 424 |
| python_function | 362 |
| python_summary | 100 |
| table_file | 31 |
| xlsx_sheet | 53 |

## file_type別件数

凡例: `file_type` は元ファイル形式、`count` は該当レコード数を表します。

| file_type | count |
| --- | --- |
|  | 469 |
| csv | 58 |
| image | 54 |
| ipynb | 222 |
| md | 72 |
| pdf | 136 |
| pptx | 411 |
| py | 986 |
| tsv | 4 |
| xlsx | 72 |

## 統合エラー

凡例: `structure_json_path` は読み込み対象、`error_type` と `error_message` は失敗理由です。

該当データはありません。
