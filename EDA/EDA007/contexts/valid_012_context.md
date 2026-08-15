# valid_012 LLM Context

## Question
京橋信用ソリューションズの契約金額（税込）はいくらですか。

## Validation Answer
5,775,000円

## Diagnosis
- required_capability: document_qa
- context_quality_for_llm: ready_for_llm
- answer_hit_top5: True
- recommended_next_step: LLM向けMarkdownコンテキストを作る

## Retrieved Evidence

### Evidence 1
- score: 163.7259
- source_eda: EDA004
- extension: .docx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 01.契約
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx

```text
乙から最終成果物の納品を受けた後、2025-11-12までに検収を行うものとする。
## paragraph_052 - style: Compact 甲は、成果物に本契約の内容との不一致または合理的に重大な瑕疵を認めた場合、前項の期限までに乙に対し書面または電子メールで具体的理由を付して通知するものとする。
## paragraph_053 - style: Compact 乙は、前号の通知を受けた場合、合理的な範囲で修正対応を行い、再提出する。
## paragraph_054 - style: Compact 甲が第1号の期限までに不合格通知を行わないときは、当該成果物は2025-11-12をもって検収完了したものとみなす。
## paragraph_055 - style: Compact 検収は、成果...
```

### Evidence 2
- score: 160.6325
- source_eda: EDA004
- extension: .docx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 01.契約
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx

```text
h_111 - style: Compact 本契約に関し甲乙間に生じる一切の紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。
## paragraph_112 - style: Heading 2 13. 署名欄
## paragraph_113 - style: First Paragraph 本契約締結の証として、本書を2通作成し、甲乙各1通を保有する。
## paragraph_114 - style: Body Text 契約締結日兼効力発生日：2025-10-01 #
## run_styles - bold: 契約締結日兼効力発生日：2025-10-01
## paragraph_115 - style: Heading 3 甲
## paragraph_116 - style:...
```

### Evidence 3
- score: 156.1083
- source_eda: EDA004
- extension: .docx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 01.契約
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx

```text
契約に定める業務範囲、対象外業務、成果物定義および前提条件との整合に基づき行う。
## table_001
row_001: 支払回 | 名目 | 比率 | 金額（税抜） | 消費税額 | 金額（税込） | 支払条件 | 支払期日
row_002: 第1回 | 着手金 | 50% | 2,625,000円 | 262,500円 | 2,887,500円 | 契約締結後5営業日以内 | 2025-10-08
row_003: 第2回 | 検収金 | 50% | 2,625,000円 | 262,500円 | 2,887,500円 | 最終成果物の検収完了後5営業日以内 | 2025-11-19
```

### Evidence 4
- score: 155.4648
- source_eda: EDA004
- extension: .pptx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 00.提案
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/00.提案/提案書_v1.pptx

```text
メント分析、公平性確認 W5 10/29-11/04 中間報告、レビュー反映、最終モデル方針確定、監査・再現性記録整理 M4: 中間報告完了 W6 11/05-11/11 最終報告、最終成果物提出、QA反映、検収対応 M5: 最終報告 / M6: 検収 11
## slide_012 7. 成果物定義 table_
row_001: 成果物 | 内容 table_
row_002: 提案書 | 背景、課題、分析方針、体制、スケジュール、見積前提を記載 table_
row_003: 契約ドラフト | スコープ、納品物、金額、支払条件、変更管理条件を記載 table_
row_004: スケジュール | 6週間の作業計画、レビュー日、納品日を記載 table_
row_005: 議事録 | キックオフ、要件確認、中間報告、...
```

### Evidence 5
- score: 155.072
- source_eda: EDA004
- extension: .pptx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 00.提案
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/00.提案/提案書_final.pptx

```text
析、セグメント分析、公平性確認 W5 10/29-11/04 中間報告、レビュー反映、最終モデル方針確定、監査・再現性記録整理 M4: 中間報告完了 W6 11/05-11/11 最終報告、最終成果物提出、QA反映、検収対応 M5: 最終報告 / M6: 検収 11
## slide_012 7. 成果物定義 table_
row_001: 成果物 | 内容 table_
row_002: 提案書 | 背景、課題、分析方針、体制、スケジュール、見積前提を記載 table_
row_003: 契約ドラフト | スコープ、納品物、金額、支払条件、変更管理条件を記載 table_
row_004: スケジュール | 6週間の作業計画、レビュー日、納品日を記載 table_
row_005: 議事録 | キックオフ、要件確認、中...
```
