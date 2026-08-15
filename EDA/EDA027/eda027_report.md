# EDA027: test 100問 unknown-allowed LLM提出候補

## 目的

EDA025でno-unknown方針が悪化したため、従来の `わかりません` を許す方針でtest 100問にLLM回答を実行し、提出形式zipを作成する。

## 出力

- answer_log: `EDA/EDA027/tables/test_unknown_allowed_answer_log.csv`
- route_summary: `EDA/EDA027/tables/test_unknown_allowed_route_summary.csv`
- predictions_csv: `EDA/EDA027/predictions/predictions.csv`
- submission_zip: `EDA/EDA027/predictions/eda027_openrouter_openai_gpt_oss_20b_free_unknown_allowed_submission.zip`
- prompt_debug: `EDA/EDA027/prompts`

## 実行設定

- provider: `openrouter`
- model: `openai/gpt-oss-20b:free`
- top_k: 8
- max_context_chars: 12000
- max_tokens: 700
- temperature: 0.0

## 全体指標

凡例: `metric` は診断指標、`value` は値を表します。

| metric | value |
| --- | --- |
| test_question_count | 100 |
| http_200_count | 53 |
| unknown_answer_count | 83 |
| empty_or_error_to_unknown_count | 50 |
| max_answer_length | 27 |

## route別診断

凡例: `route` は質問ルート、`question_count` はtest質問数、`success_status_200_count` はHTTP 200件数、`unknown_answer_count` は不明回答数、`empty_or_error_to_unknown_count` はAPI失敗または空回答を `わかりません` にした件数です。

| route | question_count | success_status_200_count | unknown_answer_count | empty_or_error_to_unknown_count |
| --- | --- | --- | --- | --- |
| code_reading | 3 | 2 | 2 | 1 |
| diff_check | 9 | 5 | 8 | 5 |
| document_whole_context | 14 | 8 | 9 | 6 |
| fallback_bm25_llm | 37 | 18 | 31 | 21 |
| format_extraction | 17 | 10 | 17 | 7 |
| image_ocr | 3 | 2 | 3 | 1 |
| table_calculation | 17 | 8 | 13 | 9 |

## HTTP status別件数

凡例: `status` はLLM APIのHTTPステータス、`count` は件数を表します。

| status | count |
| --- | --- |
| 200 | 53 |
| 429 | 47 |

## 質問別結果

凡例: `index` はtest質問番号、`route` は処理ルート、`answer` は最終回答、`answer_source` はLLM回答か空回答補完か、`status` はLLM APIのHTTPステータスを表します。

| index | route | answer | answer_source | status |
| --- | --- | --- | --- | --- |
| 0 | diff_check | 変更なし | llm | 200 |
| 1 | diff_check | わかりません | empty_or_error_to_unknown | 200 |
| 2 | format_extraction | わかりません | llm | 200 |
| 3 | format_extraction | わかりません | llm | 200 |
| 4 | code_reading | bmi | llm | 200 |
| 5 | fallback_bm25_llm | わかりません | llm | 200 |
| 6 | table_calculation | 0円 | llm | 200 |
| 7 | format_extraction | わかりません | llm | 200 |
| 8 | table_calculation | 14,744ドル。 | llm | 200 |
| 9 | diff_check | わかりません | llm | 200 |
| 10 | table_calculation | わかりません | llm | 200 |
| 11 | format_extraction | わかりません | llm | 200 |
| 12 | document_whole_context | わかりません | llm | 200 |
| 13 | fallback_bm25_llm | わかりません | llm | 200 |
| 14 | diff_check | わかりません | llm | 200 |
| 15 | format_extraction | わかりません | llm | 200 |
| 16 | format_extraction | わかりません | llm | 200 |
| 17 | format_extraction | わかりません | llm | 200 |
| 18 | document_whole_context | わかりません | llm | 200 |
| 19 | table_calculation | T04 T05 T06 T07 T08 | llm | 200 |
| 20 | document_whole_context | 渡辺遥: T07, T09, T10 藤田彩: T12 | llm | 200 |
| 21 | fallback_bm25_llm | エグゼクティブスポンサーです | llm | 200 |
| 22 | diff_check | わかりません | llm | 200 |
| 23 | document_whole_context | 398750円 | llm | 200 |
| 24 | fallback_bm25_llm | わかりません | empty_or_error_to_unknown | 200 |
| 25 | format_extraction | わかりません | llm | 200 |
| 26 | fallback_bm25_llm | わかりません | llm | 200 |
| 27 | document_whole_context | 7 | llm | 200 |
| 28 | fallback_bm25_llm | Age | llm | 200 |
| 29 | table_calculation | わかりません | llm | 200 |

## 注意点

- 根拠から判断できない場合は `わかりません` を許す。
- API失敗または空回答の場合は、提出CSVの空欄を避けるため `わかりません` を入れる。
- EDA025で悪化した検索断片フォールバックは使わない。
- SIGNATEへの実提出は行っていない。
- APIキーは `.apikey` から読み込み、成果物には保存しない。

## 結論

OpenRouter 20Bを再実行したところ、前回よりは大きく改善した。

`openai/gpt-oss-20b:free` でtest 100問を再実行した結果、HTTP 200は53件、HTTP 429は47件だった。最終回答は83件が `わかりません`、17件が非 `わかりません` になった。出力zipは `EDA/EDA027/predictions/eda027_openrouter_openai_gpt_oss_20b_free_unknown_allowed_submission.zip` で、zip内ファイルは `predictions.csv` のみである。

ただし、47件はまだHTTP 429であり、非 `わかりません` の回答にも根拠ずれや計算誤りの可能性がある。したがって、このzipは即時の本命提出候補ではなく、LLM無料枠が回復したタイミングでは一部回答が得られることを確認した実験結果として扱う。

次は、validで表計算、書式抽出、差分比較、コード読解のroute別処理を改善し、LLMへ投げる質問数と入力根拠を減らす方針を優先する。
