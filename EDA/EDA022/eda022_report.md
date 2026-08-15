# EDA022: OpenRouter LLM回答生成

## 目的

EDA021で保存したRAG検索結果をOpenRouterのLLMへ渡し、抽出型回答からLLM生成回答へ発展できるかを確認する。

## 出力

- llm_answer_log: `EDA/EDA022/tables/llm_answer_log.csv`
- hybrid_predictions_csv: `EDA/EDA022/predictions/predictions_hybrid.csv`
- hybrid_submission_zip: `EDA/EDA022/predictions/eda022_llm_hybrid_submission.zip`

## 実行設定

- models: `openai/gpt-oss-120b:free,openai/gpt-oss-20b:free,qwen/qwen3-next-80b-a3b-instruct:free`
- top_k: 6
- max_context_chars: 12000
- max_tokens: 700
- temperature: 0.0

## 出力検証

凡例: `metric` は検証項目、`value` は値を表します。

| metric | value |
| --- | --- |
| llm_call_targets | 5 |
| llm_success_count | 5 |
| llm_failed_fallback_count | 0 |
| hybrid_prediction_count | 100 |
| hybrid_llm_answers | 5 |
| hybrid_baseline_answers | 95 |
| empty_answer_count | 0 |
| max_answer_length | 900 |

## model別呼び出し件数

凡例: `model` はOpenRouterモデル名、`count` は最終的に試行した件数を表します。

| model | count |
| --- | --- |
| openai/gpt-oss-120b:free | 1 |
| openai/gpt-oss-20b:free | 4 |

## HTTP status別件数

凡例: `status` はOpenRouterのHTTPステータス、`count` は件数を表します。

| status | count |
| --- | --- |
| 200 | 5 |

## 注意点

- APIキーは `.apikey` から読み込むだけで、レポートやCSVには保存しない。
- LLMが失敗した質問はEDA021の回答へフォールバックするため、zipは常に100行の提出形式になる。
- このEDAはLLM接続と回答改善の実験であり、SIGNATEへの実提出は行っていない。
