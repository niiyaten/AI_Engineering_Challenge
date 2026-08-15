# RAGローカル実行手順（WSL2 / Ubuntu）

このディレクトリをGitから取得した場合は、以下の手順で直接実行するのが推奨です。Windows側のパスをWSL2からそのまま利用できます。

```bash
cd /mnt/e/PC/デスクトップ/SIGNATE/AI_Engineering_Challenge
uv sync --extra test
uv run python scripts/run_integrated100.py \
  --share-zip materials/share.zip \
  --workspace work/coldstart \
  --questions questions/integrated100_questions.csv \
  --output-dir outputs/coldstart \
  --question-timeout 240 \
  --refresh
```

提出用の回答は `outputs/coldstart/predictions.csv` に生成されます。初回のみ、後述するTesseract、LibreOffice、PopplerなどのOS依存ツールを導入してください。

---

## 旧ZIP配布物から実行する場合

以下は、`rag_integrated100_post_reaudit_coldstart_v1.zip` のような旧配布物を使う場合の手順です。Git管理下のこの完成構成では不要です。

## 1. 使用するファイル

ダウンロードする実行用ファイル：

```text
rag_integrated100_post_reaudit_coldstart_v1.zip
```

Qiita記事用の `qiita_rag_article_project_v2.zip` は説明資料であり、RAG本体の実行用ではありません。

---

## 2. 推奨環境

- Windows 10 / 11
- WSL2
- Ubuntu
- Python 3.12
- uv
- Tesseract OCR
- LibreOffice
- Poppler

Windowsネイティブ環境でも動作させることは可能ですが、本プロジェクトではLinux系の外部コマンドを利用しているため、WSL2 + Ubuntuを推奨します。

---

## 3. WSL2 / Ubuntuの準備

WSL2が未導入の場合は、管理者権限のPowerShellで以下を実行します。

```powershell
wsl --install -d Ubuntu
```

インストール後、必要に応じてWindowsを再起動し、Ubuntuを起動します。

既にWSL2 / Ubuntuを利用している場合、この工程は不要です。

---

## 4. ZIPをWindows側へ保存

例：

```text
C:\Users\<Windowsユーザー名>\Downloads\rag_integrated100_post_reaudit_coldstart_v1.zip
```

---

## 5. ZIPをWSL内部へコピー

Ubuntuを開き、作業ディレクトリを作成します。

```bash
mkdir -p ~/rag-test
cd ~/rag-test
```

WindowsのDownloadsフォルダからZIPをコピーします。

```bash
cp /mnt/c/Users/<Windowsユーザー名>/Downloads/rag_integrated100_post_reaudit_coldstart_v1.zip .
```

> `/mnt/c/...` 上で直接実行するより、`~/rag-test` のようなWSL内部へコピーして実行することを推奨します。日本語ファイル名や長いパスを含むためです。

ZIPを展開します。

```bash
unzip rag_integrated100_post_reaudit_coldstart_v1.zip
```

展開後、プロジェクトディレクトリへ移動します。

```bash
cd rag_integrated100_post_reaudit_coldstart_v1
```

---

## 6. 外部ツールをインストール

パッケージ情報を更新します。

```bash
sudo apt update
```

必要なツールをインストールします。

```bash
sudo apt install -y \
  unzip \
  libreoffice \
  poppler-utils \
  tesseract-ocr \
  tesseract-ocr-jpn \
  tesseract-ocr-eng
```

### インストール確認

```bash
tesseract --version
```

```bash
tesseract --list-langs
```

最低でも以下が表示されることを確認します。

```text
eng
jpn
```

LibreOffice：

```bash
libreoffice --version
```

Poppler：

```bash
pdftoppm -v
```

---

## 7. uvをインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

その後、Ubuntuを開き直すか、以下を実行します。

```bash
source ~/.local/bin/env
```

確認：

```bash
uv --version
```

---

## 8. Python 3.12環境を準備

```bash
uv python install 3.12
```

依存関係を同期します。

```bash
uv sync --python 3.12 --extra test
```

---

## 9. まずテストを実行

100問を実行する前に、テストを実行します。

```bash
uv run pytest
```

期待結果：

```text
24 passed
```

ここまで成功すれば、実行環境はほぼ正しく構築できています。

---

## 10. 100問コールドスタートを実行

以下を実行します。

```bash
uv run python scripts/run_integrated100.py \
  --share-zip materials/share.zip \
  --workspace work/local_post_reaudit \
  --questions questions/integrated100_questions.csv \
  --output-dir outputs/local_post_reaudit \
  --question-timeout 240 \
  --refresh
```

実行中は以下のような進捗が表示されます。

```text
[001/100] ...
[002/100] ...
[003/100] ...
```

---

## 11. 実行結果を確認

結果は以下へ出力されます。

```text
outputs/local_post_reaudit/
```

主なファイル：

```text
predictions.csv
audit100_answers.csv
audit100_raw_results.jsonl
audit100_evidence.jsonl
run_summary.json
workers/
```

### `run_summary.json` の確認

目安として以下の状態になれば、100問のコールドスタート再現に成功しています。

```json
{
  "answered_count": 100,
  "abstained_count": 0,
  "evidence_answered_count": 100,
  "timeout_count": 0,
  "exception_count": 0
}
```

---

## 12. 各出力ファイルの用途

### `predictions.csv`

最終回答のみを並べた提出用データです。

### `audit100_answers.csv`

質問ごとの回答や処理結果を確認するための監査用データです。

### `audit100_raw_results.jsonl`

各Executorの詳細な実行結果を保存します。

### `audit100_evidence.jsonl`

各回答の根拠となった資料・Evidenceを確認できます。

### `run_summary.json`

回答数、Evidence数、タイムアウト、例外など、実行全体のサマリです。

### `workers/`

質問単位の処理ログや中間結果が保存されます。

---

## 13. 最初はテストだけでもよい

最初から100問を実行せず、まず以下まで実施するのがおすすめです。

```bash
uv run pytest
```

`24 passed` が確認できた後に100問実行へ進みます。

---

## 14. トラブル時に確認するもの

エラーが発生した場合は、以下を確認します。

### Python / uv

```bash
uv --version
uv run python --version
```

Python 3.12系になっていることを確認します。

### OCR

```bash
tesseract --list-langs
```

`jpn` と `eng` が存在することを確認します。

### LibreOffice

```bash
which libreoffice
libreoffice --version
```

### Poppler

```bash
which pdftoppm
pdftoppm -v
```

### 実行ディレクトリ

```bash
pwd
ls
```

以下のようなファイル・ディレクトリが見えていることを確認します。

```text
materials/
questions/
scripts/
src/
pyproject.toml
```

---

## 15. 推奨する進め方

1. WSL2 / Ubuntuを準備
2. ZIPをWSL内部へコピー
3. Tesseract / LibreOffice / Popplerをインストール
4. uv + Python 3.12を準備
5. `uv run pytest`
6. `24 passed` を確認
7. 100問コールドスタート実行
8. `run_summary.json` を確認
9. `audit100_evidence.jsonl` で回答根拠を確認

問題が発生した場合は、ターミナルに表示されたエラーメッセージを省略せず確認すると原因を切り分けやすくなります。
