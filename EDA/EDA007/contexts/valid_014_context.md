# valid_014 LLM Context

## Question
青葉バイオメディカル機器案件において、鈴木 美咲さんはどの役割としてアサインされていますか。

## Validation Answer
アサインされていない

## Diagnosis
- required_capability: document_qa
- context_quality_for_llm: needs_better_retrieval
- answer_hit_top5: False
- recommended_next_step: 抽出対象と検索重みを見直す

## Retrieved Evidence

### Evidence 1
- score: 146.529
- source_eda: EDA004
- extension: .pptx
- project_name: 株式会社青葉バイオメディカル機器
- major_folder: 06.報告書
- relative_path: プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx

```text
クまたは 予測モデル（手法未固定） 中間報告 線形ベースライン （Trial 1）を 可視試行の代表とした 最終分析 Extra Trees による 性能評価結果が 採用候補として確認 3. モデル・特徴量方針
## slide_010 table_
row_001: KPI分類 | 判定基準 | 結果 | 評価 table_
row_002: データ理解 | 全33列の役割・型・注意点整理 | 概ね完了 | 達成 table_
row_003: 要因把握 | 上位5〜10変数の方向性提示 | 主要論点群を整理 | 達成 table_
row_004: モデル評価 | 学習・検証手順と性能指標提示 | Accuracy/F1/ROC-AUC等を提示 | 達成 table_
row_005: 説明可能性 | 集計ベースで人...
```

### Evidence 2
- score: 131.4771
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社青葉バイオメディカル機器
- major_folder: 05.会議
- relative_path: プロジェクト/株式会社青葉バイオメディカル機器/05.会議/報告資料/報告資料_2025-06-23.docx

```text
## paragraph_001 - style: Heading 1 分析進捗報告書
## paragraph_002 - style: Heading 2 1. 報告サマリー
## paragraph_003 - style: Compact 対象チェックポイントは M01（2025-06-23、キックオフ） です。 #
## run_styles - bold: M01（2025-06-23、キックオフ）
## paragraph_004 - style: Compact 本報告は、2025-06-23時点のプロジェクト立上げ状況を整理した中間分析報告です。 #
## run_styles - bold: 2025-06-23時点
## par...
```

### Evidence 3
- score: 130.2022
- source_eda: EDA004
- extension: .pptx
- project_name: 株式会社青葉バイオメディカル機器
- major_folder: 06.報告書
- relative_path: プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx

```text
品質確認・再現環境整備 table_
row_005: 06-30〜07-07 | T07 | EDA実施 table_
row_006: 07-07〜10 | T10 | 初期モデル作成・評価 table_
row_007: 07-11 | M02 / MS3 | EDAレビュー・中間報告 table_
row_008: 07-14 | T13/T14 / MS4 | 変更要求整理・変更管理チェックポイント table_
row_009: 07-14〜18 | T15/T16 | セグメント分析・公平性レビュー table_
row_010: 07-17〜22 | T17 | 最終報告ドラフト作成 table_
row_011: 07-25 | M03 / MS6 | 最終報告・検収会 table_
row_012: 07-...
```

### Evidence 4
- score: 129.6855
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社青葉バイオメディカル機器
- major_folder: 05.会議
- relative_path: プロジェクト/株式会社青葉バイオメディカル機器/05.会議/報告資料/報告資料_2025-06-23.docx

```text
aragraph 次回主要会議は M02（2025-07-11、EDAレビュー・中間報告） です。 それまでの実施事項を、スケジュールとWBSに紐づけて整理します。 #
## run_styles - bold: M02（2025-07-11、EDAレビュー・中間報告）
## paragraph_097 - style: Heading 3 6.1 直近実施事項
## paragraph_098 - style: Heading 3 6.2 次回報告に向けた期待成果
## paragraph_099 - style: First Paragraph M02までに期待される成果は以下です。
## paragraph_100 - style: Compact 全 33列 の定義・役割・利用可否整理 #
## run_s...
```

### Evidence 5
- score: 128.9745
- source_eda: EDA004
- extension: .docx
- project_name: 株式会社青葉バイオメディカル機器
- major_folder: 05.会議
- relative_path: プロジェクト/株式会社青葉バイオメディカル機器/05.会議/報告資料/報告資料_2025-06-23.docx

```text
画です。 契約開始日は 2025-06-23、主要マイルストンは以下の通りです。 #
## run_styles - bold: 5週間 - bold: 2025-06-23
## paragraph_023 - style: Body Text 現時点では、計画上の第1週初日にあたり、スケジュール上は順当な開始時点です。 ただし、MS1の完了判定条件である以下は、会議議事録未取得のため確認待ちです。 #
## run_styles - bold: 順当な開始時点 - bold: 確認待ち
## paragraph_024 - style: Compact 目的の合意
## paragraph_025 - style: Compact スコープの合意
## paragraph_026 - style: Compac...
```
