# EDA045: 残件20件の未route化棚卸し

## 背景と目的

EDA044提出スコアは `-0.3` まで改善したが、残り20件には既存route名では表現しきれていない質問が残っている。
EDA045では、回答生成は行わず、残件を新しく作るべきroute候補へ分類した。

## 結果

- 入力: `EDA/EDA044/tables/test_format_table_image_result.csv`
- 残件: 20件
- 新route候補数: 9件

## 新route候補別集計

凡例: `new_route_candidate` は新設すべきroute候補、`count` は件数、`indices` は対象質問ID、`recommended_next_action` は次に実装すべき処理を表す。

| new_route_candidate                 |   count | indices     | recommended_next_action                    |
|:------------------------------------|--------:|:------------|:-------------------------------------------|
| meeting_action_status_lookup        |       4 | 18,49,93,96 | 会議ID/日付/アクションIDをキーに会議録と報告資料を結合する           |
| model_formula_recompute             |       3 | 57,63,83    | 係数表、実装コード、train.csvを結合してpandasで再計算する       |
| contract_alias_contact_lookup       |       2 | 43,46       | 社内用語集、契約書、体制表、座席/連絡先情報を結合して検索する            |
| cross_project_contract_aggregation  |       2 | 38,79       | 全案件の契約書/最終報告/スケジュール/社内管理基準を正規化して集計する       |
| proposal_operation_clause_lookup    |       2 | 52,75       | PPTXスライド構造と契約条項をキーワードではなく節単位で検索する          |
| seating_chart_spatial_ocr           |       2 | 44,58       | 座席表画像をVision/OCRに送り、座席座標とラベルを構造化する         |
| spreadsheet_format_semantic_context |       2 | 65,80       | styled_cellsと同じ行/列/周辺表を結合し、色の意味を推定する       |
| structured_diff_semantic_filter     |       2 | 62,95       | PPTX/XLSX/Notebookを構造単位で比較し、状態変更や設定差分を分類する |
| chart_value_extraction              |       1 | 33          | 元データ、chart XML、画像OCR/Visionを組み合わせて値を抽出する   |

## 質問別分類

凡例: `old_route`/`old_subtype` はこれまでの分類、`new_route_candidate` は新しく必要な処理単位、`why_existing_route_is_insufficient` は既存routeで足りない理由を表す。

|   index | old_route              | old_subtype              | new_route_candidate                 | question                                                                                                                                      | why_existing_route_is_insufficient            | recommended_next_action                    |
|--------:|:-----------------------|:-------------------------|:------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------|:-------------------------------------------|
|      18 | document_whole_context | document_whole_context   | meeting_action_status_lookup        | 白峰信用リスク評価の会議ID:M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。                                                                                          | 会議録、報告資料、アクションID、チェックポイントを横断するroute           | 会議ID/日付/アクションIDをキーに会議録と報告資料を結合する           |
|      33 | image_ocr              | line_search              | chart_value_extraction              | 青潮モビリティサービスの基礎分析.docxのグラフ2で、x=3のときの青色の折れ線のyの値を小数第5位で答えてください。                                                                                  | 画像またはExcelグラフから系列名と座標値を読むroute                | 元データ、chart XML、画像OCR/Visionを組み合わせて値を抽出する   |
|      38 | table_calculation      | line_search              | cross_project_contract_aggregation  | 社内管理のAPRに照らして、APR-M3が必要な案件を主略称ですべて挙げ、それらの契約金額(税込)の合計を答えてください。                                                                                 | 複数案件の契約条件、APR、工数、データ行数を横断集計するroute            | 全案件の契約書/最終報告/スケジュール/社内管理基準を正規化して集計する       |
|      43 | fallback_bm25_llm      | line_search              | contract_alias_contact_lookup       | 東都のCTにおいて、甲側の主担当者をフルネームで教えてください。                                                                                                              | 契約書や社内用語の略称からCT/ESなどの役割を解決し、人物名や内線へつなぐroute   | 社内用語集、契約書、体制表、座席/連絡先情報を結合して検索する            |
|      44 | fallback_bm25_llm      | line_search              | seating_chart_spatial_ocr           | IMにあるFMにおいて、佐藤さんから見て右側に座っている人の名前をすべて挙げてください。                                                                                                  | 座席表画像から位置関係と氏名/EXTを読むroute                    | 座席表画像をVision/OCRに送り、座席座標とラベルを構造化する         |
|      46 | fallback_bm25_llm      | line_search              | contract_alias_contact_lookup       | 着手金が最も高い案件について、その案件のESの内線番号を教えてください。                                                                                                          | 契約書や社内用語の略称からCT/ESなどの役割を解決し、人物名や内線へつなぐroute   | 社内用語集、契約書、体制表、座席/連絡先情報を結合して検索する            |
|      49 | document_whole_context | line_search              | meeting_action_status_lookup        | 東都人材プラットフォームの会議録において、コメントがついている部分をそのまま抽出してください。                                                                                               | 会議録、報告資料、アクションID、チェックポイントを横断するroute           | 会議ID/日付/アクションIDをキーに会議録と報告資料を結合する           |
|      52 | fallback_bm25_llm      | line_search              | proposal_operation_clause_lookup    | 蒼樹会 みなみ野女性医療センターの今後の運用に関する記載の中で、データアステル側の役割として「別契約」と明記されているものを抽出してください。                                                                       | 提案書/契約書内の運用条項やスケジュール項目を抽出するroute              | PPTXスライド構造と契約条項をキーワードではなく節単位で検索する          |
|      57 | table_calculation      | line_search              | model_formula_recompute             | 青葉のTXにて算出された回帰係数を用いて全データの予測値を計算し、正解データに対する F1 スコアが最大となるように閾値を設定したときの F1 スコアを答えてください。小数第5位まで求めてください。                                           | Notebook/コード/報告書の係数や閾値を取り出してrawデータで再計算するroute | 係数表、実装コード、train.csvを結合してpandasで再計算する       |
|      58 | fallback_bm25_llm      | line_search              | seating_chart_spatial_ocr           | 社内管理フォルダにあるFMにおいて、井上さんの向かいに座っている方のEXTを教えてください。                                                                                                | 座席表画像から位置関係と氏名/EXTを読むroute                    | 座席表画像をVision/OCRに送り、座席座標とラベルを構造化する         |
|      62 | diff_check             | version_diff             | structured_diff_semantic_filter     | 青葉与信マネジメントの最終報告資料における、モデル比較で上位2件のスコア差を生んでいる設定差分は何ですか。                                                                                         | old/new差分から案件遂行に関係する変更だけを抽出するroute            | PPTX/XLSX/Notebookを構造単位で比較し、状態変更や設定差分を分類する |
|      63 | table_calculation      | line_search              | model_formula_recompute             | 青葉与信マネジメントのtrain.xlsxにて算出された回帰係数を使ってid=0を予測した場合の予測値はいくらになりますか。小数第5位まで求めてください。                                                                 | Notebook/コード/報告書の係数や閾値を取り出してrawデータで再計算するroute | 係数表、実装コード、train.csvを結合してpandasで再計算する       |
|      65 | format_extraction      | xlsx_yellow_cell_context | spreadsheet_format_semantic_context | 白峰信用リスク評価のtrain.xlsxにおいて、表示されている相関係数シートで、黄色ハイライトになっているセルの条件を答えてください。                                                                          | セル色や表示形式から、条件・集計対象・意味を復元するroute               | styled_cellsと同じ行/列/周辺表を結合し、色の意味を推定する       |
|      75 | fallback_bm25_llm      | line_search              | proposal_operation_clause_lookup    | MINAMINOのPP内のPL案において、モデル構築は第何週に実施することになっていますか。                                                                                                | 提案書/契約書内の運用条項やスケジュール項目を抽出するroute              | PPTXスライド構造と契約条項をキーワードではなく節単位で検索する          |
|      79 | fallback_bm25_llm      | line_search              | cross_project_contract_aggregation  | 恒一会 かえで総合病院の計画フォルダ内において、データアステル側の担当者のうち、1タスク当たりの想定工数(想定工数 ÷ 担当タスク数)が最も大きい人のフルネームと、その1タスク当たりの想定工数を小数第2位で答えてください。ファイルに鍵がかかっている場合は社内管理を確認してください。 | 複数案件の契約条件、APR、工数、データ行数を横断集計するroute            | 全案件の契約書/最終報告/スケジュール/社内管理基準を正規化して集計する       |
|      80 | format_extraction      | xlsx_yellow_cell_context | spreadsheet_format_semantic_context | 東都人材プラットフォームのtrain.xlsxにおいて、Sheet2の黄色にハイライトされたセルの抽出条件と集計内容を答えてください。                                                                           | セル色や表示形式から、条件・集計対象・意味を復元するroute               | styled_cellsと同じ行/列/周辺表を結合し、色の意味を推定する       |
|      83 | table_calculation      | line_search              | model_formula_recompute             | 蒼樹会 みなみ野女性医療センターのtrain.xlsxにおいて、回帰分析の結果として記載されている係数をindex=1770のデータに当てはめたときの予測値はいくつですか。小数第5位まで答えてください。                                         | Notebook/コード/報告書の係数や閾値を取り出してrawデータで再計算するroute | 係数表、実装コード、train.csvを結合してpandasで再計算する       |
|      93 | fallback_bm25_llm      | line_search              | meeting_action_status_lookup        | 蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。                                                                                                 | 会議録、報告資料、アクションID、チェックポイントを横断するroute           | 会議ID/日付/アクションIDをキーに会議録と報告資料を結合する           |
|      95 | diff_check             | version_diff             | structured_diff_semantic_filter     | 青嶺不動産アセットマネジメントのスケジュール_r1.xlsxとスケジュール_r2.xlsxを比較したとき、未着手から完了への変更を除いて、案件遂行に関連する変更点を挙げてください。                                                    | old/new差分から案件遂行に関係する変更だけを抽出するroute            | PPTX/XLSX/Notebookを構造単位で比較し、状態変更や設定差分を分類する |
|      96 | fallback_bm25_llm      | line_search              | meeting_action_status_lookup        | 青葉与信マネジメントのチェックポイント2として設定されている内容に関連するタスクIDを教えてください。                                                                                           | 会議録、報告資料、アクションID、チェックポイントを横断するroute           | 会議ID/日付/アクションIDをキーに会議録と報告資料を結合する           |

## 次の方針

優先度は、件数と正解可能性の両方で判断する。
最初に作るべきrouteは `contract_alias_contact_lookup`、`meeting_action_status_lookup`、`model_formula_recompute`、`cross_project_contract_aggregation` のいずれかである。
スコア改善だけを狙うなら、誤答リスクが高い画像・座席表より、表計算と契約横断集計を先に処理する方がよい。
