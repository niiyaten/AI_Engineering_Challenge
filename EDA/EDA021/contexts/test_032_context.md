# test_032

## Question
青嶺不動産アセットマネジメントの分析出力 metrics.json の feature_selection.selected_columns に含まれている列のうち、分析コードで生成された数値交互作用特徴量の列名をすべて答えてください。

## Route
code_reading

## Generated Answer
一方で、設定ファイル上には use_numeric_interactions: true の記述があるが、**中間報告で可視化された試行の特徴量数は6であり、相互作用特徴量の採否・反映範囲は**** Report facts JSON ****だけでは確定できない**。、smoker、bmi、ageは当初から重要候補として位置づけられていた変数群であり、最終モデルでも関連する特徴空間に含まれている、出力物として metrics / run summary / leaderboard 系の成果物が生成されている、そのため、**追加特徴量が最終的に採用されているかは未確定事項**として扱う。、相互作用特徴量（3列）

## Retrieved Records

### Rank 1
- score: 121.524517
- record_id: `pptx_slide_7041e3f7932593d4`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`

```text
Slide 5
03 実施体制
株式会社データアステル（実施者）
エグゼクティブスポンサー
中村 誠
プロジェクトマネージャー
佐藤 健一
リードDS
渡辺 遥
データエンジニア
岡田 佑樹
BA
藤田 彩
QA
小林 直樹
クライアント
青嶺不動産AM
前田 美咲 部長
手法要点
再現性優先の標準化パイプラインを採用
高カーディナリティ項目（NEIGHBORHOOD, BUILDING CLASS系）を除外し、交互作用（BBL組合せ等）を特徴量に追加
分割戦略はtime_ordered（date_columnに基づく）を試行。date_columnの実態確認は中間段階で議論
```

### Rank 2
- score: 111.208962
- record_id: `notebook_cell_b2feb4e99fa89a12`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 9: markdown
## 3. 数値特徴量の分布
```

### Rank 3
- score: 109.32971
- record_id: `generic_chunk_2041a21fb367bac5`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/05.会議/報告資料/報告資料_2025-07-22.docx`

```text
医療分野として**臨床断定回避・仮定の追跡可能性確保**を徹底

<!-- block_index=124 type=paragraph style=Heading 3 -->
### 4.3 実装状況

<!-- block_index=125 type=paragraph style=First Paragraph -->
分析コード要約および実行結果から、中間時点で以下が確認できる。

<!-- block_index=126 type=paragraph style=Compact -->
学習・評価パイプラインは実行済み

<!-- block_index=127 type=paragraph style=Compact -->
タスク種別は **classification**

<!-- block_index=128 type=paragraph style=Compact -->
学習/評価分割は **holdout ****split（test_size=0.2）**

<!-- block_index=129 type=paragraph style=Compact -->
特徴量選択により **6列採用**** / ****1列除外**

<!-- block_index=130 type=paragraph style=Compact -->
中間可視試行は **5件** 実行・参照可能

<!-- block_index=131 type=paragraph style=Compact -->
出力物として metrics / run summary / leaderboard 系の成果物が生成されている

<!-- block_index=132 type=paragraph style=First Paragraph -->
一方で、設定ファイル上には use_numeric_interactions: true の記述があるが、**中間報告で可視化された試行の特徴量数は6であり、相互作用特徴量の採否・反映範囲は**** Report facts JSON ****だけでは確定できない**。
そのため、**追加特徴量が最終的に採用されているかは未確定事項**として扱う。

<!-- block_index=133 type=paragraph style=Heading 3 -->
### 4.4 実装面の未確定事項

<!-- block_index=134 type=paragraph style=Compact -->
クラス別評価表の確定版

<!-- block_index=135 type=paragraph style=Compact -->
混同行列の提示版

<!-- block_index=136 type=paragraph style=Compact -->
重要変数順位の最終整理

<!-- block_index=137 type=paragraph style=Compact -->
中間指摘反映後の追加分析結果

<!-- block_index=138 type=paragraph style=Compact -->
変更管理判定（2025-07-24）を踏まえたスコープ影響有無

<!-- block_index=139 type=paragraph style=Heading 2 -->
## 5. リスクと対応策

<!-- block_index=140 type=paragraph style=Heading 3 -->
### 5.1 主要リスク

<!-- block_index=141 type=paragraph style=Heading 4 -->
###
```

### Rank 4
- score: 105.960945
- record_id: `notebook_cell_dcfeed61aeb4aa7c`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb`

```text
Notebook: 01_eda.ipynb
Cell 11: markdown
## 4. カテゴリ特徴量の分布
```

### Rank 5
- score: 103.669365
- record_id: `pptx_slide_27ac075e76801dfa`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`

```text
Slide 15
09 成果物サマリ
納品済の主要成果物（契約4.1に準拠）
1. プロジェクト概要書
本書を正本
納品済
2. 分析計画メモ / 実施方針書
artifacts/*
納品済
3. 中間報告書
MS4: 2025-08-26
納品済
4. 最終報告書
本書
納品済
5. 会議議事メモ
M01, M02
納品済
6. スケジュール管理表
artifacts/schedule/*
納品済
7. 分析出力
run_summary, metrics, leaderboard
納品済
```

### Rank 6
- score: 101.167533
- record_id: `metadata_4ac29b082c96a951`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`

```text
ファイル名: 株式会社青嶺不動産アセットマネジメント_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx
ファイル種別: pptx
```

### Rank 7
- score: 99.362393
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
- score: 97.915831
- record_id: `notebook_cell_165ace2c436613e1`
- record_type: `notebook_cell`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb`

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
