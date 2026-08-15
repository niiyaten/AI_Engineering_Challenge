# test_060

## Question
白峰信用リスク評価の最終報告資料内で未完事項として挙げられているIDをすべて抽出してください。

## Route
document_whole_context

## Generated Answer
監査証跡: 目的変数定義、前処理スクリプト、評価条件、モデルパラメータ、成果物版数は必ず成果物に記載のうえ保管してください。現在 run_summary/metrics は出力済みですが、会議決定事項（M01/M02）の議事録反映が必要です。、変更管理: 2025-05-01 を変更管理チェックポイントに設定済み。追加要望はこの時点で仕分け・見積りする運用としてください。固定価格のため、契約範囲外は別途見積りが必要です。、会議議事録: artifacts/meeting_minutes/会議録_2025-09-02.md（M01）および本中間レビュー議事録（M02）をプロジェクトの唯一基準として管理してください。、interest_rate / grade の「審査時点での利用可否」（A02）を確定してください。未回答の場合は並列評価で対応しますが、追加工数・説明負荷が発生します。、公平性評価: 性別・年齢などセンシティブ変数がデータに含まれていないため包括的公平性評価は制限あり。範囲と限界を最終報告に明示する必要があります。

## Retrieved Records

### Rank 1
- score: 111.360871
- record_id: `pptx_slide_236c2eb33f15e031`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx`

```text
Slide 3
01 エグゼクティブサマリ
本報告書は「企業財務指標を用いた3年後倒産予測分析プロジェクト」のクローズ向け最終報告書（Single Source of Truth）である。
主要成果
対象データ: 7,352件・66列
ROC-AUC = 0.859
Precision@top10% = 0.257
Accuracy = 0.957
重要観察事項
Attr37の欠損率が約45.25%
→ 投入可否が分析上の重要論点
不均衡（倒産率 ≈ 4.95%）への
対応が必要
要アクション（未完事項）
AI-05: 着手金支払の事後確認
AI-09: Attr37の最終採否比較
AI-08: 前処理仕様の確定
※ 本書は「確認済事項（Facts）」と「仮定（Assumptions）」を明確に分離して記載している。
```

### Rank 2
- score: 93.399993
- record_id: `generic_chunk_13d7ca7674d1b70a`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

```text
支払スケジュール: 着手金（50%）期日 2025-04-16、検収金（50%）期日 2025-06-03（各期日は契約条件に基づく）。

<!-- block_index=100 type=paragraph style=Compact -->
検討リソース（PM 向け）

<!-- block_index=101 type=paragraph style=Compact -->
クリティカルパス: データ理解 → 探索分析 → 中間レビュー → モデリング → 評価 → 報告書作成 → 検収（スケジュール上の遅延は 2025-05-27 の最終報告会へ影響）。

<!-- block_index=102 type=paragraph style=Compact -->
変更管理: 2025-05-01 を変更管理チェックポイントに設定済み。追加要望はこの時点で仕分け・見積りする運用としてください。固定価格のため、契約範囲外は別途見積りが必要です。

<!-- block_index=103 type=paragraph style=Compact -->
要注意（ガバナンス）

<!-- block_index=104 type=paragraph style=Compact -->
監査証跡: 目的変数定義、前処理スクリプト、評価条件、モデルパラメータ、成果物版数は必ず成果物に記載のうえ保管してください。現在 run_summary/metrics は出力済みですが、会議決定事項（M01/M02）の議事録反映が必要です。

<!-- block_index=105 type=paragraph style=Compact -->
公平性評価: 性別・年齢などセンシティブ変数がデータに含まれていないため包括的公平性評価は制限あり。範囲と限界を最終報告に明示する必要があります。

<!-- block_index=106 type=paragraph style=First Paragraph -->
以上。必要であれば、M02 の議事録反映後に改定版（議事録に基づく確定事項を反映した中間報告書）を速やかに発行します。
```

### Rank 3
- score: 90.609937
- record_id: `generic_chunk_7cde7193942a486e`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
style=Compact -->
実行アーティファクト（再現元）: artifacts/analysis_outputs/run_summary.json, artifacts/analysis_outputs/metrics.json, artifacts/analysis_outputs/experiments/leaderboard.json（Report facts.trace.source_files に記載）

<!-- block_index=94 type=paragraph style=Compact -->
会議議事録: artifacts/meeting_minutes/会議録_2025-09-02.md（M01）および本中間レビュー議事録（M02）をプロジェクトの唯一基準として管理してください。

<!-- block_index=95 type=paragraph style=Compact -->
要注意（PM 向け）

<!-- block_index=96 type=paragraph style=Compact -->
open actions = 7（prior_state.open_action_count = 7）。PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソース配分を確定してください。

<!-- block_index=97 type=paragraph style=Compact -->
2025-09-19 の変更管理チェックポイントは契約上の追加対応要否を判定する重要日です。追加要求が出た場合は change_request_policy（time_and_materials）に従って見積り・承認の流れを確保してください。

<!-- block_index=98 type=paragraph style=First Paragraph -->
以上

<!-- block_index=99 type=paragraph style=Body Text -->
（作成: データアステル / 分析チーム — 報告は Report facts JSON（checkpoint=M02, stage=interim）に基づく内容です）
```

### Rank 4
- score: 83.006907
- record_id: `metadata_dc9c05760e2f4dfa`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx`

```text
ファイル名: 白峰信用リスク評価株式会社_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx
ファイル種別: pptx
```

### Rank 5
- score: 81.855352
- record_id: `metadata_1b3852b3a77d0cc2`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/報告資料/報告資料_2025-06-17.pdf`

```text
ファイル名: 報告資料_2025-06-17.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/報告資料/報告資料_2025-06-17.pdf
ファイル種別: pdf
```

### Rank 6
- score: 81.855352
- record_id: `metadata_f452935adaef175d`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/報告資料/報告資料_2025-05-27.pdf`

```text
ファイル名: 報告資料_2025-05-27.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/報告資料/報告資料_2025-05-27.pdf
ファイル種別: pdf
```

### Rank 7
- score: 81.855352
- record_id: `metadata_99a1615068f27d65`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/報告資料/報告資料_2025-05-13.pdf`

```text
ファイル名: 報告資料_2025-05-13.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/報告資料/報告資料_2025-05-13.pdf
ファイル種別: pdf
```

### Rank 8
- score: 81.337905
- record_id: `generic_chunk_a2d0a8164095eda2`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

```text
er: 山本 彩乃 — 目安: MS4 後着手（2025-04-30〜）。
- モデル評価の深化（リフト、PR-AUC、混同行列、上位群の詳細解析） — Owner: 山本 彩乃 — 目安: MS5（2025-05-13）までに確定。
- 中間報告書の確定・配布（中間レビューの議事録反映含む） — Owner: 藤田 彩 — 目安: 2025-05-14〜2025-05-16（中間報告確定）。
- 変更要求の仕分け（MS4: 2025-05-01）— Owner: 伊藤 翔太。

<!-- block_index=87 type=paragraph style=Body Text -->
（注）上記の期日はプロジェクトスケジュールに基づく。prior_state に登録された Open アクションは 5 件です（open_action_count=5）。

<!-- block_index=88 type=paragraph style=Normal -->

<!-- block_index=89 type=paragraph style=Heading 2 -->
## 7. 経営/PM向け補足

<!-- block_index=90 type=paragraph style=Compact -->
主要決定依頼（早急）

<!-- block_index=91 type=paragraph style=Compact -->
loan_status の公式な文書定義（A01）を最優先で確定・配布してください。解析方向の基準になります。

<!-- block_index=92 type=paragraph style=Compact -->
interest_rate / grade の「審査時点での利用可否」（A02）を確定してください。未回答の場合は並列評価で対応しますが、追加工数・説明負荷が発生します。

<!-- block_index=93 type=paragraph style=Compact -->
中間レビュー（M02）の議事録・合意事項（採用する評価指標、リスク区分の方針・優先順位）がまだシステムに登録されていない場合、速やかに反映をお願いします（トレーサビリティ確保のため）。

<!-- block_index=94 type=paragraph style=Compact -->
スケジュールと費用（確定値）

<!-- block_index=95 type=paragraph style=Compact -->
契約開始日: 2025-04-09（既スタート）

<!-- block_index=96 type=paragraph style=Compact -->
契約期間: 7 週間

<!-- block_index=97 type=paragraph style=Compact -->
契約金額（税抜）: 4,200,000 円（project_facts.commercial_terms）

<!-- block_index=98 type=paragraph style=Compact -->
税率: 10%（税額 420,000 円） → 税込合計 4,620,000 円

<!-- block_index=99 type=paragraph style=Compact -->
支払スケジュール: 着手金（50%）期日 2025-04-16、検収金（50%）期日 2025-06-03（各期日は契約条件に基づく）。

<!-- block_index=100 type=paragraph style=Compact -->
検討リソース（PM 向け）

<!-- block_index=101
```
