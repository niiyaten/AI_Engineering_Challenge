# test_058

## Question
社内管理フォルダにあるFMにおいて、井上さんの向かいに座っている方のEXTを教えてください。

## Route
fallback_bm25_llm

## Generated Answer
| 社内管理フォルダ | IM | Internal Management |

## Retrieved Records

### Rank 1
- score: 80.65314
- record_id: `generic_chunk_972aa2b1ec8bdb17`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/社内用語集.docx`

```text
注記 | POP | callout |
| レイヤー | LAYER | 前面/背面・重なり |

<!-- block_index=15 type=paragraph style=Normal -->
**7. 社内管理・運用**

<!-- block_index=16 type=table rows=48 cols=3 -->
| 正式名称 | 社内用語 | 補足 |
| --- | --- | --- |
| 社内管理フォルダ | IM | Internal Management |
| パスワード導出規則 | PW-RULE | Password Rule |
| 決裁基準 | APR-RULE | Approval Rule |
| 座席表 | FM | Floor Map |
| 内線番号 | EXT | Extension |
| 社内用語集 | TERM-BOOK | 本資料 |
| 承認者 | APPROVER | 決裁者 |
| 鍵付き文書 | LOCKDOC | password protected document |
| 開錠キー | UNLOCK-KEY | 復号キー |
| パスワードヒント | PW-HINT | ヒント文 |
| 席ID | DESK-ID | 座席識別子 |
| 島/エリア | POD | seating island |
| 共有ドライブ起点 | SHARE-ROOT | share root |
| アクセス制御規則 | CTRL-RULE | control rule |
| 閲覧権限レベル | VIEW-LVL | viewing level |
| マスキング規則 | MASK-RULE | masking rule |
| 匿名化済み | ANON | 個人特定不可状態 |
| 仮名化 | PSEUDO | 一部識別子変換 |
| 秘匿領域 | SEC-VAULT | 社内限定保護領域 |
| 閲覧制限レベル1/2/3 | VIEW-L1/L2/L3 | セキュリティレベル |
| 持ち出し禁止 | NO-CARRY | 共有ドライブ外禁止 |
| 原本保管 | MASTER-HOLD | 元データ保全 |
| 二次配布禁止 | NO-REDIST | 外部再共有不可 |
| 削除予定日 | PURGE-DATE | 保存期限管理 |
| 参照専用 | READ-ONLY | 編集不可 |
| 監査ログ対象 | AUD-LOG | 追跡対象ファイル |
| ドラフト版 | DFT | 作成途中 |
| レビュー版 | RV | 社内レビュー用 |
| 社内確認版 | IN-CHECK | 対外提出前 |
| 顧客提出版 | CL-SUBMIT | 提出済み版 |
| 旧版凍結 | FROZEN | 変更不可版 |
| 差分確認中 | DELTA-CHK | 比較作業中 |
| 再出力版 | RERENDER | 再生成済み版 |
| 内部補足あり | INT-NOTE | ノートや備考付 |
| 注記残し | TAG-LEFT | 確認ポイント残存 |
| 図差替済 | FIG-SWAP | 図版のみ修正済み |
| 座席島 | ISLAND | 座席のまとまり |
| 紫色の席 | SEAT-V | 色ベース俗称 |
| 黄色の席 | SEAT-Y | 色ベース俗称 |
| 資料置き場 | DOC-BOX | ファイル群全体 |
| マスター管理表 | LEDGER | 台帳類の俗称 |
| 元資料 | PARENT-DOC | ソース資料 |
| 派生資料 | CHILD-DOC | 加工後資料 |
| 他案件流用 | SIDE-COPY | 使い回し |
| 案件フォル
```

### Rank 2
- score: 64.323912
- record_id: `generic_chunk_96810ddad8b3cce0`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/社内用語集.docx`

```text
# Word Markdown: 社内用語集.docx

## Source
- raw_path: `share/共有ドライブ/社内管理/社内用語集.docx`
- source_sha1: `f36ea5cc08caab893e5c457a167079c8008b0169`
- paragraph_count: 12
- table_count: 9
- image_count: 0

## Body

<!-- block_index=1 type=paragraph style=Normal -->
**データアステル社内用語集**

<!-- block_index=2 type=paragraph style=Normal -->
本資料は、社内共有フォルダ上で利用する略語・社内用語を整理したものである。

<!-- block_index=3 type=paragraph style=Normal -->
**1. 文書・成果物**

<!-- block_index=4 type=table rows=41 cols=3 -->
| 正式名称 | 社内用語 | 補足 |
| --- | --- | --- |
| 提案書 | PP | Proposal Pack / Proposal Presentation |
| 提案補足資料 | PP-ADD | 提案書の補足・別冊 |
| 契約書 | CT | Contract |
| 契約別紙 | CT-APP | 契約付属文書 |
| スケジュール | PL | Plan |
| 計画資料 | PLAN | スケジュール以外の計画資料も含めるとき |
| 会議録 | MM | Meeting Minutes |
| 報告資料 | RP | Report Pack |
| 会議投影版 | RP-DECK | 会議で投影する版 |
| 最終報告書 | FR | Final Report |
| 調査資料 | RS | Research Sheet |
| 座席表 | FM | Floor Map |
| 社内管理資料 | IM | Internal Management |
| 配布版 | DIST | 配布用に整えた版 |
| 説明台本 | SCRIPT | 発表・説明用メモ |
| レビュー記録 | RVLOG | レビューコメント記録 |
| 参考別冊 | ANNEX | 参考資料束 |
| 社内回覧版 | CIRC | 社内だけで回す版 |
| train.csv | TR | Train Raw |
| train.xlsx | TX | Train Workbook |
| leaderboard.csv | LB | Leaderboard |
| metrics.json | MT | Metrics |
| project_config.json | CFG | Config |
| 01_eda.ipynb | EDA1 | 初回EDAノート |
| features.py | FE | Feature Engineering |
| preprocess.py | PPROC | Preprocess |
| modeling.py | MDL | Modeling |
| evaluate.py | EV | Evaluation |
| infer.py | INF | Inference |
| reports/figures | FIG | 図表出力 |
| validation出力 | VAL | validation用出力 |
| 実験ログ | EXPLOG | trialログ・実験履歴 |
| 選択後データ | SEL | 特徴量選択後データ |
|
```

### Rank 3
- score: 62.242536
- record_id: `generic_chunk_7cde7193942a486e`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-16.docx`

```text
style=Compact -->
実行アーティファクト（再現元）: artifacts/analysis_outputs/run_summary.json, artifacts/analysis_outputs/metrics.json, artifacts/analysis_outputs/experiments/leaderboard.json（Report facts.trace.source_files に記載）

<!-- block_index=94 type=paragraph style=Compact -->
会議議事録: artifacts/meeting_minutes/会議録_2025-09-02.md（M01）および本中間レビュー議事録（M02）をプロジェクトの唯一基準として管理してください。

<!-- block_index=95 type=paragraph style=Compact -->
要注意（PM 向け）

<!-- block_index=96 type=paragraph style=Compact -->
open actions = 7（prior_state.open_action_count = 7）。PM はこれらクローズを優先し、中間レビューで決定された前処理方針と継続モデル候補（expected_decisions）に基づくリソース配分を確定してください。

<!-- block_index=97 type=paragraph style=Compact -->
2025-09-19 の変更管理チェックポイントは契約上の追加対応要否を判定する重要日です。追加要求が出た場合は change_request_policy（time_and_materials）に従って見積り・承認の流れを確保してください。

<!-- block_index=98 type=paragraph style=First Paragraph -->
以上

<!-- block_index=99 type=paragraph style=Body Text -->
（作成: データアステル / 分析チーム — 報告は Report facts JSON（checkpoint=M02, stage=interim）に基づく内容です）
```

### Rank 4
- score: 61.756375
- record_id: `generic_chunk_e11f34ce88ab0de5`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`

```text
# Word Markdown: データアステル社内規定_パスワード導出規則.docx

## Source
- raw_path: `share/共有ドライブ/社内管理/データアステル社内規定_パスワード導出規則.docx`
- source_sha1: `3c398b562eabcd2eadbf6482c616b72a814cf92d`
- paragraph_count: 13
- table_count: 0
- image_count: 0

## Body

<!-- block_index=1 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**データアステル社内規定_パスワード導出規則**</span>

<!-- block_index=2 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**1. 目的**</span>

<!-- block_index=3 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">案件フォルダ内の一部保護ファイルについて、社内規定に基づく共通ルールでパスワードを導出できるようにする。</span>

<!-- block_index=4 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**2. パスワード導出の基本形式**</span>

<!-- block_index=5 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">パスワードは次の形式で構成する。</span>

<!-- block_index=6 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">DA-[案件略号]-[開始年月日8桁]-[拡張子コード]</span>

<!-- block_index=7 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">例:</span>

<!-- block_index=8 type=paragraph style=Normal -->
DA-AOMINE-20250806-xlsx

<!-- block_index=9 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">**3. 案件略号一覧**</span>

<!-- block_index=10 type=paragraph style=Normal -->
<span data-font-name="BIZ UDPゴシック" data-font-size-pt="">社内用語集にて規定されている主略称を使用する</span>

<!-- block_index=11 type=paragraph style=Normal -->
<sp
```

### Rank 5
- score: 54.796339
- record_id: `generic_chunk_39dd71275f3729ed`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/青葉与信マネジメント株式会社/05.会議/報告資料/報告資料_2025-04-09.docx`

```text
い（監査／解釈基準の根幹）。

<!-- block_index=80 type=paragraph style=Compact -->
interest_rate / grade を「審査時点で利用可」とするか否かを決定してください（運用実装可否に直結）。

<!-- block_index=81 type=paragraph style=Compact -->
追加要望が発生した場合は、変更管理ポリシー（別紙見積）に従う方針で運用することを確認ください。

<!-- block_index=82 type=paragraph style=Compact -->
商務情報（Report facts の commercial／project_facts に基づく）

<!-- block_index=83 type=paragraph style=Compact -->
契約形態: 固定価格（fixed_price）

<!-- block_index=84 type=paragraph style=Compact -->
契約金額（税抜）: 4,200,000 円

<!-- block_index=85 type=paragraph style=Compact -->
税率: 10%（税額 420,000 円）

<!-- block_index=86 type=paragraph style=Compact -->
契約金額（税込）: <mark data-font-color="#FF0000" style="color:#FF0000" data-highlight="YELLOW (7)">4,620,000</mark> 円

<!-- block_index=87 type=paragraph style=Compact -->
支払スケジュール: 2 回分割（着手金 50%／検収金 50%） — 各金額は payment_schedule に記載の通り

<!-- block_index=88 type=paragraph style=Compact -->
支払管理は PM（伊藤 翔太）で統括

<!-- block_index=89 type=paragraph style=Compact -->
クリティカルパスと次マイルストーン

<!-- block_index=90 type=paragraph style=Compact -->
クリティカルな前提: loan_status の業務定義確定および interest_rate/grade の利用可否確認（これらが確定しないと中間レビュー以降のモデル解釈が不確定になります）。

<!-- block_index=91 type=paragraph style=Compact -->
次回中間レビュー（スケジュール上の中間レビューフェーズ）に向け、上記の A/B タスクを優先して完了させてください。

<!-- block_index=92 type=paragraph style=Compact -->
現状の運用上の判断メモ

<!-- block_index=93 type=paragraph style=Compact -->
キックオフ時点では、分析結果ではなく前提整理の完了を優先してください。

<!-- block_index=94 type=paragraph style=Compact -->
監査証跡の観点では、議事録（キックオフ）を含めた前提定義の早期登録が必須です。

<!-- block_index=95 type=paragraph style=Normal -->

<!-- block_index=96 type=paragraph s
```

### Rank 6
- score: 54.026381
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

### Rank 7
- score: 50.953468
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

### Rank 8
- score: 49.646555
- record_id: `generic_chunk_162608be88085038`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx`

```text
学際的な分野である。そのため、労働市場において情報非対称性を解消するための「シグナリング（能力証明）」として、形式的な教育背景や資格認定が強力なプレミアム効果を持つ。</span></span>

<!-- block_index=98 type=paragraph style=Heading 3 -->
### <span data-font-name="Arial Unicode MS" data-font-size-pt="13.0"><span data-font-color="#1F1F1F" style="color:#1F1F1F">**6.1. 高等教育（修士号・博士号）による生涯賃金の引き上げ**</span></span>

<!-- block_index=99 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">米国における調査データ（Zippia調べ）によると、データサイエンティストの過半数（51%）が学士号（Bachelor's degree）を保有しているが、34%が修士号（Master's </span></span><span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">degree）、13%が博士号（PhD）を保有しており、極めて高学歴な職業集団であることが確認できる。雇用主は、高等教育機関での厳しい学術的トレーニングを、候補者の数学的成熟度、非構造化データに対する問題解決能力、および持続的な学習能力の証明として評価している。</span></span>

<!-- block_index=100 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">この学歴は給与水準と直接的な相関関係を持つ。学士号保有者の平均年収が101,455ドルであるのに対し、修士号保有者の平均年収は109,454ドルであり、学位を一段階上げることで年間約8,000ドルの賃金上昇効果（プレミアム）が得られている。これは、高度な統計モデリングや研究開発志向の強いタスクにおいて、大学院レベルの専門知識が直接的な業務パフォーマンスに直結すると評価されているためである。</span></span>

<!-- block_index=101 type=paragraph style=Normal -->
<span data-font-name="Arial Unicode MS" data-font-size-pt=""><span data-font-color="#1F1F1F" style="color:#1F1F1F">日本市場においても、データサイエンスに関する学術研究の実績や、関連分野での修士号・博士号の保有者は極めて高く評価される傾向にある。ERIのデータでは現状の日本市場の最高学歴分布が学士号100%として扱われているものの、実務的な採用現場、特に実務経験が不足している新卒・若手層においては、学生時代におけるデータサイエンス関連の専門的な研究活動そのものが、就職や転職活動において
```
