# EDA009: 質問解析つき検索の検証

## 目的・背景

EDA008では、LLM API呼び出し自体は成功した一方で、質問が指定する `提案書` ではなく `報告資料` の根拠が上位に入り、回答がずれました。EDA009ではLLMを呼ばず、検索前に質問解析を行い、対象文書名やフォルダ名を使って根拠候補を優先できるかをvalidで検証します。

## 実行設定

- top_k: 10
- 入力チャンク: `EDA/EDA002/texts/text_chunks.jsonl`, `EDA/EDA004/texts/text_chunks.jsonl`
- 評価質問: `data/raw/share/share/質問回答/questions_valid.csv`

## 全体比較

| metric | baseline | guided | delta |
| --- | --- | --- | --- |
| top5_hit_rate | 0.3333 | 0.3333 | 0.0 |
| top10_hit_rate | 0.3667 | 0.3667 | 0.0 |

凡例: `metric` は評価指標、`baseline` は通常BM25、`guided` は質問解析つきBM25、`delta` は guided から baseline を引いた値を表します。

## 文書ヒント有無別

| has_document_hint | question_count | baseline_top5 | guided_top5 | improved | worsened |
| --- | --- | --- | --- | --- | --- |
| False | 22 | 0.2727 | 0.2727 | 0 | 0 |
| True | 8 | 0.5 | 0.5 | 0 | 0 |

凡例: `has_document_hint` は質問に提案書や契約書などの文書ヒントが含まれるか、`question_count` は質問数、`baseline_top5` と `guided_top5` はTop5正解語句ヒット率、`improved` と `worsened` はTop5判定が改善または悪化した件数を表します。

## valid_002の確認

| index | question | answer | document_hints | baseline_hit_top5 | guided_hit_top5 | baseline_top1_path | guided_top1_path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 恒一会 かえで総合病院の提案書内で、重視するとされている評価指標を答えてください。 | Recall | 提案書 | True | True | プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx | プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx |

凡例: `baseline_top1_path` は通常BM25の1位根拠、`guided_top1_path` は質問解析つきBM25の1位根拠を表します。

## Top1が変化したケース

| index | question | answer | document_hints | baseline_hit_top5 | guided_hit_top5 | baseline_top1_path | guided_top1_path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | KSSのfigure_06.pngにおいて、dayによる件数推移とあわせて表示されているTG平均が最も低い日は何日ですか。 | 20日 |  | False | False | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx | プロジェクト/株式会社青嶺不動産アセットマネジメント/05.会議/報告資料/報告資料_2025-08-06.pdf |
| 2 | 恒一会 かえで総合病院の提案書内で、重視するとされている評価指標を答えてください。 | Recall | 提案書 | True | True | プロジェクト/医療法人社団 恒一会 かえで総合病院/05.会議/報告資料/報告資料_2025-09-02.docx | プロジェクト/医療法人社団 恒一会 かえで総合病院/00.提案/提案書.pptx |
| 10 | 蒼樹会 みなみ野女性医療センターの最終報告書にて、影響度が最も高いとされている残余リスクを抜き出してください。 | 0値の疑似欠損 | 報告書 | False | False | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/00.提案/糖尿病統計情報.docx | プロジェクト/医療法人社団 蒼樹会 みなみ野女性医療センター/06.報告書/医療法人社団 蒼樹会 みなみ野女性医療センター_最終報告.pdf |
| 11 | 東都人材プラットフォームのtrain.xlsxにおいて、trainシートでフィルターで抽出されている条件を教えてください。 | Gender=Male、Country=India、target=2 |  | False | False | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx | プロジェクト/株式会社東都人材プラットフォーム/03.データ/train.xlsx |
| 27 | 蒼泉会 ひがし丘総合病院案件において、中間報告資料に記載されたMacro F1スコアの詳細値と、最終分析出力metrics.jsonに記録されているMacro F1スコアの詳細値を用いて、改善幅を小数第6位まで答えてください。 | 0.010301 | 報告資料 \| 報告書 | False | False | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_outputs/metrics.json | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/06.報告書/医療法人社団 蒼泉会 ひがし丘総合病院_最終報告.pdf |
| 28 | 蒼泉会の分析コードにおいて、CATは dtype とユニーク数の条件でどのように判定していますか。 | object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。 |  | False | False | プロジェクト/株式会社東都人材プラットフォーム/00.提案/データサイエンティスト調査.docx | プロジェクト/医療法人社団 蒼泉会 ひがし丘総合病院/04.分析/analysis_project/notebooks/01_eda.ipynb |

凡例: `baseline_top1_path` と `guided_top1_path` は、質問解析によって1位根拠がどう変わったかを表します。

## 考察

- 質問内の文書名を使うことで、LLMへ渡す前の根拠選択を制御できるかを確認する実験です。
- TopK内に正解語句があるかは簡易評価であり、表計算、書式、画像、差分が必要な質問では実際の回答可能性とずれる場合があります。
- guidedで悪化するケースがある場合は、文書ヒントの加点を弱めるか、対象プロジェクト一致をより強くする必要があります。