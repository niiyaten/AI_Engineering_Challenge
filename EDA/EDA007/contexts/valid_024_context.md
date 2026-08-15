# valid_024 LLM Context

## Question
白峰信用リスク評価の 01_eda.ipynb にある特徴量相関ヒートマップの図で可視化されている特徴量のうち、classとの相関係数の絶対値が最も小さい特徴量名を答えてください。

## Validation Answer
Attr7

## Diagnosis
- required_capability: document_qa
- context_quality_for_llm: needs_better_retrieval
- answer_hit_top5: False
- recommended_next_step: 抽出対象と検索重みを見直す

## Retrieved Evidence

### Evidence 1
- score: 619.854
- source_eda: EDA002
- extension: .ipynb
- project_name: 白峰信用リスク評価株式会社
- major_folder: 04.分析
- relative_path: プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb

```text
> 0 else pd.DataFrame() plt.figure(figsize=(12, 10)) if corr_mat.shape[0] > 0: sns.heatmap(corr_mat, cmap='coolwarm', center=0, square=True) plt.title('特徴量相関ヒートマップ') else: plt.text(0.5, 0.5, '相関を計算できる数値列が不足しています', ha='center', va='center') plt.title('特徴量相関ヒートマップ') plt.tight_layout() plt.savefig(FIG_DIR / 'feature_correlation_heatmap.png', dpi=150, bbox_inche...
```

### Evidence 2
- score: 510.4668
- source_eda: EDA002
- extension: .ipynb
- project_name: 医療法人社団 恒一会 かえで総合病院
- major_folder: 04.分析
- relative_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb

```text
False) plt.title('特徴量相関ヒートマップ') plt.tight_layout() plt.savefig(FIG_DIR / 'feature_correlation_heatmap.png', dpi=150, bbox_inches='tight') plt.show() plt.close() target_corr = corr[target_col].drop(target_col).sort_values(key=lambda s: s.abs(), ascending=False) if target_col in corr.columns else pd.Series(dtype=float) print('目的変数との相関') print(target_corr) else...
```

### Evidence 3
- score: 464.3345
- source_eda: EDA002
- extension: .ipynb
- project_name: 白峰信用リスク評価株式会社
- major_folder: 04.分析
- relative_path: プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb

```text
tr41 42.682133 dtype: float64
## cell_016 [markdown]
## 6. 相関分析
## cell_017 [code] try: from pathlib import Path FIG_DIR = Path(FIG_DIR) FIG_DIR.mkdir(parents=True, exist_ok=True) num_df = df.select_dtypes(include=[np.number]).copy() if target_col in num_df.columns: corr_target = num_df.corr(numeric_only=True)[target_col].sort_values(key=lambda s: s.abs(), a...
```

### Evidence 4
- score: 451.4664
- source_eda: EDA002
- extension: .ipynb
- project_name: 青葉与信マネジメント株式会社
- major_folder: 04.分析
- relative_path: プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb

```text
print(corr) plt.figure(figsize=(8, 6)) sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, square=True) plt.title('数値特徴量の相関ヒートマップ') plt.tight_layout() plt.savefig(FIG_DIR / 'feature_correlation_heatmap.png', dpi=150, bbox_inches='tight') plt.show() plt.close() if target_col in corr.columns: target_corr = corr[target_col].drop(target_col).sort...
```

### Evidence 5
- score: 420.9874
- source_eda: EDA002
- extension: .ipynb
- project_name: 青葉与信マネジメント株式会社
- major_folder: 04.分析
- relative_path: プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb

```text
('相関係数') plt.ylabel('特徴量') plt.tight_layout() plt.close() except Exception as _eda_exc: print(f"[warn] EDA section fallback: corr_code: {_eda_exc}") numeric_cols = df.select_dtypes(include=["number"]).columns.tolist() fig, ax = plt.subplots(figsize=(10, 8)) if len(numeric_cols) >= 2: corr = df[numeric_cols[:20]].corr(numeric_only=True) sns.heatmap(corr, cmap...
```
