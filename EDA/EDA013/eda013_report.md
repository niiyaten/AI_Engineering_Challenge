# EDA013: embedding用標準レコード作成

## 目的

EDA012で作成したMarkdown/構造JSONと、EDA011で棚卸しした画像を、BM25・ベクトル検索・LLM入力で共通利用できるJSONLへ正規化した。
画像はバイナリをそのままembeddingせず、OpenRouterの無料Vision候補で説明文へ変換し、検索用テキストとして保存する方針を検証した。

## 出力

- embedding_records: `data/processed/embedding/embedding_records.jsonl`
- record_summary: `EDA/EDA013/tables/embedding_record_summary.csv`
- file_summary: `EDA/EDA013/tables/embedding_file_summary.csv`
- image_to_text_calls: `EDA/EDA013/tables/image_to_text_calls.csv`
- ignored_files: `EDA/EDA013/tables/ignored_files.csv`

## 主要結果

- 総レコード数: 936
- 画像レコード数: 55
- OpenRouter画像toテキスト成功数: 4
- 鍵付き・変換失敗として無視したファイル数: 1
- 画像API呼び出し上限: 4

## record_type別集計

凡例: `record_type` はembedding候補の種類、`record_count` は件数、`empty_text_count` は検索テキストが空の件数、`short_text_count_lt_20` は20文字未満の件数、`avg_text_length` は平均文字数。

| record_type | record_count | empty_text_count | short_text_count_lt_20 | avg_text_length |
| --- | --- | --- | --- | --- |
| image | 55 | 0 | 0 | 673.2 |
| metadata | 46 | 0 | 0 | 115.3 |
| paragraph | 757 | 0 | 97 | 346.5 |
| table | 78 | 0 | 1 | 516.4 |

## 画像処理ステータス

凡例: `status` は画像toテキスト処理状態、`count` は画像レコード件数。

| status | count |
| --- | --- |
| ok | 4 |
| skipped_limit | 50 |
| skipped_unsupported_format | 1 |

## OpenRouter無料Visionモデル候補

凡例: `rank` は候補順、`model` はOpenRouterモデルID、`source` は候補取得元、`selected_first_success` は最初に成功したモデルかを表す。

| rank | model | source | selected_first_success |
| --- | --- | --- | --- |
| 1 | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | cli_arg | True |

## 画像toテキスト代表例

凡例: `image_path` は処理対象画像、`model` は成功モデル、`text_preview` はembeddingに入れる説明文の先頭部分。

| image_path | model | text_preview |
| --- | --- | --- |
| data/raw/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/reports/figures/figure_06.png | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 画像ファイル: figure_06.png OCR:  画像説明: The user wants me to extract information from the provided image and convert it into a specific JSON format for RAG search.  **1. Analyze the Image:** * **Title:** "day による件数推移" (Trend of the number of item |
| data/raw/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/reports/figures/categorical_distribution_top3.png | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 画像ファイル: categorical_distribution_top3.png OCR:  画像説明: The user wants me to convert the provided image into a RAG search text format. I need to extract: 1. **OCR Text**: All readable text from the image (titles, axis labels, category names,  |
| data/raw/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 画像ファイル: feature_correlation_heatmap.png OCR:  画像説明: The user wants me to convert the provided image into a RAG search-ready text format. I need to extract: 1. **OCR Text**: All visible text in the image (titles, axis labels, numbers, etc.). |
| data/raw/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/reports/figures/missing_rate_top20.png | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 画像ファイル: missing_rate_top20.png OCR:  画像説明: The user wants me to convert the provided image into RAG search text. I need to extract: 1. **OCR Text**: All readable text from the image. 2. **Chart Description**: What the chart is about (title, |

## 無視したファイル

凡例: `raw_relative_path` は元ファイル、`reason` は無視理由、`error_type` と `error_message` は変換時のエラー情報。

| raw_relative_path | reason | error_type | error_message |
| --- | --- | --- | --- |
| share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/01.契約/契約書_pw-kaede20250902.docx | docx_conversion_failed_or_keyed | BadZipFile | File is not a zip file |

## 注意点

- このEDAではembedding自体は実行していない。次段階で `text_for_embedding` をモデルに渡す。
- JSON構造は再現・根拠追跡用であり、JSON全文をそのままembeddingする前提ではない。
- OpenRouter APIキーは `.apikey` または環境変数から読み、キー本文はログ・成果物に保存しない。
- 外部APIの無料枠・レート制限により、画像toテキストは一部失敗する可能性がある。その場合もレコードに失敗理由を残す。
