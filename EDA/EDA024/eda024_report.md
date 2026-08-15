# EDA024: valid 30問 LLM回答生成

## 目的

EDA023でローカルRAGの限界が明確になったため、valid 30問すべてをOpenRouter LLMへ渡し、LLM回答生成でどこまで改善するか確認する。

## 出力

- answer_log: `EDA/EDA024/tables/valid_llm_answer_log.csv`
- route_summary: `EDA/EDA024/tables/valid_llm_route_summary.csv`
- prompt_debug: `EDA/EDA024/prompts`

## 実行設定

- model: `openai/gpt-oss-20b:free`
- top_k: 12
- max_context_chars: 24000
- max_tokens: 900
- temperature: 0.0

## モデル切り替えの経緯

当初は `openai/gpt-oss-120b:free` でvalid 30問すべてを試行したが、全件HTTP 429となった。短い疎通確認でも `openai/gpt-oss-120b:free is temporarily rate-limited upstream` が返ったため、120B無料モデルはこの時点では評価不能と判断した。

そのため、本レポートの結果は代替モデル `openai/gpt-oss-20b:free` で再実行したものを記録している。

## 全体指標

凡例: `metric` は診断指標、`value` は値を表します。

| metric | value |
| --- | --- |
| valid_question_count | 30 |
| http_200_count | 30 |
| exact_match_count | 5 |
| contains_gold_count | 7 |
| answer_in_topk_context_count | 7 |
| avg_token_recall | 0.3078 |

## route別診断

凡例: `route` は質問ルート、`question_count` はvalid質問数、`exact_match_count` は正規化完全一致数、`contains_gold_count` は予測文に正解が含まれた件数、`answer_in_topk_context_count` は上位検索根拠に正解文字列が含まれた件数、`avg_token_recall` は正解語句トークンの回収率平均、`success_status_200_count` はHTTP 200件数です。

| route | question_count | exact_match_count | contains_gold_count | answer_in_topk_context_count | avg_token_recall | success_status_200_count |
| --- | --- | --- | --- | --- | --- | --- |
| code_reading | 4 | 0 | 0 | 0 | 0.0304 | 4 |
| diff_check | 1 | 0 | 0 | 0 | 0.0 | 1 |
| document_whole_context | 7 | 2 | 4 | 4 | 0.5714 | 7 |
| fallback_bm25_llm | 8 | 3 | 3 | 3 | 0.5312 | 8 |
| format_extraction | 2 | 0 | 0 | 0 | 0.0 | 2 |
| image_ocr | 1 | 0 | 0 | 0 | 0.5 | 1 |
| table_calculation | 7 | 0 | 0 | 0 | 0.0516 | 7 |

## HTTP status別件数

凡例: `status` はOpenRouterのHTTPステータス、`count` は件数を表します。

| status | count |
| --- | --- |
| 200 | 30 |

## 質問別結果

凡例: `index` はvalid質問番号、`route` は処理ルート、`gold_answer` は正解、`llm_answer` はLLM回答、`exact_match` は正規化完全一致、`contains_gold` は回答に正解文字列が含まれるかを表します。

| index | route | gold_answer | llm_answer | exact_match | contains_gold |
| --- | --- | --- | --- | --- | --- |
| 0 | format_extraction | hr、weekday、weathersit、temp | わかりません | 0 | 0 |
| 1 | image_ocr | 20日 | 20 | 0 | 0 |
| 2 | document_whole_context | Recall | Recall, Precision, F1‑score, ROC‑AUC, Accuracy | 0 | 1 |
| 3 | table_calculation | 4,394,250円 | 1875000円 | 0 | 0 |
| 4 | code_reading | hist_gradient_boosting | わかりません | 0 | 0 |
| 5 | document_whole_context | 対象外（契約明記） | 対象外（契約明記） | 1 | 1 |
| 6 | table_calculation | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | わかりません | 0 | 0 |
| 7 | table_calculation | 32歳 | わかりません | 0 | 0 |
| 8 | fallback_bm25_llm | 1,168,750円 | 1,168,750円 | 1 | 1 |
| 9 | diff_check | QAレビューア：池田 直哉 → 小林 直樹 | 変更なし | 0 | 0 |
| 10 | document_whole_context | 0値の疑似欠損 | わかりません | 0 | 0 |
| 11 | table_calculation | Gender=Male、Country=India、target=2 | わかりません | 0 | 0 |
| 12 | fallback_bm25_llm | 5,775,000円 | ¥5,775,000 | 0 | 0 |
| 13 | table_calculation | 1526 | わかりません | 0 | 0 |
| 14 | fallback_bm25_llm | アサインされていない | わかりません | 0 | 0 |
| 15 | fallback_bm25_llm | MINAMINO、SHR、AYM | わかりません | 0 | 0 |
| 16 | fallback_bm25_llm | 43日 | わかりません | 0 | 0 |
| 17 | document_whole_context | 未連絡 | 未連絡を表します。 | 0 | 1 |
| 18 | fallback_bm25_llm | 3 | 3 | 1 | 1 |
| 19 | fallback_bm25_llm | 渡辺 遥 | 渡辺 遥 | 1 | 1 |
| 20 | fallback_bm25_llm | T09、T10、T11、T12 | T09, T10 | 0 | 0 |
| 21 | table_calculation | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | MaritalStatus = Divorced | 0 | 0 |
| 22 | code_reading | season | わかりません | 0 | 0 |
| 23 | format_extraction | 見込金額（税込）: 4,675,000 JPY | わかりません | 0 | 0 |
| 24 | code_reading | Attr7 | Attr14 | 0 | 0 |
| 25 | document_whole_context | 1. データ理解・EDA | わかりません | 0 | 0 |
| 26 | table_calculation | train_0077、train_0216、train_0242、train_0722 | わかりません | 0 | 0 |
| 27 | document_whole_context | 0.010301 | 0.010310 | 0 | 0 |
| 28 | code_reading | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 | cat_cols = [c for c in df.columns if df[c].dtype == 'object' or str(df[c].dtype) == 'category'] その後、各cに対してユニーク数を df[c].nunique(dropna=True) で算出し、必要に応じて高カードリストに格 | 0 | 0 |
| 29 | document_whole_context | 3年間 | 3年間 | 1 | 1 |

## 注意点

- valid正解はプロンプトには入れていない。正解は実行後の評価だけに使った。
- LLMでも、検索根拠が外れている場合は正答できないため、結果は検索品質と回答生成品質の両方を含む。
- APIキーは `.apikey` から読み込み、成果物には保存しない。
