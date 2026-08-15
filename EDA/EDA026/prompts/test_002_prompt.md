# test_002 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。「わかりません」と答えることは禁止です。根拠が弱い場合でも、提示根拠から最も妥当な短い回答を作ってください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 青嶺不動産アセットマネジメントのスケジュール_r2.xlsxにおいて、オレンジにハイライトされている行のタスク名をすべて答えてください。

推定route: format_extraction

route別の注意: 色、太字、下線、ハイライトなどの書式に対応する文字列だけを抽出する。

根拠:

[根拠 1]
score: 141.936686
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r2.xlsx
record_type: metadata
text:
ファイル名: スケジュール_r2.xlsx 元パス: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r2.xlsx ファイル種別: xlsx

[根拠 2]
score: 128.491729
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r1.xlsx
record_type: metadata
text:
ファイル名: スケジュール_r1.xlsx 元パス: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r1.xlsx ファイル種別: xlsx

[根拠 3]
score: 105.232429
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx
record_type: pptx_slide
text:
Slide 15 09 成果物サマリ 納品済の主要成果物（契約4.1に準拠） 1. プロジェクト概要書 本書を正本 納品済 2. 分析計画メモ / 実施方針書 artifacts/* 納品済 3. 中間報告書 MS4: 2025-08-26 納品済 4. 最終報告書 本書 納品済 5. 会議議事メモ M01, M02 納品済 6. スケジュール管理表 artifacts/schedule/* 納品済 7. 分析出力 run_summary, metrics, leaderboard 納品済

[根拠 4]
score: 100.501017
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx
record_type: metadata
text:
ファイル名: 株式会社青嶺不動産アセットマネジメント_最終報告.pptx 元パス: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx ファイル種別: pptx

[根拠 5]
score: 96.974612
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx
record_type: generic_chunk
text:
い（監査／解釈基準の根幹）。 interest_rate / grade を「審査時点で利用可」とするか否かを決定してください（運用実装可否に直結）。 追加要望が発生した場合は、変更管理ポリシー（別紙見積）に従う方針で運用することを確認ください。 商務情報（Report facts の commercial／project_facts に基づく） 契約形態: 固定価格（fixed_price） 契約金額（税抜）: 4,200,000 円 税率: 10%（税額 420,000 円） 契約金額（税込）: 4,620,000 円 支払スケジュール: 2 回分割（着手金 50%／検収金 50%） — 各金額は payment_schedule に記載の通り 支払管理は PM（伊藤 翔太）で統括 クリティカルパスと次マイルストーン クリティカルな前提: loan_status の業務定義確定および interest_rate/grade の利用可否確認（これらが確定しないと中間レビュー以降のモデル解釈が不確定になります）。 次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください。 現状の運用上の判断メモ キックオフ時点では、分析結果ではなく前提整理の完了を優先してください。 監査証跡の観点では、議事録（キックオフ）を含めた前提定義の早期登録が必須です。 <!-- block_index=96 type=paragraph s

[根拠 6]
score: 93.934248
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx
record_type: generic_chunk
text:
er: 山本 彩乃 — 目安: MS4 後着手（2025-04-30〜）。 - モデル評価の深化（リフト、PR-AUC、混同行列、上位群の詳細解析） — Owner: 山本 彩乃 — 目安: MS5（2025-05-13）までに確定。 - 中間報告書の確定・配布（中間レビューの議事録反映含む） — Owner: 藤田 彩 — 目安: 2025-05-14〜2025-05-16（中間報告確定）。 - 変更要求の仕分け（MS4: 2025-05-01）— Owner: 伊藤 翔太。 （注）上記の期日はプロジェクトスケジュールに基づく。prior_state に登録された Open アクションは 5 件です（open_action_count=5）。 ## 7. 経営/PM向け補足 主要決定依頼（早急） loan_status の公式な文書定義（A01）を最優先で確定・配布してください。解析方向の基準になります。 interest_rate / grade の「審査時点での利用可否」（A02）を確定してください。未回答の場合は並列評価で対応しますが、追加工数・説明負荷が発生します。 中間レビュー（M02）の議事録・合意事項（採用する評価指標、リスク区分の方針・優先順位）がまだシステムに登録されていない場合、速やかに反映をお願いします（トレーサビリティ確保のため）。 スケジュールと費用（確定値） 契約開始日: 2025-04-09（既スタート） 契約期間: 7 週間 契約金額（税抜）: 4,200,000 円（project_facts.commercial_terms） 税率: 10%（税額 420,000 円） → 税込合計 4,620,000 円 支払スケジュール: 着手金（50%）期日 2025-04-16、検収金（50%）期日 2025-06-03（各期日は契約条件に基づく）。 検討リソース（PM 向け） <!-- block_index=101

[根拠 7]
score: 92.313236
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/会議録/会議録_2025-08-06.docx
record_type: generic_chunk
text:
BIZ UDPゴシック" data-font-size-pt="">*直樹（QA／データアステル）* 欠席: - *小林* * * *直樹（QA／データアステル）* ## 2. 議題 目的変数・対象データ・スコープ確認（SALE PRICE / data .csv） 初期スケジュール（第1週〜第2週）承認（MS1→MS2） 役割分担・会議運営確認（定例頻度・意思決定窓口） <!-- block_index=15 type=paragraph style=Compa

[根拠 8]
score: 90.397675
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx
record_type: pptx_slide
text:
Slide 1 最終分析報告書 NYC不動産売買トランザクション価格形成要因分析 クライアント：株式会社青嶺不動産アセットマネジメント 実施者：株式会社データアステル 契約期間：2025年8月6日〜2025年9月17日 課金方式：タイム・アンド・マテリアル CONFIDENTIAL 最終報告会：2025年9月16日

[根拠 9]
score: 89.725779
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/target_distribution.png
record_type: image
text:
画像ファイル: target_distribution.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/target_distribution.png

[根拠 10]
score: 89.725779
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png
record_type: image
text:
画像ファイル: numeric_distribution_top6.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/numeric_distribution_top6.png

[根拠 11]
score: 89.725779
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/missing_rate_top20.png
record_type: image
text:
画像ファイル: missing_rate_top20.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/missing_rate_top20.png

[根拠 12]
score: 89.725779
source_path: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png
record_type: image
text:
画像ファイル: feature_correlation_heatmap.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/reports/figures/feature_correlation_heatmap.png
