# EDA059 質問・回答・ソース確度一覧

## 目的

EDA058の提出回答を変更せず、質問文、回答、参照したソースファイル、source_confidenceを質問単位で照合できるように整理した。

## 生成元と列の説明

生成元は `EDA/EDA058/tables/answer_source_audit.csv` である。回答の修正や再評価は行っていない。

凡例: `index` は質問ID、`question` は質問文、`answer` はEDA058の回答、`source_files` は参照ファイル、`source_confidence` はソース確度、`answer_status` は回答状態、`source_count` は参照ファイル数を表す。

## 件数サマリ

| answer_status   | source_confidence   |   count |
|:----------------|:--------------------|--------:|
| answered        | high                |       2 |
| answered        | low                 |      32 |
| answered        | medium              |      64 |
| unknown         | none                |       2 |

凡例: `answer_status` と `source_confidence` の組み合わせごとに、該当する質問数を示す。

## 質問・回答・ソースファイル一覧

### index 0

- 質問: 白峰信用リスク評価の提案書old.pptxから提案書.pptxへの更新内容のうち、案件遂行に関連する実質的な変更を挙げてください。
- 回答: 変更なし
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx`

### index 1

- 質問: 恒一会 かえで総合病院の最終報告書old版と最新版を比較したとき、案件遂行に関連する実質的な変更を挙げてください。
- 回答: AUC-ROC = 0.905 / Accuracy = 0.833、AUC-ROC、Accuracy、F1-macro、線形系と非線形モデルを比較
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx.md`

### index 2

- 質問: 青嶺不動産アセットマネジメントのスケジュール_r2.xlsxにおいて、オレンジにハイライトされている行のタスク名をすべて答えてください。
- 回答: プロジェクトキックオフ実施、中間報告会実施、最終報告会実施
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r2.xlsx.structure.json`

### index 3

- 質問: 恒一会 かえで総合病院の契約書において、太字で記載されている箇所のうち、日付以外のものをすべて抽出してください。
- 回答: time_and_materials、実績工数に基づき、案件完了後に最終成果物の検収を経て一括精算する。、30、分単位、25,000、円/時間
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/01.契約/契約書_pw解除版.docx.structure.json`

### index 4

- 質問: 蒼泉会 ひがし丘総合病院の01_eda.ipynbを確認して、目的変数と相関が最も高い数値特徴量を教えてください。
- 回答: bmi
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

### index 5

- 質問: 青潮モビリティサービスの最終報告にて最良モデルとしているモデルのパラメータであるmax_depthはいくらに設定されていますか。
- 回答: max_depthは5に設定されています
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/会議録/会議録_2025-08-26.docx`

### index 6

- 質問: 蒼泉会 ひがし丘総合病院案件において、提案時の税込み見込み金額と最終請求金額の差額はいくらですか。
- 回答: 0円
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

### index 7

- 質問: 青潮モビリティサービスの基礎分析.pptxにおいて、黄色ハイライトされている数値に対応するデータの抽出条件と集計内容を答えてください。
- 回答: 行ラベル(0,1,2...)でグループ化し、各列(平均 / temp, 平均 / atemp, 平均 / hum, 平均 / windspeed, 平均 / cnt)の平均値を算出する。
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`

### index 8

- 質問: 東都人材プラットフォームのデータサイエンティスト調査資料において、米国平均給与における機械学習（ML）エンジニアとデータエンジニアの差はいくらですか。
- 回答: 14,744ドル。
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

### index 9

- 質問: 青葉与信マネジメントの最終報告資料の最新版になる際に修正されたもののうち、案件遂行に関連する変更を挙げてください。
- 回答: 5. 業務提言 ― モデル運用・ガバナンス(中期)
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx.md`

### index 10

- 質問: 恒一会 かえで総合病院のtrain.xlsxにおいて、AG_ratioのヒストグラムで最も多いカウント数はいくつですか。
- 回答: 1473
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/03.データ/train.csv.data.csv`

### index 11

- 質問: 青嶺不動産アセットマネジメントの報告資料の中で、太字、下線、イタリックのすべてに該当する箇所を抽出してください。
- 回答: 該当箇所はありません
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-26.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-06.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/old/提案書.pptx`

### index 12

- 質問: 蒼泉会 ひがし丘総合病院の報告資料_2025-07-08.docxにおいて、WBS観点の進捗状況の見出しがあるのは何ページですか。
- 回答: 3
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/05.会議/報告資料/報告資料_2025-07-08.docx.md`

### index 13

- 質問: データアステル社の中でもっとも多くの案件にかかわっている人の内線番号を教えてください。
- 回答: 鈴木 美咲
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`
  - `share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`

### index 14

- 質問: 青葉与信マネジメントの提案書_v1.pptxから提案書_v3.pptxに修正されたもののうち、案件遂行に関連する変更を挙げてください。
- 回答: • ベースラインモデルを構築し基準性能を把握、• ROC-AUC, PR-AUC, 混同行列, リフト等を算出、• データ定義・前処理・評価条件・判断根拠を文書化
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/00.提案/提案書_v1.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/00.提案/提案書_v3.pptx.md`

### index 15

- 質問: 東都人材プラットフォームのtrain.xlsxにおいて、Sheet1の黄色にハイライトされたセルの抽出条件と集計内容を答えてください。
- 回答: Country: Spain, 個数: 12.0
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.xlsx.structure.json`

### index 16

- 質問: 青葉与信マネジメントの中間報告資料にて、黄色ハイライトかつ赤字となっている部分を抜き出してください。
- 回答: 0.589
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx.structure.json`

### index 17

- 質問: AYMのMMにおいて、黄色ハイライトかつREDになっている数値を対象に、最初のMMから最後のMMまでの上昇率を計算してください。上昇率は （最後の値 - 最初の値） / 最初の値 × 100 で求め、小数第2位まで答えてください。
- 回答: 208.40%
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

### index 18

- 質問: 白峰信用リスク評価の会議ID：M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。
- 回答: 2
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `EDA/EDA052/rendered_pages/白峰信用リスク評価株式会社_会議録_2025_07_15_pdf_page002.png`

### index 19

- 質問: 青嶺不動産アセットマネジメントのスケジュール_r2.xlsxにおいて、2025-08-11から2025-09-09の間に開始日または終了日が設定されているタスクIDをすべて挙げてください。
- 回答: T04 T05 T06 T07 T08
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r2.xlsx`

### index 20

- 質問: 東都人材プラットフォームの報告資料_2025-08-18.pdf で、渡辺遥と藤田彩の2人が担当となっている優先タスクを抽出してください。
- 回答: 渡辺遥: T07, T09, T10 藤田彩: T12
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/05.会議/報告資料/報告資料_2025-08-18.pdf`

### index 21

- 質問: 青葉バイオメディカル機器のクライアントの主担当者の役職は何ですか。
- 回答: エグゼクティブスポンサーです
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/01.契約/契約書_draft.docx`

### index 22

- 質問: 白峰信用リスク評価の01_eda_old.ipynbから01_eda.ipynbへの変更内容のうち、内容として変わっている点は何ですか。
- 回答: 変更なし。
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書old.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx.md`

### index 23

- 質問: ひがし丘の案件において、案件終了後のACTHが155時間10分だった場合の税込請求額は提案書内で記載の見込税込金額と比べて何円の減額になりますか。
- 回答: 398750円
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx`

### index 24

- 質問: 分析データの中で、1つでも欠損値がある行数が最も多い案件を、主略称で答えてください。
- 回答: AOMINE
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/03.データ/train.csv`

### index 25

- 質問: 白峰信用リスク評価のtrain.xlsxにおいて、青色ハイライト部分の合計値を求めてください。四捨五入して整数で答えてください。
- 回答: -11759122
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/03.データ/train.xlsx.structure.json`

### index 26

- 質問: 2025-08-15 から 2025-09-07 の間に契約期間が重なっている案件の中で、契約期間が 40日 を超えている案件を、主略称ですべて挙げてください。
- 回答: 株式会社青嶺不動産アセットマネジメント
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/05.会議/会議録/会議録_2025-07-11.docx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/00.提案/提案書.pptx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/01.契約/契約書_pw解除版.docx.structure.json`

### index 27

- 質問: 恒一会 かえで総合病院の提案書において、スコープ対象外としている項目はいくつありますか。
- 回答: 7
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`

### index 28

- 質問: 蒼樹会 みなみ野女性医療センターの分析結果として予測に影響が高いと報告されている特徴量の中で、最もターゲットとの相関が高い特徴量を答えてください。
- 回答: Age
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/04.分析/analysis_project/notebooks/01_eda.ipynb`

### index 29

- 質問: 恒一会 かえで総合病院のtrain.xlsx内のTPのヒストグラムで、3番目にカウント数が多いビンの範囲を小数第6位までで答えてください。
- 回答: 5.667456以上6.143320未満
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`

### index 30

- 質問: 青葉与信マネジメントの分析対象データにおいて、標準化されたloan_amntが0未満の行のうち、purpose=credit_cardに該当し、かつloan_amntがpurpose=credit_card全体の平均を上回る行の割合は何%ですか。小数第2位まで答えてください。
- 回答: 1.18%
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/03.データ/train.csv`

### index 31

- 質問: 固定金額契約の中で、分析データ1行あたりの契約金額（税込）が最も高い案件を、主略称と1行あたりの金額で答えてください。1行あたりの金額は円単位で切り上げてください。
- 回答: 白峰信用リスク評価 7,480,000
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/00.提案/提案書.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/00.提案/提案書_v1.pptx.structure.json`

### index 32

- 質問: 青嶺不動産アセットマネジメントの分析出力 metrics.json の feature_selection.selected_columns に含まれている列のうち、分析コードで生成された数値交互作用特徴量の列名をすべて答えてください。
- 回答: BOROUGH__x__BLOCK、BOROUGH__x__LOT、BOROUGH__x__ZIP CODE、BLOCK__x__LOT、BLOCK__x__ZIP CODE、LOT__x__ZIP CODE
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_outputs/metrics.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/README.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/data/train.csv.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/data/カラム説明.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/notebooks/01_eda.ipynb.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/scripts/bootstrap_env.py.md`

### index 33

- 質問: 青潮モビリティサービスの基礎分析.docxのグラフ2で、x=3のときの青色の折れ線のyの値を小数第5位で答えてください。
- 回答: 137.64768
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx`

### index 34

- 質問: MINAMINOにおいて、M01時点では未完了で、M02までの間に完了したAIのうち、伊藤さんが担当しているものを抽出してください。
- 回答: なし
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/会議録/会議録_2025-05-27.pdf`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/05.会議/報告資料/報告資料_2025-10-01.docx`

### index 35

- 質問: 京橋信用ソリューションズの京橋信用ソリューションズ株式会社_最終報告.pptxにおいて、F1スコアにてgradient_boostingに次ぐ順位のモデルの Accuracy はいくつですか。
- 回答: 0.90527
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

### index 36

- 質問: 恒一会 かえで総合病院案件において、中間報告時点のF1スコア実測値と最終報告時点のF1スコア実測値の差を絶対値で答えてください。
- 回答: 0.0960328831921873
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf`

### index 37

- 質問: AOBMにおいて、見込金額（税込）と確定金額（税込）の差を、ESTHとACTHの差で割った1時間あたりの減少金額を計算してください。
- 回答: 0円/時間
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/01.契約/契約書.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/05.会議/報告資料/報告資料_2025-07-11.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/01.契約/契約書.docx.md`

### index 38

- 質問: 社内管理のAPRに照らして、APR-M3が必要な案件を主略称ですべて挙げ、それらの契約金額（税込）の合計を答えてください。
- 回答: 該当なし。合計0円
- source_confidence: `high`
- answer_status: `answered`
- ソースファイル:
  - `EDA/EDA051/tables/contract_terms_inventory.csv`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.md`

### index 39

- 質問: 青潮モビリティサービスのtrain.xlsxのSheet1にあるグラフ1はどのカラムを可視化したものですか。
- 回答: Sheet1にはグラフが存在しないため、可視化されたカラムはありません
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/03.データ/train.xlsx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/04.分析/analysis_project/data/カラム説明.md`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/03.データ/カラム説明.md`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`

### index 40

- 質問: 2026年7月1日時点で存在する案件について、支払月ごとの精算総額が多い月を上位3つ、総額とあわせて答えてください。
- 回答: 2025-10: 2,887,500円, 2025-11: 2,887,500円, 2025-12: 0円
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

### index 41

- 質問: AOBMのPLANにおいて、加藤さんが担当者に含まれるタスクIDはいくつありますか。
- 回答: 3
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/02.計画/スケジュール.xlsx`

### index 42

- 質問: 蒼泉会 ひがし丘総合病院のtrain.xlsxのSheet1において、黄色ハイライトされている数値に対応するデータの抽出条件と集計内容を答えてください。
- 回答: Sheet1!F22=33.022105717、条件: col_4=1、col_5=35.9、集計: col_6
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/03.データ/train.xlsx.structure.json`

### index 43

- 質問: 東都のCTにおいて、甲側の主担当者をフルネームで教えてください。
- 回答: 石川 直樹
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

### index 44

- 質問: IMにあるFMにおいて、佐藤さんから見て右側に座っている人の名前をすべて挙げてください。
- 回答: わかりません
- source_confidence: `none`
- answer_status: `unknown`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/社内管理/座席表.pptx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/座席表.pptx.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/04.分析/analysis_outputs/experiments/leaderboard.csv.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_outputs/experiments/leaderboard.csv.md`

### index 45

- 質問: 京橋信用ソリューションズの会議録_2025-10-29.pdfと会議録_2025-11-11.pdfにおいて、会議ID M2 から M3 にかけて完了したアクションアイテムのIDをすべて挙げてください。
- 回答: A01 A02 A03 A07
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/05.会議/会議録/会議録_2025-10-29.pdf`

### index 46

- 質問: 着手金が最も高い案件について、その案件のESの内線番号を教えてください。
- 回答: 7201
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `EDA/EDA051/tables/contract_terms_inventory.csv`
  - `EDA/EDA051/tables/role_assignment_inventory.csv`
  - `EDA/EDA049/tables/seat_coordinate_table.csv`

### index 47

- 質問: 青嶺不動産アセットマネジメントのtrain.xlsxにおいて、黄色ハイライトセルは予測と実際の誤差を計算していますが、その予測値の対象となっている不動産の建設年を算出してください。
- 回答: 2025年
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/06.報告書/株式会社青嶺不動産アセットマネジメント_最終報告.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/scripts/run_train.py`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/03.データ/train.xlsx`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/04.分析/analysis_project/src/__init__.py`

### index 48

- 質問: 青嶺不動産アセットマネジメントのニューヨーク不動産市場の最新動向調査.pdfにおいて、提案されているマンション税の新税率のうち、現行税率からの絶対値の増加が最も小さい価格帯はどこですか。
- 回答: 100万ドル超 - 500万ドル以下
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/ニューヨーク不動産市場の最新動向調査.pdf`

### index 49

- 質問: 東都人材プラットフォームの会議録において、コメントがついている部分をそのまま抽出してください。
- 回答: WBS・進捗管理台帳確定（タスク割振・ガント更新）
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/05.会議/会議録/会議録_2025-08-18.docx`

### index 50

- 質問: 東都人材プラットフォームのデータサイエンティスト調査において、Salary.com が公表しているデータサイエンティストの年間基本給について、上位90%の層と中央値の差はいくらですか。
- 回答: 81,820ドル
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

### index 51

- 質問: 白峰信用リスク評価の提案書.pptxにおいて、モデルの高度化（説明性・セグメント分析）の実行予定スケジュールは案件開始から第何週目に実施予定でしょうか。
- 回答: 第9週目
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/00.提案/提案書.pptx`

### index 52

- 質問: 蒼樹会 みなみ野女性医療センターの今後の運用に関する記載の中で、データアステル側の役割として「別契約」と明記されているものを抽出してください。
- 回答: 契約範囲外の追加対応
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/提案書.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/01.契約/契約書.docx.md`

### index 53

- 質問: TOTOのFR書にて記載のある選択特徴量のうち、ENG-FTはいくつありますか。
- 回答: 0
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/notebooks/01_eda.ipynb.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/src/features.py.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/04.分析/analysis_project/src/features.py.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.csv.structure.json`

### index 54

- 質問: 青潮モビリティサービスの基礎分析.docxのグラフ1で、x=3のときのyの値を小数第5位で答えてください。
- 回答: 13.00000
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`

### index 55

- 質問: 事後精算案件のうち、提案時の見積工数と最終報告で報告されている実績工数の乖離が最も大きい案件を主略称で挙げてください。
- 回答: かえで総合病院
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx`

### index 56

- 質問: 蒼泉会 ひがし丘総合病院の01_eda.ipynbにおける目的変数分析の可視化において、y軸に実際に表示されている目盛りの最大値は何ですか。
- 回答: 1256
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb`

### index 57

- 質問: 青葉のTXにて算出された回帰係数を用いて全データの予測値を計算し、正解データに対する F1 スコアが最大となるように閾値を設定したときの F1 スコアを答えてください。小数第5位まで求めてください。
- 回答: 0.00000
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/src/evaluate.py.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/04.分析/analysis_project/src/evaluate.py.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/old/青葉与信マネジメント株式会社_最終報告.pptx.structure.json`

### index 58

- 質問: 社内管理フォルダにあるFMにおいて、井上さんの向かいに座っている方のEXTを教えてください。
- 回答: わかりません
- source_confidence: `none`
- answer_status: `unknown`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/社内管理/座席表.pptx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/座席表.pptx.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx.md`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/03.データ/カラム説明.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/03.データ/カラム説明.md`

### index 59

- 質問: 京ソのPP_final.pptxにおいて、この案件にかかる金額の提示がまとまっているのは何ページですか。
- 回答: 2ページ
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

### index 60

- 質問: 白峰信用リスク評価の最終報告資料内で未完事項として挙げられているIDをすべて抽出してください。
- 回答: AI-05、AI-09、AI-08
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx.md`

### index 61

- 質問: 京橋信用ソリューションズの分析コードにおいて、今回の学習で勾配ブースティング法のモデルに実際に渡される n_estimators、learning_rate、random_state はそれぞれいくつですか。設定ファイルに明示されていない値がある場合も、実行時にコード上で適用される値を含めて答えてください。
- 回答: n_estimators=500、learning_rate=0.3、random_state=42
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/scripts/run_train.py.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/src/modeling.py.md`

### index 62

- 質問: 青葉与信マネジメントの最終報告資料における、モデル比較で上位2件のスコア差を生んでいる設定差分は何ですか。
- 回答: n_estimatorsが500と300で異なります。
- source_confidence: `high`
- answer_status: `answered`
- ソースファイル:
  - `data\processed\share\share\共有ドライブ\プロジェクト\青葉与信マネジメント株式会社\06.報告書\青葉与信マネジメント株式会社_最終報告.pptx.md`
  - `data\processed\share\share\共有ドライブ\プロジェクト\青葉与信マネジメント株式会社\04.分析\analysis_outputs\experiments\leaderboard.csv.data.csv`
  - `data\processed\share\share\共有ドライブ\プロジェクト\青葉与信マネジメント株式会社\04.分析\analysis_outputs\experiments\leaderboard.csv.md`

### index 63

- 質問: 青葉与信マネジメントのtrain.xlsxにて算出された回帰係数を使ってid=0を予測した場合の予測値はいくらになりますか。小数第5位まで求めてください。
- 回答: 0.21480
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`

### index 64

- 質問: 青潮モビリティサービスの最終報告PDFにおいて、将来のフェーズAとフェーズBを実施した場合の想定工数は合計で何時間ですか。
- 回答: 0
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/会議録/会議録_2025-08-26.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx`

### index 65

- 質問: 白峰信用リスク評価のtrain.xlsxにおいて、表示されている相関係数シートで、黄色ハイライトになっているセルの条件を答えてください。
- 回答: 相関係数シートで、相関係数の絶対値が0.5を超えるセル(例:Attr2 と Attr3 の相関係数 -0.9960099740512748)が黄色ハイライトされます。
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/社内管理/社内用語集.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`
  - `share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx`

### index 66

- 質問: 京橋信用ソリューションズのEDAの日付分析の可視化において、件数が最も高いのは何日ですか。
- 回答: 20日
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/03.データ/train.csv`

### index 67

- 質問: 完了案件のうち、社内管理のAPRでAPR-M2に該当する案件の中で、提案時金額とFR時の金額が異なる案件を案件略称ですべて挙げてください。
- 回答: 該当案件はありません
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`
  - `share/共有ドライブ/社内管理/社内用語集.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx`

### index 68

- 質問: 東都人材プラットフォームのデータサイエンス市場の未来予測.pdfにおいて、投資実装係数の計算式が記載されているページの数値情報を式に代入し、投資実装係数を小数で答えてください。
- 回答: 0.5
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンス市場の未来予測.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

### index 69

- 質問: 白峰信用リスク評価の最終報告資料において、パイロット運用は本番化スケジュール上で第何週目から第何週目に実施予定ですか。
- 回答: W7〜W8
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx.md`

### index 70

- 質問: 白峰信用リスク評価の5月27日の報告資料で Open として優先フォロー対象に挙げられているアクションIDの中で、会議録において完了となっていないIDを上げてください。
- 回答: なし
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/白峰信用リスク評価株式会社/06.報告書/白峰信用リスク評価株式会社_最終報告.pptx.structure.json`

### index 71

- 質問: 青嶺不動産アセットマネジメントの会議録の中で、太字、下線、イタリックのすべてに該当する箇所を抽出してください。
- 回答: 4,250,000円
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/会議録/会議録_2025-08-06.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/会議録/会議録_2025-08-26.docx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/会議録/会議録_2025-09-16.docx.structure.json`

### index 72

- 質問: KSSにおいて、データエンジニアが担当するタスクIDはいくつありますか。
- 回答: 0
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/05.会議/会議録/会議録_2025-10-01.pdf`

### index 73

- 質問: 恒一会のPPで言及されている One-Hot Encoding のカテゴリ数閾値を実装設定から確認したうえで、その条件により One-Hot Encoding の対象となるカテゴリ列をすべて答えてください。
- 回答: 対象列はありません
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx.structure.json`

### index 74

- 質問: 青葉与信マネジメントの提案書_v1.pptxから提案書_v2.pptxに修正されたもののうち、案件遂行に関連する変更を挙げてください。
- 回答: 変更なし
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/00.提案/提案書_v1.pptx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/00.提案/提案書_v3.pptx.md`

### index 75

- 質問: MINAMINOのPP内のPL案において、モデル構築は第何週に実施することになっていますか。
- 回答: 第4週
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/02.計画/スケジュール.xlsx.sheets/スケジュール管理表.csv`

### index 76

- 質問: AOMINEの契約条件において、契約単価が現状よりも2,000円高く、実績工数が11.2時間少なかった場合、税込請求金額は、実際の税込請求金額と比べていくら変動しますか。
- 回答: 22,400円
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告_old.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/00.提案/提案書.pptx`

### index 77

- 質問: 蒼泉会 ひがし丘総合病院のtrain.xlsxのSheet2において、黄色ハイライトされている数値に対応するデータの抽出条件と集計内容を答えてください。
- 回答: Sheet2!E14=6746、条件: col_2=northwest、col_3=6103.852518680003、col_4=3、集計: col_5
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/03.データ/train.xlsx.structure.json`

### index 78

- 質問: ひがし丘の契約条件において、ACTHが200時間を超えた場合の精算方法に関する規定内容を答えてください。
- 回答: 超過分は別途請求する
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/01.契約/契約書.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-29.docx`

### index 79

- 質問: 恒一会 かえで総合病院の計画フォルダ内において、データアステル側の担当者のうち、1タスク当たりの想定工数（想定工数 ÷ 担当タスク数）が最も大きい人のフルネームと、その1タスク当たりの想定工数を小数第2位で答えてください。ファイルに鍵がかかっている場合は社内管理を確認してください。
- 回答: 松本 真央、35.00時間
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/raw/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/02.計画/スケジュール.xlsx`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/会議録/会議録_2025-09-30.docx.md`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/06.報告書/医療法人社団 恒一会 かえで総合病院_最終報告.pptx.md`

### index 80

- 質問: 東都人材プラットフォームのtrain.xlsxにおいて、Sheet2の黄色にハイライトされたセルの抽出条件と集計内容を答えてください。
- 回答: 抽出条件はGender=Male、target=2、Age=40-44、Country=Spain。集計内容は個数=12。
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.xlsx.structure.json`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.xlsx.sheets/Sheet1.csv`

### index 81

- 質問: 京橋信用ソリューションズとの契約書において、太字で記載されている部分を抽出してください。
- 回答: 契約締結日兼効力発生日:2025-10-01
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/01.契約/契約書.docx.structure.json`

### index 82

- 質問: 蒼泉会 ひがし丘総合病院のスケジュール.xlsxにおいて、WBSシートでオレンジ色にハイライトされている行のタスクIDをすべて教えてください。
- 回答: T02、T14、T16、T22、T24
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/02.計画/スケジュール.xlsx.structure.json`

### index 83

- 質問: 蒼樹会 みなみ野女性医療センターのtrain.xlsxにおいて、回帰分析の結果として記載されている係数をindex=1770のデータに当てはめたときの予測値はいくつですか。小数第5位まで答えてください。
- 回答: 0.38317
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/03.データ/train.xlsx.sheets/Sheet1.csv`
  - `data/processed/share/share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/03.データ/train.xlsx.sheets/train.csv`

### index 84

- 質問: 東都人材プラットフォームの最終報告書で分析結果が記載されている中で、モデル毎のF1スコアがランキング形式で記載されているページ数を教えてください。
- 回答: 5ページ目。
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/06.報告書/青葉与信マネジメント株式会社_最終報告.pptx`

### index 85

- 質問: 青葉バイオメディカル機器の最終報告において、設定されたKPIとして未達成とされている項目を挙げてください。
- 回答: なし
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/06.報告書/株式会社青葉バイオメディカル機器_最終報告.pptx`

### index 86

- 質問: 各案件のPP・契約書・PLAN・FRにおいて、DA側の実施体制として役割付きで記載されている人物は全部で何人ですか。
- 回答: 9
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx.structure.json`
  - `data/processed/share/share/共有ドライブ/社内管理/社内用語集.docx.structure.json`

### index 87

- 質問: 完了案件のうち、社内管理のAPRでAPR-M1に該当し、かつ顧客データのサンプル数が10000行以上の案件を、案件略称ですべて挙げてください。
- 回答: 該当案件なし
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/社内管理/社内用語集.docx`
  - `share/共有ドライブ/社内管理/データアステル社内管理_決裁基準.md`
  - `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx`

### index 88

- 質問: 蒼樹会 みなみ野女性医療センターの提案書内のスケジュール案において、第5週目に実施することになっている項目は何ですか。
- 回答: 解釈分析・特徴量整理、業務活用示唆整理、最終報告書ドラフト作成
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/02.計画/スケジュール.xlsx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf`

### index 89

- 質問: 京橋信用ソリューションズのスケジュール.xlsxにおいて、フェーズNo6にて最後に開始するタスク名は何ですか。
- 回答: 最終モデル確定・再評価
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/02.計画/スケジュール.xlsx.sheets/WBSタスク一覧.csv`

### index 90

- 質問: 青潮モビリティサービスのスケジュール.xlsxにおいて、バッファとして使用した工数の合計は何時間ですか。
- 回答: 14時間
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/02.計画/スケジュール.xlsx`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-07-23.docx`

### index 91

- 質問: 京橋信用ソリューションズの顧客データにおいて、目的変数と最も強い負の相関を持つカラムは何ですか。
- 回答: campaign
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/03.データ/train.csv.data.csv`

### index 92

- 質問: 恒一会 かえで総合病院案件において、マイルストーンID、タスクID、アクションIDの3種類のIDは合計でいくつ発行されていますか。マークダウンファイル以外から算出してください。
- 回答: 41件
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/02.計画/スケジュール.xlsx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`

### index 93

- 質問: 蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。
- 回答: index再実験の結果反映
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `EDA/EDA052/rendered_pages/医療法人社団_蒼樹会_みなみ野女性医療センター_会議録_2025_05_15_pdf_page002.png`

### index 94

- 質問: 蒼樹会 みなみ野女性医療センターのスケジュール.xlsxにおいて、MS3に紐づくタスクのうち、ビジネスアナリストが関わっているタスクIDを答えてください。
- 回答: []
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/02.計画/スケジュール.xlsx`
  - `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/提案書.pptx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf`

### index 95

- 質問: 青嶺不動産アセットマネジメントのスケジュール_r1.xlsxとスケジュール_r2.xlsxを比較したとき、未着手から完了への変更を除いて、案件遂行に関連する変更点を挙げてください。
- 回答: T15「モデル評価・重要特徴量整理」の担当者が、渡辺 遥から渡辺 遥 / 小林 直樹に変更された。
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r1.xlsx.sheets/スケジュール.csv`
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/02.計画/スケジュール_r2.xlsx.sheets/スケジュール.csv`

### index 96

- 質問: 青葉与信マネジメントのチェックポイント2として設定されている内容に関連するタスクIDを教えてください。
- 回答: T05、T06、T07、T08
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `EDA/EDA050/tables/checkpoint_task_inventory.csv`
  - `data/processed/share/share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/02.計画/スケジュール.xlsx.sheets/Sheet2.csv`

### index 97

- 質問: 青葉バイオメディカル機器のtrain.xlsxにおいて、黄色ハイライトが交差している2つのセルの値の差の絶対値を計算してください。
- 回答: 3778
- source_confidence: `medium`
- answer_status: `answered`
- ソースファイル:
  - `data/processed/share/share/共有ドライブ/プロジェクト/株式会社青葉バイオメディカル機器/03.データ/train.xlsx.structure.json`

### index 98

- 質問: TM案件において、RATEが変更されたのは何年何月1日からと想定されますか。
- 回答: o 契約開始日: 2025-08-06(適用開始)
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-06.pdf`
  - `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`
  - `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`
  - `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/ニューヨーク不動産市場の最新動向調査.pdf`

### index 99

- 質問: 蒼樹会 みなみ野女性医療センターの糖尿病統計情報調査結果において、死亡率が最も高い都道府県の死亡率は、4番目に低い都道府県の死亡率の何倍ですか。小数第2位まで求めてください。
- 回答: 3.00
- source_confidence: `low`
- answer_status: `answered`
- ソースファイル:
  - `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx`

