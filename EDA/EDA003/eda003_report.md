# EDA003: EDA002テキストチャンクを用いた検索ベースライン

## 目的・背景

### 背景

EDA002で作成した `.md`, `.csv`, `.json`, `.py`, `.ipynb` 由来のテキストチャンクを使い、valid/test質問に対する検索ベースラインを作成します。

このEDAでは最終回答は生成しません。目的は、回答生成の前段階である「根拠チャンク検索」がどの程度できているかを確認することです。

EDA002では、`.md`, `.csv`, `.json`, `.py`, `.ipynb` を対象に、RAGの初期インデックスへ投入しやすいテキストチャンクを作成した。これにより、Markdown文書、CSVの概要、JSON設定、Pythonコード、Notebookセル由来の情報については、機械的に検索できる状態になった。

一方で、テキスト抽出ができていることと、質問に対して必要な根拠チャンクを検索できることは別問題である。RAGでは、回答生成の前段階で正しい根拠を検索できなければ、LLMに渡す文脈が不足し、最終回答の精度も上がらない。そのため、回答生成に進む前に、まず検索部分だけを切り出して性能と失敗傾向を確認する必要がある。

### 本EDAの目的

EDA003では、EDA002で作成した `text_chunks.jsonl` を用いて、valid質問に対する検索ベースラインを作成する。検索器には外部ライブラリに依存しない簡易BM25を用い、各質問に対して上位10件のチャンクを取得する。

本EDAの主目的は、最終回答を生成することではなく、以下を確認することである。

- EDA002対象形式のチャンクだけで、valid質問の根拠候補をどの程度拾えるか
- Top1 / Top3 / Top5 / Top10 の検索結果に、正解語句が含まれる割合はどの程度か
- `.md`, `.csv`, `.json`, `.py`, `.ipynb` のうち、検索上位に出やすい形式はどれか
- 対象外形式、書式情報、画像、Excelセルなどが必要な質問でどの程度失敗するか
- 次に優先して抽出器を作るべきファイル形式は何か

### 注意点

ここで算出しているヒット率は、valid回答文字列が上位チャンク内に含まれるかを簡易的に見たものであり、SIGNATEの正式評価スコアではない。回答が本文に明示されていない計算問題や、表記揺れが大きい問題では、実際の回答可能性と一致しない場合がある。ただし、検索ベースラインの弱点を把握する指標としては有用である。

## 入力データ

| 項目 | 内容 |
|---|---|
| チャンク入力 | `EDA\EDA002\texts\text_chunks.jsonl` |
| 質問データ | `directory: data\raw\share\share\質問回答` |
| チャンク数 | 1230 |
| valid質問数 | 30 |
| test質問数 | 100 |
| 検索方式 | 簡易BM25（パス・ファイル名・案件名を補助的に重み付け） |
| 検索上位件数 | Top 10 |

## インデックス対象チャンクの拡張子分布

| extension | chunk_count |
|---|---|
| .py | 514 |
| .ipynb | 325 |
| .csv | 250 |
| .json | 88 |
| .md | 53 |

## Valid検索ヒット率

| top_k | loose_hit_count | loose_hit_rate | exact_hit_count | exact_hit_rate | mean_term_coverage |
|---|---|---|---|---|---|
| 1 | 5 | 0.1667 | 4 | 0.1333 | 0.1917 |
| 3 | 5 | 0.1667 | 4 | 0.1333 | 0.1917 |
| 5 | 5 | 0.1667 | 4 | 0.1333 | 0.2133 |
| 10 | 5 | 0.1667 | 4 | 0.1333 | 0.2133 |

## Valid質問の対応しやすさ分類

| support_category | question_count | top5_loose_hit_rate | mean_top1_score |
|---|---|---|---|
| EDA002対象形式で拾える可能性あり | 4 | 0.5 | 207.5197 |
| EDA002対象形式を明示 | 3 | 0.3333 | 478.855 |
| 対象外形式の可能性が高い | 8 | 0.125 | 106.409 |
| 形式不明 | 15 | 0.0667 | 140.8411 |

## Top1検索結果の拡張子分布

| extension | top1_count |
|---|---|
| .md | 15 |
| .ipynb | 6 |
| .py | 4 |
| .csv | 4 |
| .json | 1 |

## Valid検索結果サンプル

| index | question | answer | answer_loose_hit_top5 | answer_term_coverage_top5 | support_category | top1_extension | top1_relative_path | top1_preview |
|---|---|---|---|---|---|---|---|---|
| 0 | 青潮モビリティサービスの最終報告における、モビリティ需要の要因分析のページで、マーカーされている単語をすべて抜き出してください。 | hr、weekday、weathersit、temp | True | 0.8 | 対象外形式の可能性が高い | .md | プロジェクト/株式会社青潮モビリティサービス/03.データ/カラム説明.md | # source_path: プロジェクト/株式会社青潮モビリティサービス/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project_na... |
| 1 | KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。 | 20日 | False | 0.0 | 形式不明 | .ipynb | プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | ax1.plot(agg.index, agg['件数'], marker='o', color='tab:blue') ax1.set_title(f'{used_col} による件数推移') ax1.set_xlabel('日') ax... |
| 2 | 恒一会 かえで総合病院の提案書内で、重視するとされている評価指標を答えてください。 | Recall | False | 0.0 | 対象外形式の可能性が高い | .md | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/カラム説明.md | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project... |
| 3 | 全案件で支払った税込金額をもとに、消費税額の総額を計算してください。 | 4,394,250円 | False | 0.25 | 形式不明 | .md | 社内管理/データアステル社内管理_決裁基準.md | # source_path: 社内管理/データアステル社内管理_決裁基準.md # file_name: データアステル社内管理_決裁基準.md # extension: .md # area: 社内管理 # project_name: #... |
| 4 | 青嶺不動産アセットマネジメントの modeling.py において、前処理器の sparse_output が False になる model_type は何ですか。 | hist_gradient_boosting | True | 1.0 | EDA002対象形式を明示 | .py | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py | # source_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/modeling.py # file_name: modeling.py # extension: .... |
| 5 | 白峰信用リスク評価の最終報告書において、「プロジェクト目的とスコープ」内でAPI化はどの分類に記載されていますか。 | 対象外（契約明記） | False | 0.0 | 対象外形式の可能性が高い | .ipynb | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | > 0 else pd.DataFrame() plt.figure(figsize=(12, 10)) if corr_mat.shape[0] > 0: sns.heatmap(corr_mat, cmap='coolwarm', ce... |
| 6 | 恒一会 かえで総合病院のtrain.xlsx内の PivotTable で集計されている表から、ALPの平均が最も高いものの抽出条件を教えてください。 | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | False | 0.2 | 形式不明 | .csv | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # proj... |
| 7 | 恒一会 かえで総合病院のプロジェクトデータ（train.csv）において、disease=1の女性の中で、ALT_GPTの平均値が最も高い年齢は何歳ですか。 | 32歳 | False | 0.0 | EDA002対象形式を明示 | .csv | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # proj... |
| 8 | 蒼泉会 ひがし丘総合病院の契約条件において、仮に実績工数が見込工数の4分の3だった場合、最終請求金額（税込）は見込金額（税込）よりいくら少なくなりますか。 | 1,168,750円 | False | 0.25 | 形式不明 | .md | 社内管理/データアステル社内管理_決裁基準.md | # source_path: 社内管理/データアステル社内管理_決裁基準.md # file_name: データアステル社内管理_決裁基準.md # extension: .md # area: 社内管理 # project_name: #... |
| 9 | 青嶺不動産アセットマネジメントの提案書について、oldフォルダ内の旧版と提案フォルダ直下の最新版を比較し、変更された箇所を変更前と変更後で答えてください。 | QAレビューア：池田 直哉 → 小林 直樹 | False | 0.0 | 対象外形式の可能性が高い | .py | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py | # source_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py # file_name: __init__.py # extension: .... |

## Top5で正解語句を拾えなかったValid質問

| index | question | answer | support_category | question_needs | mentioned_extensions | top1_score | top1_extension | top1_relative_path | top1_preview |
|---|---|---|---|---|---|---|---|---|---|
| 1 | KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。 | 20日 | 形式不明 | 画像・グラフ, 計算・集計 |  | 131.5014 | .ipynb | プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | ax1.plot(agg.index, agg['件数'], marker='o', color='tab:blue') ax1.set_title(f'{used_col} による件数推移') ax1.set_xlabel('日') ax... |
| 2 | 恒一会 かえで総合病院の提案書内で、重視するとされている評価指標を答えてください。 | Recall | 対象外形式の可能性が高い | 未分類 |  | 84.4762 | .md | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/カラム説明.md | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project... |
| 3 | 全案件で支払った税込金額をもとに、消費税額の総額を計算してください。 | 4,394,250円 | 形式不明 | 計算・集計 |  | 126.2442 | .md | 社内管理/データアステル社内管理_決裁基準.md | # source_path: 社内管理/データアステル社内管理_決裁基準.md # file_name: データアステル社内管理_決裁基準.md # extension: .md # area: 社内管理 # project_name: #... |
| 5 | 白峰信用リスク評価の最終報告書において、「プロジェクト目的とスコープ」内でAPI化はどの分類に記載されていますか。 | 対象外（契約明記） | 対象外形式の可能性が高い | 未分類 |  | 83.6611 | .ipynb | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | > 0 else pd.DataFrame() plt.figure(figsize=(12, 10)) if corr_mat.shape[0] > 0: sns.heatmap(corr_mat, cmap='coolwarm', ce... |
| 6 | 恒一会 かえで総合病院のtrain.xlsx内の PivotTable で集計されている表から、ALPの平均が最も高いものの抽出条件を教えてください。 | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | 形式不明 | 表・セル, コード読解, 計算・集計 |  | 96.3056 | .csv | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # proj... |
| 7 | 恒一会 かえで総合病院のプロジェクトデータ（train.csv）において、disease=1の女性の中で、ALT_GPTの平均値が最も高い年齢は何歳ですか。 | 32歳 | EDA002対象形式を明示 | CSV/JSON読解, 計算・集計 | .csv | 427.5019 | .csv | プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # proj... |
| 8 | 蒼泉会 ひがし丘総合病院の契約条件において、仮に実績工数が見込工数の4分の3だった場合、最終請求金額（税込）は見込金額（税込）よりいくら少なくなりますか。 | 1,168,750円 | 形式不明 | コード読解, 計算・集計 |  | 246.7765 | .md | 社内管理/データアステル社内管理_決裁基準.md | # source_path: 社内管理/データアステル社内管理_決裁基準.md # file_name: データアステル社内管理_決裁基準.md # extension: .md # area: 社内管理 # project_name: #... |
| 9 | 青嶺不動産アセットマネジメントの提案書について、oldフォルダ内の旧版と提案フォルダ直下の最新版を比較し、変更された箇所を変更前と変更後で答えてください。 | QAレビューア：池田 直哉 → 小林 直樹 | 対象外形式の可能性が高い | 差分比較 |  | 125.5969 | .py | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py | # source_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py # file_name: __init__.py # extension: .... |
| 10 | 蒼樹会 みなみ野女性医療センターの最終報告書にて、影響度が最も高いとされている残余リスクを抜き出してください。 | 0値の疑似欠損 | 対象外形式の可能性が高い | 未分類 |  | 141.415 | .md | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/03.データ/カラム説明.md | # source_path: プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # pr... |
| 11 | 東都人材プラットフォームのtrain.xlsxにおいて、trainシートでフィルターで抽出されている条件を教えてください。 | Gender=Male、Country=India、target=2 | 形式不明 | 表・セル, コード読解 |  | 107.75 | .md | プロジェクト/株式会社東都人材プラットフォーム/03.データ/カラム説明.md | # source_path: プロジェクト/株式会社東都人材プラットフォーム/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project_n... |
| 12 | 京橋信用ソリューションズの契約金額（税込）はいくらですか。 | 5,775,000円 | 形式不明 | 計算・集計 |  | 140.1207 | .md | プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md | # source_path: プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project_n... |
| 13 | 青葉与信マネジメントの分析対象データにおいて、term=3 years、grade=B1、purpose=credit_cardに該当するloan_amntの平均を算出してください。四捨五入して整数値で出してください。 | 1526 | 形式不明 | 計算・集計 |  | 295.6973 | .csv | プロジェクト/青葉与信マネジメント株式会社/03.データ/train.csv | # source_path: プロジェクト/青葉与信マネジメント株式会社/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # project_... |
| 14 | 青葉バイオメディカル機器案件において、鈴木 美咲さんはどの役割としてアサインされていますか。 | アサインされていない | 形式不明 | 未分類 |  | 118.342 | .md | プロジェクト/株式会社青葉バイオメディカル機器/03.データ/カラム説明.md | # source_path: プロジェクト/株式会社青葉バイオメディカル機器/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project_n... |
| 15 | 中間報告会または中間レビューが2025年7月1日以前に実施された案件を、主略称ですべて挙げてください。 | MINAMINO、SHR、AYM | 形式不明 | 未分類 |  | 43.5786 | .md | プロジェクト/株式会社青潮モビリティサービス/03.データ/カラム説明.md | # source_path: プロジェクト/株式会社青潮モビリティサービス/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # project_na... |
| 16 | MINAMINOのPLにおいて、M01当日を1日目として数えた場合、M01の日からFR実施までの日数は何日ですか。 | 43日 | 形式不明 | 計算・集計 |  | 47.6834 | .md | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/03.データ/カラム説明.md | # source_path: プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/03.データ/カラム説明.md # file_name: カラム説明.md # extension: .md # area: プロジェクト # pr... |

※先頭15行のみ表示。全25行。

## 考察

EDA002由来のテキストチャンクを使うことで、コード、Notebook、JSON、CSV概要、Markdownに関する質問では、検索候補を一定程度取得できる。特に、質問文に `.py`, `.ipynb`, `.json`, `.csv`, `.md` などのファイル名や拡張子が明示されている場合は、パス情報と本文情報を組み合わせたBM25検索が有効に働きやすい。

一方で、本コンペの質問には、PowerPoint、Word、Excel、PDF、画像、書式情報、セル色、グラフ読み取り、旧版と最新版の差分比較などを必要とするものが多く含まれる。これらはEDA002の対象外であるため、今回の検索ベースラインだけでは根拠チャンクを取得できない。Top5で正解語句を拾えない質問の多くは、検索方式そのものよりも、インデックス対象に必要ファイル形式が含まれていないことが主因である可能性が高い。

また、CSVについてはサマリとサンプルをチャンク化しているため、列名やデータ概要の検索には使えるが、特定条件での行抽出や集計には不十分である。今後は、CSVを単なるテキストチャンクとして扱うだけでなく、質問に応じてpandasで直接検索・集計する処理を組み込む必要がある。

## 次にやるべきこと

1. EDA004では、`.docx`, `.pptx`, `.xlsx`, `.pdf` の本文抽出と、書式・セル色などのメタ情報抽出を扱う。
2. 検索評価では、valid質問を「対象形式で回答可能」「対象外形式が必要」「計算・集計が必要」に分けて確認する。
3. `.csv` と `.xlsx` は、RAGチャンク検索とは別に、表データ検索・集計ツールとして扱う方針を検討する。
4. 差分比較、画像・グラフ読み取り、書式抽出は、通常のテキストRAGとは別系統のAgentツールとして設計する。

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `tables/valid_retrieval_results.csv` | valid質問ごとの検索結果サマリ |
| `tables/valid_top_chunks.csv` | valid質問ごとの上位チャンク一覧 |
| `tables/test_top_chunks.csv` | test質問ごとの上位チャンク一覧 |
| `tables/retrieval_hit_summary.csv` | TopK別の簡易ヒット率 |
| `tables/question_support_summary.csv` | 質問分類別のヒット率 |
| `tables/no_hit_cases.csv` | Top5で正解語句を拾えなかったvalid質問 |
| `figures/01_valid_hit_rates.png` | TopK別ヒット率 |
| `figures/02_top_result_extension_counts.png` | Top1拡張子分布 |
| `figures/03_question_support_categories.png` | 質問分類分布 |
| `figures/04_top1_score_distribution.png` | Top1スコア分布 |
