"""Human_checkを使わず、既存フォールバック候補の旧・新probeを比較する。"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(worktree: Path) -> None:
    root = worktree.resolve()
    sys.path.insert(0, str(root / "src"))
    from rag_competition.llm.company_retrieval import CompanyScopedRetriever
    from rag_competition.llm.question_aware_probe import build_question_aware_probe, extract_query_signals
    from rag_competition.schemas import SearchRecord

    run = root / "data/work/gate19_test100_final_candidate"
    out = root / "data/output/multistage_planner_poc_v1"
    analysis, reports = out / "analysis", out / "reports"
    files = read_jsonl(run / "inventory/file_records.jsonl")
    records = read_jsonl(run / "extracted/search_records.jsonl")
    plans = read_jsonl(run / "planning/final_source_plans.jsonl")
    analyses = {int(row["index"]): row for row in read_jsonl(run / "planning/question_analysis.jsonl")}
    file_by_id = {row["file_id"]: row for row in files}
    records_by_file: dict[str, list[SearchRecord]] = defaultdict(list)
    for row in records:
        records_by_file[str(row["file_id"])].append(SearchRecord(**row))
    retriever = CompanyScopedRetriever(files, records)
    fallback = [row for row in plans if not row.get("final_selected_file_ids") or row.get("selection_status") in {"ambiguous", "not_found"}][:2]
    rows: list[dict[str, Any]] = []
    for plan in fallback:
        question_id = int(plan["question_id"])
        question_data = analyses[question_id]
        question = str(question_data.get("question_original") or question_data.get("question_normalized") or "")
        expanded = str(question_data.get("question_for_search") or question_data.get("question_term_expanded") or "")
        # Use the existing deterministic search expansion only for retrieval.
        # The original question remains the Planner-facing text.
        retrieval_query = expanded or question
        retrieved, _ = retriever.retrieve(retrieval_query, mode="two_stage", top_k=5)
        seen: set[str] = set()
        for item in retrieved:
            document_id = item.document_id
            if document_id in seen:
                continue
            seen.add(document_id)
            document_records = records_by_file[document_id]
            signals = extract_query_signals(question, expanded)
            old_text = "\n".join(record.text[:180] for record in document_records[:2])[:600]
            old_matches = [term for term in signals["exact_terms"] if term and term.casefold() in old_text.casefold()]
            old_locations = sum(1 for record in document_records[:2] if record.metadata)
            probe = build_question_aware_probe(file_by_id[document_id], document_records, question, expanded_question=expanded)
            new_matches = sum(len(snippet["matched_terms"]) for snippet in probe["evidence_snippets"])
            classification = "improved_relevant_evidence" if new_matches > len(old_matches) else "no_change"
            if not probe["evidence_snippets"]:
                classification = "candidate_documents_insufficient"
            elif probe["evidence_density"] == 0:
                classification = "relevant_evidence_not_in_candidates"
            rows.append({
                "question_id": question_id, "document_id": document_id, "file_name": file_by_id[document_id]["file_name"],
                "old_snippet_count": min(2, len(document_records)), "new_snippet_count": len(probe["evidence_snippets"]),
                "old_question_match_count": len(old_matches), "new_question_match_count": new_matches,
                "old_location_metadata_count": old_locations, "new_location_metadata_count": sum(item["location"] is not None for item in probe["evidence_snippets"]),
                "old_probe_characters": len(old_text), "new_probe_characters": probe["probe_character_count"],
                "new_evidence_density": probe["evidence_density"], "probe_truncated": probe["probe_truncated"],
                "classification": classification,
            })
    analysis.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    path = analysis / "document_probe_before_after.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    improved = sum(row["classification"] == "improved_relevant_evidence" for row in rows)
    (analysis / "document_probe_gap_audit.md").write_text(
        "# Document probe gap audit\n\n"
        "旧probeは文書先頭の固定断片へ依存し、日本語質問の局所語、ID、表見出し、位置metadataを一つのEvidence単位へ結合していなかった。"
        "新probeは既存SearchRecordだけを順位付けし、資料全文・Human_check・正式回答を入力に使わない。\n",
        encoding="utf-8",
    )
    (analysis / "question_aware_probe_design.md").write_text(
        "# Question-aware probe design\n\n"
        "検索シグナルは既存tokenizer、ID、日付、数値、粗い日本語句分解から得る。Recordは完全一致、正規化一致、ID・数値・日付、表見出し、位置metadataで順位付けする。"
        "上位5件を重複排除し、各本文500文字、前後context各200文字、資料全体6000文字以内に制限する。Planner入力にはさらに上位2件だけを圧縮して渡す。\n",
        encoding="utf-8",
    )
    (reports / "document_probe_offline_evaluation.md").write_text(
        "# Offline document probe evaluation\n\n"
        f"- compared candidate documents: {len(rows)}\n- improved relevant evidence: {improved}\n"
        "- 評価は質問文、既存候補資料、SearchRecordだけを使用し、Human_check・正解資料・正解回答を使用していない。\n"
        "- 文字数だけでなく、質問語一致数と位置metadata付きsnippet数を比較した。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", type=Path, required=True)
    main(parser.parse_args().worktree)
