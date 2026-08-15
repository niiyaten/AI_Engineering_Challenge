# test_015 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。根拠から判断できない場合は、無理に推測せず「わかりません」と答えてください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 東都人材プラットフォームのtrain.xlsxにおいて、Sheet1の黄色にハイライトされたセルの抽出条件と集計内容を答えてください。

推定route: format_extraction

route別の注意: 色、太字、下線、ハイライトなどの書式に対応する文字列だけを抽出する。

根拠:

[根拠 1]
score: 93.523838
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: metadata
text:
ファイル名: 株式会社東都人材プラットフォーム_最終報告.pptx 元パス: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx ファイル種別: pptx

[根拠 2]
score: 88.072957
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.xlsx
record_type: metadata
text:
ファイル名: train.xlsx 元パス: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.xlsx ファイル種別: xlsx

[根拠 3]
score: 86.148391
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: pptx_slide
text:
Slide 1 最終分析報告書 株式会社東都人材プラットフォーム 収入クラス予測モデル 企画・分析設計・初期検証 受託者：株式会社データアステル 契約期間：2025年8月18日 ～ 2025年9月29日 CONFIDENTIAL

[根拠 4]
score: 85.216213
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx
record_type: pptx_slide
text:
Slide 2 1. エグゼクティブサマリ プロジェクト概要 株式会社東都人材プラットフォーム（発注者）と株式会社データアステル（受託者）により、 人材属性データを用いた「収入クラス（target）予測モデル」の企画・分析設計・初期検証を行った6週間の案件である。 主目的は収入クラスの予測可能性と主要因の抽出、People Analyticsにおける報酬分析基盤の初期版提供である。 Accuracy 0.510 Macro F1 0.474 最終実行設定 モデル: hist_gradient_boosting 行数: 11,529 / 特徴量: 14 検証分割: random_holdout (val=0.1) 本フェーズの成果物 再現可能な前処理仕様 ／ 評価結果表 ／ 可視化図表 ／ 再現可能な分析スクリプト・ノートブック ／ 中間報告 ／ 最終報告 → 業務判断に必要な初期示唆と運用化に向けた明確な次工程を提示している。 提案書 契約書 M01/M02 中間報告 最終報告 会議・成果トレース 1 / 15

[根拠 5]
score: 83.383786
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/target_distribution.png
record_type: image
text:
画像ファイル: target_distribution.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/target_distribution.png

[根拠 6]
score: 83.383786
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png
record_type: image
text:
画像ファイル: numeric_distribution_top6.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png

[根拠 7]
score: 83.383786
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/missing_rate_top20.png
record_type: image
text:
画像ファイル: missing_rate_top20.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/missing_rate_top20.png

[根拠 8]
score: 83.383786
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png
record_type: image
text:
画像ファイル: feature_correlation_heatmap.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png
