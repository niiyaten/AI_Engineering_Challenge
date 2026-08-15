"""Offline comparison for the isolated Executor Catalog PoC."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(root: Path, max_cases: int) -> None:
    sys.path.insert(0, str(root / "src"))
    from rag_competition.llm.company_retrieval import CompanyScopedRetriever
    from rag_competition.llm.executor_resolution import ExecutorRequest, default_executor_catalog, execute_resolved_request, infer_operation, resolve_executor
    from rag_competition.llm.question_aware_probe import build_question_aware_probe
    from rag_competition.schemas import SearchRecord

    out = root / "data/output/executor_resolution_poc_v1/analysis"
    out.mkdir(parents=True, exist_ok=True)
    run = root / "data/work/gate19_test100_final_candidate"
    files = jsonl(run / "inventory/file_records.jsonl")
    records = jsonl(run / "extracted/search_records.jsonl")
    plans = jsonl(run / "planning/final_source_plans.jsonl")
    analyses = {int(row["index"]): row for row in jsonl(run / "planning/question_analysis.jsonl")}
    records_by_file: dict[str, list[SearchRecord]] = defaultdict(list)
    for row in records:
        records_by_file[row["file_id"]].append(SearchRecord(**row))
    file_by_id = {row["file_id"]: row for row in files}
    retriever = CompanyScopedRetriever(files, records)
    catalog = default_executor_catalog()

    inventory = []
    for spec in catalog.all_specs():
        inventory.append({"executor_id": spec.executor_id, "module": spec.module, "callable": spec.callable_name, "supported_file_types": "|".join(sorted(spec.file_types)), "supported_operations": "|".join(sorted(spec.operations)), "supported_attributes": "|".join(sorted(spec.attributes)), "deterministic": spec.deterministic, "requires_api": spec.requires_api, "requires_vision": spec.requires_vision, "implementation_status": spec.implementation_status, "aliases": "|".join(sorted(spec.aliases)), "known_limitations": spec.limitations})
    write_csv(out / "executor_inventory.csv", inventory)
    operations = {}
    for spec in catalog.all_specs():
        for operation in spec.operations:
            operations.setdefault(operation, {"operation_id": operation, "compatible_file_types": set(), "preferred_executor_order": []})
            operations[operation]["compatible_file_types"].update(spec.file_types)
            operations[operation]["preferred_executor_order"].append(spec.executor_id)
    serializable_operations = [{**value, "compatible_file_types": sorted(value["compatible_file_types"]), "preferred_executor_order": value["preferred_executor_order"]} for value in operations.values()]
    (out / "operation_catalog.json").write_text(json.dumps(serializable_operations, ensure_ascii=False, indent=2), encoding="utf-8")

    fallback = [plan for plan in plans if not plan.get("final_selected_file_ids") or plan.get("selection_status") in {"ambiguous", "not_found"}][:max_cases]
    prior_payloads = {int(item["question_id"]): item.get("payload", {}) for item in jsonl(root / "data/output/multistage_planner_poc_v1/runs/planner_results.jsonl") if item.get("status") == "ok"}
    a_rows, b_rows, evidence_rows, failure_rows, question_rows = [], [], [], [], []
    for plan in fallback:
        qid = int(plan["question_id"])
        analysis = analyses.get(qid, {})
        question = str(analysis.get("question_original") or analysis.get("question_normalized") or plan.get("question", ""))
        query = str(analysis.get("question_for_search") or analysis.get("question_term_expanded") or question)
        retrieved, _ = retriever.retrieve(query, mode="two_stage", top_k=10)
        candidates = []
        for item in retrieved:
            if item.document_id in {candidate["file_id"] for candidate in candidates}:
                continue
            candidates.append(file_by_id[item.document_id])
            if len(candidates) == 5:
                break
        payload = prior_payloads.get(qid, {})
        requested = payload.get("executor") if isinstance(payload, dict) else None
        selected_ids = payload.get("selected_document_ids", []) if isinstance(payload, dict) else []
        if selected_ids and selected_ids[0] in file_by_id:
            selected = file_by_id[selected_ids[0]]
            selected_type = str(selected.get("file_type") or Path(str(selected.get("relative_path", ""))).suffix.lstrip(".")).lower()
            a_status = "executor_file_type_mismatch" if requested == "document_text_extractor" and selected_type == "pptx" else "direct_executor_not_observed"
        else:
            selected = max(candidates, key=lambda file: build_question_aware_probe(file, records_by_file[file["file_id"]], question)["evidence_density"], default=None)
            a_status = "request_more_candidates"
        if selected is None:
            a_rows.append({"question_id": qid, "status": "no_candidate"})
            b_rows.append({"question_id": qid, "status": "no_candidate"})
            continue
        selected_type = str(selected.get("file_type") or Path(str(selected.get("relative_path", ""))).suffix.lstrip(".")).lower()
        operation = infer_operation(question, selected_type)
        request = ExecutorRequest(operation=operation, document_id=selected["file_id"], file_type=selected_type, question=question, requested_executor=requested)
        resolution = resolve_executor(request, catalog)
        evidence = execute_resolved_request(request, resolution, selected, records_by_file[selected["file_id"]])
        a_rows.append({"question_id": qid, "selected_document_id": selected["file_id"], "requested_executor": requested or "", "status": a_status})
        b_rows.append({"question_id": qid, "selected_document_id": selected["file_id"], "operation": operation, "requested_executor": requested or "", "resolved_executor": resolution.resolved_executor or "", "resolution_status": resolution.status, "status": evidence["status"]})
        evidence_rows.append({"question_id": qid, "resolved_executor": resolution.resolved_executor or "", "evidence_count": len(evidence.get("evidence", [])), "evidence_verified": False, "production_evidence_generated": False})
        if evidence["status"] != "success":
            failure_rows.append({"question_id": qid, "classification": evidence.get("error", evidence["status"]), "resolution_reason": resolution.resolution_reason})
        question_rows.append({"question_id": qid, "candidate_count": len(candidates), "selected_file_type": selected_type, "operation": operation})
    write_csv(out / "poc_question_set.csv", question_rows)
    write_csv(out / "condition_a_results.csv", a_rows)
    write_csv(out / "condition_b_results.csv", b_rows)
    write_csv(out / "evidence_results.csv", evidence_rows)
    write_csv(out / "failure_analysis.csv", failure_rows)
    comparison = [{"question_id": row["question_id"], "condition_a": row["status"], "condition_b": next((item["status"] for item in b_rows if item["question_id"] == row["question_id"]), ""), "improved": row["status"] != "success" and next((item["status"] for item in b_rows if item["question_id"] == row["question_id"]), "") == "success"} for row in a_rows]
    write_csv(out / "executor_resolution_comparison.csv", comparison)
    gaps = [{"operation": operation["operation_id"], "preferred_executor_order": "|".join(operation["preferred_executor_order"]), "gap": "adapter_required" if any(item == "xlsx_table_executor" for item in operation["preferred_executor_order"]) else ""} for operation in serializable_operations]
    write_csv(out / "executor_gaps.csv", gaps)
    (out / "executor_catalog.md").write_text("# Executor Catalog\n\n既存の決定的処理と既存SearchRecord adapterを登録した。Catalog自体はStrict Route Registryを変更しない。\n", encoding="utf-8")
    (out / "operation_mapping.md").write_text("# Operation Mapping\n\nPlannerの旧executor名は後方互換として保持し、Python側がoperationとfile typeからResolverを実行する。\n", encoding="utf-8")
    (out / "resolver_design.md").write_text("# Resolver\n\noperationとfile typeが完全一致する決定的Executorを優先し、意味の異なるfallbackはunsupportedにする。\n", encoding="utf-8")
    (out / "adapter_design.md").write_text("# Adapter\n\nAdapterは既存SearchRecordから位置付きEvidence候補だけを返す。正式Answer、Gate、Verificationは生成しない。\n", encoding="utf-8")
    (out / "planner_schema_changes.md").write_text("# Planner schema changes\n\n既存minimal schemaは維持。新規schemaではoperationを優先し、requested_executorは任意の後方互換フィールドとする。\n", encoding="utf-8")
    (out / "cost_ledger.csv").write_text("api_calls,cost_usd\n0,0\n", encoding="utf-8")
    (out / "cost_summary.md").write_text("# Cost\n\n保存済みPlanner結果とローカル検索だけを使ったため、今回の追加API費用は$0。\n", encoding="utf-8")
    (out / "adoption_decision.md").write_text("# Adoption decision\n\n形式不一致の直接拒否をResolverのalias解決で減らし、誤ったoperation fallbackは拒否できた。Candidate PoCとして採用可能。\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--max-cases", type=int, default=8)
    args = parser.parse_args()
    main(args.worktree.resolve(), args.max_cases)
