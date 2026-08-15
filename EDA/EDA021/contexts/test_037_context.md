# test_037

## Question
AOBMにおいて、見込金額（税込）と確定金額（税込）の差を、ESTHとACTHの差で割った1時間あたりの減少金額を計算してください。

## Route
fallback_bm25_llm

## Generated Answer
open actions = 7（prior_state.open_action_count = 7）。PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソース配分を確定してください。

## Retrieved Records

### Rank 1
- score: 91.065862
- record_id: `pptx_slide_4a470469dacaa401`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx`

```text
Slide 12
8. 費用見積
契約形態
Time & Materials
時間単価
¥25,000
見込工数
170時間
見込金額（税込）
¥4,675,000
契約条件詳細
請求単位：hour
精算ルール：実績工数に基づく事後精算（月次精算）
工数丸め単位：30分
見込金額（税抜）：4,250,000円
消費税額：425,000円
支払条件
支払回：1回（100%）
条件：当月分タイムシート確定後、請求書受領から5営業日以内
金額（税抜）：4,250,000円
消費税額：425,000円
金額（税込）：4,675,000円
⚠ 重要事項
本契約はTime & Materialsであり、上記金額は170時間を前提とした見込金額である。
最終請求額は固定総額ではなく、実績工数に時間単価を乗じ、消費税を加算した金額に基づく。
```

### Rank 2
- score: 87.878894
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
- score: 82.367574
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
- score: 78.755582
- record_id: `pptx_slide_5a9d8ed8c4f724b7`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/提案書.pptx`

```text
Slide 12
8. 費用見積
契約形態：タイム&マテリアル（実績工数精算） ｜ 通貨：JPY ｜ 請求単位：時間
時間単価
25,000円
/時間
見込工数
170時間
見込金額（税込）
4,675,000円
税抜: 4,250,000円
精算ルール
実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する
工数丸め単位：30分
上記金額は見込金額であり、最終金額は実績工数に基づく
支払条件
支払回数：1回（100%）
条件：最終成果物の検収完了後5営業日以内
金額（税抜）：4,250,000円
消費税額：425,000円 ｜ 金額（税込）：4,675,000円
12
```

### Rank 5
- score: 77.650692
- record_id: `pptx_slide_4530aa5ee84bd6d0`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`

```text
Slide 16
08
費用見積
見込金額（税込）
¥3,850,000
（税抜 ¥3,500,000 ＋ 消費税10% ¥350,000）
契約条件
契約形態　準委任（Time & Materials）
時間単価　¥25,000 / 時間
見込工数　140時間
工数丸め　30分単位
精算ルール　実績工数ベース、検収後一括精算
支払条件
一括払い（100%） │ 最終成果物の検収完了後5営業日以内 │ ¥3,850,000（税込）
■ 留意事項
本契約はTime & Materials方式のため、上記の見込工数および見込金額は計画時点の想定値であり、固定総額を保証するものではない。実際の請求額は、実績工数に基づき精算する。
```

### Rank 6
- score: 73.624345
- record_id: `pptx_slide_6edf87de064d595f`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/00.提案/提案書.pptx`

```text
Slide 13
8. 費用見積
| col_1 | col_2 | col_3 | col_4 | col_5 | col_6 |
| --- | --- | --- | --- | --- | --- |
| 支払回 | 比率 | 支払条件 | 金額（税抜） | 消費税額 | 金額（税込） |
| 1 | 100% | 最終成果物の検収完了後 5営業日以内 | 4,250,000円 | 425,000円 | 4,675,000円 |
8.1 契約条件 ／ 8.2 見積条件
契約形態
Time & Materials
実績工数ベース
時間単価
¥25,000
/ 時間（税抜）
見込工数
170 時間
30分単位で計上
見込金額
¥4,675,000
（税込）
8.3 精算ルール ／ 8.4 支払条件
※ 上記金額は見込値である。実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する。工数は30分単位で計上する。
13
```

### Rank 7
- score: 70.382941
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
- score: 69.650261
- record_id: `pptx_slide_7541bb67d077de21`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/提案書.pptx`

```text
Slide 12
8. 費用見積
見込金額（税込）
¥4,675,000
税抜 ¥4,250,000 + 消費税 ¥425,000
契約形態
タイム&マテリアル
時間単価
¥25,000/時間
見込工数
170時間
工数丸め
30分単位
※ 固定総額契約ではなく、最終請求額は実績工数に基づいて確定する
※ 精算ルール：実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算
支払条件：最終成果物の検収完了後5営業日以内に一括支払（100%）　税込 ¥4,675,000
```
