# valid_022 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。「わかりません」と答えることは禁止です。根拠が弱い場合でも、提示根拠から最も妥当な短い回答を作ってください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: AOSHIOの NB01_eda.ipynbにおいて、観察結果サマリで出力されている「TGとの相関 上位5」の中で、相関係数が最も小さいカラム名を答えてください。

推定route: code_reading

route別の注意: コードやNotebook出力から該当する値・条件・列名だけを答える。

根拠:

[根拠 1]
score: 73.784955
source_path: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda_old.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda_old.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 2]
score: 73.784955
source_path: share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 3]
score: 73.596082
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 4]
score: 73.596082
source_path: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 5]
score: 73.408174
source_path: share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 6]
score: 73.408174
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 7]
score: 73.221223
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 8]
score: 73.221223
source_path: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 9]
score: 72.666041
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 10]
score: 72.666041
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb
record_type: notebook_cell
text:
Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の時系列傾向確認（存在時） 9. 観察結果サマリ

[根拠 11]
score: 72.355299
source_path: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx
record_type: generic_chunk
text:
yle=Compact --> T03: 0.7126899909960438 T05: 0.7126899909960438 run-level 指標（analysis.metrics より）: auc_roc: 0.8250532501536466 precision_at_top10pct: 0.9428571428571428 brier_score: 0.17514583544772114 selected_feature_count: 10, excluded_feature_count: 1 実装／環境 実験は線形系（linear_baseline 系）モデル群で実施。decision-tuning（クラス判定重みの調整）が T04 の改善要因として報告されています（visible_trials の change_summary に記載）。 ## 3. 主要な分析結果 モデル比較（可視領域の要点） ベースライン（T01）から段階的にクラスバランスや特徴量拡張、閾値調整を行い、T04（閾値チューニング済み線形モデル）が最も高い f1_macro を示した（f1_macro = 0.7329671168078127）。このことは、現データにおいて「モデル構造を大きく変えずに、決定閾値やクラス判断の調整で性能改善が得られる」ことを示唆します。 AUC-ROC（0.8250532501536466）や top10% precision（0.9428571428571428）が比較的良好である点は、スコア上位の予測が高い精度で陽性を含む可能性を示しており、閾値運用による業務ルール設計の余地があります。 特徴量・前処理の状況 モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。 <!-- block_in

[根拠 12]
score: 71.293798
source_path: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx
record_type: generic_chunk
text:
k_index=40 type=paragraph style=Compact --> モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。 モデル群は線形系での評価を優先しているため、説明可能性が確保された状態での比較が行われています。 臨床的解釈上の留意 本段階での結果は学習データ内（ホールドアウト検証等）での指標であり、外部検証データや運用環境での再現性は未確認です。運用導入の判断には追加検証（外部データや診療フローを反映した評価）が必要です。 ## 4. データ品質と実装状況 データ受領／EDA／前処理 キックオフ（M01）での合意に基づき EDA・前処理方針を実施し、可視実験群を生成しています（visible_trials 実行）。feature_selection の結果（selected 10, excluded 1）が得られています。 欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。 例: 「train.csv の行数 = 3,500」「欠損数 = 0」はプロジェクト概要に記載されているが、Report facts JSON に explicit に含まれないため本レポートでは（assumption）として扱います。 実装ステータス（analysis.implementation_status） 実装ステータスは “interim_analysis”（中間分析段階）。モデル構築・比較は実施済み（visible_trials）が、最終モデル確定・本番化は未実施。 再現性トレース 実行結果・ソースのトレースは Report facts の trace.source_files に保存パスが示されています（例: artifacts/analysis_o
