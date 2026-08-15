# test_073

## Question
恒一会のPPで言及されている One-Hot Encoding のカテゴリ数閾値を実装設定から確認したうえで、その条件により One-Hot Encoding の対象となるカテゴリ列をすべて答えてください。

## Route
fallback_bm25_llm

## Generated Answer
「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。、低カードinalityのカテゴリ列に対するOne-Hot Encoding、閾値未満のカテゴリ数の場合に適用、高カーディナリティのカテゴリ列はモデリング対象外、カテゴリ数が閾値未満の場合にone-hot encoding適用

## Retrieved Records

### Rank 1
- score: 156.84064
- record_id: `pptx_slide_25ec3c6aeb4d5ff9`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`

```text
Slide 9
04
4.2 前処理方針
対象
処理方法
詳細
除外
id列
識別子のためモデリングから除外
除外
日付列
本件データに日時情報がないため実施しない
数値欠損
中央値補完
数値欠損値が存在する場合に適用
カテゴリ欠損
最頻値補完
カテゴリ欠損値が存在する場合に適用
カテゴリ変換
One-Hot Encoding
閾値未満のカテゴリ数の場合に適用
高カーディナリティ
除外
高カーディナリティのカテゴリ列は除外
Gender列
標準カテゴリ変換
2値カテゴリのため標準的な変換対象
※本データでは欠損値は存在しない前提であるが、実装上は再現性確保のため補完ルールを定義したうえで処理系に組み込む。
```

### Rank 2
- score: 102.275343
- record_id: `pptx_slide_d99afc1ac6394602`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/提案書.pptx`

```text
Slide 6
4. 分析アプローチ：データ処理方針
STEP 1
識別子除外
id等の識別子列はモデリング対象から除外
STEP 2
数値欠損処理
中央値補完を適用
STEP 3
カテゴリ欠損処理
最頻値補完を適用
STEP 4
エンコーディング
カテゴリ数が閾値未満の場合にone-hot encoding適用
STEP 5
高カーディナリティ除外
高カーディナリティのカテゴリ列はモデリング対象外
データ特性に関する留意事項
本データは実質的にカテゴリ中心の構成であるため、カテゴリ分布の偏在や長尾カテゴリの扱いを重視する
Age、Education、Experienceは順序性を持つ可能性があるが、本初期フェーズでは多クラス分類の標準実装をベースとし、解釈面で順序性を補足する
日付列が存在する場合のみ日付由来特徴量を追加するが、本データは時間粒度を持たないため時系列特徴量追加は行わない
6
```

### Rank 3
- score: 83.17841
- record_id: `generic_chunk_5a417e625ad72ddb`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/01.契約/契約書.docx`

```text
ompact -->
値分布確認

<!-- block_index=28 type=paragraph style=Compact -->
標準実装による前処理

<!-- block_index=29 type=paragraph style=Compact -->
id のような識別子列の除外

<!-- block_index=30 type=paragraph style=Compact -->
数値欠損値が存在する場合の中央値補完

<!-- block_index=31 type=paragraph style=Compact -->
カテゴリ欠損値が存在する場合の最頻値補完

<!-- block_index=32 type=paragraph style=Compact -->
有効な日付列が存在する場合に限る日付由来特徴量の追加

<!-- block_index=33 type=paragraph style=Compact -->
低カードinalityのカテゴリ列に対するOne-Hot Encoding

<!-- block_index=34 type=paragraph style=Compact -->
高カードinalityのカテゴリ列の除外

<!-- block_index=35 type=paragraph style=Compact -->
学習用・評価用データ分割

<!-- block_index=36 type=paragraph style=Compact -->
基礎集計

<!-- block_index=37 type=paragraph style=Compact -->
クラス分布

<!-- block_index=38 type=paragraph style=Compact -->
変数分布

<!-- block_index=39 type=paragraph style=Compact -->
目的変数別比較

<!-- block_index=40 type=paragraph style=Compact -->
ベースラインモデルおよび説明可能な初期モデルの構築

<!-- block_index=41 type=paragraph style=Compact -->
モデル評価

<!-- block_index=42 type=paragraph style=Compact -->
混同行列

<!-- block_index=43 type=paragraph style=Compact -->
Accuracy

<!-- block_index=44 type=paragraph style=Compact -->
Macro F1

<!-- block_index=45 type=paragraph style=Compact -->
クラス別Precision / Recall

<!-- block_index=46 type=paragraph style=Compact -->
モデル解釈

<!-- block_index=47 type=paragraph style=Compact -->
重要変数整理

<!-- block_index=48 type=paragraph style=Compact -->
属性別傾向整理

<!-- block_index=49 type=paragraph style=Compact -->
業務示唆整理

<!-- block_index=50 type=paragraph style=Compact -->
中間報告および最終報告の作成・説明

<!-- block_index=51 type=pa
```

### Rank 4
- score: 81.767836
- record_id: `generic_chunk_0ec626ab1150778a`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
yle=Normal -->

<!-- block_index=27 type=paragraph style=Heading 2 -->
## 3. キックオフ時点の確認事項

<!-- block_index=28 type=paragraph style=First Paragraph -->
キックオフ時点では、分析結果ではなく前提確認とデータ受領状況のみを共有する。

<!-- block_index=29 type=paragraph style=Compact -->
データ概要

<!-- block_index=30 type=paragraph style=Compact -->
レコード数: 17,500

<!-- block_index=31 type=paragraph style=Compact -->
カラム数: 10

<!-- block_index=32 type=paragraph style=Compact -->
欠損: 全項目 <span data-font-color="#FF0000" style="color:#FF0000">0.0</span>（初期前処理における欠損補完は不要）

<!-- block_index=33 type=paragraph style=Compact -->
分析着手前の整理事項

<!-- block_index=34 type=paragraph style=Compact -->
学習行数: 14,000、検証行数: 3,500

<!-- block_index=35 type=paragraph style=Compact -->
解析上の示唆（初期）

<!-- block_index=36 type=paragraph style=Compact -->
欠損がないため、前処理コストは低い。一方で、順序カテゴリ（grade, employment_length, term）や金利（interest_rate）の業務意味（審査時点で利用可能か）が解析と運用で異なる可能性があるため、変数の扱いを二通り（運用可能変数のみ／すべての変数）で評価する必要あり。

<!-- block_index=37 type=paragraph style=Compact -->
時系列情報が欠落しているため、ドリフト検知やビンテージ分析は本データ単体で実施不可。

<!-- block_index=38 type=paragraph style=Compact -->
留意点

<!-- block_index=39 type=paragraph style=Compact -->
「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。

<!-- block_index=40 type=paragraph style=Normal -->

<!-- block_index=41 type=paragraph style=Heading 2 -->
## 4. データ品質と実装状況

<!-- block_index=42 type=paragraph style=Compact -->
データ品質

<!-- block_index=43 type=paragraph style=Compact -->
欠損: 全カラムで 0%（eda_summary.mis
```

### Rank 5
- score: 77.59069
- record_id: `notebook_cell_cfa41f04104b4754`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 12: code
try:
 cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
 selected_cat_cols = cat_cols[:3]
 print('カテゴリ列一覧')
 print(cat_cols)
 for col in selected_cat_cols:
 print(f'{col} の度数分布')
 print(df[col].value_counts(dropna=False).head(20))
 plt.figure(figsize=(18, 5))
 if len(selected_cat_cols) > 0:
 for i, col in enumerate(selected_cat_cols, 1):
 plt.subplot(1, len(selected_cat_cols), i)
 vc = df[col].astype(str).value_counts(dropna=False).head(10)
 sns.barplot(x=vc.values, y=vc.index, palette='viridis')
 plt.title(f'{col} の分布')
 plt.xlabel('件数')
 plt.ylabel(col)
 plt.tight_layout()
 else:
 plt.text(0.5, 0.5, 'カテゴリ列はありません', ha='center', va='center', fontsize=14)
 plt.title('カテゴリ列の分布')
 plt.axis('off')
 plt.tight_layout()
 plt.savefig(FIG_DIR / 'categorical_distribution_top3.png', dpi=150, bbox_inches='tight')
 plt.show()
 plt.close()
except Exception as _eda_exc:
 print(f"[warn] EDA section fallback: categorical_code: {_eda_exc}")
 category_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
 plot_cols = category_cols[:3]
 fig, axes = plt.subplots(1, 3, figsize=(18, 4))
 for i, ax in enumerate(axes):
 if i < len(plot_cols):
 col = plot_cols[i]
 vc = df[col].astype(str).fillna("欠損").value_counts().head(10)
 vc.plot(kind="bar", ax=ax, color="#59a14f")
 ax.set_title(f"{col} 上位カテゴリ")
 ax.tick_params(axis="x", rotation=45)
 else:
 ax.axis("off")
 plt.tight_layout()
 plt.savefig(FIG_DIR / "categorical_distribution_top3.png", dpi=160, bbox_inches="tight")
 plt.show()

Output: カテゴリ列一覧
['Gender']
Gender の度数分布
Gender
Male 2930
Female 570
Name: count, dtype: int64

Output: C:\Users\hikeshita\AppData\Local\Temp\ipykernel_26524\2964952144.py:2: Pandas4Warning: For backward compatibility, 'str' dtypes are included by select_dtypes when 'object' dtype is specified. This behavior is deprecated and will be removed in a future version. Explicitly pass 'str' to `include` to select them, or to `exclude` to remove them and silence this warning.
See https://pandas.pydata.org/docs/user_guide/migration-3-strings.html#string-migration-select-dtypes for details on how to write code that works with pandas 2 and 3.
 cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
C:\Users\hikeshita\AppData\Local\Temp\ipykernel_26524\2964952144.py:14: FutureWarning: 

Passing `palette` without assigning `hue` is deprecated and will be removed in v0.14.0. Assign the `y` variable to `hue` and set `legend=False` for the same effect.

 sns.barplot(x=vc.values, y=vc.index, palette='viridis')

Output: <Figure size 1800x500 with 1 Axes>
Asset: data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell012_output003.png
```

### Rank 6
- score: 77.230101
- record_id: `notebook_cell_9c3e108797d154e0`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 12: code
try:
 import matplotlib.pyplot as plt
 from pathlib import Path

 cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
 small_num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if df[c].nunique(dropna=False) <= 10 and c != target_col]
 plot_cols = cat_cols + small_num_cols
 plot_cols = plot_cols[:3]

 print('カテゴリ列候補')
 for c in cat_cols + small_num_cols:
 print(f'\n[{c}]')
 print(df[c].value_counts(dropna=False).head(20))

 Path(FIG_DIR).mkdir(parents=True, exist_ok=True)
 if len(plot_cols) > 0:
 n = len(plot_cols)
 fig, axes = plt.subplots(n, 1, figsize=(12, 4 * n))
 if n == 1:
 axes = [axes]
 for ax, col in zip(axes, plot_cols):
 vc = df[col].astype(str).value_counts(dropna=False).head(10)
 sns.barplot(x=vc.values, y=vc.index, ax=ax, color='seagreen')
 ax.set_title(f'{col} のカテゴリ分布（上位10件）')
 ax.set_xlabel('件数')
 ax.set_ylabel(col)
 plt.tight_layout()
 plt.savefig(Path(FIG_DIR) / 'categorical_distribution_top3.png', dpi=150, bbox_inches='tight')
 plt.show()
 plt.close()
 else:
 fig, ax = plt.subplots(figsize=(8, 3))
 ax.axis('off')
 ax.text(0.5, 0.5, 'カテゴリ列は見つかりませんでした', ha='center', va='center', fontsize=12)
 plt.tight_layout()
 plt.savefig(Path(FIG_DIR) / 'categorical_distribution_top3.png', dpi=150, bbox_inches='tight')
 plt.show()
 plt.close()
except Exception as _eda_exc:
 print(f"[warn] EDA section fallback: categorical_code: {_eda_exc}")
 category_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
 plot_cols = category_cols[:3]
 fig, axes = plt.subplots(1, 3, figsize=(18, 4))
 for i, ax in enumerate(axes):
 if i < len(plot_cols):
 col = plot_cols[i]
 vc = df[col].astype(str).fillna("欠損").value_counts().head(10)
 vc.plot(kind="bar", ax=ax, color="#59a14f")
 ax.set_title(f"{col} 上位カテゴリ")
 ax.tick_params(axis="x", rotation=45)
 else:
 ax.axis("off")
 plt.tight_layout()
 plt.savefig(FIG_DIR / "categorical_distribution_top3.png", dpi=160, bbox_inches="tight")
 plt.show()

Output: カテゴリ列候補

Output: <Figure size 800x300 with 1 Axes>
Asset: data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell012_output002.png
```

### Rank 7
- score: 75.9784
- record_id: `notebook_cell_840ce7c802daa9b8`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 20: code
try:
 print('EDAサマリー')
 print('1. データ形状、型、基本統計量を確認しました。')
 print('2. 欠損は主に LAND SQUARE FEET、GROSS SQUARE FEET、TAX CLASS AT PRESENT、BUILDING CLASS AT PRESENT に存在します。')
 print('3. 数値列は外れ値や歪みを含む可能性があるため、対数変換やロバスト処理を検討できます。')
 print('4. カテゴリ列は高頻度カテゴリへの偏りを確認済みです。')
 print('5. 目的変数の分布と対数分布を確認しました。')
 print('6. 数値特徴量間および目的変数との相関を確認しました。')
 print('7. 日付列候補は pure day number 判定を考慮して探索しました。')
except Exception as _eda_exc:
 print(f"[warn] EDA section fallback: summary_code: {_eda_exc}")
 summary_rows = []
 summary_rows.append(f"レコード数: {len(df):,}")
 summary_rows.append(f"列数: {df.shape[1]:,}")
 summary_rows.append(f"欠損率上位列: {', '.join((df.isna().mean()*100).sort_values(ascending=False).head(3).index.tolist())}")
 summary_rows.append(f"数値列数: {len(df.select_dtypes(include=['number']).columns)}")
 summary_rows.append(f"カテゴリ列数: {len([c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])])}")
 summary_rows.append(f"目的変数候補: {target_col}")
 print("主要サマリ")
 for row in summary_rows:
 print(f"- {row}")

Output: EDAサマリー
1. データ形状、型、基本統計量を確認しました。
2. 欠損は主に LAND SQUARE FEET、GROSS SQUARE FEET、TAX CLASS AT PRESENT、BUILDING CLASS AT PRESENT に存在します。
3. 数値列は外れ値や歪みを含む可能性があるため、対数変換やロバスト処理を検討できます。
4. カテゴリ列は高頻度カテゴリへの偏りを確認済みです。
5. 目的変数の分布と対数分布を確認しました。
6. 数値特徴量間および目的変数との相関を確認しました。
7. 日付列候補は pure day number 判定を考慮して探索しました。
```

### Rank 8
- score: 73.980463
- record_id: `notebook_cell_50021155cb6cd3ac`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 12: code
try:
 import math
 from pathlib import Path

 Path(FIG_DIR).mkdir(parents=True, exist_ok=True)

 cat_cols = [c for c in df.columns if c != target_col and (df[c].dtype == 'object' or str(df[c].dtype) == 'category')]
 plot_cols = cat_cols[:3]

 if len(plot_cols) > 0:
 n = len(plot_cols)
 fig, axes = plt.subplots(1, n, figsize=(6 * n, 4))
 if n == 1:
 axes = [axes]
 for ax, col in zip(axes, plot_cols):
 vc = df[col].fillna('欠損').value_counts().head(15)
 sns.barplot(x=vc.values, y=vc.index.astype(str), ax=ax, color='mediumpurple')
 ax.set_title(f'{col} のカテゴリ分布')
 ax.set_xlabel('件数')
 ax.set_ylabel(col)
 plt.tight_layout()
 plt.savefig(Path(FIG_DIR) / 'categorical_distribution_top3.png', dpi=150, bbox_inches='tight')
 plt.show()
 plt.close()

 print('【カテゴリ列サマリー】')
 summary = []
 for col in cat_cols:
 summary.append({
 '列名': col,
 'ユニーク数': int(df[col].nunique(dropna=True)),
 '最頻値': None if df[col].dropna().empty else df[col].mode(dropna=True).iloc[0],
 '最頻値件数': 0 if df[col].dropna().empty else int(df[col].value_counts(dropna=True).iloc[0])
 })
 print(pd.DataFrame(summary))
except Exception as _eda_exc:
 print(f"[warn] EDA section fallback: categorical_code: {_eda_exc}")
 category_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
 plot_cols = category_cols[:3]
 fig, axes = plt.subplots(1, 3, figsize=(18, 4))
 for i, ax in enumerate(axes):
 if i < len(plot_cols):
 col = plot_cols[i]
 vc = df[col].astype(str).fillna("欠損").value_counts().head(10)
 vc.plot(kind="bar", ax=ax, color="#59a14f")
 ax.set_title(f"{col} 上位カテゴリ")
 ax.tick_params(axis="x", rotation=45)
 else:
 ax.axis("off")
 plt.tight_layout()
 plt.savefig(FIG_DIR / "categorical_distribution_top3.png", dpi=160, bbox_inches="tight")
 plt.show()

Output: 【カテゴリ列サマリー】
Empty DataFrame
Columns: []
Index: []
```
