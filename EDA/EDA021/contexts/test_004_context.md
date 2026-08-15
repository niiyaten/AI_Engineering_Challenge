# test_004

## Question
蒼泉会 ひがし丘総合病院の01_eda.ipynbを確認して、目的変数と相関が最も高い数値特徴量を教えてください。

## Route
code_reading

## Generated Answer
print('6. 数値特徴量間および目的変数との相関を確認しました。')

## Retrieved Records

### Rank 1
- score: 103.913434
- record_id: `notebook_cell_a4d1a8da61d345f6`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 2: markdown
## 固定EDA計画
1. データ読み込みと基本確認
2. 列型・記述統計の確認
3. 欠損率の集計と可視化
4. 数値列の分布確認
5. カテゴリ列の主要分布確認
6. 目的変数の分布と偏り確認
7. 数値特徴量の相関確認
8. 日付列の時系列傾向確認（存在時）
9. 観察結果サマリ
```

### Rank 2
- score: 102.997694
- record_id: `notebook_cell_dc434c60cec831e2`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 16: markdown
最も相関が高いのはchargesとageの組み合わせ
```

### Rank 3
- score: 101.220778
- record_id: `notebook_cell_4c1865976fa905e5`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 9: markdown
## 3. 数値特徴量の分布
```

### Rank 4
- score: 97.305655
- record_id: `pdf_page_6905247b1de97962`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

```text
3. 実施方法
プロジェクト全体進行
Phase 1
立上げ・要件確認
07/08
キックオフ
Phase 2
データ理解・基礎集計
07/09-07/18
データ確認・基礎集計
Phase 3
モデリング・評価
07/16-07/29
モデル構築・比較・評価
Phase 4
示唆整理・最終報告
07/30-08/05
業務提言・報告書作成
データ確認と前提固定
項目 内容
対象ファイル data¥train.csv
行数 1,600
列数 8
欠損 全列0件
文字コード utf-8-sig
目的変数 charges
除外列 id
前処理方針
ID除外
id は識別子として除外
カテゴリ処理
sex, smoker, region を対象
相互作用特徴量
数値相互作用特徴量を追加（use_numeric_interactions = true）
時系列特徴量
date_column が null/空のため実質追加なし
※ 数値相互作用特徴量は、説明性を保ちながら表現力を補強するための拡張として運用された
```

### Rank 5
- score: 95.929466
- record_id: `notebook_cell_4beea675ae7b9775`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 17: code
try:
 from pathlib import Path

 Path(FIG_DIR).mkdir(parents=True, exist_ok=True)

 num_df = df.select_dtypes(include=[np.number]).copy()
 if target_col in df.columns and target_col not in num_df.columns:
 try:
 num_df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
 except Exception:
 pass

 corr = num_df.corr(numeric_only=True)
 print('【相関行列】')
 print(corr)

 if corr.shape[0] > 0:
 plt.figure(figsize=(8, 6))
 sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, square=False)
 plt.title('特徴量の相関ヒートマップ')
 plt.tight_layout()
 plt.savefig(Path(FIG_DIR) / 'feature_correlation_heatmap.png', dpi=150, bbox_inches='tight')
 plt.show()
 plt.close()
except Exception as _eda_exc:
 print(f"[warn] EDA section fallback: corr_code: {_eda_exc}")
 numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
 fig, ax = plt.subplots(figsize=(10, 8))
 if len(numeric_cols) >= 2:
 corr = df[numeric_cols[:20]].corr(numeric_only=True)
 sns.heatmap(corr, cmap="coolwarm", center=0, ax=ax)
 ax.set_title("数値特徴量の相関ヒートマップ（先頭20列）")
 else:
 ax.axis("off")
 ax.text(0.5, 0.5, "相関分析に十分な数値列がありません", ha="center", va="center", fontsize=12)
 plt.tight_layout()
 plt.savefig(FIG_DIR / "feature_correlation_heatmap.png", dpi=160, bbox_inches="tight")
 plt.show()

Output: 【相関行列】
 id age bmi children charges
id 1.000000 0.005803 0.039221 0.012440 0.013463
age 0.005803 1.000000 0.019885 0.011519 0.102112
bmi 0.039221 0.019885 1.000000 0.083677 0.171282
children 0.012440 0.011519 0.083677 1.000000 0.026830
charges 0.013463 0.102112 0.171282 0.026830 1.000000

Output: <Figure size 800x600 with 2 Axes>
Asset: data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell017_output002.png
```

### Rank 6
- score: 93.865232
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

### Rank 7
- score: 85.247208
- record_id: `pdf_page_c2a61af291cf8644`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

```text
4. 主要な分析結果
分析結果サマリと特徴量構成
項目 値
row_count 1,600
train_rows 1,280
test_rows 320
accuracy 0.865625
f1_macro 0.742292
selected_feature_count 9
excluded_feature_count 4
特徴量構成（9列）
基本特徴量（6列）
age sex bmi
children smoker region
相互作用特徴量（3列）
age × bmi age × bmi ×
除外列（4列）
id id×age id×bmi id×childr
解釈
モデルは基本属性6項目に加え、年齢・BMI・子供数の相互作用を含めて最終化されている
価格帯の判定が単独変数の水準だけでなく、変数同士の組合せ関係にも依存しうることを示唆する
smoker、bmi、ageは当初から重要候補として位置づけられていた変数群であり、最終モデルでも関連する特徴空間に含まれている
「年齢が高くBMIも高い群」「年齢と家族構成が組み合わさる群」で価格帯分布が変わる可能性がある
```

### Rank 8
- score: 83.588443
- record_id: `pdf_page_21d14b97fbfc0029`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

```text
医療法人社団 蒼泉会 ひがし丘総合病院
最終分析報告書
医療費関連の価格帯分類と要因分析プロジェクト
契約期間: 2025-07-08 ～ 2025-08-05（5週間）
対象データ: data¥train.csv | 1,600件・8列・欠損0件
目的変数: charges（価格帯 0/1/2 の3クラス分類）
最終評価指標
Accuracy 0.8656
Macro F1 0.7423
```
