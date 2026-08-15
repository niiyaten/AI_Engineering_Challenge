# test_075

## Question
MINAMINOのPP内のPL案において、モデル構築は第何週に実施することになっていますか。

## Route
fallback_bm25_llm

## Generated Answer
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**PythonとSQLの覇権**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: 2024年のAnacondaの調査によれば、データサイエンティストの34%が日常業務でPythonを使用しており、最も人気のあるプログラミング言語としての地位を確固たるものにしている。SQLと組み合わせることで、データの抽出・加工からモデル構築までを一貫して行うための基本装備となっている。</span></span>

## Retrieved Records

### Rank 1
- score: 62.331787
- record_id: `generic_chunk_06c339eee5202c19`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
yle=Compact -->
T03: 0.7126899909960438

<!-- block_index=27 type=paragraph style=Compact -->
T05: 0.7126899909960438

<!-- block_index=28 type=paragraph style=Compact -->
run-level 指標（analysis.metrics より）:

<!-- block_index=29 type=paragraph style=Compact -->
auc_roc: 0.8250532501536466

<!-- block_index=30 type=paragraph style=Compact -->
precision_at_top10pct: 0.9428571428571428

<!-- block_index=31 type=paragraph style=Compact -->
brier_score: 0.17514583544772114

<!-- block_index=32 type=paragraph style=Compact -->
selected_feature_count: 10, excluded_feature_count: 1

<!-- block_index=33 type=paragraph style=Compact -->
実装／環境

<!-- block_index=34 type=paragraph style=Compact -->
実験は線形系（linear_baseline 系）モデル群で実施。decision-tuning（クラス判定重みの調整）が T04 の改善要因として報告されています（visible_trials の change_summary に記載）。

<!-- block_index=35 type=paragraph style=Heading 2 -->
## 3. 主要な分析結果

<!-- block_index=36 type=paragraph style=Compact -->
モデル比較（可視領域の要点）

<!-- block_index=37 type=paragraph style=Compact -->
ベースライン（T01）から段階的にクラスバランスや特徴量拡張、閾値調整を行い、T04（閾値チューニング済み線形モデル）が最も高い f1_macro を示した（f1_macro = 0.7329671168078127）。このことは、現データにおいて「モデル構造を大きく変えずに、決定閾値やクラス判断の調整で性能改善が得られる」ことを示唆します。

<!-- block_index=38 type=paragraph style=Compact -->
AUC-ROC（0.8250532501536466）や top10% precision（0.9428571428571428）が比較的良好である点は、スコア上位の予測が高い精度で陽性を含む可能性を示しており、閾値運用による業務ルール設計の余地があります。

<!-- block_index=39 type=paragraph style=Compact -->
特徴量・前処理の状況

<!-- block_index=40 type=paragraph style=Compact -->
モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。

<!-- block_in
```

### Rank 2
- score: 57.376631
- record_id: `generic_chunk_866a86384dfb5e4b`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx`

```text
脆弱であり、肺炎による死亡が第2位の大きなシェアを占めている点は、ワクチン接種などの予防医療の重要性を裏付ける統計データとなっている 。

<!-- block_index=43 type=paragraph style=Normal -->
**治療継続性の課題：受診中断率と特定健診の実施状況**

<!-- block_index=44 type=paragraph style=Normal -->
糖尿病は「サイレント・キラー」と呼ばれ、初期段階では自覚症状が乏しいため、治療の継続が困難な疾患である。統計によれば、日本国内で糖尿病治療を受けている患者のうち、1年間で約8%から10%が通院を中断している 。

<!-- block_index=45 type=paragraph style=Normal -->
受診中断者の特性を分析した統計では、以下の傾向が明らかになっている。

<!-- block_index=46 type=paragraph style=Normal -->
**年齢的要因**: 65歳以上の高齢者と比較して、20代から40代の若年・中年層で中断率が有意に高い 。

<!-- block_index=47 type=paragraph style=Normal -->
**社会経済的要因**: 働いている男性に多く、中断理由の38.2%が「仕事が忙しくて時間が取れない」ことである 。また、医療費の経済的負担を理由に挙げる者も一定数存在する 。

<!-- block_index=48 type=paragraph style=Normal -->
**心理・認知的要因**: 自覚症状がないために「治療の必要性を感じない（16.4%）」、あるいは血糖コントロールが一時的に良好になったことで「治った」と誤認して自己判断で中断するケースが認められる 。

<!-- block_index=49 type=paragraph style=Normal -->
**臨床的指標**: HbA1c 8.0%以上のコントロール不良群は、優良群と比較して受診中断リスクが約4倍高いという「負の連鎖」が存在する 。

<!-- block_index=50 type=paragraph style=Normal -->
治療継続を阻むこれらの要因は、重症化予防における最大のボトルネックとなっている。特定健康診査（特定健診）の実施率は令和4年度で58.1%であり、目標の70%には届いていない 。特に特定保健指導の実施率は26.5%と低く、生活習慣の改善が必要な層への介入が不十分な実態が統計的に示されている 。これに対し、ITシステムを活用した受診勧奨（FROM-J研究など）では、介入群において専門医への紹介率や受診継続率が有意に高まることが報告されており、テクノロジーを用いた解決策の有効性が示唆されている 。

<!-- block_index=51 type=paragraph style=Normal -->
**薬剤処方動向の変化：SGLT2阻害薬とGLP-1受容体作動薬の台頭**

<!-- block_index=52 type=paragraph style=Normal -->
ナショナルレセプトデータベース（NDB）オープンデータの詳細な分析により、日本国内の糖尿病薬物療法のパラダイムシフトが鮮明になっている。2015年度から2022年度にかけての処方薬の占有率の変化は、エビデンスに基づいた薬剤選択の変遷を如実に示している 。

<!-- block_index=53 type=paragraph style=Normal -->
以下の表は、主要な糖尿病治療薬の数量シェアおよび年平均変化率（APC）をまとめたものである
```

### Rank 3
- score: 57.352801
- record_id: `generic_chunk_56531f6bc167815e`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
k_index=40 type=paragraph style=Compact -->
モデルが使用している選択特徴数は 10、除外特徴は 1（analysis.metrics / run_summary 相関）で、feature selection が適用されていることを確認しています。

<!-- block_index=41 type=paragraph style=Compact -->
モデル群は線形系での評価を優先しているため、説明可能性が確保された状態での比較が行われています。

<!-- block_index=42 type=paragraph style=Compact -->
臨床的解釈上の留意

<!-- block_index=43 type=paragraph style=Compact -->
本段階での結果は学習データ内（ホールドアウト検証等）での指標であり、外部検証データや運用環境での再現性は未確認です。運用導入の判断には追加検証（外部データや診療フローを反映した評価）が必要です。

<!-- block_index=44 type=paragraph style=Heading 2 -->
## 4. データ品質と実装状況

<!-- block_index=45 type=paragraph style=Compact -->
データ受領／EDA／前処理

<!-- block_index=46 type=paragraph style=Compact -->
キックオフ（M01）での合意に基づき EDA・前処理方針を実施し、可視実験群を生成しています（visible_trials 実行）。feature_selection の結果（selected 10, excluded 1）が得られています。

<!-- block_index=47 type=paragraph style=Compact -->
欠損値や行数・列数の詳細（例: 行数 3,500、欠損数 0 等）はプロジェクト概要に記載されていますが、これらの具体数値が Report facts JSON に含まれていない場合は「assumption」で扱います。該当数値（行数・欠損等）を参照する場合は「assumption」と明示して運用してください。

<!-- block_index=48 type=paragraph style=Compact -->
例: 「train.csv の行数 = 3,500」「欠損数 = 0」はプロジェクト概要に記載されているが、Report facts JSON に explicit に含まれないため本レポートでは（assumption）として扱います。

<!-- block_index=49 type=paragraph style=Compact -->
実装ステータス（analysis.implementation_status）

<!-- block_index=50 type=paragraph style=Compact -->
実装ステータスは “interim_analysis”（中間分析段階）。モデル構築・比較は実施済み（visible_trials）が、最終モデル確定・本番化は未実施。

<!-- block_index=51 type=paragraph style=Compact -->
再現性トレース

<!-- block_index=52 type=paragraph style=Compact -->
実行結果・ソースのトレースは Report facts の trace.source_files に保存パスが示されています（例: artifacts/analysis_o
```

### Rank 4
- score: 57.081107
- record_id: `generic_chunk_ed35436b8aefc181`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
析から、クラウドネイティブなAI実装へと完全にパラダイムシフトを遂げている。</span></span>

<!-- block_index=109 type=paragraph style=Heading 3 -->
### <span data-font-name="Arial Unicode MS" data-font-size-pt="13.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**7.1. 中核となる技術スタックと業務の実態**</span></span>

<!-- block_index=110 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">今日において高い収入を獲得するために不可欠なコアスキルは、複数のツールチェーンを統合する能力である。</span></span>

<!-- block_index=111 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**PythonとSQLの覇権**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: 2024年のAnacondaの調査によれば、データサイエンティストの34%が日常業務でPythonを使用しており、最も人気のあるプログラミング言語としての地位を確固たるものにしている。SQLと組み合わせることで、データの抽出・加工からモデル構築までを一貫して行うための基本装備となっている。</span></span>

<!-- block_index=112 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**機械学習（Machine Learning）の常態化**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: Kaggleの調査では、日常業務で機械学習の手法を定期的に使用しているデータサイエンティストは83%に上る。もはやMLは特殊な技術ではなく、日常的な分析ツールの一部となっている。</span></span>

<!-- block_index=113 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**クラウドとインフラ構
```

### Rank 5
- score: 50.357832
- record_id: `generic_chunk_5641d27c55a9d5ba`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
ているシンガポールは、データサイエンス業界において最大122,923 SGD（シンガポールドル）の獲得可能性を持ち、平均でも104,999 SGDと極めて高い水準を誇っており、アジア圏において突出した引力を放っている。</span></span>

<!-- block_index=27 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">この圧倒的な格差は、多国籍企業における「労働のアービトラージ（裁定取引）」を強烈に促進している。米国企業は、同等水準の数理能力を持つ人材を求めて、インドのハイデラバードやムンバイ、さらには東欧や日本へ業務をアウトソーシングする、あるいはフルリモートでの直接雇用を拡大する強力な経済的インセンティブを持っている。逆に、非米国のトップタレントにとっては、居住地を維持したまま米国水準の給与（あるいは現地の相場を大きく上回る調整給与）を提示する外資系企業への流出が容易になっており、これにより日本や欧州の国内伝統企業は、優秀な人材の獲得において深刻な競争力不足に陥っているのが現状である。</span></span>

<!-- block_index=28 type=paragraph style=Heading 2 -->
## <span data-font-name="Arial Unicode MS" data-font-size-pt="17.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**4. 日本市場における報酬構造の深層：伝統的慣行とテクノロジー需要の衝突**</span></span>

<!-- block_index=29 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">世界第3位の経済規模を誇りながらも、独自の雇用慣行（メンバーシップ型雇用や年功序列）を長らく維持してきた日本市場において、データサイエンティストの報酬構造は極めて特異な進化を遂げている。</span></span>

<!-- block_index=30 type=paragraph style=Heading 3 -->
### <span data-font-name="Arial Unicode MS" data-font-size-pt="13.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**4.1. マクロな市場規模と構造的な人材不足**</span></span>

<!-- block_index=31 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">日本のテクノロジー環境は急速に進化しており、ロボティクス、AI、IoTの分野で世界を牽引している。IDCの予測によると、日本のビッグデータおよびアナリティクス市場は2025年までに250億ドル規模に達するとされ
```

### Rank 6
- score: 49.775558
- record_id: `pptx_slide_ecc03e6f13a78ef0`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx`

```text
Slide 10
04
4.3 モデル構築 / 4.4 解釈・示唆整理
4.3 モデル構築・比較
ベースラインモデル
基準性能を把握するための最も単純なモデル
線形系分類モデル
解釈可能性が高く、変数寄与の理解に適する
木系/非線形分類モデル
複雑なパターンの捕捉に優れ、高い性能を期待
学習データ内で適切な分割・検証を行い、ROC-AUC、Accuracy、Precision、Recall、F1-scoreで比較する。
4.4 解釈・示唆整理
▶ 重要特徴量の確認
▶ 誤判定傾向の把握
▶ 業務での利用可能性と限界の整理
▶ 「診断」ではなく「判定支援材料」としての位置づけを明示
医療文脈において重要なRecallと、それに伴うPrecisionのバランスを特に確認する
```

### Rank 7
- score: 48.057763
- record_id: `generic_chunk_226342815df28cdc`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
# Word Markdown: データサイエンティスト調査.docx

## Source
- raw_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`
- source_sha1: `5840fe0638d88d581a14bd71de0ad712df124754`
- paragraph_count: 128
- table_count: 3
- image_count: 1

## Body

<!-- block_index=1 type=paragraph style=Heading 1 -->
## <span data-font-name="Arial Unicode MS" data-font-size-pt="23.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**データサイエンティストの収入水準、労働市場の構造、および技術的変遷に関する包括的調査報告**</span></span>

<!-- block_index=2 type=paragraph style=Heading 2 -->
## <span data-font-name="Arial Unicode MS" data-font-size-pt="17.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**1. 導入：データ駆動型経済におけるデータサイエンティストの市場価値の根源**</span></span>

<!-- block_index=3 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">現代のグローバル経済において、データサイエンティストという職業は、単なる技術的専門職の枠を超え、企業の競争優位性を決定づける中核的な資本として位置づけられている。この現象の背景には、世界規模での爆発的な情報生成と、それを処理するための計算能力の飛躍的な向上が存在する。2023年の単年において、世界中で生成されたデータ量は約132ゼタバイト（1,320億テラバイト）に達しており、企業はかつてない規模の「データのゴールドラッシュ」の只中にある。</span></span>

<!-- block_index=4 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">この膨大なデータ資源を経済的価値へと変換するプロセスが、データサイエンティストに対する莫大な報酬の源泉となっている。Fortune Business Insightsの報告によれば、世界のデータサイエンス市場規模は2024年時点で1,331億2,000万米ドルに達している。さらに、McKinsey &amp; Companyの調査は、データ駆動型の意思決定を組織的に導入している企業が、新規顧客の獲得において23倍、既存顧客の維持において6倍という圧倒的な効率性を示していることを実証している。また、Deloitteの調査においても、企業の65%がビジネスの成功においてデータ駆動型の意思決定が不可欠な価値を持つと認
```

### Rank 8
- score: 47.370743
- record_id: `generic_chunk_d75f61ad56dcda5b`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx`

```text
| 4.3 | 0.7 |
| 40-49歳 | 10.1 | 1.8 |
| 50-59歳 | 17.8 | 6.1 |
| 60-69歳 | 25.3 | 12.0 |
| 70歳以上 | 26.4 | 16.8 |
| 全世代平均 | 18.1 | 9.1 |

<!-- block_index=14 type=paragraph style=Normal -->
年齢層別の統計を詳細に分析すると、男女ともに加齢に伴い有病率が上昇する明快な勾配が認められる。特に男性においては、60歳以降で4人に1人が糖尿病を強く疑われる段階にあり、女性でも70歳以上になると約17%から20%弱が該当する 。男性は女性と比較して、概ね全年齢層で約2倍の発症リスクを有しており、この背景には肥満、高血圧、飲酒、喫煙といった生活習慣因子の関与が示唆されている 。

<!-- block_index=15 type=paragraph style=Normal -->
令和5年（2023年）の「患者調査」の概況では、糖尿病で継続的に治療を受けている総患者数は約552万2,000人と推計されている 。前回調査（令和2年）の579万1,000人と比較すると、約26万9,000人の減少が認められるが、これは新型コロナウイルス感染症の影響による受診控えや、統計的手法の変動、あるいは死亡数の増加など複数の要因を慎重に吟味する必要がある 。疾患別の内訳では、2型糖尿病が363万9,000人と圧倒的多数を占め、1型糖尿病は12万2,000人となっている 。

<!-- block_index=16 type=paragraph style=Normal -->
生活習慣の指標としての肥満度（BMI 25以上）の推移も、糖尿病統計と密接に連動している。男性の肥満者割合は31.5%（2023年）であり、特に40代（39.7%）や50代（39.2%）の中年層で極めて高い水準にある 。一方、女性においては「やせ（BMI 18.5未満）」の割合が12.0%と高く、特に20代女性の20.2%が「やせ」に該当するという統計は、将来的な糖尿病リスクの増大という観点から、新たな公衆衛生上の懸念材料となっている 。

<!-- block_index=17 type=paragraph style=Normal -->
**都道府県別格差：死亡率ワースト地域とベスト地域の要因分析**

<!-- block_index=18 type=paragraph style=Normal -->
日本国内の糖尿病統計において最も顕著な特徴は、地理的な「健康格差」である。厚生労働省の「人口動態統計」に基づくと、糖尿病による死亡率（人口10万人対）には都道府県間で明確な有意差が存在する。全国平均の死亡率が10.6%であるのに対し、特定の地域で継続的に高い死亡率が記録されている 。

<!-- block_index=19 type=paragraph style=Normal -->
以下の表は、糖尿病による死亡率の都道府県別ランキング（ワーストおよびベスト）をまとめたものである。

<!-- block_index=20 type=table rows=6 cols=5 -->
| 順位 | 死亡率が高い都道府県（ワースト） | 死亡率（%） | 死亡率が低い都道府県（ベスト） | 死亡率（%） |
| --- | --- | --- | --- | --- |
| 1位 | 青森県 | 18.2 | 神奈川県 | 7.2 |
| 2位 | 秋田県 | 16.3 | 愛知県 | 7.9 |
| 3位 | 香川県 | 16.1 | 東京都 | 8.8 |
| 4位 | 鹿児島県 | 15.0 | 滋賀県
```
