# EDA026: test 100問 no-unknown LLM提出候補

## 目的

EDA025のno-unknown方針をtest 100問へ適用し、OpenRouter 20B回答と検索フォールバックで提出形式zipを作成する。

## 出力

- answer_log: `EDA/EDA026/tables/test_no_unknown_answer_log.csv`
- route_summary: `EDA/EDA026/tables/test_no_unknown_route_summary.csv`
- predictions_csv: `EDA/EDA026/predictions/predictions.csv`
- submission_zip: `EDA/EDA026/predictions/eda026_20b_no_unknown_submission.zip`
- prompt_debug: `EDA/EDA026/prompts`

## 実行設定

- model: `openai/gpt-oss-20b:free`
- top_k: 12
- max_context_chars: 24000
- max_tokens: 900
- temperature: 0.0

## 全体指標

凡例: `metric` は診断指標、`value` は値を表します。

| metric | value |
| --- | --- |
| test_question_count | 100 |
| http_200_count | 3 |
| unknown_answer_count | 0 |
| retrieval_fallback_count | 98 |
| max_answer_length | 238 |

## route別診断

凡例: `route` は質問ルート、`question_count` はtest質問数、`success_status_200_count` はHTTP 200件数、`unknown_answer_count` は不明回答数、`retrieval_fallback_count` は検索フォールバック件数です。

| route | question_count | success_status_200_count | unknown_answer_count | retrieval_fallback_count |
| --- | --- | --- | --- | --- |
| code_reading | 3 | 0 | 0 | 3 |
| diff_check | 9 | 2 | 0 | 8 |
| document_whole_context | 14 | 0 | 0 | 14 |
| fallback_bm25_llm | 37 | 0 | 0 | 37 |
| format_extraction | 17 | 1 | 0 | 16 |
| image_ocr | 3 | 0 | 0 | 3 |
| table_calculation | 17 | 0 | 0 | 17 |

## HTTP status別件数

凡例: `status` はOpenRouterのHTTPステータス、`count` は件数を表します。

| status | count |
| --- | --- |
| 200 | 3 |
| 429 | 97 |

## 質問別結果

凡例: `index` はtest質問番号、`route` は処理ルート、`answer` は最終回答、`answer_source` はLLM回答か検索フォールバックか、`status` はOpenRouter HTTPステータスを表します。

| index | route | answer | answer_source | status |
| --- | --- | --- | --- | --- |
| 0 | diff_check | 変更なし | llm | 200 |
| 1 | diff_check | Slide 1 最終分析報告書 肝疾患有無予測分析プロジェクト 医療法人社団 恒一会 かえで総合病院 御中 株式会社データアステル 契約期間：2025年9月2日 開始（5週間） 実績工数：140時間 最終請求金額（税込）：3,850,000円 | retrieval_fallback | 200 |
| 2 | format_extraction | 情報が不足しています | llm | 200 |
| 3 | format_extraction | 契約締結日兼効力発生日：2025-09-02 ### 甲 医療法人社団 恒一会 かえで総合病院 医療情報分析室 室長 柴田 海斗 署名：____________________________ ### 乙 株式会社データアステル データサイエンス部 署名：____________________________ ## | retrieval_fallback | 429 |
| 4 | code_reading | 医療法人社団 蒼泉会 ひがし丘総合病院 最終分析報告書 医療費関連の価格帯分類と要因分析プロジェクト 契約期間: 2025-07-08 ～ 2025-08-05（5週間） 対象データ: data¥train.csv \| 1,600件・8列・欠損0件 目的変数: charges（価格帯 0/1/2 の3クラス分類） 最終 | retrieval_fallback | 429 |
| 5 | fallback_bm25_llm | k_index=40 type=paragraph style=Compact --> モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています | retrieval_fallback | 429 |
| 6 | table_calculation | 医療法人社団 蒼泉会 ひがし丘総合病院 最終分析報告書 医療費関連の価格帯分類と要因分析プロジェクト 契約期間: 2025-07-08 ～ 2025-08-05（5週間） 対象データ: data¥train.csv \| 1,600件・8列・欠損0件 目的変数: charges（価格帯 0/1/2 の3クラス分類） 最終 | retrieval_fallback | 429 |
| 7 | format_extraction | Slide 1 Image: data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx.assets/slide001_shape001.wmf 表1 | retrieval_fallback | 429 |
| 8 | table_calculation | ## Extracted Images - data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx.assets/rId5.emf (40824 bytes) | retrieval_fallback | 429 |
| 9 | diff_check | MS1 キックオフ完了: 2025-07-08 MS2 データ理解完了: 2025-07-18 MS3 中間報告完了: 2025-07-22（本チェックポイント） 次回チェックポイント: 2025-07-24 変更管理判定 最終報告: 2025-08-05 ### 2.2 WBSトレースによる進捗整理 中間報告時点で、 | retrieval_fallback | 429 |
| 10 | table_calculation | Slide 1 最終分析報告書 肝疾患有無予測分析プロジェクト 医療法人社団 恒一会 かえで総合病院 御中 株式会社データアステル 契約期間：2025年9月2日 開始（5週間） 実績工数：140時間 最終請求金額（税込）：3,850,000円 | retrieval_fallback | 429 |
| 11 | format_extraction | Slide 15 11. 次アクション 1 本提案内容のご確認および契約条件の承認 2 キックオフ実施日程の確定 3 data\\train.csv および関連カラム説明資料の正式受領確認 4 定例会議体および報告会日程の確定 5 契約開始日 2025-08-06 に向けた着手準備の実施 株式会社データアステルは、青嶺不 | retrieval_fallback | 429 |
| 12 | document_whole_context | 医療法人社団 蒼泉会 ひがし丘総合病院 最終分析報告書 医療費関連の価格帯分類と要因分析プロジェクト 契約期間: 2025-07-08 ～ 2025-08-05（5週間） 対象データ: data¥train.csv \| 1,600件・8列・欠損0件 目的変数: charges（価格帯 0/1/2 の3クラス分類） 最終 | retrieval_fallback | 429 |
| 13 | fallback_bm25_llm | # データアステル社内管理_決裁基準 ## 1. 目的 本規程は、案件の契約金額および契約条件に応じた社内決裁レベルを定め、提案・契約・請求に関する承認プロセスを統一することを目的とする | retrieval_fallback | 429 |
| 14 | diff_check | Slide 2 01 エグゼクティブサマリー 青葉与信マネジメント株式会社 審査企画部における与信分析基盤整備に向けた、データ分析プロジェクトの提案概要である | retrieval_fallback | 429 |
| 15 | format_extraction | 画像ファイル: target_distribution.png パス: data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/reports/figures/target_distribution.png | retrieval_fallback | 429 |
| 16 | format_extraction | 次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください | retrieval_fallback | 429 |
| 17 | format_extraction | 留意点 「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください） | retrieval_fallback | 429 |
| 18 | document_whole_context | 例: 「train.csv の行数 = 3,500」「欠損数 = 0」はプロジェクト概要に記載されているが、Report facts JSON に explicit に含まれないため本レポートでは（assumption）として扱います | retrieval_fallback | 429 |
| 19 | table_calculation | Slide 1 最終分析報告書 NYC不動産売買トランザクション価格形成要因分析 クライアント：株式会社青嶺不動産アセットマネジメント 実施者：株式会社データアステル 契約期間：2025年8月6日〜2025年9月17日 課金方式：タイム・アンド・マテリアル CONFIDENTIAL 最終報告会：2025年9月16日 | retrieval_fallback | 429 |
| 20 | document_whole_context | Slide 1 最終分析報告書 株式会社東都人材プラットフォーム 収入クラス予測モデル 企画・分析設計・初期検証 受託者：株式会社データアステル 契約期間：2025年8月18日 ～ 2025年9月29日 CONFIDENTIAL | retrieval_fallback | 429 |
| 21 | fallback_bm25_llm | ## 1. 当事者 ### （1）甲 会社名：株式会社青葉バイオメディカル機器 部署名：人事本部 人材戦略部 主担当者：山田 太一 役職：人材戦略部長 ### （2）乙 会社名：株式会社データアステル 部署名：データサイエンス部 エグゼクティブスポンサー：中村 誠 プロジェクトマネージャー：加藤 大輔 リードデータサイ | retrieval_fallback | 429 |
| 22 | diff_check | Slide 1 最終分析報告書 企業財務指標を用いた3年後倒産予測分析プロジェクト クライアント: 白峰信用リスク評価株式会社 審査企画部 ベンダ: 株式会社データアステル データサイエンス部 | retrieval_fallback | 429 |
| 23 | document_whole_context | Slide 12 8. 費用見積 見込金額（税込） ¥4,675,000 税抜 ¥4,250,000 + 消費税 ¥425,000 契約形態 タイム&マテリアル 時間単価 ¥25,000/時間 見込工数 170時間 工数丸め 30分単位 ※ 固定総額契約ではなく、最終請求額は実績工数に基づいて確定する ※ 精算ルール： | retrieval_fallback | 429 |
| 24 | fallback_bm25_llm | 正式なデータ件数は A03 の品質報告で再確認してください | retrieval_fallback | 429 |
| 25 | format_extraction | 要注意（ガバナンス） 監査証跡: 目的変数定義、前処理スクリプト、評価条件、モデルパラメータ、成果物版数は必ず成果物に記載のうえ保管してください | retrieval_fallback | 429 |
| 26 | fallback_bm25_llm | 留意点 「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください） | retrieval_fallback | 429 |
| 27 | document_whole_context | Slide 16 15. 提案・契約との差分管理（1/2） \| col_1 \| col_2 \| col_3 \| col_4 \| \| --- \| --- \| --- \| --- \| \| 項目 \| 差分 \| 変更理由 \| 承認トレース \| \| 成果物 \| なし \| 契約定義の成果物を全て納品済 \| Contract 第4条 | retrieval_fallback | 429 |
| 28 | fallback_bm25_llm | 画像ファイル: target_distribution.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/target_distribution.png | retrieval_fallback | 429 |
| 29 | table_calculation | 成果物の公開・活用範囲は必ず合意された運用ルールに従ってください | retrieval_fallback | 429 |

## 注意点

- `わかりません` または空回答の場合は、検索上位根拠から本文行を選んでフォールバックした。
- 不明回答をなくす実験なので、精度よりも提出時の空振り回避を優先している。
- SIGNATEへの実提出は行っていない。
- APIキーは `.apikey` から読み込み、成果物には保存しない。
