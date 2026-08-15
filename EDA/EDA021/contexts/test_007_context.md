# test_007

## Question
青潮モビリティサービスの基礎分析.pptxにおいて、黄色ハイライトされている数値に対応するデータの抽出条件と集計内容を答えてください。

## Route
format_extraction

## Generated Answer
株式会社青潮モビリティサービス 御中

## Retrieved Records

### Rank 1
- score: 129.562095
- record_id: `metadata_7afa09e59afe4fe5`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx`

```text
ファイル名: 基礎分析.pptx
元パス: share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx
ファイル種別: pptx
```

### Rank 2
- score: 127.136766
- record_id: `pptx_slide_1bb0f88ef7fce74f`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx`

```text
Slide 1
Image: data/processed/share/share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.pptx.assets/slide001_shape001.wmf
表1
```

### Rank 3
- score: 125.482957
- record_id: `metadata_3ee1bc7921cbaf6e`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx`

```text
ファイル名: 基礎分析.docx
元パス: share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx
ファイル種別:
```

### Rank 4
- score: 124.608578
- record_id: `generic_chunk_6a12acb74d8cf3e0`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx`

```text
# Word Markdown: 基礎分析.docx

## Source
- raw_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/基礎分析.docx`
- source_sha1: `7f61e786679cec659601f5547c20da7a980adad0`
- paragraph_count: 2
- table_count: 0
- image_count: 0

## Body

<!-- block_index=1 type=paragraph style=Normal -->

<!-- block_index=2 type=paragraph style=Normal -->
```

### Rank 5
- score: 93.438443
- record_id: `metadata_b51ffac32f99893a`
- record_type: `metadata`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`

```text
ファイル名: 株式会社青潮モビリティサービス_最終報告.pdf
元パス: share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf
ファイル種別: pdf
```

### Rank 6
- score: 92.233486
- record_id: `pptx_slide_ff8a11182b2e2804`
- record_type: `pptx_slide`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/00.提案/提案書.pptx`

```text
Slide 1
データ分析プロジェクト提案書
モビリティ需要予測分析
プロジェクト
株式会社青潮モビリティサービス 御中
株式会社データアステル
```

### Rank 7
- score: 89.56551
- record_id: `generic_chunk_5bac8161e5eadf9a`
- record_type: `generic_chunk`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/05.会議/報告資料/報告資料_2025-08-06.docx`

```text
gday の定義不整合: A02（進行中）を完了し、前処理仕様へ反映する必要あり。これが未確定のまま前処理を固定すると、曜日/平日フラグ起因の特徴解釈に誤差が残るリスクがあります。

<!-- block_index=55 type=paragraph style=Compact -->
詳細な欠損・分布レポート（A03）および初期EDA図表（A04）は未提出・未着手のため、EDAベースの解釈は限定的です。metrics.json 内の eda_summary は生成されていますが、ビジネス合意用の解釈図表はまだ整備中です。

<!-- block_index=56 type=paragraph style=Compact -->
注意（数値補足）

<!-- block_index=57 type=paragraph style=Compact -->
学習データの行数（8,645行）はプロジェクト概要に記載がありますが、当該数値は本報告の主出典（Report facts JSON）内に明示されていないため「assumption（仮置き）」として扱います。正式なデータ件数は A03 の品質報告で再確認してください。

<!-- block_index=58 type=paragraph style=Heading 2 -->
## 5. リスクと対応策

<!-- block_index=59 type=paragraph style=Compact -->
主要リスク（現フェーズでの優先度高）

<!-- block_index=60 type=paragraph style=Compact -->
データ定義不整合リスク（高）

<!-- block_index=61 type=paragraph style=Compact -->
根拠: yr / workingday の辞書と実データの差異が確認されている（M01議事録・A02）。

<!-- block_index=62 type=paragraph style=Compact -->
影響: 前処理/特徴量設計の誤り、モデル解釈の齟齬。

<!-- block_index=63 type=paragraph style=Compact -->
対策: A02 を優先完了 → 前処理仕様へ反映（担当: 鈴木 / 木村）。クライアント側での定義確認（A06: 高山）を催促。MS2（2025-07-29）相当のゲート完了を確認。

<!-- block_index=64 type=paragraph style=Compact -->
外生要因依存／汎化性リスク（中）

<!-- block_index=65 type=paragraph style=Compact -->
根拠: 気象・祝日等の影響が大きい想定。現行データ範囲での偏りがある場合、外挿性が低下する。

<!-- block_index=66 type=paragraph style=Compact -->
対策: 時系列交差検証・外部期間での妥当性確認を追加で実施。結果の解釈条件を成果物に明記。

<!-- block_index=67 type=paragraph style=Compact -->
スコープ／スケジュールリスク（中）

<!-- block_index=68 type=paragraph style=Compact -->
根拠: Week3 中間での追加要求や定義修正が後工程に波及する可能性。

<!-- block_index=69 type=paragraph style=Compact -->
対策: 変更管理ポリシー（T19）に従い、スコープ外作業は別途見積。リスクバッファを活用。

<
```

### Rank 8
- score: 89.499002
- record_id: `pdf_page_d898d100e519e851`
- record_type: `pdf_page`
- source_path: `share/共有ドライブ/プロジェクト/株式会社青潮モビリティサービス/06.報告書/株式会社青潮モビリティサービス_最終報告.pdf`

```text
データアステル（検証）
```
