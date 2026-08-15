# EDA005: 統合BM25検索とテンプレ回答による提出候補作成

## 目的・背景

EDA003ではEDA002由来チャンクだけを使った検索ベースラインを作成し、EDA004ではOffice文書とPDFの抽出対象を広げました。次の段階として、EDA002とEDA004の検索用チャンクを統合し、test質問100件に対する提出候補を作成します。

本来は検索した根拠をLLMへ渡して回答生成する構成が自然ですが、今回の初回提出候補ではLLM APIやローカルLLMを使いません。理由は、外部送信なしで提出形式、全問処理、検索ログ、回答ログの再現性を先に確認するためです。また、このPCにOllamaが未導入であり、OpenRouterなどの外部API利用は今後検討段階のため、まずはBM25検索とルール/テンプレ回答で安全に一周させます。

このEDA005はスコア最大化ではなく、提出パイプラインの動作確認を主目的とします。

## 手法

- 入力チャンク: `EDA002/texts/text_chunks.jsonl` と `EDA004/texts/text_chunks.jsonl`
- 検索方式: 簡易BM25
- 検索上位件数: Top 10
- 回答生成: 上位チャンク内で質問語と重なる行を選ぶテンプレ方式
- 低スコア閾値: 25.0
- 画像、差分、書式などテンプレ回答が危険な質問は `わかりません` を返す

## 全体サマリ

- 統合チャンク数: 2541
- valid質問数: 30
- test質問数: 100
- validでテンプレ回答が正解全文を含んだ割合: 0.0667
- 提出候補CSV: `EDA/EDA005/submission/predictions.csv`
- 提出候補zip: `EDA/EDA005/submission/eda005_bm25_template_submission.zip`
- SIGNATEお試し提出スコア: -0.7666666666666667

## チャンク内訳

| source_eda | chunk_count |
| --- | --- |
| EDA004 | 1311 |
| EDA002 | 1230 |

凡例: `source_eda` はチャンクの由来、`chunk_count` は統合検索に使ったチャンク数を表します。

| extension | chunk_count |
| --- | --- |
| .xlsx | 629 |
| .py | 514 |
| .docx | 457 |
| .ipynb | 325 |
| .csv | 250 |
| .pptx | 149 |
| .json | 88 |
| .pdf | 76 |
| .md | 53 |

凡例: `extension` は元ファイルの拡張子、`chunk_count` はその拡張子由来のチャンク数を表します。

## test回答生成理由

| generation_reason | test_count |
| --- | --- |
| template_line_overlap | 71 |
| unsupported_question_type | 29 |

凡例: `generation_reason` はテンプレ回答の生成理由、`test_count` はtest質問内の件数を表します。

## test質問タイプ

| question_tags | test_count |
| --- | --- |
| 検索 | 48 |
| 計算 | 12 |
| 差分 | 8 |
| 書式, 表 | 8 |
| 書式 | 7 |
| 表 | 6 |
| コード | 3 |
| 計算, 書式, 表 | 2 |
| 画像 | 2 |
| 計算, 表 | 2 |
| 画像, 表 | 1 |
| 差分, 表 | 1 |

凡例: `question_tags` は質問文から推定した処理タイプ、`test_count` はtest質問内の件数を表します。

## valid回答サンプル

| index | question | true_answer | answer | generation_reason | top1_relative_path |
| --- | --- | --- | --- | --- | --- |
| 0 | 青潮モビリティサービスの最終報告における、モビリティ需要の要因分析のページで、マーカーされている単語をすべて抜き出してください。 | hr、weekday、weathersit、temp | わかりません | unsupported_question_type | プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx |
| 1 | KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。 | 20日 | わかりません | unsupported_question_type | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx |
| 2 | 恒一会 かえで総合病院の提案書内で、重視するとされている評価指標を答えてください。 | Recall | 提出先：医療法人社団 恒一会 かえで総合病院様 | template_line_overlap | プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx |
| 3 | 全案件で支払った税込金額をもとに、消費税額の総額を計算してください。 | 4,394,250円 | 1. 目的 | template_line_overlap | 社内管理/データアステル社内管理_決裁基準.md |
| 4 | 青嶺不動産アセットマネジメントの modeling.py において、前処理器の sparse_output が False になる model_type は何ですか。 | hist_gradient_boosting | model_type: str, | template_line_overlap | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py |
| 5 | 白峰信用リスク評価の最終報告書において、「プロジェクト目的とスコープ」内でAPI化はどの分類に記載されていますか。 | 対象外（契約明記） | 02 プロジェクト目的とスコープ | template_line_overlap | プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx |
| 6 | 恒一会 かえで総合病院のtrain.xlsx内の PivotTable で集計されている表から、ALPの平均が最も高いものの抽出条件を教えてください。 | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | # XLSXファイル: train.xlsx | template_line_overlap | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.xlsx |
| 7 | 恒一会 かえで総合病院のプロジェクトデータ（train.csv）において、disease=1の女性の中で、ALT_GPTの平均値が最も高い年齢は何歳ですか。 | 32歳 | # CSVファイル: train.csv | template_line_overlap | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv |
| 8 | 蒼泉会 ひがし丘総合病院の契約条件において、仮に実績工数が見込工数の4分の3だった場合、最終請求金額（税込）は見込金額（税込）よりいくら少なくなりますか。 | 1,168,750円 | 金額（税込）：4,675,000円 | template_line_overlap | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx |
| 9 | 青嶺不動産アセットマネジメントの提案書について、oldフォルダ内の旧版と提案フォルダ直下の最新版を比較し、変更された箇所を変更前と変更後で答えてください。 | QAレビューア：池田 直哉 → 小林 直樹 | わかりません | unsupported_question_type | プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/old/提案書.pptx |
| 10 | 蒼樹会 みなみ野女性医療センターの最終報告書にて、影響度が最も高いとされている残余リスクを抜き出してください。 | 0値の疑似欠損 | # PDFファイル: 医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf | template_line_overlap | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx |
| 11 | 東都人材プラットフォームのtrain.xlsxにおいて、trainシートでフィルターで抽出されている条件を教えてください。 | Gender=Male、Country=India、target=2 | # XLSXファイル: train.xlsx | template_line_overlap | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx |
| 12 | 京橋信用ソリューションズの契約金額（税込）はいくらですか。 | 5,775,000円 | 契約金額（税抜）：5,250,000円 - 消費税額：525,000円 - 契約金額（税込）：5,775,000円 | template_line_overlap | プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx |
| 13 | 青葉与信マネジメントの分析対象データにおいて、term=3 years、grade=B1、purpose=credit_cardに該当するloan_amntの平均を算出してください。四捨五入して整数値で出してください。 | 1526 | id,loan_amnt,term,interest_rate,grade,employment_length,purpose,credit_score,application_type,loan_status | template_line_overlap | プロジェクト/青葉与信マネジメント株式会社/03.データ/train.csv |
| 14 | 青葉バイオメディカル機器案件において、鈴木 美咲さんはどの役割としてアサインされていますか。 | アサインされていない | 0.4667 | template_line_overlap | プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx |

## 注意点

- この提出候補はLLMを使わないため、文章読解や複数資料照合はかなり弱いです。
- 計算、画像、差分、細かな書式抽出は今後の専用処理で改善する前提です。
- `わかりません` が多くても、まず提出形式と再実行可能な生成手順を確認する目的です。
- SIGNATEへの提出はこのスクリプトでは行っていません。提出結果として、`eda005_bm25_template_submission.zip` は -0.7666666666666667 でした。

## 次にやること

1. validで検索上位に正解根拠があるがテンプレ回答が外れている問題を確認する。
2. CSV/XLSXの計算問題をpandas/openpyxlで直接処理するルールを追加する。
3. OpenRouterやOllamaを使う場合は、回答生成部分だけ差し替え、モデル名とプロンプトをログに保存する。
