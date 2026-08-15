# test_098

## Question
TM案件において、RATEが変更されたのは何年何月1日からと想定されますか。

## Route
diff_check

## Generated Answer
日本政府は「健康日本21（第三次）」において、2024年度から2035年度までの期間、糖尿病対策のさらなる強化を打ち出している。これまでの統計的成果と課題を踏まえ、以下の具体的な目標が設定されている。

## Retrieved Records

### Rank 1
- score: 43.761047
- record_id: `pdf_page_f31a195f223cee62`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-06.pdf`

```text
o 中間報告ゲート: MS4（中間報告承認）: 2025-08-26（予定）
3. 主要な分析結果
（注）現在はキックオフ段階のため、モデル結果や最終評価指標は存在しません。以下はデータ理解フェーズでの初
期観察・要確認事項です。数値の多くはプロジェクト概要に基づくため Report facts JSON に未記載の項目は
「（assumption）」と明示しています。
• 目的変数関連
o 目的変数: SALE PRICE（設定済）。（config 等により target_column は SALE PRICE と確
定）
o SALE PRICE のサンプル要約（参照資料ベース）: レコード数 37,751（assumption）、最小
100,700（assumption）、最大 4,996,841（assumption）、平均 約 870,378.47
（assumption）。分布は右に歪んでいる可能性が高く、対数変換の検討が必要。
• データ品質関連の初期発見（要対応）
o 面積項目の欠損が多い: LAND SQUARE FEET 欠損 13,262 件（assumption）、GROSS
SQUARE FEET 欠損 13,555 件（assumption）。0 値も混在。
o 築年・郵便番号の異常値疑い: YEAR BUILT 最小 0、平均 ≒ 1,817.78（assumption）／ZIP
CODE に 0 が含まれる（assumption）。入力誤・欠損代替・非開示を切り分ける必要あり。
o 建物クラス・税区分の欠損: TAX CLASS AT PRESENT 欠損 362（assumption）、
BUILDING CLASS AT PRESENT 欠損 362（assumption）。
o 立地変数（BOROUGH, NEIGHBORHOOD, ZIP CODE）は価格差の主要要因と想定。
BOROUGH は 1–5 のコード（Manhattan 等）で重要軸。
o 設定ミス・確認要: analysis/config において date_column が "TAX CLASS AT TIME OF
SALE" に設定されている（configs/project_config.json / analysis_spec）。当該列名は日
付でない可能性が高く、日付列指定の再確認が必要（未解決事項）。
• 実験状況
o 現時点で可視化された試行（visible_trials）は無し（analysis.visible_trials = []）。モデル学
習・評価は実施前（implementation_status = planning_only）。
4. データ品質と実装状況
• データ品質（要点、数値は原資料に基づく／assumption 表示）
o 総レコード数: 37,751（assumption）
o 欠損/異常の注目点:
▪ LAND SQUARE FEET 欠損 13,262（assumption）
▪ GROSS SQUARE FEET 欠損 13,555（assumption）
```

### Rank 2
- score: 39.478635
- record_id: `generic_chunk_86688391df015650`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
&amp; Companyの調査は、データ駆動型の意思決定を組織的に導入している企業が、新規顧客の獲得において23倍、既存顧客の維持において6倍という圧倒的な効率性を示していることを実証している。また、Deloitteの調査においても、企業の65%がビジネスの成功においてデータ駆動型の意思決定が不可欠な価値を持つと認識しており、IBMの報告では59%の組織がビッグデータ分析の導入による競争優位性の獲得を明確に認めている。</span></span>

<!-- block_index=5 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">このように、データサイエンティストが創出する投資対効果（ROI）が定量的に証明されていることが、労働市場における同職種の需要を牽引している。米国労働省統計局（Bureau of Labor Statistics: BLS）の予測によれば、2024年から2034年にかけてのデータサイエンティストの雇用成長率は34%と見込まれており、全職業の平均を大きく上回る「極めて速い（Much faster than average）」成長カテゴリに分類されている。今後10年間にわたり、毎年約21,000件の新規求人が創出され、2024年から2034年の間だけで82,500人の雇用増加が予測されている。</span></span>

<!-- block_index=6 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">本報告では、この極めて流動的かつ成長著しい労働市場において、データサイエンティストの収入がいかなる要因（地理的条件、産業構造、教育水準、技術スキル、および生成AIなどのマクロトレンド）によって決定されているのかを、複数の信頼性の高い統計データに基づいて多角的に分析し、その構造的メカニズムを解き明かす。</span></span>

<!-- block_index=7 type=paragraph style=Heading 2 -->
## <span data-font-name="Arial Unicode MS" data-font-size-pt="17.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**2. 米国市場における報酬構造の精緻な分析：グローバルベンチマークとしての米国**</span></span>

<!-- block_index=8 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">世界最大のテクノロジークラスターと資本市場を擁する米国におけるデータサイエンティストの報酬体系は、世界の労働市場における事実上の標準（デファクト・スタンダード）として機能している。米国の報酬構造を分析することは、資本主義経済がいかに高度な知能労働を評価しているかを理解する上で不可欠である。</span></span
```

### Rank 3
- score: 37.459
- record_id: `generic_chunk_dc945ce455ac24aa`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx`

```text
500,000 円、消費税額: 350,000 円、見込金額（税込）: 3,850,000 円（payment_schedule に明記）

<!-- block_index=81 type=paragraph style=Compact -->
支払条件: 最終一括精算（最終成果物検収完了後5営業日以内）※支払スケジュールは単一回の最終精算（Report facts JSON の commercial.payment_schedule を参照）。

<!-- block_index=82 type=paragraph style=Compact -->
当面の注視点（経営判断に資する事項）

<!-- block_index=83 type=paragraph style=Compact -->
現時点は評価／モデル作成前の「準備段階」です。期待される成果（モデル精度・業務効果）は EDA→試作→評価 の順で確定されます。経営判断で必要な場合は「外部検証用データの準備」や「追加のドメイン確認（医師レビュー）」を早期に合意ください。

<!-- block_index=84 type=paragraph style=Compact -->
追加要求発生時の精算方針は time_and_materials（追加は別途見積り）です。スコープ外要望が生じた場合は 2025-09-19 の変更管理チェックポイントで影響を判断する運用としています（日付はスケジュール資料に基づく想定／assumption）。

<!-- block_index=85 type=paragraph style=Compact -->
プロジェクトは「判定支援材料の整備」を目的としており、成果物では診断の断定表現を避ける必要があります。成果物の公開・活用範囲は必ず合意された運用ルールに従ってください。

<!-- block_index=86 type=paragraph style=Compact -->
現時点での重要エビデンス（トレーサビリティ）

<!-- block_index=87 type=paragraph style=Compact -->
キックオフ想定決定事項、ステージは Report facts JSON.checkpoint に記録済み。

<!-- block_index=88 type=paragraph style=Compact -->
prior_state に議事録やオープンアクションが未登録であるため、議事録（キックオフ合意）の登録を優先してください（責任者: PM 佐藤 健一）。

<!-- block_index=89 type=paragraph style=Normal -->

<!-- block_index=90 type=paragraph style=First Paragraph -->
以上。次回（中間レビュー／M02）に向けて、上記の「次回までの実施事項」を優先し、EDA と分析計画の確定を進めます。
```

### Rank 4
- score: 36.740985
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

### Rank 5
- score: 36.546046
- record_id: `pdf_page_7c39b0033a0d3a5a`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/ニューヨーク不動産市場の最新動向調査.pdf`

```text
チャンスを緻密に拾い上げていく適応力に他ならない。
NYC 不動産市場は、かつての「投機的」な性格から、より「規律ある、選別された」市場へと
成熟しつつある。この過渡期において、正確なデータに基づき、税制や法改正の動向を先読み
する戦略こそが、持続可能な価値を創造するための唯一の道である。
```

### Rank 6
- score: 35.614453
- record_id: `generic_chunk_e3d7d82553046347`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx`

```text
る。2015年度から2022年度にかけての処方薬の占有率の変化は、エビデンスに基づいた薬剤選択の変遷を如実に示している 。

<!-- block_index=53 type=paragraph style=Normal -->
以下の表は、主要な糖尿病治療薬の数量シェアおよび年平均変化率（APC）をまとめたものである。

<!-- block_index=54 type=table rows=6 cols=4 -->
| 薬剤クラス | 2015年度シェア | 2022年度シェア | 年平均変化率 (APC) |
| --- | --- | --- | --- |
| SGLT2阻害薬 | 約1.1% | 15.5%〜17.4% | +40%前後 |
| GLP-1受容体作動薬 | 約1.1% | 約2.7% | +19.0% |
| DPP-4阻害薬 | 約27% | 24.3%〜25.3% | -2.1% (微減) |
| メトホルミン | 約37%〜38% | 約40% | +1.0% (安定) |
| SGLT2/DPP4合剤 | - | 急増傾向 | - |

<!-- block_index=55 type=paragraph style=Normal -->
最も劇的な変化を遂げたのはSGLT2阻害薬である。2015年度にはわずか1.1%であったシェアが、2022年度には17%前後にまで急拡大した。この背景には、心血管イベントの抑制や腎保護効果に関する強力な臨床エビデンスの蓄積がある 。また、GLP-1受容体作動薬も、2021年に発売された経口製剤の普及により、処方量が爆発的に増加しており、2022年度の院外処方総量は前年度の約4倍に達している 。

<!-- block_index=56 type=paragraph style=Normal -->
一方で、長らく処方の中心であったDPP-4阻害薬は、依然として高いシェアを誇るものの、微減傾向に転じている 。メトホルミンは、国内外のガイドラインで第一選択薬として推奨されていることから、40%前後の高いシェアを安定的に維持している 。これらの処方動向の変化は、単なる血糖値の低下だけでなく、「臓器保護」や「体重管理」を見据えた包括的な代謝管理へと治療の力点が移っていることを統計的に裏付けている。

<!-- block_index=57 type=paragraph style=Normal -->
しかし、薬剤の進歩の一方で、BMI 30以上の高度肥満者の割合が男女ともに年平均5%以上のペースで増加しているというNDBのデータは警鐘を鳴らしている 。医療技術による介入が、生活習慣の悪化というネガティブなトレンドを十分に抑え込めていない現状があり、今後さらに強力な肥満対策と薬物療法の最適化が求められる。

<!-- block_index=58 type=paragraph style=Normal -->
**未来への展望：健康日本21（第三次）と統計的目標値**

<!-- block_index=59 type=paragraph style=Normal -->
日本政府は「健康日本21（第三次）」において、2024年度から2035年度までの期間、糖尿病対策のさらなる強化を打ち出している。これまでの統計的成果と課題を踏まえ、以下の具体的な目標が設定されている。

<!-- block_index=60 type=paragraph style=Normal -->
**糖尿病有病者数の増加抑制**: 人口構成の変化を考慮した年齢調整有病率の維持、および絶対数としての有病者数を1,350万人以下に抑制することを目指す 。

<!-- block_index=61 type
```

### Rank 7
- score: 33.306169
- record_id: `pptx_slide_f2ad8668248a3f65`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/06.報告書/株式会社東都人材プラットフォーム_最終報告.pptx`

```text
Slide 16
11. 総括
本プロジェクトは6週間の短期フェーズとして想定された範囲内で「収入クラス予測の初期分析と業務示唆」を実現した。
最終モデルにより得られた Macro F1 ≈ 0.474、Accuracy ≈ 0.510 はカテゴリ中心のデータ構成を考慮した初期成果として実務的価値があると判断される。
⚠ 重要: 本成果は「参考情報」であり、制度判断や個別処遇の直接決定には法務・労務レビューや更なる検証が必要である。
次フェーズでの推奨事項
運用基盤の整備
公平性監査の深化
外部データ統合による
外部妥当性検証
15 / 15
```

### Rank 8
- score: 32.740955
- record_id: `generic_chunk_560bfba96d7d11dc`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
に機能しており、前述したグローバルとの報酬格差を温存する一因となっている可能性が示唆される。</span></span>

<!-- block_index=125 type=paragraph style=Heading 2 -->
## <span data-font-name="Arial Unicode MS" data-font-size-pt="17.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**8. 結論および労働市場における中長期的な示唆**</span></span>

<!-- block_index=126 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">本調査において、米国および日本を中心とするデータサイエンティストの報酬データ、技術スキルの変遷、およびマクロ経済環境を統合的に分析した結果、以下の本質的な結論が導き出される。</span></span>

<!-- block_index=127 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**グローバル水準の継続的な高騰と市場格差の固定化**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: データサイエンティストは、依然として資本主義経済において最高峰の経済的見返りが約束された職種である。米国市場における基本給の中央値は約12万ドル、総報酬は15万ドル以上に達し、今後10年間で34%という驚異的な雇用成長が予測されている。一方で、日本、欧州、インド等の市場との間には2倍から最大9倍近い報酬格差が厳然として存在している。リモートワークインフラの完成により、この格差はグローバルな労働のアービトラージを加速させており、優秀な人材の国際的流動（頭脳流出）は今後さらに激化することが確実である。</span></span>

<!-- block_index=128 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">**日本市場における「双峰性（二重構造）」の限界と変革の兆し**</span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">: 日本市場の平均年収は約1,080万円に到達し、2031年にはさらに17%の上昇が予測されている。しかしその実態は、伝統的な給与体系に縛られ500万〜800万円台を提示する旧来型企業と、1,500万円超を提示する外資系・メガベンチャー、あるいは月
```
