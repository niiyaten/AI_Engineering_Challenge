# 100問完全コールドスタート結果

## 結果

- 質問数: 100
- 回答数: 100
- Evidence付き回答: 100
- 棄権: 0
- タイムアウト: 0
- 例外: 0
- pytest: 20/20
- 総実行時間: 1404.804秒

## Runtime入力

- `materials/share.zip`
- `questions/integrated100_questions.csv`
- Executorコード

監査回答、過去の提出回答、Fact Catalog、外部APIはRuntimeで使用していません。

## 第二次監査反映

- ID 3: 太字項目の区切り整形
- ID 36: F1差の通常四捨五入
- ID 97: 黄色行・黄色列バンドの交点差
- ID 99: 資料上の表示順位に基づく死亡率比

`outputs/coldstart100/predictions.csv` は、第二次監査反映後の期待値と100/100行・バイト単位で一致しました。
