# valid_017

## Question
京橋信用ソリューションズのカラム説明において、カラム名pdaysの値-1は何を表していますか。

## Gold Answer
未連絡

## Predicted Answer
| カラム名 | データ型 | 説明 | データの例 |

## Retrieved Records

### Rank 1
- score: 130.511059
- record_id: `metadata_a2f606b24d8971a9`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/data/カラム説明.md`

```text
ファイル名: カラム説明.md 元パス: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/data/カラム説明.md ファイル種別: md
```

### Rank 2
- score: 130.08579
- record_id: `metadata_15ae1f80ad7ed7b7`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md`

```text
ファイル名: カラム説明.md 元パス: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md ファイル種別: md
```

### Rank 3
- score: 99.330768
- record_id: `markdown_chunk_5d6d129586730a17`
- record_type: `markdown_chunk`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/data/カラム説明.md`

```text
| カラム名 | データ型 | 説明 | データの例 | | --- | --- | --- | --- | | id | 整数 | 顧客の一意の識別ID | 1, 2 | | age | 整数 | 顧客の年齢 | 39, 51 | | job | 文字列 | 職業 | blue-collar, management | | marital | 文字列 | 婚姻状況 | married, single | | education | 文字列 | 学歴 | secondary, tertiary | | default | 文字列 | 債務不履行（デフォルト）の有無 | no, yes | | balance | 整数 | 年間平均残高（口座残高） | 1756, 436 | | housing | 文字列 | 住宅ローンの有無 | yes, no | | loan | 文字列 | 個人ローンの有無 | no, yes | | contact | 文字列 | 連絡手段 | cellular, telephone | | day | 整数 | 最後に連絡した日（日にち） | 3, 18 | | month | 文字列 | 最後に連絡した月 | apr, feb | | duration | 整数 | 最後の連絡の通話時間（秒） | 939, 172 | | campaign | 整数 | 今回のキャンペーンにおける連絡回数 | 1, 10 | | pdays | 整数 | 前回のキャンペーンで最後に連絡してからの経過日数（-1は未連絡） | -1, 595 | | previous | 整数 | 今回のキャンペーンより前に行われた連絡回数 | 0, 2 | | poutcome | 文字列 | 前回のキャンペーンの結果 | unknown, success | | y | 整数 | (目的変数)定期預金などを契約したかどうか（目的変数 / 1: 契約, 0: 未契約など） | 1, 0 |
```

### Rank 4
- score: 99.162408
- record_id: `markdown_chunk_3ebabc8636cccef7`
- record_type: `markdown_chunk`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md`

```text
| カラム名 | データ型 | 説明 | データの例 | | --- | --- | --- | --- | | id | 整数 | 顧客の一意の識別ID | 1, 2 | | age | 整数 | 顧客の年齢 | 39, 51 | | job | 文字列 | 職業 | blue-collar, management | | marital | 文字列 | 婚姻状況 | married, single | | education | 文字列 | 学歴 | secondary, tertiary | | default | 文字列 | 債務不履行（デフォルト）の有無 | no, yes | | balance | 整数 | 年間平均残高（口座残高） | 1756, 436 | | housing | 文字列 | 住宅ローンの有無 | yes, no | | loan | 文字列 | 個人ローンの有無 | no, yes | | contact | 文字列 | 連絡手段 | cellular, telephone | | day | 整数 | 最後に連絡した日（日にち） | 3, 18 | | month | 文字列 | 最後に連絡した月 | apr, feb | | duration | 整数 | 最後の連絡の通話時間（秒） | 939, 172 | | campaign | 整数 | 今回のキャンペーンにおける連絡回数 | 1, 10 | | pdays | 整数 | 前回のキャンペーンで最後に連絡してからの経過日数（-1は未連絡） | -1, 595 | | previous | 整数 | 今回のキャンペーンより前に行われた連絡回数 | 0, 2 | | poutcome | 文字列 | 前回のキャンペーンの結果 | unknown, success | | y | 整数 | (目的変数)定期預金などを契約したかどうか（目的変数 / 1: 契約, 0: 未契約など） | 1, 0 |
```

### Rank 5
- score: 98.3973
- record_id: `pptx_slide_b04b398906f85f8c`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

```text
Slide 6 4. 主要分析結果 ─ モデル性能 データ: 27,128件 / 18カラム ｜ 学習: 21,702件 ｜ テスト: 5,426件 ｜ モデル: gradient_boosting AUC (ROC) 0.925 識別能力 Accuracy 0.900 正確度 F1 (macro) 0.722 総合精度 Brier Score 0.066 確率較正 Precision@Top10% 0.589 上位抽出精度 解釈 高いAUCと上位抽出精度（Precision@Top10% ≈ 0.589）は、スコア上位の顧客群に契約が濃縮されていることを示す 接触優先度付けの初期運用に有用である 目的変数は不均衡（全体契約率 11.7%）であり、Accuracy単独の評価は誤解を招く 業務評価ではAUC/上位抽出指標を重視すべきである Brier scoreの値は確率閾値設定時の較正参考情報として有用
```

### Rank 6
- score: 95.282227
- record_id: `metadata_1821b471f0dc23dd`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

```text
ファイル名: 京橋信用ソリューションズ株式会社_最終報告.pptx 元パス: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx ファイル種別: pptx
```

### Rank 7
- score: 94.003973
- record_id: `python_code_chunk_88122a465339216e`
- record_type: `python_code_chunk`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/src/modeling.py`

```text
# Python Source: modeling.py ## Source - raw_path: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/src/modeling.py - source_sha1: 910b24df108940ab805411dacbf1b96a0397b384 - line_count: 90 - function_count: 1 - class_count: 0 - has_main_guard: False ## Imports | module | name | asname | | --- | --- | --- | | __future__ | annotations | | | pandas | | pd | | sklearn.ensemble | ExtraTreesClassifier | | | sklearn.ensemble | ExtraTreesRegressor | | | sklearn.ensemble | GradientBoostingClassifier | | | sklearn.ensemble | GradientBoostingRegressor | | | sklearn.ensemble | RandomForestClassifier | | | sklearn.ensemble | RandomForestRegressor | | | sklearn.linear_model | LogisticRegression | | | sklearn.linear_model | Ridge | | | sklearn.pipeline | Pipeline | | | src.common | to_float | | | src.common | to_int | | | src.features | build_preprocessor | | 凡例: module はimport元、name はfrom importの対象、asname は別名を表します。 ## Functions | name | lineno | args | docstring | | --- | --- | --- | --- | | build_pipeline | 19 | X, task_type, random_state, model_type, model_params | | 凡例: name は関数名、lineno は開始行、args は引数、docstring は先頭説明を表します。 ## File Operations | lineno | call | string_args | string_keywords | | --- | --- | --- | --- | | 30 | model_params.get | ['max_depth'] | {} | | 29 | model_params.get | ['n_estimators'] | {} | | 33 | model_params.get | ['min_samples_leaf'] | {} | | 34 | model_params.get | ['learning_rate'] | {} | | 35 | model_params.get | ['alpha'] | {} | | 36 | model_params.get | ['c'] | {} | | 52 | model_params.get | ['max_depth'] | {} | | 81 |
```

### Rank 8
- score: 93.696351
- record_id: `python_code_chunk_d877cf48cd2f7089`
- record_type: `python_code_chunk`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/scripts/run_train.py`

```text
# Python Source: run_train.py ## Source - raw_path: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/scripts/run_train.py - source_sha1: 561c55e9be117bac5bcc82ac549af1e73245dc84 - line_count: 142 - function_count: 1 - class_count: 0 - has_main_guard: True ## Imports | module | name | asname | | --- | --- | --- | | __future__ | annotations | | | sys | | | | pathlib | Path | | | src.common | as_bool | | | src.common | infer_date_column | | | src.common | infer_target_column | | | src.common | infer_task_type | | | src.common | load_csv_auto | | | src.common | load_json | | | src.common | resolve_input_path | | | src.common | resolve_output_dir | | | src.common | save_json | | | src.common | to_rel | | | src.eda | summarize_dataframe | | | src.evaluate | build_metrics_base | | | src.evaluate | evaluate_predictions | | | src.features | augment_date_features | | | src.infer | run_inference | | | src.modeling | build_pipeline | | | src.preprocess | split_feature_target | | | src.preprocess | train_test_holdout_split | | 凡例: module はimport元、name はfrom importの対象、asname は別名を表します。 ## Functions | name | lineno | args | docstring | | --- | --- | --- | --- | | main | 7 | | | 凡例: name は関数名、lineno は開始行、args は引数、docstring は先頭説明を表します。 ## File Operations | lineno | call | string_args | string_keywords | | --- | --- | --- | --- | | 39 | load_json | [] | {} | | 46 | cfg.get | ['model_params'] | {} | | 56 | load_csv_auto | [] | {} | | 119 | preview.to_csv | [] | {'encoding': 'utf-8-sig'} | | 137 | print | ['Training pipeline finished successfully.'] | {} |
```
