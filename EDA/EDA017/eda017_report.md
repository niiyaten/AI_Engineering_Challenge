# EDA017: Pythonプログラム前処理

## 目的

Pythonプログラムを実行せずに静的解析し、分析手順、使用ライブラリ、関数、入出力候補を検索できるMarkdown/JSONへ変換する。

## 出力

- Markdown/JSON: `data/processed/share/**/*.py.md`, `*.py.structure.json`
- 変換ログ: `EDA/EDA017/tables/python_conversion_log.csv`

## 処理結果

凡例: `status` は処理状態、`count` は該当Pythonファイル数を表します。

| status | count |
| --- | --- |
| ok | 100 |

## 抽出総数

凡例: 各項目は成功したPythonファイルから抽出した合計件数を表します。

| python_file_count | line_count | function_count | class_count | file_operation_count |
| --- | --- | --- | --- | --- |
| 100 | 11520 | 362 | 0 | 1086 |

## エラー

凡例: `raw_relative_path` は元ファイル、`error_type` と `error_message` は失敗理由を表します。

該当データはありません。
