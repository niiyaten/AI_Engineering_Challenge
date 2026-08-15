# EDA007: LLM向けMarkdownコンテキスト生成

## 目的・背景

EDA006では、valid 30問について、検索TopKがLLMに渡せる根拠になっているかを診断しました。その結果、`ready_for_llm` が10件あり、検索根拠はあるものの、EDA005のテンプレ回答では十分に抽出・整形できないことが分かりました。

EDA007では、LLM APIやローカルLLMをまだ呼び出さず、検索根拠をLLMへ渡しやすいMarkdown形式に整形します。これにより、将来OpenRouterやOllamaなどを導入する場合に、`Question + Retrieved Evidence Markdown -> LLM -> Answer` の形へ差し替えやすくします。

また、最終的にコード提出が必要になるため、入力ファイル、ハッシュ、パラメータ、出力ファイル、再実行手順を `manifest.json` に保存します。これにより、提出用パイプラインに移す際も、データ作成の流れを追跡できます。

## 手法

- 入力: `EDA/EDA006/tables/valid_llm_readiness.csv`
- 入力: `EDA/EDA006/tables/valid_top_sources.csv`
- valid各問についてTop 5件の検索根拠をMarkdown化
- 1根拠あたり最大 1800 文字に制限
- メタ行や重複しやすいノイズ行を軽く除去
- LLM呼び出し、外部送信、提出ファイル作成は行わない

## 全体サマリ

- validコンテキスト数: 30
- ready_for_llmコンテキスト数: 10
- 平均コンテキスト文字数: 1645.1
- manifest: `EDA/EDA007/manifest.json`

## 文脈品質別コンテキスト数

| context_quality_for_llm | context_count |
| --- | --- |
| ready_for_llm | 10 |
| needs_table_tool | 8 |
| needs_better_retrieval | 8 |
| needs_format_extraction | 2 |
| needs_image_ocr | 1 |
| needs_diff_tool | 1 |

凡例: `context_quality_for_llm` はEDA006のLLM文脈品質分類、`context_count` は生成したMarkdownコンテキスト数を表します。

## 必要能力別コンテキスト数

| required_capability | context_count |
| --- | --- |
| document_qa | 16 |
| table_tool | 7 |
| format_extraction | 2 |
| code_reading | 2 |
| table_tool, image_ocr | 1 |
| diff_tool, document_qa | 1 |
| table_tool, document_qa | 1 |

凡例: `required_capability` は質問に答えるために必要そうな汎用能力、`context_count` は生成したMarkdownコンテキスト数を表します。

## コンテキスト品質サンプル

| index | context_quality_for_llm | required_capability | answer_hit_top5 | evidence_count | context_chars | removed_noise_lines | truncated_chars | context_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | needs_format_extraction | format_extraction | False | 5 | 1733 | 2 | 0 | EDA/EDA007/contexts/valid_000_context.md |
| 1 | needs_image_ocr | table_tool, image_ocr | False | 5 | 1816 | 0 | 0 | EDA/EDA007/contexts/valid_001_context.md |
| 2 | ready_for_llm | document_qa | True | 5 | 1794 | 1 | 0 | EDA/EDA007/contexts/valid_002_context.md |
| 3 | needs_table_tool | table_tool | False | 5 | 1642 | 1 | 0 | EDA/EDA007/contexts/valid_003_context.md |
| 4 | ready_for_llm | code_reading | True | 4 | 1452 | 0 | 0 | EDA/EDA007/contexts/valid_004_context.md |
| 5 | ready_for_llm | document_qa | True | 5 | 1746 | 2 | 0 | EDA/EDA007/contexts/valid_005_context.md |
| 6 | needs_table_tool | table_tool | False | 5 | 1792 | 1 | 0 | EDA/EDA007/contexts/valid_006_context.md |
| 7 | needs_table_tool | table_tool | False | 5 | 1169 | 2 | 0 | EDA/EDA007/contexts/valid_007_context.md |
| 8 | needs_better_retrieval | document_qa | False | 5 | 1822 | 0 | 0 | EDA/EDA007/contexts/valid_008_context.md |
| 9 | needs_diff_tool | diff_tool, document_qa | False | 5 | 1760 | 2 | 0 | EDA/EDA007/contexts/valid_009_context.md |
| 10 | needs_table_tool | table_tool, document_qa | False | 5 | 1773 | 1 | 0 | EDA/EDA007/contexts/valid_010_context.md |
| 11 | needs_table_tool | table_tool | False | 5 | 1793 | 1 | 0 | EDA/EDA007/contexts/valid_011_context.md |
| 12 | ready_for_llm | document_qa | True | 5 | 1762 | 0 | 0 | EDA/EDA007/contexts/valid_012_context.md |
| 13 | needs_table_tool | table_tool | False | 3 | 749 | 1 | 0 | EDA/EDA007/contexts/valid_013_context.md |
| 14 | needs_better_retrieval | document_qa | False | 5 | 1801 | 1 | 0 | EDA/EDA007/contexts/valid_014_context.md |
| 15 | needs_better_retrieval | document_qa | False | 5 | 1816 | 0 | 0 | EDA/EDA007/contexts/valid_015_context.md |
| 16 | needs_better_retrieval | document_qa | False | 5 | 1793 | 1 | 0 | EDA/EDA007/contexts/valid_016_context.md |
| 17 | ready_for_llm | document_qa | True | 3 | 1065 | 1 | 0 | EDA/EDA007/contexts/valid_017_context.md |
| 18 | ready_for_llm | document_qa | True | 5 | 1817 | 0 | 0 | EDA/EDA007/contexts/valid_018_context.md |
| 19 | ready_for_llm | document_qa | True | 5 | 1783 | 1 | 0 | EDA/EDA007/contexts/valid_019_context.md |
| 20 | ready_for_llm | document_qa | True | 5 | 1816 | 0 | 0 | EDA/EDA007/contexts/valid_020_context.md |
| 21 | needs_table_tool | table_tool | False | 5 | 1792 | 1 | 0 | EDA/EDA007/contexts/valid_021_context.md |
| 22 | ready_for_llm | document_qa | True | 5 | 1258 | 2 | 0 | EDA/EDA007/contexts/valid_022_context.md |
| 23 | needs_format_extraction | format_extraction | False | 5 | 1818 | 0 | 0 | EDA/EDA007/contexts/valid_023_context.md |
| 24 | needs_better_retrieval | document_qa | False | 5 | 1815 | 0 | 0 | EDA/EDA007/contexts/valid_024_context.md |
| 25 | needs_better_retrieval | document_qa | False | 5 | 1821 | 0 | 0 | EDA/EDA007/contexts/valid_025_context.md |
| 26 | needs_table_tool | table_tool | False | 3 | 1089 | 0 | 0 | EDA/EDA007/contexts/valid_026_context.md |
| 27 | needs_better_retrieval | document_qa | False | 4 | 1452 | 0 | 0 | EDA/EDA007/contexts/valid_027_context.md |
| 28 | needs_better_retrieval | code_reading | False | 5 | 1817 | 0 | 0 | EDA/EDA007/contexts/valid_028_context.md |
| 29 | ready_for_llm | document_qa | True | 5 | 1797 | 1 | 0 | EDA/EDA007/contexts/valid_029_context.md |

凡例: `evidence_count` はMarkdownに含めた根拠数、`context_chars` は根拠本文の文字数、`removed_noise_lines` は除去したメタ行数、`truncated_chars` は文字数上限で切り落とした文字数を表します。

## 考察

EDA007で作成したMarkdownコンテキストは、LLM導入時の入力テンプレートとして使えます。`ready_for_llm` の問題では、このコンテキストをLLMに渡して短い回答を生成するだけで改善できる可能性があります。

一方で、`needs_table_tool`、`needs_format_extraction`、`needs_image_ocr`、`needs_diff_tool` は、Markdown整形だけでは根拠が不足する可能性があります。これらは表計算、書式抽出、画像読み取り、差分比較の専用処理と組み合わせる必要があります。

## 次にやること

1. `ready_for_llm` のvalidコンテキストに対して、LLM回答生成を試す。
2. LLMを使う場合は、モデル名、プロンプト、入力コンテキスト、出力回答をログに保存する。
3. `needs_table_tool` 向けにCSV/XLSX直接集計処理を作る。
4. 提出用コード化では、manifestに記録した入力・処理順・出力を再現できるように整理する。