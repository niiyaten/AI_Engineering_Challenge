# valid_028

## Question
蒼泉会の分析コードにおいて、CATは dtype とユニーク数の条件でどのように判定していますか。

## Gold Answer
object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。

## Predicted Answer
世界的な自動車メーカーであり、莫大な資本を持つ企業であっても、採用初年度のベースラインは500万円台からスタートし、経験や実力に応じて1,000万円の大台に届くという設計である。同社は、トヨタグループのグローバルな事業を最上流（企画・構想段階）からIT技術で支えるという巨大なスケールの業務内容を提示するとともに、完全週休2日制、リモートワークの許可、充実した教育体制といった労働環境の柔軟性と安定した基盤を提供している。これは、現金報酬のトップエンドにおいて外資系ハイテク企業と直接のマネーゲームを繰り広げるのではなく、「安定性」「大規模データの取り扱い」「長期的なキャリアパス」という総合的な魅力度で人材を惹きつける、日本企業特有の採用戦略を体現している。

## Retrieved Records

### Rank 1
- score: 69.813623
- record_id: `notebook_cell_8c5cd4bb50dc993b`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb Cell 21: code try: print('【EDAサマリー】') rows, cols = df.shape num_cols = df.select_dtypes(include=[np.number]).columns.tolist() cat_cols = [c for c in df.columns if df[c].dtype == 'object' or str(df[c].dtype) == 'category'] missing_total = int(df.isna().sum().sum()) print(f'行数: {rows}') print(f'列数: {cols}') print(f'数値列数: {len(num_cols)}') print(f'カテゴリ列数: {len(cat_cols)}') print(f'総欠損数: {missing_total}') if target_col in df.columns: print('\n【目的変数の要約】') print(df[target_col].value_counts(dropna=False).sort_index()) print('\n【列ごとのユニーク数】') print(df.nunique(dropna=True).sort_values(ascending=False)) except Exception as _eda_exc: print(f"[warn] EDA section fallback: summary_code: {_eda_exc}") summary_rows = [] summary_rows.append(f"レコード数: {len(df):,}") summary_rows.append(f"列数: {df.shape[1]:,}") summary_rows.append(f"欠損率上位列: {', '.join((df.isna().mean()*100).sort_values(ascending=False).head(3).index.tolist())}") summary_rows.append(f"数値列数: {len(df.select_dtypes(include=['number']).columns)}") summary_rows.append(f"カテゴリ列数: {len([c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])])}") summary_rows.append(f"目的変数候補: {target_col}") print("主要サマリ") for row in summary_rows: print(f"- {row}") Output: 【EDAサマリー】 行数: 1600 列数: 8 数値列数: 5 カテゴリ列数: 0 総欠損数: 0 【目的変数の要約】 charges 0 1256 1 198 2 146 Name: count, dtype: int64 【列ごとのユニーク数】 id 1600 bmi 1600 age 47 children 6 region 4 charges 3 sex 2 smoker 2 dtype: int64
```

### Rank 2
- score: 64.163877
- record_id: `notebook_cell_3802b71d6f45ff32`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb Cell 20: code try: import pandas as pd import numpy as np import matplotlib.pyplot as plt import seaborn as sns n_rows, n_cols = df.shape num_cols = df.select_dtypes(include=[np.number]).columns.tolist() cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist() missing_total = int(df.isnull().sum().sum()) missing_by_col = df.isnull().sum().sort_values(ascending=False) if target_col in df.columns: pass if len(num_cols) > 1 and target_col in num_cols: corr_s = df[num_cols].corr(numeric_only=True)[target_col].drop(target_col).sort_values(key=lambda s: s.abs(), ascending=False) high_card = [] for c in cat_cols: high_card.append({'列名': c, 'ユニーク数': df[c].nunique(dropna=True)}) if len(high_card) > 0: high_card_df = pd.DataFrame(high_card).sort_values('ユニーク数', ascending=False) except Exception as _eda_exc: summary_rows = [] summary_rows.append(f"レコード数: {len(df):,}") summary_rows.append(f"列数: {df.shape[1]:,}") summary_rows.append(f"欠損率上位列: {', '.join((df.isna().mean()*100).sort_values(ascending=False).head(3).index.tolist())}") summary_rows.append(f"数値列数: {len(df.select_dtypes(include=['number']).columns)}") summary_rows.append(f"カテゴリ列数: {len([c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])])}") summary_rows.append(f"目的変数候補: {target_col}") for row in summary_rows: pass
```

### Rank 3
- score: 61.444239
- record_id: `generic_chunk_86688391df015650`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
& Companyの調査は、データ駆動型の意思決定を組織的に導入している企業が、新規顧客の獲得において23倍、既存顧客の維持において6倍という圧倒的な効率性を示していることを実証している。また、Deloitteの調査においても、企業の65%がビジネスの成功においてデータ駆動型の意思決定が不可欠な価値を持つと認識しており、IBMの報告では59%の組織がビッグデータ分析の導入による競争優位性の獲得を明確に認めている。 このように、データサイエンティストが創出する投資対効果（ROI）が定量的に証明されていることが、労働市場における同職種の需要を牽引している。米国労働省統計局（Bureau of Labor Statistics: BLS）の予測によれば、2024年から2034年にかけてのデータサイエンティストの雇用成長率は34%と見込まれており、全職業の平均を大きく上回る「極めて速い（Much faster than average）」成長カテゴリに分類されている。今後10年間にわたり、毎年約21,000件の新規求人が創出され、2024年から2034年の間だけで82,500人の雇用増加が予測されている。 本報告では、この極めて流動的かつ成長著しい労働市場において、データサイエンティストの収入がいかなる要因（地理的条件、産業構造、教育水準、技術スキル、および生成AIなどのマクロトレンド）によって決定されているのかを、複数の信頼性の高い統計データに基づいて多角的に分析し、その構造的メカニズムを解き明かす。 ## 2. 米国市場における報酬構造の精緻な分析：グローバルベンチマークとしての米国 世界最大のテクノロジークラスターと資本市場を擁する米国におけるデータサイエンティストの報酬体系は、世界の労働市場における事実上の標準（デファクト・スタンダード）として機能している。米国の報酬構造を分析することは、資本主義経済がいかに高度な知能労働を評価しているかを理解する上で不可欠である。 </span
```

### Rank 4
- score: 58.512511
- record_id: `notebook_cell_9e77fad74c01336f`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb Cell 6: code try: import math from pathlib import Path Path(FIG_DIR).mkdir(parents=True, exist_ok=True) print('【データ概要】') print(f'行数: {df.shape[0]}') print(f'列数: {df.shape[1]}') print('\n【列情報】') info_df = pd.DataFrame({ '列名': df.columns, '型': [str(df[c].dtype) for c in df.columns], '欠損数': [int(df[c].isna().sum()) for c in df.columns], '欠損率(%)': [float(df[c].isna().mean() * 100) for c in df.columns], 'ユニーク数': [int(df[c].nunique(dropna=True)) for c in df.columns] }) print(info_df) print('\n【先頭5行】') print(df.head()) print('\n【基本統計量】') print(df.describe(include='all').transpose()) except Exception as _eda_exc: print(f"[warn] EDA section fallback: overview_code: {_eda_exc}") dtype_summary = ( df.dtypes.astype(str) .rename("dtype") .reset_index() .rename(columns={"index": "column"}) ) type_counts = dtype_summary["dtype"].value_counts().rename_axis("dtype").reset_index(name="count") print("列型サマリ") display(type_counts) numeric_cols = df.select_dtypes(include=["number"]).columns.tolist() category_cols = [c for c in df.columns if c not in numeric_cols] print(f"数値列数: {len(numeric_cols)} / カテゴリ列数: {len(category_cols)}") display(dtype_summary.head(30)) Output: 【データ概要】 Output: 行数: 1600 列数: 8 【列情報】 列名 型 欠損数 欠損率(%) ユニーク数 0 id int64 0 0.0 1600 1 age int64 0 0.0 47 2 sex str 0 0.0 2 3 bmi float64 0 0.0 1600 4 children int64 0 0.0 6 5 smoker str 0 0.0 2 6 region str 0 0.0 4 7 charges int64 0 0.0 3 【先頭5行】 id age sex bmi children smoker region charges 0 0 26 male 32.665465 3 no southeast 0 1 1 41 male 29.798725 1 no southwest 0 2 2 28 male 32.722029 0 yes northwest 1 3 3 20 female 38.429831 2 no southeast 0 4 4 45 female 29.641854 1 no northwest 0 【基本統計量】 count unique top freq mean std min \ id 1600.0 NaN NaN NaN 1007.8625 575.26841 0.0 age 1600.0 NaN NaN NaN 38.985 13.555012 18.0 sex 1600 2 male 841 NaN NaN NaN bmi 1600.0 NaN NaN NaN 32.424376 5.766915 20.627626 children 1600.0 NaN NaN NaN 1.014375 1.259031 0.0 smoker 1600 2 no 1261 NaN NaN NaN region 1600 4 northeast 414 NaN NaN NaN charges 1600.0 NaN NaN NaN 0.30625 0.628656 0.0 25% 50% 75% max id 515.75 1010.5 1509.25 1999.0 age 27.0 40.0 50.0 64.0 sex NaN NaN NaN NaN bmi 28.634267 32.268786 37.069581 47.290644 children 0.0 1.0 2.0 5.0 smoker NaN NaN NaN NaN region NaN NaN NaN NaN charges 0.0 0.0 0.0 2.0
```

### Rank 5
- score: 56.367012
- record_id: `generic_chunk_779f83f69c570e75`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
olor="#1F1F1F" style="color:#1F1F1F">これらのデータの激しいばらつき（500万円台から1,700万円台まで）は、日本市場における「給与の双峰性（二重構造）」を示唆している。外資系テック企業や一部の先進的なITメガベンチャー、あるいはDX（デジタルトランスフォーメーション）を急務とするコンサルティングファームが、年収1,000万円から1,500万円を超えるグローバル基準の「ジョブ型」報酬を提示している。その一方で、伝統的な国内企業では、既存の「職能給」や年功序列的な給与テーブルの枠内に新鋭のデータサイエンティストを強引に当てはめようとするため、500万円から800万円程度の水準に留まるケースが多数混在しているのである。 ### 4.3. 伝統的製造業の適応事例：トヨタ自動車の採用戦略 日本の基幹産業である製造業が、どのようにデータサイエンティストを処遇しようと試みているかを示す具体的な事例として、トヨタ自動車（またはその100%出資IT子会社）の採用条件が挙げられる。同社の正社員採用（業種未経験のポテンシャル採用も含む）における初年度年収は、533万円から1,045万円に設定されている。 世界的な自動車メーカーであり、莫大な資本を持つ企業であっても、採用初年度のベースラインは500万円台からスタートし、経験や実力に応じて1,000万円の大台に届くという設計である。同社は、トヨタグループのグローバルな事業を最上流（企画・構想段階）からIT技術で支えるという巨大なスケールの業務内容を提示するとともに、完全週休2日制、リモートワークの許可、充実した教育体制といった労働環境の柔軟性と安定した基盤を提供している。これは、現金報酬のトップエンドにおいて外資系ハイテク企業と直接のマネーゲームを繰り広げるのではなく、「安定性」「大規模データの取り扱い」「長期的なキャリアパス」という総合的な魅力度で人材を惹きつける、日本企業特有の採用戦略を体現している。 ###
```

### Rank 6
- score: 55.079392
- record_id: `notebook_cell_a5e6e1ea775001ee`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb Cell 12: code try: import pandas as pd import numpy as np import matplotlib.pyplot as plt import seaborn as sns cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist() summary_rows = [] for col in cat_cols: vc = df[col].astype('object').fillna('欠損').value_counts() top_val = vc.index[0] if len(vc) > 0 else np.nan top_cnt = vc.iloc[0] if len(vc) > 0 else np.nan summary_rows.append({ '列名': col, 'ユニーク数': df[col].nunique(dropna=True), '最頻値': top_val, '最頻値件数': top_cnt }) cat_summary = pd.DataFrame(summary_rows).sort_values(['ユニーク数', '列名']) if len(summary_rows) > 0 else pd.DataFrame() plot_cols = [c for c in cat_cols if c != target_col][:3] if len(plot_cols) > 0: fig, axes = plt.subplots(len(plot_cols), 1, figsize=(12, 4 * len(plot_cols))) if len(plot_cols) == 1: axes = [axes] for ax, col in zip(axes, plot_cols): vc = df[col].astype('object').fillna('欠損').value_counts().head(15) sns.barplot(x=vc.values, y=vc.index, ax=ax, palette='viridis') ax.set_title(f'{col} の分布（上位15件）') ax.set_xlabel('件数') ax.set_ylabel(col) plt.tight_layout() plt.savefig(FIG_DIR / 'categorical_distribution_top3.png', dpi=150, bbox_inches='tight') plt.close() except Exception as _eda_exc: category_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])] plot_cols = category_cols[:3] fig, axes = plt.subplots(1, 3, figsize=(18, 4)) for i, ax in enumerate(axes): if i < len(plot_cols): col = plot_cols[i] vc = df[col].astype(str).fillna("欠損").value_counts().head(10) vc.plot(kind="bar", ax=ax, color="#59a14f") ax.set_title(f"{col} 上位カテゴリ") ax.tick_params(axis="x", rotation=45) else: ax.axis("off") plt.tight_layout() plt.savefig(FIG_DIR / "categorical_distribution_top3.png", dpi=160, bbox_inches="tight")
```

### Rank 7
- score: 53.979299
- record_id: `notebook_cell_9f2d0cbd5d703899`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb Cell 20: code try: print('===== EDAサマリー =====') print(f'データサイズ: {df.shape[0]} 行 × {df.shape[1]} 列') missing = df.isnull().sum() missing = missing[missing > 0].sort_values(ascending=False) print('\n欠損のある列:') if len(missing) > 0: print(missing) num_cols = df.select_dtypes(include=[np.number]).columns.tolist() cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist() print(f'\n数値列数: {len(num_cols)}') print(f'カテゴリ列数: {len(cat_cols)}') if target_col in df.columns: y = pd.to_numeric(df[target_col], errors='coerce') print('\nターゲット要約:') print(y.describe()) print('\nターゲット分布:') print(y.value_counts().sort_index()) high_card = df.nunique(dropna=False).sort_values(ascending=False) print('\nユニーク数 上位10列:') print(high_card.head(10)) except Exception as _eda_exc: print(f"[warn] EDA section fallback: summary_code: {_eda_exc}") summary_rows = [] summary_rows.append(f"レコード数: {len(df):,}") summary_rows.append(f"列数: {df.shape[1]:,}") summary_rows.append(f"欠損率上位列: {', '.join((df.isna().mean()*100).sort_values(ascending=False).head(3).index.tolist())}") summary_rows.append(f"数値列数: {len(df.select_dtypes(include=['number']).columns)}") summary_rows.append(f"カテゴリ列数: {len([c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])])}") summary_rows.append(f"目的変数候補: {target_col}") print("主要サマリ") for row in summary_rows: print(f"- {row}") Output: ===== EDAサマリー ===== データサイズ: 11529 行 × 10 列 欠損のある列: Major 112 Experience 55 dtype: int64 数値列数: 1 カテゴリ列数: 9 ターゲット要約: count 11529.000000 mean 1.950820 std 1.653784 min 0.000000 25% 0.000000 50% 2.000000 75% 3.000000 max 5.000000 Name: target, dtype: float64 ターゲット分布: target 0 2963 1 2570 2 1633 3 1834 4 1492 5 1037 Name: count, dtype: int64 ユニーク数 上位10列: id 11529 Country 58 Profession 20 Industry 19 Major 14 Experience 12 Age 12 Education 7 target 6 Gender 4 dtype: int64 Output: C:\Users\hikeshita\AppData\Local\Temp\ipykernel_6848\2043349588.py:12: Pandas4Warning: For backward compatibility, 'str' dtypes are included by select_dtypes when 'object' dtype is specified. This behavior is deprecated and will be removed in a future version. Explicitly pass 'str' to include to select them, or to exclude to remove them and silence this warning. See https://pandas.pydata.org/docs/user_guide/migration-3-strings.html#string-migration-select-dtypes for details on how to write code that works with pandas 2 and 3. cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
```

### Rank 8
- score: 53.691766
- record_id: `notebook_cell_2001e952e53f9260`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb Cell 12: code try: from pathlib import Path import re cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist() cat_cols = [c for c in cat_cols if c != target_col] print('【カテゴリ列一覧】') print(cat_cols) summary_rows = [] for col in cat_cols: vc = df[col].value_counts(dropna=False) summary_rows.append({ '列名': col, 'ユニーク数': df[col].nunique(dropna=False), '最頻値': vc.index[0] if len(vc) > 0 else np.nan, '最頻値件数': vc.iloc[0] if len(vc) > 0 else np.nan }) if summary_rows: print('\n【カテゴリ列要約】') print(pd.DataFrame(summary_rows).sort_values('ユニーク数')) preferred = [c for c in ['term', 'grade', 'purpose'] if c in cat_cols] plot_cols = preferred[:3] if len(plot_cols) Asset: data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell012_output003.png Output: 【term と目的変数のクロス集計（行比率）】 loan_status 0 1 term 3 years 0.807904 0.192096 5 years 0.714218 0.285782 【grade と目的変数のクロス集計（行比率）】 loan_status 0 1 grade A1 0.960100 0.039900 A2 0.966725 0.033275 A3 0.787819 0.212181 A4 0.952744 0.047256 A5 0.945498 0.054502 B1 0.769231 0.230769 B2 0.800223 0.199777 B3 0.843775 0.156225 B4 0.828881 0.171119 B5 0.678886 0.321114 C1 0.831746 0.168254 C2 0.796982 0.203018 C3 0.885154 0.114846 C4 0.764839 0.235161 C5 0.787183 0.212817 D1 0.787313 0.212687 D2 0.760757 0.239243 D3 0.618361 0.381639 D4 0.586907 0.413093 D5 0.738574 0.261426 【purpose と目的変数のクロス集計（行比率）】 loan_status 0 1 purpose car 0.853786 0.146214 credit_card 0.832296 0.167704 debt_consolidation 0.770007 0.229993 home_improvement 0.865815 0.134185 house 0.902033 0.097967 major_purchase 0.208791 0.791209 medical 0.747967 0.252033 other 0.783603 0.216397 small_business 0.831461 0.168539
```
