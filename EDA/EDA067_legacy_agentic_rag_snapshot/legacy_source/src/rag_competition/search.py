from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .schemas import SearchRecord


def tokenize(text: str) -> list[str]:
    """日本語と英数字が混ざる文を、軽量BM25用の検索語へ分解する。"""
    normalized = text.lower()
    tokens = re.findall(r"[a-z0-9_]+|[一-龥ぁ-んァ-ンー]{2,}", normalized)
    extra: list[str] = []
    for token in tokens:
        if re.fullmatch(r"[一-龥ぁ-んァ-ンー]{4,}", token):
            extra.extend(token[i : i + 2] for i in range(len(token) - 1))
    return tokens + extra


@dataclass
class SearchHit:
    record: SearchRecord
    score: float
    matched_terms: list[str]


class BM25Index:
    """今回の実行で生成したSearchRecordだけを対象にした小規模BM25。"""

    def __init__(self, records: list[SearchRecord], k1: float = 1.5, b: float = 0.75) -> None:
        self.records = records
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(record.text + " " + record.raw_path) for record in records]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        self.term_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        document_frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            document_frequency.update(set(tokens))
        self.idf = {
            term: math.log(1 + (len(records) - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    def search(self, query: str, top_k: int = 20) -> list[SearchHit]:
        query_terms = tokenize(query)
        if not query_terms:
            return []
        unique_terms = list(dict.fromkeys(query_terms))
        hits: list[SearchHit] = []
        for i, record in enumerate(self.records):
            score = 0.0
            matched: list[str] = []
            length = self.doc_lengths[i] or 1
            tf = self.term_freqs[i]
            for term in unique_terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                matched.append(term)
                idf = self.idf.get(term, 0.0)
                denom = freq + self.k1 * (1 - self.b + self.b * length / (self.avgdl or 1))
                score += idf * (freq * (self.k1 + 1) / denom)
            if score > 0:
                hits.append(SearchHit(record=record, score=score, matched_terms=matched))
        # BM25スコアが同じRecordは、元ファイルとRecord IDで決定的に並べる。
        hits.sort(key=lambda hit: (-hit.score, hit.record.raw_path.casefold(), hit.record.record_id))
        return hits[:top_k]
