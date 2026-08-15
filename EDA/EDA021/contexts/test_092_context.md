# test_092

## Question
恒一会 かえで総合病院案件において、マイルストーンID、タスクID、アクションIDの3種類のIDは合計でいくつ発行されていますか。マークダウンファイル以外から算出してください。

## Route
table_calculation

## Generated Answer
欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。

## Retrieved Records

### Rank 1
- score: 143.39408
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

### Rank 2
- score: 107.740607
- record_id: `xlsx_sheet_adbb24884d97f659`
- record_type: `xlsx_sheet`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/02.計画/スケジュール.xlsx`

```text
Excelファイル: スケジュール.xlsx
シート: スケジュール
使用範囲: A1:L33
列: No., 区分, フェーズ, タスクID, タスク名, 詳細・成果物, 担当者, 開始日, 終了日, 依存タスク, ステータス, 備考
グラフ数: 0
サンプル:
| No. | 区分 | フェーズ | タスクID | タスク名 | 詳細・成果物 | 担当者 | 開始日 | 終了日 | 依存タスク | ステータス | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | マイルストーン | 1. 立上げ・計画確定 | MS1 | キックオフ完了 | 目的・スコープ・連絡系統・レビュー頻度・第1週～第2週の進め方を合意 | 佐藤 健一 | 2025-08-18T00:00:00 | 2025-08-18T00:00:00 | - | 完了 | 関連会議: M01 キックオフ |
| 2 | マイルストーン | 1. 立上げ・計画確定 | MS2 | 分析計画・環境準備完了 | 分析計画書初版、環境準備、データ読込確認、WBS確定 | 渡辺 遥 / 斎藤 悠斗 | 2025-08-22T00:00:00 | 2025-08-22T00:00:00 | - | 完了 | 週次内部レビュー |
| 3 | マイルストーン | 2. データ理解・EDA | MS3 | データ理解完了 | 欠損、分布、主要論点、EDA初版を整理 | 渡辺 遥 | 2025-08-29T00:00:00 | 2025-08-29T00:00:00 | - | 完了 | 週次内部レビュー |
| 4 | マイルストーン | 4. 中間報告・変更管理・改善 | MS4 | 中間報告完了 | 欠損処理方針、カテゴリ統合方針、主指標・補助指標、継続モデル方針を合意 | 佐藤 健一 | 2025-09-08T00:00:00 | 2025-09-08T00:00:00 | - | 完了 | 関連会議: M02 中間報告 |
| 5 | マイルストーン | 4. 中間報告・変更管理・改善 | MS5 | 変更管理チェックポイント完了 | 中間報告の決定事項を反映し、追加要求の影響有無を記録 | 佐藤 健一 | 2025-09-09T00:00:00 | 2025-09-09T00:00:00 | - | 完了 | 中間報告後判定 |
| 6 | マイルストーン | 5. 最終化・QA・納品準備 | MS6 | 最終成果物ドラフト完成 | 最終報告書ドラフト、分析成果物一式、QA指摘反映版を作成 | 渡辺 遥 / 清水 麻衣 | 2025-09-19T00:00:00 | 2025-09-19T00:00:00 | - | 完了 | 内部レビュー |
| 7 | マイルストーン | 6. 最終報告・クローズ | MS7 | 最終報告・成果物提出 | 最終分析結果、性能評価、公平性留意点、業務示唆、成果物受領内容を確認 | 佐藤 健一 | 2025-09-26T00:00:00 | 2025-09-26T00:00:00 | - | 完了 | 関連会議: M03 最終報告 |
| 8 | マイルストーン | 6. 最終報告・クローズ | MS8 | 契約期間内の補足対応完了 | 会議後質問対応、納品ログ整理、検収準備完了 | 藤田 彩 | 2025-09-29T00:00:00 | 2025-09-29T00:00:00 | - | 完了 | クローズ確認 |
```

### Rank 3
- score: 106.919779
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

### Rank 4
- score: 101.90981
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

### Rank 5
- score: 100.967867
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
- score: 100.134605
- record_id: `generic_chunk_39dd71275f3729ed`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
い（監査／解釈基準の根幹）。

<!-- block_index=80 type=paragraph style=Compact -->
interest_rate / grade を「審査時点で利用可」とするか否かを決定してください（運用実装可否に直結）。

<!-- block_index=81 type=paragraph style=Compact -->
追加要望が発生した場合は、変更管理ポリシー（別紙見積）に従う方針で運用することを確認ください。

<!-- block_index=82 type=paragraph style=Compact -->
商務情報（Report facts の commercial／project_facts に基づく）

<!-- block_index=83 type=paragraph style=Compact -->
契約形態: 固定価格（fixed_price）

<!-- block_index=84 type=paragraph style=Compact -->
契約金額（税抜）: 4,200,000 円

<!-- block_index=85 type=paragraph style=Compact -->
税率: 10%（税額 420,000 円）

<!-- block_index=86 type=paragraph style=Compact -->
契約金額（税込）: <mark data-font-color="#FF0000" style="color:#FF0000" data-highlight="YELLOW (7)">4,620,000</mark> 円

<!-- block_index=87 type=paragraph style=Compact -->
支払スケジュール: 2 回分割（着手金 50%／検収金 50%） — 各金額は payment_schedule に記載の通り

<!-- block_index=88 type=paragraph style=Compact -->
支払管理は PM（伊藤 翔太）で統括

<!-- block_index=89 type=paragraph style=Compact -->
クリティカルパスと次マイルストーン

<!-- block_index=90 type=paragraph style=Compact -->
クリティカルな前提: loan_status の業務定義確定および interest_rate/grade の利用可否確認（これらが確定しないと中間レビュー以降のモデル解釈が不確定になります）。

<!-- block_index=91 type=paragraph style=Compact -->
次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください。

<!-- block_index=92 type=paragraph style=Compact -->
現状の運用上の判断メモ

<!-- block_index=93 type=paragraph style=Compact -->
キックオフ時点では、分析結果ではなく前提整理の完了を優先してください。

<!-- block_index=94 type=paragraph style=Compact -->
監査証跡の観点では、議事録（キックオフ）を含めた前提定義の早期登録が必須です。

<!-- block_index=95 type=paragraph style=Normal -->

<!-- block_index=96 type=paragraph s
```

### Rank 7
- score: 99.055582
- record_id: `generic_chunk_b65c33743063f717`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
# Word Markdown: 報告資料_2025-09-16.docx

## Source
- raw_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
- source_sha1: `1ee371126fa3b54feba9a916ae7a235dd627f53f`
- paragraph_count: 99
- table_count: 0
- image_count: 0

## Body

<!-- block_index=1 type=paragraph style=Heading 1 -->
## 分析進捗報告書

<!-- block_index=2 type=paragraph style=Heading 2 -->
## 1. 報告サマリー

<!-- block_index=3 type=paragraph style=Compact -->
チェックポイント: M02（中間レビュー）

<!-- block_index=4 type=paragraph style=Compact -->
会議日: 2025-09-16

<!-- block_index=5 type=paragraph style=Compact -->
報告対象期間: 2025-09-02 ～ 2025-09-16

<!-- block_index=6 type=paragraph style=Compact -->
本報告の分析段階: interim（中間） — 本中間段階では Report facts JSON.analysis.checkpoint_stage に従い、visible_trials（trial_index 1〜5）で公開された実験結果のみを引用しています。最終的なチャンピオンモデルや最終スコアは本中間報告では扱いません。

<!-- block_index=7 type=paragraph style=Compact -->
主要現状要約:

<!-- block_index=8 type=paragraph style=Compact -->
初期の線形系ベースライン系列の比較試行（visible trials = 5）を実施し、trial_index=4（T04: threshold_tuned_linear）が現在のベスト（可視領域）として確認されています。

<!-- block_index=9 type=paragraph style=Compact -->
モデル評価（可視領域）は f1_macro を主指標とし、T04 の f1_macro = 0.7329671168078127、accuracy = 0.7357142857142858、補助的に AUC-ROC = 0.8250532501536466（analysis.metrics）等を記録しています。

<!-- block_index=10 type=paragraph style=Compact -->
未解決のアクション（Open）は7件（prior_state.open_action_count = 7）として残存しています（詳細は第6節参照）。

<!-- block_index=11 type=paragraph style=Heading 2 -->
## 2. 進捗状況

<!-- block_index=12 type=paragraph style=Compact -->
スケジュールとの整合（抜粋）

<!-- block_index=13 type=paragraph style=Compact -->
プロジェクト
```

### Rank 8
- score: 97.755079
- record_id: `xlsx_sheet_fd181a5aac9bbfe5`
- record_type: `xlsx_sheet`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/02.計画/スケジュール.xlsx`

```text
Excelファイル: スケジュール.xlsx
シート: マイルストーン
使用範囲: A1:G9
列: マイルストーンID, マイルストーン名, 日付, 関連会議, 完了条件, オーナー, ステータス
グラフ数: 0
サンプル:
| マイルストーンID | マイルストーン名 | 日付 | 関連会議 | 完了条件 | オーナー | ステータス |
| --- | --- | --- | --- | --- | --- | --- |
| MS1 | キックオフ完了 | 2025-07-08T00:00:00 | キックオフ | 目的、範囲、役割、評価指標、会議運営を合意 | 加藤 大輔 | 完了 |
| MS2 | データ理解完了 | 2025-07-18T00:00:00 | 週次定例 | 基礎集計、クラス分布、主要論点、初期仮説を整理 | 山本 彩乃 | 完了 |
| MS3 | 中間報告完了 | 2025-07-22T00:00:00 | 中間報告 | 初期モデル結果、重要変数傾向、深掘り観点をレビュー完了 | 山本 彩乃 | 完了 |
| MS4 | 変更管理判定完了 | 2025-07-24T00:00:00 | 変更管理チェックポイント | 追加要望の有無、影響範囲、費用・納期影響を判定 | 加藤 大輔 | 完了 |
| MS5 | 分析方針凍結 | 2025-07-29T00:00:00 | 週次定例 | 最終評価対象モデル、採用指標、報告構成を確定 | 山本 彩乃 | 完了 |
| MS6 | 最終成果物内部承認 | 2025-08-01T00:00:00 | 社内レビュー | QAレビュー完了、整合性確認完了、報告資料確定 | 池田 直哉 | 完了 |
| MS7 | 最終報告完了 | 2025-08-05T00:00:00 | 最終報告 | 最終成果物提出、説明完了、次フェーズ候補整理完了 | 加藤 大輔 | 完了 |
| MS8 | 支払期限到来 | 2025-08-13T00:00:00 | なし | 当月分タイムシート確定後、請求書受領から5営業日以内の支払期限到来 | 宮本 恒一 | 完了 |
```
