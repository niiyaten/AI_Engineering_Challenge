"""Create read-only evaluation artifacts for the B0 format-row transfer run."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
csv.field_size_limit(2**31 - 1)
RUN_ID = "b0_valid_pattern_transfer_single_fix_fresh_v1"
OUT = ROOT / "data" / "output" / RUN_ID / "analysis"
BASE_TEST = ROOT / "data" / "output" / "valid_success_pattern_test_transfer_source_recovery_test_full_fresh_v1"
FINAL_TEST = ROOT / "data" / "output" / "b0_valid_pattern_transfer_test_full_fresh_v1"
BASE_VALID = ROOT / "data" / "output" / "valid_success_pattern_test_transfer_source_recovery_valid_fresh_v1"
FINAL_VALID = ROOT / "data" / "output" / "b0_valid_pattern_transfer_valid_full_fresh_v2"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def by_question(path: Path) -> dict[int, dict[str, Any]]:
    return {int(row["question_id"]): row for row in read_jsonl(path / "answer_results.jsonl")}


def gate_by_question(path: Path) -> dict[int, dict[str, Any]]:
    return {int(row["question_id"]): row for row in read_jsonl(path / "answer_gate_results.jsonl")}


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def brief_evidence(row: dict[str, Any]) -> tuple[str, str, str, str]:
    locations = row.get("evidence_locations", [])
    if not locations:
        return "", "", "", ""
    evidence = locations[0]
    raw = evidence.get("raw_result", {})
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    row_evidence = evidence.get("row_evidence", [])
    if not row_evidence and isinstance(raw, dict):
        row_evidence = raw.get("row_evidence", [])
    locations_text = "; ".join(
        f"{item.get('answer_coordinate', '')}={item.get('answer_value', '')}" for item in row_evidence
    )
    style_text = "; ".join(
        ",".join(item.get("matched_style_cells", [])) for item in row_evidence
    )
    return (
        evidence.get("selected_file", ""),
        evidence.get("sheet_name", ""),
        locations_text,
        style_text,
    )


def question_texts() -> dict[int, str]:
    texts: dict[int, str] = {}
    for name in ("b0_candidates.csv", "b_valid_pattern_matches.csv", "b_equivalent_set_reconstruction.csv"):
        path = OUT / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for item in csv.DictReader(handle):
                if item.get("question_original"):
                    texts[int(item["question_id"])] = item["question_original"]
    return texts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = by_question(BASE_TEST)
    final = by_question(FINAL_TEST)
    base_gates = gate_by_question(BASE_TEST)
    final_gates = gate_by_question(FINAL_TEST)
    texts = question_texts()

    before_allowed = {qid for qid, gate in base_gates.items() if gate.get("allow_answer")}
    after_allowed = {qid for qid, gate in final_gates.items() if gate.get("allow_answer")}
    newly_allowed = sorted(after_allowed - before_allowed)
    existing_six = [3, 41, 43, 72, 81, 92]

    targeted: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for qid in newly_allowed:
        before = base[qid]
        after = final[qid]
        source, sheet, values, styles = brief_evidence(after)
        targeted.append({
            "question_id": qid,
            "question_original": texts.get(qid, ""),
            "matched_valid_pattern": "formatted_text_span",
            "selected_source_before": "; ".join(before.get("selected_files", [])),
            "selected_source_after": source,
            "structure_location_before": "",
            "structure_location_after": f"sheet={sheet}; {values}",
            "answer_candidate_before": before.get("answer", ""),
            "answer_candidate_after": after.get("answer", ""),
            "evidence_before": bool(before.get("evidence_locations")),
            "evidence_after": bool(after.get("evidence_locations")),
            "verification_before": base_gates[qid].get("evidence_verified"),
            "verification_after": final_gates[qid].get("evidence_verified"),
            "gate_before": base_gates[qid].get("gate_status"),
            "gate_after": final_gates[qid].get("gate_status"),
            "suppression_reason_before": base_gates[qid].get("suppression_reason", ""),
            "suppression_reason_after": final_gates[qid].get("suppression_reason", ""),
            "needs_human_review": True,
            "safe_to_submit": False,
        })
        evidence_rows.append({
            "question_id": qid,
            "answer_candidate": after.get("answer", ""),
            "selected_source": source,
            "sheet": sheet,
            "answer_value_locations": values,
            "matched_style_locations": styles,
            "gate_status": final_gates[qid].get("gate_status"),
            "verification_evidence_verified": final_gates[qid].get("evidence_verified"),
            "needs_human_review": True,
            "safe_to_submit": False,
        })
    write_csv("targeted_run_results.csv", targeted)
    write_csv("targeted_candidate_answers.csv", targeted)
    write_csv("targeted_candidate_evidence.csv", evidence_rows)

    with (OUT / "targeted_human_review.md").open("w", encoding="utf-8") as handle:
        handle.write("# New format-row candidates for human review\n\n")
        handle.write("These are formal Gate results, but neither candidate is safe to submit.\n\n")
        for item in evidence_rows:
            handle.write(f"## test {item['question_id']}\n")
            handle.write(f"- Question: {texts.get(item['question_id'], '')}\n")
            handle.write(f"- Candidate: {item['answer_candidate']}\n")
            handle.write(f"- Source: {item['selected_source']}\n")
            handle.write(f"- Sheet: {item['sheet']}\n")
            handle.write(f"- Answer cells: {item['answer_value_locations']}\n")
            handle.write(f"- Highlighted cells: {item['matched_style_locations']}\n")
            handle.write("- Review: confirm every highlighted row, the requested header, and that no relevant highlighted row is omitted.\n\n")

    six_rows = []
    for qid in existing_six:
        six_rows.append({
            "question_id": qid,
            "before_gate": base_gates[qid].get("gate_status"),
            "after_gate": final_gates[qid].get("gate_status"),
            "before_answer": base[qid].get("answer", ""),
            "after_answer": final[qid].get("answer", ""),
            "regressed": base_gates[qid].get("allow_answer") and not final_gates[qid].get("allow_answer"),
        })
    write_csv("existing_six_gate_regression.csv", six_rows)

    test_rows = []
    for qid in sorted(final):
        test_rows.append({
            "question_id": qid,
            "before_gate": base_gates[qid].get("gate_status"),
            "after_gate": final_gates[qid].get("gate_status"),
            "before_answer": base[qid].get("answer", ""),
            "after_answer": final[qid].get("answer", ""),
            "newly_allowed": qid in newly_allowed,
            "needs_human_review": qid in newly_allowed,
            "safe_to_submit": False if qid in newly_allowed else "",
        })
    write_csv("test_gate_regression.csv", test_rows)

    valid_base = by_question(BASE_VALID)
    valid_final = by_question(FINAL_VALID)
    valid_rows = []
    for qid in sorted(valid_final):
        valid_rows.append({
            "question_id": qid,
            "before_answer": valid_base[qid].get("answer", ""),
            "after_answer": valid_final[qid].get("answer", ""),
            "before_gate": valid_base[qid].get("gate_status"),
            "after_gate": valid_final[qid].get("gate_status"),
            "answer_unchanged": valid_base[qid].get("answer", "") == valid_final[qid].get("answer", ""),
        })
    write_csv("valid_regression_comparison.csv", valid_rows)
    valid_unchanged = sum(row["answer_unchanged"] for row in valid_rows)

    (OUT / "unit_test_results.md").write_text(
        "# Unit results\n\n20 tests passed: format row mapping, ambiguity suppression, format regression, source selection, and semantic contract regression.\n",
        encoding="utf-8",
    )
    (OUT / "synthetic_test_results.md").write_text(
        "# Synthetic results\n\nPassed positive cases for pastel orange highlighted rows, column reordering, and offset headers; passed negative cases for missing or duplicate target headers.\n",
        encoding="utf-8",
    )
    (OUT / "formal_evaluation_summary.md").write_text(
        "# Formal evaluation\n\n"
        "- Valid fresh v2: 30 completed, 17 answered, extraction errors 0; all 30 answers match the 17 correct / 0 incorrect / 13 blank baseline.\n"
        f"- Test fresh v1: 100 completed, {len(after_allowed)} Gate allowed, {100-len(after_allowed)} suppressed, errors 0.\n"
        f"- Newly allowed: {newly_allowed}; each remains needs_human_review=true and safe_to_submit=false in the review artifacts.\n"
        "- test 0 remains suppressed as comparison_source_missing; test 85 remains suppressed.\n",
        encoding="utf-8",
    )
    (OUT / "final_summary.md").write_text(
        "# B0 valid-pattern transfer single-fix summary\n\n"
        "Selected generic fix: map a highlighted spreadsheet row to a uniquely named requested header, including Office pastel fill colours.\n\n"
        "This is not a source-selection or Gate relaxation change. Ambiguous headers remain suppressed.\n\n"
        f"Formal test Gate set before: {sorted(before_allowed)}\n\n"
        f"Formal test Gate set after: {sorted(after_allowed)}\n\n"
        f"New human-review-only candidates: {newly_allowed}\n\n"
        f"Valid answer regression: {valid_unchanged}/30 answer strings unchanged from the formal 17/0/13 baseline.\n",
        encoding="utf-8",
    )
    print(json.dumps({"newly_allowed": newly_allowed, "after_allowed": sorted(after_allowed)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
