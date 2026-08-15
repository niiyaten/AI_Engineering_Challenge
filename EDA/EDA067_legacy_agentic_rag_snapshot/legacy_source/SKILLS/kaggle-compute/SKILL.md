---
name: kaggle-compute
description: Run code on Kaggle's free GPU/TPU compute via Kaggle Notebooks (Kernels) using the Kaggle API/CLI. Use when the user wants to use Kaggle compute resources, push and run a notebook or script as a Kaggle kernel, enable GPU/TPU, attach datasets, or retrieve kernel outputs.
allowed-tools: Bash(kaggle:*), Bash(uv run kaggle:*)
---

# Kaggle 計算リソース利用（Notebook / Kernel）

Kaggle の無料 GPU/TPU を使って計算を回す手順書。ローカルのコード（`.ipynb` または `.py`）を **Kernel** として Kaggle に push → クラウドで実行 → 出力を回収する。

## 前提

- Kaggle 無料枠の目安: **GPU 週 ~30h**、**CPU/Notebook セッションは 1 回あたり最大 ~12h**（GPU 時は ~9h）。週次でリセット
- Kernel = Kaggle Notebook。CLI からは `.ipynb`（type=notebook）か `.py`（type=script）を push できる
- 認証は [kaggle-data](#) スキルの Setup と共通（`~/.kaggle/kaggle.json`）。CLI は `uv run kaggle ...` で実行

## Setup

```bash
uv add kaggle    # 未インストールなら
```

## 全体フロー

```bash
# 1. 作業フォルダを用意しメタデータ雛形を生成
uv run kaggle kernels init -p ./my_kernel

# 2. 実行したいコードを置く（例: my_kernel/run.py または run.ipynb）
#    + kernel-metadata.json を編集（下記参照）

# 3. push（アップロード＝即実行キューに投入される）
uv run kaggle kernels push -p ./my_kernel

# 4. ステータス確認（complete / running / error）
uv run kaggle kernels status <username>/<kernel-slug>

# 5. 出力を回収
uv run kaggle kernels output <username>/<kernel-slug> -p ./my_kernel/output
```

## kernel-metadata.json

`kernels init` で生成される。主要フィールド:

```json
{
  "id": "<username>/<kernel-slug>",
  "title": "My Kernel",
  "code_file": "run.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": false,
  "enable_tpu": false,
  "enable_internet": true,
  "dataset_sources": ["<owner>/<dataset-slug>"],
  "competition_sources": ["<competition-slug>"],
  "kernel_sources": []
}
```

| フィールド | 説明 |
|---|---|
| `id` | `<username>/<kernel-slug>`。username は kaggle.json と一致させる |
| `code_file` | 実行するファイル名（`.py` か `.ipynb`） |
| `kernel_type` | `script`（.py）または `notebook`（.ipynb） |
| `enable_gpu` | `true` で GPU 割り当て（T4 x2 等） |
| `enable_tpu` | `true` で TPU 割り当て（GPU とは排他） |
| `enable_internet` | pip install 等で外部通信が必要なら `true` |
| `dataset_sources` | 入力データセット。`/kaggle/input/<dataset-slug>/` にマウントされる |
| `competition_sources` | 入力コンペデータ。`/kaggle/input/<competition-slug>/` にマウントされる |
| `kernel_sources` | 他 Kernel の出力を入力にする場合 |

## GPU / TPU を有効化

`kernel-metadata.json` で切り替えるだけ:

```json
{ "enable_gpu": true,  "enable_tpu": false }   // GPU
{ "enable_gpu": false, "enable_tpu": true  }   // TPU（GPU とは併用不可）
```

push 後はクラウド側で自動的にアクセラレータ付きセッションが起動する。

## データの入出力

- **入力**: `dataset_sources` / `competition_sources` に指定したものが実行時に `/kaggle/input/...` へ読み取り専用でマウントされる。コード内ではこのパスを参照する
- **出力**: Kernel コードは **`/kaggle/working/`** に成果物（モデル・予測 CSV 等）を書き出す。`kaggle kernels output` で回収できるのはこのディレクトリの内容

```python
# Kernel 内のコード例
import pandas as pd
df = pd.read_csv("/kaggle/input/<competition-slug>/train.csv")
# ... 学習 ...
preds.to_csv("/kaggle/working/submission.csv", index=False)
```

## 実行状況の確認とログ

```bash
# ステータス（running / complete / error）
uv run kaggle kernels status <username>/<kernel-slug>

# 実行ログ込みで出力を取得（エラー時のデバッグ）
uv run kaggle kernels output <username>/<kernel-slug> -p ./out
# → ./out に成果物と <kernel-slug>.log が落ちる
```

push 後は非同期実行。`status` が `complete` になるまでポーリングする（長時間ジョブは数分〜数時間）。

## 既存 Kernel を取得・更新

```bash
# 既存 Kernel をローカルに pull（コード + metadata）
uv run kaggle kernels pull <username>/<kernel-slug> -p ./my_kernel -m

# 編集して再 push（同じ id なら上書き＝新バージョン）
uv run kaggle kernels push -p ./my_kernel
```

## Troubleshooting

- **`kaggle: command not found`**: `uv run kaggle` を使う。未インストールなら `uv add kaggle`
- **push が即エラーになる**: `kernel-metadata.json` の `id` の username が kaggle.json と不一致／`code_file` 名が実ファイルと不一致
- **データが読めない**: `dataset_sources`/`competition_sources` の指定漏れ、またはコード側のパスが `/kaggle/input/...` になっていない
- **pip install が失敗**: `enable_internet: true` になっているか確認
- **GPU が割り当たらない**: 週次クォータ超過の可能性。`enable_gpu` を false にして CPU で回すか週リセットを待つ
- **出力が空**: 成果物を `/kaggle/working/` 以外に書いている。書き出し先を確認
