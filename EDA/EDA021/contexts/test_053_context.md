# test_053

## Question
TOTOのFR書にて記載のある選択特徴量のうち、ENG-FTはいくつありますか。

## Route
fallback_bm25_llm

## Generated Answer
モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。

## Retrieved Records

### Rank 1
- score: 59.026642
- record_id: `generic_chunk_06c339eee5202c19`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
yle=Compact -->
T03: 0.7126899909960438

<!-- block_index=27 type=paragraph style=Compact -->
T05: 0.7126899909960438

<!-- block_index=28 type=paragraph style=Compact -->
run-level 指標（analysis.metrics より）:

<!-- block_index=29 type=paragraph style=Compact -->
auc_roc: 0.8250532501536466

<!-- block_index=30 type=paragraph style=Compact -->
precision_at_top10pct: 0.9428571428571428

<!-- block_index=31 type=paragraph style=Compact -->
brier_score: 0.17514583544772114

<!-- block_index=32 type=paragraph style=Compact -->
selected_feature_count: 10, excluded_feature_count: 1

<!-- block_index=33 type=paragraph style=Compact -->
実装／環境

<!-- block_index=34 type=paragraph style=Compact -->
実験は線形系（linear_baseline 系）モデル群で実施。decision-tuning（クラス判定重みの調整）が T04 の改善要因として報告されています（visible_trials の change_summary に記載）。

<!-- block_index=35 type=paragraph style=Heading 2 -->
## 3. 主要な分析結果

<!-- block_index=36 type=paragraph style=Compact -->
モデル比較（可視領域の要点）

<!-- block_index=37 type=paragraph style=Compact -->
ベースライン（T01）から段階的にクラスバランスや特徴量拡張、閾値調整を行い、T04（閾値チューニング済み線形モデル）が最も高い f1_macro を示した（f1_macro = 0.7329671168078127）。このことは、現データにおいて「モデル構造を大きく変えずに、決定閾値やクラス判断の調整で性能改善が得られる」ことを示唆します。

<!-- block_index=38 type=paragraph style=Compact -->
AUC-ROC（0.8250532501536466）や top10% precision（0.9428571428571428）が比較的良好である点は、スコア上位の予測が高い精度で陽性を含む可能性を示しており、閾値運用による業務ルール設計の余地があります。

<!-- block_index=39 type=paragraph style=Compact -->
特徴量・前処理の状況

<!-- block_index=40 type=paragraph style=Compact -->
モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。

<!-- block_in
```

### Rank 2
- score: 49.150417
- record_id: `pptx_slide_7b03e81b344bc0fe`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`

```text
Slide 5
4. 主要な分析結果 — データ品質・特徴選択
総レコード数
11,529 eda_summary.row_count
Targetクラス数
6 クラス 0〜5
選択特徴量数
14 feature_selection
欠損データ
Major: 112件（欠損率 ≒ 0.971%）
Experience: 55件（欠損率 ≒ 0.477%）
→ カテゴリ化等で対応済
選択特徴量（14変数）
Gender
Age
Country
Education
Major
Profession
Industry
Experience
Age_ord
Exp_ord
Edu_ord
Age×Exp
Age-Exp
Edu×Exp
■ 原特徴量 ■ エンジニアリング特徴量
除外列: id（identifier_like_name）
4 / 15
```

### Rank 3
- score: 41.448142
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

### Rank 4
- score: 41.448142
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

### Rank 5
- score: 41.334931
- record_id: `generic_chunk_e91ed8fc3abaa8c9`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx`

```text
_index=41 type=paragraph style=Compact -->
想定総工数: 170時間（assumption）
※上記はプロジェクト概要等に記載の想定値を参照していますが、本報告では Report facts JSON に未記載のため “assumption” として扱います。

<!-- block_index=42 type=paragraph style=Normal -->

<!-- block_index=43 type=paragraph style=Heading 2 -->
## 4. データ品質と実装状況

<!-- block_index=44 type=paragraph style=Compact -->
実装状況: 計画段階（analysis.implementation_status = “planning_only”）。モデル構築・学習は未実行。

<!-- block_index=45 type=paragraph style=Compact -->
データ品質（現時点の仮初期所見）:

<!-- block_index=46 type=paragraph style=Compact -->
データファイル想定パス: data.tsv（データ受領・読込を T02 で確認）

<!-- block_index=47 type=paragraph style=Compact -->
欠損・型・値域の確定は未済（T04 で評価予定）。したがって、欠損件数等の数値は現時点で未確定。

<!-- block_index=48 type=paragraph style=Compact -->
実行計画（前処理フェーズ）で決める主要ルール（予定）

<!-- block_index=49 type=paragraph style=Compact -->
識別子列（例: id）はモデル入力から除外

<!-- block_index=50 type=paragraph style=Compact -->
日付由来特徴量の作成（dteday → 年/月/日/祝日等）

<!-- block_index=51 type=paragraph style=Compact -->
カテゴリ変数の符号化ルール、数値欠損は中央値等での補完（詳細は前処理仕様書で記載）

<!-- block_index=52 type=paragraph style=Compact -->
トレース可能性: 実作業は WBS の T02〜T09 にて記録し、成果物（読込確認メモ、定義差異確認メモ、品質確認結果、初期EDA図表）を artifacts に格納します。

<!-- block_index=53 type=paragraph style=Normal -->

<!-- block_index=54 type=paragraph style=Heading 2 -->
## 5. リスクと対応策

<!-- block_index=55 type=paragraph style=Compact -->
リスク: データ定義不整合（高）

<!-- block_index=56 type=paragraph style=Compact -->
説明: yr と dteday 範囲不整合、workingday 定義表記の齟齬等が懸念される。

<!-- block_index=57 type=paragraph style=Compact -->
対策: Week1（T03）で優先的に定義確認を実施し、定義差異確認メモを作成して前処理仕様に反映。MS2（2025-07-29）到達をゲートとして扱う。

<!-- block_i
```

### Rank 6
- score: 39.318121
- record_id: `generic_chunk_1619d02ce3b4b250`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/社内用語集.docx`

```text
| 翌月持越し精算 |
| 単価据置 | RATE-HOLD | 単価変更なし |
| 契約差分なし | NO-CT-DELTA | 条件変更なし |

<!-- block_index=9 type=paragraph style=Normal -->
**4. データ・分析**

<!-- block_index=10 type=table rows=35 cols=3 -->
| 正式名称 | 社内用語 | 補足 |
| --- | --- | --- |
| 目的変数 | TG | Target |
| 説明変数 | FT | Feature |
| 数値特徴量 | NUM | Numeric Feature |
| カテゴリ特徴量 | CAT | Categorical Feature |
| 選択特徴量 | SEL-FT | Selected Feature |
| エンジニアリング特徴量 | ENG-FT | Engineered Feature |
| 交互作用特徴量 | INT-FT | Interaction Feature |
| 高カーディナリティ列 | HC-CAT | High Cardinality Category |
| 欠損補完 | IMP | Imputation |
| 中央値補完 | MED-IMP | Median Imputation |
| 最頻値補完 | MODE-IMP | Mode Imputation |
| One-Hot Encoding | OHE | One-Hot Encoding |
| 標準化 | STD | Standardization |
| 抽出条件 | FILTER-COND | 条件付き抽出 |
| 生特徴量 | RAW-FT | 元列そのままの特徴量 |
| 除外特徴量 | DROP-FT | モデル入力から除外 |
| 日付由来特徴量 | DATE-FT | date展開特徴量 |
| 周期特徴量 | CYCLE-FT | sin/cosなど |
| 文字列特徴量 | TEXT-FT | 文字列由来 |
| 識別子列 | ID-FT | id, code系 |
| リーク疑い特徴量 | TARGET-LEAK | target leakage候補 |
| 重要特徴量 | FT-IMP | importance対象 |
| 特徴量順位 | FT-RANK | ranking |
| ビニング特徴量 | BIN-FT | 離散化特徴量 |
| 初回EDA | EDA-INIT | 初回探索分析 |
| 再学習候補 | RETRAIN-CAND | 追加学習候補 |
| 閾値調整枠 | THR-WIN | しきい値調整工程 |
| 特徴量再検討 | FE-REVIEW | FE見直し |
| 採択モデル | ADOPT-MDL | 最終採用モデル |
| 暫定採用 | TEMP-ADOPT | 一時採用 |
| 本番化対象外 | NO-PROD | PoC止まり |
| 検証専用 | VAL-ONLY | 本番転用なし |
| 追加検証待ち | ADD-VAL-WAIT | 継続評価予定 |
| 再現確認済み | REPRO-OK | 結果再現済み |

<!-- block_index=11 type=paragraph style=Normal -->
**5. 評価指標**

<!-- block_index=12 type=table rows=22 cols=3 -->
| 正式名称 | 社内用語 | 補足 |
| --- | --- | --- |
| Accuracy | ACC | 分類 |
| F1-macro | F1M | 分類 |
| RO
```

### Rank 7
- score: 36.429042
- record_id: `pdf_page_fc7fc23db658c661`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

```text
1. エグゼクティブサマリ
事実と仮定の切り分け
確認済み事実
項目 内容
契約形態 time_and_materials
時間単価 25,000円/時間
消費税率 10%
対象データ data¥train.csv
データ規模 1,600件・8列・欠損0件
中間報告 2025-07-22
最終報告予定日 2025-08-05
最終評価値 Accuracy 0.8656 / Macro F1 0.7423
選択特徴量数 9
本報告で明示的に仮定として扱う事項
1 最終報告会の開催議事録（M03）は提示資料中に未収録のため、納品・説
明完了の詳細証跡は提出済み成果物一式に依拠する前提
2 クラス別Precision/Recall、混同行列、重要変数順位の最終確定値は本
入力資料に明示がないため、方向性整理は行うが未提示数値の断定は避け
る
3 実績工数の最終確定値は提示資料に含まれないため、請求金額欄は契約
上の見込工数170時間を用いた精算想定値として記載する
```

### Rank 8
- score: 36.125746
- record_id: `notebook_cell_04a5b87e27c4aff8`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 16: code
try:
 from pathlib import Path

 corr_df = df.copy()
 for col in corr_df.columns:
 if corr_df[col].dtype == 'object' or str(corr_df[col].dtype).startswith('category'):
 corr_df[col] = pd.to_numeric(corr_df[col], errors='ignore')

 num_df = corr_df.select_dtypes(include=[np.number]).copy()
 if target_col in corr_df.columns and target_col not in num_df.columns:
 target_num = pd.to_numeric(corr_df[target_col], errors='coerce')
 if target_num.notna().sum() > 0:
 num_df[target_col] = target_num

 print('===== 相関確認 =====')
 plt.figure(figsize=(8, 6))
 if num_df.shape[1] >= 2:
 corr = num_df.corr(numeric_only=True)
 print(corr)
 sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', square=True)
 plt.title('数値特徴量の相関ヒートマップ')
 else:
 plt.text(0.5, 0.5, '相関を計算できる数値列が不足しています', ha='center', va='center', fontsize=14)
 plt.title('数値特徴量の相関ヒートマップ')
 plt.axis('off')
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

Output: ===== 相関確認 =====

Output: <Figure size 800x600 with 1 Axes>
Asset: data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell016_output002.png
```
