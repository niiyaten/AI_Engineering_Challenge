---
name: kaggle-data
description: Download Kaggle competition data and datasets via the Kaggle API/CLI. Use when the user needs to fetch Kaggle competition files, search or download datasets, or set up Kaggle data for a project.
allowed-tools: Bash(kaggle:*), Bash(uv run kaggle:*)
---

# Kaggle データ取得

Kaggle API (`kaggle` CLI) を使ってコンペデータ・データセットをダウンロードする。

## Setup

```bash
# インストール（このプロジェクトの依存に未追加なら）
uv add kaggle

# 認証情報: ~/.kaggle/kaggle.json （{"username":..., "key":...}）を配置済みなら設定不要
# 未配置の場合は kaggle.com → Account → Create New API Token で kaggle.json を取得し
#   ~/.kaggle/kaggle.json （Windows: %USERPROFILE%\.kaggle\kaggle.json）に置く
# 別ディレクトリに置く場合は環境変数で指定:
#   $env:KAGGLE_CONFIG_DIR = "C:/path/to/dir"
```

**Note**: 以降のコマンドは `uv run kaggle ...` で実行する（素の `kaggle` は PATH に無いことがある）。

## Competitions（コンペデータ）

```bash
# コンペ一覧／検索
uv run kaggle competitions list
uv run kaggle competitions list -s "titanic"

# コンペのファイル一覧
uv run kaggle competitions files <competition-slug>

# 全ファイルをダウンロード（zip でまとめて取得）
uv run kaggle competitions download -c <competition-slug> -p data/raw

# 単一ファイルのみ
uv run kaggle competitions download -c <competition-slug> -f train.csv -p data/raw

# 解凍（download は .zip で落ちる）
uv run kaggle competitions download -c <competition-slug> -p data/raw
# → data/raw/<competition-slug>.zip を展開
```

**Note**: 初回はブラウザで該当コンペの **Rules に同意（Join Competition）** していないと 403 になる。

`<competition-slug>` は URL の `kaggle.com/competitions/<slug>` の部分。

## Datasets（データセット）

```bash
# データセット検索
uv run kaggle datasets list -s "<keyword>"

# データセット内のファイル一覧
uv run kaggle datasets files <owner>/<dataset-slug>

# 全ファイルをダウンロード（--unzip で展開まで一括）
uv run kaggle datasets download <owner>/<dataset-slug> -p data/raw --unzip

# 単一ファイルのみ
uv run kaggle datasets download <owner>/<dataset-slug> -f <file> -p data/raw
```

`<owner>/<dataset-slug>` は URL の `kaggle.com/datasets/<owner>/<slug>` の部分。

## Discussion / Writeup（議論・解法）

コンペの discussion トピックや解法 writeup は **topic として API で取得できる**（ブラウザ不要）。
URL `kaggle.com/competitions/<slug>/writeups/...` や `.../discussion/<id>` の中身もこれで取れる。

```bash
# 1. トピック一覧から目的のトピック ID を探す
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 uv run kaggle competitions topics list <competition-slug>

# 2. ID 指定で本文 + 全コメントを取得
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 uv run kaggle competitions topics show <topic-id>
```

**Note**: `topics show` は本文に em-dash 等の非ASCII文字を含むと Windows で `cp932 codec can't encode` で落ちる。上記のとおり **`PYTHONUTF8=1 PYTHONIOENCODING=utf-8` を必ず前置**する。出力が大きい場合はファイルへリダイレクトして読む。

## Common Workflow

```bash
# 1. コンペを探す
uv run kaggle competitions list -s "<keyword>"

# 2. ファイル構成を確認
uv run kaggle competitions files <competition-slug>

# 3. データ取得（Rules 同意済みであること）
uv run kaggle competitions download -c <competition-slug> -p data/raw
#    → data/raw/<competition-slug>.zip を展開して data/raw/ に配置
```

## Troubleshooting

- **`kaggle: command not found`**: `uv run kaggle` を使う。未インストールなら `uv add kaggle`
- **401 Unauthorized**: `~/.kaggle/kaggle.json` が無い／鍵が失効。Account ページで再発行
- **403 Forbidden（コンペ）**: ブラウザで該当コンペの Rules に未同意。Join してから再実行
- **`Could not find kaggle.json`**: 配置パスが違う。`$env:KAGGLE_CONFIG_DIR` で明示するか `~/.kaggle/` に置く
- **ダウンロードが .zip のまま**: datasets は `--unzip`、competitions は手動展開が必要
- **`cp932 codec can't encode`（topics show 等）**: 出力に非ASCII文字。`PYTHONUTF8=1 PYTHONIOENCODING=utf-8` を前置する
