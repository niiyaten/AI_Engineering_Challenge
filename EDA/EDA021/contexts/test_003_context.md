# test_003

## Question
恒一会 かえで総合病院の契約書において、太字で記載されている箇所のうち、日付以外のものをすべて抽出してください。

## Route
format_extraction

## Generated Answer
欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。、例: 「train.csv の行数 = 3,500」「欠損数 = 0」はプロジェクト概要に記載されているが、Report facts JSON に explicit に含まれないため本レポートでは（assumption）として扱います。、（注）報告中の数値は Report facts JSON の metrics / project_facts に基づき記載しています。プロジェクト定義にのみ記載されているが Report facts JSON に未記載の数値は「assumption」として明示し、当報告ではそのように扱っています。、open actions = 7（prior_state.open_action_count = 7）。PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソース配分を確定してください。、2025-09-19 の変更管理チェックポイントは契約上の追加対応要否を判定する重要日です。追加要求が出た場合は change_request_policy（time_and_materials）に従って見積り・承認の流れを確保してください。

## Retrieved Records

### Rank 1
- score: 106.265601
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
- score: 105.526248
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

### Rank 3
- score: 81.255699
- record_id: `pptx_slide_5e1a46ce8e1c9eea`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`

```text
Slide 15
14. 成果物サマリ
| col_1 | col_2 | col_3 |
| --- | --- | --- |
| 成果物 | ステータス | 参照パス |
| プロジェクト概要書 | 納品済 | 本書 |
| 分析計画書 | 納品済 | 提出済 |
| データ理解レポート | 納品済 | 提出済 |
| 中間報告書（M02） | 納品済 | artifacts/reports/報告資料_2025-09-16.md |
| 最終報告書 | 納品済 | 本書 |
| 会議議事録（M01） | 納品済 | artifacts/meeting_minutes/会議録_2025-09-02.md |
| 会議議事録（M02） | 納品済 | artifacts/meeting_minutes/会議録_2025-09-16.md |
| 分析実行アーティファクト | 納品済 | artifacts/analysis_outputs/（run_summary.json、metrics.json、leaderboard.json） |
納品物は、契約に定める内容（第4条 成果物）に準拠している。すべての成果物は「disease の定義」「id の除外」「train.csv を単一ソース」といった基準に従って一貫記載している。
```

### Rank 4
- score: 81.255699
- record_id: `pptx_slide_c8d5b8671a99b286`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`

```text
Slide 15
14. 成果物サマリ
| col_1 | col_2 | col_3 |
| --- | --- | --- |
| 成果物 | ステータス | 参照パス |
| プロジェクト概要書 | 納品済 | 本書 |
| 分析計画書 | 納品済 | 提出済 |
| データ理解レポート | 納品済 | 提出済 |
| 中間報告書（M02） | 納品済 | artifacts/reports/報告資料_2025-09-16.md |
| 最終報告書 | 納品済 | 本書 |
| 会議議事録（M01） | 納品済 | artifacts/meeting_minutes/会議録_2025-09-02.md |
| 会議議事録（M02） | 納品済 | artifacts/meeting_minutes/会議録_2025-09-16.md |
| 分析実行アーティファクト | 納品済 | artifacts/analysis_outputs/（run_summary.json、metrics.json、leaderboard.json） |
納品物は、契約に定める内容（第4条 成果物）に準拠している。すべての成果物は「disease の定義」「id の除外」「train.csv を単一ソース」といった基準に従って一貫記載している。
```

### Rank 5
- score: 77.216175
- record_id: `generic_chunk_dc945ce455ac24aa`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`

```text
500,000 円、消費税額: 350,000 円、見込金額（税込）: 3,850,000 円（payment_schedule に明記）

<!-- block_index=81 type=paragraph style=Compact -->
支払条件: 最終一括精算（最終成果物検収完了後5営業日以内）※支払スケジュールは単一回の最終精算（Report facts JSON の commercial.payment_schedule を参照）。

<!-- block_index=82 type=paragraph style=Compact -->
当面の注視点（経営判断に資する事項）

<!-- block_index=83 type=paragraph style=Compact -->
現時点は評価／モデル作成前の「準備段階」です。期待される成果（モデル精度・業務効果）は EDA→試作→評価 の順で確定されます。経営判断で必要な場合は「外部検証用データの準備」や「追加のドメイン確認（医師レビュー）」を早期に合意ください。

<!-- block_index=84 type=paragraph style=Compact -->
追加要求発生時の精算方針は time_and_materials（追加は別途見積り）です。スコープ外要望が生じた場合は 2025-09-19 の変更管理チェックポイントで影響を判断する運用としています（日付はスケジュール資料に基づく想定／assumption）。

<!-- block_index=85 type=paragraph style=Compact -->
プロジェクトは「判定支援材料の整備」を目的としており、成果物では診断の断定表現を避ける必要があります。成果物の公開・活用範囲は必ず合意された運用ルールに従ってください。

<!-- block_index=86 type=paragraph style=Compact -->
現時点での重要エビデンス（トレーサビリティ）

<!-- block_index=87 type=paragraph style=Compact -->
キックオフ想定決定事項、ステージは Report facts JSON.checkpoint に記録済み。

<!-- block_index=88 type=paragraph style=Compact -->
prior_state に議事録やオープンアクションが未登録であるため、議事録（キックオフ合意）の登録を優先してください（責任者: PM 佐藤 健一）。

<!-- block_index=89 type=paragraph style=Normal -->

<!-- block_index=90 type=paragraph style=First Paragraph -->
以上。次回（中間レビュー／M02）に向けて、上記の「次回までの実施事項」を優先し、EDA と分析計画の確定を進めます。
```

### Rank 6
- score: 71.893078
- record_id: `generic_chunk_e9378ba44ef02f3f`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/05.会議/報告資料/報告資料_2025-10-01.docx`

```text
index=75 type=paragraph style=Compact -->
重要エスカレーション項目

<!-- block_index=76 type=paragraph style=Compact -->
M01 の議事録未作成と、期待される決定事項（業務目的・カラム定義・検収窓口）が未確定のまま進行すると、以降フェーズでの仕様変更・手戻りリスクが発生します。早急に議事録化・承認をお願いします。

<!-- block_index=77 type=paragraph style=Compact -->
着手金の支払フォローは期日が近いため、経理処理・承認フローの確認を要請します（担当: クライアント 高橋 課長）。

<!-- block_index=78 type=paragraph style=Compact -->
管理上の推奨事項（短期）

<!-- block_index=79 type=paragraph style=Compact -->
M01 の決定事項を「単一正本（project facts / このプロジェクト概要）」として版管理し、以降の全成果物はこの正本に整合させる運用を厳守してください（既にプロジェクト定義に明記）。

<!-- block_index=80 type=paragraph style=Compact -->
EDA および前処理方針（特に duration の扱い）について、中間報告（M02）での明確化を必須トピックとすることを推奨します。

<!-- block_index=81 type=paragraph style=Normal -->

<!-- block_index=82 type=paragraph style=First Paragraph -->
付記（トレース情報） - 現時点で参照可能な出力: artifacts/analysis_outputs/metrics.json、artifacts/analysis_outputs/run_summary.json（Report trace に登録済）
- 次回会議予定: 週次進捗 2025-10-06、MS2（EDA完了） 2025-10-14、M02 中間報告 2025-10-29

<!-- block_index=83 type=paragraph style=Body Text -->
（注）報告中の数値は Report facts JSON の metrics / project_facts に基づき記載しています。プロジェクト定義にのみ記載されているが Report facts JSON に未記載の数値は「assumption」として明示し、当報告ではそのように扱っています。
```

### Rank 7
- score: 71.764307
- record_id: `metadata_3e2958a8834ecf83`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/01.契約/契約書_pw解除版.docx`

```text
ファイル名: 契約書_pw解除版.docx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/01.契約/契約書_pw解除版.docx
ファイル種別:
```

### Rank 8
- score: 71.676163
- record_id: `pptx_slide_62df5e66794a6f19`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`

```text
Slide 15
07
成果物定義
成果物
主な内容
プロジェクト概要書
背景、目的、対象範囲、前提、制約、推進方針
分析計画書
分析手順、前処理方針、評価方法、実施計画
データ理解レポート
データ構造、品質確認、分布確認、論点整理
中間報告書
初期分析結果、モデル比較状況、追加論点
最終報告書
最終分析結果、評価、示唆、活用上の留意点、次段階提案
会議議事録
会議での合意事項、課題、アクション
スケジュール表
タスク、週次進行、マイルストーン
※すべての成果物において、diseaseの定義、idの除外、対象データ、前処理方針、評価指標、制約条件を統一して記載する。
```
