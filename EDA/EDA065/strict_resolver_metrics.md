# Strict Resolver metrics

{
  "labeled_questions": 35,
  "evaluable_questions": 21,
  "resolver_coverage": 1.0,
  "resolver_execution_success_rate": 1.0,
  "all_required_documents_exact_rate": 0.6666666666666666,
  "primary_document_accuracy": 0.6666666666666666,
  "required_document_recall": 0.6666666666666666,
  "pipeline_final_all_required_documents_exact_rate": 0.7619047619047619,
  "executor_source_override_count": 5,
  "no_selection_rate": 0.02857142857142857,
  "not_observable_rate": 0.0,
  "execution_error_rate": 0.0
}

## Subsets

{"subset": "formal_gate_evidence", "questions": 16, "evaluable": 16, "strict_exact": 14, "strict_primary": 14, "generated_by": "offline_metric", "source": "strict_resolver_results", "confidence": "medium", "requires_manual_review": false}
{"subset": "human_check", "questions": 19, "evaluable": 5, "strict_exact": 0, "strict_primary": 0, "generated_by": "offline_metric", "source": "strict_resolver_results", "confidence": "medium", "requires_manual_review": true}
{"subset": "explicit_filename", "questions": 0, "evaluable": 0, "strict_exact": 0, "strict_primary": 0, "generated_by": "offline_metric", "source": "strict_resolver_results", "confidence": "medium", "requires_manual_review": false}
{"subset": "companyless", "questions": 26, "evaluable": 13, "strict_exact": 7, "strict_primary": 7, "generated_by": "offline_metric", "source": "strict_resolver_results", "confidence": "medium", "requires_manual_review": true}
{"subset": "multiple_document", "questions": 13, "evaluable": 5, "strict_exact": 0, "strict_primary": 0, "generated_by": "offline_metric", "source": "strict_resolver_results", "confidence": "medium", "requires_manual_review": true}

Metrics are evaluated only against labels marked complete; incomplete human-reviewed labels remain observable but do not inflate accuracy claims.
