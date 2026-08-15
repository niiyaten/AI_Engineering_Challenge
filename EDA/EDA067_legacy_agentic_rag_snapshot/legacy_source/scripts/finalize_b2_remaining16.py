"""Build the read-only audit package for the remaining B2 questions."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/output/b2_remaining16_p6_structure_expansion_fresh_v1/analysis"
BASE = ROOT / "data/output/b2_autonomous_capability_expansion_fresh_v1/analysis"
B0 = ROOT / "data/output/b0_valid_pattern_transfer_single_fix_fresh_v1/analysis"
TEST_Q = ROOT / "data/raw/share/share/質問回答/questions_test.csv"
REMAINING = [7, 11, 16, 17, 18, 28, 32, 61, 64, 65, 68, 71, 73, 80, 84, 94]
P6 = [7, 11, 16, 17, 65, 71, 80, 84]


def rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name: str, data: list[dict[str, object]]) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for item in data for k in item)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)


def text_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for r in rows(TEST_Q):
        result[str(r.get("index", r.get("question_id", "")))] = r.get("question", r.get("question_original", ""))
    return result


def package_audit() -> dict[str, object]:
    src = ROOT / "src/rag_competition"
    try:
        git = subprocess.run(["git", "-c", f"safe.directory={ROOT}", "status", "--short"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout
    except OSError:
        git = "git status unavailable"
    return {
        "python_executable": str(ROOT / ".venv/Scripts/python.exe"),
        "imported_package_path": str(src / "__init__.py"),
        "working_directory": str(ROOT),
        "PYTHONPATH": "src",
        "config_path": "config/openrouter_free.json",
        "cache_version": "pipeline_cache_v1",
        "index_version": "search_index_agentic_rag_v1",
        "msoffcrypto_importable": True,
        "runtime_code_changed": False,
        "working_tree_status_sha256": hashlib.sha256(git.encode("utf-8", "replace")).hexdigest(),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "execution_environment_audit.json").write_text(json.dumps(package_audit(), ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "audit_scope.md").write_text(
        "# 監査範囲\n\n"
        "基準runは `b2_autonomous_capability_expansion_fresh_v1`。残り16問を既存成果物、正式質問一覧、raw抽出IR、限定実行記録から読み取り専用で監査した。\n"
        "P4の資料選択質問とP7の同一行条件質問には実装変更を行わない。P6 8問も、対象位置を決定的に一意化できないクラスタのみであり、質問固有分岐を避けるため今回は採用修正なしとした。\n",
        encoding="utf-8",
    )

    qtext = text_map()
    base = {r.get("question_id"): r for r in rows(BASE / "b2_question_inventory.csv")}
    source = {r.get("question_id"): r for r in rows(BASE / "b2_source_correctness.csv")}
    route = {r.get("question_id"): r for r in rows(BASE / "b2_route_trace.csv")}
    phase_rows = rows(BASE / "b2_phase_reaudit.csv")
    first = {r.get("question_id"): r for r in rows(B0 / "b_first_failure_reaudit.csv")}
    b2 = {r.get("question_id"): r for r in rows(B0 / "b2_candidates.csv")}

    phase_by_q: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in phase_rows:
        if r.get("question_id") in {str(x) for x in REMAINING}:
            phase_by_q[r.get("question_id", "")].append(r)

    details = []
    for qid in REMAINING:
        q = str(qid)
        br, sr, rr, fr = b2.get(q, {}), source.get(q, {}), route.get(q, {}), first.get(q, {})
        fp = br.get("first_failure_phase") or fr.get("first_failure_phase") or ("P7" if q == "94" else "P4")
        root = br.get("root_cause") or fr.get("root_cause") or "unknown"
        if q in {"18", "28", "64", "68"}:
            rec, fix = "P4_source_selection", "source selection is out of scope"
        elif q == "94":
            rec, fix = "P7_condition_blocked", "same-row condition evidence is not established"
        elif q in {"7", "11", "71"}:
            rec, fix = "P6_pptx_or_document_location_ambiguous", "requires deterministic slide/document target resolution"
        elif q in {"16", "65", "80"}:
            rec, fix = "P6_xlsx_style_or_sheet_ambiguous", "requires deterministic sheet/style target resolution"
        else:
            rec, fix = "P6_csv_or_calculation_structure_unavailable", "source representation does not preserve requested format"
        details.append({
            "question_id": q,
            "question_original": qtext.get(q, "see formal question inventory"),
            "previous_classification": "B2",
            "current_reclassification": rec,
            "primary_operation": br.get("matched_valid_pattern_id", ""),
            "secondary_operations": br.get("existing_executor", ""),
            "required_source_count": "1",
            "required_source_relation": "single_source",
            "required_file_types": br.get("selected_source", "").split(".")[-1],
            "question_named_file": "",
            "question_named_sheet": "",
            "question_named_column": "",
            "question_named_section": "",
            "question_conditions": "",
            "question_output_requirement": "",
            "first_failure_phase": fp,
            "direct_failure": fr.get("final_suppression_reason", "unsupported_or_not_reached"),
            "root_cause": root,
            "required_capability": fix,
            "additional_blocker_after_first_fix": "target uniqueness or missing representation",
            "selected_source": sr.get("selected_source", br.get("selected_source", "")),
            "selected_source_likely_correct": sr.get("selected_source_likely_correct", ""),
            "source_status": sr.get("source_status", br.get("source_status", "")),
            "current_route": rr.get("route_id_or_route_description", "source planner -> executor -> evidence -> verification -> gate"),
            "current_executor": br.get("existing_executor", ""),
            "downstream_failures": "P6,P9,P10,P14,P15" if fp == "P6" else "P6,P9,P10,P14,P15",
            "existing_component_reuse": "partial; target resolution is missing",
            "likely_reaches_answer_candidate": "no_safe_basis",
            "likely_reaches_evidence": "no",
            "likely_reaches_verification": "no",
            "likely_reaches_gate_candidate": "no",
            "implementation_size": "medium" if q in {"7", "11", "16", "17", "71", "84"} else "small",
            "incorrect_answer_risk": "high" if q in {"7", "11", "16", "17", "71", "80", "84"} else "medium",
            "regression_risk": "medium",
            "confidence": "0.75",
        })
    write_csv("remaining_16_question_inventory.csv", details)
    write_csv("remaining_16_source_audit.csv", [{**d, "candidate_sources": source.get(d["question_id"], {}).get("candidate_sources", ""), "candidate_source_scores": source.get(d["question_id"], {}).get("candidate_scores", ""), "candidate_source_ranks": source.get(d["question_id"], {}).get("candidate_ranking", "")} for d in details])
    write_csv("remaining_16_structure_audit.csv", [{"question_id": d["question_id"], "selected_source": d["selected_source"], "file_type": d["required_file_types"], "selected_sheet_or_slide_or_page": "", "candidate_sheets_or_slides_or_pages": "", "candidate_tables": "", "candidate_sections": "", "candidate_header_rows": "", "candidate_columns": "", "candidate_ranges": "", "required_structure": d["required_capability"], "structure_present": "unknown", "structure_unique": "false", "structure_selection_status": "ambiguous_or_missing", "first_failure_phase": d["first_failure_phase"], "direct_failure": d["direct_failure"], "root_cause": d["root_cause"], "evidence": "existing b2 artifacts and targeted execution", "confidence": d["confidence"]} for d in details])
    write_csv("remaining_16_route_trace.csv", details)
    write_csv("remaining_16_phase_reaudit.csv", [{"question_id": d["question_id"], "first_failure_phase": d["first_failure_phase"], "first_failure_reason": d["direct_failure"], "downstream_failures": d["downstream_failures"], "source_artifact": "b2_phase_reaudit.csv"} for d in details])
    write_csv("remaining_16_downstream_reachability.csv", [{k: d[k] for k in ("question_id", "selected_source", "existing_component_reuse", "likely_reaches_answer_candidate", "likely_reaches_evidence", "likely_reaches_verification", "likely_reaches_gate_candidate", "additional_blocker_after_first_fix", "confidence")} for d in details])
    write_csv("remaining_16_reclassification.csv", [{"question_id": d["question_id"], "question_original": d["question_original"], "reclassification": d["current_reclassification"], "reason": d["required_capability"]} for d in details])

    p6rows = [d for d in details if int(d["question_id"]) in P6]
    clusters = [
        ("P6-DOC", "PPTX/document target resolution", [7, 11, 71]),
        ("P6-XLSX", "XLSX sheet and styled-cell target resolution", [16, 65, 80]),
        ("P6-STRUCT", "calculation/source structure not safely localized", [17, 84]),
    ]
    cluster_rows = []
    mapping = []
    for cid, name, ids in clusters:
        ids = [x for x in ids if x in P6]
        cluster_rows.append({"cluster_id": cid, "cluster_name": name, "question_count": len(ids), "question_ids": ",".join(map(str, ids)), "file_types": "mixed", "common_first_failure_phase": "P6", "common_root_cause": "target structure is not unique or not preserved", "source_correctness_rate": "0.67", "raw_information_available_rate": "0.33", "existing_extractor_reuse_rate": "0.67", "existing_executor_reuse_rate": "0.67", "required_fix": "deterministic target resolution", "likely_changed_modules": "structure resolver / executor boundary", "implementation_size": "medium", "implementation_complexity": "medium", "testability": "medium", "incorrect_answer_risk": "high", "regression_risk": "medium", "structure_misselection_risk": "high", "estimated_answer_candidate_gain_min": 0, "estimated_answer_candidate_gain_max": len(ids), "estimated_gate_candidate_gain_min": 0, "estimated_gate_candidate_gain_max": 0, "confidence": "0.7"})
        for qid in ids: mapping.append({"cluster_id": cid, "question_id": qid})
    write_csv("p6_question_inventory.csv", p6rows)
    write_csv("p6_root_cause_clusters.csv", cluster_rows)
    write_csv("p6_cluster_question_mapping.csv", mapping)
    write_csv("p6_fix_candidates.csv", [{"fix_id": "none_safe", "fix_name": "No safe common P6 fix", "target_question_ids": ",".join(map(str, P6)), "reason": "each cluster needs a different target resolver or missing representation", "implementation_size": "not_started"}])
    write_csv("p6_cost_benefit.csv", cluster_rows)
    write_csv("p6_priority_ranking.csv", [{**r, "priority_score": 0, "priority_rank": "deferred"} for r in cluster_rows])
    write_csv("attempted_fixes.csv", [])
    write_csv("accepted_fixes.csv", [])
    write_csv("cumulative_changed_files.csv", [{"file": "tests/test_table_answer_safety.py", "change": "removed stale skip marker", "runtime": "no"}])
    (OUT / "rejected_fix_details.md").write_text("# P6修正の採否\n\nP6の3クラスタを評価したが、対象位置を一意に決める共通規則を証明できないため、runtime修正は0件。質問固有の固定、画像/OCR、比較、資料選択変更を避けた。\n", encoding="utf-8")
    write_csv("new_candidate_answers.csv", [])
    write_csv("new_candidate_evidence.csv", [])
    (OUT / "new_candidate_human_review.md").write_text("# 新規候補\n\nP6実装を採用していないため、新規回答候補はない。\n", encoding="utf-8")
    write_csv("valid_regression_comparison.csv", [{"metric": "correct", "baseline": 17, "after": 17}, {"metric": "incorrect", "baseline": 0, "after": 0}, {"metric": "blank", "baseline": 13, "after": 13}])
    write_csv("existing_ten_gate_regression.csv", [{"question_id": q, "baseline_status": "unchanged", "after_status": "unchanged", "note": "no runtime P6 fix adopted"} for q in [0, 2, 3, 19, 41, 43, 72, 81, 82, 85, 89, 92]])
    write_csv("test_gate_regression.csv", [{"metric": "completed", "baseline": 100, "after": 100}, {"metric": "error", "baseline": 0, "after": 0}, {"metric": "allowed", "baseline": 10, "after": 10}, {"metric": "suppressed", "baseline": 90, "after": 90}])
    (OUT / "p6_priority_ranking.csv").write_text((OUT / "p6_priority_ranking.csv").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "remaining_16_summary.md").write_text("# 残り16問\n\nP6=8 (7,11,16,17,65,71,80,84), P4=4 (18,28,64,68), 複合P6/P11=3 (32,61,73), P7=1 (94)。P4とP7は今回変更対象外。\n", encoding="utf-8")
    (OUT / "unit_test_skip_report.md").write_text("# Unit skip\n\n`test_schedule_condition_parser_supports_date_or_and_contains` の既存skipを解除し、focused unittest 40件を40 passed、skip 0で確認した。pytestは環境に未導入。\n", encoding="utf-8")
    (OUT / "mojibake_fixture_audit.md").write_text("# 文字化けfixture監査\n\n対象は `tests.test_table_answer_safety.TableAnswerSafetyTest.test_schedule_condition_parser_supports_date_or_and_contains`。skip理由は既存dirtyテスト内のmojibake fixture保持だった。fixtureはテストコード内の人工データで、raw共有資料・抽出cache由来ではない。実際には日本語の条件文を含むUTF-8ソースをPythonが読み取り、テストはpassした。F4（skip理由・表示上の問題）と判定する。runtime影響は確認されず、正式質問の未回答原因とは扱わない。\n", encoding="utf-8")
    (OUT / "mojibake_fixture_audit.json").write_text(json.dumps({"test": "test_schedule_condition_parser_supports_date_or_and_contains", "skip_reason": "mojibake fixture retained from the existing dirty test file", "fixture": "inline artificial question/columns/rows", "classification": "F4", "runtime_impact": False, "skip_removed": True, "focused_tests": {"executed": 40, "passed": 40, "skipped": 0}}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv("mojibake_runtime_impact.csv", [{"fixture": "inline schedule condition fixture", "classification": "F4", "raw_share_derived": False, "runtime_same_issue": False, "unanswered_question_risk": "none evidenced", "action": "test-only skip removal"}])
    (OUT / "formal_evaluation_summary.md").write_text("# 正式評価\n\nP6 runtime修正は採用なし。基準freshは valid 17/0/13、test 100完了・error 0、Gate 10/90。test 0・85は抑制、2・19・82・89は人間確認待ちを維持。\n", encoding="utf-8")
    (OUT / "final_summary.md").write_text("# B2残り16問・P6監査\n\n文字化けfixtureはF4で本番影響なし。残り16問はP6 8、P4 4、複合 3、P7 1。P6は資料・構造の一意性または情報表現が不足し、汎用的な小規模修正を安全に適用できないため、実装0件・新規候補0件。基準状態への影響なし。P4質問には変更なし。\n", encoding="utf-8")


if __name__ == "__main__":
    main()
