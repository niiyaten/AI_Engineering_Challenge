# 提出用パイプライン設計メモ

このメモは、`src/rag_competition` 配下に実装する提出用パイプラインの構成を詰めるためのたたき台です。既存のEDA成果は参考にしますが、ここでは新しい質問が来ても同じ流れで回答できる、再現可能な処理として整理します。

## 前提

- 対象データはコンペ用の配布資料であり、OpenRouterなどの外部LLM APIに渡して問題ない。
- APIキーはリポジトリ直下の `.apikey` を参照する。
- image to text のLLMモデル、通常のLLMモデル、Pythonプログラムによる計算を使える。
- 提出時は `predictions.csv` をzip化する必要がある。
- 質問文ごとの手作業回答や、正解を直接埋め込む処理は避ける。

## 全体方針

処理は大きく次の流れに分ける。

1. 資料群の棚卸
2. 質問文の読み込みと社内略語の展開
3. 参照すべき資料候補の特定
4. 質問ジャンルの分類
5. ジャンル別の回答生成
6. 回答検証と提出ファイル作成

重要なのは、3と4を分けて扱うこと。  
「どの資料を見るべきか」と「その資料に対して何をすべきか」は別問題なので、別々にログを残せる形にする。

## 1. 資料群の棚卸

目的は、質問文から参照資料を探すための索引を作ること。

この段階では本文の詳細読解までは行わず、次の情報を集める。

- ファイルパス
- ファイル名
- 拡張子
- 会社名または組織名
- フォルダ種別
- 旧版、新版、r1、r2、v1、v3などの版情報
- 会議録、報告資料、契約書、提案書、計画、データ、分析結果などの資料種別
- 日付
- 派生ファイルの関係

棚卸結果は、後続処理で読めるようにCSVまたはJSONLで保存する。

候補:

```text
data/processed/inventory/files.csv
data/processed/inventory/files.jsonl
```

改善点として、単なるファイル一覧だけではなく、同じ資料の関連ファイルを結びつける情報も持たせたい。

例:

- `報告資料_2025-04-09.docx` と `報告資料_2025-04-29.docx` は同じ種類の時系列資料
- `提案書_v1.pptx` と `提案書_v3.pptx` は差分比較対象
- `train.xlsx` と `analysis_project/data/train.csv` は同じデータを別形式で持つ可能性がある

この対応関係があると、差分比較や複数ファイル横断の質問に強くなる。

## 2. 質問文の読み込みと社内略語の展開

`questions_test.csv` を読み込み、質問文に含まれる社内略語を正式名へ展開する。

略語辞書の参照元:

```text
data/raw/share/share/共有ドライブ/社内管理/社内用語集.docx
```

ここで作るべき出力は、元の質問文と展開後の質問文を両方保持するデータ。

例:

```text
index
question_original
question_normalized
replaced_terms
```

注意点:

- 略語をすべて置換すると、ファイル名や社内資料上の表記と合わなくなる可能性がある。
- そのため、正式名だけに置き換えるのではなく、略語と正式名の両方を検索語として残す。
- 置換前後の質問文をログに残し、後で誤置換を確認できるようにする。

## 3. 参照すべき資料候補の特定

ここが最も難しい部分。  
方針としては、一発で1つのファイルを決めるのではなく、段階的に候補を絞る。

### 3.1 会社または組織の候補を決める

質問文から会社名、略称、正式名を拾い、棚卸結果と照合する。

候補が1社に絞れる場合:

- その会社配下の資料を優先する。

候補が複数社になる場合:

- 横断集計または比較の可能性が高い。
- 会社単位で候補ファイル群を分けて保持する。

会社名が明示されない場合:

- 全社横断の質問として扱う。
- 社内管理フォルダや全プロジェクト共通資料を優先候補に入れる。

### 3.2 資料種別の候補を決める

質問文の表現から、見るべき資料種別を推定する。

例:

- 契約、単価、請求、精算: 契約書、請求関連資料
- スケジュール、WBS、タスク、マイルストーン: 計画資料、スケジュール表
- 最終報告、モデル、精度、KPI: 最終報告書、分析結果
- 会議、議事、進捗: 会議録、報告資料
- 太字、下線、色、ハイライト、コメント: 構造抽出済みJSON、Office文書
- old、新版、v1、v3、r1、r2: 差分比較対象

この段階でも1つに決めきらず、候補資料にスコアを付ける。

### 3.3 候補資料に優先度を付ける

候補資料には、複数の根拠で点を付ける。

- 会社名が一致する
- ファイル名に質問語が含まれる
- フォルダ種別が質問の意図に合う
- 日付や版情報が質問文と一致する
- 拡張子がタスクに合う
- 本文検索で質問語または展開語が見つかる

LLMに最初から全ファイルを渡すのではなく、まず機械的な候補抽出で件数を絞り、その後にLLMで再判定するのがよい。

### 3.4 参照ファイル特定の出力

1問ごとに次の形で保存する。

```text
index
question_normalized
candidate_files
candidate_reason
needs_cross_company
needs_multiple_files
confidence
```

ここで `confidence` が低い場合は、回答生成側で無理に断定せず、候補を広めに取る。

## 4. 質問ジャンルの分類

参照資料候補とは別に、質問が求めている処理を分類する。

最初の分類候補:

- `document_qa`: 文書本文から事実を抜き出す
- `table_lookup`: 表やセルを参照する
- `calculation`: 集計、差分、ランキング、相関などを計算する
- `format_extraction`: 太字、下線、色、コメントなどの書式情報を使う
- `diff_comparison`: 旧版と新版、r1とr2などを比較する
- `image_ocr`: 画像、グラフ、図表を読み取る
- `code_execution`: NotebookやPythonコードを読んで再計算する
- `cross_file_aggregation`: 複数ファイルまたは複数会社を横断して集計する
- `unknown`: 判断不能

分類はLLMに任せてもよいが、出力は必ずJSONにする。

分類結果には、次の情報も持たせる。

```text
route
requires_calculation
requires_python
requires_vision_model
requires_multiple_files
answer_format_hint
classification_reason
```

## 5. ジャンル別の回答生成

ここから先は、routeごとに処理を分ける。

### document_qa

文書本文、抽出済みMarkdown、構造JSONを検索し、根拠候補をLLMへ渡して回答する。

ポイント:

- 会社名と資料種別で候補を絞る。
- 該当箇所の前後文脈を渡す。
- 根拠が弱い場合は断定させない。

### table_lookup

CSVまたはExcel展開済みCSVを読み、該当する行、列、セルを探す。

ポイント:

- 表のヘッダーを正規化する。
- 色やコメントが必要な場合は構造JSONも併用する。
- 単純なセル参照ならLLMよりPythonで処理する。

### calculation

Pythonで計算できるものはPythonで処理する。

ポイント:

- LLMには計算させず、計算式または処理計画を作らせる程度にする。
- 実際の集計、差分、ランキング、相関はPythonで行う。
- 小数、丸め、単位、百分率の指定は質問文から抽出する。

### format_extraction

Office文書やExcelの構造JSONから、太字、下線、色、コメント、ハイライトを抽出する。

ポイント:

- 本文Markdownだけでは書式情報が落ちるため、構造JSONを優先する。
- Excelの場合はセル番地、行番号、シート名を残す。

### diff_comparison

旧版と新版、または複数時点の資料を比較する。

ポイント:

- ファイル名の版情報を棚卸段階で持っておく。
- テキスト差分、表差分、スライド差分を分ける。
- 案件進行に関係する変更など、質問が求める差分だけを抽出する。

### image_ocr

図表、画像、グラフ、スクリーンショットはvision対応モデルに渡す。

ポイント:

- 画像そのものだけでなく、周辺の本文やファイル名も一緒に渡す。
- グラフの数値読み取りは誤差が出やすいため、元データがあれば元データを優先する。

### code_execution

NotebookやPythonコード、分析出力を読み、必要なら再計算する。

ポイント:

- いきなり任意コードを実行せず、まずコード内容と入力ファイルを確認する。
- 実行が必要な場合は、実行ログ、使用ファイル、出力値を保存する。
- コンペ提出用なので、再現できる形で処理を残す。

### cross_file_aggregation

複数ファイルや複数会社を横断して集計する。

ポイント:

- 会社単位、資料種別単位、日付単位で候補を分ける。
- すべての候補を一括でLLMに渡さず、Pythonで中間表を作ってから要約する。
- 集計対象外になったファイルもログに残す。

## 6. 回答検証と提出ファイル作成

回答生成後、提出前に必ず検査する。

検査項目:

- 行数がサンプル提出と一致している
- indexの順序が一致している
- 空回答がない
- 回答が長すぎない
- 質問で指定された丸め方、単位、日付形式に従っている
- 根拠ファイルが記録されている
- `わかりません` の件数と理由が確認できる

提出用の成果物:

```text
submissions/predictions.csv
submissions/submission.zip
data/processed/runs/{run_id}/answers.jsonl
data/processed/runs/{run_id}/evidence.jsonl
data/processed/runs/{run_id}/run_report.md
```

## 実装単位の案

`src/rag_competition` には、次のように責務を分ける。

```text
src/rag_competition/
  paths.py
  schemas.py
  inventory.py
  question_normalizer.py
  file_resolver.py
  task_router.py
  evidence_builder.py
  answerers/
    document_qa.py
    table_lookup.py
    calculation.py
    format_extraction.py
    diff_comparison.py
    image_ocr.py
    code_execution.py
    cross_file_aggregation.py
  llm_client.py
  submission.py
  pipeline.py
```

最初から全部を完成させる必要はない。  
まずは次の順番で小さく作るのがよい。

1. `inventory.py`: 資料棚卸を作る
2. `question_normalizer.py`: 略語展開を作る
3. `file_resolver.py`: 参照候補ファイルを複数返す
4. `task_router.py`: route分類を返す
5. `pipeline.py`: ここまでを1問ずつログに保存する
6. `submission.py`: 回答を提出形式に整える

## 改善提案

ユーザー案に追加したい改善点は次の通り。

1. 参照ファイル特定とタスク分類を分ける

同じファイルでも、質問によって「本文検索」「表計算」「書式抽出」「差分比較」が変わる。  
そのため、ファイル候補とタスク分類は別々に出す。

2. 参照ファイルは1つに決めない

候補ファイルを上位複数件保持し、後段でrouteに応じて使い分ける。  
会社名だけ分かるが資料種別が曖昧な質問では、この方が安全。

3. LLMの前に機械的な候補抽出を置く

全資料をLLMに渡すと高コストで、見落としや混乱も起きやすい。  
ファイル名、フォルダ名、会社名、日付、版情報、拡張子でまず絞る。

4. Pythonでできる計算はPythonに寄せる

LLMは分類、検索語の拡張、回答文の整形に使い、数値計算そのものはPythonで行う。

5. すべての中間結果を保存する

最終回答だけでは改善が難しい。  
質問文の正規化、候補ファイル、route、根拠、回答、エラーを保存する。

## 相談したい未決定事項

1. 参照ファイル候補の上限を何件にするか

最初は上位10件程度がよさそう。  
ただし横断集計では、会社ごとに上位数件を持つ必要がある。

2. route分類をLLMに任せるか、ルールとLLMの併用にするか

最初はルールで粗く分類し、曖昧なものだけLLMで補正するのが安定しそう。

3. image to text の処理を最初から入れるか

図表質問が多いなら早めに入れる。  
ただし元データがあるグラフは、画像より元データを優先したい。

4. LLMに渡す根拠の粒度

ページ単位、段落単位、表単位、セル周辺など、routeごとに分ける必要がある。

5. 回答できない場合の扱い

根拠がない場合は `わかりません` にするが、候補ファイルが見つかったのに答えられない場合と、候補ファイル自体が見つからない場合は区別してログに残す。

## 次に決めること

まずは、次の2点を決めると実装に入りやすい。

1. 資料棚卸の出力項目
2. 参照ファイル候補を決めるスコアの付け方

この2つが決まると、質問文から参照資料を逆引きする土台ができる。

## 既存EDA・成果物との対応調査

### 調査方針

今回の調査では、`README.md`、`EDA/eda_summary.md`、各EDAのmanifest、関連レポート、関連Pythonコード、`data/processed` 配下の成果物、`src`、`pyproject.toml` を確認した。全EDAのコード全文は読まず、`eda_summary.md` と成果物一覧から提出用パイプラインの設計モジュールに関係するEDAを絞って確認した。

確認した限り、既存成果物はかなり豊富で、次の部品は再実装せずに再利用候補にできる。

- 1ファイル1レコードのファイル台帳: `EDA/EDA001/tables/file_inventory.csv`
- 文書・表・コード・画像などの検索レコード: `data/processed/embedding/embedding_records.jsonl`
- 形式別のMarkdown・structure JSON・シートCSV: `data/processed/share/**`
- 社内略語展開: `EDA/EDA061/eda061.py` と `questions_test_expanded.csv`
- test質問分類: `EDA/EDA063/tables/test_question_classification.csv`
- route別の実験コード: EDA038からEDA044、EDA047、EDA050からEDA052、EDA057、EDA062
- 回答根拠監査: `EDA/EDA058/tables/answer_source_audit.csv`、`EDA/EDA059/tables/question_answer_source_confidence.csv`

ただし、EDA037以降の多くは「残ったtest未回答を減らす」目的の実験コードであり、特定index向けの分岐や過去回答CSVへの依存がある。そのまま提出用モジュールへコピーするのではなく、関数単位で抽出し、汎用入出力へ寄せる必要がある。

### モジュール対応表

凡例: 各行は設計上の1モジュールを表す。`既存EDA` は主に対応するEDA、`再利用候補` はPythonファイル、関数、成果物の要約、`判定` は提出用パイプラインでの利用方針を表す。

| モジュール | 対応する既存EDA | 再利用可能なPythonファイル・関数 | 再利用可能な中間成果物 | 現時点の完成度 | 判定 | 問題点・依存関係 |
|---|---|---|---|---|---|---|
| `inventory.py` | EDA001, EDA011, EDA020 | `EDA001/eda001.py`、`EDA011/eda011_pipeline_inventory.py` の `load_docs`, `run_tabular_document_inventory`, `run_format_inventory`, `run_image_inventory`, `run_diff_inventory`、`EDA020/eda020.py` の `make_record`, `records_from_structure_json` | `EDA/EDA001/tables/file_inventory.csv`, `EDA/EDA011/tables/*inventory.csv`, `data/processed/embedding/embedding_records.jsonl` | 高い | 既存成果物を優先再利用。必要なら台帳再生成関数を整理 | EDA011の台帳は設計調査用で、提出時の正式スキーマではない。`embedding_records` は検索単位であり、1ファイル1レコードの台帳とは分ける |
| `question_normalizer.py` | EDA061 | `EDA061/eda061.py` の `read_glossary`, `compile_replacer`, `expand_question`, `build_replacement_log` | `data/processed/share/share/質問回答/questions_test_expanded.csv`, `EDA/EDA061/abbreviation_replacement_log.csv` | 高い | ほぼ再利用可能。関数名と入出力だけ整理 | 現状はtest向け実行スクリプト。validや将来質問にも使えるよう、入力CSVを引数化する必要あり |
| `file_resolver.py` | EDA011, EDA020, EDA021, EDA041, EDA044, EDA050, EDA051, EDA062 | `EDA021/eda021.py` の `BM25Index`, `tokenize`, `load_records`、`EDA041/eda041.py` の `path_hints`, `all_candidate_paths`, `score_path`, `build_context`、`EDA044/eda044.py` の `find_paths`, `project_keywords`、`EDA062/eda062.py` の `choose_project_document` | `embedding_records.jsonl`, `file_inventory.csv`, `question_routes.csv`, `project_contract_periods.csv`, `project_payment_schedule.csv` | 中 | リファクタリング必要 | EDA041/044はtest残件前提の手続きが混ざる。会社名がない質問は、資料名・ID・列名・日付・固有語から絞る処理を新規整理する必要あり |
| `task_router.py` | EDA011, EDA028, EDA029, EDA063 | `EDA011/eda011_pipeline_inventory.py` の `question_route`、`EDA063/eda063.py` の `prompt_for`, `parse_json_array`, `validate_item`, `classify_batch` | `EDA/EDA011/tables/question_routes.csv`, `EDA/EDA063/tables/test_question_classification.csv`, `EDA/EDA028/tables/eda024_valid_answer_classification.csv`, `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv` | 中から高 | 既存分類結果は再利用可。分類器本体は整理必要 | EDA063はOpenRouter前提でAPI呼び出しを含む。今回はAPIを呼ばず、既存CSVを参照するだけにする |
| `evidence_builder.py` | EDA020, EDA021, EDA041, EDA043, EDA044, EDA047, EDA052 | `EDA020/eda020.py` の `records_from_*`、`EDA021/eda021.py` の `write_context`, `candidate_lines`、`EDA041/eda041.py` の `best_snippets_for_path`, `build_context`、`EDA043/eda043.py` の `compress_context`、`EDA047/eda047.py` と `EDA052/eda052.py` の `record_to_search_text` | `embedding_records.jsonl`, `EDA/EDA021/contexts/*.md`, `EDA/EDA047/tables/image_to_text_results.csv`, `EDA/EDA052/tables/pdf_page_vision_ocr_results.csv` | 中 | リファクタリング必要 | 既存contextはtest質問ごとの過去検索結果を含むため、提出用では再生成する。`embedding_records` から汎用Evidenceを作る方が安全 |
| `answerers/document_qa.py` | EDA010, EDA021, EDA041, EDA042, EDA043 | `EDA041/eda041.py` の `build_context`, `local_page_or_slide_answer`, `local_direct_answer`、`EDA043/eda043.py` の `compress_context`, `build_prompt`, `parse_json_answer` | `embedding_records.jsonl`, `*.md`, `*.structure.json`, `EDA041-043` のresult/attemptログ | 中 | 新規モジュール化が必要 | 回答生成はまだ実装対象外。既存コードはAPI呼び出しとtest残件依存が強い |
| `answerers/table_lookup.py` | EDA014, EDA030, EDA040, EDA044 | `EDA014/eda014.py` の `process_xlsx`, `worksheet_to_dataframe`, `dataframe_profile`、`EDA040/eda040.py` の `table_context`, `read_csv_safe`、`EDA044/eda044.py` の `row_context`, `read_csv_safe` | `*.xlsx.sheets/*.csv`, `*.data.csv`, `*.xlsx.structure.json`, `EDA011/tables/xlsx_sheet_inventory.csv` | 高い素材あり | リファクタリング必要 | EDA030/040は個別質問向け計算関数が多い。汎用表探索はシートCSVとstructure JSONを読む新規薄層が必要 |
| `answerers/calculation.py` | EDA030, EDA040, EDA051, EDA057, EDA062 | `EDA030/eda030.py` の `numeric_series`, `CalculationResult`, 一部の計算関数、`EDA040/eda040.py` の `numeric_series`、`EDA051/eda051.py` の `yen_to_int`, `approval_level`、`EDA057/eda057.py` の `apply_apr_rule`、`EDA062/eda062.py` の `extract_payment_rows`, `build_ledgers` | `table_valid_calculation_results.csv`, `project_master_aggregation.csv`, `cross_project_contract_master.csv`, `project_contract_periods.csv`, `payment_monthly_totals.csv`, `project_amount_comparison.csv` | 中 | 汎用化して再利用 | 計算関数はindex固有・質問固有が多い。提出用では「計算仕様をExecutionPlanで受ける」形へ再設計が必要 |
| `answerers/format_extraction.py` | EDA014, EDA015, EDA012, EDA039, EDA044 | `EDA039/eda039.py` の `extract_xlsx_format_records`, `extract_pptx_docx_format_records`, `build_format_records`、`EDA044/eda044.py` の `yellow_records_for_workbook`, `styled_text_records` | `*.structure.json`, `EDA011/tables/format_document_inventory.csv`, `EDA039/tables/test_format_route_result.csv` | 高い素材あり | 関数抽出して再利用 | 現状は質問に応じた対象path選択とLLM呼び出しが混在。書式レコード抽出だけを切り出す |
| `answerers/diff_comparison.py` | EDA011, EDA038, EDA058 | `EDA038/eda038.py` の `cleaned_lines`, `similarity`, `diff_added_lines`, `unified_context`, `build_pair`、`EDA058/eda058.py` の provenance関連 | `EDA011/tables/version_document_candidates.csv`, `EDA011/tables/diff_question_inventory.csv`, `EDA038/tables/test_diff_route_result.csv` | 中 | リファクタリング必要 | `build_pair` は既存test質問への分岐が混ざる。版情報をFileRecordに持たせる方向が必要 |
| `answerers/image_ocr.py` | EDA013, EDA047, EDA052 | `EDA047/eda047.py` の `build_inventory`, `image_metadata`, `call_openrouter_vision`, `record_to_search_text`、`EDA052/eda052.py` の `render_pdf_pages`, `call_openrouter_vision`, `record_to_search_text` | `EDA047/tables/image_to_text_results.csv`, `EDA052/tables/pdf_page_vision_ocr_results.csv`, `embedding_records.jsonl` の `image` record | 中 | 既存OCR結果は再利用可。API部分は後で共通化 | 今回はAPIを呼ばない。画像再処理はコストがあるため、既存OCR結果を優先 |
| `answerers/code_execution.py` | EDA017, EDA018, EDA021 | `EDA017/eda017.py` の `imports_from_tree`, `definitions_from_tree`, `calls_and_files_from_tree`, `process_python`、`EDA018/eda018.py` のNotebook変換関数、`EDA021/eda021.py` のBM25 | `*.py.md`, `*.py.structure.json`, `*.ipynb.md`, `*.ipynb.structure.json`, notebook assets | 中 | 読解用素材は再利用。実行基盤は新規設計 | 既存はコード読解用の構造化が中心。安全に再実行するサンドボックス・ログ設計は未整備 |
| `answerers/cross_file_aggregation.py` | EDA050, EDA051, EDA057, EDA062 | `EDA050/eda050.py` の `extract_page_rows`, `action_rows_from_page`, `checkpoint_task_rows`、`EDA051/eda051.py` の `build_contract_tables`, `build_schedule_resource_table`, `make_project_master`、`EDA057/eda057.py` の `load_contract_master`, `extract_action_records_from_markdown`、`EDA062/eda062.py` の `build_ledgers` | `meeting_action_inventory.csv`, `schedule_resource_inventory.csv`, `project_master_aggregation.csv`, `cross_project_contract_master.csv`, 契約管理CSV群 | 高い素材あり | 台帳は安全に再利用可能。汎用aggregation APIは新規 | 既存台帳は特定テーマに強い。任意の横断質問には、台帳選択と列意味解釈が必要 |
| `llm_client.py` | EDA008, EDA022, EDA024, EDA031, EDA033, EDA038-044, EDA047, EDA052, EDA063 | 各EDAの `read_openrouter_key`, `call_openrouter`, `call_openrouter_vision`, `parse_json_answer` | `.apikey`, 各attemptログ、raw response | 中 | 新規共通化が必要 | 同じOpenRouter処理が各EDAに重複。テキスト・Vision・JSON parse・retry・raw保存を共通化する |
| `submission.py` | EDA005, EDA021, EDA027, EDA034-046, EDA053-058 | `EDA021/eda021.py` の `write_predictions`、EDA038-044の `write_submission` | 各 `predictions.csv`, `*_submission.zip`, `submissions/eda044_current_policy_*` | 高い | 最小関数を新規実装し、既存は参照 | zip直下を `predictions.csv` にする処理は既存で確認済み。test回答の固定値は再利用しない |
| `pipeline.py` | EDA011, EDA021, EDA034-046, EDA058 | EDA011の棚卸フロー、EDA021の `run_rag`、EDA034以降の段階マージ処理 | EDA034-046のroute別resultログ、EDA058 source audit | 低から中 | 新規実装が必要 | 既存は実験の逐次改善パイプラインで、汎用「解析から計画保存まで」の本体ではない |

### 既存中間成果物一覧

凡例: 各行は提出用パイプラインで再利用候補となる成果物を表す。`安全性` は、testやvalidの個別回答、手動評価、提出回答を含むかを踏まえた再利用可否を表す。

| 成果物種別 | パス | 生成元EDA | レコード単位 | 主なカラム・JSONフィールド | 用途 | rawから再生成可能か | 個別回答を含むか | 安全性 |
|---|---|---|---|---|---|---|---|---|
| ファイル台帳 | `EDA/EDA001/tables/file_inventory.csv` | EDA001 | 1ファイル1行 | `relative_path`, `file_name`, `extension`, `area`, `project_name`, `major_folder`, `source_path` | `FileRecord` の初期値、会社・フォルダ・拡張子検索 | 可能 | 含まない | 安全に再利用可 |
| 形式別棚卸 | `EDA/EDA011/tables/*inventory.csv` | EDA011 | 文書、表、書式、画像、差分候補など | `relative_path`, `project_name`, `major_folder`, `table_count`, `sheet_count`, `highlight_count` など | 初期スコアリング、route別候補確認 | 可能 | 一部valid/test質問表を含むファイルあり | 資料側棚卸は安全。質問inventoryは評価用として参照のみ |
| 文書抽出結果 | `data/processed/text_baseline/extracted_documents.jsonl` | EDA002 | 1文書1レコード | `document_id`, `relative_path`, `extension`, `project_name`, `text`, `text_length` | 初期RAG、文書本文検索 | 可能 | 含まない | 安全に再利用可 |
| テキストチャンク | `data/processed/text_baseline/text_chunks.jsonl` | EDA002 | 1チャンク1レコード | `chunk_id`, `document_id`, `chunk_index`, `text` | BM25検索、SearchRecord候補 | 可能 | 含まない | 安全に再利用可 |
| Office/PDF文書抽出 | `data/processed/office_pdf_baseline/*.jsonl` | EDA004 | 1文書または1チャンク | `paragraph_count`, `table_count`, `slide_count`, `page_count`, `text` | 旧前処理の参照 | 可能 | 含まない | EDA012-020成果物を優先し、補助的に利用 |
| structure JSON | `data/processed/share/**/*.structure.json` | EDA012-019 | 1元ファイル1JSON | `raw_relative_path`, `processed_markdown_path`, `file_type`, `blocks`, `slides`, `sheets`, `pages`, `functions` など | 書式抽出、表、差分、コード読解、Evidence生成 | 可能 | 含まない | 安全に再利用可 |
| Markdown | `data/processed/share/**/*.md` | EDA012-019 | 1元ファイル1Markdown | 見出し、ページ・スライド・セルなどの注釈付き本文 | LLM文脈、全文検索、差分比較 | 可能 | 含まない | 安全に再利用可 |
| シートCSV | `data/processed/share/**/*.xlsx.sheets/*.csv` | EDA014 | 1シート1CSV | 元シート列、行データ | 表探索、計算、フィルタ | 可能 | 含まない | 安全に再利用可 |
| 正規化表CSV | `data/processed/share/**/*.data.csv` | EDA014 | 1表1CSV | 元CSV/TSV/XLSX由来の列 | 計算・集計 | 可能 | 含まない | 安全に再利用可 |
| 統合JSONL | `data/processed/embedding/embedding_records.jsonl` | EDA020 | 段落・スライド・ページ・シート・コード・画像などの検索単位 | `record_id`, `record_type`, `source_path`, `text_for_embedding`, `metadata` | `SearchRecord` の主入力、BM25/embedding共通入力 | 可能 | 含まない | 安全に再利用可 |
| 画像OCR結果 | `EDA/EDA047/tables/image_to_text_results.csv` | EDA047 | 1画像1行 | `image_path`, `model`, `success`, `search_text`, `record_json` | 画像SearchRecord補強 | 可能だがAPI費用あり | 含まない | 既存結果は安全に再利用可 |
| PDFページVision OCR | `EDA/EDA052/tables/pdf_page_vision_ocr_results.csv` | EDA052 | 1PDFページ1行 | `raw_pdf_path`, `page`, `image_path`, `search_text`, `record_json` | テキストなしPDFのSearchRecord補強 | 可能だがAPI費用あり | 含まない | 既存結果は安全に再利用可 |
| 質問正規化結果 | `data/processed/share/share/質問回答/questions_test_expanded.csv` | EDA061 | 1質問1行 | `index`, `question` | test質問の略語展開済み入力 | 可能 | test質問文を含むが回答は含まない | 提出時入力として安全 |
| 略語置換ログ | `EDA/EDA061/abbreviation_replacement_log.csv` | EDA061 | 1置換語1行 | `index`, `token`, `replacement`, `count` | 正規化の監査、検索語拡張 | 可能 | 回答は含まない | 安全に再利用可 |
| route分類結果 | `EDA/EDA063/tables/test_question_classification.csv` | EDA063 | 1質問1行 | `primary_route`, `sub_route`, `required_file_types`, `requires_calculation`, `requires_code_execution`, `confidence` | 暫定route、必要ファイル形式の初期値 | 可能だがAPI呼び出しが必要 | test質問分類を含むが回答は含まない | 設計・初期実装では安全に参照可 |
| 検索ログ | `EDA/EDA021/tables/test_rag_retrieval.csv` | EDA021 | 1質問のTopK検索結果行 | `index`, `question`, `rank`, `record_type`, `source_path`, `score` など | BM25挙動の参考、スコア設計 | 可能 | test質問に対する検索結果を含む | 評価用参照のみ。提出時は再検索する |
| valid診断 | `EDA/EDA023/tables/valid_local_rag_diagnosis.csv` | EDA023 | 1valid質問1行 | `route`, `gold_answer`, `predicted_answer`, `top1_source_path`, `failure_type` | valid 30問の確認項目、検索失敗分析 | 可能 | valid正解を含む | 実装には使わず、評価設計の参照のみ |
| 契約横断台帳 | `data/processed/share/share/契約管理/*.csv` | EDA062 | 契約、支払、月次、金額比較 | `project_name`, `contract_start_date`, `gross_amount_yen`, `source_file` など | 契約・支払・金額の横断集計 | 可能 | 含まない | 安全に再利用可 |
| 案件横断台帳 | `EDA/EDA050/tables/*.csv`, `EDA/EDA051/tables/*.csv`, `EDA/EDA057/tables/*.csv` | EDA050, EDA051, EDA057 | アクション、役割、契約、スケジュールなど | `project`, `source_path`, `action_id`, `role_names`, `approval_level` など | cross_file_aggregationの補助 | 可能 | 一部probe回答ファイルは含む | inventory系は安全。probeは参照のみ |
| 回答根拠ログ | `EDA/EDA058/tables/answer_source_audit.csv` | EDA058 | 1test質問1行 | `index`, `answer`, `source_stage`, `source_paths`, `source_confidence`, `evidence` | EvidenceRecord設計、監査項目の参考 | 再生成は可能 | test回答を含む | 実装には使わず、スキーマ設計の参考のみ |
| 質問・回答・ソース確度 | `EDA/EDA059/tables/question_answer_source_confidence.csv` | EDA059 | 1test質問1行 | `question`, `answer`, `source_files`, `source_confidence`, `answer_status` | 人手確認・監査の参考 | 可能 | test回答を含む | 実装には使わない |
| human review | `EDA/human_review.csv` | EDA060 | 1test質問1行 | `current_answer`, `source_files`, `human_answer`, `human_review` | 手動評価用 | 可能 | test回答・人手記入欄を含む | 提出用パイプラインでは使用しない |

## 設計修正

### 質問分類とファイル検索の流れ

当初設計では、質問正規化、ファイル検索、route分類を順番に並べていた。調査結果を踏まえ、責務とログは分離しつつ、完全な一方向処理にはしない。

基本の流れは次に修正する。

1. 質問の暫定解析
2. 暫定routeと必要ファイル形式の推定
3. 候補ファイル検索
4. 検索結果を使ったrouteの再評価
5. 最終実行計画の確定

理由は、質問文だけではrouteが曖昧でも、検索結果に `xlsx.structure.json` や `pptx` の差分候補が出ることで、`table_lookup`、`format_extraction`、`diff_comparison` の判断が変わるためである。

### 複数routeの扱い

質問は単一routeだけでなく、複数routeを順番に実行できる形にする。

例:

```json
{
  "primary_route": "calculation",
  "sub_routes": [
    "format_extraction",
    "table_lookup",
    "calculation"
  ],
  "execution_order": [
    "format_extraction",
    "table_lookup",
    "calculation",
    "answer_formatting"
  ]
}
```

この形式にすると、黄色セルを抽出してから表の行文脈を取り、最後に差分や割合を計算するような質問を自然に扱える。

### 会社名がない質問の扱い

会社名が質問文にない場合でも、即座に全社横断質問とは判断しない。

先に次の情報で案件を絞れるか確認する。

- 資料名
- タスクID、アクションID、マイルストーンID
- 列名、パラメータ名、モデル名
- 日付
- 略称
- ファイル名に含まれる固有語
- 社内管理資料にある用語

それでも絞れない場合だけ、全案件を候補にする。  
この方針は、READMEの「条件に該当する情報が存在しない場合は該当なしと答える」方針とも相性がよい。

### ファイル台帳と検索レコードの分離

次の2種類を分けて管理する。

- 1ファイル1レコードのファイル台帳
- 段落、表、スライド、ページ、シート、コード、画像単位の検索レコード

既存成果物では、前者は `EDA/EDA001/tables/file_inventory.csv`、後者は `data/processed/embedding/embedding_records.jsonl` が近い。

`embedding_records.jsonl` は `record_type` が `metadata`, `pptx_slide`, `xlsx_sheet`, `table_file`, `notebook_cell`, `python_function`, `python_code_chunk`, `pdf_page`, `image` などに分かれており、`SearchRecord` の土台として再利用できる。

## 共通スキーマ案

### FileRecord

1ファイル1レコードの台帳。`file_inventory.csv` と各structure JSONのメタ情報を統合する。

```json
{
  "file_id": "file_...",
  "source_path": "share/共有ドライブ/プロジェクト/.../契約書.docx",
  "processed_markdown_path": "data/processed/share/.../契約書.docx.md",
  "structure_json_path": "data/processed/share/.../契約書.docx.structure.json",
  "file_name": "契約書.docx",
  "extension": ".docx",
  "file_type": "docx",
  "area": "プロジェクト",
  "project_name": "京橋信用ソリューションズ株式会社",
  "major_folder": "01.契約",
  "document_kind": "contract",
  "version_label": "",
  "document_date": null,
  "is_latest_candidate": true,
  "related_file_ids": [],
  "source_sha1": "..."
}
```

### SearchRecord

検索単位のレコード。`embedding_records.jsonl` をほぼそのまま取り込める。

```json
{
  "record_id": "pptx_slide_...",
  "file_id": "file_...",
  "record_type": "pptx_slide",
  "source_path": "share/共有ドライブ/プロジェクト/.../提案書.pptx",
  "text": "検索対象テキスト",
  "metadata": {
    "slide_number": 3,
    "sheet_name": null,
    "page_number": null,
    "structure_json_path": "data/processed/share/...structure.json",
    "processed_markdown_path": "data/processed/share/...md"
  },
  "search_terms": [],
  "quality_flags": []
}
```

### QuestionAnalysis

質問文の暫定解析結果。略語展開、会社候補、資料種別候補、route候補を持つ。

```json
{
  "index": 0,
  "question_original": "白峰信用リスク評価の提案書old.pptx...",
  "question_normalized": "白峰信用リスク評価株式会社の提案書old.pptx...",
  "replaced_terms": [
    {"token": "白峰信用リスク評価", "replacement": "白峰信用リスク評価株式会社"}
  ],
  "project_candidates": ["白峰信用リスク評価株式会社"],
  "document_hints": ["提案書old.pptx", "提案書.pptx"],
  "identifier_hints": [],
  "date_hints": [],
  "provisional_routes": ["diff_comparison"],
  "required_file_types": ["pptx"],
  "needs_multiple_files": true,
  "needs_cross_project": false
}
```

### CandidateFile

質問に対する候補ファイル。ファイル台帳と検索レコードのスコアを分けて保持する。

```json
{
  "index": 0,
  "file_id": "file_...",
  "source_path": "share/共有ドライブ/プロジェクト/.../提案書old.pptx",
  "rank": 1,
  "score": 18.5,
  "score_breakdown": {
    "project_match": 5.0,
    "file_name_match": 6.0,
    "document_kind_match": 3.0,
    "version_hint_match": 3.0,
    "content_match": 1.5
  },
  "matched_terms": ["白峰信用リスク評価株式会社", "提案書", "old"],
  "candidate_reason": "会社名、資料名、版情報が一致",
  "confidence": 0.88
}
```

### ExecutionPlan

候補ファイルとroute再評価後の実行計画。

```json
{
  "index": 0,
  "primary_route": "diff_comparison",
  "sub_routes": ["diff_comparison", "answer_formatting"],
  "execution_order": ["diff_comparison", "answer_formatting"],
  "candidate_file_ids": ["file_old", "file_new"],
  "candidate_search_record_ids": [],
  "required_tools": ["markdown_diff"],
  "requires_llm": true,
  "requires_vision_model": false,
  "requires_python_execution": false,
  "answer_format_hint": "変更箇所を簡潔に列挙",
  "plan_confidence": 0.84,
  "plan_reason": "oldと最新版のpptxが明示されている"
}
```

### EvidenceRecord

回答根拠として採用した単位。

```json
{
  "index": 0,
  "evidence_id": "ev_...",
  "file_id": "file_...",
  "record_id": "pptx_slide_...",
  "source_path": "share/共有ドライブ/プロジェクト/.../提案書.pptx",
  "evidence_type": "diff",
  "location": {
    "page": null,
    "slide": 5,
    "sheet": null,
    "cell": null,
    "line": null
  },
  "text": "根拠本文または差分内容",
  "score": 12.0,
  "used_by_route": "diff_comparison"
}
```

### AnswerResult

回答生成後の結果。今回の最初の実装範囲ではまだ作らないが、後続用に定義する。

```json
{
  "index": 0,
  "answer": "変更なし",
  "answer_status": "answered",
  "primary_route": "diff_comparison",
  "evidence_ids": ["ev_..."],
  "source_files": ["share/共有ドライブ/プロジェクト/.../提案書.pptx"],
  "source_confidence": "medium",
  "error": null,
  "model": "openai/gpt-oss-20b:free",
  "created_at": "2026-07-12T00:00:00+09:00"
}
```

### RunRecord

1実行の監査ログ。

```json
{
  "run_id": "20260712_000000_plan_only",
  "mode": "planning_only",
  "input_questions": "data/processed/share/share/質問回答/questions_test_expanded.csv",
  "file_inventory": "EDA/EDA001/tables/file_inventory.csv",
  "search_records": "data/processed/embedding/embedding_records.jsonl",
  "outputs": {
    "question_analysis": "data/processed/runs/.../question_analysis.jsonl",
    "candidate_files": "data/processed/runs/.../candidate_files.jsonl",
    "execution_plans": "data/processed/runs/.../execution_plans.jsonl"
  },
  "question_count": 100,
  "api_calls": 0,
  "status": "completed",
  "warnings": []
}
```

### Python実装方式の比較

凡例: 各行はPythonでスキーマを表現する方式を表す。`推奨度` はこのプロジェクトでの初期実装に対する相性を示す。

| 方式 | 長所 | 短所 | 推奨度 |
|---|---|---|---|
| `dataclass` | 標準ライブラリだけで使える。軽い。JSONL保存用の辞書化もしやすい | 実行時バリデーションは自前実装が必要 | 高 |
| `TypedDict` | 既存CSV/JSONLの辞書処理と相性がよい。型ヒントとして軽い | 実体はdictなので、不正値を実行時に防げない | 中 |
| Pydantic | JSONスキーマ、バリデーション、型変換が強い | 現在の依存に入っていない。追加依存が必要 | 後段で検討 |

推奨は、初期実装では `dataclass` を中心にし、CSV/JSONLとの接続部だけ `dict` に変換する方式。  
理由は、`pyproject.toml` の依存を増やさずに済み、まずは計画保存までを小さく作れるため。Pydanticは、LLM出力JSONの検証が本格化した段階で追加検討する。

## 最初の実装範囲の具体化

今回の次段階で実装する範囲は、回答生成なしの計画作成までに限定する。

```text
質問読み込み
↓
略語展開
↓
暫定route分類
↓
候補ファイル検索
↓
最終route・実行計画作成
↓
中間結果JSONL保存
```

### 変更・新規作成するファイル案

まだ実装には入らないが、次回実装するなら以下に絞る。

```text
src/rag_competition/schemas.py
src/rag_competition/question_normalizer.py
src/rag_competition/inventory.py
src/rag_competition/file_resolver.py
src/rag_competition/task_router.py
src/rag_competition/planner.py
src/rag_competition/pipeline.py
```

この段階では `answerers/`、`llm_client.py`、`submission.py` は作らない。

### 再利用する既存コード

- `EDA061/eda061.py`: `read_glossary`, `expand_question`
- `EDA021/eda021.py`: `tokenize`, `BM25Index`
- `EDA011/eda011_pipeline_inventory.py`: `question_route` をルール分類の参考にする
- `EDA063/tables/test_question_classification.csv`: APIを呼ばず、暫定分類の既存結果として参照する
- `EDA041/eda041.py`: `score_path`、`path_hints` の考え方を参考にする

実装時はEDAファイルを直接importするのではなく、必要なロジックを提出用モジュール向けに小さく書き直す。EDAコードは実験用の入出力やtest残件依存が混ざるためである。

### 再利用する既存成果物

- `EDA/EDA001/tables/file_inventory.csv`
- `data/processed/embedding/embedding_records.jsonl`
- `data/processed/share/**/*.structure.json`
- `data/processed/share/**/*.md`
- `data/processed/share/**/*.xlsx.sheets/*.csv`
- `data/processed/share/share/質問回答/questions_test_expanded.csv`
- `EDA/EDA061/abbreviation_replacement_log.csv`
- `EDA/EDA063/tables/test_question_classification.csv`

valid確認では次も参照するが、実装ロジックには入れない。

- `EDA/EDA011/tables/question_routes.csv`
- `EDA/EDA023/tables/valid_local_rag_diagnosis.csv`

### 各関数の入出力案

凡例: 各行は次回実装する関数候補を表す。`入力` と `出力` は、上の共通スキーマ名または既存成果物名を示す。

| 関数 | 入力 | 出力 | 備考 |
|---|---|---|---|
| `load_questions(path)` | `questions_test.csv` または `questions_valid.csv` | `list[QuestionAnalysis]` の初期形 | originalだけを入れる |
| `normalize_questions(questions, glossary)` | 質問リスト、社内用語集 | `QuestionAnalysis` | 略語と正式名を両方保持 |
| `load_file_records(file_inventory, processed_root)` | `file_inventory.csv`, `data/processed/share` | `list[FileRecord]` | structure/markdown pathを補完 |
| `load_search_records(embedding_records)` | `embedding_records.jsonl` | `list[SearchRecord]` | record_type別にそのまま読み込む |
| `classify_provisional(question)` | `QuestionAnalysis` | `QuestionAnalysis` | 既存EDA063 CSVがあれば利用 |
| `resolve_candidate_files(question, file_records, search_records)` | 質問解析、台帳、検索レコード | `list[CandidateFile]` | 会社名なしでも資料名・ID・列名で絞る |
| `refine_route(question, candidates)` | 質問解析、候補ファイル | `ExecutionPlan` | 候補ファイルの拡張子・record_typeで再評価 |
| `save_jsonl(records, path)` | dataclassまたはdict | JSONL | 中間結果を保存 |

### 実行コマンド案

```bash
python -m rag_competition.pipeline --split test --mode plan-only
```

valid 30問で確認する場合:

```bash
python -m rag_competition.pipeline --split valid --mode plan-only
```

### valid 30問での確認項目

- 30問すべてに `QuestionAnalysis` が作成される
- 略語展開のログが残る
- 暫定routeが `EDA011/tables/question_routes.csv` のrouteと大きく矛盾しない
- 各質問に候補ファイルが1件以上出る
- 会社名がない質問で、全案件横断に飛ばす前に資料名・ID・列名・日付で候補を絞っている
- `ExecutionPlan` に `primary_route`, `sub_routes`, `execution_order` が入る
- valid正解や手動回答を中間JSONLに混入させない

### 完了条件

- API呼び出しなしで plan-only が完走する
- `question_analysis.jsonl`, `candidate_files.jsonl`, `execution_plans.jsonl`, `run_record.json` が出力される
- 各質問について、候補ファイル上位とroute判断理由が追跡できる
- `FileRecord` と `SearchRecord` が別スキーマとして扱われている
- test/validの個別正解や過去提出回答をコードへ埋め込んでいない

### テスト方法

- `python -m py_compile` で新規モジュールの構文確認
- 小さいユニット確認:
  - 社内用語集から略語辞書を読める
  - `questions_test_expanded.csv` と同じ展開結果になる
  - `file_inventory.csv` からFileRecordを作れる
  - `embedding_records.jsonl` からSearchRecordを作れる
  - 代表的な質問で候補ファイルが空にならない
- valid 30問で plan-only を実行し、route分布と候補ファイル数を集計する
- 出力JSONLに `gold_answer`, `human_answer`, `current_answer` が含まれていないことを確認する

## 次の1回で実装すべき範囲

次の1回で実装する範囲は、`FileRecord` と `SearchRecord` の読み込み、および `QuestionAnalysis` から `ExecutionPlan` までを保存する plan-only パイプラインに絞る。

理由は、回答生成より前に「どの資料を見に行くか」と「どの処理順で答えるか」が最も失敗原因になっているため。既存EDAでも、単純BM25やLLM単体より、資料特定・route分岐・根拠圧縮の改善が効果を出している。ここを先にJSONLで監査可能にすると、その後のanswerer実装を小さく安全に進められる。

## Formal Regression Baseline: Gate 15

The active formal regression baseline is the deterministic Gate-15 baseline.

- valid: 17 correct / 0 incorrect / 13 blank
- test: 100 complete / 0 errors
- Gate: 15 allowed / 85 suppressed
- allowed IDs: 2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92
- cumulative additions from the former Gate-10 baseline: 4, 39, 56, 63, 83
- test 10, test 0, and test 85 remain suppressed
- Unit: 125 tests or more must pass

The 15 answers must be regenerated from runtime routes and structured Evidence.
Human review records are evaluation metadata only and must not be used as runtime,
Verification, or Gate input. The authoritative artifact set is kept in
`data/output/confirmed_gate_baseline_and_next_capability_v1/analysis/`.

