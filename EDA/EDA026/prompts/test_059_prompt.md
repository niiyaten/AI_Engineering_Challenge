# test_059 prompt

## system

あなたは社内共有ドライブの資料だけを根拠に回答するRAG回答器です。提示された根拠以外の知識を使わないでください。「わかりません」と答えることは禁止です。根拠が弱い場合でも、提示根拠から最も妥当な短い回答を作ってください。回答は提出用の最終回答だけにしてください。説明、根拠番号、ファイルパス、前置きは不要です。HTMLタグ、Markdown記法、引用符の装飾は回答に含めないでください。計算が必要な場合は、根拠にある数値だけを使って計算し、単位を付けて短く答えてください。

## user

以下の質問に答えてください。

質問: 京ソのPP_final.pptxにおいて、この案件にかかる金額の提示がまとまっているのは何ページですか。

推定route: fallback_bm25_llm

route別の注意: 質問に対して必要な根拠だけを使って短く答える。

根拠:

[根拠 1]
score: 59.323364
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
ているシンガポールは、データサイエンス業界において最大122,923 SGD（シンガポールドル）の獲得可能性を持ち、平均でも104,999 SGDと極めて高い水準を誇っており、アジア圏において突出した引力を放っている。 この圧倒的な格差は、多国籍企業における「労働のアービトラージ（裁定取引）」を強烈に促進している。米国企業は、同等水準の数理能力を持つ人材を求めて、インドのハイデラバードやムンバイ、さらには東欧や日本へ業務をアウトソーシングする、あるいはフルリモートでの直接雇用を拡大する強力な経済的インセンティブを持っている。逆に、非米国のトップタレントにとっては、居住地を維持したまま米国水準の給与（あるいは現地の相場を大きく上回る調整給与）を提示する外資系企業への流出が容易になっており、これにより日本や欧州の国内伝統企業は、優秀な人材の獲得において深刻な競争力不足に陥っているのが現状である。 ## 4. 日本市場における報酬構造の深層：伝統的慣行とテクノロジー需要の衝突 世界第3位の経済規模を誇りながらも、独自の雇用慣行（メンバーシップ型雇用や年功序列）を長らく維持してきた日本市場において、データサイエンティストの報酬構造は極めて特異な進化を遂げている。 ### 4.1. マクロな市場規模と構造的な人材不足 日本のテクノロジー環境は急速に進化しており、ロボティクス、AI、IoTの分野で世界を牽引している。IDCの予測によると、日本のビッグデータおよびアナリティクス市場は2025年までに250億ドル規模に達するとされ

[根拠 2]
score: 53.747175
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
& Companyの調査は、データ駆動型の意思決定を組織的に導入している企業が、新規顧客の獲得において23倍、既存顧客の維持において6倍という圧倒的な効率性を示していることを実証している。また、Deloitteの調査においても、企業の65%がビジネスの成功においてデータ駆動型の意思決定が不可欠な価値を持つと認識しており、IBMの報告では59%の組織がビッグデータ分析の導入による競争優位性の獲得を明確に認めている。 このように、データサイエンティストが創出する投資対効果（ROI）が定量的に証明されていることが、労働市場における同職種の需要を牽引している。米国労働省統計局（Bureau of Labor Statistics: BLS）の予測によれば、2024年から2034年にかけてのデータサイエンティストの雇用成長率は34%と見込まれており、全職業の平均を大きく上回る「極めて速い（Much faster than average）」成長カテゴリに分類されている。今後10年間にわたり、毎年約21,000件の新規求人が創出され、2024年から2034年の間だけで82,500人の雇用増加が予測されている。 本報告では、この極めて流動的かつ成長著しい労働市場において、データサイエンティストの収入がいかなる要因（地理的条件、産業構造、教育水準、技術スキル、および生成AIなどのマクロトレンド）によって決定されているのかを、複数の信頼性の高い統計データに基づいて多角的に分析し、その構造的メカニズムを解き明かす。 ## 2. 米国市場における報酬構造の精緻な分析：グローバルベンチマークとしての米国 世界最大のテクノロジークラスターと資本市場を擁する米国におけるデータサイエンティストの報酬体系は、世界の労働市場における事実上の標準（デファクト・スタンダード）として機能している。米国の報酬構造を分析することは、資本主義経済がいかに高度な知能労働を評価しているかを理解する上で不可欠である。 </span

[根拠 3]
score: 52.941719
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
1F">: 生成AIが自動的にコードを記述し、基礎的なモデルを構築できる時代において、企業がデータサイエンティストに真に求めているのは「技術的知識」だけではない。「AI技術を実際の企業の事業課題（ドメイン）と結び付け、具体的なビジネス価値（利益）を創出できる人材」である。 この「AI技術とビジネスの橋渡し」ができる高度なアーキテクト層に対しては、2025年以降グローバルで給与がさらに高騰すると予測されている。ボストン・インスティテュート・オブ・アナリティクスの報告によれば、AI、機械学習、NLP、およびクラウドスキルの需要は圧倒的なものとなり、シニアレベルの役割では20万ドル（約3,000万円）を優に超える報酬が支払われるベンチマークが形成されつつある。 ### 7.3. 職業に対する社会的認知の国際比較 このように実務レベルでの重要性が増す一方で、職業に対する社会的認知度には依然として地域差が存在する。同データサイエンティスト協会の調査によれば、米国、ドイツ、インド、中国の海外4カ国では、データサイエンティストに対して「収入が多い」「将来性がある」「安定性がある」というポジティブなイメージが非常に強く定着している。 対照的に、日本国内における認知率は2022年の43%から2025年には49%へ着実に上昇しているものの、「収入が多い」といったイメージは海外ほど高く形成されていない。日本国内において専門職としての地位確立は依然として「道半ば」であると分析されている。この社会的認知の差は、経営層や人事部が専門家に対して支払う報酬水準に対する心理的なキャップ（上限）として無意識に機能しており、前述したグローバルとの報酬格差を温存する一因となっている可能性が示唆される。 ## <span data-font-name="Arial Unicode MS"

[根拠 4]
score: 49.307041
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
# Word Markdown: データサイエンティスト調査.docx ## Source - raw_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx - source_sha1: 5840fe0638d88d581a14bd71de0ad712df124754 - paragraph_count: 128 - table_count: 3 - image_count: 1 ## Body ## データサイエンティストの収入水準、労働市場の構造、および技術的変遷に関する包括的調査報告 ## 1. 導入：データ駆動型経済におけるデータサイエンティストの市場価値の根源 現代のグローバル経済において、データサイエンティストという職業は、単なる技術的専門職の枠を超え、企業の競争優位性を決定づける中核的な資本として位置づけられている。この現象の背景には、世界規模での爆発的な情報生成と、それを処理するための計算能力の飛躍的な向上が存在する。2023年の単年において、世界中で生成されたデータ量は約132ゼタバイト（1,320億テラバイト）に達しており、企業はかつてない規模の「データのゴールドラッシュ」の只中にある。 この膨大なデータ資源を経済的価値へと変換するプロセスが、データサイエンティストに対する莫大な報酬の源泉となっている。Fortune Business Insightsの報告によれば、世界のデータサイエンス市場規模は2024年時点で1,331億2,000万米ドルに達している。さらに、McKinsey & Companyの調査は、データ駆動型の意思決定を組織的に導入している企業が、新規顧客の獲得において23倍、既存顧客の維持において6倍という圧倒的な効率性を示していることを実証している。また、Deloitteの調査においても、企業の65%がビジネスの成功においてデータ駆動型の意思決定が不可欠な価値を持つと認

[根拠 5]
score: 44.488512
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
学際的な分野である。そのため、労働市場において情報非対称性を解消するための「シグナリング（能力証明）」として、形式的な教育背景や資格認定が強力なプレミアム効果を持つ。 ### 6.1. 高等教育（修士号・博士号）による生涯賃金の引き上げ 米国における調査データ（Zippia調べ）によると、データサイエンティストの過半数（51%）が学士号（Bachelor's degree）を保有しているが、34%が修士号（Master's degree）、13%が博士号（PhD）を保有しており、極めて高学歴な職業集団であることが確認できる。雇用主は、高等教育機関での厳しい学術的トレーニングを、候補者の数学的成熟度、非構造化データに対する問題解決能力、および持続的な学習能力の証明として評価している。 この学歴は給与水準と直接的な相関関係を持つ。学士号保有者の平均年収が101,455ドルであるのに対し、修士号保有者の平均年収は109,454ドルであり、学位を一段階上げることで年間約8,000ドルの賃金上昇効果（プレミアム）が得られている。これは、高度な統計モデリングや研究開発志向の強いタスクにおいて、大学院レベルの専門知識が直接的な業務パフォーマンスに直結すると評価されているためである。 日本市場においても、データサイエンスに関する学術研究の実績や、関連分野での修士号・博士号の保有者は極めて高く評価される傾向にある。ERIのデータでは現状の日本市場の最高学歴分布が学士号100%として扱われているものの、実務的な採用現場、特に実務経験が不足している新卒・若手層においては、学生時代におけるデータサイエンス関連の専門的な研究活動そのものが、就職や転職活動において

[根拠 6]
score: 43.556584
source_path: share/共有ドライブ/プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx
record_type: generic_chunk
text:
| 4.3 | 0.7 | | 40-49歳 | 10.1 | 1.8 | | 50-59歳 | 17.8 | 6.1 | | 60-69歳 | 25.3 | 12.0 | | 70歳以上 | 26.4 | 16.8 | | 全世代平均 | 18.1 | 9.1 | 年齢層別の統計を詳細に分析すると、男女ともに加齢に伴い有病率が上昇する明快な勾配が認められる。特に男性においては、60歳以降で4人に1人が糖尿病を強く疑われる段階にあり、女性でも70歳以上になると約17%から20%弱が該当する 。男性は女性と比較して、概ね全年齢層で約2倍の発症リスクを有しており、この背景には肥満、高血圧、飲酒、喫煙といった生活習慣因子の関与が示唆されている 。 令和5年（2023年）の「患者調査」の概況では、糖尿病で継続的に治療を受けている総患者数は約552万2,000人と推計されている 。前回調査（令和2年）の579万1,000人と比較すると、約26万9,000人の減少が認められるが、これは新型コロナウイルス感染症の影響による受診控えや、統計的手法の変動、あるいは死亡数の増加など複数の要因を慎重に吟味する必要がある 。疾患別の内訳では、2型糖尿病が363万9,000人と圧倒的多数を占め、1型糖尿病は12万2,000人となっている 。 生活習慣の指標としての肥満度（BMI 25以上）の推移も、糖尿病統計と密接に連動している。男性の肥満者割合は31.5%（2023年）であり、特に40代（39.7%）や50代（39.2%）の中年層で極めて高い水準にある 。一方、女性においては「やせ（BMI 18.5未満）」の割合が12.0%と高く、特に20代女性の20.2%が「やせ」に該当するという統計は、将来的な糖尿病リスクの増大という観点から、新たな公衆衛生上の懸念材料となっている 。 都道府県別格差：死亡率ワースト地域とベスト地域の要因分析 日本国内の糖尿病統計において最も顕著な特徴は、地理的な「健康格差」である。厚生労働省の「人口動態統計」に基づくと、糖尿病による死亡率（人口10万人対）には都道府県間で明確な有意差が存在する。全国平均の死亡率が10.6%であるのに対し、特定の地域で継続的に高い死亡率が記録されている 。 以下の表は、糖尿病による死亡率の都道府県別ランキング（ワーストおよびベスト）をまとめたものである。 | 順位 | 死亡率が高い都道府県（ワースト） | 死亡率（%） | 死亡率が低い都道府県（ベスト） | 死亡率（%） | | --- | --- | --- | --- | --- | | 1位 | 青森県 | 18.2 | 神奈川県 | 7.2 | | 2位 | 秋田県 | 16.3 | 愛知県 | 7.9 | | 3位 | 香川県 | 16.1 | 東京都 | 8.8 | | 4位 | 鹿児島県 | 15.0 | 滋賀県

[根拠 7]
score: 43.406222
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
> 日本のテクノロジー環境は急速に進化しており、ロボティクス、AI、IoTの分野で世界を牽引している。IDCの予測によると、日本のビッグデータおよびアナリティクス市場は2025年までに250億ドル規模に達するとされている。この急速な市場拡大に対し、人材供給は致命的に不足している。経済産業省（METI）の報告によれば、日本は2030年までに約50,000人のデータサイエンス専門人材の不足に直面すると予測されており、この極端な需給の不均衡が、日本国内における同職種の賃金上昇圧力を形成している。東京、大阪、福岡などのテクノロジーハブを中心に、金融、ヘルスケア、製造業などのセクターにおいて、データ駆動型の意思決定を推進するための高度な分析能力に対する需要が急増している。 ### 4.2. 日本における平均給与水準と階層化された給与レンジ 日本国内の報酬データを網羅的に収集したERI（Economic Research Institute）の分析によると、日本におけるデータサイエンティストの平均年間給与は約10,813,371円に達している。これを時給に換算すると約5,199円であり、さらに年間平均ボーナスとして515,798円が支給されている。 一般的な給与レンジは7,472,039円から13,192,313円の間に収まっており、経験年数に基づく階層化も明確に現れている。 エントリーレベル : 約840万円

[根拠 8]
score: 43.37208
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
イエンティストの認知・理解および生成AIの業務利用に関する調査」によると、日本国内での生成AIの業務利用（検討中を含む）は2023年の20%から2025年には34%へ急拡大している。就労者の61%が「生成AIによって業務が変わった、あるいは変わりそう」と回答しており、実務へ の不可逆的な浸透が確認された。特に顕著なのが、議事録作成、ドキュメント要約、原稿作成といった自然言語処理（NLP）分野の技術導入である。 この生成AIの普及は、労働市場に二つの相反する心理的・経済的効果をもたらしている。 代替への懸念（仕事の喪失への恐怖） : 米国市場では、「AIが人間の仕事を奪う」という強い懸念を抱く層が、36%から49%へと急激に増加している。これは、定型的なデータクレンジングや基礎的なスクリプトの記述といった、これまで若手アナリストが担ってきた「作業」の価値が急速にコモディティ化（陳腐化）している現実を反映している。ただし、日米ともに生成AIが身近なツールとして普及したことで、AIそのものに対する漠然とした「怖い」「不安」という感情自体は減少傾向にある。 ビジネス価値創出人材へのプレミアムの高騰 : 生成AIが自動的にコードを記述し、基礎的なモデルを構築できる時代において、企業がデータサイエンティストに真に求めているのは「技術的知識」だけではない。「AI技術を実際の企業の事業課題（ドメイン）と結び付け、具体的なビジネス価値（利益）を創出できる人材」である。 <!-- blo

[根拠 9]
score: 42.392646
source_path: data/raw/share/share/共有ドライブ/プロジェクト/京橋信用ソリューションズ株式会社/04.分析/analysis_project/reports/figures/figure_06.png
record_type: image
text:
画像ファイル: figure_06.png OCR: 画像説明: The user wants me to extract information from the provided image and convert it into a specific JSON format for RAG search. 1. Analyze the Image: * Title: "day による件数推移" (Trend of the number of items by day). * X-axis: "日" (Day), ranging from 0 to 30 (roughly). The ticks are at intervals of 5 (0, 5, 10, 15, 20, 25, 30). * Left Y-axis: "件数" (Number of items), ranging from 200 to 1600. * Right Y-axis: "目的変数平均" (Average of the dependent variable), ranging from 0.05 to 0.25. * Data Series: * Blue line with circle markers: Represents "件数" (Number of items). It fluctuates significantly. * Orange line with square markers: Represents "目的変数平均" (Average of the dependent variable). It also fluctuates. 2. Extract Specific Values (Trends): * Blue Line (件数): * Starts low around day 1 (approx 200). * Rises to around 800 on day 2. * Dips to around 650 on day 3. * Rises to over 1100 on day 5. * Peaks around 1150 on day 6. * Generally stays between 1000-1150 until day 10. * Drops sharply to around 300 on day 10. * Recovers to around 900 on day 11. * Peaks again around 1600 on day 20. * Ends around 350-400 on day 31. * Orange Line (目的変数平均): * Starts very high on day 1 (approx 0.25). * Drops sharply to around 0.15 on day 2. * Rises to around 0.18 on day 3. * Drops to around 0.12 on day 5. * Generally trends downwards with some fluctuations. * Lowest point seems to be around day 20 (approx 0.05). * Another low point around day 29 (approx 0.07). * Ends around 0.08 on day 31. 3. Address the Specific Question (Implicit in "RAG search" context, though the prompt asks for general text conversion): The prompt asks to convert the image into text for RAG search. It specifically mentions "valid index=1: KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。" (In KSS's figure_06.png, on which day is the TG average displayed along with the trend of the number of items by day the lowest?). * I need to find the lowest point on the orange line ("目的変数平均"). * Looking at the graph, the orange line hits its minimum value at day 20. The value is around 0.05. 4. Formulate the Output: * ocr_text: Transcribe the title, axis labels, and units. * chart_description: Describe the chart type (line chart with two y-axes), the two series (blue circles for count, orange squares for average), and the x-axis range. * extracted_values: List key data points or ranges if necessary, but the prompt asks for "specific values". I will list the axis ranges and the title. * search_summary: Summarize the content for search purposes. Mention the title, axes, and the specific question about the lowest TG average day. * confidence_notes: Note any uncertainties (e.g., exact day 0 vs 1, precise values). Refining the Output Structure: * ocr_text: "day による件数推移", "件数", "目的変数平均", "日", "200", "400", "600", "800", "1000", "1200", "1400", "1600", "0.05", "0.10", "0.15", "0.20", "0.25". * chart_description: A line chart titled "day による件数推移" showing trends over "日" (days). The left y-axis is "件数" (count) from 200 to 1600. The right y-axis is "目的変数平均" (average dependent variable) from 0.05 to 0.25. There are two lines: a blue line with circles representing "件数" and an orange line with squares representing "目的変数平均". * extracted_values: This section should probably capture the key visible numbers. * Title: day による件数推移 * Left Axis Label: 件数 * Right Axis Label: 目的変数平均 * X-axis Label: 日 * Y 読み取り値: [] 検索用要約: The user wants me to extract information from the provided image and convert it into a specific JSON format for RAG search. 1. Analyze the Image: * Title: "day による件数推移" (Trend of the number of items by day). * X-axis: "日" (Day), ranging from 0 to 30 (roughly). The ticks are at intervals of 5 (0, 5, 10, 15, 20, 25, 30). * Left Y-axis: "件数" (Number of items), ranging from 200 to 1600. * Right Y-axis: "目的変数平均" (Average of the dependent variable), ranging from 0.05 to 0.25. * Data Series: * Blue line with circle markers: Represents "件数" (Number of items). It fluctuates significantly. * Orange line with square markers: Represents "目的変数平均" (Average of the dependent variable). It also fluctuates. 2. Extract Specific Values (Trends): * Blue Line (件数): * Starts low around day 1 (approx 200). * Rises to around 800 on day 2. * Dips to around 650 on day 3. * Rises to over 1100 on day 5. * Peaks around 1150 on day 6. * Generally stays between 1000-1150 until day 10. * Drops sharply to around 300 on day 10. * Recovers to around 900 on day 11. * Peaks again around 1600 on day 20. * Ends around 350-400 on day 31. * Orange Line (目的変数平均): * Starts very high on day 1 (approx 0.25). * Drops sharply to around 0.15 on day 2. * Rises to around 0.18 on day 3. * Drops to around 0.12 on day 5. * Generally trends downwards with some fluctuations. * Lowest point seems to be around day 20 (approx 0.05). * Another low point around day 29 (approx 0.07). * Ends around 0.08 on day 31. 3. Address the Specific Question (Implicit in "RAG search" context, though the prompt asks for general text conversion): The prompt asks to convert the image into text for RAG search. It specifically mentions "valid index=1: KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。" (In KSS's figure_06.png, on which day is the TG average displayed along with the trend of the number of items by day the lowest?). * I need to find the lowest point on the orange line ("目的変数平均"). * Looking at the graph, the orange line hits its minimum value at day 20. The value is around 0.05. 4. Formulate the Output: * ocr_text: Transcribe the title, axis labels, and units. * chart_description: Describe the chart type (line chart with two y-axes), the two series (blue circles for count, orange squares for average), and the x-axis range. * extracted_values: List key data points or ranges if necessary, but the prompt asks for "specific values". I will list the axis ranges and the title. * search_summary: Summarize the content for search purposes. Mention the title, axes, and the specific question about the lowest TG average day. * confidence_notes: Note any uncertainties (e.g., exact day 0 vs 1, precise values). Refining the Output Structure: * ocr_text: "day による件数推移", "件数", "目的変数平均", "日", "200", "400", "600", "800", "1000", "1200", "1400", "1600", "0.05", "0.10", "0.15", "0.20", "0.25". * chart_description: A line chart titled "day による件数推移" showing trends over "日" (days). The left y-axis is "件数" (count) from 200 to 1600. The right y-axis is "目的変数平均" (average dependent variable) from 0.05 to 0.25. There are two lines: a blue line with circles representing "件数" and an orange line with squares representing "目的変数平均". * extracted_values: This section should probably capture the key visible numbers. * Title: day による件数推移 * Left Axis Label: 件数 * Right Axis Label: 目的変数平均 * X-axis Label: 日 * Y 注意: JSONとしては解析できなかったため、応答全文を説明として保存した。

[根拠 10]
score: 42.235333
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
に機能しており、前述したグローバルとの報酬格差を温存する一因となっている可能性が示唆される。 ## 8. 結論および労働市場における中長期的な示唆 本調査において、米国および日本を中心とするデータサイエンティストの報酬データ、技術スキルの変遷、およびマクロ経済環境を統合的に分析した結果、以下の本質的な結論が導き出される。 グローバル水準の継続的な高騰と市場格差の固定化 : データサイエンティストは、依然として資本主義経済において最高峰の経済的見返りが約束された職種である。米国市場における基本給の中央値は約12万ドル、総報酬は15万ドル以上に達し、今後10年間で34%という驚異的な雇用成長が予測されている。一方で、日本、欧州、インド等の市場との間には2倍から最大9倍近い報酬格差が厳然として存在している。リモートワークインフラの完成により、この格差はグローバルな労働のアービトラージを加速させており、優秀な人材の国際的流動（頭脳流出）は今後さらに激化することが確実である。 日本市場における「双峰性（二重構造）」の限界と変革の兆し : 日本市場の平均年収は約1,080万円に到達し、2031年にはさらに17%の上昇が予測されている。しかしその実態は、伝統的な給与体系に縛られ500万〜800万円台を提示する旧来型企業と、1,500万円超を提示する外資系・メガベンチャー、あるいは月

[根拠 11]
score: 41.706783
source_path: share/共有ドライブ/プロジェクト/株式会社青嶺不動産アセットマネジメント/00.提案/ニューヨーク不動産市場の最新動向調査.pdf
record_type: pdf_page
text:
新規契約件数 302 348 19 前年同月比 (%) 0.0% -21.4% -26.9% 新規リスティング数 716 734 48 前年同月比 (%) +11.2% +3.1% +2.1% 2 価格帯別では、500 万ドルから 999 万ドルのコンドミニアム契約が 45.8％急増しており、ラ グジュアリー市場の底堅さを証明している 2。一方で、100 万ドル以下のコーポ契約は 20％減 少し、このセグメントでは買い手の交渉力が数年ぶりに高まっている 4。 ブルックリン市場：在庫の微増と価格のレジリエンス ブルックリンは、マンハッタンに代わる居住地としての地位を確固たるものにしているが、 2026 年初頭は厳しい天候の影響を最も受け、全物件種別で契約件数が急減した 2。しかし、在 庫レベルは徐々に回復しており、2026 年 1 月時点で 1,499 件のリスティングがあり、前年比 で 6％増加している 13。 ブルックリン市場の特筆すべき点は、平方フィート単価の継続的な上昇である。平均単価は前 年比 15％増を記録しており、これは高価なコンドミニアムの取引比率が高まったことが寄与し ている 13。また、ウィリアムズバーグやダウンタウン・ブルックリンといった成熟したエリア に加え、ブッシュウィックのような新興エリアでは、在庫が 30.3％も急増し、希望価格が 16.3％下落するという「買い手有利」な状況が発生している 15。 クイーンズ市場：NYC で最も活発な実需層の受け皿 クイーンズは、2026 年の NYC において最もダイナミックな市場の一つとして浮上している。 1 月の新規契約件数は前年比 4.3％増の 289 件となり、他区が減少する中で異彩を放った 17。

[根拠 12]
score: 41.208112
source_path: share/共有ドライブ/プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx
record_type: generic_chunk
text:
1F1F1F">3. グローバル市場における労働のアービトラージと地理的格差 デジタル空間で完結する業務特性を持つデータサイエンス分野において、人材獲得競争は急速に国境を越えつつある。しかし、マクロ経済の力学、各国の物価水準、およびIT産業の成熟度の違いにより、グローバルな報酬水準には依然として圧倒的な地理的格差が存在する。 各国のデータサイエンティストの平均総報酬（追加報酬を含む米ドル換算値）を比較したデータは以下の通りである。 | 国・地域・都市 | 平均総報酬・年収（米ドル換算） | 報告されている給与レンジ（米ドル換算） | | --- | --- | --- | | 米国（USA） | 156,790 | - | | シンガポール | 122,923 (SGD) / 平均104,999 (SGD) | - | | ドイツ | 85,115 | - | | 英国（UK） | 79,978 | - | | オーストラリア | 79,218 / シドニー: 85,032 | 64,591 – 94,251 | | カナダ | 73,607 | - | | 日本 | 54,105 / 東京: 52,081 | 40,579 – 67,632 | | インド（全体平均） | 16,759 | - | | インド（ニューデリー） | 18,662 | - | | インド（ムンバイ） | 14,745 | - | | インド（ハイデラバード） | 14,242 | - | これらのデータセットは、現代のグローバル労働市場における深遠な不均衡を浮き彫りにしている。米国の報酬水準（156,790ドル）は、ヨーロッパの経済大国であるドイツ（85,115ドル）や英国（79,978ドル）の約2倍に達し、日本（54,105ドル）に対しては約3倍、インド（全体平均16,759ドル）に対しては実に約9倍以上の開きがある。また、アジアの金融・テクノロジーハブとして急成長しているシンガポールは、データサイエンス業界において最大122,923 SGD（シンガポールドル）の獲得可能性を持ち、平均でも104,999 SGDと極めて高い水準を誇っており、アジア圏において突出した引力を放っている。 <!-- block_index=27 type=paragraph
