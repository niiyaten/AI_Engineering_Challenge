# valid_023 LLM Context

## Question
AOSHIOのM02資料（docx）において、黄色でハイライトされている部分をすべて抜き出してください。

## Validation Answer
見込金額（税込）: 4,675,000 JPY

## Diagnosis
- required_capability: format_extraction
- context_quality_for_llm: needs_format_extraction
- answer_hit_top5: False
- recommended_next_step: Word/PPTの書式メタ情報をRAG向けに正規化する

## Retrieved Evidence

### Evidence 1
- score: 119.4533
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 恒一会 かえで総合病院
- major_folder: 05.会議
- relative_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx

```text
（閾値チューニング済み線形モデル）が最も高い f1_macro を示した（f1_macro = 0.7329671168078127）。このことは、現データにおいて「モデル構造を大きく変えずに、決定閾値やクラス判断の調整で性能改善が得られる」ことを示唆します。
## paragraph_038 - style: Compact AUC-ROC（0.8250532501536466）や top10% precision（0.9428571428571428）が比較的良好である点は、スコア上位の予測が高い精度で陽性を含む可能性を示しており、閾値運用による業務ルール設計の余地があります。
## paragraph_039 - style: Compact 特徴量・前処理の状況
## paragraph_040 - s...
```

### Evidence 2
- score: 117.1386
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社東都人材プラットフォーム
- major_folder: 00.提案
- relative_path: プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx

```text
を防ぎ、中長期的な企業価値向上へのコミットメントを引き出している。 #
## run_styles - font_color=1F1F1F: この基本給（約11万〜12万ドル）と総報酬（約15万〜15.8万ドル）の間に存在する約3万ドルから4万ドルのギャップは、企業のインセンティブ設計の巧妙さを表している。企業は、データサイエンティストの個人的なパフォーマンスを企業の業績や株価と直接連動させることで、短期的な離職を防ぎ、中長期的な企業価値向上へのコミットメントを引き出している。
## paragraph_017 - style: Heading 3 2.3. 産業別（Industry）の利益構造に基づく報酬格差 #
## run_styles - bold/font_color=1F1F1F: 2.3. 産業別（I...
```

### Evidence 3
- score: 115.6362
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 恒一会 かえで総合病院
- major_folder: 05.会議
- relative_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx

```text
案を提示します。
## paragraph_092 - style: Compact トレーサビリティ（参照先）
## paragraph_093 - style: Compact 実行アーティファクト（再現元）: artifacts/analysis_outputs/run_summary.json, artifacts/analysis_outputs/metrics.json, artifacts/analysis_outputs/experiments/leaderboard.json（Report facts.trace.source_files に記載）
## paragraph_094 - style: Compact 会議議事録: artifacts/meeting_minutes/会議録_20...
```

### Evidence 4
- score: 111.0655
- source_eda: EDA004
- extension: .docx
- project_name: 青葉与信マネジメント株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx

```text
ないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。
## paragraph_041 - style: Heading 2 4. データ品質と実装状況
## paragraph_042 - style: Compact データ品質
## paragraph_043 - style: Compact 欠損: 全カラムで 0%（eda_summary.missing_ratio_top10 の全項目が 0.0）
## paragraph_044 - style: Compact カラム数: 10（id を含む）
## p...
```

### Evidence 5
- score: 110.9612
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社東都人材プラットフォーム
- major_folder: 00.提案
- relative_path: プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx

```text
均時給は55.40ドルであり、これは中央値をわずかに上回っていることから、一部の高額所得者が平均値を押し上げる右傾分布（Right-skewed distribution）を形成していることが推察される。
## paragraph_011 - style: Normal 労働市場の動向をリアルタイムで反映する民間プラットフォームのデータに基づくと、2025年に向けた基本給の予測はさらに上昇傾向を示している。複数の情報源から抽出した2025年の基本給の分布は以下の通りである。 #
## run_styles - font_color=1F1F1F: 労働市場の動向をリアルタイムで反映する民間プラットフォームのデータに基づくと、2025年に向けた基本給の予測はさらに上昇傾向を示している。複数の情報源から抽出した202...
```
