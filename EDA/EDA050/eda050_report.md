# EDA050: 会議録/アクションID台帳

## 背景と目的

EDA048では、会議録/アクションID構造化が残件16件中4件を占めた。
EDA050では、`05.会議` 配下の会議録と報告資料をページ単位に分解し、meeting_id、日付、ページ、アクションID、コメント、チェックポイントを台帳化する。

## 結果

- ページレコード数: 166
- アクションID周辺レコード数: 213
- チェックポイント/タスク候補レコード数: 95
- no text PDFファイル数: 14
- 残件4問の候補生成数: 4

## 残件候補

凡例: `candidate_answer` はローカル台帳から抽出した回答候補、`needs_review` は提出採用前に確認が必要かを表す。

|   index | candidate_answer   | needs_review   |
|--------:|:-------------------|:---------------|
|      18 |                    | True           |
|      49 |                    | True           |
|      93 |                    | True           |
|      96 |                    | False          |

## 出力

- ページ台帳: `EDA/EDA050/tables/meeting_page_inventory.csv`
- アクション台帳: `EDA/EDA050/tables/meeting_action_inventory.csv`
- チェックポイント/タスク台帳: `EDA/EDA050/tables/checkpoint_task_inventory.csv`
- no text PDF台帳: `EDA/EDA050/tables/no_text_pdf_inventory.csv`
- 残件候補: `EDA/EDA050/tables/meeting_action_question_probe.csv`

## 注意

PDF由来のアクション表は改行で崩れている箇所がある。
提出用に使う場合は、今回の周辺文脈候補をさらに表形式へ整形するか、該当ページだけLLMへ渡して短答化する。
