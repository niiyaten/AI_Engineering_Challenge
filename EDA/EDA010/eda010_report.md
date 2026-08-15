# EDA010: 文書単位LLMコンテキストの検証

## 目的・背景

EDA009で対象文書を推定できた質問について、チャンクTopKではなく文書全体をLLM向けMarkdownにした場合に、正解語句が文書内に含まれるか、無料LLMへ渡せる長さかを確認します。ここではLLM APIは呼びません。

## 実行設定

- char_limit: 24000
- 入力: `EDA/EDA009/tables/valid_guided_retrieval_comparison.csv`
- 文書本文: `EDA/EDA002/texts/extracted_documents.jsonl`, `EDA/EDA004/texts/extracted_documents.jsonl`

## 集計

| metric | value |
| --- | --- |
| target_questions | 8.0 |
| document_found | 8.0 |
| answer_hit_whole_document | 4.0 |
| answer_hit_context | 4.0 |
| clipped_by_char_limit | 1.0 |
| mean_document_chars | 9723.1 |
| max_document_chars | 38748.0 |

凡例: `metric` は集計指標、`value` は対象質問または文書単位での件数・文字数を表します。

## valid_002の確認

| index | answer | target_document_path | document_chars | answer_hit_whole_document | answer_hit_context | context_path |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | Recall | プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx | 4943 | True | True | EDA/EDA010/contexts/valid_002_whole_document_context.md |

凡例: `target_document_path` はEDA009で選ばれた文書、`answer_hit_whole_document` は文書全体に正解語句が含まれるか、`answer_hit_context` は文字数上限後のLLM入力に正解語句が含まれるかを表します。

## 対象質問一覧

| index | document_hints | answer | document_found | document_chars | answer_hit_context | target_document_path |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 提案書 | Recall | True | 4943 | True | プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx |
| 5 | 報告書 | 対象外（契約明記） | True | 6356 | True | プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx |
| 9 | 提案書 | QAレビューア：池田 直哉 → 小林 直樹 | True | 8974 | False | プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/ニューヨーク不動産市場の最新動向調査.pdf |
| 10 | 報告書 | 0値の疑似欠損 | True | 404 | False | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf |
| 17 | カラム説明 | 未連絡 | True | 1166 | True | プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md |
| 25 | 提案書 | 1. データ理解・EDA | True | 38748 | False | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx |
| 27 | 報告資料 \| 報告書 | 0.010301 | True | 8156 | False | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf |
| 29 | 契約書 | 3年間 | True | 9038 | True | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/01.契約/契約書.docx |

凡例: `document_hints` は質問から検出した対象文書名、`document_found` は文書単位本文を取得できたか、`document_chars` は文書本文の文字数を表します。

## 考察

- 文書指定があるdocument_qaでは、チャンクTopKより文書全体コンテキストの方が根拠漏れを減らせる可能性があります。
- ただし、文書全体が長すぎる場合は、章・スライド単位の再ランキングが必要です。
- 表計算、書式、画像、差分が必要な質問は、文書全体をLLMに渡すだけでは不十分です。