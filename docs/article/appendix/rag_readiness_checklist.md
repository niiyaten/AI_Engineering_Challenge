# RAG Readiness Checklist

社内文書をRAGへ入れる前の簡易監査表です。

## 文書単体

- [ ] タイトルだけで文書の目的が分かる
- [ ] 文書IDが一意である
- [ ] 作成日 / 発行日 / 更新日が分かる
- [ ] Draft / Approved / Obsolete が分かる
- [ ] 最新版かどうか機械判定できる
- [ ] 見出し階層がある
- [ ] 1セクションが概ね1トピックになっている
- [ ] 「上記」「前述」「同条件」だけに依存していない
- [ ] 略語の初出に定義がある
- [ ] 表の列名に意味と単位がある
- [ ] 色だけで重要な意味を表していない
- [ ] グラフの軸名・単位・captionがある
- [ ] 重要なグラフには元数値データが残っている
- [ ] スクリーンショットだけに重要情報が閉じていない

## Metadata

- [ ] document_id
- [ ] document_type
- [ ] project / department
- [ ] version
- [ ] status
- [ ] issued_at / updated_at
- [ ] latest
- [ ] access_groups / confidentiality
- [ ] source_path
- [ ] content_hash

## RAG取り込み

- [ ] section-aware chunkingをしている
- [ ] 親見出しをchunkへ引き継いでいる
- [ ] BM25とvectorを併用できる
- [ ] metadata filterが使える
- [ ] 権限filterをretrieval前に適用する
- [ ] 旧版を通常検索から除外できる
- [ ] 文書更新時に差分だけ再indexできる
- [ ] 削除・廃止文書をindexから除外できる
- [ ] 回答から元文書の位置へ戻れる
