# test_036

## Question
恒一会 かえで総合病院案件において、中間報告時点のF1スコア実測値と最終報告時点のF1スコア実測値の差を絶対値で答えてください。

## Route
fallback_bm25_llm

## Generated Answer
2 中間報告時点の試行結果共有

## Retrieved Records

### Rank 1
- score: 94.133811
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
- score: 90.5831
- record_id: `pptx_slide_d5fd9fa3daf2271a`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`

```text
Slide 18
17. 総括
本プロジェクトは、提案・契約どおりの期間内に分析基盤および初期モデルを整備し、判定支援として実用性のある示唆（閾値運用案、運用前パイロット設計、データ品質管理方針）を提示した。
主要な成果と今後の方向性
内部検証結果
良好。スコア上位の患者を優先的にフォローする運用に即した施策が実行可能である。
実運用化の条件
外部検証やパイロットによる再確認、運用フローの整備が必須である。
推奨アクション
運用パイロット→評価→本番化の順で進めることを推奨する。
推奨する次のステップ
運用パイロット
実施
精度・業務負荷
評価
閾値最終
チューニング
本番化検討
ご不明点や追加の検証依頼があれば、会議にてご指示ください。
```

### Rank 3
- score: 90.5831
- record_id: `pptx_slide_b348a01e2b898800`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`

```text
Slide 18
17. 総括
本プロジェクトは、提案・契約どおりの期間内に分析基盤および初期モデルを整備し、判定支援として実用性のある示唆（閾値運用案、運用前パイロット設計、データ品質管理方針）を提示した。
主要な成果と今後の方向性
内部検証結果
良好。スコア上位の患者を優先的にフォローする運用に即した施策が実行可能である。
実運用化の条件
外部検証やパイロットによる再確認、運用フローの整備が必須である。
推奨アクション
運用パイロット→評価→本番化の順で進めることを推奨する。
推奨する次のステップ
運用パイロット
実施
精度・業務負荷
評価
閾値最終
チューニング
本番化検討
ご不明点や追加の検証依頼があれば、会議にてご指示ください。
```

### Rank 4
- score: 88.378777
- record_id: `pdf_page_f855af2ac2219c5c`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

```text
3. 実施方法
モデリング方針と評価方法
モデリング方針
中間報告時点
公開可能試行: 5件
中間時点最良モデル: linear_baseline
Accuracy: 0.86875 / Macro F1: 0.7320
最終分析出力
最終モデル: random_forest
n_estimators: 500 | max_depth: 12
min_samples_leaf: 2 | class_weight: balanced
max_features: sqrt
評価方法
タスク種別 classification（3クラス分類）
データ分割 holdout split (test_size=0.2)
学習データ 1,280件
テストデータ 320件
評価指標
Accuracy
Macro F1
各クラス Precision / Recall
混同行列
※ クラス別Precision/Recall・混同行列の最終値は入力資料に未収録のため、
 評価実施済みの事実のみ記載し、未確認数値の補完記載は行わない
```

### Rank 5
- score: 85.211345
- record_id: `pdf_page_835c5148db117ede`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

```text
9. 成果物サマリ
成果物サマリ
成果物 状態 役割
提案書 作成済み 合意形成
契約ドラフト/契約書 作成済み 契約条件固定
スケジュール 作成済み 進行管理
議事録 作成・保管対象 合意記録
中間報告 作成済み 進捗共有
最終報告 本書 最終成果報告
分析計画書/分析作業メモ 作成対象 再現性確保
課題管理表 作成対象 論点管理
目的変数定義メモ 作成対象 用語統一
データ前処理仕様メモ 作成対象 実装整合
モデル評価サマリ 作成対象 評価記録
主要仮定一覧 作成対象 追跡可能性確保
本報告で確認できる到達内容
1 プロジェクト前提の固定
2 中間報告時点の試行結果共有
3 最終分析出力の評価値確認
4 変更管理差分の整理
5 今後の運用・拡張提言の明文化
```

### Rank 6
- score: 82.916059
- record_id: `metadata_8cda600cb73d3838`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`

```text
ファイル名: 医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx
ファイル種別: pptx
```

### Rank 7
- score: 82.916059
- record_id: `metadata_d570985f0177469e`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`

```text
ファイル名: 医療法人社団 恒一会 かえで総合病院_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx
ファイル種別: pptx
```

### Rank 8
- score: 81.773254
- record_id: `generic_chunk_c4ac9c113e383414`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/05.会議/報告資料/報告資料_2025-07-22.docx`

```text
>
公開可能試行の範囲では、**Macro F1 = 0.7319904178115971、Accuracy = 0.86875** が確認されている。

<!-- block_index=11 type=paragraph style=Compact -->
ただし、これは**中間時点の可視結果**であり、最終評価対象モデルの確定前である。

<!-- block_index=12 type=paragraph style=Compact -->
未解決事項として、**クラス不均衡への対応方針の最終化、追加深掘り観点の優先順位決定、表現上の医療ドメイン配慮の最終確認**が残っている。

<!-- block_index=13 type=paragraph style=Heading 2 -->
## 2. 進捗状況

<!-- block_index=14 type=paragraph style=Heading 3 -->
### 2.1 チェックポイント時点の全体進捗

<!-- block_index=15 type=paragraph style=First Paragraph -->
本案件は、5週間計画のうち**第3週マイルストーン**に位置している。スケジュール上の該当イベントは以下の通り。

<!-- block_index=16 type=paragraph style=Compact -->
**MS1 ****キックオフ完了**: 2025-07-08

<!-- block_index=17 type=paragraph style=Compact -->
**MS2 ****データ理解完了**: 2025-07-18

<!-- block_index=18 type=paragraph style=Compact -->
**MS3 ****中間報告完了**: 2025-07-22（本チェックポイント）

<!-- block_index=19 type=paragraph style=Compact -->
**次回チェックポイント**: 2025-07-24 変更管理判定

<!-- block_index=20 type=paragraph style=Compact -->
**最終報告**: 2025-08-05

<!-- block_index=21 type=paragraph style=Heading 3 -->
### 2.2 WBSトレースによる進捗整理

<!-- block_index=22 type=paragraph style=First Paragraph -->
中間報告時点で、計画上は以下のタスク群が本チェックポイントに関連する。

<!-- block_index=23 type=paragraph style=Compact -->
完了到達が期待されるタスク

<!-- block_index=24 type=paragraph style=Compact -->
T01 プロジェクト開始準備・招集

<!-- block_index=25 type=paragraph style=Compact -->
T02 キックオフ実施

<!-- block_index=26 type=paragraph style=Compact -->
T03 対象データ・カラム定義確認

<!-- block_index=27 type=paragraph style=Compact -->
T04 分析計画詳細化

<!-- block_index=28 type=paragraph style=Compact -->
T05 課題管理表・運営ルール整備

<!-- block_i
```
