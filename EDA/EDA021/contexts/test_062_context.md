# test_062

## Question
青葉与信マネジメントの最終報告資料における、モデル比較で上位2件のスコア差を生んでいる設定差分は何ですか。

## Route
diff_check

## Generated Answer
上位10%スコア群における不良含有率が高く、スコアに基づくバケット化でリスク区分の初期運用設計（重点審査・与信条件変更の検討等）が可能である。

## Retrieved Records

### Rank 1
- score: 103.894312
- record_id: `pptx_slide_5723d44c147c4c2a`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx`

```text
Slide 5
4. 分析結果 ― データ構成とモデル評価
(A) データ構成（確定事実）
| col_1 | col_2 |
| --- | --- |
| 項目 | 値 |
| 行数 | 17,500 |
| カラム数 | 10 |
| 欠損 | 全カラム 0 |
| loan_status 平均（基準不良率） | 0.2148（≒21.48%） |
(B) モデル評価（確定事実）
ベースライン: extra_trees (n_estimators=500)
train=14,000 / test=3,500
| col_1 | col_2 |
| --- | --- |
| 指標 | 値 |
| ROC-AUC | 0.7127 |
| Accuracy | 0.7780 |
| F1 (macro) | 0.6027 |
| Brier Score | 0.1581 |
| precision@top10% | 0.4886 |
実務インパクトの見積り
上位10%スコア群における不良含有率が高く、スコアに基づくバケット化でリスク区分の初期運用設計（重点審査・与信条件変更の検討等）が可能である。
```

### Rank 2
- score: 103.894312
- record_id: `pptx_slide_610398bd1f054401`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx`

```text
Slide 5
4. 分析結果 ― データ構成とモデル評価
(A) データ構成（確定事実）
| col_1 | col_2 |
| --- | --- |
| 項目 | 値 |
| 行数 | 17,500 |
| カラム数 | 10 |
| 欠損 | 全カラム 0 |
| loan_status 平均（基準不良率） | 0.2148（≒21.48%） |
(B) モデル評価（確定事実）
ベースライン: extra_trees (n_estimators=500)
train=14,000 / test=3,500
| col_1 | col_2 |
| --- | --- |
| 指標 | 値 |
| ROC-AUC | 0.7127 |
| Accuracy | 0.7780 |
| F1 (macro) | 0.6027 |
| Brier Score | 0.1581 |
| precision@top10% | 0.4886 |
実務インパクトの見積り
上位10%スコア群における不良含有率が高く、スコアに基づくバケット化でリスク区分の初期運用設計（重点審査・与信条件変更の検討等）が可能である。
```

### Rank 3
- score: 90.628591
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

### Rank 4
- score: 90.628591
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

### Rank 5
- score: 78.760393
- record_id: `metadata_a3f7a535254af5d3`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx`

```text
ファイル名: 青葉与信マネジメント株式会社_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx
ファイル種別: pptx
```

### Rank 6
- score: 78.760393
- record_id: `metadata_15c641cf6b37c2f1`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx`

```text
ファイル名: 青葉与信マネジメント株式会社_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx
ファイル種別: pptx
```

### Rank 7
- score: 78.405198
- record_id: `metadata_db92fcf64432f4c5`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

```text
ファイル名: 報告資料_2025-04-29.docx
元パス: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx
ファイル種別:
```

### Rank 8
- score: 78.405198
- record_id: `metadata_3efbfb9a6b10dc93`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
ファイル名: 報告資料_2025-04-09.docx
元パス: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx
ファイル種別:
```
