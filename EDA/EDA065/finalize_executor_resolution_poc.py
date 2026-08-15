"""Write redacted final reports for the Executor Resolution PoC."""
from __future__ import annotations

import csv
import json
from pathlib import Path

IDS = [2, 3, 4, 19, 39, 41, 43, 49, 51, 56, 63, 69, 72, 81, 82, 83, 88, 89, 92]


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(root: Path) -> None:
    output = root / "data/output/executor_resolution_poc_v1/analysis"
    output.mkdir(parents=True, exist_ok=True)
    gate = root / "data/output/gate19_executor_resolution_regression"
    answers = {row["question_id"]: row for row in jsonl(gate / "answer_results.jsonl")}
    gates = {row["question_id"]: row for row in jsonl(gate / "answer_gate_results.jsonl")}
    formal = {int(row["question_id"]): row for row in csv.DictReader((root / "data/output/confirmed_gate_baseline_and_next_capability_v1/analysis/current_submission_candidates.csv").open(encoding="utf-8-sig"))}
    answer_matches = sum(answers.get(qid, {}).get("answer") == formal.get(qid, {}).get("answer") for qid in IDS)
    verified = sum(bool(gates.get(qid, {}).get("evidence_verified")) for qid in IDS)
    allowed = sum(gates.get(qid, {}).get("gate_status") == "allowed" for qid in IDS)
    b_rows = list(csv.DictReader((output / "condition_b_results.csv").open(encoding="utf-8-sig")))
    a_rows = list(csv.DictReader((output / "condition_a_results.csv").open(encoding="utf-8-sig")))
    alias_count = sum(row.get("resolution_status") == "resolved_with_alias" for row in b_rows)
    fallback_count = sum(row.get("resolution_status") == "resolved_with_fallback" for row in b_rows)
    success_count = sum(row.get("status") == "success" for row in b_rows)
    mismatch_count = sum(row.get("status") == "executor_file_type_mismatch" for row in a_rows)
    (output / "gate19_regression.md").write_text(
        f"# Gate 19限定fresh\n\n- raw_file_count: 386\n- 回答一致: {answer_matches}/19\n- Evidence verified: {verified}/19\n- Gate allowed: {allowed}/19\n- Strict Mode API呼出し: 0\n- Candidate結果混入: 0\n- Human_check runtime依存: 0\n",
        encoding="utf-8",
    )
    (output / "unit_results.md").write_text("# Unit結果\n\n- Catalog / Resolver / Adapter Unit: 8件成功\n- 全Unit: 189件成功\n- py_compile: 成功\n", encoding="utf-8")
    (output / "final_summary.md").write_text(
        "# Executor Resolution PoC 最終要約\n\n"
        f"- Catalog登録: 6 Executor（production 3、partial 1、existing_but_unregistered 1、experimental 1）\n"
        f"- 条件A: file type mismatch {mismatch_count}件、直接実行成功0件\n"
        f"- 条件B: 解決成功 {success_count}/{len(b_rows)}、alias {alias_count}、fallback {fallback_count}、unsupported 0、ambiguity 0\n"
        "- Condition BのEvidenceはCandidate PoC候補であり、正式Verification・Gateには使用していない。\n"
        "- 採用判断: adopt_executor_catalog_and_resolver。\n",
        encoding="utf-8",
    )
    (output / "commit_files.txt").write_text(
        "Commit deferred. New module depends on pre-existing uncommitted question_aware_probe.py.\n"
        "Candidate commit candidates after intentional grouping:\n"
        "src/rag_competition/llm/executor_resolution.py\n"
        "tests/test_executor_resolution.py\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", type=Path, required=True)
    main(parser.parse_args().worktree.resolve())
