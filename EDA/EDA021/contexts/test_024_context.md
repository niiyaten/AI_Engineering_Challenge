# test_024

## Question
分析データの中で、1つでも欠損値がある行数が最も多い案件を、主略称で答えてください。

## Route
fallback_bm25_llm

## Generated Answer
学習データの行数（8,645行）はプロジェクト概要に記載がありますが、当該数値は本報告の主出典（Report facts JSON）内に明示されていないため「assumption（仮置き）」として扱います。正式なデータ件数は A03 の品質報告で再確認してください。

## Retrieved Records

### Rank 1
- score: 60.027366
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

### Rank 2
- score: 56.077809
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

### Rank 3
- score: 53.303585
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

### Rank 4
- score: 51.68599
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

### Rank 5
- score: 47.836616
- record_id: `generic_chunk_5bac8161e5eadf9a`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx`

```text
gday の定義不整合: A02（進行中）を完了し、前処理仕様へ反映する必要あり。これが未確定のまま前処理を固定すると、曜日/平日フラグ起因の特徴解釈に誤差が残るリスクがあります。

<!-- block_index=55 type=paragraph style=Compact -->
詳細な欠損・分布レポート（A03）および初期EDA図表（A04）は未提出・未着手のため、EDAベースの解釈は限定的です。metrics.json 内の eda_summary は生成されていますが、ビジネス合意用の解釈図表はまだ整備中です。

<!-- block_index=56 type=paragraph style=Compact -->
注意（数値補足）

<!-- block_index=57 type=paragraph style=Compact -->
学習データの行数（8,645行）はプロジェクト概要に記載がありますが、当該数値は本報告の主出典（Report facts JSON）内に明示されていないため「assumption（仮置き）」として扱います。正式なデータ件数は A03 の品質報告で再確認してください。

<!-- block_index=58 type=paragraph style=Heading 2 -->
## 5. リスクと対応策

<!-- block_index=59 type=paragraph style=Compact -->
主要リスク（現フェーズでの優先度高）

<!-- block_index=60 type=paragraph style=Compact -->
データ定義不整合リスク（高）

<!-- block_index=61 type=paragraph style=Compact -->
根拠: yr / workingday の辞書と実データの差異が確認されている（M01議事録・A02）。

<!-- block_index=62 type=paragraph style=Compact -->
影響: 前処理/特徴量設計の誤り、モデル解釈の齟齬。

<!-- block_index=63 type=paragraph style=Compact -->
対策: A02 を優先完了 → 前処理仕様へ反映（担当: 鈴木 / 木村）。クライアント側での定義確認（A06: 高山）を催促。MS2（2025-07-29）相当のゲート完了を確認。

<!-- block_index=64 type=paragraph style=Compact -->
外生要因依存／汎化性リスク（中）

<!-- block_index=65 type=paragraph style=Compact -->
根拠: 気象・祝日等の影響が大きい想定。現行データ範囲での偏りがある場合、外挿性が低下する。

<!-- block_index=66 type=paragraph style=Compact -->
対策: 時系列交差検証・外部期間での妥当性確認を追加で実施。結果の解釈条件を成果物に明記。

<!-- block_index=67 type=paragraph style=Compact -->
スコープ／スケジュールリスク（中）

<!-- block_index=68 type=paragraph style=Compact -->
根拠: Week3 中間での追加要求や定義修正が後工程に波及する可能性。

<!-- block_index=69 type=paragraph style=Compact -->
対策: 変更管理ポリシー（T19）に従い、スコープ外作業は別途見積。リスクバッファを活用。

<
```

### Rank 6
- score: 44.978446
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

### Rank 7
- score: 43.238486
- record_id: `generic_chunk_0ec626ab1150778a`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
yle=Normal -->

<!-- block_index=27 type=paragraph style=Heading 2 -->
## 3. キックオフ時点の確認事項

<!-- block_index=28 type=paragraph style=First Paragraph -->
キックオフ時点では、分析結果ではなく前提確認とデータ受領状況のみを共有する。

<!-- block_index=29 type=paragraph style=Compact -->
データ概要

<!-- block_index=30 type=paragraph style=Compact -->
レコード数: 17,500

<!-- block_index=31 type=paragraph style=Compact -->
カラム数: 10

<!-- block_index=32 type=paragraph style=Compact -->
欠損: 全項目 <span data-font-color="#FF0000" style="color:#FF0000">0.0</span>（初期前処理における欠損補完は不要）

<!-- block_index=33 type=paragraph style=Compact -->
分析着手前の整理事項

<!-- block_index=34 type=paragraph style=Compact -->
学習行数: 14,000、検証行数: 3,500

<!-- block_index=35 type=paragraph style=Compact -->
解析上の示唆（初期）

<!-- block_index=36 type=paragraph style=Compact -->
欠損がないため、前処理コストは低い。一方で、順序カテゴリ（grade, employment_length, term）や金利（interest_rate）の業務意味（審査時点で利用可能か）が解析と運用で異なる可能性があるため、変数の扱いを二通り（運用可能変数のみ／すべての変数）で評価する必要あり。

<!-- block_index=37 type=paragraph style=Compact -->
時系列情報が欠落しているため、ドリフト検知やビンテージ分析は本データ単体で実施不可。

<!-- block_index=38 type=paragraph style=Compact -->
留意点

<!-- block_index=39 type=paragraph style=Compact -->
「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。

<!-- block_index=40 type=paragraph style=Normal -->

<!-- block_index=41 type=paragraph style=Heading 2 -->
## 4. データ品質と実装状況

<!-- block_index=42 type=paragraph style=Compact -->
データ品質

<!-- block_index=43 type=paragraph style=Compact -->
欠損: 全カラムで 0%（eda_summary.mis
```

### Rank 8
- score: 40.613747
- record_id: `pptx_slide_25ec3c6aeb4d5ff9`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`

```text
Slide 9
04
4.2 前処理方針
対象
処理方法
詳細
除外
id列
識別子のためモデリングから除外
除外
日付列
本件データに日時情報がないため実施しない
数値欠損
中央値補完
数値欠損値が存在する場合に適用
カテゴリ欠損
最頻値補完
カテゴリ欠損値が存在する場合に適用
カテゴリ変換
One-Hot Encoding
閾値未満のカテゴリ数の場合に適用
高カーディナリティ
除外
高カーディナリティのカテゴリ列は除外
Gender列
標準カテゴリ変換
2値カテゴリのため標準的な変換対象
※本データでは欠損値は存在しない前提であるが、実装上は再現性確保のため補完ルールを定義したうえで処理系に組み込む。
```
