# 前処理方針とEDA台帳

## このファイルの目的

このファイルは、共有ドライブ内のファイルをRAG用の中間データへ変換する方針と、各EDAでどの前処理を実施したかを記録する台帳です。

最終的には、GPT-OSS-120bなどのLLMへ原本ファイルをそのまま渡すのではなく、質問に応じて必要な根拠だけを取り出して渡します。そのために、各ファイル形式を以下のように整理します。

- Markdown: LLMに読ませる本文、見出し、表、画像説明、要約
- JSON: 出典、ページ、スライド、シート、セル、書式、画像パス、ブロック番号などの再現用メタデータ
- CSVまたはDataFrame: 計算が必要な表データ
- JSONL: BM25、embedding、LLM入力で共通利用する検索用レコード

## 基本方針

1. 原本は `data/raw` に残し、加工結果は `data/processed` に保存する。
2. LLM入力用にはMarkdownを作る。
3. 再現、検索、計算、根拠追跡用にはJSONを作る。
4. 表データはMarkdown化だけでなく、計算可能なCSVまたはDataFrameとして扱う。
5. 画像は画像ファイルを保持しつつ、OCRまたはVisionモデルで説明文を作る。
6. 鍵付きファイル、破損ファイル、開けないファイルは無理に復号せず、無視理由を台帳に残す。
7. validの正解を回答生成に混ぜない。validは評価と診断にのみ使う。
8. 外部APIを使う場合は、APIキーを成果物に保存せず、モデル名、処理件数、失敗理由を記録する。
9. 根拠が不足している場合は、無理に回答を生成せず `わかりません` を許す。精度改善は不明回答の禁止ではなく、根拠抽出と計算処理の改善で行う。

## ファイル形式別の前処理方針

| 対象 | Markdown化 | JSON化 | 追加で必要な処理 | 状態 |
|---|---|---|---|---|
| Word `.docx` | 段落、見出し、表をMarkdown化 | run単位の太字、下線、色、ハイライト、表、画像メタデータを保存 | 鍵付きファイルは無視 | EDA012で実施済み |
| Excel `.xlsx` | シート概要、表の要約、重要範囲をMarkdown化 | シート名、セル値、数式、書式、結合、非表示、グラフ情報を保存 | pandas/openpyxlで計算可能にする | EDA014で実施済み |
| CSV/TSV | カラム、行数、統計量、サンプルをMarkdown化 | カラム型、欠損、統計量、元パスを保存 | 計算はDataFrameで実行 | EDA014で実施済み |
| PowerPoint `.pptx` | スライド単位で本文、表、箇条書きをMarkdown化 | スライド番号、図形、表、位置、書式、画像参照を保存 | 版違い比較にも使う | EDA015で実施済み |
| PDF `.pdf` | ページ単位で本文をMarkdown化 | ページ番号、抽出順、ページサイズ、回転、メタデータを保存 | 表や段組みの抽出順は必要に応じて追加確認 | EDA016で実施済み |
| 画像 `.png` など | Vision/OCR結果をMarkdown要約化 | 画像パス、OCR、説明、抽出値、モデル名、信頼度を保存 | グラフ数値は後処理または元データ再計算 | EDA013で一部実施 |
| Python `.py` | ファイル要約、関数一覧、入出力候補、コード全文をMarkdown化 | AST由来の関数、import、呼び出し、ファイル入出力候補を保存 | コード読解ルートで使用 | EDA017で実施済み |
| Notebook `.ipynb` | Markdownセル、コードセル、出力要約をMarkdown化 | セル順、コード、出力、画像、実行結果を保存 | 図と生成元コードの対応付けが必要 | EDA018で実施済み |
| Markdown `.md` | 原則そのまま利用 | メタデータ、見出し構造、ファイルパス、品質フラグを保存 | 必要ならチャンク化 | EDA019で実施済み |
| JSON `.json` | 内容要約をMarkdown化 | 原構造を保持 | スキーマ推定が必要 | 一部実施済み |
| 統合JSONL | 検索用本文を保持 | record_id、source_path、record_type、metadataを保持 | BM25、embedding、LLM入力で共通利用 | EDA020で実施済み |

凡例: `対象` は前処理対象のファイル形式、`Markdown化` はLLMに読ませる内容、`JSON化` は再現と検索に使う構造情報、`追加で必要な処理` は回答精度のために必要な処理、`状態` は現在の実装状況を表します。

## EDA別前処理台帳

| EDA | 対象 | 実施内容 | 主な出力 | 状態 |
|---|---|---|---|---|
| EDA001 | 全体 | 共有ドライブ、質問、提出形式の棚卸し | `file_inventory.csv` | 実施済み |
| EDA002 | テキスト系 | md、csv、json、py、ipynbなどの初期テキスト抽出とチャンク化 | `extracted_documents.jsonl`, `text_chunks.jsonl` | 実施済み |
| EDA004 | Office/PDF | docx、pptx、xlsx、pdfの本文抽出、シート概要抽出 | `extracted_documents.jsonl`, `text_chunks.jsonl`, `sheet_summary.csv` | 実施済み |
| EDA011 | 全体設計 | 表、書式、画像、差分、文書全体LLM、質問ルーティングの棚卸し | `question_routes.csv`, 各種inventory | 実施済み |
| EDA012 | Word `.docx` | WordをMarkdownと再現用JSONへ変換 | `data/processed/share/**/*.docx.md`, `*.structure.json` | 実施済み |
| EDA013 | 標準レコード、画像一部 | Markdown/JSON/画像を検索用JSONLへ統合し、優先4画像をOpenRouter Visionで説明文化 | `data/processed/embedding/embedding_records.jsonl` | 実施済み |
| EDA014 | Excel/CSV/TSV | 表データをMarkdown、構造JSON、計算用CSVへ変換 | `data/processed/share/**/*.xlsx.md`, `*.xlsx.structure.json`, `*.sheets/*.csv`, `*.data.csv` | 実施済み |
| EDA015 | PowerPoint `.pptx` | スライド単位Markdown、構造JSON、画像assetsへ変換 | `data/processed/share/**/*.pptx.md`, `*.pptx.structure.json`, `*.pptx.assets/*` | 実施済み |
| EDA016 | PDF `.pdf` | PDFをページ単位Markdownと構造JSONへ変換 | `data/processed/share/**/*.pdf.md`, `*.pdf.structure.json` | 実施済み |
| EDA017 | Python `.py` | PythonをAST静的解析し、コードMarkdownと構造JSONへ変換 | `data/processed/share/**/*.py.md`, `*.py.structure.json` | 実施済み |
| EDA018 | Notebook `.ipynb` | Notebookをセル単位Markdown、構造JSON、出力画像assetsへ変換 | `data/processed/share/**/*.ipynb.md`, `*.ipynb.structure.json`, `*.ipynb.assets/*` | 実施済み |
| EDA019 | Markdown `.md` | 既存Markdownの品質確認を行い、そのままprocessedへ保存 | `data/processed/share/**/*.md`, `*.md.structure.json` | 実施済み |
| EDA020 | 全processed構造JSON | EDA012からEDA019の成果物を検索用JSONLへ統合 | `data/processed/embedding/embedding_records.jsonl` | 実施済み |
| EDA021 | test質問100件 | 統合JSONLでBM25検索し、抽出型回答と提出形式zipを作成 | `EDA/EDA021/predictions/predictions.csv`, `eda021_local_rag_submission.zip` | 実施済み |
| EDA022 | test質問の一部 | EDA021の検索contextをOpenRouter LLMへ送り、hybrid提出zipを作成 | `EDA/EDA022/tables/llm_answer_log.csv`, `eda022_llm_hybrid_submission.zip` | 実施済み |
| EDA023 | valid質問30件 | ローカルRAGをvalidで評価し、検索失敗と回答抽出・計算失敗を分類 | `EDA/EDA023/tables/valid_local_rag_diagnosis.csv`, `valid_route_summary.csv` | 実施済み |
| EDA024 | valid質問30件 | OpenRouter LLMでvalid全問回答を試行。120Bは全件429、20Bは完走 | `EDA/EDA024/tables/valid_llm_answer_log.csv`, `valid_llm_route_summary.csv` | 実施済み |
| EDA025 | valid質問30件 | `わかりません` 禁止と検索フォールバックを検証 | `EDA/EDA025/tables/valid_no_unknown_answer_log.csv`, `eda025_report.md` | 実施済み。不採用方針 |
| EDA026 | test質問100件 | no-unknown test提出候補のスクリプトを作成 | `EDA/EDA026/eda026.py` | EDA025悪化を受け不採用 |
| EDA027 | test質問100件、無料モデル確認 | `わかりません` 許容方針でOpenRouterとGeminiのtest提出形式zipを作成し、120Bや他無料モデルも1問で疎通確認 | `EDA/EDA027/tables/test_unknown_allowed_answer_log.csv`, `model_probe_log.csv`, `eda027_openrouter_openai_gpt_oss_20b_free_unknown_allowed_submission.zip` | 実施済み |
| EDA028 | valid質問30件 | EDA024の回答を正解・不明・誤答に分類し、route別の次アクションを整理 | `EDA/EDA028/tables/eda024_valid_answer_classification.csv`, `eda024_route_classification_summary.csv` | 実施済み |
| EDA029 | valid正解以外25件 | 不明・誤答・近似正解について、必要データ種別、失敗領域、次修正を分類 | `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv`, `source_type_summary.csv` | 実施済み |
| EDA030 | valid表計算7件 | CSV、Excelフィルター、PivotTable相当、文書横断金額集計をサブタイプ分類し、pandas/openpyxlで実計算 | `EDA/EDA030/tables/table_valid_calculation_results.csv`, `table_subtype_summary.csv`, `cross_project_tax_details.csv` | 実施済み |
| EDA031 | valid表計算7件 | EDA030の計算結果をOpenRouter LLMへ渡し、提出用の短い回答へ整形できるか検証 | `EDA/EDA031/tables/llm_table_answer_log.csv`, `llm_table_attempt_log.csv` | 実施済み |
| EDA032 | valid正解以外25件 | Markdown、structure JSON、Notebook出力、CSV、metricsから回答候補を一括生成 | `EDA/EDA032/tables/structured_candidate_answers.csv`, `structured_candidate_route_summary.csv` | 実施済み |
| EDA033 | valid正解以外25件 | EDA032候補をOpenRouter LLMへ渡し、提出用回答へ整形してvalid評価 | `EDA/EDA033/tables/llm_structured_candidate_answer_log.csv`, `llm_structured_candidate_attempt_log.csv` | 実施済み |
| EDA034 | valid全体とtest 100件 | EDA033のvalid改善を全体回答へ統合し、testは短く明確な20B回答のみ採用して提出zipを作成 | `EDA/EDA034/tables/valid_pipeline_answer_log.csv`, `EDA/EDA034/tables/test_pipeline_answer_log.csv`, `EDA/EDA034/predictions/eda034_structured_safe_submission.zip` | 実施済み |
| EDA035 | test不明回答83件 | EDA034で残った不明回答に、書式、表、CSV、コード、スケジュール系のローカル処理を追加適用 | `EDA/EDA035/tables/test_unknown_reduction_log.csv`, `EDA/EDA035/predictions/eda035_unknown_reduction_submission.zip` | 実施済み |
| EDA036 | test構造化候補38件 | EDA035候補をOpenRouterへ送り、短答化結果を確認。既存の非不明回答は保持し、未回答2件だけ追加採用 | `EDA/EDA036/tables/test_openrouter_structured_answer_log.csv`, `EDA/EDA036/predictions/eda036_openrouter_structured_test_submission.zip` | 実施済み |
| EDA037 | test未対応route 67件 | diff、document、table、format、fallbackへローカル候補生成を追加し、安全な4件だけ提出候補に採用 | `EDA/EDA037/tables/test_unhandled_route_candidates.csv`, `EDA/EDA037/predictions/eda037_unhandled_routes_submission.zip` | 実施済み |
| EDA038 | test差分比較route 9件 | old/newファイルを明示的にペアリングし、Markdown差分とOpenRouter短答化で6件を追加採用 | `EDA/EDA038/tables/test_diff_route_attempt_log.csv`, `EDA/EDA038/predictions/eda038_diff_route_submission.zip` | 実施済み |
| EDA039 | test書式抽出route 7件 | Excel/PPTX/Wordのstructure JSONから書式レコードを作成。構造JSONだけでは追加採用0件 | `EDA/EDA039/tables/test_format_route_attempt_log.csv`, `EDA/EDA039/predictions/eda039_format_route_submission.zip` | 実施済み |
| EDA040 | test表計算route 9件 | ヒストグラム、バッファ工数、ID数をローカル計算で3件追加採用。回帰係数系などは未解決 | `EDA/EDA040/tables/test_table_route_attempt_log.csv`, `EDA/EDA040/predictions/eda040_table_route_submission.zip` | 実施済み |
| EDA041 | test文書横断・本文検索route 36件 | Markdown、CSV、structure JSONから根拠文脈を作成し、OpenRouter 20Bで短答化。3件を追加採用 | `EDA/EDA041/tables/test_document_search_route_attempt_log.csv`, `EDA/EDA041/predictions/eda041_document_search_route_submission.zip` | 実施済み |
| EDA042 | EDA041空content 33件 | max_tokens増量、JSON回答強制、raw response保存で再試行。reasoning有効化後に10件を追加採用 | `EDA/EDA042/tables/test_document_retry_attempt_log.csv`, `EDA/EDA042/raw_responses/`, `EDA/EDA042/predictions/eda042_document_retry_submission.zip` | 実施済み |
| EDA043 | EDA042 length空content 15件 | 質問語で文脈を圧縮し、max_tokens 1500で再試行。12件を追加採用 | `EDA/EDA043/tables/test_compressed_context_retry_attempt_log.csv`, `EDA/EDA043/raw_responses/`, `EDA/EDA043/predictions/eda043_compressed_context_retry_submission.zip` | 実施済み |
| EDA044 | format/table/image route 16件 | 書式メタデータ、表CSV/Markdown、画像/グラフ周辺文脈を一括処理。9件を追加採用。提出スコアは `-0.3` | `EDA/EDA044/tables/test_format_table_image_attempt_log.csv`, `EDA/EDA044/raw_responses/`, `EDA/EDA044/predictions/eda044_format_table_image_submission.zip` | 実施済み |
| EDA045 | EDA044後の残件20件 | 既存routeで表現できていない質問を9種類の新route候補へ分類 | `EDA/EDA045/tables/remaining_route_gap_inventory.csv`, `EDA/EDA045/tables/remaining_route_gap_summary.csv` | 実施済み |
| EDA046 | EDA045後の残件20件 | 新route候補ごとに専用文脈を作り、OpenRouter 20Bで短答化。4件を追加採用 | `EDA/EDA046/tables/test_all_remaining_routes_result.csv`, `EDA/EDA046/tables/test_all_remaining_routes_attempt_log.csv`, `EDA/EDA046/predictions/eda046_all_remaining_routes_submission.zip` | 実施済み |
| EDA047 | processed画像56件 | 画像ファイル自体を棚卸しし、優先8件をOpenRouter Vision free modelでimage-to-text化。再実行と成功済み結果保持により5件成功 | `EDA/EDA047/tables/image_asset_inventory.csv`, `EDA/EDA047/tables/image_to_text_results.csv`, `EDA/EDA047/image_to_text_records.jsonl`, `EDA/EDA047/image_to_text_context.md` | 実施済み |
| EDA048 | EDA046後の不明16件 | 残った `わかりません` を失敗ファミリー別に分類し、次に作るべき構造化処理を整理 | `EDA/EDA048/tables/remaining_unknown_diagnosis.csv`, `EDA/EDA048/tables/remaining_unknown_family_summary.csv`, `EDA/EDA048/eda048_report.md` | 実施済み |
| EDA049 | 座席表/Floor Map | PPTX図形座標からの復元可否を確認。text shapeは無く、画像Visionも不完全だったため、検証用座席座標テーブルを作成 | `EDA/EDA049/tables/seat_pptx_shape_audit.csv`, `EDA/EDA049/tables/seat_coordinate_table.csv`, `EDA/EDA049/tables/seat_question_probe.csv` | 実施済み |
| EDA050 | 会議録/アクションID | 会議録・報告資料をページ単位に台帳化し、アクションID、コメント、チェックポイント候補を抽出。no text PDFも分離 | `EDA/EDA050/tables/meeting_page_inventory.csv`, `EDA/EDA050/tables/meeting_action_inventory.csv`, `EDA/EDA050/tables/no_text_pdf_inventory.csv` | 実施済み |
| EDA051 | 全案件横断集計 | 契約条件、役割/担当者、計画/リソース候補、案件マスターを作成 | `EDA/EDA051/tables/contract_terms_inventory.csv`, `EDA/EDA051/tables/role_assignment_inventory.csv`, `EDA/EDA051/tables/project_master_aggregation.csv` | 実施済み |
| EDA052 | no text PDF | PDF本文抽出が空だった会議録をページ画像化し、OpenRouter VisionでOCR。白峰M04 page 2とみなみ野A10候補を取得 | `EDA/EDA052/tables/rendered_no_text_pdf_pages.csv`, `EDA/EDA052/tables/pdf_page_vision_ocr_results.csv`, `EDA/EDA052/tables/no_text_pdf_question_probe.csv` | 実施済み |
| EDA053 | OCR/座席表候補統合 | EDA049とEDA052の候補を提出候補へ統合し、安全版と攻め版を作成 | `EDA/EDA053/tables/eda053_candidate_pool.csv`, `EDA/EDA053/tables/eda053_safe_adoption_log.csv`, `EDA/EDA053/predictions/eda053_safe_unknown_reduction_submission.zip` | 実施済み |
| EDA054 | 残件ローカル表/LLM確認 | みなみ野PL案と青葉与信チェックポイントをローカル表から確認し、一部をOpenRouter短答化 | `EDA/EDA054/tables/eda054_candidate_answers.csv`, `EDA/EDA054/tables/eda054_openrouter_attempts.csv`, `EDA/EDA054/predictions/eda054_remaining_unknown_submission.zip` | 実施済み |
| EDA055 | グラフ/黄色セル/回帰係数 | Word chart XML、Excel structure JSON、計算用CSVから3件をローカル再計算 | `EDA/EDA055/tables/eda055_route_results.csv`, `EDA/EDA055/predictions/eda055_chart_format_formula_submission.zip` | 実施済み |
| EDA056 | コメント/条項/差分 | raw docxコメント範囲、契約条項検索、スケジュールr1/r2差分で3件を追加採用 | `EDA/EDA056/tables/eda056_route_results.csv`, `EDA/EDA056/predictions/eda056_meeting_operation_schedule_submission.zip` | 実施済み |
| EDA057 | 全案件横断集計 | APR-M3判定、着手金最大案件のES内線、鍵付きかえで計画の代替工数集計を実施 | `EDA/EDA057/tables/eda057_route_results.csv`, `EDA/EDA057/tables/cross_project_contract_master.csv`, `EDA/EDA057/predictions/eda057_cross_project_submission.zip` | 実施済み |
| EDA058 | モデル比較差分/ソース精査 | 青葉与信のモデル比較上位2件の設定差分をleaderboardから抽出し、最終回答100件のソース元台帳を作成。提出スコアは `-0.26666666666666666` | `EDA/EDA058/tables/eda058_route_results.csv`, `EDA/EDA058/tables/answer_source_audit.csv`, `EDA/EDA058/predictions/eda058_model_diff_submission.zip` | 実施済み |

凡例: `EDA` は実験番号、`対象` は主な前処理対象、`実施内容` は行った処理、`主な出力` は後続処理で参照する成果物、`状態` は現在の完了状況を表します。

## Word前処理の整理

Word文書そのもののMarkdown/JSON化は、EDA013ではなくEDA012で実施済みです。

EDA012では、Word文書47件のうち46件を変換しました。失敗した1件は、既知の鍵付きまたは破損扱いの `契約書_pw-kaede20250902.docx` です。今後は鍵付きファイルとして無視します。

EDA013では、EDA012で作成したWord由来のMarkdown/JSONを、画像レコードなどと一緒に `embedding_records.jsonl` へ統合しました。つまり、EDA013はWord変換そのものではなく、検索・embedding・LLM入力で使う標準レコード化の工程です。

## 統合JSONLと初期RAGの整理

EDA020では、Word、表、PowerPoint、PDF、Python、Notebook、Markdownの前処理結果を `data/processed/embedding/embedding_records.jsonl` に統合しました。総レコード数は 2484 件で、空テキスト、record_id重複、統合エラーはいずれも 0 件です。

EDA021では、この統合JSONLを使ってtest 100問にローカルBM25 RAGを実行しました。出力は提出形式の `predictions.csv` とzipですが、LLM APIは使っておらず、本文行の抽出型回答です。そのため、形式確認用の初期提出候補として扱い、精度向上はroute別処理とLLM最終回答生成で行います。

EDA022では、EDA021の検索contextをOpenRouter LLMへ送り、先頭5問でLLM回答生成を検証しました。5問すべてHTTP 200で回答を取得し、LLM成功分だけEDA021回答を置き換えた `predictions_hybrid.csv` とzipを作成しました。未処理分や失敗分はEDA021回答へフォールバックするため、提出形式は100行を維持します。

EDA023では、test提出前の評価基準としてvalid 30問にローカルRAGを実行しました。完全一致0件、予測文に正解を含む件数0件、正解がTopK根拠に含まれる件数5件であり、BM25検索と本文行抽出だけでは提出品質に届かないことを確認しました。

EDA024では、valid 30問すべてをOpenRouter LLMで回答する比較を行いました。`openai/gpt-oss-120b:free` は上流レート制限により全件HTTP 429でしたが、代替の `openai/gpt-oss-20b:free` は30問すべてHTTP 200で完走し、完全一致5件、正解含有7件でした。LLMで改善は見られるものの、表計算、書式、差分、コード読解はroute別の根拠整形が必要です。

EDA025では、`わかりません` を出さないno-unknown方針をvalidで検証しました。HTTP 429が多く発生したことに加え、検索フォールバックが本文断片を回答として返すケースが多く、完全一致1件、正解含有2件に悪化しました。そのため、根拠不足時に誤答を強制する方針は採用せず、`わかりません` を許したうえでroute別の根拠整形を改善します。

EDA027では、`わかりません` を許す従来方針でtest 100問の提出形式zipを作成しました。OpenRouter無料枠の日次制限または `openai/gpt-oss-20b:free` の上流レート制限により、OpenRouter 20Bでは100問中99問がHTTP 429となりました。追加で、OpenRouterの無料モデル24件を取得し、120B、20B、Qwenを含む8モデルを1問で確認しましたが、すべてHTTP 429でした。

その後、Gemini経路を追加して `gemini-3.5-flash` でも再実行しましたが、100問中92問がHTTP 429、3問がHTTP 500、2問がtimeoutとなり、最終的な回答は100件すべて `わかりません` でした。そのため、EDA027のzipは提出非推奨として扱います。

さらにOpenRouter 20Bを再実行したところ、100問中53問がHTTP 200、47問がHTTP 429となりました。最終回答は83件が `わかりません`、17件が非 `わかりません` です。前回よりは改善しましたが、まだ多数が不明回答であるため、提出する場合も形式確認または参考提出に留め、精度改善はroute別処理で進めます。

EDA028では、EDA024のvalid 30問の回答を質問系統ごとに分類しました。完全一致5件、近似正解5件、不明回答14件、明確な誤答6件でした。近似正解には、`20` と `20日`、`¥5,775,000` と `5,775,000円`、`未連絡を表します。` と `未連絡` のように、単位、記号、余計な語を整えれば正解に近いものを含めています。`table_calculation`、`format_extraction`、`diff_check`、`code_reading` は完全一致も近似正解もほぼ出ておらず、LLMへ投げる前にroute別処理を作る必要があります。

EDA029では、EDA028で正解ではなかった25件について、必要データ種別と失敗領域を分類しました。必要データ種別は `pptx` 6件、`docx` 5件、`py_or_ipynb` 4件、`csv` 3件、`xlsx_pivot` 2件、`xlsx` 2件、`image` 2件、`pptx_or_docx_versions` 1件でした。失敗領域は `calculation` が7件で最多ですが、対象文書検索6件、回答整形5件、コード/Notebook検索4件も重要です。したがって、CSVだけを見直すのではなく、Excel/PivotTable、PowerPoint/Word書式、old/new差分、py/ipynb検索も並行して改善する必要があります。

EDA030では、EDA029で `table_calculation` とされたvalid 7件を対象に、表計算のサブタイプ分類と実計算を行いました。CSV条件抽出、groupby平均、四捨五入、最近傍id抽出、Excel AutoFilter抽出、PivotTable相当の再計算はgoldと一致しました。全案件の消費税総額だけは、文書から再構成した計算値が `4,384,250円`、valid goldが `4,394,250円` となり、10,000円差を要確認として記録しました。

EDA031では、EDA030の計算結果と計算メモをOpenRouterへ送り、LLMが最終回答だけを返せるか確認しました。`openai/gpt-oss-120b:free` は7件すべてHTTP 429でしたが、`openai/gpt-oss-20b:free` は7件すべてHTTP 200で回答しました。LLM回答は7件すべてEDA030の計算回答に近く、gold類似は6件でした。差分の1件は、EDA030の要確認案件である消費税総額です。

EDA032では、EDA029の正解以外25件を対象に、表計算、書式、コード/Notebook、スケジュールCSV、文書Markdown、metrics JSONから回答候補を一括生成しました。25件すべて候補を生成でき、gold類似は24件でした。残る1件は、EDA030から継続している全案件消費税総額の10,000円差です。

EDA033では、EDA032候補をOpenRouterへ送り、LLMで最終回答へ整形しました。`openai/gpt-oss-120b:free` は25件中1件がHTTP 200、24件がHTTP 429でした。`openai/gpt-oss-20b:free` は残り24件すべてHTTP 200でした。LLM回答のgold類似は24件で、EDA032候補と同じでした。したがって、改善の主因はLLMではなく、構造化データからの候補生成です。

EDA034では、EDA024のvalid全体回答にEDA033の改善回答を上書きし、valid 30件中29件がgold類似となる統合ログを作成しました。test 100件については、EDA027のOpenRouter 20B回答のうち短く明確な17件だけを採用し、残り83件は `わかりません` とする安全側の提出候補zipを作成しました。EDA021のBM25抽出回答は会社名や文書冒頭の混入が多かったため、提出用では原則不採用としました。

EDA035では、EDA034で `わかりません` だった83件を対象に、既存の構造化データとraw表から回答候補を作る処理をtestへ適用しました。追加採用は14件で、test 100件の非不明回答は17件から31件に増えました。採用した主な処理は、Word太字run抽出、Excelオレンジ行抽出、青色セル合計、CSV再計算、コード内パラメータ抽出、metricsとコードの結合、スケジュール期間抽出です。根拠が弱い候補は採用せず、残り69件は `わかりません` のまま残しました。

EDA036では、EDA035の構造化候補38件をOpenRouterへ送り、GPT-OSS-20Bで短答化を確認しました。38件はHTTP 200でしたが、既存の非不明回答をLLMで上書きするとWord抽出回答が途中で切れる例がありました。そのため、提出候補ではEDA035で採用済みの回答は保持し、EDA035時点で `わかりません` だった行だけLLM回答で埋めます。この方針で2件を追加採用し、test 100件の非不明回答は33件になりました。

EDA037では、EDA036で残った未対応route 67件へローカル候補生成を追加しました。差分はold/new Markdownの差分行、文書全体は見出し・ページ周辺、表計算はヒストグラム・スケジュールCSV・相関、書式はExcel黄色セルと太字/下線/イタリック、fallbackは本文行検索を使います。誤答混入を避けるため、差分系と汎用本文検索の `needs_review=True` 候補は提出回答に採用せず、Excel/書式/相関で根拠が比較的明確な4件だけを追加採用しました。test 100件の非不明回答は37件です。

## 次に優先する前処理

1. 表データを使った実回答
   - EDA014でExcel/CSV/TSVの中間データはできました。
   - EDA030で `table_calculation` valid 7件をpandas/openpyxlで計算し、6件はgoldと一致しました。
   - EDA031で計算結果をOpenRouter 20Bへ渡したところ、7件すべて計算回答に近い最終回答が得られました。
   - 次はEDA030の実装を、valid専用のindex分岐ではなく、質問文から対象案件、列名、条件、集計方法を抽出して実行する汎用ルーターへ寄せます。
   - 提出用では、表計算routeについてはLLMを必須にせず、ローカル計算結果を直接採用する選択も残します。

2. 書式、差分、文書全体LLMの実回答化
   - EDA020で統合JSONLはできました。
   - EDA022でLLM接続はできました。
   - EDA032で太字、下線、ハイライト、old/new差分、文書指定、コード/Notebook、スケジュール系のvalid候補生成を一括で検証しました。
   - 次はvalid専用のindex分岐を減らし、質問文から対象案件、対象ファイル、抽出条件を推定してtestにも適用できる汎用ルーターへ寄せます。

3. 画像の数値抽出改善
   - EDA013では検索用説明文は得られました。
   - EDA014/EDA015/EDA018で表、スライド内グラフ、Notebook出力画像のメタデータも得られました。
   - グラフの値を厳密に答えるには、Visionプロンプト改善、OCR、または元CSV/Notebookからの再計算を検討します。

4. validルート別の回答検証
   - EDA023の `valid_local_rag_diagnosis.csv` を基準にします。
   - `question_routes.csv` に従い、表計算、文書全体、書式、画像、差分、コード読解の順に実回答を検証します。

5. 提出用パイプライン化
   - EDA021のローカルRAGとEDA022のLLM hybridは提出形式確認としては通りました。
   - EDA024ではLLM全問回答のvalid評価を開始しました。
   - EDA025では `わかりません` 禁止が悪化したため、根拠不足時は不明回答を許す方針に戻します。
   - EDA027ではOpenRouter 20B再実行で一部回答が得られましたが、無料枠でtest全問を一括LLM回答する運用は依然として不安定です。
   - EDA028ではEDA024の失敗をroute別に分類し、最優先は `table_calculation` のローカル計算であると整理しました。
   - EDA029では、CSVだけでなくExcel/PivotTable、PowerPoint/Word、コード/Notebook、画像、差分処理が改善対象であると整理しました。
   - EDA030では、表計算7件のうち6件をローカル計算で再現できたため、表系質問はLLMへ丸投げせず、計算結果と根拠だけをLLMに渡す方針を採用します。
   - EDA031では、計算結果を渡せば20Bでも短い最終回答へ整形できることを確認しました。ただし、カンマ区切りや読点などの表記が変わるため、評価形式を重視する場合はローカル計算回答をそのまま使う方が安定する可能性があります。
   - EDA032/EDA033では、正解ではなかった25件のうち24件が構造化候補またはLLM整形後にgold類似となりました。提出用ではまず構造化候補を作り、LLMは候補整形に限定します。
   - EDA034/EDA035では、test提出候補に同じ方針を適用しました。EDA034は安全側に17件だけ非不明回答を採用し、EDA035はローカル構造化処理で14件を追加採用しました。
   - EDA036では、OpenRouter 20Bへtest構造化候補を送り、未回答2件を追加採用しました。一方で、既存の高信頼ローカル回答をLLMで上書きすると情報が欠落する可能性があるため、LLMは未回答の補完と回答表記確認に限定します。
   - EDA037では、未対応route全体へ候補生成を広げました。差分系や汎用検索系は候補生成まではできましたが、提出採用にはLLM整形または個別確認が必要です。
   - EDA038では、差分比較routeを個別化し、testの非不明回答を37件から43件に増やしました。old/newのペアリングは有効ですが、ローカル差分候補をそのまま採用した行は誤答確認が必要です。
   - EDA039では、書式抽出routeを個別化しましたが、追加採用は0件でした。PowerPoint/Wordの黄色ハイライトが画像化されている場合は、structure JSONではなくOCRまたはVision routeが必要です。
   - EDA040では、表計算routeを個別化し、ヒストグラム、バッファ工数、ID数の3件を追加採用しました。回帰係数、APR判定、複数資料の定義照合は、さらに専用route化が必要です。
   - EDA041では、文書横断・本文検索routeを個別化し、36件分の根拠文脈を抽出しました。ユーザー確認によりコンペ用データとしてOpenRouter送信が許可されたため、20Bで36件を短答化し、3件を追加採用しました。
   - EDA042では、EDA041でcontentが空だった33件を再試行しました。GPT-OSS-20Bはreasoning必須であり、reasoning有効化とmax_tokens増量により10件を追加採用しました。`finish_reason=length` でcontent空の15件は、文脈圧縮またはさらに大きいtoken上限が必要です。
   - EDA043では、EDA042で残ったlength空content 15件に対して、質問語に一致する行だけへ文脈を圧縮し、max_tokens 1500で再試行しました。圧縮により12件を追加採用し、非不明回答は71件になりました。
   - EDA044では、format/table/image routeをまとめて処理し、9件を追加採用しました。ただし、画像や書式の否定回答は誤答リスクがあるため、提出前に個別確認が必要です。
   - EDA045では、残件20件を新route候補へ分類しました。次は `meeting_action_status_lookup`、`model_formula_recompute`、`cross_project_contract_aggregation` のように、ローカルで再現しやすいrouteから実装します。
   - EDA046では、EDA045で整理した残件20件を対象に、route別の専用文脈抽出とOpenRouter 20B短答化を一括で試しました。4件を追加採用し、非不明回答は84件になりました。`情報が不足しています` のような不十分回答は採用しないように判定条件を修正しました。
   - EDA047では、`data/processed/share` 配下の画像56件を棚卸しし、優先度の高い8件をOpenRouterのVision対応free modelへ送ってimage-to-textを試しました。再実行と成功済み結果保持により5件の説明文を取得できましたが、座席表を含む3件は依然としてupstream timeoutまたは空contentでした。画像そのものを読ませるrouteは有効ですが、無料モデルでは分割実行、成功結果の保持、元CSV/Notebook再計算との併用が必要です。
   - EDA048では、EDA046後も `わかりません` の16件について、個別routeを作っても残った理由を整理しました。最も多いのは会議録/アクションID構造化4件、全案件横断集計3件、座席表の空間関係2件です。次はLLM再試行よりも、会議録台帳、座席表座標テーブル、契約/担当者/工数の横断テーブルを優先します。
   - EDA049では、座席表PPTXのshape構造を確認し、人名・EXT・役割がtext shapeとして存在しないことを確認しました。OpenRouter VisionはHTTP 200でしたが1席欠落したため、提出採用はせず、検証用seedで座席座標テーブルを作りました。最終提出用では画像OCR/Visionの再生成、または固定画像に対する座標抽出処理が必要です。
   - EDA050では、会議録/報告資料をページ単位に台帳化しました。Word会議録は使えますが、白峰・みなみ野など一部PDFは `[no text extracted]` であり、アクションIDや進捗サマリを取るにはPDFページ画像のOCR/Visionが必要です。
   - EDA051では、契約条件、役割/担当者、計画/リソース候補を全案件横断で集計しました。契約金額・担当体制の土台はできましたが、APR-M3の略称定義、ESと座席表内線の結合、鍵付きまたは未抽出計画の工数は追加処理が必要です。
   - EDA052では、`[no text extracted]` のPDFから残件に直結する2ファイルを優先して画像化し、OpenRouter VisionでOCRしました。白峰M04の進捗サマリはpage 2候補、みなみ野A10は「index再実験の結果反映」候補を取得しました。ただしVision OCRは10ページ中4ページ成功であり、提出採用前に対象ページ画像とraw responseの確認が必要です。
   - EDA053では、EDA049とEDA052で作った候補をEDA046提出候補へ統合しました。PDFページ画像OCR由来の2件は安全版に採用し、残りの `わかりません` は16件から14件になりました。座席表の検証用seed由来2件も含める攻め版では12件まで減りましたが、座席表は画像からの完全再抽出が未完了のため要確認です。
   - EDA054では、EDA053 safe版で残った14件に対し、ローカル表データとOpenRouter短答化を組み合わせて再確認しました。みなみ野のPL案はスケジュールCSVから `第4週`、青葉与信のチェックポイント2はMS2関連タスクから `T05、T06、T07、T08` を採用し、safe版の `わかりません` は12件になりました。OpenRouterで短答化できなかった長文候補や、根拠が弱い横断集計・座席表・モデル再計算は採用しません。
   - EDA055では、EDA054後の残件12件から、ローカルで値を再現できる3件を個別route化しました。Word内グラフはdocx zip内のchart XMLを直接読み、Excel黄色セルはstructure JSONと前方補完済みCSVを突き合わせ、回帰係数はExcel由来CSVの係数と対象行特徴量で再計算しました。これにより `わかりません` は12件から9件になりました。index 80は質問文ではSheet2とありますが、raw xlsx上の黄色セルは `Sheet1!E1409` の1件だけだったため、実ファイル上の黄色セルを優先します。
   - EDA056では、EDA055後の残件9件から、会議録コメント、運用条項、スケジュール差分の3件を個別route化しました。Wordコメントはraw docx内の `comments.xml` と本文XMLのコメント範囲を対応付け、運用条項は提案書/契約書の節単位検索で抽出し、スケジュール差分はr1/r2のCSVをタスクIDで比較して状態変更と番号表記差を除外しました。これにより `わかりません` は9件から6件になりました。index 52は「別契約」という完全一致語ではなく「別途対応」「別紙見積」由来の候補なので、最終提出前に確認します。
   - EDA057では、EDA056後の残件6件から、全案件横断の契約・担当者・社内管理情報が必要な3件を個別route化しました。APR-M3判定は契約金額、医療案件フラグ、契約形態から社内決裁基準を再計算し、本部長承認案件なしとして `該当なし。合計0円` を採用しました。着手金最大案件のES内線は、契約台帳、役割台帳、座席表候補を結合して `7201` を採用しました。かえで案件の計画ファイルは `BadZipFile` で開けないため、会議録・報告資料のAction IDと最終報告の想定総工数140時間から代替集計し、`松本 真央、35.00時間` を採用しました。これにより `わかりません` は6件から3件になりました。座席表候補と鍵付き計画ファイル代替は要確認です。
   - EDA058では、座席表以外で残っていたindex 62を処理しました。青葉与信マネジメントの最終報告資料のモデル比較表と `leaderboard.csv.data.csv` を突き合わせ、上位2件はどちらも `extra_trees` で、差分は `n_estimators=500` と `n_estimators=300` のみと確認しました。回答は `n_estimatorsが500と300で異なります。` とし、`わかりません` は座席表2件だけになりました。また、最終回答100件について回答を変更せず、個別route採用ログまたはBM25検索上位からソース元台帳 `answer_source_audit.csv` を作成しました。`eda058_model_diff_submission.zip` の提出スコアは `-0.26666666666666666` でした。
   - 今後はtest提出前にEDA023相当のvalid評価を通し、改善が確認できたものだけを提出候補にします。
   - 最終的にはBM25/embedding検索、route別処理、必要な計算、LLM最終回答生成を1つの再現可能な推論コードへまとめます。
   - EDA061では、社内用語集を使って質問文の略語を正式名称へ展開し、処理済み質問CSVと置換ログを作成しました。EDA062では、契約期間・支払予定・支払月別合計に加え、正式な提案書と最終報告書の税込金額、差額、抽出根拠、比較可否、社内決裁基準に基づく必要承認レベル（主任・課長・部長・本部長）を案件横断台帳として整備しました。決裁基準は金額帯、医療案件、time_and_materials契約の順に適用し、提案時見込金額には仮適用であることを記録します。EDA063では、質問文だけをOpenRouter GPT-OSS-20Bへ送り、必要ファイル形式、計算要否、コード実行要否、最終LLM要否をJSON分類しました。分類は後続routeの候補として使い、実行前に根拠ファイルと分類の妥当性を確認します。
