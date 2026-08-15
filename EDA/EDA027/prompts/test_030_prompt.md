# test_030 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。根拠から判断できない場合は、無理に推測せず「わかりません」と答えてください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 青葉与信マネジメントの分析対象データにおいて、標準化されたloan_amntが0未満の行のうち、purpose=credit_cardに該当し、かつloan_amntがpurpose=credit_card全体の平均を上回る行の割合は何%ですか。小数第2位まで答えてください。

推定route: table_calculation

route別の注意: 表・CSV・Excelの値を読み取り、必要なら計算して短く答える。

根拠:

[根拠 1]
score: 83.983524
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx
record_type: generic_chunk
text:
い（監査／解釈基準の根幹）。 interest_rate / grade を「審査時点で利用可」とするか否かを決定してください（運用実装可否に直結）。 追加要望が発生した場合は、変更管理ポリシー（別紙見積）に従う方針で運用することを確認ください。 商務情報（Report facts の commercial／project_facts に基づく） 契約形態: 固定価格（fixed_price） 契約金額（税抜）: 4,200,000 円 税率: 10%（税額 420,000 円） 契約金額（税込）: 4,620,000 円 支払スケジュール: 2 回分割（着手金 50%／検収金 50%） — 各金額は payment_schedule に記載の通り 支払管理は PM（伊藤 翔太）で統括 クリティカルパスと次マイルストーン クリティカルな前提: loan_status の業務定義確定および interest_rate/grade の利用可否確認（これらが確定しないと中間レビュー以降のモデル解釈が不確定になります）。 次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください。 現状の運用上の判断メモ キックオフ時点では、分析結果ではなく前提整理の完了を優先してください。 監査証跡の観点では、議事録（キックオフ）を含めた前提定義の早期登録が必須です。 <!-- block_index=96 type=paragraph s

[根拠 2]
score: 82.275722
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/03.データ/train.csv
record_type: table_file
text:
表ファイル: train.csv 形式: csv 行数: 17500 列数: 10 列: id, loan_amnt, term, interest_rate, grade, employment_length, purpose, credit_score, application_type, loan_status サンプル: | id | loan_amnt | term | interest_rate | grade | employment_length | purpose | credit_score | application_type | loan_status | | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | | 0 | 1256.7108 | 5 years | 10.60377869 | B1 | 5 years | debt_consolidation | 680.4317659 | Individual | 0 | | 1 | 569.5596067 | 3 years | 17.30556544 | C5 | 3 years | house | 713.0631282 | Individual | 0 | | 2 | 1118.83805 | 3 years | 14.04134157 | C3 | 2 years | debt_consolidation | 696.137378 | Individual | 1 | | 3 | 610.7217277 | 3 years | 13.04834802 | C2 | 5 years | medical | 656.3730904 | Individual | 0 | | 4 | 1180.02684 | 3 years | 11.38486247 | B3 | 10 years | debt_consolidation | 657.211233 | Individual | 0 | | 5 | 1172.219819 | 3 years | 11.39718304 | B3 | 5 years | debt_consolidation | 712.157342 | Joint App | 0 | | 6 | 2433.646304 | 3 years | 10.10181044 | B3 | 10 years | debt_consolidation | 713.2019707 | Individual | 0 | | 7 | 1021.9603 | 5 years | 18.09302821 | D4 | 4 years | debt_consolidation | 658.2994753 | Individual | 0 |

[根拠 3]
score: 82.224924
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx
record_type: pptx_slide
text:
Slide 2 1. エグゼクティブサマリ ― プロジェクト概要 プロジェクト目的 loan_status を目的変数として、 返済不良リスクの主要因整理、 リスクセグメンテーション、 業務説明可能な形での示唆提供 分析対象データ data/train.csv 17,500 レコード / 10 カラム 欠損 0 件 目的変数: loan_status 契約概要 期間: 2025/4/9 〜 5/28（7週間） 形態: 固定価格 金額: ¥4,200,000（税抜） 発注: 青葉与信マネジメント 主要成果指標（ベースライン: extra_trees, train=14,000 / test=3,500） 0.7127 ROC-AUC 0.778 Accuracy 0.6027 F1 (macro) 0.1581 Brier Score 0.4886 Prec@Top10% 全体結論 上位リスク群に不良が集約される傾向を確認（precision@top10% ≈ 0.49）。実用に資するリスク区分の提示が可能。 ただし、interest_rate / grade の運用時点での利用可否、および時系列検証の不足により、本番利用には追加確認・外部検証・運用設計が必須である。

[根拠 4]
score: 82.224924
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx
record_type: pptx_slide
text:
Slide 2 1. エグゼクティブサマリ ― プロジェクト概要 プロジェクト目的 loan_status を目的変数として、 返済不良リスクの主要因整理、 リスクセグメンテーション、 業務説明可能な形での示唆提供 分析対象データ data/train.csv 17,500 レコード / 10 カラム 欠損 0 件 目的変数: loan_status 契約概要 期間: 2025/4/9 〜 5/28（7週間） 形態: 固定価格 金額: ¥4,200,000（税抜） 発注: 青葉与信マネジメント 主要成果指標（ベースライン: extra_trees, train=14,000 / test=3,500） 0.7127 ROC-AUC 0.778 Accuracy 0.6027 F1 (macro) 0.1581 Brier Score 0.4886 Prec@Top10% 全体結論 上位リスク群に不良が集約される傾向を確認（precision@top10% ≈ 0.49）。実用に資するリスク区分の提示が可能。 ただし、interest_rate / grade の運用時点での利用可否、および時系列検証の不足により、本番利用には追加確認・外部検証・運用設計が必須である。

[根拠 5]
score: 81.53255
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/03.データ/train.xlsx
record_type: xlsx_sheet
text:
Excelファイル: train.xlsx シート: train 使用範囲: A1:J17501 列: id, loan_amnt, term, interest_rate, grade, employment_length, purpose, credit_score, application_type, loan_status グラフ数: 0 サンプル: | id | loan_amnt | term | interest_rate | grade | employment_length | purpose | credit_score | application_type | loan_status | | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | | 0 | 1256.7108 | 5 years | 10.60377869 | B1 | 5 years | debt_consolidation | 680.4317659 | Individual | 0 | | 1 | 569.5596067 | 3 years | 17.30556544 | C5 | 3 years | house | 713.0631282 | Individual | 0 | | 2 | 1118.83805 | 3 years | 14.04134157 | C3 | 2 years | debt_consolidation | 696.137378 | Individual | 1 | | 3 | 610.7217277 | 3 years | 13.04834802 | C2 | 5 years | medical | 656.3730904 | Individual | 0 | | 4 | 1180.02684 | 3 years | 11.38486247 | B3 | 10 years | debt_consolidation | 657.211233 | Individual | 0 | | 5 | 1172.219819 | 3 years | 11.39718304 | B3 | 5 years | debt_consolidation | 712.157342 | Joint App | 0 | | 6 | 2433.646304 | 3 years | 10.10181044 | B3 | 10 years | debt_consolidation | 713.2019707 | Individual | 0 | | 7 | 1021.9603 | 5 years | 18.09302821 | D4 | 4 years | debt_consolidation | 658.2994753 | Individual | 0 |

[根拠 6]
score: 80.998576
source_path: share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx
record_type: generic_chunk
text:
style=Compact --> 実行アーティファクト（再現元）: artifacts/analysis_outputs/run_summary.json, artifacts/analysis_outputs/metrics.json, artifacts/analysis_outputs/experiments/leaderboard.json（Report facts.trace.source_files に記載） 会議議事録: artifacts/meeting_minutes/会議録_2025-09-02.md（M01）および本中間レビュー議事録（M02）をプロジェクトの唯一基準として管理してください。 要注意（PM 向け） open actions = 7（prior_state.open_action_count = 7）。PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソース配分を確定してください。 2025-09-19 の変更管理チェックポイントは契約上の追加対応要否を判定する重要日です。追加要求が出た場合は change_request_policy（time_and_materials）に従って見積り・承認の流れを確保してください。 以上 （作成: データアステル / 分析チーム — 報告は Report facts JSON（checkpoint=M02, stage=interim）に基づく内容です）

[根拠 7]
score: 80.798007
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx
record_type: generic_chunk
text:
支払スケジュール: 着手金（50%）期日 2025-04-16、検収金（50%）期日 2025-06-03（各期日は契約条件に基づく）。 検討リソース（PM 向け） クリティカルパス: データ理解 → 探索分析 → 中間レビュー → モデリング → 評価 → 報告書作成 → 検収（スケジュール上の遅延は 2025-05-27 の最終報告会へ影響）。 変更管理: 2025-05-01 を変更管理チェックポイントに設定済み。追加要望はこの時点で仕分け・見積りする運用としてください。固定価格のため、契約範囲外は別途見積りが必要です。 要注意（ガバナンス） 監査証跡: 目的変数定義、前処理スクリプト、評価条件、モデルパラメータ、成果物版数は必ず成果物に記載のうえ保管してください。現在 run_summary/metrics は出力済みですが、会議決定事項（M01/M02）の議事録反映が必要です。 公平性評価: 性別・年齢などセンシティブ変数がデータに含まれていないため包括的公平性評価は制限あり。範囲と限界を最終報告に明示する必要があります。 以上。必要であれば、M02 の議事録反映後に改定版（議事録に基づく確定事項を反映した中間報告書）を速やかに発行します。

[根拠 8]
score: 80.759854
source_path: share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/00.提案/提案書_v3.pptx
record_type: pptx_slide
text:
Slide 3 02 1. 背景 審査企画部において、返済不良リスクの定量的把握と審査判断の説明可能性・監査可能性を両立する分析基盤の整備が求められている。 対象データ概要 train.csv 学習用データ: 17,500件 変数: 10項目 目的変数: loan_status ▶ 分析内容 与信リスクの定量分析 セグメント別リスク差異の可視化 説明可能なモデル構築・評価 業務活用可能な示唆の整理 ▶ 期待成果 リスク要因の整理 リスクセグメンテーション ポートフォリオ評価基盤 監査可能な文書体系 主要データ項目 loan_amnt term interest_rate grade employment_length purpose credit_score application_type 金融分析案件としての重要観点 1 返済不良リスクの早期把握 2 審査基準の説明可能性確保 3 ポートフォリオ健全性比較 4 監査証跡・アクセス制御の確保 5 7週間での短納期対応
