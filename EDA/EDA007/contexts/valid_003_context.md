# valid_003 LLM Context

## Question
全案件で支払った税込金額をもとに、消費税額の総額を計算してください。

## Validation Answer
4,394,250円

## Diagnosis
- required_capability: table_tool
- context_quality_for_llm: needs_table_tool
- answer_hit_top5: False
- recommended_next_step: CSV/XLSXをpandas/openpyxlで直接処理する

## Retrieved Evidence

### Evidence 1
- score: 82.9049
- source_eda: EDA002
- extension: .md
- project_name: nan
- major_folder: データアステル社内管理_決裁基準.md
- relative_path: 社内管理/データアステル社内管理_決裁基準.md

```text
## 1. 目的 本規程は、案件の契約金額および契約条件に応じた社内決裁レベルを定め、提案・契約・請求に関する承認プロセスを統一することを目的とする。
## 2. 通常の決裁基準 契約金額（税込）に応じた基本の決裁レベルは次の通りとする。 | 契約金額（税込） | 必要な承認 | |---|---| | 3,000,000円未満 | 主任承認 | | 3,000,000...
```

### Evidence 2
- score: 82.1207
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 蒼泉会 ひがし丘総合病院
- major_folder: 01.契約
- relative_path: プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/01.契約/契約書.docx

```text
請求単位はhourとする。
## paragraph_073 - style: Compact 時間単価は25,000円（消費税別）とする。
## paragraph_074 - style: Compact 想定総工数は170時間とする。
## paragraph_075 - style: Compact 見込金額は、税抜4,250,000円、消費税425,000円、税込4,675,000円とする。
## paragraph_076 - style: Compact 前項の見込金額は170時間を前提とした見込額であり、契約総額を固定するものではない。最終請求額は、実績工数に時間単価を乗じ、これに消費税を加算した金額とする。
## paragraph_077 - style: Heading 3 6.3 工数記...
```

### Evidence 3
- score: 81.8023
- source_eda: EDA004
- extension: .docx
- project_name: 青葉与信マネジメント株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx

```text
モデル比較方針）作成（タスク: T11） - 担当: 藤田 彩（資料作成）、山本 彩乃（内容確認）
## paragraph_074 - style: Body Text 低優先（モデル本体・評価の詳細化） - C1: ベースライン／説明性重視モデルの比較計画作成（タスク: T14/T15 設定） - 担当: 山本 彩乃 - C2: 現行パイプラインの再現手順・版管理の整備（アーティファクト格納の整理）
## paragraph_075 - style: Body Text 備考（トレーサビリティ） - 参照タスク: T01〜T25（スケジュールのタスクIDに紐付け）。次のレビューで各タスクの「予定→進行中→完了」へステータス更新を行い、クリティカルパスの遅延有無を確認します。 - 現時点のオープンアクション数...
```

### Evidence 4
- score: 80.9208
- source_eda: EDA004
- extension: .docx
- project_name: 青葉与信マネジメント株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx

```text
4 - style: Compact 契約金額（税抜）: 4,200,000 円
## paragraph_085 - style: Compact 税率: 10%（税額 420,000 円）
## paragraph_086 - style: Compact 契約金額（税込）: 4,620,000 円 #
## run_styles - highlight=YELLOW (7)/font_color=FF0000: 4,620,000
## paragraph_087 - style: Compact 支払スケジュール: 2 回分割（着手金 50%／検収金 50%） — 各金額は payment_schedule に記載の通り
## paragraph_088 - style: Compact 支払管理は PM...
```

### Evidence 5
- score: 79.2077
- source_eda: EDA004
- extension: .docx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 05.会議
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/05.会議/報告資料/報告資料_2025-10-01.docx

```text
経営/PM向け補足
## paragraph_067 - style: Compact 商務情報（契約条件）
## paragraph_068 - style: Compact 契約開始日: 2025-10-01
## paragraph_069 - style: Compact 契約期間: 6週間（プロジェクト期間）
## paragraph_070 - style: Compact 契約金額（税抜）: 5,250,000 円
## paragraph_071 - style: Compact 消費税率: 10%、消費税額: 525,000 円、税込合計: 5,775,000 円
## paragraph_072 - style: Compact 支払スケジュール（契約に準拠）
## paragraph_07...
```
