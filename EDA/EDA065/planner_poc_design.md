# Planner PoC design

Condition 1 supplies question, filename/project/file-type/role signals, and generic retrieval scores. Condition 2 adds compact Top-K document probes. Evaluate final Top-1 accuracy, Top-3 recall, required-document recall, multi-document recall, wrong-company selections, same-name confusion, abstention quality, and executor-family selection. Human labels remain evaluation-only. Only 1 B-group questions currently satisfy both complete-label and generic-Top-10 conditions; do not pad the PoC with U-group seating questions until their final-source labels are clarified.
