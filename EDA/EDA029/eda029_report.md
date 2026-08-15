# EDA029: 不明・誤答・近似正解の原因データ種別診断

## 目的

EDA028で `correct` ではなかったvalid質問を対象に、必要な元データ種別、失敗領域、次に直すべき処理を分類する。これにより、CSVだけを見直すべきか、Excel、PowerPoint、Word、コード、画像、差分処理を見直すべきかを判断する。

## 入力

- EDA028分類表: `EDA/EDA028/tables/eda024_valid_answer_classification.csv`

## 出力

- 質問別原因診断: `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv`
- データ種別別集計: `EDA/EDA029/tables/source_type_summary.csv`
- 失敗領域別集計: `EDA/EDA029/tables/failure_area_summary.csv`
- 次修正別集計: `EDA/EDA029/tables/next_fix_summary.csv`
- outcome別データ種別集計: `EDA/EDA029/tables/source_type_by_outcome_summary.csv`

## 全体指標

凡例: `metric` は診断指標、`value` は値を表します。

| metric | value |
| --- | --- |
| diagnosis_target_count | 25 |
| unknown_count | 14 |
| wrong_count | 6 |
| near_correct_count | 5 |

## 必要データ種別別集計

凡例: `required_source_type` は回答に必要な主なデータ種別、`count` は件数を表します。

| required_source_type | count |
| --- | --- |
| pptx | 6 |
| docx | 5 |
| py_or_ipynb | 4 |
| csv | 3 |
| image | 2 |
| xlsx_pivot | 2 |
| xlsx | 2 |
| pptx_or_docx_versions | 1 |

## 失敗領域別集計

凡例: `failure_area` は改善が必要な処理領域、`count` は件数を表します。

| failure_area | count |
| --- | --- |
| calculation | 7 |
| target_retrieval | 6 |
| answer_formatting | 5 |
| code_retrieval_or_output_extraction | 4 |
| format_metadata_extraction | 2 |
| diff_pipeline | 1 |

## 次修正別集計

凡例: `next_fix` は次に実装・改善すべき処理、`count` は件数を表します。

| next_fix | count |
| --- | --- |
| improve_project_document_targeting | 6 |
| normalize_final_answer | 5 |
| target_py_ipynb_by_filename_then_extract | 4 |
| implement_pandas_csv_calculation | 3 |
| query_structure_json_format_runs | 2 |
| implement_tabular_calculation_router | 2 |
| read_xlsx_pivot_or_recompute_from_sheet | 2 |
| compare_old_new_documents | 1 |

## outcome別データ種別

凡例: `outcome` はEDA028の分類、`required_source_type` は必要データ種別、`count` は件数を表します。

| outcome | required_source_type | count |
| --- | --- | --- |
| unknown | pptx | 4 |
| unknown | csv | 3 |
| near_correct | docx | 3 |
| unknown | py_or_ipynb | 2 |
| unknown | xlsx | 2 |
| wrong | py_or_ipynb | 2 |
| near_correct | image | 1 |
| near_correct | pptx | 1 |
| wrong | docx | 1 |
| unknown | xlsx_pivot | 1 |
| wrong | pptx_or_docx_versions | 1 |
| unknown | docx | 1 |
| unknown | image | 1 |
| wrong | xlsx_pivot | 1 |
| wrong | pptx | 1 |

## 質問別原因診断

凡例: `index` はvalid質問番号、`route` は質問系統、`outcome` はEDA028分類、`required_source_type` は必要データ種別、`failure_area` は失敗領域、`next_fix` は次修正、`gold_answer` は正解、`llm_answer` はEDA024回答を表します。

| index | route | outcome | required_source_type | failure_area | next_fix | gold_answer | llm_answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | format_extraction | unknown | pptx | format_metadata_extraction | query_structure_json_format_runs | hr、weekday、weathersit、temp | わかりません |
| 1 | image_ocr | near_correct | image | answer_formatting | normalize_final_answer | 20日 | 20 |
| 2 | document_whole_context | near_correct | pptx | answer_formatting | normalize_final_answer | Recall | Recall, Precision, F1‑score, ROC‑AUC, Accuracy |
| 3 | table_calculation | wrong | docx | calculation | implement_tabular_calculation_router | 4,394,250円 | 1875000円 |
| 4 | code_reading | unknown | py_or_ipynb | code_retrieval_or_output_extraction | target_py_ipynb_by_filename_then_extract | hist_gradient_boosting | わかりません |
| 6 | table_calculation | unknown | xlsx_pivot | calculation | read_xlsx_pivot_or_recompute_from_sheet | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | わかりません |
| 7 | table_calculation | unknown | csv | calculation | implement_pandas_csv_calculation | 32歳 | わかりません |
| 9 | diff_check | wrong | pptx_or_docx_versions | diff_pipeline | compare_old_new_documents | QAレビューア：池田 直哉 → 小林 直樹 | 変更なし |
| 10 | document_whole_context | unknown | pptx | target_retrieval | improve_project_document_targeting | 0値の疑似欠損 | わかりません |
| 11 | table_calculation | unknown | xlsx | calculation | implement_tabular_calculation_router | Gender=Male、Country=India、target=2 | わかりません |
| 12 | fallback_bm25_llm | near_correct | docx | answer_formatting | normalize_final_answer | 5,775,000円 | ¥5,775,000 |
| 13 | table_calculation | unknown | csv | calculation | implement_pandas_csv_calculation | 1526 | わかりません |
| 14 | fallback_bm25_llm | unknown | pptx | target_retrieval | improve_project_document_targeting | アサインされていない | わかりません |
| 15 | fallback_bm25_llm | unknown | docx | target_retrieval | improve_project_document_targeting | MINAMINO、SHR、AYM | わかりません |
| 16 | fallback_bm25_llm | unknown | image | target_retrieval | improve_project_document_targeting | 43日 | わかりません |
| 17 | document_whole_context | near_correct | docx | answer_formatting | normalize_final_answer | 未連絡 | 未連絡を表します。 |
| 20 | fallback_bm25_llm | near_correct | docx | answer_formatting | normalize_final_answer | T09、T10、T11、T12 | T09, T10 |
| 21 | table_calculation | wrong | xlsx_pivot | calculation | read_xlsx_pivot_or_recompute_from_sheet | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | MaritalStatus = Divorced |
| 22 | code_reading | unknown | py_or_ipynb | code_retrieval_or_output_extraction | target_py_ipynb_by_filename_then_extract | season | わかりません |
| 23 | format_extraction | unknown | xlsx | format_metadata_extraction | query_structure_json_format_runs | 見込金額（税込）: 4,675,000 JPY | わかりません |
| 24 | code_reading | wrong | py_or_ipynb | code_retrieval_or_output_extraction | target_py_ipynb_by_filename_then_extract | Attr7 | Attr14 |
| 25 | document_whole_context | unknown | pptx | target_retrieval | improve_project_document_targeting | 1. データ理解・EDA | わかりません |
| 26 | table_calculation | unknown | csv | calculation | implement_pandas_csv_calculation | train_0077、train_0216、train_0242、train_0722 | わかりません |
| 27 | document_whole_context | wrong | pptx | target_retrieval | improve_project_document_targeting | 0.010301 | 0.010310 |
| 28 | code_reading | wrong | py_or_ipynb | code_retrieval_or_output_extraction | target_py_ipynb_by_filename_then_extract | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 | cat_cols = [c for c in df.columns if df[c].dtype == 'object' or str(df[c].dtype) == 'category'] その後、各cに対してユニーク数を df[c].nunique(dropna=True) で算出し、必要に応じて高カードリストに格納する。 |

## 結論

- 正解以外25件のうち、表データ系の改善対象が最も多い。
- `table_calculation` はCSV、Excel、PivotTable、複数文書横断集計が混在しており、単にCSV抽出だけを直せばよい状態ではない。
- 書式抽出はPowerPoint、Excel、Word/docxのstructure JSONを直接読む処理が必要である。
- 差分比較とコード読解は、検索根拠の増量ではなく、old/new比較やファイル名指定検索を実装する必要がある。
