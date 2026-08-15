"""Read-only re-audit of historic R3 labels against the Gate-15 runtime run."""

from __future__ import annotations

import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data/output/confirmed_gate_baseline_and_next_capability_v1/analysis"
RUN = ROOT / "data/output/gate15_no_human_review_test_fresh_v1"
OUT = ROOT / "data/output/r3_structure_resolver_audit_v1/analysis"
RAW_ROOT = ROOT / "data/raw"
PROCESSED_ROOT = ROOT / "data/processed"


def jsonl(path: Path) -> dict[int, dict]:
    return {int(row["question_id"]): row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if row}


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, object]]) -> None:
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def normalize_path(path: Path) -> str:
    return unicodedata.normalize("NFC", path.as_posix())


def project_from_source(source: str) -> str:
    parts = Path(source).parts
    try:
        return parts[parts.index("プロジェクト") + 1]
    except (ValueError, IndexError):
        return ""


def workbook_structure(source: str) -> dict:
    """Load existing extracted structure only; raw workbooks are never written."""
    raw_path = Path(source)
    if raw_path.suffix.lower() != ".xlsx":
        return {}
    if not raw_path.is_absolute():
        raw_path = ROOT / raw_path
    try:
        relative = raw_path.relative_to(RAW_ROOT)
    except ValueError:
        return {}
    target = normalize_path(PROCESSED_ROOT / (relative.as_posix() + ".structure.json"))
    candidates = [path for path in PROCESSED_ROOT.rglob("*.structure.json") if normalize_path(path) == target]
    if len(candidates) != 1:
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


# These are audit conclusions, not runtime routing rules. They separate stale R3
# labels from source-selection, calculation, and semantic blockers.
REAUDIT = {
    7: ("R5-source", "質問指定の基礎分析.pptxではなく提案書.pptxが選択されている", "source_selection"),
    8: ("R5-source", "データサイエンティスト調査資料ではなくスケジュール.xlsxが選択されている", "source_selection"),
    11: ("R5-source", "報告資料ではなくold提案書.pptxが選択されている", "source_selection"),
    12: ("R3-candidate", "指定DOCXの見出しからページ番号を決定するResolverがない", "heading_page_resolver"),
    16: ("R5-source", "中間報告資料ではなくスケジュール.xlsxが選択されている", "source_selection"),
    17: ("R5-source", "AYMのMM資料ではなく別案件のleaderboard.csvが選択されている", "source_selection"),
    25: ("R3-candidate", "色付きセルを含む小さな表領域と値列を一意に選択できない", "style_region_resolver"),
    30: ("R2-calculation", "標準化表現、平均比較、比率計算の仕様が不足している", "calculation_preprocessing_resolver"),
    31: ("R6-multi-source", "契約種別・契約金額・分析行数を跨いで結合する必要がある", "multi_source_join"),
    38: ("R6-policy-join", "APR規程と案件データを結合する必要がある", "policy_data_join"),
    46: ("R6-multi-source", "着手金とES内線は単一train.csvでは決定できない", "multi_source_join"),
    65: ("R11-ambiguous", "相関係数シートに静的な黄色セルを確認できず、条件付き書式か資料不整合の追加確認が必要", "conditional_format_investigation"),
    66: ("R5-source", "EDA可視化ではなくスケジュール.xlsxが選択されている", "source_selection"),
    71: ("R5-source", "会議録ではなくold提案書.pptxが選択されている", "source_selection"),
    80: ("R11-ambiguous", "質問指定のSheet2は空で、黄色セルはSheet1にのみ存在する", "sheet_content_disambiguation"),
    90: ("R11-ambiguous", "スケジュール表にバッファを示す明示値がなく、条件を構造化できない", "semantic_row_classification"),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    questions_path = next((ROOT / "data/raw/share/share").rglob("questions_test.csv"))
    questions = {int(row["index"]): row["question"] for row in csv_rows(questions_path)}
    historic = {int(row["question_id"]): row for row in csv_rows(BASELINE / "suppressed_90_classification.csv") if row["classification"] == "R3"}
    answers = jsonl(RUN / "answer_results.jsonl")
    gates = jsonl(RUN / "answer_gate_results.jsonl")
    traces = jsonl(RUN / "route_traces.jsonl")
    records = []
    for question_id in sorted(historic):
        answer, gate, trace = answers[question_id], gates[question_id], traces[question_id]
        source = next(iter(answer.get("selected_files", [])), "")
        classification, missing, resolver = REAUDIT[question_id]
        structure = workbook_structure(source)
        sheet_summary = []
        if structure:
            for sheet in structure.get("sheets", []):
                colored = [cell.get("coordinate", "") for cell in sheet.get("styled_cells", []) if cell.get("fill_color") not in {"", "00000000", "FFFFFFFF"}]
                sheet_summary.append({
                    "sheet": sheet.get("sheet_name", ""),
                    "state": sheet.get("sheet_state", ""),
                    "dimension": sheet.get("dimension", ""),
                    "merged_ranges": sheet.get("merged_ranges", []),
                    "hidden_rows": sheet.get("hidden_rows", []),
                    "hidden_columns": sheet.get("hidden_columns", []),
                    "colored_cells": colored[:20],
                })
        records.append({
            "question_id": question_id,
            "question_original": questions[question_id],
            "target_company": project_from_source(source),
            "selected_source": source,
            "file_type": Path(source).suffix.lower().lstrip("."),
            "selected_route": trace.get("selected_route", ""),
            "stopped_operation": "+".join(answer.get("operations_executed", [])),
            "first_failure_phase": answer.get("failure_stage", ""),
            "suppression_reason": gate.get("suppression_reason", ""),
            "current_evidence": json.dumps(answer.get("evidence_locations", []), ensure_ascii=False),
            "workbook_structure_summary": json.dumps(sheet_summary, ensure_ascii=False),
            "reaudited_classification": classification,
            "missing_structure_information": missing,
            "required_resolver_function": resolver,
            "implementation_difficulty": "small" if classification == "R3-candidate" else "not_resolver_only",
            "incorrect_answer_risk": "medium" if classification == "R3-candidate" else "high",
            "same_capability_questions": "25,65,80" if resolver == "style_region_resolver" else "",
            "priority_rank": "",
        })

    # Ranking favours source-correct, static, and deterministic structure.
    order = [25, 12, 65, 80, 90, 30, 46, 31, 38, 7, 8, 11, 16, 17, 66, 71]
    ranking = []
    by_id = {row["question_id"]: row for row in records}
    for rank, question_id in enumerate(order, start=1):
        row = dict(by_id[question_id])
        row["priority_rank"] = rank
        row["priority_score"] = max(1, 17 - rank)
        row["implementation_recommendation"] = (
            "design_only; only one fully deterministic question in this cluster"
            if question_id == 25
            else "do_not_implement_before_non_resolver_blocker_is_resolved"
        )
        ranking.append(row)
    write_csv("r3_suppression_audit.csv", records)
    write_csv("r3_priority_ranking.csv", ranking)

    clusters = [
        {"cluster_id": "C1", "cluster_name": "style_region_resolver", "question_ids": "25,65,80", "estimated_resolvable_count": 1, "required_files": "table_executor.py, extractors.py", "reuse": "styled_cells, merged_ranges, table evidence", "unit_tests": "region selection, colored cell selection, ambiguity suppression", "gate_conditions": "one region, one color condition, reproducible value mapping", "incorrect_answer_risk": "high for 65/80", "implementation_size": "small to medium", "recommendation": "not yet: only 25 is fully deterministic"},
        {"cluster_id": "C2", "cluster_name": "heading_page_resolver", "question_ids": "12", "estimated_resolvable_count": 1, "required_files": "document_executor.py, extractors.py", "reuse": "DOCX heading paragraphs", "unit_tests": "unique heading, missing heading, duplicate heading", "gate_conditions": "unique heading and reproducible page mapping", "incorrect_answer_risk": "medium", "implementation_size": "small", "recommendation": "single question; defer"},
        {"cluster_id": "C3", "cluster_name": "column_semantic_resolver", "question_ids": "30,46,90", "estimated_resolvable_count": 0, "required_files": "table_executor.py, calculation_engine.py", "reuse": "normalized headers and table filters", "unit_tests": "synonym candidates and ambiguity suppression", "gate_conditions": "all semantic conditions map uniquely", "incorrect_answer_risk": "high", "implementation_size": "medium", "recommendation": "blocked by preprocessing, multi-source, or semantic condition gaps"},
        {"cluster_id": "C4", "cluster_name": "source_route_correction", "question_ids": "7,8,11,16,17,66,71", "estimated_resolvable_count": 0, "required_files": "source_selection.py, route_registry.py", "reuse": "candidate source inventory", "unit_tests": "named document and role matching", "gate_conditions": "required source selected uniquely", "incorrect_answer_risk": "high", "implementation_size": "out of scope", "recommendation": "not a Resolver-only change"},
        {"cluster_id": "C5", "cluster_name": "multi_source_relation_resolver", "question_ids": "31,38,46", "estimated_resolvable_count": 0, "required_files": "source_requirements.py, calculation_engine.py", "reuse": "source relation spec", "unit_tests": "entity join and missing-source suppression", "gate_conditions": "all source roles and joins proven", "incorrect_answer_risk": "high", "implementation_size": "medium or larger", "recommendation": "out of scope"},
        {"cluster_id": "C6", "cluster_name": "structure_ambiguity_audit", "question_ids": "65,80,90", "estimated_resolvable_count": 0, "required_files": "extractors.py", "reuse": "sheet state, styles, row text", "unit_tests": "blank named sheet and missing semantic marker", "gate_conditions": "no contradiction between question and raw structure", "incorrect_answer_risk": "high", "implementation_size": "small", "recommendation": "audit only; it cannot create a safe answer"},
    ]
    write_csv("r3_capability_clusters.csv", clusters)

    expected_evidence = {
        "source_file": "",
        "worksheet": "",
        "candidate_regions": [],
        "selected_region": None,
        "region_selection_reason": "",
        "header_candidates": [],
        "selected_header_rows": [],
        "normalized_headers": [],
        "column_candidates": [],
        "selected_column": None,
        "row_candidates": [],
        "selected_row": None,
        "relative_position_operations": [],
        "excluded_candidates": [],
        "ambiguity_score": 1.0,
        "confidence": 0.0,
        "gate_allowed": False,
        "gate_reason": "design_only",
    }
    evidence_dir = OUT / "expected_evidence"
    evidence_dir.mkdir(exist_ok=True)
    for question_id in (12, 25, 65, 80, 90):
        evidence = dict(expected_evidence)
        evidence["question_id"] = question_id
        evidence["source_file"] = by_id[question_id]["selected_source"]
        evidence["candidate_regions"] = json.loads(by_id[question_id]["workbook_structure_summary"] or "[]")
        evidence["gate_reason"] = "requires_unique_structure_and_non_resolver blockers to be resolved"
        (evidence_dir / f"test_{question_id:03d}_expected_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    (OUT / "selected_cluster_design.md").write_text(
        "# Selected Resolver Capability\n\n"
        "## Decision\n\n"
        "No R3 cluster is implemented in this run. The requirement that one small capability"
        " safely cover at least two questions is not met after current-source verification.\n\n"
        "## First future candidate\n\n"
        "`style_region_resolver` is the nearest candidate: it would resolve a unique small styled"
        " Excel region before delegating aggregation to the existing table executor. However, only"
        " test 25 currently has a static, source-consistent colored-cell region. Test 65 has no"
        " static yellow cell, and test 80 names an empty Sheet2 while the colored cell is on Sheet1."
        " Implementing it now would violate the two-question and ambiguity-suppression criteria.\n\n"
        "## Expected Evidence\n\n"
        "A future resolver must retain source_file, worksheet, all candidate_regions, selected_region,"
        " normalized headers, column and row candidates, excluded candidates, ambiguity score, and"
        " Gate reason. It must suppress when a named sheet is empty or color exists only through an"
        " unresolved conditional-format rule.\n",
        encoding="utf-8",
    )
    (OUT / "selected_cluster_test_plan.md").write_text(
        "# Unit Test Plan\n\n"
        "- Select a unique colored subregion regardless of row and column order.\n"
        "- Preserve merged-cell and hidden-sheet metadata.\n"
        "- Reject multiple same-scoring regions.\n"
        "- Reject a question-named sheet with no cells.\n"
        "- Reject colors that require unresolved conditional formatting.\n"
        "- Preserve selected and excluded candidates in Evidence.\n"
        "- Run the full Unit suite, valid fresh, test fresh, and exact Gate-15 regression after any implementation.\n",
        encoding="utf-8",
    )
    counts = Counter(row["reaudited_classification"] for row in records)
    (OUT / "implementation_report.md").write_text(
        "# R3 Resolver Audit Report\n\n"
        f"- Historic R3 labels audited: {len(records)}\n"
        f"- Re-audit counts: {dict(counts)}\n"
        "- Runtime changes: none\n"
        "- New Gate candidates: none\n"
        "- Regression runs: not required because no runtime code changed\n"
        "- Formal Gate-15 baseline: unchanged\n",
        encoding="utf-8",
    )
    print(json.dumps({"r3_historic_count": len(records), "counts": counts, "output": str(OUT)}, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
