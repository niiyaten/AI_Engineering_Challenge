# Qiita記事プロジェクト：Document QA / RAG構築記 v2

コンペで構築した `Retrieval + Executor + Evidence Gate` 型Document QAを紹介し、さらに**実務へ持ち込む場合のVector / Hybrid RAG構成と、RAGが扱いやすい資料管理**までまとめた公開用プロジェクトです。

## ファイル構成

```text
qiita_rag_article_project_v2/
├── article.md
├── README.md
├── figures/                    # Qiita貼付用 PNG / SVG
│   ├── 01_architecture.*
│   ├── 02_document_pipeline.*
│   ├── 03_executor_router.*
│   ├── 04_evidence_gate.*
│   ├── 05_audit_cycle.*
│   ├── 06_route_breakdown.*
│   ├── 07_practical_rag_architecture.*
│   ├── 08_rag_friendly_document_management.*
│   └── 09_document_lifecycle.*
├── diagrams/                   # Graphviz DOT編集元
├── templates/
│   ├── document_metadata.yaml
│   └── chunk_metadata.yaml
├── examples/
│   ├── recommended_folder_structure.md
│   └── index_record.json
├── docs/
│   └── practical_rag_blueprint.md
└── appendix/
    ├── implementation_map.md
    ├── publication_checklist.md
    └── rag_readiness_checklist.md
```

## v2で追加した内容

- コンペ型Executor RAGを実務へどう転用するか
- Vector searchを主軸に戻す理由
- BM25 + Vector + Metadata Filter + RerankerのHybrid Retrieval
- Section-aware chunking / Parent-Child chunk
- RAG向けの文書作成ルール
- Draft / Approved / Obsoleteを含む版管理
- ACL / 権限metadataとsecurity filtering
- 更新差分だけを再embeddingする文書ライフサイクル
- 文書・chunk metadataのサンプル
- RAG Readiness Checklist

## Qiitaへ投稿するとき

`article.md`の画像は相対パスです。

```markdown
![実務向けRAGアーキテクチャ](./figures/07_practical_rag_architecture.png)
```

QiitaへPNGをアップロードし、発行された画像URLに差し替えてください。

## 図の再生成

Graphvizを使用しています。

```bash
dot -Tpng -Gdpi=180 diagrams/07_practical_rag_architecture.dot -o figures/07_practical_rag_architecture.png
dot -Tsvg diagrams/07_practical_rag_architecture.dot -o figures/07_practical_rag_architecture.svg
```

日本語フォントは `Noto Sans CJK JP` を指定しています。
