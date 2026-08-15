# EDA033: EDA032候補をLLMで最終回答へ整形

## 背景と目的

EDA032では、validで正解できていなかった25件に対して、構造化データから回答候補を一括生成した。
EDA033では、その候補をOpenRouter LLMへ渡し、提出用の短い回答へ整形したときにvalid goldへどれだけ近づくかを確認する。

goldはプロンプトに含めず、評価にのみ使う。

## 実行設定

- 入力: `EDA/EDA032/tables/structured_candidate_answers.csv`
- 対象: 25件
- モデル候補: `openai/gpt-oss-120b:free, openai/gpt-oss-20b:free, qwen/qwen3-next-80b-a3b-instruct:free, deepseek/deepseek-chat-v3-0324:free`
- max_tokens: 600
- temperature: 0.0
- sleep_sec: 1.0

## 結果

- 対象件数: 25
- LLM回答取得件数: 25
- LLM回答のgold類似件数: 24
- EDA032候補のgold類似件数: 24

## route別結果

凡例: `count` は対象件数、`llm_match_count` はLLM回答のgold類似件数、`candidate_match_count` はEDA032候補のgold類似件数を表す。

| route                  |   count |   llm_match_count |   candidate_match_count |
|:-----------------------|--------:|------------------:|------------------------:|
| table_calculation      |       7 |                 6 |                       6 |
| document_whole_context |       5 |                 5 |                       5 |
| fallback_bm25_llm      |       5 |                 5 |                       5 |
| code_reading           |       4 |                 4 |                       4 |
| format_extraction      |       2 |                 2 |                       2 |
| diff_check             |       1 |                 1 |                       1 |
| image_ocr              |       1 |                 1 |                       1 |

## 質問別結果

凡例: `selected_model` は採用した回答のモデル、`status` はHTTPステータス、`llm_answer` はLLM整形後の回答、`candidate_answer` はEDA032候補、`gold_answer` はvalid正解、`llm_match` はLLM回答のgold類似判定、`candidate_match` はEDA032候補のgold類似判定を表す。

|   index | route                  | selected_model           |   status | llm_answer                                                                             | candidate_answer                                                                       | gold_answer                                                                            | llm_match   | candidate_match   |
|--------:|:-----------------------|:-------------------------|---------:|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:------------|:------------------|
|       0 | format_extraction      | openai/gpt-oss-20b:free  |      200 | hr、weekday、weathersit、temp                                                             | hr、weekday、weathersit、temp                                                             | hr、weekday、weathersit、temp                                                             | True        | True              |
|       1 | image_ocr              | openai/gpt-oss-20b:free  |      200 | 20日                                                                                    | 20日                                                                                    | 20日                                                                                    | True        | True              |
|       2 | document_whole_context | openai/gpt-oss-20b:free  |      200 | Recall                                                                                 | Recall                                                                                 | Recall                                                                                 | True        | True              |
|       3 | table_calculation      | openai/gpt-oss-20b:free  |      200 | 4,384,250円                                                                             | 4,384,250円                                                                             | 4,394,250円                                                                             | False       | False             |
|       4 | code_reading           | openai/gpt-oss-20b:free  |      200 | hist_gradient_boosting                                                                 | hist_gradient_boosting                                                                 | hist_gradient_boosting                                                                 | True        | True              |
|       6 | table_calculation      | openai/gpt-oss-20b:free  |      200 | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | True        | True              |
|       7 | table_calculation      | openai/gpt-oss-20b:free  |      200 | 32歳                                                                                    | 32歳                                                                                    | 32歳                                                                                    | True        | True              |
|       9 | diff_check             | openai/gpt-oss-20b:free  |      200 | QAレビューア:池田 直哉 → 小林 直樹                                                                  | QAレビューア:池田 直哉 → 小林 直樹                                                                  | QAレビューア：池田 直哉 → 小林 直樹                                                                  | True        | True              |
|      10 | document_whole_context | openai/gpt-oss-20b:free  |      200 | 0値の疑似欠損                                                                                | 0値の疑似欠損                                                                                | 0値の疑似欠損                                                                                | True        | True              |
|      11 | table_calculation      | openai/gpt-oss-20b:free  |      200 | Gender=Male、Country=India、target=2                                                     | Gender=Male、Country=India、target=2                                                     | Gender=Male、Country=India、target=2                                                     | True        | True              |
|      12 | fallback_bm25_llm      | openai/gpt-oss-20b:free  |      200 | 5,775,000円                                                                             | 5,775,000円                                                                             | 5,775,000円                                                                             | True        | True              |
|      13 | table_calculation      | openai/gpt-oss-20b:free  |      200 | 1526                                                                                   | 1526                                                                                   | 1526                                                                                   | True        | True              |
|      14 | fallback_bm25_llm      | openai/gpt-oss-20b:free  |      200 | アサインされていない                                                                             | アサインされていない                                                                             | アサインされていない                                                                             | True        | True              |
|      15 | fallback_bm25_llm      | openai/gpt-oss-20b:free  |      200 | MINAMINO、SHR、AYM                                                                       | MINAMINO、SHR、AYM                                                                       | MINAMINO、SHR、AYM                                                                       | True        | True              |
|      16 | fallback_bm25_llm      | openai/gpt-oss-120b:free |      200 | 43日                                                                                    | 43日                                                                                    | 43日                                                                                    | True        | True              |
|      17 | document_whole_context | openai/gpt-oss-20b:free  |      200 | 未連絡                                                                                    | 未連絡                                                                                    | 未連絡                                                                                    | True        | True              |
|      20 | fallback_bm25_llm      | openai/gpt-oss-20b:free  |      200 | T09、T08、T10、T11、T12                                                                    | T09、T08、T10、T07、T11、T12                                                                | T09、T10、T11、T12                                                                        | True        | True              |
|      21 | table_calculation      | openai/gpt-oss-20b:free  |      200 | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | True        | True              |
|      22 | code_reading           | openai/gpt-oss-20b:free  |      200 | season                                                                                 | season                                                                                 | season                                                                                 | True        | True              |
|      23 | format_extraction      | openai/gpt-oss-20b:free  |      200 | 見込金額(税込): 4,675,000 JPY                                                                | 見込金額(税込): 4,675,000 JPY                                                                | 見込金額（税込）: 4,675,000 JPY                                                                | True        | True              |
|      24 | code_reading           | openai/gpt-oss-20b:free  |      200 | Attr7                                                                                  | Attr7                                                                                  | Attr7                                                                                  | True        | True              |
|      25 | document_whole_context | openai/gpt-oss-20b:free  |      200 | 1. データ理解・EDA                                                                           | 1. データ理解・EDA                                                                           | 1. データ理解・EDA                                                                           | True        | True              |
|      26 | table_calculation      | openai/gpt-oss-20b:free  |      200 | train_0077、train_0216、train_0242、train_0722                                            | train_0077、train_0216、train_0242、train_0722                                            | train_0077、train_0216、train_0242、train_0722                                            | True        | True              |
|      27 | document_whole_context | openai/gpt-oss-20b:free  |      200 | 0.010301                                                                               | 0.010301                                                                               | 0.010301                                                                               | True        | True              |
|      28 | code_reading           | openai/gpt-oss-20b:free  |      200 | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。             | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。             | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。             | True        | True              |

## HTTPステータス別試行数

凡例: `status` はOpenRouter HTTPステータス、`count` は試行回数を表す。

|   status |   count |
|---------:|--------:|
|      200 |      25 |
|      429 |      24 |

## モデル別試行数

凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`count` は試行回数を表す。

| model                    |   status |   count |
|:-------------------------|---------:|--------:|
| openai/gpt-oss-120b:free |      200 |       1 |
| openai/gpt-oss-120b:free |      429 |      24 |
| openai/gpt-oss-20b:free  |      200 |      24 |

## 所感

EDA032候補が十分に正しい場合、LLMは最終回答の整形役として使える。
一方で、候補が既に提出形式に近い場合、LLMを通すことで表記が変わるリスクもある。
提出用パイプラインでは、routeごとに「ローカル候補を直接採用するか」「LLM整形を通すか」をvalidで比較して決める。
