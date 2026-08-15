# valid_008 LLM Context

## Question
蒼泉会 ひがし丘総合病院の契約条件において、仮に実績工数が見込工数の4分の3だった場合、最終請求金額（税込）は見込金額（税込）よりいくら少なくなりますか。

## Validation Answer
1,168,750円

## Diagnosis
- required_capability: document_qa
- context_quality_for_llm: needs_better_retrieval
- answer_hit_top5: False
- recommended_next_step: 抽出対象と検索重みを見直す

## Retrieved Evidence

### Evidence 1
- score: 251.3034
- source_eda: EDA004
- extension: .pptx
- project_name: 医療法人社団 蒼泉会 ひがし丘総合病院
- major_folder: 00.提案
- relative_path: プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx

```text
ラフト | 契約条件、精算条件、変更条件 | 契約実務 table_
row_004: スケジュール | 5週間の作業計画 | 進行管理 table_
row_005: 議事録 | 会議決定事項、宿題、論点 | 合意記録 table_
row_006: 中間報告 | 基礎集計、初期示唆、モデル途中結果 | 方針確認 table_
row_007: 最終報告 | 分析結果、評価結果、示唆、次フェーズ提言 | 成果報告 table_
row_008: 分析計画書/作業メモ | 前処理、学習、評価、解釈の手順整理 | 再現性確保 table_
row_009: 課題管理表 | 論点、課題、対応状況 | 進行管理 table_
row_010: 目的変数定義メモ | chargesの定義固定 | 用語統一 table_row_011...
```

### Evidence 2
- score: 234.3781
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 蒼泉会 ひがし丘総合病院
- major_folder: 01.契約
- relative_path: プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/01.契約/契約書.docx

```text
請求単位はhourとする。
## paragraph_073 - style: Compact 時間単価は25,000円（消費税別）とする。
## paragraph_074 - style: Compact 想定総工数は170時間とする。
## paragraph_075 - style: Compact 見込金額は、税抜4,250,000円、消費税425,000円、税込4,675,000円とする。
## paragraph_076 - style: Compact 前項の見込金額は170時間を前提とした見込額であり、契約総額を固定するものではない。最終請求額は、実績工数に時間単価を乗じ、これに消費税を加算した金額とする。
## paragraph_077 - style: Heading 3 6.3 工数記...
```

### Evidence 3
- score: 211.5582
- source_eda: EDA004
- extension: .pdf
- project_name: 医療法人社団 蒼泉会 ひがし丘総合病院
- major_folder: 06.報告書
- relative_path: プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf

```text
意記録 中間報告 作成済み 進捗共有 最終報告 本書 最終成果報告 分析計画書/分析作業メモ 作成対象 再現性確保 課題管理表 作成対象 論点管理 目的変数定義メモ 作成対象 用語統一 データ前処理仕様メモ 作成対象 実装整合 モデル評価サマリ 作成対象 評価記録 主要仮定一覧 作成対象 追跡可能性確保 本報告で確認できる到達内容 1 プロジェクト前提の固定 2 中間報告時点の試行結果共有 3 最終分析出力の評価値確認 4 変更管理差分の整理 5 今後の運用・拡張提言の明文化
## page_017 11. 提案・契約との差分管理 提案・契約との差分管理 管理対象 差分有無 評価 成果物 なし 整合 スコープ なし 整合 KPI/受入基準 なし 整合 契約形態・支払条件 なし 整合 モデル方針 あり 管理下変更...
```

### Evidence 4
- score: 187.853
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 蒼泉会 ひがし丘総合病院
- major_folder: 05.会議
- relative_path: プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/05.会議/報告資料/報告資料_2025-07-08.docx

```text
: 見込金額（税込） | 4,675,000円
row_008: 精算方式 | 実績工数に基づく事後精算（月次精算）
## table_008
row_001: 支払回 | マイルストーン | 金額（税込） | 条件
row_002: 1 | 第1回実績精算 | 4,675,000円 | 契約締結後5営業日以内
## table_009
row_001: 管理対象 | 実施事項 | 対応タスク | 期限目安
row_002: 会議記録 | キックオフ議事録作成・配布 | T02 | 早期対応
row_003: データ確認 | 対象データとカラム定義の整合確認 | T03 | 2025-07-10
row_004: 分析計画 | 前処理・評価・解釈手順の詳細化 | T04 | 2025-07-11 row_005...
```

### Evidence 5
- score: 175.6118
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 蒼泉会 ひがし丘総合病院
- major_folder: 05.会議
- relative_path: プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/05.会議/報告資料/報告資料_2025-07-08.docx

```text
確定不可
## table_004
row_001: 項目 | 値
row_002: 対象ファイル | data\train.csv
row_003: 行数 | 1,600
row_004: 列数 | 8
row_005: 欠損件数 | 全列0件
row_006: 文字コード | utf-8-sig
## table_005
row_001: 項目 | 状況
row_002: 分析実装ステータス | planning_only
row_003: モデル結果公開可否 | no_model_results
row_004: visible_trials | 0件
row_005: best_visible_trial | なし
row_006: 評価指標実績値 | 未公開 / 未報告
row_007: 最終採用モデ...
```
