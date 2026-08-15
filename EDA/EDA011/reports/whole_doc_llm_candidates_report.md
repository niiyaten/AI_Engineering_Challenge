# EDA011: 文書全体LLM候補整理

EDA010で文書全体コンテキスト内にvalid正解語句が含まれた質問を、LLM回答検証の候補として整理しました。

- 候補件数: 4
- 推奨モデル: `openai/gpt-oss-20b:free`
- 今回は外部API呼び出しは行わず、候補整理に留めています。

## 候補一覧

| index | answer | target_document_path | context_chars | context_path |
| --- | --- | --- | --- | --- |
| 2 | Recall | プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx | 4943 | EDA/EDA010/contexts/valid_002_whole_document_context.md |
| 5 | 対象外（契約明記） | プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx | 6356 | EDA/EDA010/contexts/valid_005_whole_document_context.md |
| 17 | 未連絡 | プロジェクト/京橋信用ソリューションズ株式会社/03.データ/カラム説明.md | 1166 | EDA/EDA010/contexts/valid_017_whole_document_context.md |
| 29 | 3年間 | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/01.契約/契約書.docx | 9038 | EDA/EDA010/contexts/valid_029_whole_document_context.md |

凡例: `index` はvalid質問番号、`answer` はvalid正解、`target_document_path` は対象文書、`context_chars` はLLM入力文字数、`context_path` は生成済みMarkdownを表します。
