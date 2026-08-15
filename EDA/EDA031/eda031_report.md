# EDA031: 表計算結果をLLMで最終回答へ整形する検証

## 背景と目的

EDA030では、validの表計算系7件に対して、pandas/openpyxlで計算できるかを確認した。
EDA031では、その計算結果をOpenRouter LLMへ渡し、LLMが提出用の短い回答へ整形できるかを検証する。

重要な点として、validの `gold_answer` はプロンプトには含めない。goldは実行後の評価にだけ使う。

## 実行設定

- 入力: `EDA/EDA030/tables/table_valid_calculation_results.csv`
- 対象: EDA030の表計算7件
- モデル候補: `openai/gpt-oss-120b:free, openai/gpt-oss-20b:free, qwen/qwen3-next-80b-a3b-instruct:free, deepseek/deepseek-chat-v3-0324:free, tencent/hy3:free, poolside/laguna-xs-2.1:free, cohere/north-mini-code:free, nvidia/nemotron-3.5-content-safety:free`
- OpenRouter無料モデル追加取得: `ok`
- max_tokens: 500
- temperature: 0.0
- sleep_sec: 1.0

## 結果

- 対象質問数: 7
- LLM回答取得数: 7
- goldに近い回答数: 6
- EDA030の計算回答に近い回答数: 7

## 質問別結果

凡例: `selected_model` は最終的に採用した回答のモデル、`status` はHTTPステータス、`llm_answer` はLLMの回答、`computed_answer` はEDA030のローカル計算結果、`gold_answer` はvalid正解、`similar_to_gold` は表記ゆれを少し許したgold類似判定、`similar_to_computed` はローカル計算結果との類似判定を表す。

|   index | selected_model          |   status | llm_answer                                                                                | computed_answer                                                                        | gold_answer                                                                            | similar_to_gold   | similar_to_computed   |
|--------:|:------------------------|---------:|:------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:------------------|:----------------------|
|       3 | openai/gpt-oss-20b:free |      200 | 4,384,250円                                                                                | 4,384,250円                                                                             | 4,394,250円                                                                             | False             | True                  |
|       6 | openai/gpt-oss-20b:free |      200 | Gender=Male、disease=1、Age=68                                                              | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | True              | True                  |
|       7 | openai/gpt-oss-20b:free |      200 | 32歳                                                                                       | 32歳                                                                                    | 32歳                                                                                    | True              | True                  |
|      11 | openai/gpt-oss-20b:free |      200 | Gender=Male, Country=India, target=2                                                      | Gender=Male、Country=India、target=2                                                     | Gender=Male、Country=India、target=2                                                     | True              | True                  |
|      13 | openai/gpt-oss-20b:free |      200 | 1526                                                                                      | 1526                                                                                   | 1526                                                                                   | True              | True                  |
|      21 | openai/gpt-oss-20b:free |      200 | Attrition = No, Gender = Female, MaritalStatus = Single, EducationField = Human Resources | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | True              | True                  |
|      26 | openai/gpt-oss-20b:free |      200 | train_0077, train_0216, train_0242, train_0722                                            | train_0077、train_0216、train_0242、train_0722                                            | train_0077、train_0216、train_0242、train_0722                                            | True              | True                  |

## HTTPステータス別試行数

凡例: `status` はOpenRouterのHTTPステータス、`count` は試行回数を表す。`0` はHTTP応答前の接続エラーやタイムアウトを表す。

|   status |   count |
|---------:|--------:|
|      200 |       7 |
|      429 |       7 |

## モデル別試行数

凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`count` は試行回数を表す。

| model                    |   status |   count |
|:-------------------------|---------:|--------:|
| openai/gpt-oss-120b:free |      429 |       7 |
| openai/gpt-oss-20b:free  |      200 |       7 |

## 所感

この実験は、表計算そのものをLLMに任せるのではなく、ローカル計算で得た値をLLMに最終回答として整形させる構成の検証である。
goldに近い回答が増える場合、提出用パイプラインでは `table_calculation` routeだけ先にローカル計算し、その結果をLLMへ渡す方針が有効と判断できる。
一方、LLMが計算済み回答を崩す、余計な説明を足す、またはAPI制限で失敗する場合は、表計算routeではLLMを使わずローカル計算結果を直接採用する方が安定する。
