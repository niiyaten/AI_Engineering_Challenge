# EDA054: 残り `わかりません` の追加候補化

## 背景と目的

EDA053 safe版で残った `わかりません` 14件を対象に、既存の前処理成果から追加で採用できる回答を探す。
OpenRouterは、長い候補の短答化に限定して使う。

## 方針

- EDA053 safe版をベースにする。
- ローカルで根拠候補を作る。
- 長文候補はOpenRouter `openai/gpt-oss-20b:free` で最終回答へ短答化する。
- 提出候補へ採用するのは、`needs_review=False` かつ `confidence` が `high` または `medium` のものだけにする。

## 結果

- EDA053 safe版の `わかりません`: 14
- EDA054後の `わかりません`: 12
- 追加採用: 2

追加採用した回答は以下。

| index | route | 採用回答 | 根拠 |
| --- | --- | --- | --- |
| 75 | proposal_plan_week_lookup | 第4週 | みなみ野女性医療センターの `スケジュール管理表.csv` で、フェーズ4「モデル構築・比較」が2025-04-25開始。契約開始2025-04-03を第1週起点とすると第4週。 |
| 96 | checkpoint_task_lookup | T05、T06、T07、T08 | 青葉与信マネジメントの `Sheet2.csv` で、MS2「データ理解完了」の関連タスクが `T05~T08` と明記されている。 |

凡例: `index` はtest質問ID、`route` は今回使った処理、`採用回答` は提出候補へ反映した短答、`根拠` は採用判断に使ったファイルと判断内容を表す。

OpenRouterは、長文候補の短答化に使った。index 75では `第4週` が得られたが、index 52、62、80、95は `わかりません` または空回答だったため採用しない。

残った `わかりません` は、index 33、38、44、46、49、52、58、62、79、80、83、95の12件。

## 出力

- 候補ログ: `EDA/EDA054/tables/eda054_candidate_answers.csv`
- OpenRouter試行ログ: `EDA/EDA054/tables/eda054_openrouter_attempts.csv`
- 提出候補zip: `EDA/EDA054/predictions/eda054_remaining_unknown_submission.zip`

## 注意

横断集計、座席表、モデル再計算、Excel黄色セルの候補は、根拠がまだ弱いものは採用しない。
