# Strict Resolver runtime notes

EDA065 does not rerun or instrument production code. It observes the Gate19 `final_source_plans.jsonl`, `source_selection_results.jsonl`, and `answer_results.jsonl` emitted by the actual Strict Pipeline. `selected_documents` is the planning-stage source set. `executor_selected_documents` is the executor-reported final usage set; an override is recorded rather than treated automatically as a planning error.
