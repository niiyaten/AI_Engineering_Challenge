# valid_000 LLM Context

## Question
青潮モビリティサービスの最終報告における、モビリティ需要の要因分析のページで、マーカーされている単語をすべて抜き出してください。

## Validation Answer
hr、weekday、weathersit、temp

## Diagnosis
- required_capability: format_extraction
- context_quality_for_llm: needs_format_extraction
- answer_hit_top5: False
- recommended_next_step: Word/PPTの書式メタ情報をRAG向けに正規化する

## Retrieved Evidence

### Evidence 1
- score: 165.4777
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社青潮モビリティサービス
- major_folder: 05.会議
- relative_path: プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx

```text
metrics.json、leaderboard 等）。Trace 情報: Report facts JSON.trace.source_files を参照。
## paragraph_050 - style: Heading 2 4. データ品質と実装状況
## paragraph_051 - style: Compact データ読み込み・前処理状況
## paragraph_052 - style: Compact 入力ファイル（data/train.tsv）の読み込みと前処理パイプラインは実行済みで、実験群（T01〜T05）は上述の設定（date features, cyclical features, transform_target 等）で構築・評価済みです（analysis.run_summary ...
```

### Evidence 2
- score: 148.5227
- source_eda: EDA004
- extension: .pptx
- project_name: 株式会社青潮モビリティサービス
- major_folder: 00.提案
- relative_path: プロジェクト/株式会社青潮モビリティサービス/00.提案/提案書.pptx

```text
## slide_001 データ分析プロジェクト提案書 モビリティ需要予測分析 プロジェクト 株式会社青潮モビリティサービス 御中 株式会社データアステル
## slide_002 1. 背景 課題認識 ▲ 需要ピーク時の サービス可用性確保 ■ 供給不足・過剰配置の 抑制 ● 配車・再配置計画の 高度化 対象データ：train.tsv データ規模 8,645行 × 15列 1時間単位の時系列データ 含まれる情報 日時・季節・曜日・祝日 天候・気温・湿度・風速 目的変数 cnt（利用者数） 時間単位の需要予測に使用 ※ 拠点情報、車両情報、位置情報、移動履歴、イベント情報等は本データに含まれないため、本フェーズでは全体需要の時間別予測と変動要因の把握を中心に進める。デー...
```

### Evidence 3
- score: 147.637
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社青潮モビリティサービス
- major_folder: 05.会議
- relative_path: プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx

```text
: 上記タスクは WBS のタスクID（T02〜T11等）に対応しており、成果物は artifacts に格納してトレーサビリティを確保します。
## paragraph_076 - style: Heading 2 7. 経営/PM向け補足
## paragraph_077 - style: Compact 現フェーズは「キックオフ／計画合意」段階であり、モデル学習や評価結果は未実施です。したがって、精度に関する数値的な結論や最終的な業務影響の確定は今段階では出せません（analysis.checkpoint_stage = “kickoff” に準拠）。
## paragraph_078 - style: Compact 商業条件（ご参考、Report facts JSON 所載）
## paragraph...
```

### Evidence 4
- score: 135.3319
- source_eda: EDA004
- extension: .pptx
- project_name: 株式会社青潮モビリティサービス
- major_folder: 00.提案
- relative_path: プロジェクト/株式会社青潮モビリティサービス/00.提案/提案書.pptx

```text
: 追加要望の発生 | 分析過程で追加論点や追加作業が発生する可能性 | 追加対応は別途見積または追加発注として管理し、既存スコープへの影響を明確化 14
## slide_015 10. 前提条件と除外事項 10.1 前提条件 ✓ 学習データの正本は train.tsv ✓ 目的変数は cnt ✓ 分析粒度は日付×時間の1時間単位 ✓ 実データとの不整合は実データを優先 ✓ yr, workingday の定義整合性は初期確認事項 ✓ 規格化済み気象変数はそのまま利用 ✓ 外生要因前提は成果物で明示 ✓ 運用事実と需要仮説は分離して記載 10.2 除外事項 ✗ 本番システム実装、API化、バッチ化、MLOps構築 ✗ 空間分析、位置情報分析、移動履歴分析 ✗ 配車最適化、再配置最適化の実装 ✗ 外部データとの...
```

### Evidence 5
- score: 135.192
- source_eda: EDA004
- extension: .pdf
- project_name: 株式会社青潮モビリティサービス
- major_folder: 06.報告書
- relative_path: プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf

```text
## page_001 株式会社 データアステル
## page_002 [テキスト抽出なし]
## page_003 [テキスト抽出なし]
## page_004 [テキスト抽出なし]
## page_005 [テキスト抽出なし]
## page_006 [テキスト抽出なし]
## page_007 [テキスト抽出なし]
## page_008 データアステル（検証）
## page_009 [テキスト抽出なし]
## page_010 [テキスト抽出なし]
## page_011 [テキスト抽出なし]
## page_012 株式会社データアステル
## page_013 [テキスト抽出なし]
```
