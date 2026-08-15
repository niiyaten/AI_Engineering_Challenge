# EDA008: OpenRouter LLM回答生成の最小検証

## 目的・背景

EDA007で作成した `ready_for_llm` のMarkdownコンテキストを使い、OpenRouter経由でLLM回答生成を試します。対象はvalidのうち、EDA006で検索根拠が比較的そろっていると判断した問題のみです。

APIキーは環境変数 `OPENROUTER_API_KEY`、またはプロジェクト直下の `.apikey` から読み込み、コード、CSV、ログ、manifestには保存しません。LLM入力からはValidation Answer節を隠し、QuestionとRetrieved Evidenceだけで回答させます。

## 実行設定

- model: `openai/gpt-oss-20b:free`
- free_model_fallback: False
- temperature: 0.0
- max_tokens: 512
- reasoning_enabled: True
- dry_run: False
- limit: 1

## 結果サマリ

- 対象件数: 1
- API成功件数: 1
- valid正解全文を含んだ割合: 0.0000

## ステータス内訳

| status | count |
| --- | --- |
| ok | 1 |

凡例: `status` はLLM呼び出し状態、`count` は件数を表します。

## 回答サンプル

| index | status | true_answer | llm_answer | contains_true_answer | error_message |
| --- | --- | --- | --- | --- | --- |
| 2 | ok | Recall | f1_macro、AUC‑ROC、top10% precision | False |  |

## API試行ログ

| index | model | status | elapsed_sec | error_message |
| --- | --- | --- | --- | --- |
| 2 | openai/gpt-oss-20b:free | ok | 6.052 |  |

凡例: `model` は試行したOpenRouterモデルID、`status` はAPI呼び出し状態、`elapsed_sec` は成功時の処理秒数、`error_message` は失敗時の内容を表します。

## 次にやること

1. モデルを比較し、ready_for_llmのvalid一致率を確認する。
2. プロンプトで回答形式をさらに制御する。
3. testに適用する前に、CSV/XLSX直接集計などLLM以外の不足処理を追加する。