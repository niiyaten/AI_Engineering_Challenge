# EDA011: 回答ポリシー設計

Incorrectが-1点になることを踏まえ、route別に安全側の回答方針を整理しました。

| route | answer_policy | valid_count |
| --- | --- | --- |
| code_reading | コード全文または該当関数をLLMへ渡す | 4 |
| diff_check | 版比較が未実装ならわかりません | 1 |
| document_whole_context | LLMで文書内根拠から短く回答 | 7 |
| fallback_bm25_llm | BM25根拠が弱い場合はわかりません | 8 |
| format_extraction | 書式メタデータから抽出し、不明ならわかりません | 2 |
| image_ocr | OCR/画像理解が未実装ならわかりません | 1 |
| table_calculation | pandas/openpyxlで計算結果を回答 | 7 |

凡例: `route` は処理ルート、`answer_policy` は回答生成方針、`valid_count` はvalid質問数を表します。
