# valid_021 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。根拠が不足している場合は「わかりません」と答えてください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 青葉バイオメディカル機器のtrain.xlsxのPivotシートにおいて、平均月収が最も高い層の抽出条件を答えてください。

推定route: table_calculation

route別の注意: 表・CSV・Excelの値を読み取り、必要なら計算して短く答える。

根拠:

[根拠 1]
score: 106.192524
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.xlsx
record_type: xlsx_sheet
text:
Excelファイル: train.xlsx シート: Pivot 使用範囲: A1:B88 列: col_1, col_2 グラフ数: 0 サンプル: | col_1 | col_2 | | --- | --- | | nan | | | nan | | | 行ラベル | 平均 / MonthlyIncome | | No | 6989.955882352941 | | Female | 7216.258064516129 | | Divorced | 7404.811320754717 | | Life Sciences | 6090.4 | | Marketing | 5994 |

[根拠 2]
score: 95.620271
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx
record_type: metadata
text:
ファイル名: 株式会社青葉バイオメディカル機器_最終報告.pptx 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx ファイル種別: pptx

[根拠 3]
score: 89.914374
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.xlsx
record_type: metadata
text:
ファイル名: train.xlsx 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.xlsx ファイル種別: xlsx

[根拠 4]
score: 85.341339
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx
record_type: pptx_slide
text:
Slide 12 報酬水準 MonthlyIncome StockOptionLevel 働き方 OverTime BusinessTravel WorkLifeBalance 所属・職務 Department JobRole JobLevel 勤続・昇進 TotalWorkingYears YearsAtCompany YearsInCurrentRole YearsSinceLastPromotion YearsWithCurrManager 満足度・関係性 JobSatisfaction EnvironmentSatisfaction RelationshipSatisfaction 属性変数（分析対象だが施策利用に注意） Age | Gender | MaritalStatus 業務解釈 • 離職は単一要因ではなく、処遇・働き方・キャリア・所属環境の複合要因として捉えるべきである • 若手層・勤続初期層・役割定着前層・昇進停滞感のある層・残業負荷が高い層でリスクが高まりやすい可能性がある • ただし、上記は施策仮説であり、追加集計と業務確認で補強すべき内容である 4. 離職に関連する主要観点

[根拠 5]
score: 84.634439
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx
record_type: pptx_slide
text:
Slide 1 最終分析報告書 従業員離職要因分析および離職リスク検知 初期分析 株式会社青葉バイオメディカル機器 人事本部 人材戦略部 プロジェクト期間：2025年6月23日 ～ 2025年7月28日（5週間） 契約形態：Time and Materials 目的変数：Attrition（従業員離職） 735行 × 33列 対象データ 2025年7月28日 最終成果物提出

[根拠 6]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/preprocess.py
record_type: metadata
text:
ファイル名: preprocess.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/preprocess.py ファイル種別: py

[根拠 7]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/modeling.py
record_type: metadata
text:
ファイル名: modeling.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/modeling.py ファイル種別: py

[根拠 8]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/infer.py
record_type: metadata
text:
ファイル名: infer.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/infer.py ファイル種別: py

[根拠 9]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/features.py
record_type: metadata
text:
ファイル名: features.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/features.py ファイル種別: py

[根拠 10]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/evaluate.py
record_type: metadata
text:
ファイル名: evaluate.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/evaluate.py ファイル種別: py

[根拠 11]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/eda.py
record_type: metadata
text:
ファイル名: eda.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/eda.py ファイル種別: py

[根拠 12]
score: 84.303838
source_path: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/common.py
record_type: metadata
text:
ファイル名: common.py 元パス: share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/04.分析/analysis_project/src/common.py ファイル種別: py
