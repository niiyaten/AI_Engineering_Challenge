# EDA総括

## このファイルの目的

このファイルは、`EDA001` から `EDA052` までの内容を、RAGパイプライン構築の観点で整理した総括メモです。  
各EDAの詳細なログ、表、個別レポートは各 `EDA/EDAXXX/` に残し、ここでは「何が分かったか」「どの部品ができたか」「次に何を実装すべきか」を中心にまとめます。

本プロジェクトの本質は、共有ドライブ内の多様なファイル群を、LLMや計算処理が扱える中間表現へ変換し、質問ごとに適切な処理へ振り分けることです。  
単純な全文検索だけでは、表計算、書式、画像、差分、特定文書指定の質問に対応しきれないため、検索前の質問解析と処理ルーティングを重視します。

## フェーズ別整理

| フェーズ | 対応EDA | やったこと | 主な成果物 | 現在の位置づけ |
|---|---|---|---|---|
| データ棚卸し | EDA001 | 共有ドライブ、質問、提出形式の全体確認 | `file_inventory.csv`、質問タイプ集計 | データ全体像の把握 |
| ファイル抽出 | EDA002, EDA004 | テキスト系、Office、PDFを文書本文・チャンクへ変換 | `extracted_documents.jsonl`、`text_chunks.jsonl`、`sheet_summary.csv` | RAGと直接処理の入力基盤 |
| 検索・提出ベースライン | EDA003, EDA005 | BM25検索、ルール回答、お試し提出 | 検索ログ、`eda005_bm25_template_submission.zip` | 提出形式確認済み、スコアは低い |
| LLM入力診断 | EDA006, EDA007, EDA008 | valid診断、LLM用Markdown生成、OpenRouter接続確認 | `valid_llm_readiness.csv`、LLM context、APIログ | LLM接続は可能だが、根拠選択が重要 |
| 質問解析・文書単位化 | EDA009, EDA010 | 文書名・フォルダ名を使った検索補正、文書全体コンテキスト化 | guided検索比較、whole document contexts | 文書指定質問の根拠選択を改善 |
| パイプライン棚卸し | EDA011 | 文書LLM候補、表処理、書式、画像、差分、全問ルーティング、回答方針、提出用チェックリストを統合整理 | `EDA/EDA011/tables/`、`EDA/EDA011/reports/` | 提出用コードへ落とすための設計台帳 |
| Word再現Markdown化 | EDA012 | Word文書をMarkdownと再現用JSONへ変換 | `data/processed/share/**/*.docx.md`、`.structure.json` | LLM入力と書式再現の前処理 |
| embedding入力標準化 | EDA013 | Markdown/JSON/画像を検索用JSONLへ正規化し、優先画像をOpenRouter Visionで説明文化 | `data/processed/embedding/embedding_records.jsonl` | BM25、ベクトル検索、LLM入力の共通中間データ |
| 表データ前処理 | EDA014 | Excel/CSV/TSVをMarkdown、構造JSON、計算用CSVへ変換 | `*.xlsx.md`、`*.structure.json`、`*.sheets/*.csv`、`*.data.csv` | 表計算質問の入力基盤 |
| PowerPoint前処理 | EDA015 | PowerPointをスライド単位Markdown、構造JSON、画像assetsへ変換 | `*.pptx.md`、`*.pptx.structure.json`、`*.pptx.assets/*` | 提案書、報告書、座席表、差分確認の入力基盤 |
| PDF前処理 | EDA016 | PDFをページ単位Markdown、構造JSONへ変換 | `*.pdf.md`、`*.pdf.structure.json` | 会議録、報告資料、報告書のページ単位検索基盤 |
| コード前処理 | EDA017, EDA018 | PythonとNotebookを静的解析し、Markdown/JSON/assetsへ変換 | `*.py.md`、`*.ipynb.md`、`*.structure.json`、`*.assets/*` | コード読解、図生成元、分析手順確認の入力基盤 |
| 既存Markdown確認 | EDA019 | 既存Markdownを品質確認し、そのままprocessedへ保存 | `*.md`、`*.md.structure.json` | 既存文書の直接利用基盤 |
| 統合JSONL | EDA020 | EDA012からEDA019の前処理結果を検索用JSONLへ統合 | `data/processed/embedding/embedding_records.jsonl` | BM25、embedding、LLM入力の共通検索基盤 |
| test RAG出力 | EDA021 | test 100問へローカルBM25 RAGを実行し、提出形式zipを作成 | `predictions.csv`、`eda021_local_rag_submission.zip` | 提出形式確認済みの初期RAG候補 |
| LLM回答生成 | EDA022 | EDA021の検索contextをOpenRouterのLLMへ渡し、LLM回答とhybrid提出zipを作成 | `llm_answer_log.csv`、`eda022_llm_hybrid_submission.zip` | LLM接続済み、根拠不足時の課題も確認 |
| valid診断 | EDA023 | valid 30問にローカルRAGを実行し、正解との比較で失敗要因を分類 | `valid_local_rag_diagnosis.csv`、`valid_route_summary.csv` | test提出前の評価基準として使用 |
| LLM全問試行 | EDA024 | valid 30問すべてをOpenRouter LLMへ送信した | `valid_llm_answer_log.csv`、`eda024_report.md` | 120Bは全件429、20Bで30問完走 |
| no-unknown検証 | EDA025 | valid 30問で `わかりません` を禁止し、失敗時に検索根拠へフォールバックした | `valid_no_unknown_answer_log.csv`、`eda025_report.md` | 誤答断片が増えたため不採用 |
| test LLM提出候補 | EDA026, EDA027 | no-unknown test案を不採用にし、`わかりません` 許容方針でtest zipを作成 | `eda027_openrouter_openai_gpt_oss_20b_free_unknown_allowed_submission.zip`、`eda027_report.md` | OpenRouter 20B再実行で一部回答、ただし多数不明 |
| valid失敗分類 | EDA028 | EDA024のvalid回答を正解・不明・誤答に分類し、route別の次アクションを整理 | `eda024_valid_answer_classification.csv`、`eda028_report.md` | route別改善の優先順位付け |
| 失敗原因データ種別診断 | EDA029 | EDA028の正解以外を対象に、必要データ種別、失敗領域、次修正を分類 | `eda024_failure_source_diagnosis.csv`、`eda029_report.md` | どの前処理を直すべきかの判断材料 |
| 表計算ルーター実計算 | EDA030 | valid表計算7件をサブタイプ分類し、CSV、Excelフィルター、PivotTable相当、文書横断金額を実計算 | `table_valid_calculation_results.csv`、`eda030_report.md` | 表系質問はローカル計算してLLMへ結果を渡す方針 |
| 表計算結果のLLM整形 | EDA031 | EDA030の計算結果をOpenRouter LLMへ渡し、提出用の短い回答へ整形できるか検証 | `llm_table_answer_log.csv`、`eda031_report.md` | 表計算routeではLLMを計算役でなく整形役にする方針 |
| 構造化候補の一括生成 | EDA032 | EDA029の正解以外25件に対して、Markdown、structure JSON、Notebook出力、CSV、metricsから回答候補を生成 | `structured_candidate_answers.csv`、`eda032_report.md` | route別ローカル処理で24/25まで候補化 |
| 構造化候補のLLM整形 | EDA033 | EDA032候補をOpenRouter LLMへ渡し、valid goldとの類似を評価 | `llm_structured_candidate_answer_log.csv`、`eda033_report.md` | LLM整形後も24/25。候補品質が支配的 |
| 提出候補統合 | EDA034 | valid改善結果を統合し、testは短く明確な20B回答だけを採用 | `valid_pipeline_answer_log.csv`、`test_pipeline_answer_log.csv`、`eda034_structured_safe_submission.zip` | 安全側のtest提出候補。非不明回答17件 |
| test不明回答のroute別削減 | EDA035 | EDA034で残ったtest不明回答に、書式、表、CSV、コード、スケジュール系のローカル処理を追加適用 | `test_unknown_reduction_log.csv`、`eda035_unknown_reduction_submission.zip`、`eda035_report.md` | 非不明回答を31件まで増加。ただし未対応routeは残る |
| test構造化候補のLLM確認 | EDA036 | EDA035の構造化候補をOpenRouterへ送り、testで短答化できるか確認 | `test_openrouter_structured_answer_log.csv`、`eda036_openrouter_structured_test_submission.zip`、`eda036_report.md` | 未回答2件を追加採用。非不明回答33件 |
| 未対応routeの一括候補生成 | EDA037 | diff、document、table、format、fallbackの未対応routeへローカル候補生成を追加 | `test_unhandled_route_candidates.csv`、`eda037_unhandled_routes_submission.zip`、`eda037_report.md` | 安全側に4件追加採用。候補ログを次段LLM入力に使う |

凡例: `フェーズ` はEDAを機能単位にまとめた区分、`対応EDA` はその区分に含めた実験番号、`やったこと` は検証内容、`主な成果物` は後続で参照するファイル、`現在の位置づけ` は最終パイプライン内での役割を表します。

## 現在の結論

最終構成は、以下の流れを基本方針にします。

1. 共有ドライブをファイル形式別に抽出する。
2. テキストチャンク、文書全体Markdown、表データ、書式情報、画像候補、ファイルメタデータとして中間データ化する。
3. 質問から対象プロジェクト、対象文書名、求める情報タイプ、必要な処理を解析する。
4. 質問に応じて、文書全体LLM、表計算、書式抽出、画像/OCR、差分確認、コード読解、BM25+LLMへ振り分ける。
5. 必要な根拠抽出または計算を行う。
6. LLMには、検索で雑に集めたチャンクではなく、絞り込んだ文書・根拠・計算結果を渡す。
7. `predictions.csv` を作成する。

特に重要なのは、検索前の質問解析です。  
EDA008では、`提案書内で` と聞かれている質問に対して報告資料のチャンクが上位に入り、LLMが `f1_macro、AUC-ROC、top10% precision` と回答しました。正解は `Recall` でした。  
これはLLM単体の問題というより、LLMに渡した根拠がずれていたことが原因です。

EDA009では、質問内の `提案書` を使って対象文書を優先した結果、`valid_002` のTop1根拠を `報告資料_2025-09-02.docx` から `00.提案/提案書.pptx` に変更できました。  
EDA010では、その提案書全体に正解 `Recall` が含まれることも確認できました。

## 主要な数値

| 項目 | 結果 |
|---|---:|
| 共有ドライブ内ファイル数 | 405 |
| 案件数 | 10 |
| valid質問数 | 30 |
| test質問数 | 100 |
| EDA002抽出成功 | 199 |
| EDA002チャンク数 | 1230 |
| EDA004抽出成功 | 117 |
| EDA004抽出失敗 | 2 |
| EDA004チャンク数 | 1311 |
| EDA005お試し提出スコア | -0.7666666666666667 |
| EDA006 ready_for_llm | 10 |
| EDA006 Top5正解語句ヒット率 | 0.3333 |
| EDA010 文書指定document_qa対象 | 8 |
| EDA010 文書全体に正解語句あり | 4 |
| EDA011 文書全体LLM候補 | 4 |
| EDA011 画像ファイル数 | 54 |
| EDA011 ルーティング対象質問数 | 130 |
| EDA012 Word変換成功 | 46 |
| EDA012 Word変換失敗 | 1 |
| EDA013 embedding標準レコード数 | 936 |
| EDA013 画像レコード数 | 55 |
| EDA013 OpenRouter画像toテキスト成功 | 4 |
| EDA014 Excel/CSV/TSV変換成功 | 50 |
| EDA014 Excel/CSV/TSV変換失敗 | 2 |
| EDA015 PowerPoint変換成功 | 25 |
| EDA015 PowerPoint変換失敗 | 1 |
| EDA016 PDF変換成功 | 28 |
| EDA016 PDF抽出ページ数 | 220 |
| EDA017 Python変換成功 | 100 |
| EDA018 Notebook変換成功 | 11 |
| EDA019 Markdown品質OK | 31 |
| EDA020 統合JSONLレコード数 | 2484 |
| EDA020 空テキストレコード数 | 0 |
| EDA020 record_id重複数 | 0 |
| EDA021 test予測行数 | 100 |
| EDA021 空回答数 | 0 |
| EDA021 提出zip内ファイル | predictions.csv |
| EDA021提出スコア | -1 |
| EDA022 LLM試行質問数 | 5 |
| EDA022 LLM成功数 | 5 |
| EDA022 hybrid予測行数 | 100 |
| EDA022 hybrid空回答数 | 0 |
| EDA023 valid完全一致数 | 0 |
| EDA023 valid正解含有数 | 0 |
| EDA023 valid正解がTopK根拠に含まれる件数 | 5 |
| EDA024 GPT-OSS-120B試行数 | 30 |
| EDA024 GPT-OSS-120B HTTP 429件数 | 30 |
| EDA024 GPT-OSS-20B試行数 | 30 |
| EDA024 GPT-OSS-20B HTTP 200件数 | 30 |
| EDA024 GPT-OSS-20B valid完全一致数 | 5 |
| EDA024 GPT-OSS-20B valid正解含有数 | 7 |
| EDA025 HTTP 200件数 | 4 |
| EDA025 HTTP 429件数 | 26 |
| EDA025 valid完全一致数 | 1 |
| EDA025 valid正解含有数 | 2 |
| EDA025 検索フォールバック件数 | 26 |
| EDA027 test質問数 | 100 |
| EDA027 Gemini HTTP 200件数 | 3 |
| EDA027 Gemini HTTP 429件数 | 92 |
| EDA027 Gemini HTTP 500件数 | 3 |
| EDA027 Gemini timeout件数 | 2 |
| EDA027 Gemini 不明回答数 | 100 |
| EDA027 OpenRouter 20B再実行 HTTP 200件数 | 53 |
| EDA027 OpenRouter 20B再実行 HTTP 429件数 | 47 |
| EDA027 OpenRouter 20B再実行 不明回答数 | 83 |
| EDA027 OpenRouter 20B再実行 非不明回答数 | 17 |
| EDA027 提出zip内ファイル | predictions.csv |
| EDA027 OpenRouter無料モデル取得数 | 24 |
| EDA027 モデル疎通確認数 | 8 |
| EDA027 モデル疎通確認HTTP 429件数 | 8 |
| EDA028 EDA024完全一致数 | 5 |
| EDA028 EDA024近似正解数 | 5 |
| EDA028 EDA024完全一致または近似正解数 | 10 |
| EDA028 EDA024不明回答数 | 14 |
| EDA028 EDA024明確な誤答数 | 6 |
| EDA028 route別最優先アクション | table_calculationのローカル計算 |
| EDA029 診断対象数 | 25 |
| EDA029 required_source_type最多 | pptx 6件 |
| EDA029 failure_area最多 | calculation 7件 |
| EDA029 next_fix最多 | improve_project_document_targeting 6件 |
| EDA029 CSV系修正対象 | csv 3件 |
| EDA029 Excel系修正対象 | xlsx 2件、xlsx_pivot 2件 |
| EDA030 表計算valid対象数 | 7 |
| EDA030 ローカル計算gold一致または包含一致数 | 6 |
| EDA030 要確認数 | 1 |
| EDA031 GPT-OSS-120B HTTP 429件数 | 7 |
| EDA031 GPT-OSS-20B HTTP 200件数 | 7 |
| EDA031 LLM回答取得数 | 7 |
| EDA031 gold類似回答数 | 6 |
| EDA031 EDA030計算回答類似数 | 7 |
| EDA032 対象数 | 25 |
| EDA032 候補生成数 | 25 |
| EDA032 gold類似候補数 | 24 |
| EDA033 LLM回答取得数 | 25 |
| EDA033 GPT-OSS-120B HTTP 200件数 | 1 |
| EDA033 GPT-OSS-120B HTTP 429件数 | 24 |
| EDA033 GPT-OSS-20B HTTP 200件数 | 24 |
| EDA033 LLM回答gold類似数 | 24 |
| EDA034 valid gold類似数 | 29 |
| EDA034 test非不明回答数 | 17 |
| EDA034 test不明回答数 | 83 |
| EDA035 追加採用回答数 | 14 |
| EDA035 test非不明回答数 | 31 |
| EDA035 test不明回答数 | 69 |
| EDA036 OpenRouter対象件数 | 38 |
| EDA036 GPT-OSS-20B HTTP 200件数 | 38 |
| EDA036 GPT-OSS-120B HTTP 429件数 | 6 |
| EDA036 LLM回答取得件数 | 32 |
| EDA036 LLM追加採用件数 | 2 |
| EDA036 test非不明回答数 | 33 |
| EDA036 test不明回答数 | 67 |
| EDA037 追加採用回答数 | 4 |
| EDA037 test非不明回答数 | 37 |
| EDA037 test不明回答数 | 63 |

凡例: `項目` はEDA001〜019で得た代表的な集計指標、`結果` は件数、割合、または提出スコアを表します。

## ルーティング結果

| split | route | question_count |
|---|---|---:|
| valid | fallback_bm25_llm | 8 |
| valid | table_calculation | 7 |
| valid | document_whole_context | 7 |
| valid | code_reading | 4 |
| valid | format_extraction | 2 |
| valid | image_ocr | 1 |
| valid | diff_check | 1 |
| test | fallback_bm25_llm | 37 |
| test | table_calculation | 17 |
| test | format_extraction | 17 |
| test | document_whole_context | 14 |
| test | diff_check | 9 |
| test | code_reading | 3 |
| test | image_ocr | 3 |

凡例: `split` はvalidまたはtest、`route` は質問から推定した処理ルート、`question_count` は該当質問数を表します。

## EDA別の扱い

| EDA | 整理後の扱い | 補足 |
|---|---|---|
| EDA001 | 残す | 全体棚卸しの起点 |
| EDA002 | 残す | テキスト系抽出の本体 |
| EDA003 | EDA005/006の前段として参照 | EDA002だけでの検索限界確認 |
| EDA004 | 残す | Office/PDF抽出の本体 |
| EDA005 | 提出形式確認として残す | お試し提出スコア `-0.7666666666666667` |
| EDA006 | LLM前診断として残す | ready_for_llm分類の起点 |
| EDA007 | EDA008の入力生成として残す | チャンクTopK型LLM context |
| EDA008 | LLM接続検証として残す | gpt-oss-20b:freeでAPI成功、根拠ずれも確認 |
| EDA009 | 残す | 質問解析つき検索の起点 |
| EDA010 | 残す | 文書全体コンテキスト化の起点 |
| EDA011 | 残す | 軽量棚卸し群を統合したパイプライン棚卸し |
| EDA012 | 残す | Word文書のLLM可読Markdown化と書式再現用JSON化 |
| EDA013 | 残す | embedding/BM25/LLM共通の標準レコード作成と画像toテキスト検証 |
| EDA014 | 残す | Excel/CSV/TSVのMarkdown/JSON/計算用CSV化 |
| EDA015 | 残す | PowerPointのスライド単位Markdown/JSON/assets化 |
| EDA016 | 残す | PDFのページ単位Markdown/JSON化 |
| EDA017 | 残す | PythonのAST静的解析とMarkdown/JSON化 |
| EDA018 | 残す | Notebookのセル単位Markdown/JSON/assets化 |
| EDA019 | 残す | 既存Markdownの品質確認とprocessed保存 |
| EDA020 | 残す | 全形式の前処理成果物を統合した検索用JSONL |
| EDA021 | 残す | test 100問のローカルBM25 RAGと提出形式zip作成 |
| EDA022 | 残す | OpenRouter LLM回答生成とEDA021フォールバック付きhybrid提出zip作成 |
| EDA023 | 残す | validで検索失敗と回答抽出・計算失敗を切り分ける診断 |
| EDA024 | 残す | 120Bは上流レート制限で全件429、20Bではvalid 30問を完走 |
| EDA025 | 不採用方針として残す | `わかりません` 禁止は検索断片の誤答を増やし、EDA024より悪化 |
| EDA026 | 不採用スクリプトとして残す | EDA025の結果を受け、no-unknown test提出候補としては使わない |
| EDA027 | 残す | OpenRouter 20B再実行でHTTP 200が53件まで回復したが、まだ不明回答83件 |
| EDA028 | 残す | EDA024のvalid失敗をroute別に分類し、次アクションを整理 |
| EDA029 | 残す | 不明・誤答・近似正解の原因データ種別と次修正を整理 |
| EDA030 | 残す | 表計算valid 7件をローカル計算し、6件でgold一致または包含一致 |
| EDA031 | 残す | EDA030計算結果をOpenRouter 20Bで整形し、7件すべて計算回答に近い回答を取得 |
| EDA032 | 残す | EDA029の25件を一括で構造化データから候補化し、24件でgold類似 |
| EDA033 | 残す | EDA032候補をLLM整形し、24件でgold類似。LLMより候補生成品質が重要と確認 |
| EDA034 | 残す | valid統合で29/30をgold類似にし、testは安全側に17件だけ非不明回答として採用 |
| EDA035 | 残す | EDA034のtest不明83件にroute別ローカル処理を追加し、14件を新規採用 |
| EDA036 | 残す | EDA035候補38件をOpenRouterで確認し、未回答2件だけ追加採用 |
| EDA037 | 残す | EDA036で残った未対応routeにローカル候補生成を追加し、安全側に4件採用 |

凡例: `EDA` は実験番号、`整理後の扱い` は今後参照する際の位置づけ、`補足` は残す理由または統合先を表します。


## EDA012の要点

EDA012では、`data/raw/share` 配下のWord文書を、`data/processed/share` 配下に同じディレクトリ構成でMarkdown化しました。太字、斜体、下線、文字色、ハイライト、段落スタイル、表、画像メタデータは、LLM向けMarkdownだけでなく `.structure.json` にも保存しています。

対象Wordファイルは 47 件、変換成功は 46 件、変換失敗は 1 件でした。出力は `data/processed/share/**/*.docx.md` と `data/processed/share/**/*.docx.structure.json` です。失敗した1件は、既知のパスワード付き契約書 `契約書_pw-kaede20250902.docx` で、`BadZipFile` として扱われました。

## EDA013の要点

EDA013では、EDA012で作成したWord由来のMarkdown/構造JSONと、共有ドライブ内の画像ファイルを、`data/processed/embedding/embedding_records.jsonl` に統合しました。レコード種別は `metadata`、`paragraph`、`table`、`image` です。JSON構造をそのままembeddingするのではなく、`text_for_embedding` に検索用の自然文・Markdown断片を置き、出典、ブロック番号、見出し、書式、画像パスなどは `metadata` に保持します。

総レコード数は 936 件で、内訳は `paragraph` 757 件、`table` 78 件、`metadata` 46 件、`image` 55 件でした。画像55件のうち優先4件をOpenRouterの無料Visionモデル `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` に送り、画像説明テキストを取得しました。`figure_06.png` では、タイトル、軸、凡例、件数線、目的変数平均線の説明が得られています。

ただし、無料Visionモデルの応答はJSON厳守ではなく、推論過程に近い英文説明が混ざりました。検索用テキストとしては有用ですが、数値を厳密に構造化して表計算のように使うには、次段階でプロンプト改善または後処理が必要です。

## EDA014の要点

EDA014では、Excel、CSV、TSVをMarkdown、構造JSON、計算用CSVへ変換しました。対象52件のうち50件が成功し、失敗は2件でした。失敗した2件は、Office一時ファイル `~$スケジュール.xlsx` と、既知の鍵付きまたは破損扱いの `スケジュール.xlsx` です。

CSV/TSVは、カラム、行数、型、欠損、統計量、サンプル行をJSONとMarkdownへ保存し、UTF-8の正規化CSVも出力しました。Excelは、シートごとのCSV、シート名、使用範囲、数式、書式、結合、非表示行列、グラフメタデータを保存しました。

この段階では、表データの前処理基盤ができた状態です。`table_calculation` 質問へ実回答するには、EDA014の出力またはraw表データをpandas/openpyxlで読み、質問ごとの計算処理を実装する必要があります。

## EDA015の要点

EDA015では、PowerPointをスライド単位Markdown、構造JSON、抽出画像assetsへ変換しました。対象26件のうち25件が成功し、失敗はOffice一時ファイル `~$提案書.pptx` の1件だけでした。

成功したPowerPointから、386スライド、4455テキスト図形、79表、3画像、6グラフを抽出しました。JSONには、スライド番号、図形名、図形種別、位置、サイズ、テキストrun書式、表、画像パス、グラフメタデータ、ノートを保存しています。

この段階では、提案書、報告書、座席表、版違い比較に使うスライド単位の入力基盤ができた状態です。次は、PowerPoint由来のMarkdown/JSONを `embedding_records.jsonl` に統合する必要があります。

## EDA016の要点

EDA016では、PDF 28件をページ単位Markdownと構造JSONへ変換しました。全件成功し、合計220ページ、抽出文字数は53211文字でした。

JSONには、ページ番号、抽出テキスト、文字数、ページサイズ、回転、PDFメタデータを保存しています。PDFは表や段組みの抽出順が崩れる可能性があるため、ページ番号付きで根拠追跡できるようにしました。このEDAでは画像レンダリングやOCRは行っていません。

## EDA017の要点

EDA017では、Pythonファイル100件を実行せずに静的解析し、Markdownと構造JSONへ変換しました。全件成功し、合計11520行、362関数、1086件のファイル入出力候補を抽出しました。

JSONには、import、関数、クラス、関数呼び出し、ファイル入出力らしき呼び出し、main guard有無を保存しています。Markdownには、概要表とコード全文を保存しています。これにより、コード読解質問や、図・表がどの処理で生成されたかを追いやすくなりました。

## EDA018の要点

EDA018では、Notebook 11件を実行せずにセル単位Markdownと構造JSONへ変換しました。全件成功し、合計211セル、105コードセル、106 Markdownセル、202出力、54画像assetsを抽出しました。

JSONには、セル順、セル種別、実行番号、source、出力テキスト、画像assetsを保存しています。Notebook出力画像は `*.ipynb.assets/*` に保存しました。これにより、分析手順、コード、出力、図をまとめて検索できる状態になりました。

## EDA019の要点

EDA019では、既存Markdown 31件について、空ファイル、置換文字、NUL文字、極端に短い本文などを簡易確認し、問題がなかったためそのまま `data/processed/share` へ保存しました。全31件がOKで、警告とエラーはありませんでした。

既存Markdownは再変換せず、本文はそのまま保持し、見出し、リンク数、文字数、行数、品質フラグを `*.md.structure.json` に保存しています。

## EDA020の要点

EDA020では、EDA012からEDA019までで作成した `*.structure.json` と、EDA013で得た画像レコードを、`data/processed/embedding/embedding_records.jsonl` に統合しました。docx段落・表、Excel/CSV/TSV、PowerPointスライド、PDFページ、Python関数・コードチャンク、Notebookセル、Markdownチャンクを、同じ検索レコード形式で扱えるようにしています。

総レコード数は 2484 件で、空テキストレコード数は 0 件、`record_id` 重複は 0 件、統合エラーは 0 件でした。これにより、BM25、embedding、LLM入力の前段で共通利用する検索基盤ができました。

## EDA021の要点

EDA021では、EDA020の統合JSONLを使って、test 100問に対するローカルBM25 RAGを実行しました。LLM APIは使わず、検索上位レコードから本文らしい行を抽出するテンプレート回答で `predictions.csv` を作成しています。

出力は `EDA/EDA021/predictions/predictions.csv` と `EDA/EDA021/predictions/eda021_local_rag_submission.zip` です。提出形式として、予測行数100、空回答0、index順0から99、zip内ファイルは `predictions.csv` のみであることを確認しました。

このzipを提出した結果、SIGNATEスコアは `-1` でした。形式確認としては通りましたが、ローカルBM25検索と本文行抽出だけでは回答品質が不十分です。表計算、書式抽出、差分比較、画像数値抽出、LLMによる最終回答生成は、route別に専用実装する必要があります。

## EDA022の要点

EDA022では、EDA021の検索ログをLLM用contextとして整形し、OpenRouterへ送って最終回答を生成する実験を行いました。APIキーは `.apikey` から読み込み、成果物には保存しません。モデル候補は `openai/gpt-oss-120b:free`、`openai/gpt-oss-20b:free`、`qwen/qwen3-next-80b-a3b-instruct:free` の順で試し、失敗または空回答の場合は次モデルへフォールバックします。

今回は先頭5問で検証し、5問すべてHTTP 200でLLM回答を取得できました。最終採用モデルは `openai/gpt-oss-120b:free` が1件、`openai/gpt-oss-20b:free` が4件でした。出力は `EDA/EDA022/tables/llm_answer_log.csv`、`EDA/EDA022/predictions/predictions_hybrid.csv`、`EDA/EDA022/predictions/eda022_llm_hybrid_submission.zip` です。hybrid zipは、LLM成功分だけEDA021回答を置き換え、未処理分はEDA021回答へフォールバックするため、100行の提出形式を維持します。

一方で、差分、書式、表計算の質問では、LLMが「わかりません」または保守的な回答を返しました。これはLLMの能力不足というより、EDA021の検索contextだけではold/new差分、セル色、太字、表計算に必要な構造情報が十分に渡っていないためです。

## EDA023の要点

EDA023では、いきなりtestへ提出するのではなく、valid 30問でローカルRAGを診断しました。EDA020の統合JSONLに対してBM25検索を行い、EDA021相当の抽出型回答を作成したうえで、正解との比較、正解がTopK根拠に含まれるか、route別の失敗傾向を確認しています。LLM APIは使っていません。

結果は、完全一致0件、予測文に正解を含む件数0件、正解文字列がTopK根拠に含まれる件数5件でした。これは、EDA021の `-1` スコアと整合しており、現在のローカルBM25 + 抽出型回答は、提出前のベースラインとしても不十分です。

ただし、タグ混入は回答前にHTML/Markdownを除去することで抑制できることも確認しました。問題の中心は、検索対象文書の絞り込み、表計算、書式抽出、差分比較、コード/Notebook出力値の取得をroute別に実装していない点です。

## EDA024の要点

EDA024では、EDA023の結果を受けて、valid 30問すべてをOpenRouter LLMに投げる比較実験を作成しました。valid正解はプロンプトに含めず、質問、推定route、BM25上位根拠だけをLLMへ渡す設計です。

当初は `openai/gpt-oss-120b:free` を使いましたが、30問すべてHTTP 429でした。短い疎通確認プロンプトでも同じ429となり、OpenRouterのエラー本文では `openai/gpt-oss-120b:free is temporarily rate-limited upstream` と返っていました。したがって、120B無料モデルの回答品質はこの時点では評価できていません。

代替として `openai/gpt-oss-20b:free` で再実行したところ、valid 30問すべてHTTP 200で完走しました。完全一致は5件、予測文に正解を含む件数は7件でした。EDA023のローカルRAG完全一致0件からは改善しましたが、`table_calculation`、`format_extraction`、`diff_check`、`code_reading` は依然として弱く、LLM単体ではなくroute別の根拠整形と計算処理が必要です。

## EDA025の要点

EDA025では、EDA024で `わかりません` が残ったことを受け、valid 30問で不明回答を禁止するno-unknown方針を検証しました。プロンプトで `わかりません` を避けるよう指示し、LLM回答が空または不明回答になった場合は検索上位根拠から本文行を選んでフォールバックしています。valid正解はプロンプトには含めず、評価にのみ使用しました。

結果は、HTTP 200が4件、HTTP 429が26件、完全一致1件、正解含有2件でした。検索フォールバックが26件発生し、その多くは質問に対する回答ではなく、検索上位文書の本文断片でした。EDA024のGPT-OSS-20B結果である完全一致5件、正解含有7件より悪化しています。

したがって、`わかりません` を機械的に禁止する方針は採用しません。根拠が不足している場合は `わかりません` を許し、誤答を強制しない方が安全です。今後は不明回答を禁止するのではなく、表計算、書式抽出、差分比較、コード読解、文書全体コンテキストの整形を改善して、不明回答が自然に減る方向を優先します。

## EDA027の要点

EDA027では、EDA025の反省を踏まえて、`わかりません` を許す従来方針でtest 100問のLLM回答生成と提出形式zip作成を行いました。API失敗または空回答の場合は、提出CSVの空欄を避けるため `わかりません` を入れますが、EDA025で悪化した検索断片フォールバックは使いません。

OpenRouter 20Bでは100問中99問がHTTP 429になったため、同じEDA027スクリプトにGemini経路を追加し、`.apikey` の `gemini` キーを使って `gemini-3.5-flash` でも再実行しました。

出力は `EDA/EDA027/predictions/predictions.csv` と `EDA/EDA027/predictions/eda027_gemini_unknown_allowed_submission.zip` です。zip内ファイルは `predictions.csv` のみで、提出形式としての作成は完了しています。

ただし、Geminiでも100問中92問がHTTP 429、3問がHTTP 500、2問がtimeoutでした。429の主なエラーは `You do not have enough quota to make this request.` であり、無料枠またはプロジェクト上限の問題と判断します。HTTP 200だった3問も `わかりません` または空回答補完で、最終的な予測は100件すべて `わかりません` です。したがって、このzipは実提出候補としては採用しません。test全問を無料LLMに一括送信するより、validでroute別処理を改善し、LLMに渡す件数と根拠を絞る方針を優先します。

その後、OpenRouter 20Bを再実行したところ、100問中53問がHTTP 200、47問がHTTP 429になりました。最終回答は83件が `わかりません`、17件が非 `わかりません` です。出力は `EDA/EDA027/predictions/eda027_openrouter_openai_gpt_oss_20b_free_unknown_allowed_submission.zip` です。前回よりは大きく改善しましたが、まだ多数が不明回答であり、非不明回答にも根拠ずれや計算誤りがあり得るため、即時の本命提出候補ではなく、無料枠回復時の到達点として扱います。

追加で、同じEDA027配下の `eda027_model_probe.py` により、OpenRouterの無料モデル一覧取得と1問だけのモデル疎通確認を行いました。無料モデルは24件取得できましたが、確認した8モデルはすべてHTTP 429でした。`openai/gpt-oss-120b:free`、`openai/gpt-oss-20b:free`、`qwen/qwen3-next-80b-a3b-instruct:free` も429で、エラーは上流レート制限または `free-models-per-day` の日次制限でした。

## EDA028の要点

EDA028では、EDA024のvalid 30問について、正解したもの、`わかりません` になったもの、間違ったものを質問系統ごとに分類しました。valid正解は分類評価にのみ使い、回答生成には使っていません。

全体では、完全一致5件、近似正解5件、不明回答14件、明確な誤答6件でした。近似正解には、`20` と `20日`、`¥5,775,000` と `5,775,000円`、`未連絡を表します。` と `未連絡` のように、単位、記号、余計な語を整えれば正解に近いものを含めています。

route別には、`document_whole_context` は7件中2件正解・2件近似正解、`fallback_bm25_llm` は8件中3件正解・2件近似正解でした。一方で、`table_calculation`、`format_extraction`、`diff_check`、`code_reading` は完全一致も近似正解もほぼ出ていません。したがって、次に優先するのは、LLMの再試行ではなく、`table_calculation` のローカル計算、`format_extraction` の書式JSON利用、`diff_check` の文書差分処理、`code_reading` のコード/Notebook検索改善です。

## EDA029の要点

EDA029では、EDA028で `correct` ではなかった25件を対象に、必要な元データ種別、失敗領域、次に直すべき処理を分類しました。

必要データ種別では、`pptx` 6件、`docx` 5件、`py_or_ipynb` 4件、`csv` 3件、`xlsx_pivot` 2件、`xlsx` 2件、`image` 2件、`pptx_or_docx_versions` 1件でした。したがって、CSVだけを見直せばよい状態ではありません。

失敗領域では、`calculation` が7件で最多でした。内訳はCSV計算3件、Excel/PivotTable系4件です。次いで、対象文書検索の改善が6件、最終回答整形が5件、コード/Notebookのファイル名指定検索と出力抽出が4件でした。

次にやるべきことは、まず表計算系を `csv`、`xlsx`、`xlsx_pivot`、複数文書横断集計に分けて実装することです。その次に、PowerPoint/Excel/Wordのstructure JSONから書式情報を直接読む処理、old/new比較、コード/Notebookの対象ファイル検索を進めます。

## EDA030とEDA031の要点

EDA030では、EDA029で `table_calculation` とされたvalid 7件を対象に、CSV、Excel AutoFilter、PivotTable相当の再計算、文書横断の消費税集計を実装しました。6件はgoldと一致または包含一致しました。残る1件は全案件の消費税総額で、文書から再構成した計算値が `4,384,250円`、valid goldが `4,394,250円` となり、10,000円差を要確認として記録しました。

EDA031では、EDA030の計算結果をOpenRouter LLMへ渡し、最終回答だけを返させました。`openai/gpt-oss-120b:free` は7件すべてHTTP 429でしたが、`openai/gpt-oss-20b:free` は7件すべてHTTP 200でした。LLM回答は7件すべてEDA030の計算回答に近く、gold類似は6件でした。goldと合わなかった1件はEDA030時点で計算値とgoldに差がある消費税総額です。

この結果から、表計算routeではLLMに計算を任せるより、ローカル計算で値を出し、LLMには回答表記の整形だけを任せる構成が妥当です。ただし、今回の20B回答は `、` を `,` に変えるなど軽い表記変更があるため、提出用ではLLMを通さずローカル計算結果をそのまま採用する選択も検討します。

## EDA032とEDA033の要点

EDA032では、EDA029で正解ではなかったvalid 25件に対して、構造化データから回答候補を一括生成しました。表計算はEDA030結果、書式はdocx/pptxのstructure JSON、コードとNotebookはMarkdown/structure JSONとraw CSV再計算、スケジュール系は`*.xlsx.sheets/*.csv`、文書系はprocessed Markdownとmetrics JSONを使いました。結果は25件すべて候補を生成し、gold類似は24件でした。

EDA033では、EDA032候補をOpenRouter LLMへ渡して提出用回答へ整形しました。`openai/gpt-oss-120b:free` は25件中1件だけHTTP 200、24件はHTTP 429でした。`openai/gpt-oss-20b:free` は残り24件すべてHTTP 200でした。LLM回答のgold類似は24件で、EDA032候補と同じ結果でした。

残った不一致は、引き続き `index=3` の全案件消費税総額です。文書から再構成した値は `4,384,250円`、valid goldは `4,394,250円` で、10,000円差の原因は未解決です。

この結果から、validで落ちていた多くの問題はLLM性能ではなく、LLMへ渡す前の候補生成不足が主因だと判断できます。提出用パイプラインでは、まずroute別にローカル候補を作り、LLMは必要な場合だけ整形役として使う方針が妥当です。

## EDA034とEDA035の要点

EDA034では、EDA024のvalid全体回答にEDA033の改善回答を上書きし、valid 30件中29件がgold類似となる統合ログを作成しました。test 100件については、EDA027のOpenRouter 20B回答のうち短く明確な17件だけを採用し、残り83件は `わかりません` とする安全側の提出候補zipを作成しました。EDA021のBM25抽出回答は会社名や文書冒頭の混入が多かったため、提出用では原則不採用としました。

EDA035では、EDA034で `わかりません` だった83件を対象に、validで効いた構造化候補生成をtestにも適用しました。追加した処理は、Wordの太字run抽出、Excelのオレンジ行抽出、青色セル合計、CSV再計算、コード内パラメータ抽出、metricsとコードの結合、スケジュールCSVの期間抽出、未完了ID抽出などです。

結果として14件を追加採用し、test 100件の非不明回答は17件から31件へ増えました。出力は `EDA/EDA035/tables/test_unknown_reduction_log.csv`、`EDA/EDA035/predictions/predictions.csv`、`EDA/EDA035/predictions/eda035_unknown_reduction_submission.zip` です。提出形式は100行、zip内ファイルは `predictions.csv` のみであることを確認しました。

一方で、`fallback_bm25_llm`、`diff_check`、`document_whole_context`、`xlsx_yellow_cell_context`、画像由来の計算、汎用的な表計算はまだ多く残っています。EDA035では、根拠が弱い候補や `needs_review=True` の候補は原則採用していないため、今後は残り69件をroute別にさらに処理する必要があります。

## EDA036の要点

EDA036では、EDA035で作ったExcel、Word、CSV、コード、スケジュール系の構造化候補をOpenRouterへ送り、testでもLLMが短い最終回答へ整形できるかを確認しました。対象は候補または根拠がある38件です。モデルは `openai/gpt-oss-20b:free` を優先し、失敗時だけ `openai/gpt-oss-120b:free` へフォールバックしました。

結果は、GPT-OSS-20Bが38件すべてHTTP 200、120Bフォールバックは6件HTTP 429でした。LLM回答が空でなかったものは32件です。ただし、既にEDA035で非 `わかりません` だった回答をLLMで上書きすると、長いWord抽出回答が途中で短く切られる例がありました。そのため提出候補では、EDA035で採用済みの回答は保持し、EDA035時点で `わかりません` だった行だけLLM回答で埋める方針にしました。

最終的に、EDA036で追加採用したのは2件です。`index=10` のAG_ratioヒストグラム最大カウントは `1473`、`index=15` の黄色セル文脈は `Country: Spain, 個数: 12.0` になりました。test 100件の非不明回答は31件から33件、不明回答は67件です。

## EDA037の要点

EDA037では、EDA036後も残っていた未対応routeをまとめて対象にし、差分、文書全体、表計算、書式、fallback検索のローカル候補生成を追加しました。具体的には、old/new Markdownの差分行抽出、文書内見出し・ページ検索、Excel黄色セルの行列文脈復元、ヒストグラム再計算、スケジュールCSVフィルター、顧客データ相関計算、本文行検索を実装しました。

ただし、差分系と汎用本文検索は誤答混入リスクが高いため、`needs_review=True` の候補は提出回答へ採用していません。安全側に採用したのは4件で、test 100件の非不明回答は33件から37件、不明回答は63件になりました。

EDA038では、差分比較routeを個別処理しました。旧版/新版のPowerPoint、Notebook、Excelスケジュールを質問ごとにペアリングし、Markdown差分を作成してOpenRouterで短答化を試しました。対象9件のうち、EDA037時点で `わかりません` だった6件を追加採用し、test 100件の非不明回答は43件です。なお、一部モデルはHTTP 429または無料利用不可のHTTP 404となったため、ローカル差分候補を採用した行もあります。

EDA039では、書式抽出routeを個別処理しました。Excelの `styled_cells`、PowerPoint/Wordのtext runから、黄色ハイライト、太字、下線、イタリックなどのレコードを作成し、OpenRouterで短答化を試しました。しかし、画像として埋め込まれたハイライトや、構造JSONに残らない書式があり、追加採用は0件でした。test 100件の非不明回答は43件のままです。

EDA040では、表計算routeを個別処理しました。TPヒストグラムの10ビン再計算、青潮スケジュールのバッファ工数合計、かえで案件の非Markdownファイル由来ID数カウントをローカル計算で追加採用しました。OpenRouterへ表文脈を渡した回帰係数系やAPR判定系は、contentが空または根拠不足で採用できませんでした。test 100件の非不明回答は46件です。

EDA041では、文書横断・本文検索routeを個別処理しました。`fallback_bm25_llm` と `document_whole_context` の36件を対象に、対象プロジェクト、資料種別、略称、IDを使ってMarkdown、CSV、structure JSONから根拠文脈を抽出しました。ユーザー確認によりコンペ用データとしてOpenRouter送信が許可されたため、OpenRouter 20Bで36件すべて短答化しました。HTTP 200は36件で、3件を追加採用し、test 100件の非不明回答は49件になりました。

EDA042では、EDA041でHTTP 200にもかかわらず `content` が空だった33件を再試行しました。原因確認のためraw responseを保存し、`max_tokens` を900へ増やし、JSON形式の短答を強制しました。最初にreasoningを無効化したところGPT-OSS-20B側でHTTP 400となり、raw responseから「reasoning必須」であることを確認しました。その後reasoningを有効化して再実行した結果、18件は `finish_reason=stop` でcontentあり、15件は `finish_reason=length` でcontent空のままでした。`情報不足` や `見つかりません` などの不明相当回答は採用対象から除外し、10件を追加採用しました。test 100件の非不明回答は59件です。

EDA043では、EDA042で残った `finish_reason=length` かつcontent空の15件を対象に、EDA041の根拠文脈を質問語に強く一致する行だけへ圧縮して再試行しました。`max_tokens` は1500に上げ、reasoningは有効のままにしました。圧縮により14件は `finish_reason=stop` となり、1件だけ `length` が残りました。`不明` などの不明相当回答は採用対象から除外し、12件を追加採用しました。test 100件の非不明回答は71件です。

EDA044では、EDA043後に残った `format_extraction`、`table_calculation`、`image_ocr` の16件をまとめて対象にしました。Excel/PPTX/DOCXのstructure JSONから書式候補、CSV/Markdownから表計算候補、画像/グラフ周辺のメタデータと元データ候補を作成し、ローカル計算またはOpenRouter 20Bで短答化しました。9件を追加採用し、test 100件の非不明回答は80件です。ただし、`存在しない`、`[]`、`該当箇所はありません` のような否定回答も含まれるため、提出前に要確認です。`eda044_format_table_image_submission.zip` の提出スコアは `-0.3` でした。

EDA045では、EDA044後に残った20件を対象に、まだ専用routeを作れていない質問種別を棚卸ししました。新route候補は9種類で、件数が多いものは `meeting_action_status_lookup` 4件、`model_formula_recompute` 3件、`contract_alias_contact_lookup` 2件、`cross_project_contract_aggregation` 2件です。次は、画像や座席表よりも、会議/アクション横断、モデル係数再計算、契約横断集計のようにローカル再現性が高いrouteを優先します。

追加採用した主な回答は、Excel黄色セルの文脈復元2件、会議録の太字・下線・イタリック抽出1件、顧客データの負の相関カラム1件です。差分routeや汎用検索routeにも候補は生成できていますが、提出へ反映するにはLLM整形または個別根拠確認が必要です。

## 未解決の重要点

- EDA023のvalid診断で、ローカルBM25 + 抽出型回答は完全一致0件であり、test提出前にvalidでroute別改善を確認する必要があると分かりました。
- EDA024でGPT-OSS-120B全問回答を試しましたが、全件HTTP 429で未成功でした。代替のGPT-OSS-20Bでは30問完走し、完全一致5件でした。
- EDA025で `わかりません` 禁止を試しましたが、検索フォールバック由来の誤答断片が増え、完全一致1件、正解含有2件に悪化しました。
- EDA027で `わかりません` 許容のtest提出形式zipをOpenRouter 20Bで再作成したところ、HTTP 200は53件、非不明回答は17件でした。
- EDA027の追加モデル疎通確認では、無料モデル24件を取得できたものの、確認した8モデルはすべてHTTP 429でした。
- EDA028でEDA024のvalid回答を分類したところ、完全一致5件、近似正解5件、不明14件、明確な誤答6件でした。
- EDA029で正解以外25件の原因を分類したところ、CSVだけでなく、PowerPoint、Word、Excel、PivotTable、コード/Notebook、画像、差分処理がそれぞれ改善対象だと分かりました。
- EDA030で表計算7件をローカル計算したところ6件がgold一致または包含一致し、EDA031でその計算結果をOpenRouter 20Bへ渡すと7件すべて計算回答に近い最終回答が得られました。
- EDA032/EDA033で、正解ではなかった25件のうち24件は構造化データ候補またはLLM整形後回答がgoldに近くなりました。残る1件は消費税総額の既知差分です。
- EDA034でEDA024のvalid全体回答にEDA033の構造化改善を上書きしたところ、valid 30件中29件がgold類似となりました。test提出候補は誤答リスクを抑えるため、EDA027の20B回答で短く明確な17件のみ採用し、残り83件は `わかりません` としました。
- EDA035でEDA034のtest不明83件にroute別ローカル処理を追加適用し、14件を追加採用しました。test非不明回答は31件、不明回答は69件です。
- EDA036でEDA035の構造化候補38件をOpenRouterへ送り、未回答2件を追加採用しました。既存の非不明回答はLLMで上書きしない方が安全です。
- EDA037で未対応routeにローカル候補生成を追加し、安全側に4件を追加採用しました。差分系と汎用検索系は候補生成まで進みましたが、提出採用には追加確認が必要です。
- EDA022でOpenRouter LLM接続は成功しましたが、検索contextだけでは差分、書式、表計算の質問に十分答えられないことが確認できました。
- EDA021のローカルBM25抽出型RAGは提出形式としては通りましたが、提出スコアは `-1` であり、正答率向上にはroute別の専用処理が必要です。
- 表計算ルートは、EDA030でvalid 7件の個別計算まで進み、EDA031で計算結果をLLM整形できることも確認しました。次はvalid専用分岐を汎用ルーター化する必要があります。
- 書式、コード、差分、文書指定、スケジュール系は、EDA032でvalidの候補生成が可能と確認しました。次はtestへ適用できる汎用ルールに落とす必要があります。
- 画像/OCRルートは、優先4画像のOpenRouter Vision説明文までは取得できましたが、数値抽出の構造化は未完成です。
- 差分ルートは、版違い候補の整理とPowerPoint構造化までは進みましたが、段落・スライド単位の比較実装が必要です。
- 文書全体LLMルートは有望ですが、無料モデルのレート制限と長文入力に注意が必要です。
- PDFはページ単位テキスト化済みですが、表や段組みの抽出順は必要に応じて個別確認が必要です。
- Python/Notebookは静的解析済みですが、コードは実行していないため、実際の出力値は既存出力やrawデータから確認する必要があります。
- `02.計画/スケジュール.xlsx` は暗号化Officeファイルで、現時点ではパスワード不明です。周辺文書から補完する方針です。

## 次に優先する作業

次は、EDAを増やすよりも、提出用パイプラインに直結する部品を実装する段階です。

1. EDA023を評価基準にし、validで改善を確認してからtest提出する。
2. `table_calculation` routeのvalid 7件から、EDA014のCSV/JSONを使ってpandas/openpyxlで実回答を出す。
3. `format_extraction` routeのvalid/test質問に対して、既存の書式メタデータで答えられるか確認する。
4. `diff_check` route向けに、old/new文書のスライド・段落単位比較を実装する。
5. GPT-OSS-120Bはレート制限が解消したタイミングでEDA024を再実行し、validで実測する。
6. EDA025の結果を踏まえ、根拠不足時は `わかりません` を許しつつ、route別根拠整形で不明回答を減らす。
7. EDA027の結果を踏まえ、無料枠でtest全問を一括LLM回答する運用は避ける。
8. EDA028の分類結果をもとに、まず `table_calculation`、次に `format_extraction`、`diff_check`、`code_reading` を潰す。
9. EDA029の原因分類をもとに、CSVだけでなくExcel/PivotTable、PPTX/Word書式、old/new差分、py/ipynb検索を個別に改善する。
10. EDA022/EDA024のLLM接続を、route別処理とLLM最終回答生成を呼ぶ提出用パイプラインへ発展させる。

## 参照する主な成果物

| パス | 内容 |
|---|---|
| `EDA/EDA001/tables/file_inventory.csv` | 共有ドライブ内の全ファイル一覧 |
| `EDA/EDA002/texts/extracted_documents.jsonl` | テキスト系ファイルの文書単位抽出 |
| `EDA/EDA002/texts/text_chunks.jsonl` | テキスト系ファイルの検索用チャンク |
| `EDA/EDA004/texts/extracted_documents.jsonl` | Office/PDFの文書単位抽出 |
| `EDA/EDA004/texts/text_chunks.jsonl` | Office/PDFの検索用チャンク |
| `EDA/EDA004/tables/sheet_summary.csv` | Excelシートの範囲、フィルター、数式、書式概要 |
| `EDA/EDA004/tables/extraction_errors.csv` | 抽出できなかったファイル一覧 |
| `EDA/EDA009/tables/valid_guided_retrieval_comparison.csv` | 通常BM25と質問解析つきBM25の比較 |
| `EDA/EDA010/contexts/` | 文書全体LLMコンテキスト |
| `EDA/EDA011/tables/table_question_inventory.csv` | 表計算質問の棚卸し |
| `EDA/EDA011/tables/tabular_document_inventory.csv` | CSV/XLSX文書の棚卸し |
| `EDA/EDA011/tables/format_question_inventory.csv` | 書式質問の棚卸し |
| `EDA/EDA011/tables/image_file_inventory.csv` | 画像ファイル棚卸し |
| `EDA/EDA011/tables/diff_question_inventory.csv` | 差分質問の棚卸し |
| `EDA/EDA011/tables/question_routes.csv` | valid/test全問の処理ルート |
| `EDA/EDA011/tables/submission_pipeline_checklist.csv` | 提出用パイプライン設計チェックリスト |
| `EDA/EDA012/tables/docx_markdown_conversion_log.csv` | WordからMarkdown/JSONへの変換ログ |
| `EDA/EDA013/tables/embedding_record_summary.csv` | embedding標準レコードの種別別集計 |
| `EDA/EDA013/tables/image_to_text_calls.csv` | OpenRouter Visionの画像toテキスト呼び出し結果 |
| `EDA/EDA014/tables/tabular_conversion_log.csv` | Excel/CSV/TSV前処理の変換ログ |
| `EDA/EDA015/tables/pptx_conversion_log.csv` | PowerPoint前処理の変換ログ |
| `EDA/EDA016/tables/pdf_conversion_log.csv` | PDF前処理の変換ログ |
| `EDA/EDA017/tables/python_conversion_log.csv` | Python前処理の変換ログ |
| `EDA/EDA018/tables/notebook_conversion_log.csv` | Notebook前処理の変換ログ |
| `EDA/EDA019/tables/markdown_quality_log.csv` | Markdown品質確認ログ |
| `EDA/EDA020/tables/embedding_record_summary.csv` | 統合JSONLのrecord_type、file_type別集計 |
| `EDA/EDA020/tables/integration_errors.csv` | 統合時のエラー一覧 |
| `EDA/EDA021/tables/test_rag_retrieval.csv` | test 100問の検索上位レコードと回答ログ |
| `EDA/EDA021/predictions/eda021_local_rag_submission.zip` | ローカルBM25 RAGで作成した提出形式zip |
| `EDA/EDA022/tables/llm_answer_log.csv` | OpenRouter LLM回答生成の結果ログ |
| `EDA/EDA022/predictions/eda022_llm_hybrid_submission.zip` | LLM成功分とEDA021フォールバックを統合した提出形式zip |
| `EDA/EDA023/tables/valid_local_rag_diagnosis.csv` | valid 30問の予測、正解、検索根拠、失敗分類 |
| `EDA/EDA023/tables/valid_route_summary.csv` | route別のvalid診断集計 |
| `EDA/EDA024/tables/valid_llm_answer_log.csv` | valid 30問をOpenRouter LLMへ試行した結果ログ |
| `EDA/EDA024/prompts/` | valid正解を含まないLLM用プロンプト確認ファイル |
| `EDA/EDA025/tables/valid_no_unknown_answer_log.csv` | `わかりません` 禁止方針のvalid回答ログ |
| `EDA/EDA025/eda025_report.md` | no-unknown方針を不採用にした理由と診断指標 |
| `EDA/EDA027/tables/test_unknown_allowed_answer_log.csv` | `わかりません` 許容方針でtest 100問を試した回答ログ |
| `EDA/EDA027/tables/model_probe_log.csv` | 120B、20B、Qwenなど無料モデル8件の疎通確認ログ |
| `EDA/EDA027/tables/openrouter_free_models.csv` | OpenRouterから取得した現在の無料モデル一覧 |
| `EDA/EDA027/predictions/eda027_openrouter_openai_gpt_oss_20b_free_unknown_allowed_submission.zip` | OpenRouter 20B再実行で作成した提出形式zip |
| `EDA/EDA027/predictions/eda027_gemini_unknown_allowed_submission.zip` | Geminiで `わかりません` 許容方針により作成した提出形式zip。提出非推奨 |
| `EDA/EDA027/eda027_report.md` | EDA027のOpenRouter 20B再実行結果と提出判断 |
| `EDA/EDA027/eda027_model_probe_report.md` | EDA027内の無料モデル疎通確認レポート |
| `EDA/EDA028/tables/eda024_valid_answer_classification.csv` | EDA024 valid回答の質問別分類 |
| `EDA/EDA028/tables/eda024_route_classification_summary.csv` | EDA024 valid回答のroute別分類集計 |
| `EDA/EDA028/tables/eda024_next_action_summary.csv` | EDA024失敗を潰すための次アクション別件数 |
| `EDA/EDA028/eda028_report.md` | EDA024の正解・不明・誤答分類レポート |
| `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv` | EDA024の正解以外について必要データ種別と失敗領域を分類した表 |
| `EDA/EDA029/tables/source_type_summary.csv` | 正解以外の質問で必要なデータ種別別件数 |
| `EDA/EDA029/tables/next_fix_summary.csv` | 次に修正すべき処理別件数 |
| `EDA/EDA029/eda029_report.md` | 不明・誤答・近似正解の原因データ種別診断レポート |
| `EDA/EDA030/tables/table_valid_calculation_results.csv` | valid表計算7件の計算結果とgold照合 |
| `EDA/EDA030/tables/table_subtype_summary.csv` | 表計算サブタイプ別の件数と一致件数 |
| `EDA/EDA030/tables/cross_project_tax_details.csv` | 全案件消費税集計の案件別内訳 |
| `EDA/EDA030/eda030_report.md` | 表計算ルーター分類と実計算のレポート |
| `EDA/EDA031/tables/llm_table_answer_log.csv` | EDA030計算結果をOpenRouter LLMへ渡した回答ログ |
| `EDA/EDA031/tables/llm_table_attempt_log.csv` | 120B、20Bなどモデル別の試行ステータスログ |
| `EDA/EDA031/prompts/valid_XXX_prompt.json` | goldを含めないLLM入力プロンプト |
| `EDA/EDA031/eda031_report.md` | 表計算結果のLLM整形検証レポート |
| `EDA/EDA032/tables/structured_candidate_answers.csv` | 正解ではなかったvalid 25件の構造化データ由来回答候補 |
| `EDA/EDA032/tables/structured_candidate_route_summary.csv` | EDA032候補生成のroute別集計 |
| `EDA/EDA032/eda032_report.md` | 構造化データ候補生成の一括検証レポート |
| `EDA/EDA033/tables/llm_structured_candidate_answer_log.csv` | EDA032候補をLLM整形した回答ログ |
| `EDA/EDA033/tables/llm_structured_candidate_attempt_log.csv` | EDA033のモデル別HTTPステータスログ |
| `EDA/EDA033/prompts/valid_XXX_prompt.json` | goldを含めないEDA033用LLMプロンプト |
| `EDA/EDA033/eda033_report.md` | 構造化候補のLLM整形評価レポート |
| `EDA/EDA034/tables/valid_pipeline_answer_log.csv` | EDA024全体回答にEDA033改善を上書きしたvalid統合評価ログ |
| `EDA/EDA034/tables/test_pipeline_answer_log.csv` | test 100問の提出用回答候補、採用元、信頼度ログ |
| `EDA/EDA034/predictions/eda034_structured_safe_submission.zip` | EDA034の安全側提出候補zip。非不明回答17件、残りは `わかりません` |
| `EDA/EDA034/eda034_report.md` | valid統合結果、test提出候補の内訳、次アクション整理 |
| `EDA/EDA035/tables/test_unknown_reduction_log.csv` | EDA034のtest不明回答に対するroute別ローカル候補と採用可否ログ |
| `EDA/EDA035/predictions/eda035_unknown_reduction_submission.zip` | EDA035の提出形式zip。非不明回答31件、残りは `わかりません` |
| `EDA/EDA035/eda035_report.md` | test不明回答削減の採用内訳、未対応route、次アクション整理 |
| `EDA/EDA036/tables/test_openrouter_structured_answer_log.csv` | EDA035構造化候補をOpenRouterへ送ったtest回答ログ |
| `EDA/EDA036/tables/test_openrouter_structured_attempt_log.csv` | OpenRouterのモデル別試行ログ |
| `EDA/EDA036/predictions/eda036_openrouter_structured_test_submission.zip` | EDA036の提出形式zip。非不明回答33件、残りは `わかりません` |
| `EDA/EDA036/eda036_report.md` | test構造化候補のLLM確認結果、HTTP集計、採用方針 |
| `EDA/EDA037/tables/test_unhandled_route_candidates.csv` | EDA036で残った未対応routeへのローカル候補生成ログ |
| `EDA/EDA037/predictions/eda037_unhandled_routes_submission.zip` | EDA037の提出形式zip。非不明回答37件、残りは `わかりません` |
| `EDA/EDA037/eda037_report.md` | 未対応routeの候補生成、採用内訳、残課題の整理 |
| `EDA/EDA038/tables/test_diff_route_attempt_log.csv` | 差分比較routeの旧版/新版ペア、ローカル差分、OpenRouter試行、採用可否ログ |
| `EDA/EDA038/predictions/eda038_diff_route_submission.zip` | EDA038の提出形式zip。非不明回答43件、残りは `わかりません` |
| `EDA/EDA038/eda038_report.md` | 差分比較routeの個別処理結果、HTTP状態、未改善理由 |
| `EDA/EDA039/tables/test_format_route_attempt_log.csv` | 書式抽出routeのstructure JSON抽出レコード、OpenRouter試行、採用可否ログ |
| `EDA/EDA039/predictions/eda039_format_route_submission.zip` | EDA039の提出形式zip。非不明回答43件、残りは `わかりません` |
| `EDA/EDA039/eda039_report.md` | 書式抽出routeの個別処理結果。構造JSONだけでは追加採用0件 |
| `EDA/EDA040/tables/test_table_route_attempt_log.csv` | 表計算routeのローカル計算、表文脈LLM試行、採用可否ログ |
| `EDA/EDA040/predictions/eda040_table_route_submission.zip` | EDA040の提出形式zip。非不明回答46件、残りは `わかりません` |
| `EDA/EDA040/eda040_report.md` | 表計算routeの個別処理結果。ヒストグラム、バッファ工数、ID数を追加採用 |
| `EDA/EDA041/tables/test_document_search_route_attempt_log.csv` | 文書横断・本文検索routeの文脈抽出、OpenRouter 20B短答化、採用可否ログ |
| `EDA/EDA041/predictions/eda041_document_search_route_submission.zip` | EDA041の提出形式zip。非不明回答49件、残りは `わかりません` |
| `EDA/EDA041/eda041_report.md` | 文書横断・本文検索routeの結果。36件すべてHTTP 200、追加採用3件 |
| `EDA/EDA042/tables/test_document_retry_attempt_log.csv` | EDA041の空content 33件に対するOpenRouter再試行、finish_reason、messageキー、採用可否ログ |
| `EDA/EDA042/raw_responses/` | EDA042のOpenRouter raw response保存先 |
| `EDA/EDA042/predictions/eda042_document_retry_submission.zip` | EDA042の提出形式zip。非不明回答59件、残りは `わかりません` |
| `EDA/EDA042/eda042_report.md` | 空content再試行結果。reasoning必須、finish_reason=lengthの残存、追加採用10件 |
| `EDA/EDA043/tables/test_compressed_context_retry_attempt_log.csv` | EDA042で残ったlength空content 15件への圧縮文脈再試行ログ |
| `EDA/EDA043/raw_responses/` | EDA043のOpenRouter raw response保存先 |
| `EDA/EDA043/predictions/eda043_compressed_context_retry_submission.zip` | EDA043の提出形式zip。非不明回答71件、残りは `わかりません` |
| `EDA/EDA043/eda043_report.md` | 圧縮文脈再試行結果。15件中12件を追加採用 |
| `EDA/EDA044/tables/test_format_table_image_attempt_log.csv` | format/table/image route 16件のローカル候補、OpenRouter回答、採用可否ログ |
| `EDA/EDA044/raw_responses/` | EDA044のOpenRouter raw response保存先 |
| `EDA/EDA044/predictions/eda044_format_table_image_submission.zip` | EDA044の提出形式zip。非不明回答80件、残りは `わかりません` |
| `EDA/EDA044/eda044_report.md` | 書式、表計算、画像/グラフrouteの一括処理結果。9件追加採用、一部否定回答は要確認 |
| `EDA/EDA045/tables/remaining_route_gap_inventory.csv` | EDA044後の残件20件を新route候補へ分類した質問別台帳 |
| `EDA/EDA045/tables/remaining_route_gap_summary.csv` | 新route候補別の件数、対象ID、推奨アクション |
| `EDA/EDA045/eda045_report.md` | 未route化質問の棚卸しと次に作るべきroute整理 |
| `data/processed/embedding/embedding_records.jsonl` | BM25、ベクトル検索、LLM入力で共通利用する標準レコード |
| `data/processed/share/**/*.docx.md` | Word文書のLLM入力向けMarkdown |
| `data/processed/share/**/*.docx.structure.json` | Word再構成用の段落、run、表、画像メタデータ |
| `data/processed/share/**/*.xlsx.sheets/*.csv` | Excelシートを計算可能にしたCSV |
| `data/processed/share/**/*.pptx.md` | PowerPointスライド単位のLLM入力向けMarkdown |
| `data/processed/share/**/*.pptx.structure.json` | PowerPointのスライド、図形、表、画像、グラフメタデータ |
| `data/processed/share/**/*.pdf.md` | PDFページ単位のLLM入力向けMarkdown |
| `data/processed/share/**/*.py.structure.json` | Pythonのimport、関数、呼び出し、入出力候補 |
| `data/processed/share/**/*.ipynb.structure.json` | Notebookのセル、出力、画像assetsメタデータ |
| `data/processed/share/**/*.md.structure.json` | 既存Markdownの見出し、リンク、品質フラグ |

凡例: `パス` は参照対象のファイル位置、`内容` はそのファイルを確認すると分かる情報を表します。
## 追記: EDA046/EDA047

EDA046では、EDA045で整理した残件20件に対して9種類の新route候補を一括実装した。既存のEDA044提出候補をベースに、各質問のrouteごとに関連Markdown/CSV/structure JSONを圧縮抽出し、OpenRouter `openai/gpt-oss-20b:free` へ渡して回答候補を作成した。禁止語を含む回答は採用しないよう再判定し、最終的に追加採用は4件、test 100件中の非 `わかりません` は80件から84件になった。提出候補は `EDA/EDA046/predictions/eda046_all_remaining_routes_submission.zip` に保存した。

EDA047では、画像そのものを読む前処理として、`data/processed/share` 配下の画像56枚を台帳化し、優先上位8枚をOpenRouter Visionモデル `nvidia/nemotron-nano-12b-v2-vl:free` へ送信した。再実行と成功済み結果の保持を行い、8枚中5枚で検索用テキストを作成できた。結果は `EDA/EDA047/tables/image_asset_inventory.csv`、`EDA/EDA047/tables/image_to_text_results.csv`、`EDA/EDA047/image_to_text_records.jsonl`、`EDA/EDA047/image_to_text_context.md` に保存した。失敗した画像はOpenRouterのupstream timeoutなどでcontentが空だったため、raw responseを `EDA/EDA047/raw_responses/` に残した。

EDA048では、EDA046後も `わかりません` のまま残った16件について、なぜ個別routeを作っても解けなかったかを分類した。主因はLLMの短答化ではなく、会議録/アクションID、座席表、横断契約集計、回帰係数再計算など、LLMへ渡す前の構造化テーブル不足だった。診断結果は `EDA/EDA048/tables/remaining_unknown_diagnosis.csv`、集計は `EDA/EDA048/tables/remaining_unknown_family_summary.csv`、考察は `EDA/EDA048/eda048_report.md` に保存した。次は、会議録台帳、座席表座標テーブル、全案件契約正規化テーブルを優先する。

## 追記: EDA049/EDA050/EDA051

EDA049では、座席表 `座席表.pptx` をPPTX図形座標から構造化できるか検証した。structure JSON上はスライド全面の画像が1枚あり、人名・EXT・役割はtext shapeとして存在しなかったため、PPTX図形座標だけでは復元不能と判断した。OpenRouter Visionでも座席表の一部欠落が発生したため、不完全Vision結果は採用せず、検証用seedで15席の座席座標テーブルを作成した。出力は `EDA/EDA049/tables/seat_pptx_shape_audit.csv`、`seat_coordinate_table.csv`、`seat_question_probe.csv`。

EDA050では、`05.会議` 配下の会議録・報告資料をページ単位に分割し、meeting_id、日付、ページ、アクションID、コメント、チェックポイント候補を台帳化した。ページ166件、アクションID周辺213件、チェックポイント/タスク候補95件を作成した。一方、白峰・みなみ野などのPDF会議録は `[no text extracted]` が多く、14ファイルを `no_text_pdf_inventory.csv` に分離した。これらは次にPDFページ画像OCR/Visionが必要。

EDA051では、全案件横断集計の土台として、契約条件、役割/担当者、計画/リソース候補、案件マスターを作成した。契約11件、役割49件、リソース候補327件を抽出した。これにより、契約金額・着手金・担当体制の横断比較は可能になったが、APR-M3の略称定義、ESと内線の結合、鍵付き計画ファイル由来の工数はまだ追加整備が必要。

## 追記: EDA052

EDA052では、EDA050で `[no text extracted]` だったPDF 14件のうち、残件に直結する白峰信用リスク評価の `会議録_2025-07-15.pdf` と、蒼樹会 みなみ野女性医療センターの `会議録_2025-05-15.pdf` を優先し、PDFページをPNGにレンダリングしてOpenRouter VisionでOCRした。10ページを画像化し、4ページでOCRに成功した。候補として、白峰M04の進捗サマリはpage 2、みなみ野のA10は「index再実験の結果反映」と読む候補が得られた。結果は `EDA/EDA052/tables/pdf_page_vision_ocr_results.csv`、候補は `EDA/EDA052/tables/no_text_pdf_question_probe.csv` に保存した。

## 追記: EDA053

EDA053では、EDA046提出候補で残っていた `わかりません` 16件を対象に、EDA049とEDA052で作った回答候補を統合して置換できるかを確認した。安全版では、PDFページ画像OCRで根拠が取れた2件だけを採用し、残りの `わかりません` は16件から14件になった。採用した回答は、index 18の `2` と、index 93の `index再実験の結果反映`。

攻め版では、座席表の検証用seedから得た2件も追加採用し、残りの `わかりません` は12件になった。ただし、index 44の `高橋、池田` とindex 58の `7103` は、座席表画像からの完全な再抽出ではなく検証用seedに依存しているため、提出採用は要確認とした。

出力は `EDA/EDA053/tables/eda053_candidate_pool.csv`、`EDA/EDA053/tables/eda053_safe_adoption_log.csv`、`EDA/EDA053/tables/eda053_aggressive_adoption_log.csv` に保存した。提出形式zipは、安全版が `EDA/EDA053/predictions/eda053_safe_unknown_reduction_submission.zip`、攻め版が `EDA/EDA053/predictions/eda053_aggressive_unknown_reduction_submission.zip`。SIGNATEへの提出は行っていない。

## 追記: EDA054

EDA054では、EDA053 safe版で残った `わかりません` 14件を対象に、ローカル表データとOpenRouter短答化で追加採用できる候補を確認した。長文候補はOpenRouter `openai/gpt-oss-20b:free` へ送り、最終回答だけに整形できるかを試した。提出候補へ採用する条件は、`needs_review=False` かつ根拠が表データで確認できるものに限定した。

結果として、index 75は、みなみ野女性医療センターのスケジュールCSVからモデル構築・比較フェーズが2025-04-25開始であることを確認し、契約開始2025-04-03を第1週起点として `第4週` を採用した。index 96は、青葉与信マネジメントのマイルストーン表でMS2「データ理解完了」の関連タスクが `T05~T08` と明記されていたため、`T05、T06、T07、T08` を採用した。これによりsafe版の `わかりません` は14件から12件になった。

OpenRouterはHTTP 200で応答したが、index 52、62、80、95は `わかりません` または空回答だったため採用しなかった。残件は、グラフ数値、APR-M3横断集計、座席表、着手金最大案件のES内線、会議録コメント、運用条項、モデル比較差分、かえで工数、黄色セル意味、回帰係数再計算、スケジュール差分である。出力は `EDA/EDA054/tables/eda054_candidate_answers.csv`、`EDA/EDA054/tables/eda054_openrouter_attempts.csv`、提出候補は `EDA/EDA054/predictions/eda054_remaining_unknown_submission.zip` に保存した。SIGNATEへの提出は行っていない。

## 追記: EDA055

EDA055では、EDA054後に残った `わかりません` 12件のうち、LLMではなくローカル処理で再現しやすい3件を個別route化した。対象は、index 33のWord内グラフ値、index 80のExcel黄色セルの意味、index 83のExcel回帰係数再計算である。OpenRouterなどの外部APIは使わず、raw/processedファイルから値を取り直した。

index 33は、`基礎分析.docx` をdocx zipとして読み、`word/charts/chart2.xml` の1本目の系列から x=3 の値 `137.64768` を抽出した。index 80は、`train.xlsx.structure.json` の黄色セル `E1409` と、前方補完した `train.xlsx.sheets/Sheet1.csv` から、抽出条件 `Gender=Male、target=2、Age=40-44、Country=Spain`、集計内容 `個数=12` を採用した。index 83は、`train.xlsx.sheets/Sheet1.csv` の回帰係数を index=1770 の特徴量へ適用し、予測値 `0.38317` を採用した。

この結果、提出候補の `わかりません` は12件から9件になった。出力は `EDA/EDA055/tables/eda055_route_results.csv`、提出候補CSVは `EDA/EDA055/predictions/eda055_chart_format_formula_predictions.csv`、提出形式zipは `EDA/EDA055/predictions/eda055_chart_format_formula_submission.zip` に保存した。index 80は質問文ではSheet2とあるが、raw xlsxをopenpyxlで確認すると黄色セルは `Sheet1!E1409` の1件だけだったため、実ファイル上の黄色セルを優先して採用した。SIGNATEへの提出は行っていない。

## 追記: EDA056

EDA056では、EDA055後に残った `わかりません` 9件のうち、会議録コメント、運用条項、スケジュール差分の3件をローカル処理で確認した。EDA055の提出候補をベースに、raw docx、processed Markdown、processed CSVから根拠を取り直し、OpenRouterなどの外部APIは使わなかった。

index 49は、東都人材プラットフォームのraw Word会議録に含まれる `word/comments.xml` と `word/document.xml` を対応付け、コメント本文ではなくコメント範囲が付与された本文 `WBS・進捗管理台帳確定（タスク割振・ガント更新）` を抽出して採用した。index 52は、みなみ野女性医療センターの提案書・契約書から、契約範囲外の追加対応が別途対応または別紙見積で扱われる記載を確認し、回答候補として `契約範囲外の追加対応` を採用した。ただし、資料内に「別契約」という完全一致語は見つからなかったため、要確認候補とした。index 95は、青嶺不動産アセットマネジメントの `スケジュール_r1.xlsx` と `スケジュール_r2.xlsx` をタスクIDで比較し、未着手から完了へのステータス変更と番号表記差を除外した結果、`T15「モデル評価・重要特徴量整理」の担当者が、渡辺 遥から渡辺 遥 / 小林 直樹に変更された。` を採用した。

この結果、提出候補の `わかりません` は9件から6件になった。残件は index 38、44、46、58、62、79。出力は `EDA/EDA056/tables/eda056_route_results.csv`、提出候補CSVは `EDA/EDA056/predictions/eda056_meeting_operation_schedule_predictions.csv`、提出形式zipは `EDA/EDA056/predictions/eda056_meeting_operation_schedule_submission.zip` に保存した。SIGNATEへの提出は行っていない。

## 追記: EDA057

EDA057では、EDA056後に残った `わかりません` 6件のうち、全案件横断の契約・担当者・社内管理情報を組み合わせる3件を個別route化した。対象は index 38 のAPR-M3横断集計、index 46 の着手金最大案件のES内線、index 79 のかえで案件における1タスク当たり想定工数である。OpenRouterなどの外部APIは使わず、EDA051の契約/役割台帳、EDA049の座席表候補、raw/processed資料から再計算した。

index 38は、社内管理の決裁基準に従い、税込契約金額から通常承認を判定し、医療案件は1段階引き上げ、`time_and_materials` は少なくとも部長承認として再計算した。その結果、APR-M3、つまり本部長承認が必要な案件はなく、回答は `該当なし。合計0円` とした。index 46は、契約台帳の着手金最大が白峰信用リスク評価株式会社の2,720,000円であり、ESが中村 誠、座席表候補では中村のExec席の内線が `7201` であるため、`7201` を採用した。ただし座席表はEDA049の検証用seed由来のため要確認とした。

index 79は、rawのかえで計画ファイル `スケジュール.xlsx` をopenpyxlで開こうとしたが `BadZipFile` となったため、鍵付きまたは通常xlsxでないファイルとして扱った。代替として、かえで案件の会議録・報告資料からAction ID単位でデータアステル側担当者を重複排除して数え、最終報告の想定総工数140時間を担当タスク数で割った。松本 真央が4タスクで最大となり、回答は `松本 真央、35.00時間` とした。ただし計画フォルダ本体からの直接抽出ではないため要確認とした。

この結果、提出候補の `わかりません` は6件から3件になった。残件は index 44、58、62。出力は `EDA/EDA057/tables/eda057_route_results.csv`、`EDA/EDA057/tables/cross_project_contract_master.csv`、`EDA/EDA057/tables/kaede_task_owner_counts.csv`、提出候補CSVは `EDA/EDA057/predictions/eda057_cross_project_predictions.csv`、提出形式zipは `EDA/EDA057/predictions/eda057_cross_project_submission.zip` に保存した。SIGNATEへの提出は行っていない。

## 追記: EDA058

EDA058では、EDA057後に残った `わかりません` 3件のうち、座席表以外の index 62 を処理した。対象質問は、青葉与信マネジメントの最終報告資料におけるモデル比較で、上位2件のスコア差を生んだ設定差分を問うものである。座席表2件は、EDA049/EDA047で画像・座標復元が不安定だったため今回は触らなかった。

index 62は、最終報告資料のモデル比較表で上位2件がどちらも `extra_trees` であることを確認し、詳細設定を `analysis_outputs/experiments/leaderboard.csv.data.csv` から確認した。上位1件は `trial_index=10, extra_trees, n_estimators=500, f1_macro=0.60266642`、上位2件は `trial_index=6, extra_trees, n_estimators=300, f1_macro=0.59534963` であり、主要設定の差分は `n_estimators` のみだった。そのため回答は `n_estimatorsが500と300で異なります。` とした。

また、RAGとしての根拠追跡のため、EDA058提出候補100行の回答を変更せずに、各回答のソース元台帳を作成した。個別routeの採用ログに根拠ファイルがある場合はそれを優先し、採用ログに `source_paths` がない行はEDA021のBM25検索上位ソースを補助根拠として記録した。最終的な `わかりません` は index 44、58 の座席表2件のみである。出力は `EDA/EDA058/tables/eda058_route_results.csv`、`EDA/EDA058/tables/aoba_credit_leaderboard_top2.csv`、`EDA/EDA058/tables/answer_source_audit.csv`、提出候補CSVは `EDA/EDA058/predictions/eda058_model_diff_predictions.csv`、提出形式zipは `EDA/EDA058/predictions/eda058_model_diff_submission.zip` に保存した。

`eda058_model_diff_submission.zip` を提出した結果、SIGNATEスコアは `-0.26666666666666666` だった。EDA044の `-0.3` からはわずかに改善したが、まだマイナスであり、残る座席表2件だけでなく、既存の非不明回答にも誤答が含まれている可能性が高い。

## 追記: EDA061〜EDA063

EDA061では、社内用語集とパスワード導出規則を読み込み、rawのtest質問100件に含まれる社内略語を正式名称へ展開した。展開後の質問文は `data/processed/share/share/質問回答/questions_test_expanded.csv` に保存し、127件の置換を `EDA/EDA061/abbreviation_replacement_log.csv` に記録した。かえで総合病院のパスワード導出規則 `DA-KAEDE-20250902-xlsx` も確認した。

EDA062では、index 40のような案件横断集計に備え、10案件の契約開始日・終了日・契約日数・契約形態を `data/processed/share/share/契約管理/project_contract_periods.csv` に整理した。また、契約書の13支払回を `project_payment_schedule.csv` に抽出し、支払月別合計を `payment_monthly_totals.csv` にまとめた。ひがし丘総合病院の終了日は、契約書の「開始日から5週間」から導出した値であることを記録している。さらにindex 67のような差分確認に備え、案件ごとに正式な提案書と最終報告書を選び、税込金額・抽出根拠・参照ファイル・最終報告時金額から提案時金額を引いた差額・比較可否を `project_amount_comparison.csv` に整理した。加えて、社内管理の決裁基準Markdownに基づき、金額帯、医療案件、time_and_materials契約を考慮した必要承認レベル（主任・課長・部長・本部長）と判定理由も記録した。金額が両方から抽出できない案件は比較不能・承認判定不能として明示し、提案時見込金額には基準を仮適用している。

EDA063では、EDA061の略語展開済みtest質問100件をOpenRouterの `openai/gpt-oss-20b:free` へ送り、質問ジャンルと必要処理をJSON形式で分類した。分類は100件すべてHTTP 200・JSON解析成功で、主routeは `document_qa` 22件、`calculation` 18件、`mixed` 17件、`table_lookup` 12件などとなった。index 40は `calculation / metric_aggregation`、index 57は `mixed` かつ `requires_code_execution=true` と判定された。結果は `EDA/EDA063/tables/test_question_classification.csv`、API試行ログは `openrouter_classification_attempts.csv` に保存した。LLM分類は後続routeの候補であり、実行前にファイル存在と分類妥当性を確認する。

## 現時点の全体まとめ

### 1. EDA001〜EDA010: 読み込みと初期RAG

rawデータのファイル形式・破損ファイル・質問形式を確認し、Markdown、JSON、BM25検索、LLMへ渡す文脈の基本形を作成した。Word、PowerPoint、Excel、PDF、画像、Python、Notebookの抽出方針を確認し、提出CSVとzipの形式も検証した。EDA005ではルールベース回答を採用し、提出形式確認として `-0.7666666666666667` を記録した。

### 2. EDA011〜EDA020: 前処理方針の確立

質問route、表データ、書式、画像、差分、文書全体contextを棚卸しした。rawを元データ、processedを抽出・構造化データとして分け、Wordは書式を保持したMarkdown/JSON、Excelは表・セル書式・数式情報、PowerPointはスライド・shape・画像情報、PDFはページ単位、コードとNotebookは本文・実行結果として扱う方針にした。鍵付きファイルは無理に開かず、周辺情報または導出規則を使う方針も定めた。

### 3. EDA021〜EDA027: BM25とLLM接続

BM25ローカルRAG、OpenRouter LLM、Geminiの接続を試した。LLM接続後はローカル検索だけより回答数が増えたが、無料枠の429、content空、長文contextによる誤答が発生した。`わかりません` を機械的に禁止する方針はvalidで悪化したため、根拠不足時は不明回答を許し、根拠整形とroute別処理を優先する方針にした。

### 4. EDA028〜EDA034: validでの失敗分類と構造化計算

valid 30問を質問ジャンルごとに分類し、表計算、書式抽出、差分比較、コード読解、文書全体contextなどの失敗要因を明確化した。構造化データから回答候補を作るrouteを追加し、validでは構造化候補をLLMで短答化することで、EDA034時点で30問中29問をgold類似まで改善した。計算はLLMに任せず、ローカルで再計算した値を最終回答へ使う方針を採用した。

### 5. EDA035〜EDA046: testへのroute展開

validで有効だったExcel、Word、CSV、Markdown、JSON、コード、Notebook、スケジュール、差分の処理をtestへ展開した。OpenRouter 20Bは構造化候補の短答化に限定し、既存の根拠ある回答を不用意に上書きしないようにした。提出候補の非不明回答は段階的に増えたが、testスコアでは誤答も混在するため、回答数だけを増やすより根拠の確度を重視する必要があると分かった。

### 6. EDA047〜EDA058: 残件routeと根拠追跡

画像Vision/OCR、座席表、PDFページOCR、会議録アクションID、APR判定、全案件契約集計、Wordコメント、運用条項、スケジュール差分、モデル設定差分を個別route化した。EDA058では最終回答100件のソース元台帳 `answer_source_audit.csv` を作成し、最終的な `わかりません` は座席表のindex 44・58の2件となった。

ただし、`eda058_model_diff_submission.zip` のSIGNATEスコアは `-0.26666666666666666` だった。READMEの評価方式ではMissingは0点、Incorrectは-1点なので、残り2件の不明回答だけでなく、非不明回答にも誤答または質問条件を満たさない回答が複数あると判断している。

### 7. EDA059〜EDA060: ソース確認と人手評価準備

EDA059では、100問について質問文、現在の回答、参照ファイル、source_confidenceをCSVとMarkdownにまとめた。EDA060では、同じ会社の質問を連続させた人手評価用の `EDA/human_review.csv` を作成し、`human_answer` と `human_review` を空欄で用意した。現在の回答は `current_answer` に保持しているため、人手確認で元回答を上書きしない。

### 8. EDA061〜EDA063: 質問理解と自動route分類

EDA061では社内略語を正式名称へ展開し、100問中93問、127箇所を変換した。EDA062では10案件の契約期間、13件の支払予定、支払月別合計に加え、提案時金額と最終報告時金額の比較台帳を構造化した。EDA063では略語展開済み質問100問をGPT-OSS-20Bへ送り、primary_route、sub_route、必要ファイル形式、計算要否、コード実行要否、LLM回答要否を分類した。分類は100問すべて成功し、index 40は集計系、index 57は計算とコード実行を含む複合系、index 67は提案時と最終報告時の金額差分探索系となった。

### 現在の構成

```text
質問文
  ↓
EDA061: 社内略語を正式名称へ展開
  ↓
EDA063: LLMで質問ジャンルと必要処理を分類
  ↓
必要ファイル形式と参照案件を特定
  ↓
検索・構造化抽出・差分比較・計算・コード実行の専用routeへ分岐
  ↓
必要な場合だけLLMで最終回答を短答化
```

凡例: LLM分類はroute選択の補助情報であり、分類結果だけを正解とみなさない。専用route実行前に、参照ファイルの存在、抽出値、計算式、回答条件を検証する。

### 現在の主要な未解決事項

- EDA058の非不明回答を人手で正誤確認し、誤答の種類を特定すること。
- 座席表の画像・座標関係を完全に再構成すること。
- index 57のような回帰係数適用・閾値探索を安全なコード実行routeとして実装すること。
- index 40のような案件横断集計で、契約期間・支払予定・対象日条件を一貫して処理すること。
- LLM分類の `mixed` 判定を専用routeへ正しく分解し、分類誤り時の再判定を用意すること。
- testで改善を確認する前に、同じ処理をvalidで再現性確認すること。

### 次の実装方針

まずEDA060の人手評価を進め、誤答の多いrouteを特定する。その結果をもとに、EDA063の分類結果を入力とするroute dispatcherを作り、`calculation`、`code_execution`、`cross_project_aggregation`、`format_extraction`、`diff_comparison`の順に専用処理を接続する。最終提出用コードでは、質問分類、ファイル検索、構造化抽出、計算、LLM回答生成、predictions.csv作成までを一つの再現可能なパイプラインにまとめる。

## 追記: EDA066

EDA066では、`SIGNATE`直下に分散していた7つの `SIGNATE_Agentic_RAG_*` 作業ツリーを棚卸しした。Excel行到達性監査とPowerPointタイムライン統合には未コミットの実装差分があったため、差分パッチと新規Pythonソースを `EDA066_external_rag_worktree_inventory/` に保存する。5GB級の `data/output/`、原本、仮想環境はGitへ含めず、作業ツリー名、ブランチ、基点コミット、再生成対象として台帳に記録した。

この整理により、最終RAGパイプラインはルートの `src/` と `scripts/` を正とし、外部作業ツリーは将来の再評価対象としてEDAに分離する。外部API依存のOpenRouter試行は、再現性と実行コストの観点から最終コールドスタート経路には採用しない。
