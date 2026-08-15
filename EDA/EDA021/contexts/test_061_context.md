# test_061

## Question
京橋信用ソリューションズの分析コードにおいて、今回の学習で勾配ブースティング法のモデルに実際に渡される n_estimators、learning_rate、random_state はそれぞれいくつですか。設定ファイルに明示されていない値がある場合も、実行時にコード上で適用される値を含めて答えてください。

## Route
code_reading

## Generated Answer
「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。

## Retrieved Records

### Rank 1
- score: 115.013484
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

### Rank 2
- score: 109.733645
- record_id: `pptx_slide_d6564141622d2e46`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

```text
Slide 2
ビジネス成果
予測スコア上位10%のPrecision = 0.589
上位層に契約が濃縮されることを確認
営業効率化の初期導出に成功
説明可能性情報を整備し、実運用性の議論基礎を提供
分析成果
AUC(ROC) = 0.925
Accuracy = 0.900 / F1(macro) = 0.722
Brier score = 0.066
gradient_boosting を中心に検証
duration含有/非含有モデルを分離評価
運用提言（要点）
事前判断にはduration除外モデルを使用
上位スコア群でA/Bテストを短期実施
業務効果を定量検証すること
監査証跡・アクセス制御を本番化前に実装
1. エグゼクティブサマリー
甲：京橋信用ソリューションズ株式会社 / 乙：株式会社データアステル｜契約期間 2025-10-01 ～ 6週間｜固定価格契約
```

### Rank 3
- score: 106.229372
- record_id: `metadata_1821b471f0dc23dd`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

```text
ファイル名: 京橋信用ソリューションズ株式会社_最終報告.pptx
元パス: share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx
ファイル種別: pptx
```

### Rank 4
- score: 105.13081
- record_id: `generic_chunk_e9378ba44ef02f3f`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/05.会議/報告資料/報告資料_2025-10-01.docx`

```text
index=75 type=paragraph style=Compact -->
重要エスカレーション項目

<!-- block_index=76 type=paragraph style=Compact -->
M01 の議事録未作成と、期待される決定事項（業務目的・カラム定義・検収窓口）が未確定のまま進行すると、以降フェーズでの仕様変更・手戻りリスクが発生します。早急に議事録化・承認をお願いします。

<!-- block_index=77 type=paragraph style=Compact -->
着手金の支払フォローは期日が近いため、経理処理・承認フローの確認を要請します（担当: クライアント 高橋 課長）。

<!-- block_index=78 type=paragraph style=Compact -->
管理上の推奨事項（短期）

<!-- block_index=79 type=paragraph style=Compact -->
M01 の決定事項を「単一正本（project facts / このプロジェクト概要）」として版管理し、以降の全成果物はこの正本に整合させる運用を厳守してください（既にプロジェクト定義に明記）。

<!-- block_index=80 type=paragraph style=Compact -->
EDA および前処理方針（特に duration の扱い）について、中間報告（M02）での明確化を必須トピックとすることを推奨します。

<!-- block_index=81 type=paragraph style=Normal -->

<!-- block_index=82 type=paragraph style=First Paragraph -->
付記（トレース情報） - 現時点で参照可能な出力: artifacts/analysis_outputs/metrics.json、artifacts/analysis_outputs/run_summary.json（Report trace に登録済）
- 次回会議予定: 週次進捗 2025-10-06、MS2（EDA完了） 2025-10-14、M02 中間報告 2025-10-29

<!-- block_index=83 type=paragraph style=Body Text -->
（注）報告中の数値は Report facts JSON の metrics / project_facts に基づき記載しています。プロジェクト定義にのみ記載されているが Report facts JSON に未記載の数値は「assumption」として明示し、当報告ではそのように扱っています。
```

### Rank 5
- score: 104.8844
- record_id: `pptx_slide_b04b398906f85f8c`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/06.報告書/京橋信用ソリューションズ株式会社_最終報告.pptx`

```text
Slide 6
4. 主要分析結果 ─ モデル性能
データ: 27,128件 / 18カラム　｜　学習: 21,702件　｜　テスト: 5,426件　｜　モデル: gradient_boosting
AUC (ROC)
0.925
識別能力
Accuracy
0.900
正確度
F1 (macro)
0.722
総合精度
Brier Score
0.066
確率較正
Precision@Top10%
0.589
上位抽出精度
解釈
高いAUCと上位抽出精度（Precision@Top10% ≈ 0.589）は、スコア上位の顧客群に契約が濃縮されていることを示す
接触優先度付けの初期運用に有用である
目的変数は不均衡（全体契約率 11.7%）であり、Accuracy単独の評価は誤解を招く
業務評価ではAUC/上位抽出指標を重視すべきである
Brier scoreの値は確率閾値設定時の較正参考情報として有用
```

### Rank 6
- score: 104.329383
- record_id: `pdf_page_0ee5b12f77502356`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-26.pdf`

```text
▪ rmse: 708753.9903292693
▪ r2: 0.46831846615046635
▪ selected_feature_count: 13, excluded_feature_count: 4
o T04（T04, log_target_hist_gradient_boosting）
▪ model_type: hist_gradient_boosting（ターゲットに log1p を適用）
▪ rmse: 738055.754082396
▪ r2: 0.4234474680039092
▪ selected_feature_count: 13, excluded_feature_count: 4
o T05（T05, configured_default）
▪ model_type: random_forest
▪ rmse: 706251.4871887658
▪ r2: 0.47206641189165033
▪ selected_feature_count: 13, excluded_feature_count: 4
• 現時点の「最良（可視）試行」について
o best_visible_trial: T05（random_forest）
▪ rmse: 706251.4871887658、r2: 0.47206641189165033（Report
facts.best_visible_trial と analysis.metrics に整合）
▪ analysis.metrics に記載の MAE: 428820.1407276015（これも中間結果の指標とし
て参照可能）
o コメント（中間観察）:
▪ 線形ベースライン（T01/T02）は本データ特性では性能が劣後しており（rmse が非常に大きく、
r2 が負の値）、非線形手法（T03/T05）の方が大幅に改善している。T03/T05 の rmse は
約 7.08e5〜7.06e5、r2 は約 0.47（T05）前後で安定している点が確認できる。
▪ T04（ターゲットに log1p を適用した hist gradient boosting）はやや性能低下が見られ、
ターゲット変換の効果は条件依存であることが示唆される。
o 注意: これらは中間チェックポイントで可視化されたトライアル（trial_index 1〜5）の結果であり、最終
モデルや最終スコアを示すものではありません（Report facts.analysis.checkpoint_stage =
“interim” の方針に準拠）。
4. データ品質と実装状況
• 実行構成（参照）
o 分析仕様の date_column 設定: “TAX CLASS AT TIME OF SALE”（configs / analysis
run_summary に一致）
o split_strategy（実行設定）: time_ordered（project config に設定）
o use_date_features: true（設定）
• データ品質（現時点で確定している論点）
o 面積系、築年、ZIP コード等に品質懸念がある旨はキックオフで指摘済（M01 会議録）。ただし、
Report facts JSON に欠損の正確な集計値は含まれていないため、件数や割合は以下のとおり扱
います。
▪ LAND SQUARE FEET / GROSS SQUARE FEET の欠損・ゼロ値に関する具体件数: 前段
資料に数値があるが、本チェックポイントの Report facts JSON に明示されていないため
「assumption（前提資料に基づく）」として扱います。正確な欠損集計は A05 の完了で確定
予定（責任者: 岡田／渡辺、期限: 2025-08-15 のオリジナル要求）。
o date_column の扱い: 設定は “TAX CLASS AT TIME OF SALE” だが、そのカラムが時系列と
して妥当かは検証中（M01 のアクション A03）。解析パイプラインは date_column を用いた
time_ordered split を試行しているが、パース可能性に依存するため中間判定での扱いに注意が必
要。
• 実装状況
```

### Rank 7
- score: 101.259389
- record_id: `generic_chunk_0ec626ab1150778a`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
yle=Normal -->

<!-- block_index=27 type=paragraph style=Heading 2 -->
## 3. キックオフ時点の確認事項

<!-- block_index=28 type=paragraph style=First Paragraph -->
キックオフ時点では、分析結果ではなく前提確認とデータ受領状況のみを共有する。

<!-- block_index=29 type=paragraph style=Compact -->
データ概要

<!-- block_index=30 type=paragraph style=Compact -->
レコード数: 17,500

<!-- block_index=31 type=paragraph style=Compact -->
カラム数: 10

<!-- block_index=32 type=paragraph style=Compact -->
欠損: 全項目 <span data-font-color="#FF0000" style="color:#FF0000">0.0</span>（初期前処理における欠損補完は不要）

<!-- block_index=33 type=paragraph style=Compact -->
分析着手前の整理事項

<!-- block_index=34 type=paragraph style=Compact -->
学習行数: 14,000、検証行数: 3,500

<!-- block_index=35 type=paragraph style=Compact -->
解析上の示唆（初期）

<!-- block_index=36 type=paragraph style=Compact -->
欠損がないため、前処理コストは低い。一方で、順序カテゴリ（grade, employment_length, term）や金利（interest_rate）の業務意味（審査時点で利用可能か）が解析と運用で異なる可能性があるため、変数の扱いを二通り（運用可能変数のみ／すべての変数）で評価する必要あり。

<!-- block_index=37 type=paragraph style=Compact -->
時系列情報が欠落しているため、ドリフト検知やビンテージ分析は本データ単体で実施不可。

<!-- block_index=38 type=paragraph style=Compact -->
留意点

<!-- block_index=39 type=paragraph style=Compact -->
「基準不良率（全体の loan_status=1 比率）」は本 Report facts JSON に明示されていないため、現時点では確定値を記載していません（該当値を使用する場合はキックオフでの業務定義を待つか、EDA 出力から正式に取得して記録してください）。この種の値を用いたリフト/増分評価は、基準不良率が確定してから算出します（assumption）。

<!-- block_index=40 type=paragraph style=Normal -->

<!-- block_index=41 type=paragraph style=Heading 2 -->
## 4. データ品質と実装状況

<!-- block_index=42 type=paragraph style=Compact -->
データ品質

<!-- block_index=43 type=paragraph style=Compact -->
欠損: 全カラムで 0%（eda_summary.mis
```

### Rank 8
- score: 101.108684
- record_id: `generic_chunk_83a76662b12c1d9f`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
1F">: 生成AIが自動的にコードを記述し、基礎的なモデルを構築できる時代において、企業がデータサイエンティストに真に求めているのは「技術的知識」だけではない。「AI技術を実際の企業の事業課題（ドメイン）と結び付け、具体的なビジネス価値（利益）を創出できる人材」である。</span></span>

<!-- block_index=121 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">この「AI技術とビジネスの橋渡し」ができる高度なアーキテクト層に対しては、2025年以降グローバルで給与がさらに高騰すると予測されている。ボストン・インスティテュート・オブ・アナリティクスの報告によれば、AI、機械学習、NLP、およびクラウドスキルの需要は圧倒的なものとなり、シニアレベルの役割では20万ドル（約3,000万円）を優に超える報酬が支払われるベンチマークが形成されつつある。</span></span>

<!-- block_index=122 type=paragraph style=Heading 3 -->
### <span data-font-name="Arial Unicode MS" data-font-size-pt="13.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**7.3. 職業に対する社会的認知の国際比較**</span></span>

<!-- block_index=123 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">このように実務レベルでの重要性が増す一方で、職業に対する社会的認知度には依然として地域差が存在する。同データサイエンティスト協会の調査によれば、米国、ドイツ、インド、中国の海外4カ国では、データサイエンティストに対して「収入が多い」「将来性がある」「安定性がある」というポジティブなイメージが非常に強く定着している。</span></span>

<!-- block_index=124 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">対照的に、日本国内における認知率は2022年の43%から2025年には49%へ着実に上昇しているものの、「収入が多い」といったイメージは海外ほど高く形成されていない。日本国内において専門職としての地位確立は依然として「道半ば」であると分析されている。この社会的認知の差は、経営層や人事部が専門家に対して支払う報酬水準に対する心理的なキャップ（上限）として無意識に機能しており、前述したグローバルとの報酬格差を温存する一因となっている可能性が示唆される。</span></span>

<!-- block_index=125 type=paragraph style=Heading 2 -->
## <span data-font-name="Arial Unicode MS"
```
