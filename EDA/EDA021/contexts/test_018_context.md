# test_018

## Question
白峰信用リスク評価の会議ID：M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。

## Route
document_whole_context

## Generated Answer
欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。

## Retrieved Records

### Rank 1
- score: 83.733611
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
- score: 75.149869
- record_id: `metadata_3e21996edf9466fa`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-07-15.pdf`

```text
ファイル名: 会議録_2025-07-15.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-07-15.pdf
ファイル種別: pdf
```

### Rank 3
- score: 75.149869
- record_id: `metadata_e7236e746a1b8726`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-06-17.pdf`

```text
ファイル名: 会議録_2025-06-17.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-06-17.pdf
ファイル種別: pdf
```

### Rank 4
- score: 75.149869
- record_id: `metadata_29b217fb2d788b4f`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-05-27.pdf`

```text
ファイル名: 会議録_2025-05-27.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-05-27.pdf
ファイル種別: pdf
```

### Rank 5
- score: 75.149869
- record_id: `metadata_f5effdd1f0ab6798`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-05-13.pdf`

```text
ファイル名: 会議録_2025-05-13.pdf
元パス: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/05.会議/会議録/会議録_2025-05-13.pdf
ファイル種別: pdf
```

### Rank 6
- score: 75.088221
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
- score: 73.044358
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

### Rank 8
- score: 69.008695
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
