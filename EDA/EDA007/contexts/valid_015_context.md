# valid_015 LLM Context

## Question
中間報告会または中間レビューが2025年7月1日以前に実施された案件を、主略称ですべて挙げてください。

## Validation Answer
MINAMINO、SHR、AYM

## Diagnosis
- required_capability: document_qa
- context_quality_for_llm: needs_better_retrieval
- answer_hit_top5: False
- recommended_next_step: 抽出対象と検索重みを見直す

## Retrieved Evidence

### Evidence 1
- score: 124.5201
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

### Evidence 2
- score: 124.0502
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 恒一会 かえで総合病院
- major_folder: 05.会議
- relative_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx

```text
れます。経営判断で必要な場合は「外部検証用データの準備」や「追加のドメイン確認（医師レビュー）」を早期に合意ください。
## paragraph_084 - style: Compact 追加要求発生時の精算方針は time_and_materials（追加は別途見積り）です。スコープ外要望が生じた場合は 2025-09-19 の変更管理チェックポイントで影響を判断する運用としています（日付はスケジュール資料に基づく想定／assumption）。
## paragraph_085 - style: Compact プロジェクトは「判定支援材料の整備」を目的としており、成果物では診断の断定表現を避ける必要があります。成果物の公開・活用範囲は必ず合意された運用ルールに従ってください。
## paragraph_08...
```

### Evidence 3
- score: 121.1079
- source_eda: EDA004
- extension: .docx
- project_name: 青葉与信マネジメント株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx

```text
025-05-14〜2025-05-16（中間報告確定）。 - 変更要求の仕分け（MS4: 2025-05-01）— Owner: 伊藤 翔太。
## paragraph_087 - style: Body Text （注）上記の期日はプロジェクトスケジュールに基づく。prior_state に登録された Open アクションは 5 件です（open_action_count=5）。
## paragraph_089 - style: Heading 2 7. 経営/PM向け補足
## paragraph_090 - style: Compact 主要決定依頼（早急）
## paragraph_091 - style: Compact loan_status の公式な文書定義（A01）を最優先で確定・配布してく...
```

### Evidence 4
- score: 121.1027
- source_eda: EDA004
- extension: .docx
- project_name: 青葉与信マネジメント株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx

```text
（50%）期日 2025-04-16、検収金（50%）期日 2025-06-03（各期日は契約条件に基づく）。
## paragraph_100 - style: Compact 検討リソース（PM 向け）
## paragraph_101 - style: Compact クリティカルパス: データ理解 → 探索分析 → 中間レビュー → モデリング → 評価 → 報告書作成 → 検収（スケジュール上の遅延は 2025-05-27 の最終報告会へ影響）。
## paragraph_102 - style: Compact 変更管理: 2025-05-01 を変更管理チェックポイントに設定済み。追加要望はこの時点で仕分け・見積りする運用としてください。固定価格のため、契約範囲外は別途見積りが必要です。
## p...
```

### Evidence 5
- score: 108.6509
- source_eda: EDA004
- extension: .docx
- project_name: 青葉与信マネジメント株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx

```text
4 - style: Compact 契約金額（税抜）: 4,200,000 円
## paragraph_085 - style: Compact 税率: 10%（税額 420,000 円）
## paragraph_086 - style: Compact 契約金額（税込）: 4,620,000 円 #
## run_styles - highlight=YELLOW (7)/font_color=FF0000: 4,620,000
## paragraph_087 - style: Compact 支払スケジュール: 2 回分割（着手金 50%／検収金 50%） — 各金額は payment_schedule に記載の通り
## paragraph_088 - style: Compact 支払管理は PM...
```
