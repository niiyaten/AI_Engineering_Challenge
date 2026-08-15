# valid_004 LLM Context

## Question
青嶺不動産アセットマネジメントの modeling.py において、前処理器の sparse_output が False になる model_type は何ですか。

## Validation Answer
hist_gradient_boosting

## Diagnosis
- required_capability: code_reading
- context_quality_for_llm: ready_for_llm
- answer_hit_top5: True
- recommended_next_step: LLM向けMarkdownコンテキストを作る

## Retrieved Evidence

### Evidence 2
- score: 401.0632
- source_eda: EDA002
- extension: .py
- project_name: 株式会社青嶺不動産アセットマネジメント
- major_folder: 04.分析
- relative_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py

```text
_boosting") # REGION: MODEL_SELECTION START n_estimators = to_int(model_params.get("n_estimators"), 300) max_depth = model_params.get("max_depth") if max_depth in ("", "None", "null"): max_depth = None min_samples_leaf = to_int(model_params.get("min_samples_leaf"), 1) learning_rate = to_float(model_params.get("learning_rate"), 0.1) alpha = to_float(model_par...
```

### Evidence 3
- score: 396.4896
- source_eda: EDA002
- extension: .py
- project_name: 株式会社青嶺不動産アセットマネジメント
- major_folder: 04.分析
- relative_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py

```text
el_key == "hist_gradient_boosting": model = HistGradientBoostingClassifier( learning_rate=learning_rate, max_depth=to_int(model_params.get("max_depth"), 6), max_iter=to_int(model_params.get("max_iter"), 300), min_samples_leaf=to_int(model_params.get("min_samples_leaf"), 20), l2_regularization=l2_regularization, random_state=random_state, ) elif model_key == ...
```

### Evidence 4
- score: 392.5797
- source_eda: EDA002
- extension: .py
- project_name: 株式会社青嶺不動産アセットマネジメント
- major_folder: 04.分析
- relative_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py

```text
model = Ridge(alpha=alpha) else: model = RandomForestRegressor( n_estimators=n_estimators, random_state=random_state, n_jobs=-1, max_depth=max_depth, min_samples_leaf=min_samples_leaf, max_features=max_features, ) else: if model_key == "extra_trees": model = ExtraTreesClassifier( n_estimators=n_estimators, random_state=random_state, n_jobs=-1, max_depth=max_...
```

### Evidence 5
- score: 391.8915
- source_eda: EDA002
- extension: .py
- project_name: 株式会社青嶺不動産アセットマネジメント
- major_folder: 04.分析
- relative_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py

```text
jobs=-1, max_depth=max_depth, min_samples_leaf=min_samples_leaf, max_features=max_features, ) elif model_key == "gradient_boosting": model = GradientBoostingRegressor( n_estimators=n_estimators, learning_rate=learning_rate, max_depth=to_int(model_params.get("max_depth"), 3), random_state=random_state, ) elif model_key == "hist_gradient_boosting": model = His...
```
