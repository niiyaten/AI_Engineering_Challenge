# EDA034: valid改善結果をtest提出用パイプラインへ反映

## 背景と目的
EDA032/033では、validで失敗していた25件に対して、構造化データから回答候補を作り、LLMで最終回答に整える方針が有効だった。
EDA034では、その考え方を提出用の実行単位に寄せ、validではEDA024の全体回答にEDA033の改善結果を上書きし、testではEDA027の20B回答を安全側に採用して提出zipを作成した。

金額差の未解決メモ: valid index=3の消費税額は、ローカル再構成では4,384,250円、goldは4,394,250円で、差額10,000円が残っている。今回は提出パイプライン化を優先し、この差は既知課題として扱う。

## 入力
- valid基準回答: `EDA/EDA024/tables/valid_llm_answer_log.csv`
- valid構造化改善: `EDA/EDA033/tables/llm_structured_candidate_answer_log.csv`
- test 20B回答: `EDA/EDA027/tables/test_unknown_allowed_answer_log.csv`
- test BM25候補: `EDA/EDA021/predictions/predictions.csv`
- route定義: `EDA/EDA011/tables/question_routes.csv`

## 出力
- valid統合評価ログ: `EDA/EDA034/tables/valid_pipeline_answer_log.csv`
- test回答ログ: `EDA/EDA034/tables/test_pipeline_answer_log.csv`
- 提出CSV: `EDA/EDA034/predictions/predictions.csv`
- 提出zip: `EDA/EDA034/predictions/eda034_structured_safe_submission.zip`

## valid結果
- valid件数: 30
- 類似正解数: 29
- 類似正解率: 0.967

凡例: `route` は質問の処理ルート、`count` はvalid質問数、`match_count` はgold類似判定がTrueの件数を表す。

| route                  |   count |   match_count |
|:-----------------------|--------:|--------------:|
| fallback_bm25_llm      |       8 |             8 |
| document_whole_context |       7 |             7 |
| table_calculation      |       7 |             6 |
| code_reading           |       4 |             4 |
| format_extraction      |       2 |             2 |
| diff_check             |       1 |             1 |
| image_ocr              |       1 |             1 |

## test提出候補の内訳
凡例: `source_stage` は採用した回答元、`confidence` は提出時の信頼度、`count` はtest質問数を表す。

| source_stage          | confidence   |   count |
|:----------------------|:-------------|--------:|
| eda027_openrouter_20b | medium       |      17 |
| safe_unknown          | none         |      83 |

凡例: `route` は質問の処理ルート、`count` はtest質問数、`non_unknown_count` は「わかりません」以外の回答数を表す。

| route                  |   count |   non_unknown_count |
|:-----------------------|--------:|--------------------:|
| fallback_bm25_llm      |      37 |                   6 |
| document_whole_context |      14 |                   5 |
| table_calculation      |      17 |                   4 |
| diff_check             |       9 |                   1 |
| code_reading           |       3 |                   1 |
| format_extraction      |      17 |                   0 |
| image_ocr              |       3 |                   0 |

## 判断
今回は、低信頼の長文BM25回答を提出に混ぜると-1リスクが大きいため、EDA027の20B回答で短く明確なものを優先し、それ以外は「わかりません」とした。
EDA021で見られたHTMLタグ混入、根拠文の長文丸写し、別案件の管理文言混入は提出用では除外している。

次はEDA035として、testの「わかりません」になった質問をroute別に分け、table_calculation、format_extraction、diff_checkの順に構造化処理を増やすのが妥当。
