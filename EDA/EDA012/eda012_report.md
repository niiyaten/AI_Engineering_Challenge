# EDA012: Word文書の再現可能Markdown化

## 目的・背景

`data/raw/share` 配下のWord文書を、`data/processed/share` 配下に同じディレクトリ構成でMarkdown化します。
太字、斜体、下線、文字色、ハイライト、段落スタイル、表、画像メタデータは、Markdown表示だけでなく `.structure.json` にも保存します。
これにより、LLMにはMarkdownを渡し、必要に応じてJSONからWordに近い構造を再構成できるようにします。

## 実行設定

- source_root: `data/raw/share`
- processed_root: `data/processed/share`
- clean_output: True

## 結果

- 対象Wordファイル数: 47
- 変換成功: 46
- 変換失敗: 1
- 抽出表数: 78
- 抽出画像数: 1

## 失敗ファイル

| raw_relative_path | error_type | error_message |
|---|---|---|
| `share/共有ドライブ/プロジェクト/医療法人社団 恒一会 かえで総合病院/01.契約/契約書_pw-kaede20250902.docx` | BadZipFile | File is not a zip file |

凡例: `raw_relative_path` は `data/raw/share` からの相対パス、`error_type` は例外種別、`error_message` は失敗理由を表します。

## 主な出力

| パス | 内容 |
|---|---|
| `data/processed/share/**/*.docx.md` | LLM入力向けMarkdown |
| `data/processed/share/**/*.docx.structure.json` | Word再構成用の段落・run・表・画像メタデータ |
| `EDA/EDA012/tables/docx_markdown_conversion_log.csv` | 変換ログ |

凡例: `パス` は出力先、`内容` はそのファイルが持つ情報を表します。
