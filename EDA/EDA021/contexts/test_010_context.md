# test_010

## Question
恒一会 かえで総合病院のtrain.xlsxにおいて、AG_ratioのヒストグラムで最も多いカウント数はいくつですか。

## Route
table_calculation

## Generated Answer
Asset: data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell014_output003.png

## Retrieved Records

### Rank 1
- score: 76.303872
- record_id: `notebook_cell_b38d066baeffeb12`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 14: code
try:
 print('目的変数の分布')
 print(df[target_col].value_counts(dropna=False).sort_index())
 print('目的変数の割合')
 print((df[target_col].value_counts(dropna=False, normalize=True).sort_index() * 100).round(2))
 plt.figure(figsize=(6, 4))
 order = sorted(df[target_col].dropna().unique().tolist())
 sns.countplot(data=df, x=target_col, order=order, palette='Set2')
 plt.title('目的変数の分布')
 plt.xlabel('クラス')
 plt.ylabel('件数')
 plt.tight_layout()
 plt.savefig(FIG_DIR / 'target_distribution.png', dpi=150, bbox_inches='tight')
 plt.show()
 plt.close()
 num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col and c != 'id']
 if len(num_cols) > 0:
 diff = df.groupby(target_col)[num_cols].mean().T
 diff.columns = [f'クラス_{c}' for c in diff.columns]
 print('目的変数ごとの数値列平均')
 print(diff)
except Exception as _eda_exc:
 print(f"[warn] EDA section fallback: target_code: {_eda_exc}")
 series = df[target_col]
 fig, ax = plt.subplots(1, 2, figsize=(14, 4))
 if pd.api.types.is_numeric_dtype(series):
 uniq = series.dropna().nunique()
 if uniq > 20:
 sns.histplot(series.dropna(), bins=30, ax=ax[0], color="#f28e2b")
 ax[0].set_title("目的変数ヒストグラム")
 sns.boxplot(x=series.dropna(), ax=ax[1], color="#e15759")
 ax[1].set_title("目的変数ボックスプロット")
 else:
 vc = series.value_counts(dropna=False).sort_index()
 vc.plot(kind="bar", ax=ax[0], color="#f28e2b")
 ax[0].set_title("目的変数カテゴリ分布")
 (vc / vc.sum() * 100).round(2).plot(kind="bar", ax=ax[1], color="#e15759")
 ax[1].set_title("目的変数カテゴリ比率(%)")
 else:
 vc = series.astype(str).fillna("欠損").value_counts().head(20)
 vc.plot(kind="bar", ax=ax[0], color="#f28e2b")
 ax[0].set_title("目的変数カテゴリ分布")
 (vc / vc.sum() * 100).round(2).plot(kind="bar", ax=ax[1], color="#e15759")
 ax[1].set_title("目的変数カテゴリ比率(%)")
 plt.tight_layout()
 plt.savefig(FIG_DIR / "target_distribution.png", dpi=160, bbox_inches="tight")
 plt.show()

Output: 目的変数の分布
disease
0 2054
1 1446
Name: count, dtype: int64
目的変数の割合
disease
0 58.69
1 41.31
Name: proportion, dtype: float64

Output: C:\Users\hikeshita\AppData\Local\Temp\ipykernel_26524\2580755668.py:8: FutureWarning: 

Passing `palette` without assigning `hue` is deprecated and will be removed in v0.14.0. Assign the `x` variable to `hue` and set `legend=False` for the same effect.

 sns.countplot(data=df, x=target_col, order=order, palette='Set2')

Output: <Figure size 600x400 with 1 Axes>
Asset: data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell014_output003.png
Output: 目的変数ごとの数値列平均
 クラス_0 クラス_1
Age 46.494158 43.665284
T_Bil 0.964897 3.274925
D_Bil 0.214108 1.412094
ALP 193.348998 272.217098
ALT_GPT 19.658627 68.715102
AST_GOT 25.257543 58.736706
TP 6.598225 6.326069
Alb 3.774216 3.382087
AG_ratio 0.930002 0.805385
```

### Rank 2
- score: 65.404823
- record_id: `pptx_slide_b792551ccdc031fa`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`

```text
Slide 5
4. データ概要と特徴量選定
データ基本情報（EDA出力）
3,500行
行数
12列
カラム数
なし
欠損値
disease (0/1)
目的変数
特徴量選定
全カラム（12列）
id / Age / Gender
T_Bil / D_Bil / ALP
ALT_GPT / AST_GOT
TP / Alb / AG_ratio
disease
特徴量
選定
選択特徴量（10列）
Age / Gender
T_Bil / D_Bil / ALP
ALT_GPT / AST_GOT
TP / Alb / AG_ratio
除外（1列）
id
（identifier_like_name）
```

### Rank 3
- score: 65.404823
- record_id: `pptx_slide_fd9d82b3e977362b`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`

```text
Slide 5
4. データ概要と特徴量選定
データ基本情報（EDA出力）
3,500行
行数
12列
カラム数
なし
欠損値
disease (0/1)
目的変数
特徴量選定
全カラム（12列）
id / Age / Gender
T_Bil / D_Bil / ALP
ALT_GPT / AST_GOT
TP / Alb / AG_ratio
disease
特徴量
選定
選択特徴量（10列）
Age / Gender
T_Bil / D_Bil / ALP
ALT_GPT / AST_GOT
TP / Alb / AG_ratio
除外（1列）
id
（identifier_like_name）
```

### Rank 4
- score: 63.841321
- record_id: `metadata_8cda600cb73d3838`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`

```text
ファイル名: 医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx
ファイル種別: pptx
```

### Rank 5
- score: 63.841321
- record_id: `metadata_d570985f0177469e`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`

```text
ファイル名: 医療法人社団 恒一会 かえで総合病院_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx
ファイル種別: pptx
```

### Rank 6
- score: 62.686546
- record_id: `metadata_dbe8ba95a8cf1738`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.xlsx`

```text
ファイル名: train.xlsx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.xlsx
ファイル種別: xlsx
```

### Rank 7
- score: 60.284145
- record_id: `metadata_9d72dff44927aea8`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/data/カラム説明.md`

```text
ファイル名: カラム説明.md
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/data/カラム説明.md
ファイル種別: md
```

### Rank 8
- score: 60.093049
- record_id: `metadata_6af666c6c79848c1`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/カラム説明.md`

```text
ファイル名: カラム説明.md
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/カラム説明.md
ファイル種別: md
```
