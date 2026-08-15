# test_047

## Question
青嶺不動産アセットマネジメントのtrain.xlsxにおいて、黄色ハイライトセルは予測と実際の誤差を計算していますが、その予測値の対象となっている不動産の建設年を算出してください。

## Route
format_extraction

## Generated Answer
クライアント：株式会社青嶺不動産アセットマネジメント

## Retrieved Records

### Rank 1
- score: 114.094229
- record_id: `metadata_4ac29b082c96a951`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`

```text
ファイル名: 株式会社青嶺不動産アセットマネジメント_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx
ファイル種別: pptx
```

### Rank 2
- score: 108.286504
- record_id: `pptx_slide_04bd7b49a8169aea`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`

```text
Slide 7
04 データ品質（確定事実）
レコード数
37,751件
data\train.csv
特徴量数
19
selected_feature_count
GROSS SF欠損率
35.9%
重大な品質課題
LAND SF欠損率
35.1%
重大な品質課題
高カーディナリティのため除外した列
NEIGHBORHOOD
unique: 251
BUILDING CLASS AT PRESENT
unique: 123
BUILDING CLASS AT TIME OF SALE
unique: 121
データ品質に関する主要な所見
GROSS SQUARE FEET（35.9%）およびLAND SQUARE FEET（35.1%）の欠損率が突出して高い
YEAR BUILTに入力異常（0等）を含む — 実際の効果は補正後に再評価が必要
ZIP CODEの0値が存在 — 外部ZIP参照による修正が可能
対象カラムと型方針は分析計画に従い整理済み（selected_feature_count = 19）
時系列粒度を直接示す信頼できる日付カラムが存在しない（市況サイクルの調整未実施）
```

### Rank 3
- score: 106.664238
- record_id: `python_code_chunk_7d44f2d6c2dbe22a`
- record_type: `python_code_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/scripts/run_train.py`

```text
# Python Source: run_train.py

## Source
- raw_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/scripts/run_train.py`
- source_sha1: `bcf0c0540b7873d0eac2cd7a1829b184957b698b`
- line_count: 630
- function_count: 8
- class_count: 0
- has_main_guard: True

## Imports

| module | name | asname |
| --- | --- | --- |
| __future__ | annotations | |
| sys | | |
| pathlib | Path | |
| numpy | | np |
| pandas | | pd |
| sklearn.metrics | f1_score | |
| sklearn.model_selection | StratifiedKFold | |
| src.common | as_bool | |
| src.common | infer_date_column | |
| src.common | infer_target_column | |
| src.common | infer_task_type | |
| src.common | load_csv_auto | |
| src.common | load_json | |
| src.common | resolve_input_path | |
| src.common | resolve_output_dir | |
| src.common | save_json | |
| src.common | to_rel | |
| src.eda | summarize_dataframe | |
| src.evaluate | build_metrics_base | |
| src.evaluate | evaluate_predictions | |
| src.features | add_categorical_frequency_features | |
| src.features | augment_cyclical_time_features | |
| src.features | augment_date_features | |
| src.features | augment_numeric_interactions | |
| src.features | augment_ordered_category_features | |
| src.features | group_rare_categories | |
| src.features | select_feature_columns | |
| src.infer | run_inference | |
| src.modeling | build_pipeline | |
| src.preprocess | split_feature_target | |
| src.preprocess | train_valid_test_split | |

凡例: `module` はimport元、`name` はfrom importの対象、`asname` は別名を表します。

## Functions

| name | lineno | args | docstring |
| --- | --- | ---
```

### Rank 4
- score: 106.403007
- record_id: `metadata_ff88f6251e76408a`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/03.データ/train.xlsx`

```text
ファイル名: train.xlsx
元パス: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/03.データ/train.xlsx
ファイル種別: xlsx
```

### Rank 5
- score: 104.043455
- record_id: `python_code_chunk_577b544b8b4d575e`
- record_type: `python_code_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py`

```text
# Python Source: __init__.py

## Source
- raw_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py`
- source_sha1: `da39a3ee5e6b4b0d3255bfef95601890afd80709`
- line_count: 0
- function_count: 0
- class_count: 0
- has_main_guard: False

## Imports

該当データはありません。

凡例: `module` はimport元、`name` はfrom importの対象、`asname` は別名を表します。

## Functions

該当データはありません。

凡例: `name` は関数名、`lineno` は開始行、`args` は引数、`docstring` は先頭説明を表します。

## File Operations

該当データはありません。

凡例: `call` は呼び出し名、`string_args` と `string_keywords` はファイルパス候補を含む文字列引数です。

## Code

```python

```
```

### Rank 6
- score: 103.944552
- record_id: `python_code_chunk_fd6f104c8ce6b3a2`
- record_type: `python_code_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py`

```text
# Python Source: modeling.py

## Source
- raw_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py`
- source_sha1: `6ebaac679ed86d1c7083f77eca2a6ee82ae8c4cf`
- line_count: 125
- function_count: 1
- class_count: 0
- has_main_guard: False

## Imports

| module | name | asname |
| --- | --- | --- |
| __future__ | annotations | |
| pandas | | pd |
| sklearn.ensemble | ExtraTreesClassifier | |
| sklearn.ensemble | ExtraTreesRegressor | |
| sklearn.ensemble | GradientBoostingClassifier | |
| sklearn.ensemble | GradientBoostingRegressor | |
| sklearn.ensemble | HistGradientBoostingClassifier | |
| sklearn.ensemble | HistGradientBoostingRegressor | |
| sklearn.ensemble | RandomForestClassifier | |
| sklearn.ensemble | RandomForestRegressor | |
| sklearn.linear_model | LogisticRegression | |
| sklearn.linear_model | Ridge | |
| sklearn.pipeline | Pipeline | |
| src.common | to_float | |
| src.common | to_int | |
| src.features | build_preprocessor | |

凡例: `module` はimport元、`name` はfrom importの対象、`asname` は別名を表します。

## Functions

| name | lineno | args | docstring |
| --- | --- | --- | --- |
| build_pipeline | 21 | X, task_type, random_state, model_type, model_params | |

凡例: `name` は関数名、`lineno` は開始行、`args` は引数、`docstring` は先頭説明を表します。

## File Operations

| lineno | call | string_args | string_keywords |
| --- | --- | --- | --- |
| 32 | model_params.get | ['max_depth'] | {} |
| 39 | model_params.get | ['class_weight'] | {} |
| 40 | model_params.get | ['max_features'] | {} |
| 31 | model_params.get | ['n_estimators'] | {} |
| 35 | model_params.get |
```

### Rank 7
- score: 103.630598
- record_id: `pptx_slide_eaebdff029c19c9e`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`

```text
Slide 1
最終分析報告書
NYC不動産売買トランザクション価格形成要因分析
クライアント：株式会社青嶺不動産アセットマネジメント
実施者：株式会社データアステル
契約期間：2025年8月6日〜2025年9月17日
課金方式：タイム・アンド・マテリアル
CONFIDENTIAL
最終報告会：2025年9月16日
```

### Rank 8
- score: 103.614623
- record_id: `python_code_chunk_0be47dbc4774c3bc`
- record_type: `python_code_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/features.py`

```text
# Python Source: features.py

## Source
- raw_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/features.py`
- source_sha1: `8d32730601febc05845a95649c81575df8545ea7`
- line_count: 337
- function_count: 11
- class_count: 0
- has_main_guard: False

## Imports

| module | name | asname |
| --- | --- | --- |
| __future__ | annotations | |
| numpy | | np |
| pandas | | pd |
| sklearn.compose | ColumnTransformer | |
| sklearn.impute | SimpleImputer | |
| sklearn.pipeline | Pipeline | |
| sklearn.preprocessing | OneHotEncoder | |

凡例: `module` はimport元、`name` はfrom importの対象、`asname` は別名を表します。

## Functions

| name | lineno | args | docstring |
| --- | --- | --- | --- |
| is_pure_day_number_column | 47 | series | |
| augment_date_features | 56 | df, date_col | |
| augment_numeric_interactions | 79 | df, enabled, max_numeric_features, max_interaction_pairs | |
| augment_cyclical_time_features | 108 | df, enabled | |
| augment_ordered_category_features | 129 | df, enabled | |
| is_identifier_like_column | 156 | name | |
| _categorical_columns | 163 | df | |
| group_rare_categories | 176 | df, enabled, min_count | |
| add_categorical_frequency_features | 211 | df, enabled, min_unique, max_unique | |
| select_feature_columns | 245 | X, categorical_unique_limit, group_rare_categories_enabled, rare_category_min_count, add_categorical_frequency_features_enabled, categorical_frequency_min_unique, categorical_frequency_max_unique | |
| build_preprocessor | 320 | X, sparse_output | |

凡例: `name` は関数名、`lineno` は開始行、`args` は引数、`docstring` は先頭説明を表します。

## File Operatio
```
