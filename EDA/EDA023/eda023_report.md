# EDA023: validローカルRAG診断

## 目的

test提出前にvalid 30問でRAGを検証し、検索失敗と回答抽出・計算失敗を分けて確認する。

## 出力

- diagnosis: `EDA/EDA023/tables/valid_local_rag_diagnosis.csv`
- route_summary: `EDA/EDA023/tables/valid_route_summary.csv`
- contexts: `EDA/EDA023/contexts`

## 実行設定

- top_k: 8
- max_answer_chars: 900
- LLM API: 未使用

## 全体指標

凡例: `metric` は診断指標、`value` は値を表します。

| metric | value |
| --- | --- |
| valid_question_count | 30 |
| exact_match_count | 0 |
| contains_gold_count | 0 |
| answer_in_topk_context_count | 5 |
| avg_token_recall | 0.0229 |

## route別診断

凡例: `route` は質問ルート、`question_count` はvalid質問数、`exact_match_count` は正規化完全一致数、`contains_gold_count` は予測文に正解が含まれた件数、`answer_in_topk_context_count` は上位検索根拠に正解文字列が含まれた件数、`avg_token_recall` は正解語句トークンの回収率平均です。

| route | question_count | exact_match_count | contains_gold_count | answer_in_topk_context_count | avg_token_recall |
| --- | --- | --- | --- | --- | --- |
| code_reading | 4 | 0 | 0 | 0 | 0.0237 |
| diff_check | 1 | 0 | 0 | 0 | 0.0714 |
| document_whole_context | 7 | 0 | 0 | 3 | 0.0429 |
| fallback_bm25_llm | 8 | 0 | 0 | 2 | 0.0 |
| format_extraction | 2 | 0 | 0 | 0 | 0.0833 |
| image_ocr | 1 | 0 | 0 | 0 | 0.0 |
| table_calculation | 7 | 0 | 0 | 0 | 0.0079 |

## failure_type別件数

凡例: `failure_type` は失敗分類、`count` は該当件数を表します。

| failure_type | count |
| --- | --- |
| answer_extraction_or_calculation_failed | 5 |
| near_source_but_missing_answer | 20 |
| retrieval_failed | 5 |

## 質問別サンプル

凡例: `index` はvalid質問番号、`route` は処理ルート、`gold_answer` は正解、`predicted_answer` はローカルRAG回答、`failure_type` は診断分類です。

| index | route | gold_answer | predicted_answer | failure_type |
| --- | --- | --- | --- | --- |
| 0 | format_extraction | hr、weekday、weathersit、temp | 株式会社青潮モビリティサービス（以下「甲」という。）と株式会社データアステル（以下「乙」という。）は、モビリティ需要予測分析プロジェクトに関し、以下のとおりデータ分析業務委託契約（以下「本契約」という。）を締結する。、株式会社青潮モビリティ | near_source_but_missing_answer |
| 1 | image_ocr | 20日 | The prompt asks to convert the image into text for RAG search. It specifically mentions "valid index=1: KSSのfigure_06.pn | near_source_but_missing_answer |
| 2 | document_whole_context | Recall | 欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損 | near_source_but_missing_answer |
| 3 | table_calculation | 4,394,250円 | キックオフ時点では、分析結果ではなく前提整理の完了を優先してください。 | retrieval_failed |
| 4 | code_reading | hist_gradient_boosting | クライアント：株式会社青嶺不動産アセットマネジメント | near_source_but_missing_answer |
| 5 | document_whole_context | 対象外（契約明記） | プロジェクト目的とスコープ | answer_extraction_or_calculation_failed |
| 6 | table_calculation | Gender=Male、disease=1、Age=68で抽出されたデータに対する平均 / ALP | 欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損 | near_source_but_missing_answer |
| 7 | table_calculation | 32歳 | ベースライン（T01）から段階的にクラスバランスや特徴量拡張、閾値調整を行い、T04（閾値チューニング済み線形モデル）が最も高い f1_macro を示した（f1_macro = 0.7329671168078127）。このことは、現データ | near_source_but_missing_answer |
| 8 | fallback_bm25_llm | 1,168,750円 | 前項の見込金額は170時間を前提とした見込額であり、契約総額を固定するものではない。最終請求額は、実績工数に時間単価を乗じ、これに消費税を加算した金額とする。 | near_source_but_missing_answer |
| 9 | diff_check | QAレビューア：池田 直哉 → 小林 直樹 | 株式会社青嶺不動産アセットマネジメント 様、案件フォルダ内の一部保護ファイルについて、社内規定に基づく共通ルールでパスワードを導出できるようにする。、追加対応は、別途合意が成立した範囲について、time_and_materials条件に基づ | near_source_but_missing_answer |
| 10 | document_whole_context | 0値の疑似欠損 | ファイル名: 医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf 元パス: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_ | near_source_but_missing_answer |
| 11 | table_calculation | Gender=Male、Country=India、target=2 | グローバルスタンダードの技術資格: クラウドコンピューティングの浸透に伴い、AWS（Amazon Web Services）、Microsoft Azure、GCP（Google Cloud Platform）などのクラウド環境における認定 | near_source_but_missing_answer |
| 12 | fallback_bm25_llm | 5,775,000円 | 京橋信用ソリューションズ株式会社 | near_source_but_missing_answer |
| 13 | table_calculation | 1526 | 「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得 | near_source_but_missing_answer |
| 14 | fallback_bm25_llm | アサインされていない | 株式会社青葉バイオメディカル機器 | near_source_but_missing_answer |
| 15 | fallback_bm25_llm | MINAMINO、SHR、AYM | open actions = 7（prior_state.open_action_count = 7）。PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソー | near_source_but_missing_answer |
| 16 | fallback_bm25_llm | 43日 | The prompt asks to convert the image into text for RAG search. It specifically mentions "valid index=1: KSSのfigure_06.pn | retrieval_failed |
| 17 | document_whole_context | 未連絡 | \| カラム名 \| データ型 \| 説明 \| データの例 \| | answer_extraction_or_calculation_failed |
| 18 | fallback_bm25_llm | 3 | 本業務の対象データ、前提および制約は以下のとおりとする。 | answer_extraction_or_calculation_failed |
| 19 | fallback_bm25_llm | 渡辺 遥 | 株式会社青嶺不動産アセットマネジメント（以下「甲」という。）と株式会社データアステル（以下「乙」という。）は、不動産売買価格分析 初期診断プロジェクトに関し、以下のとおりデータ分析業務委託契約（以下「本契約」という。）を締結する。 | answer_extraction_or_calculation_failed |
| 20 | fallback_bm25_llm | T09、T10、T11、T12 | 次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください。、\| 第2〜3週 \| \| 探索的分析、セグメント別不良率確認、仮説整理 \| 中間レビュー1 \|、キックオフ時点では、分析結果 | retrieval_failed |
| 21 | table_calculation | Attrition = No、Gender = Female、MaritalStatus = Single、EducationField = Human Resources | 株式会社青葉バイオメディカル機器 | near_source_but_missing_answer |
| 22 | code_reading | season | 9. 観察結果サマリ | retrieval_failed |
| 23 | format_extraction | 見込金額（税込）: 4,675,000 JPY | 「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得 | near_source_but_missing_answer |
| 24 | code_reading | Attr7 | ax.set_title("数値特徴量の相関ヒートマップ（先頭20列）") | near_source_but_missing_answer |
| 25 | document_whole_context | 1. データ理解・EDA | color="#1F1F1F" style="color:#1F1F1F">これらの複数の信頼性の高い情報源の中間値を統合すると、2025年における米国のデータサイエンティストの平均的な基本給（Headline base salary）は約 | near_source_but_missing_answer |
| 26 | table_calculation | train_0077、train_0216、train_0242、train_0722 | 監査証跡: 目的変数定義、前処理スクリプト、評価条件、モデルパラメータ、成果物版数は必ず成果物に記載のうえ保管してください。現在 run_summary/metrics は出力済みですが、会議決定事項（M01/M02）の議事録反映が必要です | retrieval_failed |
| 27 | document_whole_context | 0.010301 | 欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損 | near_source_but_missing_answer |
| 28 | code_reading | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 | 世界的な自動車メーカーであり、莫大な資本を持つ企業であっても、採用初年度のベースラインは500万円台からスタートし、経験や実力に応じて1,000万円の大台に届くという設計である。同社は、トヨタグループのグローバルな事業を最上流（企画・構想段 | near_source_but_missing_answer |
| 29 | document_whole_context | 3年間 | 医療法人社団 蒼樹会 みなみ野女性医療センター | answer_extraction_or_calculation_failed |

## 所見

- EDA021で見えたタグ混入は、回答生成前のHTML/Markdown除去で抑制できる。
- ただし、正解が検索上位contextに存在していても、差額計算、書式抽出、表集計は本文行抽出だけでは外しやすい。
- 次はroute別に、表計算、書式抽出、差分比較、コード/Notebook値抽出の専用処理をvalidで改善する。
