# 実務RAG Blueprint

## 推奨する基本構成

```text
User
 ↓
Query Understanding
 ↓
Metadata / ACL Filter
 ↓
BM25 ─────┐
           ├→ RRF → Reranker → Context → LLM → Evidence/Citation
Vector ────┘
                         │
                         └→ 必要時のみ Executor / Tool
```

## Vector RAGで扱うもの

- 規格・標準・手順の検索
- 過去報告書の類似事例検索
- 背景・理由・経緯の説明
- 複数文書の要約
- 関連資料の案内

## Tool / Executorへ回すもの

- Excel / CSVのfilter・groupby・集計
- 数式・統計計算
- 版間diff
- JSON / Codeの構造比較
- Office書式や位置関係
- OCRが必要な表・図

## Retrieval

1. Query normalization
2. 略称・同義語展開
3. ACL / project / document_type / status / date filter
4. BM25 + Vector
5. RRF
6. Reranker
7. Parent context expansion
8. LLMへ投入

## Indexする文書

原則：`approved AND latest`

必要に応じて別indexまたはfilterで、

- draft
- obsolete
- raw data
- intermediate artifacts

を切り分ける。

## 文書作成ルール

- 一意なdocument_id
- タイトル、目的、適用範囲を明記
- 見出し階層を使う
- 1セクション1トピック
- 略語は初出で定義
- 表の列名に単位を持つ
- 色だけに意味を依存しない
- グラフは元データとcaptionを残す
- 「上記」「同条件」だけに依存しない
- Draft / Approved / Obsoleteを明示
- 権限metadataを付ける

## 最低限の評価指標

### Retrieval
- Recall@K
- MRR / nDCG（必要なら）
- 正しい文書・sectionがTop-Kに入る率

### Answer
- Groundedness
- Citation correctness
- Answer completeness
- Abstain precision

### Operation
- indexing latency
- query latency
- stale document率
- ACL違反 0件

## 小規模PoCの始め方

1. 承認済み資料100〜500件に限定
2. 代表質問30〜50問をGolden Set化
3. BM25 baselineを作る
4. Vectorを追加
5. Hybrid + rerankerを比較
6. 誤答を「検索失敗 / 読解失敗 / 業務処理失敗」に分類
7. 業務処理失敗だけTool化
