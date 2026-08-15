# test_093 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。「わかりません」と答えることは禁止です。根拠が弱い場合でも、提示根拠から最も妥当な短い回答を作ってください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。

推定route: fallback_bm25_llm

route別の注意: 質問に対して必要な根拠だけを使って短く答える。

根拠:

[根拠 1]
score: 125.28962
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf
record_type: metadata
text:
ファイル名: 医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf 元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf ファイル種別: pdf

[根拠 2]
score: 113.694893
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf
record_type: pdf_page
text:
株式会社データアステル

[根拠 3]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/target_distribution.png
record_type: image
text:
画像ファイル: target_distribution.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/target_distribution.png

[根拠 4]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/overview_schema.png
record_type: image
text:
画像ファイル: overview_schema.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/overview_schema.png

[根拠 5]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png
record_type: image
text:
画像ファイル: numeric_distribution_top6.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png

[根拠 6]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/missing_rate_top20.png
record_type: image
text:
画像ファイル: missing_rate_top20.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/missing_rate_top20.png

[根拠 7]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png
record_type: image
text:
画像ファイル: feature_correlation_heatmap.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png

[根拠 8]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/date_feature_trend.png
record_type: image
text:
画像ファイル: date_feature_trend.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/date_feature_trend.png

[根拠 9]
score: 112.491521
source_path: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/categorical_distribution_top3.png
record_type: image
text:
画像ファイル: categorical_distribution_top3.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/categorical_distribution_top3.png

[根拠 10]
score: 111.313859
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/src/preprocess.py
record_type: metadata
text:
ファイル名: preprocess.py 元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/src/preprocess.py ファイル種別: py

[根拠 11]
score: 111.313859
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/src/modeling.py
record_type: metadata
text:
ファイル名: modeling.py 元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/src/modeling.py ファイル種別: py

[根拠 12]
score: 111.313859
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/src/infer.py
record_type: metadata
text:
ファイル名: infer.py 元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/src/infer.py ファイル種別: py
