# EDA055: グラフ値・黄色セル・回帰係数route

## 背景と目的

EDA054後に残った `わかりません` のうち、ローカルで再現しやすい3件を個別route化する。
対象は、index 33のWordグラフ値、index 80のExcel黄色セル、index 83のExcel回帰係数再計算。

## 方針

- OpenRouterは使わず、元ファイルまたはprocessed表から再計算する。
- 提出候補へ採用するのは、根拠ファイルと計算手順が明確なものだけにする。
- EDA054の提出候補をベースに、今回の3件だけを上書きする。

## 結果

- EDA054時点の `わかりません`: 12
- EDA055後の `わかりません`: 9
- 追加採用: 3

| index | route | 採用回答 | 根拠 |
| --- | --- | --- | --- |
| 33 | docx_chart_xml_value_extraction | 137.64768 | `基礎分析.docx` 内の `word/charts/chart2.xml` から1本目の系列を抽出し、x=3の値を取得。 |
| 80 | xlsx_yellow_cell_semantic_extraction | 抽出条件はGender=Male、target=2、Age=40-44、Country=Spain。集計内容は個数=12。 | `train.xlsx.structure.json` の黄色セル `E1409` と、前方補完したSheet1集計表から条件と個数を復元。 |
| 83 | xlsx_regression_formula_recompute | 0.38317 | `train.xlsx.sheets/Sheet1.csv` の回帰係数をindex=1770の行に適用して再計算。 |

凡例: `index` はtest質問ID、`route` は今回の処理名、`採用回答` は提出候補に反映した回答、`根拠` は採用判断に使ったファイルと計算内容を表す。

## 出力

- route結果: `EDA/EDA055/tables/eda055_route_results.csv`
- 提出候補CSV: `EDA/EDA055/predictions/eda055_chart_format_formula_predictions.csv`
- 提出候補zip: `EDA/EDA055/predictions/eda055_chart_format_formula_submission.zip`

## 注意

index 80は質問文ではSheet2とあるが、raw xlsxをopenpyxlで確認したところ、シートは `Sheet1`, `Sheet2`, `train` の3枚で、黄色セルは `Sheet1!E1409` の1件だけだった。
そのため、提出候補では実ファイル上の黄色セルを優先して `Sheet1!E1409` 由来の条件と個数を採用する。
