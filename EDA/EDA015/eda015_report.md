# EDA015: PowerPoint前処理

## 目的

PowerPointをスライド単位Markdownと構造JSONへ変換し、提案書、報告書、座席表、版違い比較で利用できる中間データを作る。

## 出力

- Markdown/JSON: `data/processed/share/**/*.pptx.md`, `*.pptx.structure.json`
- 抽出画像: `data/processed/share/**/*.pptx.assets/*`
- 変換ログ: `EDA/EDA015/tables/pptx_conversion_log.csv`

## 処理結果

凡例: `status` は処理状態、`count` は該当PowerPointファイル数を表します。

| status | count |
| --- | --- |
| error | 1 |
| ok | 25 |

## 抽出総数

凡例: 各項目は成功したPowerPointから抽出したスライド、テキスト図形、表、画像、グラフの合計件数を表します。

| slide_count | text_shape_count | table_count | image_count | chart_count |
| --- | --- | --- | --- | --- |
| 386 | 4455 | 79 | 3 | 6 |

## エラー・スキップ

凡例: `raw_relative_path` は元ファイル、`status` は処理状態、`error_type` と `error_message` は失敗理由を表します。

| raw_relative_path | status | error_type | error_message | processed_markdown_path | processed_structure_path | slide_count | text_shape_count | table_count | image_count | chart_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/~$提案書.pptx | error | RuntimeError | temporary_office_file |  |  |  |  |  |  |  |

## 注意点

- このEDAではスライド画像をOpenRouterへ送っていない。画像説明が必要な場合は、抽出assetsを対象に別工程で実行する。
- グラフは基本メタデータを保存するが、グラフ内の数値系列の厳密抽出は次工程で扱う。
- PowerPointの座標はpt単位に変換してJSONへ保存した。
