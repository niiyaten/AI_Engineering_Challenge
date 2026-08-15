# Strict Resolver versus generic Top-K

- both_correct: 7
- both_fail: 6
- generic_top5_only_contains_label: 1
- strict_only_correct: 7
- strict_result_not_evaluable: 14

Strict uses source requirements and content verification before final execution. Generic Top-K is a BM25-plus-metadata retrieval audit. They are complementary measurements, not equivalent accuracy scores.
