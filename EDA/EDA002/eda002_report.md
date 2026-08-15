# EDA002: 直接読めるテキスト系ファイルの抽出ベースライン

## 目的・背景

### 背景

本コンペティションでは、架空企業の共有ドライブに蓄積された案件資料を対象に、社内から寄せられる質問へ根拠に基づいて回答するRAGシステムの構築が求められる。対象資料は単一形式ではなく、文書、表、コード、Notebook、画像を含む資料などが混在しているため、最初から全ファイル形式を同じ方法で処理すると、抽出品質や検索ノイズの問題を切り分けにくい。

EDA001では、共有ドライブ全体のファイル構成、案件フォルダ、拡張子の分布、質問データの概要を整理し、本コンペで扱うデータの全体像を確認した。その結果、RAGの初期インデックスを作るうえでは、まず機械的に本文を取り出しやすいファイル形式から処理を始めるのが妥当と判断した。

### 本EDAの目的

EDA002では、比較的そのまま読み取りやすい `.md`, `.csv`, `.json`, `.py`, `.ipynb` を対象に、テキスト抽出のベースラインを作成する。これらはMarkdown文書、表形式データ、設定ファイル、分析コード、分析Notebookに相当し、案件の背景、分析条件、特徴量、評価指標、出力結果などを含む可能性が高い。

本EDAの主目的は、対象ファイルをRAGの初期検索対象として利用できる状態にすることである。具体的には、各ファイルから本文を抽出し、ファイルパス・案件名・大分類フォルダなどのメタ情報を付与したうえで、後続の検索処理で扱いやすいチャンク単位に分割する。

### 確認観点

本EDAでは、単に抽出処理が成功したかだけでなく、抽出後のテキストがRAGに投入しやすい品質になっているかを確認する。確認観点は、抽出失敗の有無、抽出文字数、行数、チャンク数、ファイル形式ごとの偏り、ファイル別のテキスト量ランキング、抽出本文サンプルの妥当性である。

特に `.ipynb` は、実行ログ、表出力、画像のBase64埋め込みによって本文が過剰に肥大化しやすい。また、大容量CSVは全文を単純にチャンク化すると検索インデックスを圧迫し、必要な行や列を探しにくくなる。そのため、本EDAではNotebook出力の上限設定、埋め込み画像Base64の除外、CSVの概要抽出を行い、初期検索に使いやすい軽量なテキスト表現を作る。

### 後続工程での位置づけ

ここで作成する `extracted_documents.jsonl` と `text_chunks.jsonl` は、後続の検索ベースライン、質問に対する候補文書検索、ファイル形式別の追加抽出方針検討に利用する。EDA002の段階では回答生成までは行わず、RAGの土台となるテキスト化処理の安定性と偏りを確認する。

## 入力データ

- 共有ドライブ: `data/raw/share/share/共有ドライブ`
- 対象拡張子: `.csv, .ipynb, .json, .md, .py`
- チャンクサイズ: 1200 文字
- チャンクオーバーラップ: 200 文字
- Notebook出力上限: 1出力あたり 2000 文字
- Notebook出力上限: 1Notebookあたり 50000 文字
- Notebook source上限: 1セルあたり 20000 文字

## 出力ファイル

- `EDA/EDA002/texts/extracted_documents.jsonl`: 1ファイル1レコードの抽出本文
- `EDA/EDA002/texts/text_chunks.jsonl`: 検索インデックス投入用のチャンク
- `data/processed/text_baseline/extracted_documents.jsonl`: 後続処理向けコピー
- `data/processed/text_baseline/text_chunks.jsonl`: 後続処理向けコピー
- `EDA/EDA002/tables/*.csv`: 棚卸し・成功率・プレビュー・エラー・ファイル別ランキング

## 全体サマリ

- 対象ファイル数: 199
- 抽出成功: 199
- 抽出失敗: 0
- 作成チャンク数: 1230
- 抽出テキスト総文字数: 1119595

## 拡張子別の抽出状況

| extension | file_count | total_size_kb | success_count | error_count | success_rate |
|---|---|---|---|---|---|
| .py | 100 | 447.13 | 100 | 0 | 1.0 |
| .md | 31 | 46.28 | 31 | 0 | 1.0 |
| .csv | 29 | 27304.75 | 29 | 0 | 1.0 |
| .json | 28 | 54.4 | 28 | 0 | 1.0 |
| .ipynb | 11 | 13900.199999999999 | 11 | 0 | 1.0 |

## 抽出方法別サマリ

| extension | extraction_method | extracted_files | total_text_length | mean_text_length | total_line_count |
|---|---|---|---|---|---|
| .csv | csv_summary_sample | 18 | 163772 | 9098.4 | 2860 |
| .csv | csv_full | 11 | 57364 | 5214.9 | 734 |
| .ipynb | ipynb_cells_text_limited_outputs | 11 | 311200 | 28290.9 | 8585 |
| .json | json_pretty_text | 28 | 77125 | 2754.5 | 2420 |
| .md | markdown_raw_text | 31 | 45068 | 1453.8 | 1260 |
| .py | python_raw_text | 100 | 465066 | 4650.7 | 12130 |

## チャンク数サマリ

| extension | chunk_count | mean_chunk_length | max_chunk_length |
|---|---|---|---|
| .py | 514 | 1064.7 | 1199 |
| .ipynb | 325 | 1149.0 | 1199 |
| .csv | 250 | 1061.3 | 1200 |
| .json | 88 | 1012.2 | 1199 |
| .md | 53 | 932.9 | 1200 |

## ファイル別テキスト量ランキング

| document_id | extension | relative_path | extraction_method | size_bytes | text_length | line_count | text_length_share |
|---|---|---|---|---|---|---|---|
| doc_fedf164e75a35759 | .ipynb | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 227836 | 35387 | 944 | 0.0316 |
| doc_f8aa3d477d935cb8 | .ipynb | プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 339513 | 35182 | 978 | 0.0314 |
| doc_f7bbe31b3fc35746 | .ipynb | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 449328 | 33718 | 847 | 0.0301 |
| doc_10145cb6808672ad | .ipynb | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 407839 | 33472 | 910 | 0.0299 |
| doc_de03c1e2611d7376 | .ipynb | プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 360775 | 32771 | 878 | 0.0293 |
| doc_c76ce2191c7a7cf9 | .ipynb | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda_old.ipynb | ipynb_cells_text_limited_outputs | 6134637 | 32611 | 907 | 0.0291 |
| doc_e52d8af8e3e09f73 | .ipynb | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 5543913 | 32599 | 907 | 0.0291 |
| doc_c24302a2e2b18332 | .csv | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/data/train.csv | csv_summary_sample | 3718995 | 30092 | 261 | 0.0269 |
| doc_e2f7ed7ede4cfe4f | .csv | プロジェクト/白峰信用リスク評価株式会社/03.データ/train.csv | csv_summary_sample | 3718995 | 30072 | 261 | 0.0269 |
| doc_281f4f8dee33851a | .py | プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/scripts/run_train.py | python_raw_text | 30448 | 30006 | 643 | 0.0268 |
| doc_ef874fff56cacbf8 | .py | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/scripts/run_train.py | python_raw_text | 29966 | 29545 | 636 | 0.0264 |
| doc_fc494cad6b99891d | .py | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/scripts/run_train.py | python_raw_text | 29966 | 29537 | 636 | 0.0264 |
| doc_cecf9c7ef79041bf | .py | プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/scripts/run_train.py | python_raw_text | 29966 | 29535 | 636 | 0.0264 |
| doc_f90e331bf1399a0f | .py | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/scripts/run_train.py | python_raw_text | 29966 | 29531 | 636 | 0.0264 |
| doc_bc9c5d0845ebe443 | .ipynb | プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 485457 | 27653 | 816 | 0.0247 |
| doc_f7950acecd6c9962 | .ipynb | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 250696 | 26566 | 813 | 0.0237 |
| doc_f74251b3e48af6b1 | .ipynb | プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 31047 | 19717 | 534 | 0.0176 |
| doc_22cccbd0e3648b72 | .csv | プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/artifacts/analysis_outputs/train_preview.csv | csv_full | 17660 | 18086 | 232 | 0.0162 |
| doc_81b5cef8ad5b6965 | .py | プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/scripts/run_train.py | python_raw_text | 15534 | 15388 | 345 | 0.0137 |
| doc_24f68be614ae06ba | .py | プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/features.py | python_raw_text | 13359 | 13198 | 350 | 0.0118 |

## ファイル別チャンク数ランキング

| document_id | extension | relative_path | chunk_count | mean_chunk_length | max_chunk_length | chunk_share |
|---|---|---|---|---|---|---|
| doc_fedf164e75a35759 | .ipynb | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb | 37 | 1149.0 | 1199 | 0.0301 |
| doc_f8aa3d477d935cb8 | .ipynb | プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | 36 | 1170.1 | 1199 | 0.0293 |
| doc_c24302a2e2b18332 | .csv | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/data/train.csv | 36 | 1030.3 | 1200 | 0.0293 |
| doc_e2f7ed7ede4cfe4f | .csv | プロジェクト/白峰信用リスク評価株式会社/03.データ/train.csv | 36 | 1029.7 | 1200 | 0.0293 |
| doc_10145cb6808672ad | .ipynb | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb | 35 | 1147.5 | 1198 | 0.0285 |
| doc_f7bbe31b3fc35746 | .ipynb | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb | 35 | 1155.1 | 1195 | 0.0285 |
| doc_e52d8af8e3e09f73 | .ipynb | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | 34 | 1151.9 | 1199 | 0.0276 |
| doc_de03c1e2611d7376 | .ipynb | プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb | 34 | 1157.0 | 1199 | 0.0276 |
| doc_c76ce2191c7a7cf9 | .ipynb | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda_old.ipynb | 34 | 1152.3 | 1199 | 0.0276 |
| doc_281f4f8dee33851a | .py | プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/scripts/run_train.py | 31 | 1160.4 | 1199 | 0.0252 |
| doc_cecf9c7ef79041bf | .py | プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/scripts/run_train.py | 31 | 1145.3 | 1198 | 0.0252 |
| doc_f90e331bf1399a0f | .py | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/scripts/run_train.py | 31 | 1144.6 | 1199 | 0.0252 |
| doc_ef874fff56cacbf8 | .py | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/scripts/run_train.py | 31 | 1145.6 | 1198 | 0.0252 |
| doc_fc494cad6b99891d | .py | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/scripts/run_train.py | 31 | 1145.3 | 1198 | 0.0252 |
| doc_bc9c5d0845ebe443 | .ipynb | プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb | 29 | 1145.2 | 1197 | 0.0236 |
| doc_f7950acecd6c9962 | .ipynb | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb | 28 | 1139.6 | 1199 | 0.0228 |
| doc_f74251b3e48af6b1 | .ipynb | プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | 21 | 1127.8 | 1199 | 0.0171 |
| doc_22cccbd0e3648b72 | .csv | プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/artifacts/analysis_outputs/train_preview.csv | 19 | 1141.4 | 1173 | 0.0154 |
| doc_81b5cef8ad5b6965 | .py | プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/scripts/run_train.py | 16 | 1146.7 | 1192 | 0.013 |
| doc_0f57c5fbd2e6af70 | .py | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/features.py | 14 | 1111.7 | 1198 | 0.0114 |

## 抽出本文サンプル

| document_id | extension | relative_path | extraction_method | text_length | text_preview |
|---|---|---|---|---|---|
| doc_c24302a2e2b18332 | .csv | プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/data/train.csv | csv_summary_sample | 30092 | # source_path: プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/data/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # project_name: 白峰信用リスク評価株式会社 # major_folder: 04.分析 # CSVファイル: train.csv  - 行数: 7352 - 列数: 66 - 区切り文字: ',' - 列名: id, Attr1, Attr2, Attr3, Attr4, Attr5, Attr6, Attr7, Attr8, Attr9, Attr10, Attr11, Attr12, Attr13, Attr14, Attr15, Attr16, Attr17, Attr18, Attr19, Attr20, Attr21, Attr22, Attr23, Attr24, Attr25, Attr26, Attr27, Attr28, Attr29, Attr30, Attr31, Attr32, Attr33 |
| doc_e2f7ed7ede4cfe4f | .csv | プロジェクト/白峰信用リスク評価株式会社/03.データ/train.csv | csv_summary_sample | 30072 | # source_path: プロジェクト/白峰信用リスク評価株式会社/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # project_name: 白峰信用リスク評価株式会社 # major_folder: 03.データ # CSVファイル: train.csv  - 行数: 7352 - 列数: 66 - 区切り文字: ',' - 列名: id, Attr1, Attr2, Attr3, Attr4, Attr5, Attr6, Attr7, Attr8, Attr9, Attr10, Attr11, Attr12, Attr13, Attr14, Attr15, Attr16, Attr17, Attr18, Attr19, Attr20, Attr21, Attr22, Attr23, Attr24, Attr25, Attr26, Attr27, Attr28, Attr29, Attr30, Attr31, Attr32, Attr33, Attr34, Attr35, At |
| doc_22cccbd0e3648b72 | .csv | プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/artifacts/analysis_outputs/train_preview.csv | csv_full | 18086 | # source_path: プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/artifacts/analysis_outputs/train_preview.csv # file_name: train_preview.csv # extension: .csv # area: プロジェクト # project_name: 青葉与信マネジメント株式会社 # major_folder: 04.分析 # CSVファイル: train_preview.csv  - 行数: 200 - 列数: 10 - 区切り文字: ',' - 列名: id, loan_amnt, term, interest_rate, grade, employment_length, purpose, credit_score, application_type, loan_status  ## dtypes ,dtype id,int64 loan_amnt,float64 term,str interest_rate,float64 grade,str employmen |
| doc_558f0524ad87a81b | .csv | プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/data/train.csv | csv_summary_sample | 11373 | # source_path: プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/data/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # project_name: 株式会社青葉バイオメディカル機器 # major_folder: 04.分析 # CSVファイル: train.csv  - 行数: 735 - 列数: 33 - 区切り文字: ',' - 列名: id, Age, Attrition, BusinessTravel, DailyRate, Department, DistanceFromHome, Education, EducationField, EnvironmentSatisfaction, Gender, HourlyRate, JobInvolvement, JobLevel, JobRole, JobSatisfaction, MaritalStatus, MonthlyIncome, NumCompaniesWorked, O |
| doc_8289b30011ebfdb4 | .csv | プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.csv | csv_summary_sample | 11353 | # source_path: プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.csv # file_name: train.csv # extension: .csv # area: プロジェクト # project_name: 株式会社青葉バイオメディカル機器 # major_folder: 03.データ # CSVファイル: train.csv  - 行数: 735 - 列数: 33 - 区切り文字: ',' - 列名: id, Age, Attrition, BusinessTravel, DailyRate, Department, DistanceFromHome, Education, EducationField, EnvironmentSatisfaction, Gender, HourlyRate, JobInvolvement, JobLevel, JobRole, JobSatisfaction, MaritalStatus, MonthlyIncome, NumCompaniesWorked, Over18, OverTime, Per |
| doc_fedf164e75a35759 | .ipynb | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 35387 | # source_path: プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb # file_name: 01_eda.ipynb # extension: .ipynb # area: プロジェクト # project_name: 株式会社東都人材プラットフォーム # major_folder: 04.分析 # Notebook: 01_eda.ipynb  ## cell_000 [markdown] # EDAノートブック  本ノートブックは、分析業務で使うEDAを固定手順で実行するための定型版です。 可視化結果は相対パスで `reports/figures` に保存します。  ## cell_001 [markdown] ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9.  |
| doc_f8aa3d477d935cb8 | .ipynb | プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 35182 | # source_path: プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb # file_name: 01_eda.ipynb # extension: .ipynb # area: プロジェクト # project_name: 青葉与信マネジメント株式会社 # major_folder: 04.分析 # Notebook: 01_eda.ipynb  ## cell_000 [markdown] # EDAノートブック  本ノートブックは、分析業務で使うEDAを固定手順で実行するための定型版です。 可視化結果は相対パスで `reports/figures` に保存します。  ## cell_001 [markdown] ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果 |
| doc_f7bbe31b3fc35746 | .ipynb | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 33718 | # source_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb # file_name: 01_eda.ipynb # extension: .ipynb # area: プロジェクト # project_name: 株式会社青嶺不動産アセットマネジメント # major_folder: 04.分析 # Notebook: 01_eda.ipynb  ## cell_000 [markdown] # EDAノートブック  本ノートブックは、分析業務で使うEDAを固定手順で実行するための定型版です。 可視化結果は相対パスで `reports/figures` に保存します。  ## cell_001 [markdown] ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在 |
| doc_10145cb6808672ad | .ipynb | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 33472 | # source_path: プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb # file_name: 01_eda.ipynb # extension: .ipynb # area: プロジェクト # project_name: 医療法人社団 蒼樹会 みなみ野女性医療センター # major_folder: 04.分析 # Notebook: 01_eda.ipynb  ## cell_000 [markdown] # EDAノートブック  本ノートブックは、分析業務で使うEDAを固定手順で実行するための定型版です。 可視化結果は相対パスで `reports/figures` に保存します。  ## cell_001 [markdown] ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系 |
| doc_de03c1e2611d7376 | .ipynb | プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb | ipynb_cells_text_limited_outputs | 32771 | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb # file_name: 01_eda.ipynb # extension: .ipynb # area: プロジェクト # project_name: 医療法人社団 恒一会 かえで総合病院 # major_folder: 04.分析 # Notebook: 01_eda.ipynb  ## cell_000 [markdown] # EDAノートブック  本ノートブックは、分析業務で使うEDAを固定手順で実行するための定型版です。 可視化結果は相対パスで `reports/figures` に保存します。  ## cell_001 [markdown] ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） |
| doc_36f301e2b52f8a47 | .json | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_outputs/metrics.json | json_pretty_text | 7059 | # source_path: プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_outputs/metrics.json # file_name: metrics.json # extension: .json # area: プロジェクト # project_name: 株式会社東都人材プラットフォーム # major_folder: 04.分析 # JSONファイル: metrics.json  - top_level_type: dict - item_count: 39 - top_level_keys: task_type, encoding, target_column, date_column, use_date_features, use_numeric_interactions, use_cyclical_time_features, use_ordered_category_features, group_rare_categories, rare_category_min_count, use_categorical_frequency |
| doc_aacf7f80580f34e1 | .json | プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_outputs/metrics.json | json_pretty_text | 5358 | # source_path: プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_outputs/metrics.json # file_name: metrics.json # extension: .json # area: プロジェクト # project_name: 株式会社青葉バイオメディカル機器 # major_folder: 04.分析 # JSONファイル: metrics.json  - top_level_type: dict - item_count: 42 - top_level_keys: task_type, encoding, target_column, date_column, use_date_features, use_numeric_interactions, use_cyclical_time_features, use_ordered_category_features, group_rare_categories, rare_category_min_count, use_categorical_frequency |
| doc_737214815983ed61 | .json | プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_outputs/run_summary.json | json_pretty_text | 4976 | # source_path: プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_outputs/run_summary.json # file_name: run_summary.json # extension: .json # area: プロジェクト # project_name: 株式会社東都人材プラットフォーム # major_folder: 04.分析 # JSONファイル: run_summary.json  - top_level_type: dict - item_count: 33 - top_level_keys: target_column, date_column, task_type, use_date_features, use_numeric_interactions, use_cyclical_time_features, use_ordered_category_features, group_rare_categories, rare_category_min_count, use_categorical_frequen |
| doc_3a3798293b040d44 | .json | プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_outputs/metrics.json | json_pretty_text | 4555 | # source_path: プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_outputs/metrics.json # file_name: metrics.json # extension: .json # area: プロジェクト # project_name: 株式会社青嶺不動産アセットマネジメント # major_folder: 04.分析 # JSONファイル: metrics.json  - top_level_type: dict - item_count: 39 - top_level_keys: task_type, encoding, target_column, date_column, use_date_features, use_numeric_interactions, use_cyclical_time_features, use_ordered_category_features, group_rare_categories, rare_category_min_count, use_categorical_fre |
| doc_b126b2974232ad86 | .json | プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_outputs/metrics.json | json_pretty_text | 4464 | # source_path: プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_outputs/metrics.json # file_name: metrics.json # extension: .json # area: プロジェクト # project_name: 医療法人社団 恒一会 かえで総合病院 # major_folder: 04.分析 # JSONファイル: metrics.json  - top_level_type: dict - item_count: 42 - top_level_keys: task_type, encoding, target_column, date_column, use_date_features, use_numeric_interactions, use_cyclical_time_features, use_ordered_category_features, group_rare_categories, rare_category_min_count, use_categorical_frequ |

## 考察

対象とした5種類の拡張子については、抽出失敗の有無、抽出テキスト量、チャンク数を確認することで、初期RAGインデックスへの投入可否を判断できる状態になった。Markdown、CSV、JSON、Pythonコード、Notebookは少なくとも機械的なテキスト化が可能であり、後続の検索ベースラインに利用できる見込みがある。

一方で、Notebookは実行出力や長大なログ、Markdownセル内の埋め込み画像Base64を含みやすく、抽出テキスト量とチャンク数が過剰になりやすい。そのため、本版ではNotebookの出力本文に上限を設け、埋め込み画像Base64をプレースホルダ化し、Markdownセル・コードセル・限定されたテキスト出力を中心に抽出する方針とした。これにより、検索結果がNotebook由来のノイズに偏るリスクを下げる。

CSVについては、大容量ファイルを全文テキスト化せず、列名、型、欠損、先頭・末尾サンプル、要約統計を抽出している。これは初期検索には有効だが、特定条件の行抽出や集計が必要な質問では、テキスト検索だけでなくpandas等による直接検索・集計処理を組み合わせる必要がある。

以上より、EDA002はテキスト抽出ベースラインとしては有効である。ただし、検索精度を確認する段階では、ファイル別テキスト量ランキングとチャンク数ランキングを参照し、特定ファイルが検索結果を支配していないかを継続的に確認する。

## 抽出失敗

抽出失敗はありません。

## 次にやること

1. `text_chunks.jsonl` を使い、キーワード検索またはベクトル検索の最小構成を作る。
2. valid質問30件について、今回のテキスト抽出だけで答えられる問題を切り分ける。
3. Notebook由来チャンクがまだ多い場合は、Notebook出力上限やチャンク設計をさらに調整する。