# EDA027補助: OpenRouter無料モデル疎通確認

## 目的

EDA027でtest 100問のほとんどがHTTP 429になったため、120Bや他の無料モデルでも同じ制限に当たるかを少数リクエストで確認する。

## 実行設定

- question_index: 0
- model_limit: 8
- max_tokens: 300
- top_k: 8

## 現在取得できた無料モデル数

- free_model_count: 24
- model_list_error: なし

## HTTP status別件数

凡例: `status` はOpenRouterのHTTPステータス、`count` は件数です。

| status | count |
| --- | --- |
| 429 | 8 |

## モデル別結果

凡例: `model` はOpenRouterモデルID、`status` はHTTPステータス、`answer` は返答、`is_unknown` は不明回答判定、`error_message` はAPIエラー概要です。

| model | status | elapsed_sec | answer | is_unknown | error_message | question_index | route | top1_source_path | wall_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openai/gpt-oss-120b:free | 429 | 1.018 |  | 1 | Provider returned error \| openai/gpt-oss-120b:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 1.018 |
| openai/gpt-oss-20b:free | 429 | 0.978 |  | 1 | Provider returned error \| openai/gpt-oss-20b:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 0.978 |
| qwen/qwen3-next-80b-a3b-instruct:free | 429 | 1.944 |  | 1 | Provider returned error \| qwen/qwen3-next-80b-a3b-instruct:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 1.944 |
| cognitivecomputations/dolphin-mistral-24b-venice-edition:free | 429 | 0.566 |  | 1 | Provider returned error \| cognitivecomputations/dolphin-mistral-24b-venice-edition:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 0.566 |
| cohere/north-mini-code:free | 429 | 0.346 |  | 1 | Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 0.346 |
| google/gemma-4-26b-a4b-it:free | 429 | 0.125 |  | 1 | Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 0.125 |
| google/gemma-4-31b-it:free | 429 | 0.333 |  | 1 | Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 0.333 |
| liquid/lfm-2.5-1.2b-instruct:free | 429 | 2.14 |  | 1 | Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day | 0 | diff_check | share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx | 2.14 |

## 注意点

- このEDAはモデル可用性の確認であり、SIGNATEへの提出は行っていない。
- APIキーは `.apikey` から読み込み、成果物には保存しない。
