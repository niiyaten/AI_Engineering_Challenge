# 外部作業ツリー台帳

| 作業ツリー | ブランチ | 基点コミット | 整理内容 |
|---|---|---|---|
| `SIGNATE_Agentic_RAG_excel_row_audit` | `feature/excel-row-filter-reachability` | `16b45b6` | 追跡済み4ファイルの差分、PowerPointタイムラインExecutorとテストを保存 |
| `SIGNATE_Agentic_RAG_overnight_baseline_eda` | `audit/overnight-baseline-and-eda` | `34409d3` | ベースライン再実行の生成物のみ。元データ削除状態を記録 |
| `SIGNATE_Agentic_RAG_pptx_timeline_integration` | `feature/pptx-timeline-integration` | `34409d3` | コミット済みの統合試行。未コミットの実装差分なし |
| `SIGNATE_Agentic_RAG_pptx_timeline_integration_v2` | `feature/pptx-timeline-integration-v2` | `34409d3` | 追跡済み4ファイルの差分、PowerPointタイムラインExecutorとテストを保存 |
| `SIGNATE_Agentic_RAG_pptx_timeline_range_fix` | `feature/pptx-timeline-range-fix` | `8c9b00d` | タイムライン範囲修正の生成物のみ。元データ削除状態を記録 |
| `SIGNATE_Agentic_RAG_raw_discovery_fix` | `fix/clean-raw-discovery` | `34409d3` | raw探索修正の生成物のみ |
| `SIGNATE_Agentic_RAG_test49_openrouter_poc` | `feature/test49-openrouter-poc` | `7f73b11` | OpenRouter候補選択試行の生成物のみ。外部API依存のため最終パイプラインへは不採用 |

凡例: 「差分」はGit追跡済みファイルの未コミット変更、「未追跡ソース」は新規Python実装・テストを指す。「生成物のみ」は `data/output/` などの大容量実行結果を指し、元の作業ツリーを削除する前に必要な結果だけを別途確認する。
