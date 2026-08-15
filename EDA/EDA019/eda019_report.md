# EDA019: Markdown品質確認と保存

## 目的

既存Markdownを再変換せず、文字化けや空ファイルなどを簡易確認したうえで、`data/processed/share` へ同じ内容で保存する。

## 出力

- Markdown: `data/processed/share/**/*.md`
- 構造JSON: `data/processed/share/**/*.md.structure.json`
- 変換ログ: `EDA/EDA019/tables/markdown_quality_log.csv`

## 処理結果

凡例: `status` は品質確認状態、`count` は該当Markdownファイル数を表します。

| status | count |
| --- | --- |
| ok | 31 |

## 警告

凡例: `quality_flags` は検出した品質警告、`char_count` は文字数、`heading_count` はMarkdown見出し数を表します。

該当データはありません。

## エラー

凡例: `raw_relative_path` は元ファイル、`error_type` と `error_message` は失敗理由を表します。

該当データはありません。
