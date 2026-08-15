# EDA053: `わかりません` 候補統合

## 背景と目的

EDA046時点でtest 100件中16件が `わかりません` のまま残っている。
EDA049の座席表候補とEDA052のPDF Vision OCR候補を使い、未回答をどこまで減らせるか確認する。

## 方針

- safe版: `needs_review=False` の候補だけを採用する。
- aggressive版: 座席表の検証用候補も採用する。
- EDA051の横断集計候補はまだ回答として不完全なため、今回は採用しない。

## 結果

- EDA046時点の `わかりません`: 16
- safe版の `わかりません`: 14
- aggressive版の `わかりません`: 12
- safe版の追加採用: 2
- aggressive版の追加採用: 4

## 出力

- 候補プール: `EDA/EDA053/tables/eda053_candidate_pool.csv`
- safe採用ログ: `EDA/EDA053/tables/eda053_safe_adoption_log.csv`
- aggressive採用ログ: `EDA/EDA053/tables/eda053_aggressive_adoption_log.csv`
- safe提出zip: `EDA/EDA053/predictions/eda053_safe_unknown_reduction_submission.zip`
- aggressive提出zip: `EDA/EDA053/predictions/eda053_aggressive_unknown_reduction_submission.zip`

## 注意

座席表候補は検証用seed由来であり、提出採用前に画像と照合する必要がある。
PDF Vision OCR候補もraw responseとページ画像を確認してから提出判断する。
