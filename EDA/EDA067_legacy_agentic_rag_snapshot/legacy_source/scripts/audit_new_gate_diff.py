from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/output/semantic_list_new_gate_diff_audit_v1/analysis"
PREV = "semantic_list_extraction_relevance_aware_test_full_fresh_v1"
CURR = "semantic_list_evidence_contract_gate_bridge_test_full_fresh_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ["status"]
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run_rows(run: str) -> dict[int, dict]:
    base = ROOT / "data/output" / run
    gates = {int(x["question_id"]): x for x in read_jsonl(base / "answer_gate_results.jsonl")}
    answers = {int(x["question_id"]): x for x in read_jsonl(base / "answer_results.jsonl")}
    work = ROOT / "data/work" / run
    executions = {int(x["question_id"]): x for x in read_jsonl(work / "execution/tool_executions.jsonl")}
    return {qid: {"gate": gates.get(qid, {}), "answer": answers.get(qid, {}), "execution": executions.get(qid, {})} for qid in set(gates) | set(answers) | set(executions)}


def tool_output(row: dict) -> dict:
    return (row.get("execution", {}).get("tool_outputs") or [{}])[-1]


def evidence_rows(row: dict) -> list[dict]:
    return [x for x in (tool_output(row).get("evidence") or []) if isinstance(x, dict)]


def compact_evidence(row: dict) -> tuple[str, str, str, str, str]:
    evidence = evidence_rows(row)
    selected = [x for x in evidence if x.get("included") is True]
    excluded = [x for x in evidence if x.get("included") is False]
    selected_text = "\n".join(str(x.get("original_text") or x.get("answer_value") or "") for x in selected)
    excluded_text = "\n".join(f"{x.get('original_text','')} [{x.get('exclusion_reason','')}]" for x in excluded)
    locations = "\n".join(json.dumps({k: x.get(k) for k in ("source_file", "page", "slide", "sheet", "table", "row", "column", "source_location")}, ensure_ascii=False) for x in selected)
    context = "\n".join(f"before={x.get('context_before','')} / after={x.get('context_after','')}" for x in selected)
    return selected_text, excluded_text, locations, context, json.dumps(evidence, ensure_ascii=False)


def main() -> None:
    prev, curr = run_rows(PREV), run_rows(CURR)
    question_text = {}
    for path in [ROOT / "data/output/source_selection_resolution_capability_final_fresh_v1/analysis/capability_matrix_after_source_selection.csv", ROOT / "data/output/semantic_list_extraction_relevance_aware_fresh_v1/analysis/semantic_list_question_inventory.csv"]:
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as f:
                for item in csv.DictReader(f):
                    if item.get("question_id") is not None:
                        question_text[(item.get("dataset", ""), int(item["question_id"]))] = item.get("question_original", "")
    prev_allowed = {q for q, r in prev.items() if r["gate"].get("gate_status") == "allowed"}
    curr_allowed = {q for q, r in curr.items() if r["gate"].get("gate_status") == "allowed"}
    new = sorted(curr_allowed - prev_allowed)
    rows = []
    human = ["# 新規正式Gate許可の人間確認\n", f"前回run: `{PREV}`\n", f"今回run: `{CURR}`\n", f"新規許可: {new}\n"]
    for qid in new:
        p, c = prev.get(qid, {}), curr[qid]
        selected, excluded, locations, context, raw = compact_evidence(c)
        answer = c.get("answer", {}).get("answer", tool_output(c).get("answer", ""))
        ver = tool_output(c).get("verification", {})
        contract = tool_output(c).get("list_evidence_contract", {})
        rows.append({
            "question_id": qid,
            "question_original": question_text.get(("test", qid), c.get("answer", {}).get("question", "")),
            "answer_candidate": answer,
            "previous_gate_status": p.get("gate", {}).get("gate_status", "missing"),
            "previous_suppression_reason": p.get("gate", {}).get("suppression_reason", ""),
            "current_gate_status": c.get("gate", {}).get("gate_status", ""),
            "current_gate_reason": c.get("gate", {}).get("suppression_reason", ""),
            "newly_allowed": True,
            "needs_human_review": True,
            "safe_to_submit": False,
            "capability": "version_diff" if qid == 0 else "semantic_list_extraction",
            "executor": c.get("gate", {}).get("executor_name", "semantic_document_lookup"),
            "selected_sources": "\n".join(c.get("answer", {}).get("selected_files", [])),
            "selected_containers": json.dumps(contract.get("selected_containers", []), ensure_ascii=False),
            "included_items": selected,
            "excluded_items": excluded,
            "exclusion_reasons": "saved per candidate",
            "answer_column_evidence": all(x.get("answer_column_name") or x.get("answer_value") for x in evidence_rows(c)),
            "filter_column_evidence": all(x.get("filter_column_name") or x.get("filter_match") is True for x in evidence_rows(c)),
            "location_evidence": locations,
            "original_text": selected,
            "context": context,
            "completeness_check": ver.get("completeness_check_passed", contract.get("completeness_check_passed")),
            "independent_reconstruction": ver.get("independent_reconstruction_answer", ""),
            "common_verification": ver.get("verification_status", ""),
            "answer_gate": c.get("gate", {}).get("gate_status", ""),
            "raw_evidence_json": raw,
        })
        human.extend([
            f"## test {qid}\n",
            f"- 質問: {question_text.get(('test', qid), c.get('answer', {}).get('question', ''))}\n",
            f"- 回答候補: {answer}\n",
            f"- 前回Gate: {p.get('gate', {}).get('gate_status', 'missing')} / {p.get('gate', {}).get('suppression_reason', '')}\n",
            f"- 今回Gate: {c.get('gate', {}).get('gate_status', '')}\n",
            f"- 資料: {c.get('answer', {}).get('selected_files', [])}\n",
            f"- 採用項目と原文: {selected}\n",
            f"- 除外項目: {excluded or 'なし'}\n",
            f"- 位置Evidence: {locations}\n",
            f"- 前後文脈: {context}\n",
            f"- 完全性確認: {ver.get('completeness_check_passed', contract.get('completeness_check_passed'))}\n",
            f"- 独立再構成: {ver.get('independent_reconstruction_answer', '')}\n",
            f"- 共通Verification: {ver.get('verification_status', '')}\n",
            "- 人間確認点: 質問の対象範囲、採用項目の漏れ、除外理由、原文位置と回答粒度をraw資料で確認する。\n",
        ])
    write_csv("newly_allowed_gate_diff.csv", rows)
    write_csv("strict_gate_set_comparison.csv", [
        {"set_name": "previous_allowed", "question_ids": ",".join(map(str, sorted(prev_allowed))), "count": len(prev_allowed)},
        {"set_name": "current_allowed", "question_ids": ",".join(map(str, sorted(curr_allowed))), "count": len(curr_allowed)},
        {"set_name": "current_only", "question_ids": ",".join(map(str, new)), "count": len(new)},
        {"set_name": "previous_only", "question_ids": ",".join(map(str, sorted(prev_allowed - curr_allowed))), "count": len(prev_allowed - curr_allowed)},
        {"set_name": "intersection", "question_ids": ",".join(map(str, sorted(prev_allowed & curr_allowed))), "count": len(prev_allowed & curr_allowed)},
    ])
    # 準厳格候補は正式Gate差分とは分離する。既存成果物に記録された候補のみを参照する。
    semi = []
    semi_path = ROOT / "data/output/semantic_list_evidence_contract_gate_bridge_fresh_v1/analysis/semantic_list_semi_strict_test_candidates.csv"
    if semi_path.exists():
        with semi_path.open(encoding="utf-8-sig", newline="") as f:
            semi = list(csv.DictReader(f))
    write_csv("semi_strict_additional_candidates.csv", semi)
    (OUT / "newly_allowed_human_review.md").write_text("".join(human), encoding="utf-8")
    summary = [
        f"# Gate差分監査\n\n前回: `{PREV}` allowed={len(prev_allowed)}\n\n今回: `{CURR}` allowed={len(curr_allowed)}\n\n",
        f"今回のみallowed: {sorted(curr_allowed - prev_allowed)}\n\n前回のみallowed: {sorted(prev_allowed - curr_allowed)}\n\n共通: {sorted(prev_allowed & curr_allowed)}\n\n",
        f"期待値整合: {len(prev_allowed - curr_allowed) == 0 and len(curr_allowed - prev_allowed) == 2 and len(prev_allowed & curr_allowed) == 6}\n\n",
        "新規正式Gate許可はtest 0とtest 85。準厳格候補、人間監査済み回答、既存allowedの状態変更は新規許可数へ含めていない。\n",
    ]
    (OUT / "gate_diff_summary.md").write_text("".join(summary), encoding="utf-8")
    print(json.dumps({"previous_allowed": sorted(prev_allowed), "current_allowed": sorted(curr_allowed), "newly_allowed": new, "previous_only": sorted(prev_allowed - curr_allowed), "common": sorted(prev_allowed & curr_allowed)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
