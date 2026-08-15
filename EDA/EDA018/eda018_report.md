# EDA018: Notebook前処理

## 目的

Notebookを実行せずにセル単位Markdownと構造JSONへ変換し、分析手順、コード、出力、図を検索できるようにする。

## 出力

- Markdown/JSON: `data/processed/share/**/*.ipynb.md`, `*.ipynb.structure.json`
- 出力画像: `data/processed/share/**/*.ipynb.assets/*`
- 変換ログ: `EDA/EDA018/tables/notebook_conversion_log.csv`

## 処理結果

凡例: `status` は処理状態、`count` は該当Notebookファイル数を表します。

| status | count |
| --- | --- |
| ok | 11 |

## 抽出総数

凡例: 各項目は成功したNotebookから抽出した合計件数を表します。

| notebook_count | cell_count | code_cell_count | markdown_cell_count | output_count | image_asset_count |
| --- | --- | --- | --- | --- | --- |
| 11 | 211 | 105 | 106 | 202 | 54 |

## エラー

凡例: `raw_relative_path` は元ファイル、`error_type` と `error_message` は失敗理由を表します。

該当データはありません。
