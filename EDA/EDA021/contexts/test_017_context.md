# test_017

## Question
AYMのMMにおいて、黄色ハイライトかつREDになっている数値を対象に、最初のMMから最後のMMまでの上昇率を計算してください。上昇率は （最後の値 - 最初の値） / 最初の値 × 100 で求め、小数第2位まで答えてください。

## Route
format_extraction

## Generated Answer
「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。

## Retrieved Records

### Rank 1
- score: 128.029732
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
- score: 120.442762
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
- score: 106.904983
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
- score: 105.248569
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

### Rank 5
- score: 94.471178
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

### Rank 6
- score: 89.39646
- record_id: `generic_chunk_ffad5b0952383675`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
nt-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: 234,000ドル</span></span>

<!-- block_index=84 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">この推移から、最初の5年間で約4万ドル、10年経過時点で約8万ドルという極めて急激な昇給カーブを描くことがわかる。初期のキャリア段階で基礎的なデータ処理能力を証明し、その後、複雑なモデル構築やビジネス戦略の立案へと役割を拡張していくプロセスが、この賃金上昇を支えている。</span></span>

<!-- block_index=85 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">また、Interview Query等のプラットフォームが提供する役職レベル別の基本給データでも、この傾向は明確に裏付けられている。</span></span>

<!-- block_index=86 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**エントリーレベル（経験0-1年）**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: 平均 100,369ドル（中央値 92K / 最高 155K）</span></span>

<!-- block_index=87 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**ミッドレベル（経験2-5年）**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: 平均 134,182ドル（中央値 139K / 最高 181K）</span></span>

<!-- block_index=88 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**シニア（経験
```

### Rank 7
- score: 87.562916
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
- score: 84.365205
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
