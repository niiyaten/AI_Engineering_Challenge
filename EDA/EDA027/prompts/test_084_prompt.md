# test_084 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。根拠から判断できない場合は、無理に推測せず「わかりません」と答えてください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 東都人材プラットフォームの最終報告書で分析結果が記載されている中で、モデル毎のF1スコアがランキング形式で記載されているページ数を教えてください。

推定route: document_whole_context

route別の注意: 指定文書内の該当箇所を読み、聞かれた語句だけを答える。

根拠:

[根拠 1]
score: 149.711965
source_path: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx
record_type: generic_chunk
text:
k_index=40 type=paragraph style=Compact --> モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。 モデル群は線形系での評価を優先しているため、説明可能性が確保された状態での比較が行われています。 臨床的解釈上の留意 本段階での結果は学習データ内（ホールドアウト検証等）での指標であり、外部検証データや運用環境での再現性は未確認です。運用導入の判断には追加検証（外部データや診療フローを反映した評価）が必要です。 ## 4. データ品質と実装状況 データ受領／EDA／前処理 キックオフ（M01）での合意に基づき EDA・前処理方針を実施し、可視実験群を生成しています（visible_trials 実行）。feature_selection の結果（selected 10, excluded 1）が得られています。 欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。 例: 「train.csv の行数 = 3,500」「欠損数 = 0」はプロジェクト概要に記載されているが、Report facts JSON に explicit に含まれないため本レポートでは（assumption）として扱います。 実装ステータス（analysis.implementation_status） 実装ステータスは “interim_analysis”（中間分析段階）。モデル構築・比較は実施済み（visible_trials）が、最終モデル確定・本番化は未実施。 再現性トレース 実行結果・ソースのトレースは Report facts の trace.source_files に保存パスが示されています（例: artifacts/analysis_o

[根拠 2]
score: 117.116201
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
icode MS" data-font-size-pt=""> : 約840万円 平均レベル : 約1,080万円 シニアレベル : 約1,260万円 さらに、この強い需要は今後も継続すると見込まれており、ERIの予測モデルによれば、5年後の2031年には日本における平均年収が現在の水準から約17%上昇し、12,651,708円に達すると推計されている。 一方で、若手人材のコーディングブートキャンプや独自のAI予測モデルに基づくSheCodesのデータでは、以下のようなより広範な推計値が示されている。 エントリーレベル（経験0-2年） <span data-font-color="#

[根拠 3]
score: 116.621734
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: metadata
text:
ファイル名: 株式会社東都人材プラットフォーム_最終報告.pptx 元パス: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx ファイル種別: pptx

[根拠 4]
score: 115.921949
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: pptx_slide
text:
Slide 6 4. 主要な分析結果 — モデル性能比較 | col_1 | col_2 | col_3 | col_4 | | --- | --- | --- | --- | | 順位 | モデルタイプ | Macro F1 | Accuracy | | 1 | hist_gradient_boosting | 0.4736 | 0.5104 | | 2 | hist_gradient_boosting | 0.4731 | 0.5082 | | 3 | random_forest | 0.4648 | 0.4879 | | 4 | hist_gradient_boosting | 0.4607 | 0.4996 | | 5 | linear_baseline | 0.4493 | 0.4731 | | 6 | linear_baseline | 0.4488 | 0.4722 | 中間試行の推移: 線形ベースライン(T01: F1=0.309) → 順序情報導入(T03: F1=0.449) → 非線形モデル(最終: F1=0.474) 過学習の状況: Train F1≈0.645 vs Val F1≈0.620 — テストでの低下は限定的だが過学習リスクに注意 Chart: {"chart_type": "BAR_CLUSTERED (57)", "title": "モデル別性能比較", "series_count": 2, "category_axis_title": "", "value_axis_title": ""} 5 / 15

[根拠 5]
score: 112.770256
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: pptx_slide
text:
Slide 2 1. エグゼクティブサマリ プロジェクト概要 株式会社東都人材プラットフォーム（発注者）と株式会社データアステル（受託者）により、 人材属性データを用いた「収入クラス（target）予測モデル」の企画・分析設計・初期検証を行った6週間の案件である。 主目的は収入クラスの予測可能性と主要因の抽出、People Analyticsにおける報酬分析基盤の初期版提供である。 Accuracy 0.510 Macro F1 0.474 最終実行設定 モデル: hist_gradient_boosting 行数: 11,529 / 特徴量: 14 検証分割: random_holdout (val=0.1) 本フェーズの成果物 再現可能な前処理仕様 ／ 評価結果表 ／ 可視化図表 ／ 再現可能な分析スクリプト・ノートブック ／ 中間報告 ／ 最終報告 → 業務判断に必要な初期示唆と運用化に向けた明確な次工程を提示している。 提案書 契約書 M01/M02 中間報告 最終報告 会議・成果トレース 1 / 15

[根拠 6]
score: 112.108314
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: pptx_slide
text:
Slide 1 最終分析報告書 株式会社東都人材プラットフォーム 収入クラス予測モデル 企画・分析設計・初期検証 受託者：株式会社データアステル 契約期間：2025年8月18日 ～ 2025年9月29日 CONFIDENTIAL

[根拠 7]
score: 110.887217
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx
record_type: pptx_slide
text:
Slide 6 4. 分析結果 ― モデル比較 モデル比較証跡― 主要モデルの性能ランキング | col_1 | col_2 | col_3 | col_4 | | --- | --- | --- | --- | | 順位 | モデル | F1 (macro) | Accuracy | | 1 | extra_trees | 0.6027 | 0.7780 | | 2 | extra_trees | 0.5953 | 0.7751 | | 3 | gradient_boosting | 0.5899 | 0.8011 | | 4 | random_forest | 0.5893 | 0.7980 | | 5 | random_forest | 0.5855 | 0.7951 | | 6 | random_forest | 0.5834 | 0.7957 | 解釈上の注意点 • interest_rate / grade はモデル性能に寄与している可能性が高いが、「審査時点で利用可能な情報か」によって本番時の再現性が大きく変わる（リーケージ懸念） • 変数寄与の重要度ランキングはモデル依存であり、業務解釈には注意が必要である 確認が必要な事項 • loan_status の業務上の最終定義（0/1 の意味付け）および運用上の解釈（承認可否基準、遅延定義等） • 時系列検証が不可（date列なし）のため、ドリフト・ビンテージ検証には別途データ取得が必要 Chart: {"chart_type": "COLUMN_CLUSTERED (51)", "title": "F1 (macro) vs Accuracy ― モデル比較", "series_count": 2, "category_axis_title": "", "value_axis_title": ""} ※モデルの詳細はleaderboard.csvに記載

[根拠 8]
score: 110.887217
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx
record_type: pptx_slide
text:
Slide 6 4. 分析結果 ― モデル比較 モデル比較証跡― 主要モデルの性能ランキング | col_1 | col_2 | col_3 | col_4 | | --- | --- | --- | --- | | 順位 | モデル | F1 (macro) | Accuracy | | 1 | extra_trees | 0.6027 | 0.7780 | | 2 | extra_trees | 0.5953 | 0.7751 | | 3 | gradient_boosting | 0.5899 | 0.8011 | | 4 | random_forest | 0.5893 | 0.7980 | | 5 | random_forest | 0.5855 | 0.7951 | | 6 | random_forest | 0.5834 | 0.7957 | 解釈上の注意点 • interest_rate / grade はモデル性能に寄与している可能性が高いが、「審査時点で利用可能な情報か」によって本番時の再現性が大きく変わる（リーケージ懸念） • 変数寄与の重要度ランキングはモデル依存であり、業務解釈には注意が必要である 確認が必要な事項 • loan_status の業務上の最終定義（0/1 の意味付け）および運用上の解釈（承認可否基準、遅延定義等） • 時系列検証が不可（date列なし）のため、ドリフト・ビンテージ検証には別途データ取得が必要 Chart: {"chart_type": "COLUMN_CLUSTERED (51)", "title": "F1 (macro) vs Accuracy ― モデル比較", "series_count": 2, "category_axis_title": "", "value_axis_title": ""} ※モデルの詳細はleaderboard.csvに記載
