# EDA067: 旧SIGNATE_Agentic_RAG本体のスナップショット

## 目的

完成版 `AI_Engineering_Challenge` へ移行する前の `SIGNATE_Agentic_RAG` 本体を、再評価用のEDA資料として保存する。最終パイプラインの実行経路とは分離する。

## 保存対象

- 旧RAGの `src/`、`rag_competition/`、`scripts/`、`tests/`
- `config/`、`docs/`、`evaluation/`、`submissions/`、`SKILLS/`
- 旧README、`pyproject.toml`、`uv.lock`、`.gitignore`

## 保存しない対象

- `data/raw/`、`data/interim/`、`data/processed/`、`data/output/`、`data/work/`
- 仮想環境、uvキャッシュ、APIキー、Git内部データ

これらは大容量の原本・中間生成物・ローカル状態である。完成版は `materials/share.zip` を唯一の入力としてコールドスタート実行できるため、旧データは再現の必須条件ではない。

## 旧リポジトリ情報

- Remote: `https://github.com/niiyaten/SIGNATE_Agentic_RAG.git`
- Local branch at migration: `master`
- Local HEAD at migration: `e87d565 Document Gate 15 pipeline inventory`

旧リポジトリの履歴そのものはGitHub側に残る。このEDAは、完成版リポジトリ内から旧実装の設計と検証を参照するためのスナップショットである。
