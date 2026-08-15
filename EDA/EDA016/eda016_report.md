# EDA016: PDF前処理

## 目的

PDFをページ単位Markdownと構造JSONへ変換し、会議録、報告資料、提案書、報告書をページ番号付きで検索できるようにする。

## 出力

- Markdown/JSON: `data/processed/share/**/*.pdf.md`, `*.pdf.structure.json`
- 変換ログ: `EDA/EDA016/tables/pdf_conversion_log.csv`

## 処理結果

凡例: `status` は処理状態、`count` は該当PDFファイル数を表します。

| status | count |
| --- | --- |
| ok | 28 |

## 抽出総数

凡例: `pdf_count` は成功PDF数、`page_count` は抽出ページ総数、`total_char_count` は抽出文字数の合計です。

| pdf_count | page_count | total_char_count |
| --- | --- | --- |
| 28 | 220 | 53211 |

## エラー

凡例: `raw_relative_path` は元ファイル、`error_type` と `error_message` は失敗理由を表します。

該当データはありません。

## 注意点

- このEDAではPDFを画像レンダリングしてOCRする処理は行っていない。
- 表や段組みの抽出順が崩れる可能性があるため、ページ番号をJSONに保持する。
