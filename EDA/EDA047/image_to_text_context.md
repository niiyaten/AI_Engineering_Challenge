# Image To Text Context

## image_id=2 source=data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell018_output001.png
2011年1月から2012年1月までの日次データの推移を表す折れ線グラフ。 dteadayによる時系列推移 日付 平均値 {'series_name': '平均値', 'x_axis': '日付 (2011-01 から 2012-01)', 'y_axis': '平均値 (0 から 250)', 'legend': '平均値', 'readable_values': ['2011-01: 約30', '2011-03: 約100', '2011-05: 約200', '2011-07: 約220', '2011-09: 約250', '2011-11: 約150', '2012-01: 約120']} 2011年1月以降、平均値が上昇傾向にある。 2011年9月頃に平均値がピーク(約250)に達した。 2012年1月には平均値が低下傾向にある。

## image_id=4 source=data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell012_output003.png
カテゴリ分布を示す3つの水平バー図。 dtday のカテゴリ分布 season のカテゴリ分布 yr のカテゴリ分布 {'title': 'dtday のカテゴリ分布', 'x_axis': '件数', 'y_axis': 'dtday', 'series': '2011-01-01から2011-02-07までの日付', 'color_gradient': '濃紫から黄緑'} {'title': 'season のカテゴリ分布', 'x_axis': '件数', 'y_axis': 'season', 'series': ['1', '2', '3', '4'], 'color_gradient': '黄緑から濃紫'} {'title': 'yr のカテゴリ分布', 'x_axis': '件数', 'y_axis': 'yr', 'series': ['0'], 'color': '濃紺'} dtdayの分布は日付ごとに色が変化し、2011-01-01は最も濃い色、2011-02-07は最も明るい色である。 seasonの分布では、season=3が最も高い値、season=1が最も低い値を示している。 yrの分布は単一の値(0)で構成され、件数が最大値を示している。

## image_id=5 source=data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell016_output001.png
数値特徴量の相関ヒートマップ id season yr mth hr holiday weekday workingday weathersit temp atemp hum windspeed cnt {'title': '数値特徴量の相関ヒートマップ', 'x_axis': ['id', 'season', 'yr', 'mth', 'hr', 'holiday', 'weekday', 'workingday', 'weathersit', 'temp', 'atemp', 'hum', 'windspeed', 'cnt'], 'y_axis': ['id', 'season', 'yr', 'mth', 'hr', 'holiday', 'weekday', 'workingday', 'weathersit', 'temp', 'atemp', 'hum', 'windspeed', 'cnt'], 'color_bar': '0.0から1.0', 'color_gradient': '赤から青'} idとseasonの相関係数が1.0 tempとatempの相関係数が0.9 humとwindspeedの相関係数が0.8 cntとtempの相関係数が0.7 cntとatempの相関係数が0.6 cntとhumの相関係数が0.5 cntとwindspeedの相関係数が0.4 cntとworkingdayの相関係数が0.3 cntとholidayの相関係数が0.2 cntとmthの相関係数が0.1 cntとyrの相関係数が0.0 cntとseasonの相関係数が-0.1 cntとidの相関係数が-0.2

## image_id=6 source=data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/notebooks/01_eda.ipynb.assets/cell014_output001.png
cntの分布を表すヒストグラムと正規分布曲線のグラフ。 cnt の分布 {'series_name': 'cnt の分布', 'x_axis': 'cnt', 'y_axis': '度数', 'legend': '正規分布曲線'} cntの値が0に近いほど度数が多く、cntが増えるにつれて度数は減少する傾向がある。 正規分布曲線はヒストグラムの形状を概ね追っている。 最大の度数は約1600で、cnt=0の箱に対応する。

## image_id=8 source=data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx.assets/slide006_shape003.png
信用リスク評価に関する5つの主要プロセスのフローチャート 4.1 データ理解 品質確認 4.2 前処理 方針策定 4.3 モデル 比較 4.4 リスクセグメンテーション 4.5 ガバナンス 監査対応 型・件数・欠損確認 欠損補完ルール策定 ベースライン構築 高リスク抽出 監査証跡の確保 分布・極端値把握 外れ値処理比較 複数モデル比較 重要変数の把握 アクセス制御文書化 相関構造分析 線形/木系で方針分離 不均衡対応手法比較 財務悪化パターン整理 採否・閾値根拠記録 高欠損列の採否評価 再現性条件固定化 しきい値別評価 スコア出力方針 前提・制約の明示 5列5行の表で、各プロセスの詳細手法を列挙 信用リスク評価プロセスの5段階フロー データ品質確認から始まるプロセスフロー モデル比較が評価の核心 リスクセグメンテーションの重要性 ガバナンス体制の監査対応 評価手法の多様性 再現性の確保要件
