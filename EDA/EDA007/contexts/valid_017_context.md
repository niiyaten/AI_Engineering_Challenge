# valid_017 LLM Context

## Question
京橋信用ソリューションズのカラム説明において、カラム名pdaysの値-1は何を表していますか。

## Validation Answer
未連絡

## Diagnosis
- required_capability: document_qa
- context_quality_for_llm: ready_for_llm
- answer_hit_top5: True
- recommended_next_step: LLM向けMarkdownコンテキストを作る

## Retrieved Evidence

### Evidence 3
- score: 176.4552
- source_eda: EDA004
- extension: .docx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 01.契約
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx

```text
paragraph_031 - style: Compact pdays=-1 の業務上特別値としての設計
## paragraph_032 - style: Compact エンコーディング方針
## paragraph_033 - style: Compact 学習・評価データ分割方針
## paragraph_034 - style: Compact ベースラインモデルおよび説明可能なモデルの比較評価
## paragraph_035 - style: Compact duration 含有モデルと非含有モデルの比較整理
## paragraph_036 - style: Compact 性能評価、重要変数分析、セグメント別示唆の整理
## paragraph_037 - style: Compact 監...
```

### Evidence 4
- score: 165.3145
- source_eda: EDA004
- extension: .pptx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 00.提案
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/00.提案/提案書_final.pptx

```text
ム説明.md を正式なカラム定義として参照 欠損件数0件を前提に、業務上の不明値カテゴリを識別 education=unknown、contact=unknown、poutcome=unknown は欠損補完せず有効カテゴリとして保持 pdays=-1 は前回未接触を示す特別値として扱い、数値とフラグの両面から有効性を検証 4.2 探索的データ分析 目的変数 y の分布と契約率11.7%を確認 顧客属性別、接触履歴別、過去成果別の契約率を整理 balance、duration、campaign、previous 等の外れ値・裾の長い分布を確認 高見込み顧客の特徴仮説を形成し、中間レビューで妥当性を確認 対象データ概要 データセット: train.csv ｜ レコード数: 27,128件 ｜ カラム数: 18 ｜...
```

### Evidence 5
- score: 163.7984
- source_eda: EDA004
- extension: .pptx
- project_name: 京橋信用ソリューションズ株式会社
- major_folder: 00.提案
- relative_path: プロジェクト/京橋信用ソリューションズ株式会社/00.提案/提案書_v1.pptx

```text
## slide_001 データ分析プロジェクト提案書 定期預金契約予測モデル構築と説明可能な分析基盤の整備 提出先：京橋信用ソリューションズ株式会社 リスク管理部 与信モデル統括課 作成：株式会社データアステル データサイエンス部 1
## slide_002 1. 背景 京橋信用ソリューションズ株式会社 リスク管理部 与信モデル統括課において、金融商品提案および顧客接触施策の高度化に向け、顧客ごとの契約見込みを定量的に把握し、説明可能な形で活用できる分析基盤の整備が求められている。本プロジェクトでは、27,128件・18カラムの顧客データを用い、定期預金等の契約有無を予測する初期版モデルを構築する。 現状の課題 経験則依存 経験則に依存した接触判断が行われてい...
```
