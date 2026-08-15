# EDA006: validを用いたLLM導入前RAG診断

## 目的・背景

EDA005では、EDA002とEDA004の検索用チャンクを統合し、BM25検索とテンプレ回答で提出候補を作成しました。提出形式は確認できましたが、スコアは低く、回答品質を改善するには検索・抽出・表計算・書式・画像・差分のどこが不足しているかを切り分ける必要があります。

EDA006では、valid 30問を使って、将来LLMに渡す前のRAGパイプラインを診断します。ここでvalid正解を見る目的は、個別回答をハードコードすることではなく、検索TopKに必要な根拠が入っているか、LLMに渡せる文脈になっているか、どの汎用処理を追加すべきかを評価することです。

## 手法

- EDA002とEDA004の検索用チャンクを統合する
- valid質問ごとにBM25でTop 10を取得する
- valid正解語句がTop5/Top10に含まれるかを簡易照合する
- 質問文から必要能力を分類する
- `ready_for_llm` または不足カテゴリに分類し、次アクションを決める

## 全体サマリ

- valid質問数: 30
- ready_for_llm件数: 10
- answer_hit_top5率: 0.3333
- answer_hit_top10率: 0.3667

## LLM文脈品質の分類

| context_quality_for_llm | question_count |
| --- | --- |
| ready_for_llm | 10 |
| needs_table_tool | 8 |
| needs_better_retrieval | 8 |
| needs_format_extraction | 2 |
| needs_image_ocr | 1 |
| needs_diff_tool | 1 |

凡例: `context_quality_for_llm` はLLMへ渡す前の文脈品質、`question_count` はvalid内の件数を表します。

## 必要能力の分類

| required_capability | question_count |
| --- | --- |
| document_qa | 16 |
| table_tool | 7 |
| format_extraction | 2 |
| code_reading | 2 |
| table_tool, image_ocr | 1 |
| diff_tool, document_qa | 1 |
| table_tool, document_qa | 1 |

凡例: `required_capability` は質問に答えるために必要そうな汎用能力、`question_count` はvalid内の件数を表します。

## 次アクション優先度

| recommended_next_step | context_quality_for_llm | question_count | answer_hit_top5_rate | mean_top1_score |
| --- | --- | --- | --- | --- |
| LLM向けMarkdownコンテキストを作る | ready_for_llm | 10 | 1.0 | 222.3693 |
| CSV/XLSXをpandas/openpyxlで直接処理する | needs_table_tool | 8 | 0.0 | 286.8441 |
| 抽出対象と検索重みを見直す | needs_better_retrieval | 8 | 0.0 | 229.5783 |
| Word/PPTの書式メタ情報をRAG向けに正規化する | needs_format_extraction | 2 | 0.0 | 142.4655 |
| OCRまたは画像理解の抽出器を追加する | needs_image_ocr | 1 | 0.0 | 139.5378 |
| ファイル差分をスライド・段落単位で比較する | needs_diff_tool | 1 | 0.0 | 155.5413 |

凡例: `recommended_next_step` は次に作るべき汎用処理、`answer_hit_top5_rate` は該当グループでTop5に正解語句が含まれた割合、`mean_top1_score` は検索Top1スコア平均を表します。

## valid診断サンプル

| index | question | answer | required_capability | context_quality_for_llm | answer_hit_top5 | top1_relative_path | recommended_next_step |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 青潮モビリティサービスの最終報告における、モビリティ需要の要因分析のページで、マーカーされている単語をすべて抜き出してください。 | hr、weekday、weathersit、temp | format_extraction | needs_format_extraction | False | プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx | Word/PPTの書式メタ情報をRAG向けに正規化する |
| 1 | KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。 | 20日 | table_tool, image_ocr | needs_image_ocr | False | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx | OCRまたは画像理解の抽出器を追加する |
| 2 | 恒一会 かえで総合病院の提案書内で、重視するとされている評価指標を答えてください。 | Recall | document_qa | ready_for_llm | True | プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx | LLM向けMarkdownコンテキストを作る |
| 3 | 全案件で支払った税込金額をもとに、消費税額の総額を計算してください。 | 4,394,250円 | table_tool | needs_table_tool | False | 社内管理/データアステル社内管理_決裁基準.md | CSV/XLSXをpandas/openpyxlで直接処理する |
| 4 | 青嶺不動産アセットマネジメントの modeling.py において、前処理器の sparse_output が False になる model_type は何ですか。 | hist_gradient_boosting | code_reading | ready_for_llm | True | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py | LLM向けMarkdownコンテキストを作る |
| 5 | 白峰信用リスク評価の最終報告書において、「プロジェクト目的とスコープ」内でAPI化はどの分類に記載されていますか。 | 対象外（契約明記） | document_qa | ready_for_llm | True | プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx | LLM向けMarkdownコンテキストを作る |
| 6 | 恒一会 かえで総合病院のtrain.xlsx内の PivotTable で集計されている表から、ALPの平均が最も高いものの抽出条件を教えてください。 | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | table_tool | needs_table_tool | False | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.xlsx | CSV/XLSXをpandas/openpyxlで直接処理する |
| 7 | 恒一会 かえで総合病院のプロジェクトデータ（train.csv）において、disease=1の女性の中で、ALT_GPTの平均値が最も高い年齢は何歳ですか。 | 32歳 | table_tool | needs_table_tool | False | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv | CSV/XLSXをpandas/openpyxlで直接処理する |
| 8 | 蒼泉会 ひがし丘総合病院の契約条件において、仮に実績工数が見込工数の4分の3だった場合、最終請求金額（税込）は見込金額（税込）よりいくら少なくなりますか。 | 1,168,750円 | document_qa | needs_better_retrieval | False | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx | 抽出対象と検索重みを見直す |
| 9 | 青嶺不動産アセットマネジメントの提案書について、oldフォルダ内の旧版と提案フォルダ直下の最新版を比較し、変更された箇所を変更前と変更後で答えてください。 | QAレビューア：池田 直哉 → 小林 直樹 | diff_tool, document_qa | needs_diff_tool | False | プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/old/提案書.pptx | ファイル差分をスライド・段落単位で比較する |
| 10 | 蒼樹会 みなみ野女性医療センターの最終報告書にて、影響度が最も高いとされている残余リスクを抜き出してください。 | 0値の疑似欠損 | table_tool, document_qa | needs_table_tool | False | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx | CSV/XLSXをpandas/openpyxlで直接処理する |
| 11 | 東都人材プラットフォームのtrain.xlsxにおいて、trainシートでフィルターで抽出されている条件を教えてください。 | Gender=Male、Country=India、target=2 | table_tool | needs_table_tool | False | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx | CSV/XLSXをpandas/openpyxlで直接処理する |
| 12 | 京橋信用ソリューションズの契約金額（税込）はいくらですか。 | 5,775,000円 | document_qa | ready_for_llm | True | プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx | LLM向けMarkdownコンテキストを作る |
| 13 | 青葉与信マネジメントの分析対象データにおいて、term=3 years、grade=B1、purpose=credit_cardに該当するloan_amntの平均を算出してください。四捨五入して整数値で出してください。 | 1526 | table_tool | needs_table_tool | False | プロジェクト/青葉与信マネジメント株式会社/03.データ/train.csv | CSV/XLSXをpandas/openpyxlで直接処理する |
| 14 | 青葉バイオメディカル機器案件において、鈴木 美咲さんはどの役割としてアサインされていますか。 | アサインされていない | document_qa | needs_better_retrieval | False | プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx | 抽出対象と検索重みを見直す |
| 15 | 中間報告会または中間レビューが2025年7月1日以前に実施された案件を、主略称ですべて挙げてください。 | MINAMINO、SHR、AYM | document_qa | needs_better_retrieval | False | プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx | 抽出対象と検索重みを見直す |
| 16 | MINAMINOのPLにおいて、M01当日を1日目として数えた場合、M01の日からFR実施までの日数は何日ですか。 | 43日 | document_qa | needs_better_retrieval | False | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx | 抽出対象と検索重みを見直す |
| 17 | 京橋信用ソリューションズのカラム説明において、カラム名pdaysの値-1は何を表していますか。 | 未連絡 | document_qa | ready_for_llm | True | プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md | LLM向けMarkdownコンテキストを作る |
| 18 | 東都のCTにおいて、全14章のうち「本業務の対象データ、前提および制約」が記載されている章番号を数字で答えてください。 | 3 | document_qa | ready_for_llm | True | プロジェクト/株式会社東都人材プラットフォーム/01.契約/契約書.docx | LLM向けMarkdownコンテキストを作る |
| 19 | 青嶺不動産アセットマネジメント案件で分析設計を担当する人の名前をフルネームで抽出してください。 | 渡辺 遥 | document_qa | ready_for_llm | True | プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-26.pdf | LLM向けMarkdownコンテキストを作る |
| 20 | AYMのPLにおいて、探索的分析・仮説整理フェーズに一致するタスクIDをすべて挙げてください。 | T09、T10、T11、T12 | document_qa | ready_for_llm | True | プロジェクト/青葉与信マネジメント株式会社/02.計画/スケジュール.xlsx | LLM向けMarkdownコンテキストを作る |
| 21 | 青葉バイオメディカル機器のtrain.xlsxのPivotシートにおいて、平均月収が最も高い層の抽出条件を答えてください。 | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | table_tool | needs_table_tool | False | プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.xlsx | CSV/XLSXをpandas/openpyxlで直接処理する |
| 22 | AOSHIOの NB01_eda.ipynbにおいて、観察結果サマリで出力されている「TGとの相関 上位5」の中で、相関係数が最も小さいカラム名を答えてください。 | season | document_qa | ready_for_llm | True | プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb | LLM向けMarkdownコンテキストを作る |
| 23 | AOSHIOのM02資料（docx）において、黄色でハイライトされている部分をすべて抜き出してください。 | 見込金額（税込）: 4,675,000 JPY | format_extraction | needs_format_extraction | False | プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx | Word/PPTの書式メタ情報をRAG向けに正規化する |
| 24 | 白峰信用リスク評価の 01_eda.ipynb にある特徴量相関ヒートマップの図で可視化されている特徴量のうち、classとの相関係数の絶対値が最も小さい特徴量名を答えてください。 | Attr7 | document_qa | needs_better_retrieval | False | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | 抽出対象と検索重みを見直す |
| 25 | 東都人材プラットフォームの提案書P7において、赤で強調されている箇所の文字列を抜き出してください。 | 1. データ理解・EDA | document_qa | needs_better_retrieval | False | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx | 抽出対象と検索重みを見直す |
| 26 | 青葉バイオメディカル機器のtrain.csvにおいて、EducationFieldがMarketingかつMonthlyIncomeが10000より大きいデータを抽出し、Ageの平均値を計算してください。その平均値に最も近い年齢のidをすべて答えてください。 | train_0077、train_0216、train_0242、train_0722 | table_tool | needs_table_tool | False | プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.csv | CSV/XLSXをpandas/openpyxlで直接処理する |
| 27 | 蒼泉会 ひがし丘総合病院案件において、中間報告資料に記載されたMacro F1スコアの詳細値と、最終分析出力metrics.jsonに記録されているMacro F1スコアの詳細値を用いて、改善幅を小数第6位まで答えてください。 | 0.010301 | document_qa | needs_better_retrieval | False | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_outputs/metrics.json | 抽出対象と検索重みを見直す |
| 28 | 蒼泉会の分析コードにおいて、CATは dtype とユニーク数の条件でどのように判定していますか。 | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 | code_reading | needs_better_retrieval | False | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx | 抽出対象と検索重みを見直す |
| 29 | 蒼樹会 みなみ野女性医療センターの契約書第8条において、本契約終了後に秘密保持義務が存続する期間は何年間ですか。 | 3年間 | document_qa | ready_for_llm | True | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/01.契約/契約書.docx | LLM向けMarkdownコンテキストを作る |

## 考察

`ready_for_llm` は、検索Top5に正解語句が含まれており、次にLLM向けMarkdownコンテキストを整形すれば改善しやすい候補です。一方で、画像、差分、書式、表計算が必要な問題は、LLMだけを追加しても根拠不足や誤答になりやすいため、専用の抽出・計算ツールが必要です。

EDA007では、今回の診断結果をもとに、LLMへ渡す根拠を読みやすくするMarkdownコンテキスト生成を作るのが自然です。ただし、表計算や画像読み取りが多い場合は、それらの専用ツールを先に作る選択肢もあります。