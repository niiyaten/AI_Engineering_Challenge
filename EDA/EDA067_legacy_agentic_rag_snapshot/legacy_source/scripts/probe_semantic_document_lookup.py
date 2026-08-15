from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rag_competition.llm_client import OpenRouterClient
from rag_competition.schemas import CompactFileProfile, FileRecord, SearchRecord


def jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="openai/gpt-oss-20b:free")
    parser.add_argument("--no-api-cache", action="store_true")
    args = parser.parse_args()
    subtype_path = args.output_dir / "document_extraction_subtypes.csv"
    semantic_ids = [int(row["question_id"]) for row in csv.DictReader(subtype_path.open(encoding="utf-8-sig")) if row["subtype"] == "semantic_document_lookup"]
    analyses = {row["index"]: row for row in jsonl(args.run_dir / "planning" / "question_analysis.jsonl")}
    plans = {str(row["question_id"]): row for row in jsonl(args.run_dir / "planning" / "final_source_plans.jsonl")}
    files = {row["file_id"]: row for row in jsonl(args.run_dir / "inventory" / "file_records.jsonl")}
    records = jsonl(args.run_dir / "extracted" / "search_records.jsonl")
    by_file: dict[str, list[dict]] = {}
    for record in records: by_file.setdefault(record["file_id"], []).append(record)
    client = OpenRouterClient(project_root=args.run_dir.parents[2], output_dir=args.run_dir / "logs", model=args.model, temperature=0.0, use_cache=not args.no_api_cache)
    results: list[dict] = []
    for question_id in semantic_ids:
        analysis = analyses.get(str(question_id), {})
        plan = plans.get(str(question_id), {})
        selected = [str(value) for value in plan.get("final_selected_file_ids", [])]
        candidates = []
        for file_id in selected:
            for record in by_file.get(file_id, [])[:4]:
                candidates.append({"candidate_id": record["record_id"], "file_id": file_id, "source_path": files.get(file_id, {}).get("raw_path", ""), "record_type": record.get("record_type", ""), "preview": record.get("text", "")[:600]})
        candidates = candidates[:20]
        prompt = json.dumps({"question": analysis.get("question_original", ""), "candidates": candidates, "output": {"selected_candidate_ids": [], "selection_reason": "", "confidence": 0.0, "missing_information": [], "selection_status": "selected|ambiguous|not_found|insufficient_context|error"}}, ensure_ascii=False)
        result = client.call_json("semantic_document_lookup", prompt, max_tokens=800)
        parsed = result.parsed_json if result.success else {}
        results.append({"question_id": question_id, "candidate_count": len(candidates), "selected_count": len(parsed.get("selected_candidate_ids", [])), "selection_status": parsed.get("selection_status", "error"), "confidence": parsed.get("confidence", 0.0), "selection_reason": parsed.get("selection_reason", ""), "api_called": result.api_called, "cache_hit": result.cache_hit, "model": result.model, "prompt_hash": result.prompt_hash, "parse_success": result.parse_success, "fallback_used": not result.success, "fallback_reason": result.error})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "semantic_document_lookup_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(results[0].keys()) if results else ["question_id"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(results)
    (args.output_dir / "semantic_document_lookup_results.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n", encoding="utf-8")
    (args.output_dir / "semantic_document_lookup_summary.json").write_text(json.dumps({"question_count": len(results), "api_call_count": client.api_call_count, "cache_hit_count": sum(row["cache_hit"] for row in results), "parse_success_count": sum(row["parse_success"] for row in results), "fallback_count": sum(row["fallback_used"] for row in results), "model": args.model}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
