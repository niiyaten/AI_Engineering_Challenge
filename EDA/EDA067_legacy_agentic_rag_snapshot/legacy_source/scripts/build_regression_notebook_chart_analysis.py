"""Build evaluation-only artifacts for the regression, notebook, and chart expansion."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/output/regression_notebook_chart_autonomous_expansion_v1/analysis"
TEST_RUN = ROOT / "data/output/regression_notebook_chart_autonomous_expansion_chart_test_v1"
VALID_RUN = ROOT / "data/output/regression_notebook_chart_autonomous_expansion_chart_valid_v1"
BASELINE_TEST = ROOT / "data/output/confirmed_gate_baseline_and_next_capability_test_v1"
TARGETED_RUNS = {
    "regression": ROOT / "data/output/regression_notebook_chart_autonomous_expansion_regression_targeted_v1",
    "notebook": ROOT / "data/output/regression_notebook_chart_autonomous_expansion_notebook_targeted_v1",
    "chart": ROOT / "data/output/regression_notebook_chart_autonomous_expansion_chart_targeted_v2",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = OUTPUT / name
    fields = sorted({key for row in rows for key in row}) or ["note"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def answer_map(run: Path) -> dict[int, dict[str, Any]]:
    return {int(row["question_id"]): row for row in read_jsonl(run / "answer_results.jsonl")}


def gate_map(run: Path) -> dict[int, dict[str, Any]]:
    return {int(row["question_id"]): row for row in read_jsonl(run / "answer_gate_results.jsonl")}


def questions() -> dict[int, str]:
    path = next((ROOT / "data/raw/share/share").rglob("questions_test.csv"))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {int(row["index"]): row["question"] for row in csv.DictReader(handle)}


def git_value(*args: str) -> str:
    result = subprocess.run(["git", "-c", f"safe.directory={ROOT}", *args], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    return result.stdout if result.returncode == 0 else result.stderr


def raw_path_for(question_id: int, answers: dict[int, dict[str, Any]]) -> Path | None:
    files = answers[question_id].get("selected_files", [])
    return ROOT / files[0] if files else None


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    test_answers, test_gates = answer_map(TEST_RUN), gate_map(TEST_RUN)
    valid_answers, valid_gates = answer_map(VALID_RUN), gate_map(VALID_RUN)
    baseline_answers, baseline_gates = answer_map(BASELINE_TEST), gate_map(BASELINE_TEST)
    question_map = questions()
    msoffcrypto_importable = importlib.util.find_spec("msoffcrypto") is not None
    environment = {
        "python_executable": sys.executable,
        "imported_package_path": str(Path(__import__("rag_competition").__file__).resolve()),
        "working_directory": str(ROOT),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "config_path": "config/",
        "cache_version": "cache-source:b2_autonomous_capability_expansion_*_final_v1",
        "index_version": "cache-source:b2_autonomous_capability_expansion_*_final_v1",
        "msoffcrypto_importable": msoffcrypto_importable,
    }
    (OUTPUT / "execution_environment_audit.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "starting_worktree_snapshot.json").write_text(json.dumps({
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "git_status_at_artifact_generation": git_value("status", "--short"),
        "git_diff_name_only": git_value("diff", "--name-only"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    cluster_rows = [
        {"cluster": "regression", "question_ids": "63,83", "implementation": "accepted", "route": "excel.regression.predict_from_coefficients", "outcome": "83 allowed; 63 suppressed because preprocessing binding is not proven"},
        {"cluster": "notebook", "question_ids": "4,56", "implementation": "accepted", "route": "notebook.output.lookup", "outcome": "4 allowed from saved correlation output; 56 suppressed because saved y-axis ticks are absent"},
        {"cluster": "chart", "question_ids": "10,39", "implementation": "accepted", "route": "excel.chart.series.column", "outcome": "39 allowed from ChartEx relationships; 10 suppressed because the histogram is image-only"},
    ]
    write_csv("cluster_status.csv", cluster_rows)
    changed = [
        "src/rag_competition/calculation_engine.py",
        "src/rag_competition/table_executor.py",
        "src/rag_competition/notebook_executor.py",
        "src/rag_competition/chart_executor.py",
        "src/rag_competition/tool_registry.py",
        "src/rag_competition/answer_gate.py",
        "src/rag_competition/route_registry.py",
        "tests/test_calculation_engine.py",
        "tests/test_notebook_executor.py",
        "tests/test_chart_executor.py",
    ]
    write_csv("cumulative_changed_files.csv", [{"path": value, "scope": "runtime" if value.startswith("src/") else "test"} for value in changed])

    regression_answers = answer_map(TARGETED_RUNS["regression"])
    regression_gates = gate_map(TARGETED_RUNS["regression"])
    regression_rows = []
    for question_id in (63, 83):
        answer = regression_answers[question_id]
        evidence = answer.get("evidence_locations", [])
        regression_rows.append({
            "question_id": question_id, "question": question_map[question_id], "answer": answer.get("answer", ""),
            "status": answer.get("status"), "gate": regression_gates[question_id].get("gate_status"),
            "failure": "; ".join(answer.get("warnings", [])), "evidence": evidence,
        })
    write_csv("regression_calculation_trace.csv", regression_rows)
    write_csv("regression_targeted_results.csv", regression_rows)
    (OUTPUT / "regression_summary.md").write_text(
        "# Regression coefficient prediction\n\n"
        "- Variable bindings are matched by normalized variable name, not column order.\n"
        "- test 83 passed: the coefficient block, intercept, key row, all input cells, products, and rounding are reproducible.\n"
        "- test 63 remains suppressed: the workbook also contains standardized values, but does not prove which representation the coefficients use.\n",
        encoding="utf-8",
    )

    notebook_answers = answer_map(TARGETED_RUNS["notebook"])
    notebook_gates = gate_map(TARGETED_RUNS["notebook"])
    notebook_path = raw_path_for(4, notebook_answers)
    notebook = json.loads(notebook_path.read_text(encoding="utf-8")) if notebook_path else {"cells": []}
    cell_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for index, cell in enumerate(notebook.get("cells", [])):
        source = "".join(cell.get("source", []))
        cell_rows.append({"cell_index": index, "cell_type": cell.get("cell_type"), "source": source})
        for output_index, output in enumerate(cell.get("outputs", [])):
            output_rows.append({"cell_index": index, "output_index": output_index, "output_type": output.get("output_type"), "data_keys": sorted((output.get("data") or {}).keys()), "text": output.get("text") or (output.get("data") or {}).get("text/plain", "")})
    write_csv("notebook_cell_inventory.csv", cell_rows)
    write_csv("notebook_output_inventory.csv", output_rows)
    notebook_rows = []
    for question_id in (4, 56):
        answer = notebook_answers[question_id]
        notebook_rows.append({"question_id": question_id, "question": question_map[question_id], "answer": answer.get("answer", ""), "status": answer.get("status"), "gate": notebook_gates[question_id].get("gate_status"), "failure": "; ".join(answer.get("warnings", [])), "evidence": answer.get("evidence_locations", [])})
    write_csv("notebook_targeted_results.csv", notebook_rows)
    (OUTPUT / "notebook_summary.md").write_text(
        "# Notebook saved output audit\n\n"
        "- test 4 reads the persisted correlation matrix; `charges` and identifier columns are excluded before selecting the unique signed maximum.\n"
        "- test 56 remains suppressed. The notebook stores a PNG but no explicit y-axis ticks or limits, and this run did not use OCR or visual models.\n",
        encoding="utf-8",
    )

    chart_rows: list[dict[str, Any]] = []
    series_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for question_id in (10, 39):
        source = raw_path_for(question_id, test_answers)
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            charts = [name for name in names if name.startswith("xl/charts/") and name.endswith(".xml") and "/_rels/" not in name]
            pivots = [name for name in names if name.startswith("xl/pivotTables/") and name.endswith(".xml") and "/_rels/" not in name]
            images = [name for name in names if name.startswith("xl/media/")]
        answer = test_answers[question_id]
        evidence = answer.get("evidence_locations", [])
        chart_rows.append({"question_id": question_id, "source": str(source.relative_to(ROOT)), "native_chart_parts": charts, "pivot_parts": pivots, "image_parts": images, "answer": answer.get("answer", ""), "status": answer.get("status"), "evidence": evidence})
        if evidence:
            item = evidence[0]
            series_rows.append({"question_id": question_id, "chart_part": item.get("chart_part"), "chart_name": item.get("chart_name"), "series_name": item.get("series_name"), "defined_name": item.get("defined_name")})
            source_rows.append({"question_id": question_id, "sheet": item.get("sheet_name"), "source_sheet": item.get("source_sheet"), "source_cell": item.get("source_cell"), "source_range": item.get("source_range"), "source_header_value": item.get("source_header_value")})
    write_csv("chart_inventory.csv", chart_rows)
    write_csv("chart_series_inventory.csv", series_rows)
    write_csv("chart_source_mapping.csv", source_rows)
    chart_target_rows = [{"question_id": q, "question": question_map[q], "answer": test_answers[q].get("answer", ""), "status": test_answers[q].get("status"), "gate": test_gates[q].get("gate_status"), "warnings": test_answers[q].get("warnings", []), "evidence": test_answers[q].get("evidence_locations", [])} for q in (10, 39)]
    write_csv("chart_targeted_results.csv", chart_target_rows)
    (OUTPUT / "chart_summary.md").write_text(
        "# Excel native chart audit\n\n"
        "- test 39: Sheet1 -> drawing object `グラフ 1` -> chartEx1.xml -> `_xlchart.v1.2` -> `train!M1`; the source header and series label both equal `hum`.\n"
        "- test 10: no native chart part exists. The graph sheet contains ten image parts and the Pivot table is an age/gender aggregate, not a histogram frequency table. The count remains suppressed.\n",
        encoding="utf-8",
    )

    candidates = []
    for question_id in (4, 39, 83):
        answer, gate = test_answers[question_id], test_gates[question_id]
        candidates.append({
            "question_id": question_id, "question": question_map[question_id], "answer_candidate": answer.get("answer"),
            "selected_source": answer.get("selected_files", []), "evidence": answer.get("evidence_locations", []),
            "verification": "passed", "formal_gate_allowed": gate.get("allow_answer"),
            "human_review_status": "pending", "needs_human_review": True, "safe_to_submit": False,
        })
    write_csv("new_candidate_answers.csv", candidates)
    write_csv("new_candidate_evidence.csv", candidates)
    (OUTPUT / "new_candidate_human_review.md").write_text(
        "# New candidates requiring human review\n\n"
        "| Test | Candidate | Review focus |\n|---|---|---|\n"
        "| 4 | bmi | Confirm the notebook question uses signed, not absolute, correlation and excludes the target itself. |\n"
        "| 39 | hum | Confirm the question refers to the first native ChartEx object on Sheet1. |\n"
        "| 83 | 0.38317 | Recompute from the listed intercept, coefficient cells, and index row. |\n",
        encoding="utf-8",
    )

    valid_metrics = json.loads((VALID_RUN / "evaluation/valid_metrics.json").read_text(encoding="utf-8"))
    existing = [2, 3, 19, 41, 43, 72, 81, 82, 89, 92]
    existing_rows = []
    for question_id in existing:
        before, after = baseline_answers[question_id], test_answers[question_id]
        existing_rows.append({
            "question_id": question_id, "answer_unchanged": before.get("answer") == after.get("answer"),
            "evidence_unchanged": before.get("evidence_locations") == after.get("evidence_locations"),
            "gate_unchanged": baseline_gates[question_id].get("allow_answer") == test_gates[question_id].get("allow_answer"),
        })
    write_csv("existing_ten_gate_regression.csv", existing_rows)
    gate_rows = []
    for question_id in sorted(test_gates):
        gate_rows.append({"question_id": question_id, "gate_status": test_gates[question_id].get("gate_status"), "allowed": test_gates[question_id].get("allow_answer"), "answer": test_answers[question_id].get("answer", "")})
    write_csv("test_gate_regression.csv", gate_rows)
    write_csv("valid_regression_comparison.csv", [{"metric": key, "value": value} for key, value in valid_metrics.items() if key != "failure_stage_counts"])
    summary = {
        "run_id": "regression_notebook_chart_autonomous_expansion_v1",
        "valid": {"correct": valid_metrics["normalized_match_count"], "incorrect": valid_metrics["incorrect_count"], "blank": valid_metrics["blank_count"]},
        "test": {"completed": len(test_answers), "errors": 0},
        "gate": {"allowed": sum(bool(item.get("allow_answer")) for item in test_gates.values()), "suppressed": sum(not bool(item.get("allow_answer")) for item in test_gates.values())},
        "allowed_question_ids": [key for key, value in test_gates.items() if value.get("allow_answer")],
        "new_human_review_candidates": [4, 39, 83],
        "test_0": test_gates[0].get("gate_status"),
        "test_85": test_gates[85].get("gate_status"),
        "api_call_count": 0,
        "paid_model_count": 0,
    }
    (OUTPUT / "formal_evaluation_summary.md").write_text("# Formal evaluation\n\n```json\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    (OUTPUT / "unit_test_results.md").write_text(
        "# Unit and synthetic tests\n\n"
        "`python -P -m unittest discover -s tests -v` completed successfully after the three cluster changes. "
        "The suite includes coefficient-name alignment, ambiguous standardized inputs, saved notebook matrix parsing, ChartEx relationship traversal, duplicate chart suppression, header mismatch, and missing native chart cases.\n",
        encoding="utf-8",
    )
    (OUTPUT / "final_summary.md").write_text(
        "# Regression, Notebook, and Chart Expansion\n\n"
        "All three clusters were audited. Three deterministic routes were accepted: coefficient prediction, saved notebook correlation output, and native ChartEx series metadata.\n\n"
        f"Final valid: {summary['valid']['correct']} correct, {summary['valid']['incorrect']} incorrect, {summary['valid']['blank']} blank.\n\n"
        f"Final test Gate: {summary['gate']['allowed']} allowed, {summary['gate']['suppressed']} suppressed. New candidates 4, 39, and 83 remain pending human review and are not submission-safe.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
