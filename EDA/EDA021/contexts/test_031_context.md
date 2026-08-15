# test_031

## Question
固定金額契約の中で、分析データ1行あたりの契約金額（税込）が最も高い案件を、主略称と1行あたりの金額で答えてください。1行あたりの金額は円単位で切り上げてください。

## Route
fallback_bm25_llm

## Generated Answer
工数丸め単位は30分とし、30分未満の端数は30分単位で切り上げて計上する。

## Retrieved Records

### Rank 1
- score: 157.048606
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

### Rank 2
- score: 120.355452
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
- score: 117.052348
- record_id: `markdown_chunk_95e123adfbf3f37b`
- record_type: `markdown_chunk`
- source_path: `share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`

```text
# データアステル社内管理_決裁基準

## 1. 目的

本規程は、案件の契約金額および契約条件に応じた社内決裁レベルを定め、提案・契約・請求に関する承認プロセスを統一することを目的とする。

## 2. 通常の決裁基準

契約金額（税込）に応じた基本の決裁レベルは次の通りとする。

| 契約金額（税込） | 必要な承認 |
|---|---|
| 3,000,000円未満 | 主任承認 |
| 3,000,000円以上 5,000,000円未満 | 課長承認 |
| 5,000,000円以上 8,000,000円未満 | 部長承認 |
| 8,000,000円以上 | 本部長承認 |

## 3. 追加基準

### 3.1 医療案件

医療機関、医療法人、病院、診療所その他これに準ずる案件は、個人情報・機微情報の取扱いおよび説明責任を踏まえ、通常の決裁基準より **1段階上** の承認を必要とする。

例:

- 通常で `課長承認` の金額帯に該当する場合は `部長承認`
- 通常で `部長承認` の金額帯に該当する場合は `本部長承認`

## 3.2 time_and_materials 契約

`time_and_materials` 契約は、金額に関わらず **部長承認以上** を必要とする。

この基準は通常の決裁基準および医療案件ルールより優先して適用する。ただし、医療案件かつ `time_and_materials` 契約であり、通常基準から1段階上げた結果が本部長承認に達する場合は、本部長承認を要する。

## 4. 適用順序

決裁レベルは次の順に判定する。

1. 通常の決裁基準を契約金額（税込）から判定する
2. 医療案件である場合は 1段階引き上げる
3. `time_and_materials` 契約である場合は、少なくとも部長承認以上とする

## 5. 補足

- 本規程における「契約金額」は、提案時の見込金額ではなく、契約締結時点で社内決裁に付された税込金額を原則とする。
- 契約変更により税込金額または契約形態が変わる場合は、必要に応じて再決裁を行う。
```

### Rank 4
- score: 110.947048
- record_id: `generic_chunk_c907a2d587336ccb`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/01.契約/契約書.docx`

```text
nd_materialsとし、実績工数に基づき精算する。上記は固定総額契約ではなく、最終請求額は実績工数に基づいて確定する。

<!-- block_index=54 type=paragraph style=Heading 3 -->
### 6.2 商業条件

<!-- block_index=55 type=paragraph style=First Paragraph -->
本契約の商業条件は以下のとおりとする。

<!-- block_index=56 type=table rows=9 cols=2 -->
| 項目 | 内容 |
| --- | --- |
| 通貨 | JPY |
| 課金単位 | hour |
| 時間単価 | 25,000円/時間 |
| 想定総工数 | 170時間 |
| 想定金額（税抜） | 4,250,000円 |
| 消費税率 | 10% |
| 消費税額 | 425,000円 |
| 想定金額（税込） | 4,675,000円 |

<!-- block_index=57 type=paragraph style=Heading 3 -->
### 6.3 工数記録および丸め

<!-- block_index=58 type=paragraph style=Compact -->
乙は、作業実績を工数表その他の合理的な方法により記録し、甲の求めがある場合は提示する。

<!-- block_index=59 type=paragraph style=Compact -->
工数計上は30分単位で行う。

<!-- block_index=60 type=paragraph style=Compact -->
30分未満の端数は30分に切り上げ、30分を超え1時間未満の端数は次の30分単位に切り上げる。

<!-- block_index=61 type=paragraph style=Heading 3 -->
### 6.4 精算方法

<!-- block_index=62 type=paragraph style=First Paragraph -->
精算は、実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する。

<!-- block_index=63 type=paragraph style=Heading 3 -->
### 6.5 支払条件

<!-- block_index=64 type=paragraph style=First Paragraph -->
甲は、乙に対し、以下の支払条件に従い支払うものとする。

<!-- block_index=65 type=table rows=2 cols=7 -->
| 支払回 | マイルストーン | 比率 | 金額（税抜） | 消費税額 | 金額（税込） | 支払期限 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 最終一括精算 | 100% | 4,250,000円 | 425,000円 | 4,675,000円 | 最終成果物の検収完了後5営業日以内（2025-09-24） |

<!-- block_index=66 type=paragraph style=Heading 3 -->
### 6.6 請求

<!-- block_index=67 type=paragraph style=Compact -->
乙は、検収完了後、実績工数に基づく金額を記載した請求書を甲に発行する。

<!-- block_index=68 type=paragraph style=Compact -->
甲は、適法な請求書を受領した場合、前項の支払期限までに乙の指定口
```

### Rank 5
- score: 107.465074
- record_id: `generic_chunk_f11a598d242af3e0`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/01.契約/契約書.docx`

```text
graph style=Compact -->
想定総工数：170時間

<!-- block_index=81 type=paragraph style=Compact -->
想定金額（税抜）：4,250,000円

<!-- block_index=82 type=paragraph style=Compact -->
消費税率：10%

<!-- block_index=83 type=paragraph style=Compact -->
消費税額：425,000円

<!-- block_index=84 type=paragraph style=Compact -->
想定金額（税込）：4,675,000円

<!-- block_index=85 type=paragraph style=Heading 3 -->
### 6.3 工数計上および丸め

<!-- block_index=86 type=paragraph style=Compact -->
工数は乙の作業実績に基づき計上する。

<!-- block_index=87 type=paragraph style=Compact -->
工数丸め単位は30分とし、30分未満の端数は30分単位で切り上げて計上する。

<!-- block_index=88 type=paragraph style=Compact -->
乙は、甲の求めがある場合、実績工数の明細を提示する。

<!-- block_index=89 type=paragraph style=Heading 3 -->
### 6.4 精算方法

<!-- block_index=90 type=paragraph style=First Paragraph -->
精算方法は、実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算するものとする。

<!-- block_index=91 type=paragraph style=Heading 3 -->
### 6.5 支払条件

<!-- block_index=92 type=paragraph style=First Paragraph -->
甲は、乙に対し、以下のとおり支払う。

<!-- block_index=93 type=table rows=2 cols=8 -->
| 支払回 | マイルストン | 比率 | 金額（税抜） | 消費税額 | 金額（税込） | 支払条件 | 支払期日 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 最終一括精算 | 100% | 4,250,000円 | 425,000円 | 4,675,000円 | 最終成果物の検収完了後5営業日以内 | 2025-09-03 |

<!-- block_index=94 type=paragraph style=Heading 3 -->
### 6.6 支払方法

<!-- block_index=95 type=paragraph style=First Paragraph -->
乙は、検収完了後、適法な請求書を甲に発行する。甲は、前項の支払期日までに、乙指定の銀行口座へ振込送金の方法により支払う。振込手数料は甲の負担とする。

<!-- block_index=96 type=paragraph style=Heading 2 -->
## 7. 知的財産権

<!-- block_index=97 type=paragraph style=Heading 3 -->
### 7.1 甲に帰属するもの

<!-- block_index=98 type=paragraph st
```

### Rank 6
- score: 104.970954
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

### Rank 7
- score: 101.956819
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

### Rank 8
- score: 96.191426
- record_id: `pptx_slide_134671eaec266438`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

```text
Slide 9
5. 業務提言 ─ 運用方法と閾値設定
1. パイロット運用（短期即実行）
限定地域・担当者でのパイロット運用を実施
上位スコア群に対し優先接触を実行
効果計測: 接触成功率、受注率、営業工数（4〜8週間）
事前意思決定ではduration除外モデルを必ず使用する
2. 推奨閾値設定
上位 10%　→　高優先
10 ─ 30%　→　候補
30% 以下　→　低優先
※ 閾値はA/Bテスト結果により調整する
各閾値に対する期待効果のKPI定量評価
増分契約率: 各閾値層での契約率向上を定量評価
コスト効率: 接触あたりの販促コストと受注額の比率
説明ログと閾値設定を標準化する
```
