# AI Engineering Challenge — 最終RAGパイプライン

このリポジトリは、共有ドライブの原本だけから100問に回答する、WSL2向けの最終RAGパイプラインです。外部API、事前生成カタログ、期待回答を使わずにコールドスタート実行できます。

## 最短実行

WSL2 の Ubuntu で、以下を実行します。

```bash
cd /mnt/e/PC/デスクトップ/SIGNATE/AI_Engineering_Challenge
uv sync
uv run python scripts/run_integrated100.py \
  --share-zip materials/share.zip \
  --workspace work/coldstart \
  --questions questions/integrated100_questions.csv \
  --output-dir outputs/coldstart \
  --question-timeout 240 \
  --refresh
```

完了後の提出用CSVは `outputs/coldstart/predictions.csv` です。WSL2の導入・依存ツールの確認は [RAG_local_execution_WSL2.md](RAG_local_execution_WSL2.md) を参照してください。

## 構成

- `src/`: 回答ルーティング、文書抽出、表計算、OCR、画像埋込表の復元ロジック
- `scripts/`: 100問コールドスタート実行スクリプト
- `materials/`: 実行入力の共有ドライブZIP
- `questions/`: 統合100問と監査用質問
- `tests/`: 回帰テスト
- `validation/`: 期待回答との差分確認と対象修正の検証結果
- `outputs/final_coldstart100/`: 2026-08-15に実施した最終100問コールドスタートの出力・証跡
- `EDA/`: 最終パイプラインに至るまでの探索・評価履歴。実行本体とは分離

## 最終検証結果

- 100問中100問に回答、棄権・タイムアウト・例外は0
- ID34: Action表の複数行セルを座標ベースで復元
- ID80: 埋込画像の黄色Pivot階層を復元して再集計
- ID93: 次のAction IDまでの複数行セルを結合
- `pytest -q`: 24件成功

再実行結果の詳細は `outputs/final_coldstart100/run_summary.json`、根拠は `audit100_evidence.jsonl`、回答は `predictions.csv` にあります。
