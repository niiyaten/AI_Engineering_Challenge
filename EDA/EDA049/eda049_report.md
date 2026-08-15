# EDA049: 座席表の図形座標構造化

## 背景と目的

EDA048で残った座席表系2問は、`FM`、つまりフロアマップ内の左右・向かい関係を読む必要がある。
EDA049では、まずPPTX structure JSONのshape座標だけで座席表を復元できるかを確認し、無理な場合は画像Visionで座席表を座標テーブル化する。

## 結果

- PPTX shape数: 3
- PPTX text shape数: 0
- 画像shape数: 1
- shape textから復元可能: False
- 座席テーブルsource: `fallback_visual_seed`
- 座席レコード数: 15
- OpenRouter status: ``
- OpenRouter finish_reason: ``

## 判断

PPTX structure JSON上、座席表はスライド全面の画像として埋め込まれており、人名・EXT・役割はtext shapeとして存在しない。
したがって、PPTX図形座標だけでは座席表を復元できない。
提出用に再現するなら、画像OCR/Visionで人名・EXTを取得し、画像座標またはPOD内相対座標へ変換する処理が必要。

## 出力

- shape監査: `EDA/EDA049/tables/seat_pptx_shape_audit.csv`
- 座席座標テーブル: `EDA/EDA049/tables/seat_coordinate_table.csv`
- 残件質問への候補回答: `EDA/EDA049/tables/seat_question_probe.csv`

凡例: `x_order` は同一POD内の左右位置、`y_order` は上下位置、`source` は座席テーブル生成方法を表す。
