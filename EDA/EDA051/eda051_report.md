# EDA051: 全案件横断集計テーブル

## 背景と目的

EDA048では、全案件横断集計が残件16件中3件を占めた。
検索文脈だけでは全件比較が保証できないため、契約条件、金額、担当体制、計画リソースを案件単位のテーブルへ正規化する。

## 結果

- 契約条件レコード数: 11
- 役割/担当者レコード数: 49
- 計画/リソース候補レコード数: 327
- 案件マスター行数: 11
- 残件候補行数: 3

## 残件候補

凡例: `candidate_answer` は横断テーブルから作った候補、`needs_review` は提出採用前に確認が必要かを表す。

|   index | question                                                      | candidate_answer   | needs_review   |
|--------:|:--------------------------------------------------------------|:-------------------|:---------------|
|      38 | 社内管理のAPRに照らして、APR-M3が必要な案件を主略称ですべて挙げ、それらの契約金額(税込)の合計を答えてください。 |                    | True           |
|      46 | 着手金が最も高い案件について、その案件のESの内線番号を教えてください。                          | 白峰信用リスク評価株式会社      | True           |
|      79 | かえで総合病院の計画フォルダ内で、1タスク当たりの想定工数が最も大きい人と工数を答える。                  | resource rows: 0   | True           |

## 出力

- 契約条件: `EDA/EDA051/tables/contract_terms_inventory.csv`
- 役割/担当者: `EDA/EDA051/tables/role_assignment_inventory.csv`
- 計画/リソース候補: `EDA/EDA051/tables/schedule_resource_inventory.csv`
- 案件マスター: `EDA/EDA051/tables/project_master_aggregation.csv`
- 残件候補: `EDA/EDA051/tables/cross_project_question_probe.csv`

## 注意

契約金額や着手金はMarkdown本文から正規表現で抽出している。
最終提出用では、抽出元の構造JSONや契約書表を併用し、金額の取り違えを検査する必要がある。
ESなどの役割略称と内線番号を結びつけるには、EDA049の座席表テーブルと役割テーブルを結合する。
