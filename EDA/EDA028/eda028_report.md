# EDA028: EDA024 valid回答の質問系統別分類

## 目的

EDA024のvalid 30問について、正解したもの、`わかりません` になったもの、間違ったものを質問系統ごとに分類する。valid正解は分類評価にのみ使い、回答生成には使わない。

## 入力

- EDA024回答ログ: `EDA/EDA024/tables/valid_llm_answer_log.csv`

## 出力

- 質問別分類: `EDA/EDA028/tables/eda024_valid_answer_classification.csv`
- route別集計: `EDA/EDA028/tables/eda024_route_classification_summary.csv`
- bucket別集計: `EDA/EDA028/tables/eda024_bucket_summary.csv`
- next_action別集計: `EDA/EDA028/tables/eda024_next_action_summary.csv`

## 全体指標

凡例: `metric` は診断指標、`value` は値を表します。

| metric | value |
| --- | --- |
| valid_question_count | 30 |
| correct_count | 5 |
| near_correct_count | 5 |
| correct_or_near_correct_count | 10 |
| unknown_count | 14 |
| wrong_count | 6 |
| partial_or_over_answer_count | 4 |
| answer_in_topk_context_count | 7 |

## route別分類

凡例: `route` は質問系統、`question_count` はvalid質問数、`correct_count` は完全一致数、`near_correct_count` は表記・単位・過不足はあるが近い回答数、`unknown_count` は不明回答数、`wrong_count` は近似正解でも不明でもない回答数を表します。

| route | question_count | correct_count | near_correct_count | unknown_count | wrong_count | partial_or_over_answer_count | answer_extraction_error_count | wrong_evidence_or_missing_process_count | answer_in_topk_context_count | avg_token_recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code_reading | 4 | 0 | 0 | 2 | 2 | 0 | 0 | 1 | 0 | 0.0304 |
| diff_check | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0.0 |
| document_whole_context | 7 | 2 | 2 | 2 | 1 | 2 | 0 | 1 | 4 | 0.5714 |
| fallback_bm25_llm | 8 | 3 | 2 | 3 | 0 | 1 | 0 | 0 | 3 | 0.5312 |
| format_extraction | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0.0 |
| image_ocr | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0.5 |
| table_calculation | 7 | 0 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0.0516 |

## 診断bucket別件数

凡例: `diagnostic_bucket` は回答失敗の診断分類、`count` は件数を表します。

| diagnostic_bucket | count |
| --- | --- |
| unknown_answer | 14 |
| correct_exact | 5 |
| partial_or_over_answer | 4 |
| weak_overlap_wrong | 3 |
| wrong_evidence_or_missing_process | 3 |
| format_normalization_needed | 1 |

## 次アクション別件数

凡例: `next_action` は次に優先する改善作業、`count` は該当質問数を表します。

| next_action | count |
| --- | --- |
| implement_local_table_calculation | 7 |
| keep | 5 |
| tighten_final_answer_format | 4 |
| improve_code_notebook_retrieval | 4 |
| tighten_document_selection | 3 |
| improve_retrieval_context | 3 |
| use_format_metadata_json | 2 |
| build_document_diff_pipeline | 1 |
| normalize_units_and_symbols | 1 |

## 質問別分類

凡例: `index` はvalid質問番号、`route` は質問系統、`broad_bucket` は `correct`、`near_correct`、`unknown`、`wrong` の大分類、`diagnostic_bucket` は詳細分類、`next_action` は改善方針、`gold_answer` は正解、`llm_answer` はEDA024のLLM回答を表します。

| index | route | broad_bucket | diagnostic_bucket | next_action | gold_answer | llm_answer |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | format_extraction | unknown | unknown_answer | use_format_metadata_json | hr、weekday、weathersit、temp | わかりません |
| 1 | image_ocr | near_correct | partial_or_over_answer | tighten_final_answer_format | 20日 | 20 |
| 2 | document_whole_context | near_correct | partial_or_over_answer | tighten_final_answer_format | Recall | Recall, Precision, F1‑score, ROC‑AUC, Accuracy |
| 3 | table_calculation | wrong | weak_overlap_wrong | implement_local_table_calculation | 4,394,250円 | 1875000円 |
| 4 | code_reading | unknown | unknown_answer | improve_code_notebook_retrieval | hist_gradient_boosting | わかりません |
| 5 | document_whole_context | correct | correct_exact | keep | 対象外（契約明記） | 対象外（契約明記） |
| 6 | table_calculation | unknown | unknown_answer | implement_local_table_calculation | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | わかりません |
| 7 | table_calculation | unknown | unknown_answer | implement_local_table_calculation | 32歳 | わかりません |
| 8 | fallback_bm25_llm | correct | correct_exact | keep | 1,168,750円 | 1,168,750円 |
| 9 | diff_check | wrong | wrong_evidence_or_missing_process | build_document_diff_pipeline | QAレビューア：池田 直哉 → 小林 直樹 | 変更なし |
| 10 | document_whole_context | unknown | unknown_answer | tighten_document_selection | 0値の疑似欠損 | わかりません |
| 11 | table_calculation | unknown | unknown_answer | implement_local_table_calculation | Gender=Male、Country=India、target=2 | わかりません |
| 12 | fallback_bm25_llm | near_correct | format_normalization_needed | normalize_units_and_symbols | 5,775,000円 | ¥5,775,000 |
| 13 | table_calculation | unknown | unknown_answer | implement_local_table_calculation | 1526 | わかりません |
| 14 | fallback_bm25_llm | unknown | unknown_answer | improve_retrieval_context | アサインされていない | わかりません |
| 15 | fallback_bm25_llm | unknown | unknown_answer | improve_retrieval_context | MINAMINO、SHR、AYM | わかりません |
| 16 | fallback_bm25_llm | unknown | unknown_answer | improve_retrieval_context | 43日 | わかりません |
| 17 | document_whole_context | near_correct | partial_or_over_answer | tighten_final_answer_format | 未連絡 | 未連絡を表します。 |
| 18 | fallback_bm25_llm | correct | correct_exact | keep | 3 | 3 |
| 19 | fallback_bm25_llm | correct | correct_exact | keep | 渡辺 遥 | 渡辺 遥 |
| 20 | fallback_bm25_llm | near_correct | partial_or_over_answer | tighten_final_answer_format | T09、T10、T11、T12 | T09, T10 |
| 21 | table_calculation | wrong | weak_overlap_wrong | implement_local_table_calculation | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | MaritalStatus = Divorced |
| 22 | code_reading | unknown | unknown_answer | improve_code_notebook_retrieval | season | わかりません |
| 23 | format_extraction | unknown | unknown_answer | use_format_metadata_json | 見込金額（税込）: 4,675,000 JPY | わかりません |
| 24 | code_reading | wrong | wrong_evidence_or_missing_process | improve_code_notebook_retrieval | Attr7 | Attr14 |
| 25 | document_whole_context | unknown | unknown_answer | tighten_document_selection | 1. データ理解・EDA | わかりません |
| 26 | table_calculation | unknown | unknown_answer | implement_local_table_calculation | train_0077、train_0216、train_0242、train_0722 | わかりません |
| 27 | document_whole_context | wrong | wrong_evidence_or_missing_process | tighten_document_selection | 0.010301 | 0.010310 |
| 28 | code_reading | wrong | weak_overlap_wrong | improve_code_notebook_retrieval | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 | cat_cols = [c for c in df.columns if df[c].dtype == 'object' or str(df[c].dtype) == 'category'] その後、各cに対してユニーク数を df[c].nunique(dropna=True) で算出し、必要に応じて高カードリストに格納する。 |
| 29 | document_whole_context | correct | correct_exact | keep | 3年間 | 3年間 |

## 結論

- EDA024の完全一致は5件、近似正解は5件、不明回答は14件、明確な誤答は6件だった。
- 完全一致と近似正解を合わせると10件で、完全一致だけを見るよりEDA024の有効性は少し高い。
- 近似正解5件のうち4件は、正解語句を含むが余計な語がある、または単位などが不足した回答だった。
- `document_whole_context` と `fallback_bm25_llm` は完全一致が出ており、文書選択と回答形式を整える余地がある。
- `table_calculation`、`format_extraction`、`diff_check`、`code_reading` は完全一致がなく、LLMへ投げる前のroute別処理が必要である。
- 次に優先するのは、`table_calculation` のローカル計算、`format_extraction` の書式JSON利用、`diff_check` の文書差分処理である。
