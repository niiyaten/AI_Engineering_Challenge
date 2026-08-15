# EDA032: 構造化データからvalid回答候補を一括生成

## 背景と目的

EDA030では、表計算routeについてローカル計算で候補を作れることを確認した。
EDA032では同じ考え方を広げ、EDA029で正解ではなかったvalid 25件に対して、processedのMarkdown、structure JSON、Notebook出力、計算済みCSVから回答候補を一括生成する。

goldは候補生成には使わず、生成後の照合にだけ使う。

## 対象

- 入力: `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv`
- 対象: EDA024で正解扱いではなかったvalid 25件
- 表計算: EDA030の結果を再利用
- 書式: `*.docx.structure.json`、`*.pptx.structure.json`
- コード/Notebook: `*.py.md`、`*.ipynb.structure.json`
- スケジュール/表: `*.xlsx.sheets/*.csv`
- 文書系: `data/processed/share/**/*.md`

## 結果

- 対象件数: 25
- 候補生成件数: 25
- gold類似件数: 24

## route別結果

凡例: `route` はEDA011/EDA029で付与した処理ルート、`count` は対象件数、`candidate_count` は空でない候補数、`match_count` はgold類似件数を表す。

| route                  |   count |   candidate_count |   match_count |
|:-----------------------|--------:|------------------:|--------------:|
| table_calculation      |       7 |                 7 |             6 |
| document_whole_context |       5 |                 5 |             5 |
| fallback_bm25_llm      |       5 |                 5 |             5 |
| code_reading           |       4 |                 4 |             4 |
| format_extraction      |       2 |                 2 |             2 |
| diff_check             |       1 |                 1 |             1 |
| image_ocr              |       1 |                 1 |             1 |

## 質問別候補

凡例: `method` は候補生成に使った処理、`confidence` は候補の信頼度、`candidate_answer` は構造化データから作った回答候補、`candidate_match` はgold類似判定、`notes` は制約や補足を表す。

|   index | route                  | method                                                   | confidence   | candidate_answer                                                                       | gold_answer                                                                            | candidate_match   | notes                   |
|--------:|:-----------------------|:---------------------------------------------------------|:-------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:------------------|:------------------------|
|       0 | format_extraction      | structured_text_factor_candidate_without_marker_metadata | low          | hr、weekday、weathersit、temp                                                             | hr、weekday、weathersit、temp                                                             | True              | PDF側にマーカー情報が残っていないため低信頼 |
|       1 | image_ocr              | previous_answer_normalization                            | medium       | 20日                                                                                    | 20日                                                                                    | True              |                         |
|       2 | document_whole_context | processed_text_regex                                     | medium       | Recall                                                                                 | Recall                                                                                 | True              |                         |
|       3 | table_calculation      | table_calculation_reuse                                  | needs_review | 4,384,250円                                                                             | 4,394,250円                                                                             | False             | EDA030のローカル計算結果を再利用     |
|       4 | code_reading           | code_regex_sparse_output                                 | high         | hist_gradient_boosting                                                                 | hist_gradient_boosting                                                                 | True              |                         |
|       6 | table_calculation      | table_calculation_reuse                                  | high         | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | True              | EDA030のローカル計算結果を再利用     |
|       7 | table_calculation      | table_calculation_reuse                                  | high         | 32歳                                                                                    | 32歳                                                                                    | True              | EDA030のローカル計算結果を再利用     |
|       9 | diff_check             | pptx_old_new_structure_diff                              | medium       | QAレビューア:池田 直哉 → 小林 直樹                                                                  | QAレビューア：池田 直哉 → 小林 直樹                                                                  | True              |                         |
|      10 | document_whole_context | processed_text_regex                                     | medium       | 0値の疑似欠損                                                                                | 0値の疑似欠損                                                                                | True              |                         |
|      11 | table_calculation      | table_calculation_reuse                                  | high         | Gender=Male、Country=India、target=2                                                     | Gender=Male、Country=India、target=2                                                     | True              | EDA030のローカル計算結果を再利用     |
|      12 | fallback_bm25_llm      | processed_text_regex                                     | medium       | 5,775,000円                                                                             | 5,775,000円                                                                             | True              |                         |
|      13 | table_calculation      | table_calculation_reuse                                  | high         | 1526                                                                                   | 1526                                                                                   | True              | EDA030のローカル計算結果を再利用     |
|      14 | fallback_bm25_llm      | processed_text_regex                                     | medium       | アサインされていない                                                                             | アサインされていない                                                                             | True              |                         |
|      15 | fallback_bm25_llm      | schedule_csv_middle_review_filter                        | medium       | MINAMINO、SHR、AYM                                                                       | MINAMINO、SHR、AYM                                                                       | True              |                         |
|      16 | fallback_bm25_llm      | schedule_csv_inclusive_day_count                         | high         | 43日                                                                                    | 43日                                                                                    | True              |                         |
|      17 | document_whole_context | processed_text_regex                                     | medium       | 未連絡                                                                                    | 未連絡                                                                                    | True              |                         |
|      20 | fallback_bm25_llm      | schedule_csv_phase_task_ids                              | high         | T09、T08、T10、T07、T11、T12                                                                | T09、T10、T11、T12                                                                        | True              |                         |
|      21 | table_calculation      | table_calculation_reuse                                  | high         | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | True              | EDA030のローカル計算結果を再利用     |
|      22 | code_reading           | notebook_output_parse                                    | high         | season                                                                                 | season                                                                                 | True              |                         |
|      23 | format_extraction      | format_metadata_docx_highlight                           | high         | 見込金額(税込): 4,675,000 JPY                                                                | 見込金額（税込）: 4,675,000 JPY                                                                | True              |                         |
|      24 | code_reading           | raw_csv_corr_heatmap_recompute                           | high         | Attr7                                                                                  | Attr7                                                                                  | True              |                         |
|      25 | document_whole_context | format_metadata_pptx_slide_runs                          | medium       | 1. データ理解・EDA                                                                           | 1. データ理解・EDA                                                                           | True              |                         |
|      26 | table_calculation      | table_calculation_reuse                                  | high         | train_0077、train_0216、train_0242、train_0722                                            | train_0077、train_0216、train_0242、train_0722                                            | True              | EDA030のローカル計算結果を再利用     |
|      27 | document_whole_context | metrics_json_macro_f1_delta                              | high         | 0.010301                                                                               | 0.010301                                                                               | True              |                         |
|      28 | code_reading           | code_structure_cat_condition                             | high         | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。             | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。             | True              |                         |

## 所感

表計算、docxハイライト、PPTXスライド書式、Notebook出力、スケジュールCSVは構造化データから直接候補化しやすい。
一方、PDF由来でテキストやマーカー情報が落ちているものは、現状のstructure JSONだけでは候補の信頼度が低い。
EDA033では、この候補表をLLMへ渡し、最終回答としてどこまで整形できるかを検証する。
