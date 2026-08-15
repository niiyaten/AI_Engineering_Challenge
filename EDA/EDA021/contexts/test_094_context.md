# test_094

## Question
蒼樹会 みなみ野女性医療センターのスケジュール.xlsxにおいて、MS3に紐づくタスクのうち、ビジネスアナリストが関わっているタスクIDを答えてください。

## Route
table_calculation

## Generated Answer
医療法人社団 蒼樹会 みなみ野女性医療センター

## Retrieved Records

### Rank 1
- score: 160.434799
- record_id: `metadata_1e0853e7a6c4b8a5`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/02.計画/スケジュール.xlsx`

```text
ファイル名: スケジュール.xlsx
元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/02.計画/スケジュール.xlsx
ファイル種別: xlsx
```

### Rank 2
- score: 145.965406
- record_id: `generic_chunk_6c6c031bd0b4e312`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
ody Text -->
優先度高（次回チェックポイント＝中間レビュー前に完了推奨） - A1: loan_status の業務定義を確定・文書化（タスク: T02）
- 担当: 発注者 中村 浩一（最終承認）／ベンダー: 山本 彩乃（確認）
- 状態: 要確定（議事録登録が前提） - A2: interest_rate / grade の「審査時点での利用可否」を確定（タスク: T03）
- 担当: 発注者 中村 浩一、ビジネスアナリスト 藤田 彩（調整）
- 目的: リーケージ判定と「モデルに投入する変数セット」の最終決定 - A3: 議事録登録と正式アクション（キックオフ議事録のアップロード）
- 担当: PM 伊藤 翔太 / ビジネスアナリスト 藤田 彩
- 理由: 監査証跡の整備（現時点で議事録は未登録）

<!-- block_index=73 type=paragraph style=Body Text -->
中優先（データ理解・中間レビュー準備） - B1: データ品質確認と型整備の完了（タスク: T06, T07） — 品質確認スクリプト・変数定義表作成
- 担当: データエンジニア 斎藤 悠斗 / ビジネスアナリスト 藤田 彩 - B2: 単変量・セグメント別不良率の初期分析（タスク: T09, T10） — 中間レビューの材料作成
- 担当: リードデータサイエンティスト 山本 彩乃 / 藤田 彩 - B3: 中間レビュー資料（初期探索結果 + モデル比較方針）作成（タスク: T11）
- 担当: 藤田 彩（資料作成）、山本 彩乃（内容確認）

<!-- block_index=74 type=paragraph style=Body Text -->
低優先（モデル本体・評価の詳細化） - C1: ベースライン／説明性重視モデルの比較計画作成（タスク: T14/T15 設定）
- 担当: 山本 彩乃 - C2: 現行パイプラインの再現手順・版管理の整備（アーティファクト格納の整理）

<!-- block_index=75 type=paragraph style=Body Text -->
備考（トレーサビリティ） - 参照タスク: T01〜T25（スケジュールのタスクIDに紐付け）。次のレビューで各タスクの「予定→進行中→完了」へステータス更新を行い、クリティカルパスの遅延有無を確認します。 - 現時点のオープンアクション数は Report facts prior_state.open_action_count = 0 ですが、上記 A1/A2/A3 はキックオフ議事録登録を前提に正式アクションとして登録する必要があります。

<!-- block_index=76 type=paragraph style=Normal -->

<!-- block_index=77 type=paragraph style=Heading 2 -->
## 7. 経営/PM向け補足

<!-- block_index=78 type=paragraph style=Compact -->
重要決定依頼（経営／PM へ）

<!-- block_index=79 type=paragraph style=Compact -->
loan_status の 0/1 の業務定義を至急確定し、議事録で公式に残してください（監査／解釈基準の根幹）。

<!-- block_index=80 type=paragraph style=Compact -->
interest_rate / grade を「審査時点で利用可」とするか否かを決定してください（運用実装可否に直結）。

<!-- block_index=81 type=para
```

### Rank 3
- score: 134.499832
- record_id: `pptx_slide_01827e4c3929ca11`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/提案書.pptx`

```text
Slide 8
5. 実施体制
クライアント体制
医療法人社団 蒼樹会 みなみ野女性医療センター
医療情報・品質改善推進室　林 さくら 室長
ベンダー体制
株式会社データアステル
データサイエンス部
エグゼクティブスポンサー
山田 直樹
全体統括、重要課題の意思決定支援
プロジェクトマネージャー
伊藤 翔太
進行管理、課題管理、対外窓口
リードデータサイエンティスト
鈴木 美咲
分析設計、モデル評価、結果解釈
データエンジニア
岡田 佑樹
データ整形、前処理実装、再現環境整備
ビジネスアナリスト
松本 真央
要件整理、業務論点整理、報告資料整備
QAレビュー担当
池田 直哉
成果物レビュー、整合性・品質確認
推進運営
週次進捗確認
週1回
中間レビュー
分析方針確定後1回
最終報告会
成果物提出時1回
議事録管理
決定・保留・依頼を明確化
8
```

### Rank 4
- score: 126.070388
- record_id: `metadata_05dc2d9dc7bd81b8`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf`

```text
ファイル名: 医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf
元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf
ファイル種別: pdf
```

### Rank 5
- score: 114.418244
- record_id: `pdf_page_28abcae95ee5f6f1`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf`

```text
株式会社データアステル
```

### Rank 6
- score: 113.265183
- record_id: `image_b3b9d0926e16a4f3`
- record_type: `image`
- source_path: `data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/target_distribution.png`

```text
画像ファイル: target_distribution.png
パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/target_distribution.png
```

### Rank 7
- score: 113.265183
- record_id: `image_9dda88847df98bc6`
- record_type: `image`
- source_path: `data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/overview_schema.png`

```text
画像ファイル: overview_schema.png
パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/overview_schema.png
```

### Rank 8
- score: 113.265183
- record_id: `image_3bffd193497a82ec`
- record_type: `image`
- source_path: `data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png`

```text
画像ファイル: numeric_distribution_top6.png
パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png
```
