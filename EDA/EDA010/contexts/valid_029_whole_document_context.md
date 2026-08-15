# valid_029 Whole Document Context

## Question
蒼樹会 みなみ野女性医療センターの契約書第8条において、本契約終了後に秘密保持義務が存続する期間は何年間ですか。

## Target Document
- relative_path: プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/01.契約/契約書.docx
- source_eda: EDA004
- extension: .docx
- project_name: 医療法人社団 蒼樹会 みなみ野女性医療センター
- major_folder: 01.契約

## Document Text
```text
# DOCXファイル: 契約書.docx

## paragraph_001
- style: Heading 1
データ分析業務委託契約書

## paragraph_002
- style: First Paragraph
本契約は、2025-04-03付で、以下の当事者間において締結される。

## paragraph_003
- style: Heading 2
1. 当事者

## paragraph_004
- style: First Paragraph
委託者（以下「甲」という。）
医療法人社団 蒼樹会 みなみ野女性医療センター
部署：医療情報・品質改善推進室
主担当者：林 さくら 室長
### run_styles
- bold: 委託者（以下「甲」という。）

## paragraph_005
- style: Body Text
受託者（以下「乙」という。）
株式会社データアステル
部署：データサイエンス部
### run_styles
- bold: 受託者（以下「乙」という。）

## paragraph_006
- style: Body Text
甲および乙は、糖尿病判定データ分析プロジェクトに関し、以下のとおりデータ分析業務委託契約（以下「本契約」という。）を締結する。

## paragraph_007
- style: Heading 2
2. 目的

## paragraph_008
- style: First Paragraph
本契約は、乙が甲に対し、data\train.csv を用いて、目的変数 Outcome（糖尿病であるか：1、でないか：0）の予測可能性を検証し、医療品質改善および患者アウトカム改善に資する分析基盤を整備するためのデータ分析業務を提供することを目的とする。
### run_styles
- bold: Outcome

## paragraph_009
- style: Body Text
本業務の目的は、次の各号のとおりとする。

## paragraph_010
- style: Compact
Outcome を目的変数とする分類分析を実施し、糖尿病判定に寄与する主要因子を特定すること

## paragraph_011
- style: Compact
甲の医療情報・品質改善推進室が再利用可能な、前処理・分析・評価の標準手順を定義すること

## paragraph_012
- style: Compact
今後の業務活用可否を判断できる水準で、分析精度、解釈性および運用上の留意点を整理すること

## paragraph_013
- style: First Paragraph
なお、本業務における分析結果は、診療判断の代替ではなく、診療補助および品質改善の参考情報として取り扱うものとし、医学的因果関係の証明または臨床判断の自動化を目的としない。

## paragraph_014
- style: Heading 2
3. 業務範囲

## paragraph_015
- style: Compact
乙が本契約に基づき実施する業務（以下「本業務」という。）は、以下のとおりとする。

## paragraph_016
- style: Compact
data\train.csv の内容確認、カラム定義確認および品質診断

## paragraph_017
- style: Compact
Outcome を目的変数とした分類分析

## paragraph_018
- style: Compact
0値、外れ値およびスケーリング要否を含む前処理方針の比較検討

## paragraph_019
- style: Compact
ベースラインモデルおよび複数候補モデルの性能比較

## paragraph_020
- style: Compact
評価結果の可視化および解釈

## paragraph_021
- style: Compact
業務活用に向けた示唆整理

## paragraph_022
- style: Compact
最終報告書を含む成果物一式の作成

## paragraph_023
- style: Compact
本業務の対象データおよび前提は、以下のとおりとする。

## paragraph_024
- style: Compact
対象ファイルは data\train.csv とする

## paragraph_025
- style: Compact
対象データは 3,000 行、10 カラム、文字コードは utf-8-sig とする

## paragraph_026
- style: Compact
Outcome を目的変数とし、index は識別用であり予測特徴量には使用しない

## paragraph_027
- style: Compact
CSV上の欠損はないが、BloodPressure、SkinThickness、Insulin、BMI に含まれる0値等については疑似欠損の可能性を検討する

## paragraph_028
- style: Compact
本データは時系列情報を持たないため、時系列分析は本業務の対象外とする

## paragraph_029
- style: Compact
本業務の対象外は、以下のとおりとする。

## paragraph_030
- style: Compact
本番システム実装、API化、運用監視設計

## paragraph_031
- style: Compact
電子カルテ等の他システムとの接続開発

## paragraph_032
- style: Compact
新規データ取得、追加調査、追加ヒアリングの大幅拡張

## paragraph_033
- style: Compact
医学的因果関係の証明

## paragraph_034
- style: Compact
臨床ガイドライン改定提案

## paragraph_035
- style: Compact
本分析結果のみに基づく診療判断ルールの制定

## paragraph_036
- style: Compact
契約締結時点で提示されていない追加データの統合分析

## paragraph_037
- style: Compact
本契約範囲外の追加帳票および追加会議体の無償対応

## paragraph_038
- style: Compact
乙は、本業務を再現性、説明可能性および医療分野への配慮を重視して遂行し、Accuracy単独ではなく、ROC-AUC、Precision、Recall、F1-scoreおよび混同行列を用いて評価を行う。

## paragraph_039
- style: Heading 2
4. 成果物および検収

## paragraph_040
- style: Normal
本業務における成果物は、以下のとおりとする。

## paragraph_041
- style: Compact
プロジェクト概要書

## paragraph_042
- style: Compact
スケジュール

## paragraph_043
- style: Compact
打合せ議事録

## paragraph_044
- style: Compact
中間報告書

## paragraph_045
- style: Compact
最終報告書

## paragraph_046
- style: Compact
分析用データ理解メモ

## paragraph_047
- style: Compact
前処理・評価方針書

## paragraph_048
- style: Compact
モデル比較結果サマリ

## paragraph_049
- style: Compact
業務活用示唆一覧

## paragraph_050
- style: Normal
検収対象は、前項記載の合意済み成果物一式とする。

## paragraph_051
- style: Normal
乙は、契約期間内に最終成果物を提出するものとし、最終成果物提出の基準日を 2025-05-15 とする。

## paragraph_052
- style: Normal
甲は、最終成果物受領後、内容を確認し、合理的な理由に基づき修正を要すると判断した場合には、受領後5営業日以内にその旨を乙へ書面または電子メールにて通知するものとする。

## paragraph_053
- style: Normal
甲が前項の期間内に修正要請または不合格通知を行わない場合、当該成果物は当該期間満了日をもって検収完了したものとみなす。

## paragraph_054
- style: Normal
乙が甲の指摘に基づき契約範囲内で合理的な修正を行った場合、甲は再提出後速やかに確認し、適合を確認した時点で検収を完了するものとする。

## paragraph_055
- style: Heading 2
5. 契約期間

## paragraph_056
- style: Compact
本契約の効力発生日および締結日は、2025-04-03とする。

## paragraph_057
- style: Compact
本契約の契約期間は、2025-04-03から2025-05-15までとする。

## paragraph_058
- style: Compact
前項の期間満了後であっても、第6条、第7条、第8条、第10条、第11条および第12条の規定は、性質上存続すべき範囲で引き続き有効に存続する。

## paragraph_059
- style: Heading 2
6. 報酬および支払条件

## paragraph_060
- style: Compact
本契約の契約形態は固定価格契約とする。
### run_styles
- bold: 固定価格契約

## paragraph_061
- style: Compact
本契約の報酬総額は、税抜 3,600,000円、消費税額 360,000円、税込 3,960,000円 とし、契約時に金額を固定し、工数実績による事後精算は行わない。
### run_styles
- bold: 3,600,000円
- bold: 360,000円
- bold: 3,960,000円
- bold: 契約時に金額を固定し、工数実績による事後精算は行わない。

## paragraph_062
- style: Compact
支払条件は以下のとおりとする。

## paragraph_063
- style: Compact
甲は、前項の金額を、乙の指定する銀行口座へ振込送金の方法により支払うものとし、振込手数料は甲の負担とする。

## paragraph_064
- style: Compact
支払債務の履行日は、甲による振込手続完了日とする。

## paragraph_065
- style: Heading 2
7. 知的財産権

## paragraph_066
- style: Compact
甲が乙に提供したデータ、資料、業務情報その他甲に帰属する既存の知的財産権は、甲に留保される。

## paragraph_067
- style: Compact
乙が本業務の遂行前から保有する分析手法、ノウハウ、テンプレート、汎用プログラム、ライブラリ、フレームワークその他乙の既存の知的財産権は、乙に留保される。

## paragraph_068
- style: Compact
本業務の成果物のうち、甲の提供データに基づき本契約のために新たに作成された報告書、分析結果資料および業務活用示唆一覧に関する著作権その他の知的財産権は、甲が第6条に定める報酬の全額を支払った時点で、甲に移転するものとする。

## paragraph_069
- style: Compact
前項にかかわらず、乙は、自己の既存ノウハウ、汎用的な分析技術、再利用可能な手法およびテンプレートを引き続き利用できるものとする。

## paragraph_070
- style: Compact
乙は、甲の事前の書面承諾なく、甲の機密情報または個人を識別し得る情報を第三者へ開示してはならない。

## paragraph_071
- style: Heading 2
8. 秘密保持

## paragraph_072
- style: Compact
甲および乙は、本契約または本業務に関連して相手方から開示を受けた技術上、営業上、業務上その他一切の非公知情報ならびに医療関連データ（以下「秘密情報」という。）を、厳重に管理し、本契約の履行以外の目的に使用してはならない。

## paragraph_073
- style: Compact
前項にかかわらず、次の各号のいずれかに該当する情報は秘密情報に含まれない。

## paragraph_074
- style: Compact
開示時に公知であった情報

## paragraph_075
- style: Compact
開示後、受領当事者の責によらず公知となった情報

## paragraph_076
- style: Compact
開示前から適法に保有していた情報

## paragraph_077
- style: Compact
正当な権限を有する第三者から適法に取得した情報

## paragraph_078
- style: Compact
相手方の秘密情報によらず独自に開発した情報

## paragraph_079
- style: Compact
乙は、医療関連データについて、要配慮情報に準じた慎重な取扱いを行い、共有範囲、保管先およびアクセス権限を必要最小限に限定するものとする。

## paragraph_080
- style: Compact
甲および乙は、法令または裁判所その他公的機関の命令により秘密情報の開示を求められた場合、法令上許容される範囲で事前に相手方へ通知し、必要最小限の範囲で開示するものとする。

## paragraph_081
- style: Compact
本条の義務は、本契約終了後も3年間存続するものとする。

## paragraph_082
- style: Heading 2
9. 再委託

## paragraph_083
- style: Compact
乙は、本業務の全部を第三者に再委託してはならない。

## paragraph_084
- style: Compact
乙が本業務の一部を再委託する必要がある場合には、事前に甲の書面承諾を得るものとする。

## paragraph_085
- style: Compact
前項の場合であっても、乙は、再委託先に本契約と同等の秘密保持義務その他必要な義務を課し、再委託先の行為について自己の行為と同一の責任を負うものとする。

## paragraph_086
- style: Heading 2
10. 解除

## paragraph_087
- style: Compact
甲または乙は、相手方が本契約に違反し、相当期間を定めて是正を催告したにもかかわらず、当該期間内に是正されない場合、本契約の全部または一部を解除することができる。

## paragraph_088
- style: Compact
甲または乙は、相手方に次の各号のいずれかの事由が生じた場合、何らの催告を要せず直ちに本契約を解除することができる。

## paragraph_089
- style: Compact
支払停止または支払不能となったとき

## paragraph_090
- style: Compact
差押え、仮差押え、仮処分、競売、破産手続開始、民事再生手続開始その他これらに類する申立てがあったとき

## paragraph_091
- style: Compact
解散、清算または事業の全部もしくは重要な一部を第三者に譲渡したとき

## paragraph_092
- style: Compact
反社会的勢力に該当し、または関与していることが判明したとき

## paragraph_093
- style: Compact
本契約を継続し難い重大な背信行為があったとき

## paragraph_094
- style: Compact
前二項による解除は、相手方に対する損害賠償請求を妨げない。

## paragraph_095
- style: Heading 2
11. 責任範囲

## paragraph_096
- style: Compact
乙は、善良なる管理者の注意をもって本業務を遂行するものとする。

## paragraph_097
- style: Compact
乙は、分析結果について再現性および説明可能性に配慮するが、当該結果が特定の医療上、経営上または業務上の成果を保証するものではない。

## paragraph_098
- style: Compact
甲は、分析結果を診療判断の代替として使用せず、医療判断の最終責任は甲に帰属するものとする。

## paragraph_099
- style: Compact
乙は、甲から提供されたデータ、カラム説明その他前提情報の正確性、完全性または最新性について保証しない。

## paragraph_100
- style: Compact
乙の損害賠償責任は、乙の故意または重過失による場合を除き、甲が本契約に基づき乙に支払う報酬総額（税込 3,960,000円）を上限とする。
### run_styles
- bold: 3,960,000円

## paragraph_101
- style: Compact
乙は、逸失利益、間接損害、特別損害または結果損害について責任を負わない。ただし、乙の故意または重過失による場合はこの限りでない。

## paragraph_102
- style: Heading 2
12. 準拠法および裁判管轄

## paragraph_103
- style: Compact
本契約は、日本法に準拠し、日本法に従って解釈される。

## paragraph_104
- style: Compact
本契約に関して当事者間に生じた一切の紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。

## paragraph_105
- style: Heading 2
13. 署名欄

## paragraph_106
- style: First Paragraph
本契約締結の証として、本書を2通作成し、甲乙各1通を保有する。

## paragraph_107
- style: Body Text
契約締結日：2025-04-03
### run_styles
- bold: 契約締結日：2025-04-03

## paragraph_108
- style: Heading 3
甲

## paragraph_109
- style: First Paragraph
医療法人社団 蒼樹会 みなみ野女性医療センター
医療情報・品質改善推進室
主担当者：林 さくら 室長

## paragraph_110
- style: Body Text
署名：________________________

## paragraph_111
- style: Heading 3
乙

## paragraph_112
- style: First Paragraph
株式会社データアステル
データサイエンス部

## paragraph_113
- style: Body Text
署名：________________________

## paragraph_114
- style: Heading 2
14. 特約事項（追加対応の扱い）

## paragraph_115
- style: Compact
本契約範囲外の追加対応は、別紙見積にて金額・納期を事前合意のうえ実施する。
### run_styles
- bold: 本契約範囲外の追加対応は、別紙見積にて金額・納期を事前合意のうえ実施する。

## paragraph_116
- style: Compact
追加対応が発生しない前提で本契約を締結する。
### run_styles
- bold: 追加対応が発生しない前提で本契約を締結する。

## paragraph_117
- style: Compact
前二項に基づき、契約スコープ外の要望が発生した場合、甲乙はその影響範囲を整理し、別紙見積による正式合意後に限り、乙が追加対応を実施する。

## paragraph_118
- style: Compact
追加対応は本契約の固定報酬には含まれず、別途合意した条件に従って取り扱う。

## table_001
row_001: 支払回 | 支払割合 | 支払条件 | 税抜金額 | 消費税額 | 税込金額 | 支払期日
row_002: 1 | 100% | 最終成果物の検収完了後5営業日以内 | 3,600,000円 | 360,000円 | 3,960,000円 | 2025-05-22
```
