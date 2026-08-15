# test_067

## Question
完了案件のうち、社内管理のAPRでAPR-M2に該当する案件の中で、提案時金額とFR時の金額が異なる案件を案件略称ですべて挙げてください。

## Route
fallback_bm25_llm

## Generated Answer
- 通常で `部長承認` の金額帯に該当する場合は `本部長承認`、- 通常で `課長承認` の金額帯に該当する場合は `部長承認`、2025-09-19 の変更管理チェックポイントは契約上の追加対応要否を判定する重要日です。追加要求が出た場合は change_request_policy（time_and_materials）に従って見積り・承認の流れを確保してください。、次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください。、キックオフ時点では、分析結果ではなく前提整理の完了を優先してください。

## Retrieved Records

### Rank 1
- score: 142.68431
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

### Rank 2
- score: 82.281199
- record_id: `generic_chunk_4cccee31d4d0f4b1`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/社内用語集.docx`

```text
ス俗称 |
| 資料置き場 | DOC-BOX | ファイル群全体 |
| マスター管理表 | LEDGER | 台帳類の俗称 |
| 元資料 | PARENT-DOC | ソース資料 |
| 派生資料 | CHILD-DOC | 加工後資料 |
| 他案件流用 | SIDE-COPY | 使い回し |
| 案件フォルダ一式 | CASE-BOX | 案件単位の塊 |
| 共有ドライブ | SHARE-BAY | 社内俗称 |
| 社内ルール | INT-RULE | 決裁・PW規則等含む |

<!-- block_index=17 type=paragraph style=Normal -->
**8. 組織・案件略称**

<!-- block_index=18 type=table rows=9 cols=3 -->
| 正式名称 | 社内用語 | 補足 |
| --- | --- | --- |
| データサイエンス本部 | DS-HQ | 組織略称 |
| 案件推進室 | CASE-HUB | PMO系チーム |
| 営業企画 | BIZ-PLAN | 営業支援・提案管理 |
| 法務・情報管理 | LEGAL-INFO | 法務確認・情報統制 |
| 統括マネージャー | LEAD-MGR | 役職略称 |
| 経営スポンサー | EXEC-SP | 役職英語表記 |
| 案件オーナー | CASE-OWN | 営業責任者・主管部門長 |
| 品質レビュー責任者 | QA-HEAD | QA統括者 |

<!-- block_index=19 type=paragraph style=Normal -->

<!-- block_index=20 type=table rows=13 cols=4 -->
| 案件名 | 主略称 | 別名候補 | 補足 |
| --- | --- | --- | --- |
| 京橋信用ソリューションズ株式会社 | KSS | 京ソ, 京橋, 京ソリ, KYO | KSS を正式、会話では 京ソ 系も可 |
| 青葉与信マネジメント株式会社 | AYM | 青葉, 青マネ, 与信青葉, AY | AYM を正式 |
| 白峰信用リスク評価株式会社 | SHR | 白峰, 白リス, 白峰信評, SHI | SHR を正式 |
| 株式会社青潮モビリティサービス | AOSHIO | 青潮, 青モビ, 潮モビ, AOS | 長いので通称併用可 |
| 医療法人社団 蒼泉会 ひがし丘総合病院 | SOHK | ひがし丘, 蒼泉会, 丘病院, 東丘 | 医療案件略称として SOHK を正式 |
| 株式会社東都人材プラットフォーム | TOTO | 東都, 人材PF, 東都PF, TTP | TOTO を正式 |
| 株式会社青嶺不動産アセットマネジメント | AOMINE | 青嶺, 不動産AM, 青嶺AM, AOM | 長いので通称併用可 |
| 医療法人社団 恒一会 かえで総合病院 | KAEDE | かえで, 恒一会, 楓病院, 楓 | KAEDE を正式 |
| 株式会社青葉バイオメディカル機器 | AOBM | 青葉バイオ, 青バイオ, バイオ機器, ABM | AYM と混同しやすいため AOBM を正式 |
| 医療法人社団 蒼樹会 みなみ野女性医療センター | MINAMINO | みなみ野, 蒼樹会, 女性医療, みな女 | 既存レコードとの整合上 MINAMINO を正式 |
| 案件横断 | CROSS | 横断, 案件横断 | 将来変動あり |
| 社内管理共通 | INTERNAL | 社内管理, 共通管理 | 案件非依存 |

<!-- block_index=21 typ
```

### Rank 3
- score: 75.977545
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

### Rank 4
- score: 71.082233
- record_id: `generic_chunk_e11f34ce88ab0de5`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`

```text
# Word Markdown: データアステル社内規定_パスワード導出規則.docx

## Source
- raw_path: `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`
- source_sha1: `3c398b562eabcd2eadbf6482c616b72a814cf92d`
- paragraph_count: 13
- table_count: 0
- image_count: 0

## Body

<!-- block_index=1 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**データアステル社内規定_パスワード導出規則**</span>

<!-- block_index=2 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**1. 目的**</span>

<!-- block_index=3 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">案件フォルダ内の一部保護ファイルについて、社内規定に基づく共通ルールでパスワードを導出できるようにする。</span>

<!-- block_index=4 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**2. パスワード導出の基本形式**</span>

<!-- block_index=5 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">パスワードは次の形式で構成する。</span>

<!-- block_index=6 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">DA-[案件略号]-[開始年月日8桁]-[拡張子コード]</span>

<!-- block_index=7 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">例:</span>

<!-- block_index=8 type=paragraph style=Normal -->
DA-AOMINE-20250806-xlsx

<!-- block_index=9 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**3. 案件略号一覧**</span>

<!-- block_index=10 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">社内用語集にて規定されている主略称を使用する</span>

<!-- block_index=11 type=paragraph style=Normal -->
<sp
```

### Rank 5
- score: 67.198347
- record_id: `generic_chunk_f509df3eab7c3d02`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx`

```text
t -->
Week1（〜2025-07-29）でのデータ定義差異の解消可否が、以降の分析方針（前処理・特徴量設計・分割戦略）を左右します。早期対応を推奨します（MS2 をゲート化）。

<!-- block_index=83 type=paragraph style=Compact -->
追加データ取得（イベント、拠点、移動履歴等）を行う場合は、スコープ・工数に影響するため早めに要求の可否を決定してください（変更管理: T19／MS7）。

<!-- block_index=84 type=paragraph style=Compact -->
短期案件のため、本フェーズでは「予測可能性の確認」と「説明可能性の確保」を優先し、本番実装やMLOpsは次フェーズで検討する方針です。

<!-- block_index=85 type=paragraph style=First Paragraph -->
最後に、現在のオープン状態は「議事録未登録のため詳細宿題は未反映」ですが、Report facts JSON の記録上はオープンアクション数=0です。キックオフで決定・議論された内容は議事録作成後に課題管理表へ反映し、次回中間報告（M02: 2025-08-06）に向けてT02〜T05を完了することを優先します。

<!-- block_index=86 type=paragraph style=Body Text -->
以上。
```

### Rank 6
- score: 64.467987
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

### Rank 7
- score: 64.157901
- record_id: `generic_chunk_a992c01bb40b7d6d`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/社内用語集.docx`

```text
INO | みなみ野, 蒼樹会, 女性医療, みな女 | 既存レコードとの整合上 MINAMINO を正式 |
| 案件横断 | CROSS | 横断, 案件横断 | 将来変動あり |
| 社内管理共通 | INTERNAL | 社内管理, 共通管理 | 案件非依存 |

<!-- block_index=21 type=paragraph style=Normal -->
```

### Rank 8
- score: 58.195627
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
