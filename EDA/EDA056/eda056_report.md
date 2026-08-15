# EDA056: 会議録コメント・運用条項・スケジュール差分route

## 背景と目的

EDA055後に残った `わかりません` 9件のうち、会議録コメント、運用条項、スケジュール差分に該当する3件をローカル処理で確認した。
LLMには投げず、raw docx、processed Markdown、processed CSVを直接読んで、提出候補として採用できる回答だけをEDA055候補に上書きする。

## 結果

- EDA055時点の `わかりません`: 9
- EDA056後の `わかりません`: 6
- 追加採用: 3

| index | route | 採用回答 | confidence | needs_review |
| --- | --- | --- | --- | --- |
| 49 | docx_comment_range_extraction | WBS・進捗管理台帳確定（タスク割振・ガント更新） | high | False |
| 52 | operation_clause_lookup | 契約範囲外の追加対応 | medium | True |
| 95 | structured_schedule_diff_filter | T15「モデル評価・重要特徴量整理」の担当者が、渡辺 遥から渡辺 遥 / 小林 直樹に変更された。 | high | False |

凡例: `index` はtest質問ID、`route` は今回の処理名、`採用回答` は提出候補に反映した回答、`confidence` は根拠の強さ、`needs_review` は最終提出前に人手確認したい候補かどうかを表す。

## 処理内容

- index 49: raw docxの `word/comments.xml` と `word/document.xml` を対応付け、コメント本文ではなく、コメント範囲が付与された本文を抽出した。
- index 52: みなみ野の提案書と契約書から、契約範囲外の追加対応が別途対応・別紙見積で扱われる条項を抽出した。ただし、資料内では「別契約」という完全一致語ではなく「別途対応」「別紙見積」と表現されているため、needs_review=Trueとした。
- index 95: `スケジュール_r1.xlsx` と `スケジュール_r2.xlsx` をタスクIDで比較し、未着手から完了へのステータス変更と番号表記差を除外して、案件遂行に関連する差分だけを残した。

## 出力

- route結果: `EDA/EDA056/tables/eda056_route_results.csv`
- 提出候補CSV: `EDA/EDA056/predictions/eda056_meeting_operation_schedule_predictions.csv`
- 提出候補zip: `EDA/EDA056/predictions/eda056_meeting_operation_schedule_submission.zip`

## 注意

index 52は「別契約」という語が直接資料に見つからないため、完全に安全な採用ではない。提出スコアを見る前に、`契約範囲外の追加対応` で評価されそうかを確認する余地がある。
