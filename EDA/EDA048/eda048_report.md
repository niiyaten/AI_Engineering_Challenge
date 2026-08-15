# EDA048: EDA046後に `わかりません` が残る理由の整理

## 背景と目的

EDA046では、EDA045で分類した残件20件に個別routeを作り、OpenRouter 20Bで短答化した。
その結果、4件は追加採用できたが、16件はまだ `わかりません` のままだった。

EDA048では、この16件について「個別routeを作ってもなぜ解けなかったか」を分類し、次に作るべき処理を決める。

## 入力

- EDA046結果: `EDA/EDA046/tables/test_all_remaining_routes_result.csv`
- EDA046 attempt log: `EDA/EDA046/tables/test_all_remaining_routes_attempt_log.csv`
- EDA045 gap inventory: `EDA/EDA045/tables/remaining_route_gap_inventory.csv`
- EDA047 image-to-text結果: `EDA/EDA047/tables/image_to_text_results.csv`

## 結果

- EDA046後の `わかりません`: 16件
- EDA047画像処理: 8件中5件成功

## 残件の失敗ファミリー

凡例: `failure_family` は失敗の種類、`eda048_priority` は次に実装する優先度、`size` は件数を表す。

| failure_family                       | eda048_priority   |   size |
|:-------------------------------------|:------------------|-------:|
| meeting_action_structure             | high              |      4 |
| cross_project_structured_aggregation | high              |      3 |
| spatial_image                        | high              |      2 |
| chart_value                          | high              |      1 |
| model_formula_recompute              | high              |      1 |
| pptx_table_or_clause_lookup          | medium            |      2 |
| semantic_diff                        | medium            |      2 |
| spreadsheet_format_semantics         | medium            |      1 |

## 残件別の診断

凡例: `index` はtest質問番号、`new_route_candidate` はEDA045で提案したroute、`why_unknown` は残った理由、`next_action` は次に作る処理を表す。

|   index | route                  | new_route_candidate                 | question                                                                                                                                      | failure_family                       | why_unknown                                                              | next_action                                                                         |
|--------:|:-----------------------|:------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------|:-------------------------------------------------------------------------|:------------------------------------------------------------------------------------|
|      18 | document_whole_context | meeting_action_status_lookup        | 白峰信用リスク評価の会議ID:M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。                                                                                          | meeting_action_structure             | PDF/Word会議録の本文検索だけでは、会議ID、ページ、アクションID、コメント、完了状態の対応が構造化されていない。            | 会議録/報告資料をページ単位・表単位で再抽出し、meeting_id、date、page、action_id、status、comment_textを持つ台帳を作る。 |
|      33 | image_ocr              | chart_value_extraction              | 青潮モビリティサービスの基礎分析.docxのグラフ2で、x=3のときの青色の折れ線のyの値を小数第5位で答えてください。                                                                                  | chart_value                          | 画像説明だけでは小数第5位の値を読めない。元Notebook/CSVまたは生成コードから系列値を再計算する必要がある。              | Notebookの該当セルと元CSVを結合し、グラフ番号、系列色、x値からy値を計算するrouteを作る。Visionは図の特定補助に限定する。            |
|      38 | table_calculation      | cross_project_contract_aggregation  | 社内管理のAPRに照らして、APR-M3が必要な案件を主略称ですべて挙げ、それらの契約金額(税込)の合計を答えてください。                                                                                 | cross_project_structured_aggregation | 複数案件の契約書、社内管理基準、計画表、担当者情報を横断して正規化する必要がある。検索文脈では比較対象の全件性が保証できない。          | 全案件の契約条件・略称・金額・担当者・工数を1つの正規化テーブルにし、質問ごとに集計式を実行する。                                   |
|      44 | fallback_bm25_llm      | seating_chart_spatial_ocr           | IMにあるFMにおいて、佐藤さんから見て右側に座っている人の名前をすべて挙げてください。                                                                                                  | spatial_image                        | 座席表画像の人名/EXTだけでなく、左右・向かいを座標として読む必要がある。EDA047でも座席表は再実行時に空contentで安定しなかった。 | 座席表画像をVisionで再試行し、成功時の結果を保持したうえで、人名・EXT・x/y座標の表に変換する。PPTX shape座標から座席表を復元できるかも確認する。 |
|      46 | fallback_bm25_llm      | contract_alias_contact_lookup       | 着手金が最も高い案件について、その案件のESの内線番号を教えてください。                                                                                                          | cross_project_structured_aggregation | 複数案件の契約書、社内管理基準、計画表、担当者情報を横断して正規化する必要がある。検索文脈では比較対象の全件性が保証できない。          | 全案件の契約条件・略称・金額・担当者・工数を1つの正規化テーブルにし、質問ごとに集計式を実行する。                                   |
|      49 | document_whole_context | meeting_action_status_lookup        | 東都人材プラットフォームの会議録において、コメントがついている部分をそのまま抽出してください。                                                                                               | meeting_action_structure             | PDF/Word会議録の本文検索だけでは、会議ID、ページ、アクションID、コメント、完了状態の対応が構造化されていない。            | 会議録/報告資料をページ単位・表単位で再抽出し、meeting_id、date、page、action_id、status、comment_textを持つ台帳を作る。 |
|      52 | fallback_bm25_llm      | proposal_operation_clause_lookup    | 蒼樹会 みなみ野女性医療センターの今後の運用に関する記載の中で、データアステル側の役割として「別契約」と明記されているものを抽出してください。                                                                       | pptx_table_or_clause_lookup          | PowerPoint内の表・図形テキストの読み順や略称解決が弱く、該当するスケジュール/条項をピンポイントで拾えていない。            | PPTX shapeの座標、表セル、スライド番号を保持した検索レコードを作り、略称から対象ファイルを絞る。                               |
|      58 | fallback_bm25_llm      | seating_chart_spatial_ocr           | 社内管理フォルダにあるFMにおいて、井上さんの向かいに座っている方のEXTを教えてください。                                                                                                | spatial_image                        | 座席表画像の人名/EXTだけでなく、左右・向かいを座標として読む必要がある。EDA047でも座席表は再実行時に空contentで安定しなかった。 | 座席表画像をVisionで再試行し、成功時の結果を保持したうえで、人名・EXT・x/y座標の表に変換する。PPTX shape座標から座席表を復元できるかも確認する。 |
|      62 | diff_check             | structured_diff_semantic_filter     | 青葉与信マネジメントの最終報告資料における、モデル比較で上位2件のスコア差を生んでいる設定差分は何ですか。                                                                                         | semantic_diff                        | 文字列差分は取れているが、案件遂行に関連する変更だけを抽出する意味フィルタが弱い。Excel差分では状態変更の除外条件も必要。          | old/newをスライド・シート・セクション単位で対応付け、数値/期日/体制/条件/モデル設定だけを差分候補としてLLMに渡す。                    |
|      75 | fallback_bm25_llm      | proposal_operation_clause_lookup    | MINAMINOのPP内のPL案において、モデル構築は第何週に実施することになっていますか。                                                                                                | pptx_table_or_clause_lookup          | PowerPoint内の表・図形テキストの読み順や略称解決が弱く、該当するスケジュール/条項をピンポイントで拾えていない。            | PPTX shapeの座標、表セル、スライド番号を保持した検索レコードを作り、略称から対象ファイルを絞る。                               |
|      79 | fallback_bm25_llm      | cross_project_contract_aggregation  | 恒一会 かえで総合病院の計画フォルダ内において、データアステル側の担当者のうち、1タスク当たりの想定工数(想定工数 ÷ 担当タスク数)が最も大きい人のフルネームと、その1タスク当たりの想定工数を小数第2位で答えてください。ファイルに鍵がかかっている場合は社内管理を確認してください。 | cross_project_structured_aggregation | 複数案件の契約書、社内管理基準、計画表、担当者情報を横断して正規化する必要がある。検索文脈では比較対象の全件性が保証できない。          | 全案件の契約条件・略称・金額・担当者・工数を1つの正規化テーブルにし、質問ごとに集計式を実行する。                                   |
|      80 | format_extraction      | spreadsheet_format_semantic_context | 東都人材プラットフォームのtrain.xlsxにおいて、Sheet2の黄色にハイライトされたセルの抽出条件と集計内容を答えてください。                                                                           | spreadsheet_format_semantics         | セル色は抽出済みでも、その色が何の条件・集計を意味するかが表構造と結びついていない。                               | openpyxlで色付きセルの座標、周辺見出し、同じ行/列の値、数式をまとめ、条件候補をローカルで推定する。                              |
|      83 | table_calculation      | model_formula_recompute             | 蒼樹会 みなみ野女性医療センターのtrain.xlsxにおいて、回帰分析の結果として記載されている係数をindex=1770のデータに当てはめたときの予測値はいくつですか。小数第5位まで答えてください。                                         | model_formula_recompute              | 係数表、標準化表、対象行、閾値探索を正しく接続する必要があり、文脈LLMだけでは計算式が確定しない。                       | Excelの回帰分析シート、標準化シート、trainシートを直接読み、係数名と対象列を対応させてPythonで再計算する。                       |
|      93 | fallback_bm25_llm      | meeting_action_status_lookup        | 蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。                                                                                                 | meeting_action_structure             | PDF/Word会議録の本文検索だけでは、会議ID、ページ、アクションID、コメント、完了状態の対応が構造化されていない。            | 会議録/報告資料をページ単位・表単位で再抽出し、meeting_id、date、page、action_id、status、comment_textを持つ台帳を作る。 |
|      95 | diff_check             | structured_diff_semantic_filter     | 青嶺不動産アセットマネジメントのスケジュール_r1.xlsxとスケジュール_r2.xlsxを比較したとき、未着手から完了への変更を除いて、案件遂行に関連する変更点を挙げてください。                                                    | semantic_diff                        | 文字列差分は取れているが、案件遂行に関連する変更だけを抽出する意味フィルタが弱い。Excel差分では状態変更の除外条件も必要。          | old/newをスライド・シート・セクション単位で対応付け、数値/期日/体制/条件/モデル設定だけを差分候補としてLLMに渡す。                    |
|      96 | fallback_bm25_llm      | meeting_action_status_lookup        | 青葉与信マネジメントのチェックポイント2として設定されている内容に関連するタスクIDを教えてください。                                                                                           | meeting_action_structure             | PDF/Word会議録の本文検索だけでは、会議ID、ページ、アクションID、コメント、完了状態の対応が構造化されていない。            | 会議録/報告資料をページ単位・表単位で再抽出し、meeting_id、date、page、action_id、status、comment_textを持つ台帳を作る。 |

## 考察

個別routeを作っても残った理由は、LLMの回答能力よりも、LLMへ渡す前の根拠候補がまだ計算可能・比較可能な形になっていないことが大きい。
特に、会議録/アクションID、座席表、横断契約集計、回帰係数再計算は、Markdown検索ではなく専用の構造化テーブルを先に作る必要がある。

EDA047の再実行で画像説明は5件まで増えたが、座席表はまだ安定して読めていない。
座席表質問はVisionの文章説明だけでなく、PPTX shape座標または画像からの座標テーブル化が必要。

## 次にやるべきこと

1. EDA049: 会議録/アクションID台帳を作る。
2. EDA050: 座席表を人名、EXT、POD、x/y座標のテーブルにする。
3. EDA051: 全案件の契約条件、金額、略称、担当者、工数を正規化した横断テーブルを作る。
4. EDA052: Excelの色付きセルと周辺見出し、数式、集計対象を結びつける。
5. EDA053: 回帰係数、標準化、対象行、閾値探索をローカルで再計算する。
6. EDA054: old/new差分をスライド、シート、セクション単位で対応付け、案件遂行に関係する差分だけを抽出する。
