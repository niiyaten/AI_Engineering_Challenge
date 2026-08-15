"""Offline Candidate foundation PoC; never writes formal artifacts."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main(root: Path, max_cases: int) -> None:
    sys.path.insert(0, str(root / "src"))
    from rag_competition.llm.candidate_evidence import candidate_evidence_from_adapter, generate_candidate_answer, select_candidate_evidence, serialize_candidate_evidence, verify_candidate_evidence
    from rag_competition.llm.company_retrieval import CompanyScopedRetriever
    from rag_competition.llm.executor_resolution import ExecutorRequest, default_executor_catalog, execute_resolved_request, infer_operation, resolve_executor
    from rag_competition.llm.question_aware_probe import build_question_aware_probe
    from rag_competition.schemas import SearchRecord

    out = root / "data/output/candidate_foundation_longrun_v1/analysis"; out.mkdir(parents=True, exist_ok=True)
    run = root / "data/work/gate19_test100_final_candidate"
    files, records, plans = load_jsonl(run / "inventory/file_records.jsonl"), load_jsonl(run / "extracted/search_records.jsonl"), load_jsonl(run / "planning/final_source_plans.jsonl")
    analyses = {int(row["index"]): row for row in load_jsonl(run / "planning/question_analysis.jsonl")}
    file_by_id = {row["file_id"]: row for row in files}; by_file: dict[str, list[SearchRecord]] = defaultdict(list)
    for row in records: by_file[row["file_id"]].append(SearchRecord(**row))
    retriever, catalog = CompanyScopedRetriever(files, records), default_executor_catalog()
    fallback = [plan for plan in plans if not plan.get("final_selected_file_ids") or plan.get("selection_status") in {"ambiguous", "not_found"}][:max_cases]
    quality, verification_rows, answer_rows, operations, adapters, executors, question_rows = [], [], [], [], [], [], []
    for plan in fallback:
        qid = int(plan["question_id"]); analysis = analyses.get(qid, {})
        question = str(analysis.get("question_original") or analysis.get("question_normalized") or plan.get("question", ""))
        query = str(analysis.get("question_for_search") or analysis.get("question_term_expanded") or question)
        hits, meta = retriever.retrieve(query, mode="two_stage", top_k=10)
        candidates = []
        for hit in hits:
            if hit.document_id not in {row["file_id"] for row in candidates}:
                candidates.append(file_by_id[hit.document_id])
            if len(candidates) == 5: break
        if not candidates:
            question_rows.append({"question_id": qid, "status": "no_candidate"}); continue
        selected = max(candidates, key=lambda file: build_question_aware_probe(file, by_file[file["file_id"]], question)["evidence_density"])
        file_type = str(selected.get("file_type") or Path(str(selected.get("relative_path", ""))).suffix.lstrip(".")).lower()
        operation = infer_operation(question, file_type)
        request = ExecutorRequest(operation=operation, document_id=selected["file_id"], file_type=file_type, question=question)
        resolution = resolve_executor(request, catalog)
        adapter_result = execute_resolved_request(request, resolution, selected, by_file[selected["file_id"]])
        evidence_items = candidate_evidence_from_adapter(qid, request, resolution, selected, adapter_result)
        verifications = [verify_candidate_evidence(item) for item in evidence_items]
        serialized = [serialize_candidate_evidence(item, verification) for item, verification in zip(evidence_items, verifications)]
        selected_evidence, selection_ambiguous = select_candidate_evidence(evidence_items)
        selected_verification = verify_candidate_evidence(selected_evidence, ambiguity=selection_ambiguous) if selected_evidence else None
        answer = generate_candidate_answer(selected_evidence, selected_verification) if selected_evidence and selected_verification else None
        question_rows.append({"question_id": qid, "candidate_count": len(candidates), "selected_document_id": selected["file_id"], "file_type": file_type, "operation": operation, "resolver_status": resolution.status, "executor": resolution.resolved_executor or "", "adapter_status": adapter_result.get("status"), "retrieval_company_constrained": meta.get("company_constrained", False)})
        for item in serialized:
            quality.append({"question_id": qid, "document_id": item["document_id"], "file_type": item["file_type"], "operation": item["operation"], "executor": item["executor_id"], "location": item["location"], "matched_term_count": len(item["matched_terms"]), "support_status": item["support_status"], "candidate_only": item["candidate_only"]})
            verification_rows.append({"question_id": qid, "support_status": item["verification"]["support_status"], "verified": item["verification"]["verified"], "reasons": "|".join(item["verification"]["reasons"])})
        answer_rows.append({"question_id": qid, "status": answer.status if answer else "abstain", "answer_type": answer.answer_type if answer else "", "evidence_count": len(evidence_items), "support_status": answer.support_status if answer else "insufficient", "candidate_only": True})
        operations.append({"question_id": qid, "operation": operation, "status": resolution.status, "gap": "" if resolution.resolved_executor else resolution.resolution_reason})
        adapters.append({"question_id": qid, "adapter": resolution.adapter_id or "", "status": adapter_result.get("status"), "gap": adapter_result.get("error", "")})
        executors.append({"question_id": qid, "executor": resolution.resolved_executor or "", "status": resolution.status, "file_type": file_type})
    save_csv(out / "poc_question_set.csv", question_rows); save_csv(out / "evidence_quality_results.csv", quality); save_csv(out / "evidence_verification_results.csv", verification_rows); save_csv(out / "candidate_answer_results.csv", answer_rows); save_csv(out / "operation_gap_analysis.csv", operations); save_csv(out / "adapter_gap_analysis.csv", adapters); save_csv(out / "executor_gap_analysis.csv", executors)
    (out / "cycle_log.csv").write_text("cycle,mode,api_calls\n1,offline_candidate_foundation,0\n", encoding="utf-8")
    (out / "api_cost_ledger.csv").write_text("api_calls,cost_usd\n0,0\n", encoding="utf-8")
    (out / "api_cost_summary.md").write_text("# API cost\n\n保存済みデータだけを使用。追加API呼出し・費用は0。\n", encoding="utf-8")
    (out / "candidate_schema.md").write_text("# Candidate schema\n\nCandidateEvidence、CandidateEvidenceVerification、CandidateAnswerResultは正式schemaをimportせず、candidate_only=trueを強制する。\n", encoding="utf-8")
    (out / "candidate_pipeline_architecture.md").write_text("# Pipeline\n\nretrieval → question-aware probe → operation inference → resolver → adapter → CandidateEvidence → verification → CandidateAnswer/abstain。Strict Pipelineとは未接続。\n", encoding="utf-8")
    (out / "rejected_changes.md").write_text("# Rejected\n\nVision、問題固有rule、formal artifact更新、意味の異なるExecutor fallbackは実装しない。\n", encoding="utf-8")
    (out / "deferred_work.md").write_text("# Deferred\n\nstyle/layout/chart用のAdapter、複数Evidenceの汎用回答合成、Visionは別PoCへ保留。\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--worktree", type=Path, required=True); parser.add_argument("--max-cases", type=int, default=8)
    args = parser.parse_args(); main(args.worktree.resolve(), args.max_cases)
