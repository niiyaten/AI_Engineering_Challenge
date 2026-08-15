# EDA064 Top-K method

EDA064 calls `candidate_files_for_question` directly. It builds a BM25 index over the 1,614 SearchRecord entries, aggregates hit scores by `file_id`, then adds heuristic metadata scores. It is a document candidate ranking audit, not the Gate19 Strict Resolver or a capability-specific final source selector. No vector index or LLM selector is used.
