# test_084

## Question
東都人材プラットフォームの最終報告書で分析結果が記載されている中で、モデル毎のF1スコアがランキング形式で記載されているページ数を教えてください。

## Route
document_whole_context

## Generated Answer
株式会社東都人材プラットフォーム（発注者）と株式会社データアステル（受託者）により、

## Retrieved Records

### Rank 1
- score: 147.144089
- record_id: `generic_chunk_56531f6bc167815e`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
k_index=40 type=paragraph style=Compact -->
モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。

<!-- block_index=41 type=paragraph style=Compact -->
モデル群は線形系での評価を優先しているため、説明可能性が確保された状態での比較が行われています。

<!-- block_index=42 type=paragraph style=Compact -->
臨床的解釈上の留意

<!-- block_index=43 type=paragraph style=Compact -->
本段階での結果は学習データ内（ホールドアウト検証等）での指標であり、外部検証データや運用環境での再現性は未確認です。運用導入の判断には追加検証（外部データや診療フローを反映した評価）が必要です。

<!-- block_index=44 type=paragraph style=Heading 2 -->
## 4. データ品質と実装状況

<!-- block_index=45 type=paragraph style=Compact -->
データ受領／EDA／前処理

<!-- block_index=46 type=paragraph style=Compact -->
キックオフ（M01）での合意に基づき EDA・前処理方針を実施し、可視実験群を生成しています（visible_trials 実行）。feature_selection の結果（selected 10, excluded 1）が得られています。

<!-- block_index=47 type=paragraph style=Compact -->
欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。

<!-- block_index=48 type=paragraph style=Compact -->
例: 「train.csv の行数 = 3,500」「欠損数 = 0」はプロジェクト概要に記載されているが、Report facts JSON に explicit に含まれないため本レポートでは（assumption）として扱います。

<!-- block_index=49 type=paragraph style=Compact -->
実装ステータス（analysis.implementation_status）

<!-- block_index=50 type=paragraph style=Compact -->
実装ステータスは “interim_analysis”（中間分析段階）。モデル構築・比較は実施済み（visible_trials）が、最終モデル確定・本番化は未実施。

<!-- block_index=51 type=paragraph style=Compact -->
再現性トレース

<!-- block_index=52 type=paragraph style=Compact -->
実行結果・ソースのトレースは Report facts の trace.source_files に保存パスが示されています（例: artifacts/analysis_o
```

### Rank 2
- score: 117.571649
- record_id: `pptx_slide_73f56f49252ab578`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`

```text
Slide 6
4. 主要な分析結果 — モデル性能比較
| col_1 | col_2 | col_3 | col_4 |
| --- | --- | --- | --- |
| 順位 | モデルタイプ | Macro F1 | Accuracy |
| 1 | hist_gradient_boosting | 0.4736 | 0.5104 |
| 2 | hist_gradient_boosting | 0.4731 | 0.5082 |
| 3 | random_forest | 0.4648 | 0.4879 |
| 4 | hist_gradient_boosting | 0.4607 | 0.4996 |
| 5 | linear_baseline | 0.4493 | 0.4731 |
| 6 | linear_baseline | 0.4488 | 0.4722 |
中間試行の推移: 線形ベースライン(T01: F1=0.309) → 順序情報導入(T03: F1=0.449) → 非線形モデル(最終: F1=0.474)
過学習の状況: Train F1≈0.645 vs Val F1≈0.620 — テストでの低下は限定的だが過学習リスクに注意
Chart: {"chart_type": "BAR_CLUSTERED (57)", "title": "モデル別性能比較", "series_count": 2, "category_axis_title": "", "value_axis_title": ""}
5 / 15
```

### Rank 3
- score: 117.387567
- record_id: `metadata_a303480473fd6bdd`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`

```text
ファイル名: 株式会社東都人材プラットフォーム_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
ファイル種別: pptx
```

### Rank 4
- score: 114.944529
- record_id: `pptx_slide_7fc0a887d55d3975`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`

```text
Slide 2
1. エグゼクティブサマリ
プロジェクト概要
株式会社東都人材プラットフォーム（発注者）と株式会社データアステル（受託者）により、
人材属性データを用いた「収入クラス（target）予測モデル」の企画・分析設計・初期検証を行った6週間の案件である。
主目的は収入クラスの予測可能性と主要因の抽出、People Analyticsにおける報酬分析基盤の初期版提供である。
Accuracy
0.510
Macro F1
0.474
最終実行設定
モデル: hist_gradient_boosting
行数: 11,529 / 特徴量: 14
検証分割: random_holdout (val=0.1)
本フェーズの成果物
再現可能な前処理仕様 ／ 評価結果表 ／ 可視化図表 ／ 再現可能な分析スクリプト・ノートブック ／ 中間報告 ／ 最終報告
→ 業務判断に必要な初期示唆と運用化に向けた明確な次工程を提示している。
提案書
契約書
M01/M02
中間報告
最終報告
会議・成果トレース
1 / 15
```

### Rank 5
- score: 113.386672
- record_id: `pptx_slide_d70d3d356174ac76`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx`

```text
Slide 6
4. 分析結果 ― モデル比較
モデル比較証跡― 主要モデルの性能ランキング
| col_1 | col_2 | col_3 | col_4 |
| --- | --- | --- | --- |
| 順位 | モデル | F1 (macro) | Accuracy |
| 1 | extra_trees | 0.6027 | 0.7780 |
| 2 | extra_trees | 0.5953 | 0.7751 |
| 3 | gradient_boosting | 0.5899 | 0.8011 |
| 4 | random_forest | 0.5893 | 0.7980 |
| 5 | random_forest | 0.5855 | 0.7951 |
| 6 | random_forest | 0.5834 | 0.7957 |
解釈上の注意点
• interest_rate / grade はモデル性能に寄与している可能性が高いが、「審査時点で利用可能な情報か」によって本番時の再現性が大きく変わる（リーケージ懸念）
• 変数寄与の重要度ランキングはモデル依存であり、業務解釈には注意が必要である
確認が必要な事項
• loan_status の業務上の最終定義（0/1 の意味付け）および運用上の解釈（承認可否基準、遅延定義等）
• 時系列検証が不可（date列なし）のため、ドリフト・ビンテージ検証には別途データ取得が必要
Chart: {"chart_type": "COLUMN_CLUSTERED (51)", "title": "F1 (macro) vs Accuracy ― モデル比較", "series_count": 2, "category_axis_title": "", "value_axis_title": ""}
※モデルの詳細はleaderboard.csvに記載
```

### Rank 6
- score: 113.386672
- record_id: `pptx_slide_9555281868ed1b53`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx`

```text
Slide 6
4. 分析結果 ― モデル比較
モデル比較証跡― 主要モデルの性能ランキング
| col_1 | col_2 | col_3 | col_4 |
| --- | --- | --- | --- |
| 順位 | モデル | F1 (macro) | Accuracy |
| 1 | extra_trees | 0.6027 | 0.7780 |
| 2 | extra_trees | 0.5953 | 0.7751 |
| 3 | gradient_boosting | 0.5899 | 0.8011 |
| 4 | random_forest | 0.5893 | 0.7980 |
| 5 | random_forest | 0.5855 | 0.7951 |
| 6 | random_forest | 0.5834 | 0.7957 |
解釈上の注意点
• interest_rate / grade はモデル性能に寄与している可能性が高いが、「審査時点で利用可能な情報か」によって本番時の再現性が大きく変わる（リーケージ懸念）
• 変数寄与の重要度ランキングはモデル依存であり、業務解釈には注意が必要である
確認が必要な事項
• loan_status の業務上の最終定義（0/1 の意味付け）および運用上の解釈（承認可否基準、遅延定義等）
• 時系列検証が不可（date列なし）のため、ドリフト・ビンテージ検証には別途データ取得が必要
Chart: {"chart_type": "COLUMN_CLUSTERED (51)", "title": "F1 (macro) vs Accuracy ― モデル比較", "series_count": 2, "category_axis_title": "", "value_axis_title": ""}
※モデルの詳細はleaderboard.csvに記載
```

### Rank 7
- score: 113.107891
- record_id: `pptx_slide_45bbe5691fcb5f45`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`

```text
Slide 1
最終分析報告書
株式会社東都人材プラットフォーム
収入クラス予測モデル 企画・分析設計・初期検証

受託者：株式会社データアステル
契約期間：2025年8月18日 ～ 2025年9月29日
CONFIDENTIAL
```

### Rank 8
- score: 107.953373
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
