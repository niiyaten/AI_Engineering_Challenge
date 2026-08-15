# EDA014: Excel/CSV/TSV表データ前処理

## 目的

Excel、CSV、TSVを、LLMが読めるMarkdown、再現・検索用JSON、計算可能なCSVへ変換する。
表データはLLMに丸投げせず、後続のpandas/openpyxl処理で計算できる形を保持する。

## 出力

- Markdown/JSON: `data/processed/share/**/*.xlsx.md`, `*.xlsx.structure.json`, `*.csv.md`, `*.csv.structure.json`
- ExcelシートCSV: `data/processed/share/**/*.xlsx.sheets/*.csv`
- 正規化CSV: `data/processed/share/**/*.data.csv`
- 変換ログ: `EDA/EDA014/tables/tabular_conversion_log.csv`

## 処理結果

凡例: `extension` は拡張子、`status` は処理状態、`count` は該当ファイル数を表します。

| extension | status | count |
| --- | --- | --- |
| .csv | ok | 29 |
| .tsv | ok | 2 |
| .xlsx | error | 2 |
| .xlsx | ok | 19 |

## エラー・スキップ

凡例: `raw_relative_path` は元ファイル、`extension` は拡張子、`status` は処理状態、`error_type` と `error_message` は失敗理由を表します。

| raw_relative_path | extension | status | error_type | error_message |
| --- | --- | --- | --- | --- |
| share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/02.計画/~$スケジュール.xlsx | .xlsx | error | RuntimeError | temporary_office_file |
| share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/02.計画/スケジュール.xlsx | .xlsx | error | BadZipFile | File is not a zip file |

## 注意点

- 暗号化またはOffice一時ファイルは無理に復号せず、エラーまたはスキップとして扱う。
- Excel数式は保存するが、式の再計算はこのEDAでは行わない。
- グラフは存在数と基本メタデータを保存する。画像としての読み取りや数値抽出は別工程で扱う。
