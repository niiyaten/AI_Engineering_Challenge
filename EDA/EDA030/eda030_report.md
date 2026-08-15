# EDA030: 表計算ルーターの分類と実計算

## 背景と目的

EDA029では、EDA024のvalid誤答・不明の主因として、表データの検索後に計算できていないケースが目立つことが分かった。
EDA030では、valid内の `route=table_calculation` 7件を対象に、質問を汎用的な計算サブタイプへ分類し、実際にpandas/openpyxlで計算した。

今回の目的は、LLMに表や文書を丸ごと読ませる前に、ローカル処理で確定できる計算を切り出せるかを確認することです。
そのため、validのgoldはプロンプトや計算処理には使わず、計算後の照合だけに使っています。

## 実施内容

1. `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv` から `route=table_calculation` の7件を抽出した。
2. 質問文から、表計算のサブタイプを付与した。
3. CSV/XLSXの元データは `data/raw/share`、文書横断の金額根拠は `data/processed/share` を参照した。
4. pandas/openpyxlで実計算し、計算回答とgoldを照合した。

触った主なデータは以下です。

- `data/raw/share/.../医療法人社団 恒一会 かえで総合病院/03.データ/train.csv`
- `data/raw/share/.../医療法人社団 恒一会 かえで総合病院/03.データ/train.xlsx`
- `data/raw/share/.../株式会社東都人材プラットフォーム/03.データ/train.xlsx`
- `data/raw/share/.../青葉与信マネジメント株式会社/03.データ/train.csv`
- `data/raw/share/.../株式会社青葉バイオメディカル機器/03.データ/train.csv`
- `data/processed/share/share/共有ドライブ/プロジェクト/*/06.報告書/*.md`
- `data/processed/share/share/共有ドライブ/プロジェクト/*/01.契約/*.md`

## 結果

- 対象: 7件
- goldと一致または包含一致: 6件
- 要確認: 1件

`index=3` の消費税総額は、文書から再構成した計算値が `4,384,250円` となり、valid goldの `4,394,250円` と10,000円差が出た。
10案件の税額候補を文書から突き合わせてもgoldに一致する組み合わせは見つからなかったため、ここはPDF抽出漏れ、文書側の表現差、またはgold側の要確認差分として扱う。

## 質問別の計算結果

凡例: `index` はvalid質問番号、`implemented_subtype` は実行した計算処理の種類、`predicted_answer` はローカル計算で得た回答、`gold_answer` はvalid正解、`answer_match` は表記ゆれを少しならした一致判定、`needs_review` は人手確認が必要なもの、`source_paths` は参照した主な根拠ファイルを表します。

|   index | implemented_subtype           | predicted_answer                                                                       | gold_answer                                                                            | answer_match   | needs_review   | source_paths                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|--------:|:------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------|:---------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|       3 | cross_project_tax_sum         | 4,384,250円                                                                             | 4,394,250円                                                                             | False          | True           | data\processed\share\share\共有ドライブ\プロジェクト\京橋信用ソリューションズ株式会社\06.報告書\京橋信用ソリューションズ株式会社_最終報告.pptx.md<br>data\processed\share\share\共有ドライブ\プロジェクト\医療法人社団 恒一会 かえで総合病院\06.報告書\医療法人社団 恒一会 かえで総合病院_最終報告.pptx.md<br>data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/01.契約/契約書.docx.md<br>data\processed\share\share\共有ドライブ\プロジェクト\医療法人社団 蒼泉会 ひがし丘総合病院\06.報告書\医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf.md<br>data\processed\share\share\共有ドライブ\プロジェクト\株式会社東都人材プラットフォーム\06.報告書\株式会社東都人材プラットフォーム_最終報告.pptx.md<br>data\processed\share\share\共有ドライブ\プロジェクト\株式会社青嶺不動産アセットマネジメント\06.報告書\株式会社青嶺不動産アセットマネジメント_最終報告.pptx.md<br>data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/01.契約/契約書.docx.md<br>data\processed\share\share\共有ドライブ\プロジェクト\株式会社青葉バイオメディカル機器\06.報告書\株式会社青葉バイオメディカル機器_最終報告.pptx.md<br>data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/01.契約/契約書.docx.md<br>data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/01.契約/契約書.docx.md |
|       6 | pivot_or_groupby_max_mean     | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP                                      | True           | False          | data\raw\share\share\共有ドライブ\プロジェクト\医療法人社団 恒一会 かえで総合病院\03.データ\train.csv                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|       7 | filter_groupby_max_mean       | 32歳                                                                                    | 32歳                                                                                    | True           | False          | data\raw\share\share\共有ドライブ\プロジェクト\医療法人社団 恒一会 かえで総合病院\03.データ\train.csv                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|      11 | excel_filter_state_extraction | Gender=Male、Country=India、target=2                                                     | Gender=Male、Country=India、target=2                                                     | True           | False          | data\raw\share\share\共有ドライブ\プロジェクト\株式会社東都人材プラットフォーム\03.データ\train.xlsx                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|      13 | filter_aggregate_mean         | 1526                                                                                   | 1526                                                                                   | True           | False          | data\raw\share\share\共有ドライブ\プロジェクト\青葉与信マネジメント株式会社\03.データ\train.csv                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|      21 | pivot_or_groupby_max_mean     | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | True           | False          | data\raw\share\share\共有ドライブ\プロジェクト\株式会社青葉バイオメディカル機器\03.データ\train.csv                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|      26 | filter_mean_nearest_ids       | train_0077、train_0216、train_0242、train_0722                                            | train_0077、train_0216、train_0242、train_0722                                            | True           | False          | data\raw\share\share\共有ドライブ\プロジェクト\株式会社青葉バイオメディカル機器\03.データ\train.csv                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

## 質問別の処理内容

凡例: `question` はvalid質問文、`detail` は実際に行ったフィルター、集計、抽出処理を表します。

|   index | question                                                                                                                          | detail                                                                                   |
|--------:|:----------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------|
|       3 | 全案件で支払った税込金額をもとに、消費税額の総額を計算してください。                                                                                                | 10案件の消費税額を合計。計算値=4,384,250円。valid goldとは10,000円差があり、PDF抽出または正解側の要確認差分として記録。              |
|       6 | 恒一会 かえで総合病院のtrain.xlsx内の PivotTable で集計されている表から、ALPの平均が最も高いものの抽出条件を教えてください。                                                       | Gender,disease,AgeでALP平均を集計し、最大値=873.697898の組み合わせを取得。                                    |
|       7 | 恒一会 かえで総合病院のプロジェクトデータ（train.csv）において、disease=1の女性の中で、ALT_GPTの平均値が最も高い年齢は何歳ですか。                                                    | disease=1かつGender=Femaleで217行に絞り、Age別ALT_GPT平均の最大値=250.500039を取得。                        |
|      11 | 東都人材プラットフォームのtrain.xlsxにおいて、trainシートでフィルターで抽出されている条件を教えてください。                                                                     | trainシートのAutoFilter ref=A1:J11530から3条件を抽出。                                               |
|      13 | 青葉与信マネジメントの分析対象データにおいて、term=3 years、grade=B1、purpose=credit_cardに該当するloan_amntの平均を算出してください。四捨五入して整数値で出してください。                     | 条件一致141行のloan_amnt平均=1526.404170を四捨五入。                                                   |
|      21 | 青葉バイオメディカル機器のtrain.xlsxのPivotシートにおいて、平均月収が最も高い層の抽出条件を答えてください。                                                                     | Attrition,Gender,MaritalStatus,EducationFieldでMonthlyIncome平均を集計し、最大値=17328.000000の組を取得。 |
|      26 | 青葉バイオメディカル機器のtrain.csvにおいて、EducationFieldがMarketingかつMonthlyIncomeが10000より大きいデータを抽出し、Ageの平均値を計算してください。その平均値に最も近い年齢のidをすべて答えてください。 | 条件一致13行のAge平均=46.230769。最小距離=0.230769のidを抽出。                                             |

## サブタイプ別件数

凡例: `subtype` は質問から判定した計算処理の種類、`count` は該当したvalid質問数を表す。

| implemented_subtype           |   count |   answer_match_count |   needs_review_count |
|:------------------------------|--------:|---------------------:|---------------------:|
| pivot_or_groupby_max_mean     |       2 |                    2 |                    0 |
| cross_project_tax_sum         |       1 |                    0 |                    1 |
| excel_filter_state_extraction |       1 |                    1 |                    0 |
| filter_aggregate_mean         |       1 |                    1 |                    0 |
| filter_groupby_max_mean       |       1 |                    1 |                    0 |
| filter_mean_nearest_ids       |       1 |                    1 |                    0 |

## 生成物

- `tables/table_valid_calculation_results.csv`: valid表計算7件の計算結果とgold照合
- `tables/table_subtype_summary.csv`: サブタイプ別件数
- `tables/table_calculation_case_plan.csv`: 質問ごとの処理計画
- `tables/cross_project_tax_details.csv`: 全案件消費税集計の内訳

## 次の方針

RAG本体では、検索で表ファイルや表由来Markdownを上位に出すだけでなく、質問が計算型なら以下の順に処理する。

1. 質問文から対象案件、ファイル種別、列名、条件、集計関数を抽出する。
2. CSV/XLSXはLLMへ丸投げせず、pandas/openpyxlで計算する。
3. 計算結果と根拠行数、集計軸、対象ファイルをLLMへ渡し、最終回答の表記だけを整える。
4. 文書横断の金額集計は、最終報告、契約書、提案書の優先順位を明示し、重複・old版を除外する。
