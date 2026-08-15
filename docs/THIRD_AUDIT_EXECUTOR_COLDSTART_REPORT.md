# 第三次監査 Executor統合・100問コールドスタート報告

## 結果

- 独立実行対象: ID6 / ID35 / ID36 / ID40
- 100問コールドスタート: 100/100回答
- Evidenceあり: 100/100
- 棄権: 0
- タイムアウト: 0
- 例外: 0
- 実行時間: 656.831秒
- 外部API: 不使用
- prior answers / expected answers / fact catalog: 不使用
- pytest: 23/23成功
- オーバーレイ単体テスト: 5/5成功

## 独立実行結果

| ID | 回答 | Route | Method | Evidence |
|---:|---|---|---|---:|
| 6 | 実績工数の最終確定値および確定した最終請求金額が資料に含まれていないため、差額は算出できません。 | tm_invoice_difference | tm_final_invoice_not_determinable | 6 |
| 35 | 0.90527 | scoring_precision | pptx_displayed_ranked_metric | 1 |
| 36 | 0.09619113 | remaining50_generalization | interim_report_vs_metrics_f1_difference | 2 |
| 40 | 1位：2025年10月 11,412,500円、2位：2025年9月 9,858,750円、3位：2025年8月 8,118,000円 | remaining50_generalization | cross_project_monthly_settlement_ranking | 13 |

## 第二次監査コールドスタートとの差分

回答変更は2問だけです。

- ID6: `0円` → `算出できない`
- ID35: `0.905271` → `0.90527`

ID36とID40の回答値は不変です。ID40は固定金額案件のEvidenceが追加され、Evidence件数が12件から13件へ増加しました。

## 実装時に検出・修正した問題

当初のオーバーレイv2は、専用Executorのコンストラクタをworkerへ挿入していましたが、`execute()`を呼び出していませんでした。そのため、ID6とID35が旧ルートへ流れる状態でした。

workerを修正し、次の順序で実際にExecutorを呼び出すようにしました。

1. ScoringPrecisionExecutor
2. TMInvoiceDifferenceExecutor
3. Remaining50GeneralizationExecutor
4. AuditGeneralizationExecutor
5. Base Recovery

また、PDF抽出で「タイムシート」が `タイム シート` または改行分割されるケースに対応しました。

## 回帰確認

- 回答差分: ID6、ID35のみ
- Route差分: ID6、ID35のみ
- Method差分: ID6、ID35のみ
- Evidence件数差分: ID6、ID40のみ
- 専用Executorの他問への誤発火: 0件
