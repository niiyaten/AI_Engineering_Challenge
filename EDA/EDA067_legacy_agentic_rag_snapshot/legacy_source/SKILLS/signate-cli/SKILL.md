---
name: signate-cli
description: SIGNATE competition CLI for listing competitions, downloading data, and submitting predictions. Use when the user needs to interact with SIGNATE competitions - submit results, download datasets, or check competition/task information.
allowed-tools: Bash(signate:*), Bash(uv run signate:*)
---

# SIGNATE CLI

SIGNATE CLI (`signate`) enables competition data download and prediction submission from the command line.

## This Competition

- **Competition key**: `37308d147238487c96551300b8e4cb76`
- **Task key**: `8940dcfa70434a6aaaa28d661652d536`
- **Task**: 木材含水率予測（近赤外スペクトル分析チャレンジ）

### File keys

| file_key | file_name | description |
|---|---|---|
| `d1edef347a9c48839a97ba92084ce045` | train.csv | 学習用データ |
| `68b2ee0219334457873c7d2ee1028c7a` | test.csv | 評価用データ |
| `c4246245c6834758980910e4bdd99052` | sample_submit.csv | サンプル提出ファイル |

## Setup

```bash
# Install (already in this project's dependencies)
uv add signate

# Generate API token (initial setup only, interactive)
uv run signate token -e your-email@example.com
# Token is saved to ~/.signate/signate.json
```

## Commands

### List competitions

```bash
uv run signate competition-list
```

### List tasks for a competition

```bash
uv run signate task-list --competition_key=37308d147238487c96551300b8e4cb76
```

### List downloadable files

```bash
uv run signate file-list --task_key=8940dcfa70434a6aaaa28d661652d536
```

**Note**: Must consent to competition participation via browser first.

### Download data files

```bash
# Download train.csv to current directory
uv run signate download \
  --task_key=8940dcfa70434a6aaaa28d661652d536 \
  --file_key=d1edef347a9c48839a97ba92084ce045

# Download to a specific directory
uv run signate download \
  --task_key=8940dcfa70434a6aaaa28d661652d536 \
  --file_key=d1edef347a9c48839a97ba92084ce045 \
  --path=data/raw
```

### Submit predictions

```bash
# Submit with memo
uv run signate submit \
  --task_key=8940dcfa70434a6aaaa28d661652d536 \
  experiments/NNN_YYYYMMDD_name/predictions/test.csv \
  --memo "experiment description"

# Example: submit experiment 011's predictions
uv run signate submit \
  --task_key=8940dcfa70434a6aaaa28d661652d536 \
  experiments/011_20260403_cnn1d_large_kernel/predictions/test.csv \
  --memo "CNN large kernel, OOF RMSE=16.20"
```

## Submission File Format

- Header: none
- Columns: `sample_number,predicted_moisture_content`
- Must match `data/processed/sample_submit.csv` format

```csv
95,50.123
96,48.456
97,52.789
```

## Common Workflow

```bash
# 1. Check available competitions
uv run signate competition-list

# 2. Check tasks
uv run signate task-list --competition_key=37308d147238487c96551300b8e4cb76

# 3. Download data (if needed)
uv run signate download --task_key=8940dcfa70434a6aaaa28d661652d536 --file_key=d1edef347a9c48839a97ba92084ce045 --path=data/raw

# 4. Run experiment and generate predictions
uv run python experiments/NNN_YYYYMMDD_name/main.py

# 5. Submit predictions
uv run signate submit --task_key=8940dcfa70434a6aaaa28d661652d536 experiments/NNN_YYYYMMDD_name/predictions/test.csv --memo "description"
```

## Troubleshooting

- **`signate: command not found`**: Use `uv run signate` instead of bare `signate`
- **Authentication error**: Re-run `uv run signate token -e <email>` to regenerate token
- **Participation required**: Visit the competition page in browser and click "参加" before downloading or submitting
- **Encoding issues in output**: CLI output may show garbled Japanese text on Windows - this is a display issue only and does not affect functionality
