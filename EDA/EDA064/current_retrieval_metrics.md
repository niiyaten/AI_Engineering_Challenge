# Current Top-K metrics

{"correct_source_missing_rate": 0.375, "group": "gate19_labeled", "labeled_questions": 16, "top10_recall": 0.625, "top1_accuracy": 0.125, "top3_recall": 0.375, "top5_recall": 0.5}
{"correct_source_missing_rate": 0.5142857142857142, "group": "all_labeled", "labeled_questions": 35, "top10_recall": 0.4857142857142857, "top1_accuracy": 0.17142857142857143, "top3_recall": 0.2857142857142857, "top5_recall": 0.37142857142857144}

# Top-1 source-label diagnostics

{"companyless_labeled_questions": 26, "cross_company_contamination": 15, "explicit_filename_failure": 3, "same_name_file_confusion": 5, "top1_company_match": 12, "top1_document_role_match": 14, "top1_file_type_match": 17}

Company, file-type, and role diagnostics are inferred from labeled source paths. Multi-document labels are treated as a matching set and require manual review for causal interpretation.