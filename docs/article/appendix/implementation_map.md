# 記事と実装概念の対応

この公開プロジェクトはQiita記事用に抽象化しています。コンペ版の固有データ・問題文は含めません。

| 記事内概念 | コンペ版での役割 | 実務版での置き換え |
|---|---|---|
| DocumentStore | 複数形式資料の構造抽出 | Ingestion / Parsing / Metadata Enrichment |
| Question Planner | 質問ルーティング | Query understanding / Router |
| Specialized Executor | 高リスク定型処理 | Tool / Function calling |
| Generalization Executor | 操作単位の汎用処理 | 業務ロジック / Python Tool |
| Base Recovery | 汎用fallback | Hybrid Retrieval + LLM |
| Evidence Gate | 根拠検証 | Citation / Grounding / Validation |
| Cold Start | 100問再現性確認 | Regression test / Golden set |
