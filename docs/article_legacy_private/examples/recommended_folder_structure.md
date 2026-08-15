# RAG向け資料フォルダ構成例

```text
knowledge/
├── standards/                  # 規格・共通基準
├── procedures/                 # 標準手順
├── equipment/                  # 装置マニュアル・仕様
└── projects/
    └── PRJ-2026-012/
        ├── 00_meta/            # metadata / 用語集 / index対象設定
        ├── 10_plan/            # 計画・要求仕様
        ├── 20_execution/       # 実施記録・会議録
        ├── 30_data/            # 正本データ（必要に応じてRAG対象外）
        ├── 40_analysis/        # 分析結果・Notebook・中間成果物
        └── 50_report/          # 承認済み報告書
```

## 原則

- フォルダ構成は人間が探しやすいことを優先する。
- RAG側はフォルダ名だけで意味を判断せず、metadataへ正規化する。
- `Draft / Approved / Obsolete`を明示し、通常検索は`Approved + latest`を既定にする。
- 元データと派生成果物を分ける。
- 画像やグラフの元数値データを可能な限り残す。
