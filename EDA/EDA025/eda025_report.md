# EDA025: valid 30問 no-unknown LLM回答生成

## 目的

EDA024でLLM回答の改善が見えた一方で `わかりません` が残ったため、valid 30問で不明回答を出さないパイプラインを検証する。

## 出力

- answer_log: `EDA/EDA025/tables/valid_no_unknown_answer_log.csv`
- route_summary: `EDA/EDA025/tables/valid_no_unknown_route_summary.csv`
- prompt_debug: `EDA/EDA025/prompts`

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
| valid_question_count | 30 |
| http_200_count | 4 |
| exact_match_count | 1 |
| contains_gold_count | 2 |
| answer_in_topk_context_count | 7 |
| avg_token_recall | 0.0976 |
| unknown_answer_count | 0 |
| retrieval_fallback_count | 26 |

## route別診断

凡例: `route` は質問ルート、`question_count` はvalid質問数、`exact_match_count` は正規化完全一致数、`contains_gold_count` は予測文に正解が含まれた件数、`answer_in_topk_context_count` は上位検索根拠に正解文字列が含まれた件数、`avg_token_recall` は正解語句トークンの回収率平均、`success_status_200_count` はHTTP 200件数です。

| route | question_count | exact_match_count | contains_gold_count | answer_in_topk_context_count | avg_token_recall | success_status_200_count |
| --- | --- | --- | --- | --- | --- | --- |
| code_reading | 4 | 0 | 0 | 0 | 0.0237 | 0 |
| diff_check | 1 | 0 | 0 | 0 | 0.0714 | 0 |
| document_whole_context | 7 | 0 | 1 | 4 | 0.2159 | 1 |
| fallback_bm25_llm | 8 | 0 | 0 | 3 | 0.0 | 0 |
| format_extraction | 2 | 0 | 0 | 0 | 0.0 | 1 |
| image_ocr | 1 | 1 | 1 | 0 | 1.0 | 1 |
| table_calculation | 7 | 0 | 0 | 0 | 0.0357 | 1 |

## HTTP status別件数

凡例: `status` はOpenRouterのHTTPステータス、`count` は件数を表します。

| status | count |
| --- | --- |
| 200 | 4 |
| 429 | 26 |

## 質問別結果

凡例: `index` はvalid質問番号、`route` は処理ルート、`gold_answer` は正解、`llm_answer` は最終回答、`answer_source` はLLM回答か検索フォールバックか、`exact_match` は正規化完全一致、`contains_gold` は回答に正解文字列が含まれるかを表します。

| index | route | gold_answer | llm_answer | answer_source | exact_match | contains_gold |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | format_extraction | hr、weekday、weathersit、temp | （該当なし） | llm | 0 | 0 |
| 1 | image_ocr | 20日 | 20日 | llm | 1 | 1 |
| 2 | document_whole_context | Recall | Recall, Precision, F1‑score, ROC‑AUC, Accuracy | llm | 0 | 1 |
| 3 | table_calculation | 4,394,250円 | 1875000円 | llm | 0 | 0 |
| 4 | code_reading | hist_gradient_boosting | Slide 1 最終分析報告書 NYC不動産売買トランザクション価格形成要因分析 クライアント：株式会社青嶺不動産アセットマネジメント 実施者：株式会社データアステル 契約期間：2025年8月6日〜2025年9月17日 課金方式：タイム・アンド・マテリアル CONFIDENTIAL 最終報告会：2025年9月16日 | retrieval_fallback | 0 | 0 |
| 5 | document_whole_context | 対象外（契約明記） | Slide 2 目次 01 エグゼクティブサマリ 02 プロジェクト目的とスコープ 03 実施方法 04 主要な分析結果と解釈 05 業務提言 06 実装・運用計画 07 制約事項と残余リスク 08 今後の拡張ロードマップ 09 成果物サマリ 10 提案・契約との差分管理 11 総括 | retrieval_fallback | 0 | 0 |
| 6 | table_calculation | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | ## 3. 主要な分析結果 モデル比較（可視領域の要点） ベースライン（T01）から段階的にクラスバランスや特徴量拡張、閾値調整を行い、T04（閾値チューニング済み線形モデル）が最も高い f1_macro を示した（f1_macro = 0.7329671168078127） | retrieval_fallback | 0 | 0 |
| 7 | table_calculation | 32歳 | Slide 1 最終分析報告書 肝疾患有無予測分析プロジェクト 医療法人社団 恒一会 かえで総合病院 御中 株式会社データアステル 契約期間：2025年9月2日 開始（5週間） 実績工数：140時間 最終請求金額（税込）：3,850,000円 | retrieval_fallback | 0 | 0 |
| 8 | fallback_bm25_llm | 1,168,750円 | Slide 12 8. 費用見積 見込金額（税込） ¥4,675,000 税抜 ¥4,250,000 + 消費税 ¥425,000 契約形態 タイム&マテリアル 時間単価 ¥25,000/時間 見込工数 170時間 工数丸め 30分単位 ※ 固定総額契約ではなく、最終請求額は実績工数に基づいて確定する ※ 精算ルール： | retrieval_fallback | 0 | 0 |
| 9 | diff_check | QAレビューア：池田 直哉 → 小林 直樹 | Slide 1 データ分析プロジェクト提案書 株式会社青嶺不動産アセットマネジメント 様 ニューヨーク市不動産売買データに基づく価格形成要因分析 株式会社データアステル データサイエンス部 | retrieval_fallback | 0 | 0 |
| 10 | document_whole_context | 0値の疑似欠損 | 画像ファイル: target_distribution.png パス: data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/reports/figures/target_distribution.png | retrieval_fallback | 0 | 0 |
| 11 | table_calculation | Gender=Male、Country=India、target=2 | 特筆すべきは、テクノロジースタートアップ領域に特化した求人プラットフォームである「Built In」のデータにおいて、最高水準の給与が345,000ドルに達している点である | retrieval_fallback | 0 | 0 |
| 12 | fallback_bm25_llm | 5,775,000円 | Slide 1 最終分析報告書 定期預金契約有無予測・説明可能性分析プロジェクト 甲 京橋信用ソリューションズ株式会社 リスク管理部 与信モデル統括課 乙 株式会社データアステル データサイエンス部 報告日 2025年11月11日 | retrieval_fallback | 0 | 0 |
| 13 | table_calculation | 1526 | 追加データ取得（イベント、拠点、移動履歴等）を行う場合は、スコープ・工数に影響するため早めに要求の可否を決定してください（変更管理: T19／MS7） | retrieval_fallback | 0 | 0 |
| 14 | fallback_bm25_llm | アサインされていない | Slide 1 最終分析報告書 従業員離職要因分析および離職リスク検知 初期分析 株式会社青葉バイオメディカル機器 人事本部 人材戦略部 プロジェクト期間：2025年6月23日 ～ 2025年7月28日（5週間） 契約形態：Time and Materials 目的変数：Attrition（従業員離職） 735行 × | retrieval_fallback | 0 | 0 |
| 15 | fallback_bm25_llm | MINAMINO、SHR、AYM | PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソース配分を確定してください | retrieval_fallback | 0 | 0 |
| 16 | fallback_bm25_llm | 43日 | ERIのデータでは現状の日本市場の最高学歴分布が学士号100%として扱われているものの、実務的な採用現場、特に実務経験が不足している新卒・若手層においては、学生時代におけるデータサイエンス関連の専門的な研究活動そのものが、就職や転職活動において | retrieval_fallback | 0 | 0 |
| 17 | document_whole_context | 未連絡 | ## Functions \| name \| lineno \| args \| docstring \| \| --- \| --- \| --- \| --- \| \| build_pipeline \| 19 \| X, task_type, random_state, model_type, model_params \| \| 凡例: | retrieval_fallback | 0 | 0 |
| 18 | fallback_bm25_llm | 3 | data\\train.csv の内容確認、カラム定義確認および品質診断 Outcome を目的変数とした分類分析 0値、外れ値およびスケーリング要否を含む前処理方針の比較検討 ベースラインモデルおよび複数候補モデルの性能比較 評価結果の可視化および解釈 業務活用に向けた示唆整理 最終報告書を含む成果物一式の作成 本業務 | retrieval_fallback | 0 | 0 |
| 19 | fallback_bm25_llm | 渡辺 遥 | ## 1. 当事者 ### 1.1 甲 会社名：株式会社青嶺不動産アセットマネジメント 部署名：資産運用本部 レジデンシャル戦略部 主担当者：前田 美咲（部長） ### 1.2 乙 会社名：株式会社データアステル 部署名：データサイエンス部 ### 1.3 実施体制 乙の主たる実施体制は以下のとおりとする | retrieval_fallback | 0 | 0 |
| 20 | fallback_bm25_llm | T09、T10、T11、T12 | 次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください | retrieval_fallback | 0 | 0 |
| 21 | table_calculation | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | Slide 1 最終分析報告書 従業員離職要因分析および離職リスク検知 初期分析 株式会社青葉バイオメディカル機器 人事本部 人材戦略部 プロジェクト期間：2025年6月23日 ～ 2025年7月28日（5週間） 契約形態：Time and Materials 目的変数：Attrition（従業員離職） 735行 × | retrieval_fallback | 0 | 0 |
| 22 | code_reading | season | Notebook: 01_eda_old.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. | retrieval_fallback | 0 | 0 |
| 23 | format_extraction | 見込金額（税込）: 4,675,000 JPY | 留意点 「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください） | retrieval_fallback | 0 | 0 |
| 24 | code_reading | Attr7 | Notebook: 01_eda.ipynb Cell 2: markdown ## 固定EDA計画 1. データ読み込みと基本確認 2. 列型・記述統計の確認 3. 欠損率の集計と可視化 4. 数値列の分布確認 5. カテゴリ列の主要分布確認 6. 目的変数の分布と偏り確認 7. 数値特徴量の相関確認 8. 日付列の | retrieval_fallback | 0 | 0 |
| 25 | document_whole_context | 1. データ理解・EDA | Slide 2 1. 背景 株式会社東都人材プラットフォーム 人事戦略部 人材データ活用室では、報酬分析・公平性確認・人材活用支援の高度化に向け、個人属性と収入クラスの関係を定量的に把握し、業務判断に活用できる分析基盤の整備が求められている | retrieval_fallback | 0 | 0 |
| 26 | table_calculation | train_0077、train_0216、train_0242、train_0722 | 要注意（ガバナンス） 監査証跡: 目的変数定義、前処理スクリプト、評価条件、モデルパラメータ、成果物版数は必ず成果物に記載のうえ保管してください | retrieval_fallback | 0 | 0 |
| 27 | document_whole_context | 0.010301 | 医療法人社団 蒼泉会 ひがし丘総合病院 最終分析報告書 医療費関連の価格帯分類と要因分析プロジェクト 契約期間: 2025-07-08 ～ 2025-08-05（5週間） 対象データ: data¥train.csv \| 1,600件・8列・欠損0件 目的変数: charges（価格帯 0/1/2 の3クラス分類） 最終 | retrieval_fallback | 0 | 0 |
| 28 | code_reading | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 | ### 4.3. 伝統的製造業の適応事例：トヨタ自動車の採用戦略 日本の基幹産業である製造業が、どのようにデータサイエンティストを処遇しようと試みているかを示す具体的な事例として、トヨタ自動車（またはその100%出資IT子会社）の採用条件が挙げられる | retrieval_fallback | 0 | 0 |
| 29 | document_whole_context | 3年間 | 契約締結日：2025-04-03 ### 甲 医療法人社団 蒼樹会 みなみ野女性医療センター 医療情報・品質改善推進室 主担当者：林 さくら 室長 署名：________________________ ### 乙 株式会社データアステル データサイエンス部 署名：________________________ ## | retrieval_fallback | 0 | 0 |

## 注意点

- valid正解はプロンプトには入れていない。正解は実行後の評価だけに使った。
- `わかりません` または空回答の場合は、検索上位根拠から本文行を選んでフォールバックした。
- 不明回答をなくす実験なので、精度よりも提出時の空振り回避を優先している。
- APIキーは `.apikey` から読み込み、成果物には保存しない。

## 結論

このno-unknown方針は採用しない。

理由は、`わかりません` を避けるための検索フォールバックが26件発生し、その多くが質問に対する回答ではなく、検索上位文書の本文断片になったためである。validの完全一致は1件、正解含有は2件に留まり、EDA024の通常LLM方針より悪化した。

したがって、根拠が不足している場合に `わかりません` を許す方針の方が、誤答を強制的に出すより安全である。今後は `わかりません` を単純に禁止するのではなく、route別の根拠作成、表計算、書式抽出、差分比較を改善して `わかりません` が自然に減る方向を優先する。
