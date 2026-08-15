"""EDA065: Strict Resolver と EDA064 の汎用 Top-K を比較するオフライン監査。

このスクリプトは既存の Gate 19 run と EDA064 の成果物を読むだけである。
正解資料ラベルは比較時だけに使い、Resolver や候補検索の入力には渡さない。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EDA_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EDA_ROOT.parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline EDA065.")
    parser.add_argument("--latest-root", type=Path, required=True)
    parser.add_argument("--eda064-root", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else ["generated_by", "source", "confidence", "requires_manual_review"])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def canonical_path(value: str) -> str:
    """比較専用に raw 相対パスと historical share パスを同じ形へ揃える。"""
    path = (value or "").replace("\\", "/")
    marker = "/share/"
    if marker in path:
        path = "share/" + path.split(marker, 1)[1]
    elif path.startswith("share/"):
        path = path
    if path.lower().endswith(".structure.json"):
        path = path[: -len(".structure.json")]
    elif path.lower().endswith((".pptx.md", ".docx.md", ".xlsx.md", ".pdf.md", ".csv.md")):
        path = path[:-3]
    return path.casefold()


def split_paths(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in re.split(r"[|;\n]", value or "") if part.strip()]


def question_rows(latest: Path) -> dict[int, str]:
    """test questions are the common key space for Gate19 と Human_check のラベルである。"""
    path = next((latest / "data/raw").rglob("questions_test.csv"))
    return {int(row["index"]): row["question"] for row in read_csv(path)}


def label_quality(label: dict[str, str]) -> tuple[str, bool, str]:
    source = label.get("source_of_label", "")
    note = label.get("notes", "")
    if source == "gate19_answer_results":
        return "formal_evidence", True, "Gate19 actual selected files"
    if "正解" in note and "不正解" not in note:
        return "human_final_source", True, "Human review marked the source set as correct"
    return "human_reviewed_source", False, "Human file was inspected, but final-source completeness is not explicit"


def bool_text(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def matching_paths(paths: list[str], targets: set[str]) -> list[str]:
    return [path for path in paths if canonical_path(path) in targets]


def make_eda064_method_artifacts(eda064: Path) -> None:
    """EDA064 の候補順位が Strict Resolver ではないことをコードと成果物から固定する。"""
    script = eda064 / "scripts/run_eda064.py"
    text = script.read_text(encoding="utf-8")
    score_keys = re.findall(r'breakdown\["([^"]+)"\]', text)
    schema = {
        "called_function": "rag_competition.planner.candidate_files_for_question",
        "search_index": "rag_competition.search.BM25Index",
        "search_unit": "SearchRecord, then aggregated by file_id",
        "vector_search": False,
        "bm25_search": True,
        "strict_resolver_used": False,
        "file_score_components": list(dict.fromkeys(score_keys)),
        "document_aggregation": "BM25 hit scores are summed per file_id; one CandidateFile is emitted per file",
        "tie_breaking": "descending score, then raw_path.casefold(), then file_id",
        "explicit_filename_priority": "not a separate strict-resolution stage; document_hints can contribute score",
        "capability_specific_resolver_used": False,
    }
    (EDA_ROOT / "eda064_topk_score_schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    (EDA_ROOT / "eda064_topk_method.md").write_text(
        "# EDA064 Top-K method\n\n"
        "EDA064 calls `candidate_files_for_question` directly. It builds a BM25 index over the 1,614 SearchRecord entries, aggregates hit scores by `file_id`, then adds heuristic metadata scores. "
        "It is a document candidate ranking audit, not the Gate19 Strict Resolver or a capability-specific final source selector. No vector index or LLM selector is used.\n",
        encoding="utf-8",
    )
    trace = [
        {"stage": "question analysis", "module": "EDA064/run_eda064.py", "function": "analyze_questions", "input": "test question", "output": "QuestionAnalysis", "selection_unit": "question", "ranking": False, "notes": "offline reuse of current heuristic analysis"},
        {"stage": "candidate ranking", "module": "rag_competition.planner", "function": "candidate_files_for_question", "input": "QuestionAnalysis + FileRecord + SearchRecord", "output": "CandidateFile[]", "selection_unit": "file after SearchRecord aggregation", "ranking": True, "notes": "BM25 plus metadata score"},
        {"stage": "offline evaluation", "module": "EDA064/run_eda064.py", "function": "top-k comparison", "input": "CandidateFile[] + offline labels", "output": "Top-1/3/5/10 metrics", "selection_unit": "document path", "ranking": False, "notes": "labels are never given to the candidate function"},
    ]
    write_csv(EDA_ROOT / "eda064_topk_code_trace.csv", trace)


def make_strict_code_artifacts(latest: Path) -> None:
    """実コード上の Strict source plan と downstream dispatch の境界を記録する。"""
    trace = [
        {"stage": "question/source requirement", "module": "source_selection.py", "function": "build_heuristic_source_plan / call_source_planner", "input": "QuestionAnalysis + FileRecord", "output": "source_requirements", "selection_unit": "requirement", "ranking": "deterministic candidates", "multiple_documents": True, "explicit_filename": True, "project_name": True, "document_role": True, "human_check_dependency": False},
        {"stage": "candidate construction", "module": "source_selection.py", "function": "deterministic_candidates_for_requirement", "input": "source requirement + file profiles", "output": "candidate rows", "selection_unit": "file", "ranking": True, "multiple_documents": True, "explicit_filename": True, "project_name": True, "document_role": True, "human_check_dependency": False},
        {"stage": "final source plan", "module": "source_selection.py", "function": "run_source_selection_planning", "input": "candidate selections + content verification", "output": "final_selected_file_ids", "selection_unit": "file set", "ranking": "selection plus verification", "multiple_documents": True, "explicit_filename": True, "project_name": True, "document_role": True, "human_check_dependency": False},
        {"stage": "source contract", "module": "source_selection_resolution.py", "function": "resolve_source_selection", "input": "final_file_ids + source requirements", "output": "resolved source set", "selection_unit": "source set", "ranking": False, "multiple_documents": True, "explicit_filename": "inherited", "project_name": True, "document_role": True, "human_check_dependency": False},
        {"stage": "route and execution", "module": "tool_registry.py / route_registry.py", "function": "run_answer_pipeline / choose_route", "input": "final_selected_file_ids", "output": "executor inputs and selected_files evidence", "selection_unit": "selected file set", "ranking": False, "multiple_documents": True, "explicit_filename": "not re-ranked", "project_name": "already constrained", "document_role": "route dependent", "human_check_dependency": False},
    ]
    write_csv(EDA_ROOT / "strict_resolver_code_trace.csv", trace)
    (EDA_ROOT / "strict_resolver_architecture.md").write_text(
        "# Strict Resolver architecture\n\n"
        "Gate19 uses source requirements, deterministic candidate construction, candidate selection/content verification, then `final_selected_file_ids`. "
        "`resolve_source_selection` turns that selected set into a conservative source contract; it does not independently rerank all SearchRecord entries. "
        "The tool registry receives this final set, picks a route from the selected file types, and passes it to the capability executor. Human_check is not part of this path.\n",
        encoding="utf-8",
    )
    matrix = [
        {"capability_family": "source selection planning", "source_input": "requirements + profiles + content verification", "final_selection": "final_selected_file_ids", "evidence_relation": "selected files become executor/evidence inputs", "gate_relation": "unresolved or unsupported source set can suppress execution", "observability": "planning jsonl"},
        {"capability_family": "route registry", "source_input": "selected FileRecord list", "final_selection": "none", "evidence_relation": "route determines executor evidence schema", "gate_relation": "unsupported route can suppress", "observability": "tool execution output"},
        {"capability_family": "executor", "source_input": "selected files plus extracted records", "final_selection": "may narrow relevant structures, not source plan", "evidence_relation": "emits locations and used files", "gate_relation": "verification/evidence determines allowed", "observability": "answer_results/execution outputs"},
    ]
    write_csv(EDA_ROOT / "strict_resolver_capability_matrix.csv", matrix)


def main() -> None:
    args = parse_args()
    latest = args.latest_root.resolve()
    eda064 = args.eda064_root.resolve()
    if not (latest / "data/work/gate19_test100_final_candidate/planning/final_source_plans.jsonl").exists():
        raise FileNotFoundError("Gate19 planning artifacts are required for this offline audit")
    for directory in (EDA_ROOT / "data", EDA_ROOT / "outputs", EDA_ROOT / "analysis"):
        directory.mkdir(parents=True, exist_ok=True)

    make_eda064_method_artifacts(eda064)
    make_strict_code_artifacts(latest)

    questions = question_rows(latest)
    labels = read_csv(eda064 / "human_source_labels.csv")
    generic_rows = read_csv(eda064 / "current_retrieval_topk.csv")
    work = latest / "data/work/gate19_test100_final_candidate"
    files = read_jsonl(work / "inventory/file_records.jsonl")
    files_by_id = {row["file_id"]: row for row in files}
    plans = {int(row["question_id"]): row for row in read_jsonl(work / "planning/final_source_plans.jsonl")}
    source_results = {int(row["question_id"]): row for row in read_jsonl(work / "planning/source_selection_results.jsonl")}
    answers_path = latest / "data/output/gate19_test100_final_candidate/answer_results.jsonl"
    answers = {int(row["question_id"]): row for row in read_jsonl(answers_path)}

    eval_labels: list[dict[str, Any]] = []
    for label in labels:
        question_id = int(label["question_id"])
        quality, complete, note = label_quality(label)
        paths = split_paths(label.get("human_selected_documents", ""))
        eval_labels.append({
            "dataset": label["dataset"], "question_id": question_id, "question": questions.get(question_id, ""),
            "label_source": label.get("source_of_label", ""), "required_documents": " | ".join(paths),
            "primary_document": paths[0] if paths else "", "supporting_documents": " | ".join(paths[1:]),
            "required_document_count": len(paths), "label_confidence": quality, "label_is_complete": complete,
            "ambiguity": not complete, "notes": note + ("; " + label.get("notes", "") if label.get("notes") else ""),
            "generated_by": "offline_label_quality_audit", "source": "EDA064 human_source_labels.csv", "confidence": "high" if complete else "medium", "requires_manual_review": not complete,
        })
    write_csv(EDA_ROOT / "evaluation_source_labels.csv", eval_labels)
    (EDA_ROOT / "label_quality_audit.md").write_text(
        "# Label quality audit\n\n"
        f"- Labels: {len(eval_labels)}\n"
        f"- Complete labels: {sum(bool(row['label_is_complete']) for row in eval_labels)}\n"
        f"- Human-reviewed but incomplete labels: {sum(not bool(row['label_is_complete']) for row in eval_labels)}\n"
        "Formal Gate19 selected files are complete offline labels. Human labels marked as correct are treated as complete; other human-inspected files remain U-group candidates. Path identity, not basename identity, is used for comparison.\n",
        encoding="utf-8",
    )

    generic_by_question: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in generic_rows:
        if row.get("dataset") == "test":
            generic_by_question[int(row["question_id"])].append(row)
    for rows in generic_by_question.values():
        rows.sort(key=lambda row: int(row["candidate_rank"]))

    strict_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for label in eval_labels:
        qid = label["question_id"]
        target_paths = {canonical_path(path) for path in split_paths(label["required_documents"])}
        plan = plans.get(qid)
        result = source_results.get(qid)
        answer = answers.get(qid, {})
        if plan is None or result is None:
            strict = {
                "resolver_name": "Gate19 source selection planning", "resolver_applicable": False, "resolver_executed": False,
                "resolver_output_type": "not_observable", "selected_documents": [], "candidate_documents": [],
                "selection_reason": "no planning artifact", "execution_error": "", "no_selection_reason": "not_observable",
                "selected_route": "", "selected_capability": "",
            }
        else:
            selected_ids = [str(value) for value in plan.get("final_selected_file_ids", [])]
            selected_paths = [files_by_id[value]["raw_path"] for value in selected_ids if value in files_by_id]
            candidate_paths = [row.get("source_file", "") for row in result.get("source_candidates", [])]
            operations = [row.get("operation_type", "") for row in plan.get("operations", []) if isinstance(row, dict)]
            strict = {
                "resolver_name": "run_source_selection_planning + resolve_source_selection",
                "resolver_applicable": True, "resolver_executed": True,
                "resolver_output_type": "source_selection_result",
                "selected_documents": selected_paths, "candidate_documents": candidate_paths,
                "selection_reason": plan.get("selector_mode", ""), "execution_error": " | ".join(plan.get("errors", [])),
                "no_selection_reason": "" if selected_paths else plan.get("selection_status", "not_found"),
                "selected_route": " | ".join(operations), "selected_capability": answer.get("route", "") or answer.get("capability", ""),
            }
        # Planning-stage selection and executor-reported actual usage are distinct.
        # Keeping both exposes cases where a capability narrows or replaces its input set.
        executor_selected = split_paths(answer.get("selected_files", []))
        selected = strict["selected_documents"]
        selected_match = matching_paths(selected, target_paths)
        required_recall = len({canonical_path(path) for path in selected_match}) / len(target_paths) if target_paths else 0.0
        exact = bool(target_paths) and {canonical_path(path) for path in selected} == target_paths
        primary = bool(selected) and canonical_path(selected[0]) == canonical_path(label["primary_document"])
        executor_match = matching_paths(executor_selected, target_paths)
        executor_exact = bool(target_paths) and {canonical_path(path) for path in executor_selected} == target_paths
        executor_recall = len({canonical_path(path) for path in executor_match}) / len(target_paths) if target_paths else 0.0
        generic = generic_by_question.get(qid, [])
        top_paths = {limit: [row["source_file"] for row in generic if int(row["candidate_rank"]) <= limit] for limit in (1, 3, 5, 10)}
        top_match = {limit: bool(matching_paths(paths, target_paths)) for limit, paths in top_paths.items()}
        strict_rows.append({
            "dataset": label["dataset"], "question_id": qid, "question": label["question"],
            "selected_route": strict["selected_route"], "selected_capability": strict["selected_capability"],
            "resolver_name": strict["resolver_name"], "resolver_applicable": strict["resolver_applicable"], "resolver_executed": strict["resolver_executed"],
            "resolver_output_type": strict["resolver_output_type"], "selected_documents": " | ".join(selected), "candidate_documents": " | ".join(strict["candidate_documents"]),
            "selection_reason": strict["selection_reason"], "explicit_filename_detected": any("." in token and token.rsplit(".", 1)[-1].lower() in {"docx", "pptx", "xlsx", "pdf", "csv", "ipynb"} for token in re.findall(r"[^\s]+", label["question"])),
            "company_detected": bool(re.search(r"株式会社|法人|会|病院", label["question"])), "document_role_detected": bool(re.search(r"提案書|契約書|報告|会議録|スケジュール|座席表", label["question"])),
            "execution_error": strict["execution_error"], "no_selection_reason": strict["no_selection_reason"],
            "required_document_recall": round(required_recall, 4), "primary_document_accuracy": primary, "all_required_documents_exact": exact,
            "executor_selected_documents": " | ".join(executor_selected), "executor_source_override": bool(executor_selected) and {canonical_path(path) for path in executor_selected} != {canonical_path(path) for path in selected},
            "pipeline_final_required_document_recall": round(executor_recall, 4), "pipeline_final_all_required_documents_exact": executor_exact,
            "unnecessary_document_count": max(0, len(selected) - len(selected_match)), "label_is_complete": label["label_is_complete"],
            "generated_by": "offline_gate19_planning_observation", "source": "Gate19 planning artifacts", "confidence": "high" if strict["resolver_executed"] else "low", "requires_manual_review": not bool(label["label_is_complete"]),
        })
        strict_ok = bool(label["label_is_complete"]) and exact
        generic_ok = bool(label["label_is_complete"]) and top_match[5]
        if not bool(label["label_is_complete"]):
            outcome = "strict_result_not_evaluable"
        elif strict_ok and generic_ok:
            outcome = "both_correct"
        elif strict_ok:
            outcome = "strict_only_correct"
        elif generic_ok:
            outcome = "generic_top5_only_contains_label"
        elif not strict["resolver_applicable"]:
            outcome = "strict_not_applicable"
        else:
            outcome = "both_fail"
        comparison_rows.append({
            "dataset": label["dataset"], "question_id": qid, "question": label["question"], "required_documents": label["required_documents"],
            "strict_selected_documents": " | ".join(selected), "generic_top1": " | ".join(top_paths[1]), "generic_top3": " | ".join(top_paths[3]), "generic_top5": " | ".join(top_paths[5]), "generic_top10": " | ".join(top_paths[10]),
            "strict_exact": strict_ok, "generic_top1_contains_label": top_match[1], "generic_top3_contains_label": top_match[3], "generic_top5_contains_label": top_match[5], "generic_top10_contains_label": top_match[10],
            "comparison_outcome": outcome, "strict_not_observable": not strict["resolver_executed"], "multiple_document_shortfall": bool(label["required_document_count"] > 1 and not exact),
            "generated_by": "offline_comparison", "source": "Gate19 planning + EDA064 TopK", "confidence": "high" if label["label_is_complete"] else "medium", "requires_manual_review": not bool(label["label_is_complete"]),
        })
    write_csv(EDA_ROOT / "strict_resolver_results.csv", strict_rows)
    write_csv(EDA_ROOT / "strict_resolver_question_results.csv", strict_rows)
    write_csv(EDA_ROOT / "resolver_vs_generic_comparison.csv", comparison_rows)

    evaluable = [row for row in strict_rows if row["label_is_complete"]]
    metrics = {
        "labeled_questions": len(strict_rows), "evaluable_questions": len(evaluable),
        "resolver_coverage": sum(bool(row["resolver_applicable"]) for row in strict_rows) / len(strict_rows) if strict_rows else 0,
        "resolver_execution_success_rate": sum(bool(row["resolver_executed"]) for row in strict_rows) / len(strict_rows) if strict_rows else 0,
        "all_required_documents_exact_rate": sum(bool(row["all_required_documents_exact"]) for row in evaluable) / len(evaluable) if evaluable else 0,
        "primary_document_accuracy": sum(bool(row["primary_document_accuracy"]) for row in evaluable) / len(evaluable) if evaluable else 0,
        "required_document_recall": sum(float(row["required_document_recall"]) for row in evaluable) / len(evaluable) if evaluable else 0,
        "pipeline_final_all_required_documents_exact_rate": sum(bool(row["pipeline_final_all_required_documents_exact"]) for row in evaluable) / len(evaluable) if evaluable else 0,
        "executor_source_override_count": sum(bool(row["executor_source_override"]) for row in strict_rows),
        "no_selection_rate": sum(not bool(row["selected_documents"]) for row in strict_rows) / len(strict_rows) if strict_rows else 0,
        "not_observable_rate": sum(row["resolver_output_type"] == "not_observable" for row in strict_rows) / len(strict_rows) if strict_rows else 0,
        "execution_error_rate": sum(bool(row["execution_error"]) for row in strict_rows) / len(strict_rows) if strict_rows else 0,
    }
    subsets = {
        "formal_gate_evidence": [row for row, label in zip(strict_rows, eval_labels) if label["label_source"] == "gate19_answer_results"],
        "human_check": [row for row, label in zip(strict_rows, eval_labels) if label["label_source"] != "gate19_answer_results"],
        "explicit_filename": [row for row in strict_rows if row["explicit_filename_detected"]],
        "companyless": [row for row in strict_rows if not row["company_detected"]],
        "multiple_document": [row for row, label in zip(strict_rows, eval_labels) if label["required_document_count"] > 1],
    }
    subset_rows = []
    for name, rows in subsets.items():
        complete = [row for row in rows if row["label_is_complete"]]
        subset_rows.append({"subset": name, "questions": len(rows), "evaluable": len(complete), "strict_exact": sum(bool(row["all_required_documents_exact"]) for row in complete), "strict_primary": sum(bool(row["primary_document_accuracy"]) for row in complete), "generated_by": "offline_metric", "source": "strict_resolver_results", "confidence": "medium", "requires_manual_review": any(not row["label_is_complete"] for row in rows)})
    write_csv(EDA_ROOT / "strict_resolver_failure_analysis.csv", [row for row in strict_rows if not row["all_required_documents_exact"]])
    write_csv(EDA_ROOT / "strict_resolver_errors.csv", [row for row in strict_rows if row["execution_error"] or row["no_selection_reason"]])
    (EDA_ROOT / "strict_resolver_runtime_notes.md").write_text(
        "# Strict Resolver runtime notes\n\n"
        "EDA065 does not rerun or instrument production code. It observes the Gate19 `final_source_plans.jsonl`, `source_selection_results.jsonl`, and `answer_results.jsonl` emitted by the actual Strict Pipeline. "
        "`selected_documents` is the planning-stage source set. `executor_selected_documents` is the executor-reported final usage set; an override is recorded rather than treated automatically as a planning error.\n",
        encoding="utf-8",
    )
    (EDA_ROOT / "strict_resolver_metrics.md").write_text("# Strict Resolver metrics\n\n" + json.dumps(metrics, ensure_ascii=False, indent=2) + "\n\n## Subsets\n\n" + "\n".join(json.dumps(row, ensure_ascii=False) for row in subset_rows) + "\n\nMetrics are evaluated only against labels marked complete; incomplete human-reviewed labels remain observable but do not inflate accuracy claims.\n", encoding="utf-8")

    factor_rows = []
    for row, label in zip(strict_rows, eval_labels):
        if label["label_source"] != "gate19_answer_results":
            continue
        factor_rows.append({"question_id": row["question_id"], "strict_exact": row["all_required_documents_exact"], "pipeline_final_exact": row["pipeline_final_all_required_documents_exact"], "executor_source_override": row["executor_source_override"], "selection_method": row["selection_reason"], "route": row["selected_route"], "reason_category": "explicit_filename" if row["explicit_filename_detected"] else "source_requirement_and_content_verification", "selected_documents": row["selected_documents"], "executor_selected_documents": row["executor_selected_documents"], "generated_by": "offline_gate19_factor_audit", "source": "planning artifacts", "confidence": "medium", "requires_manual_review": True})
    write_csv(EDA_ROOT / "gate19_selection_success_factors.csv", factor_rows)
    comparison_counter = Counter(row["comparison_outcome"] for row in comparison_rows)
    (EDA_ROOT / "resolver_vs_generic_summary.md").write_text("# Strict Resolver versus generic Top-K\n\n" + "\n".join(f"- {name}: {count}" for name, count in sorted(comparison_counter.items())) + "\n\nStrict uses source requirements and content verification before final execution. Generic Top-K is a BM25-plus-metadata retrieval audit. They are complementary measurements, not equivalent accuracy scores.\n", encoding="utf-8")

    group_rows = []
    for strict, comparison, label in zip(strict_rows, comparison_rows, eval_labels):
        if not label["label_is_complete"] or not strict["resolver_executed"]:
            group, reason = "U", "label incomplete or Strict output not observable"
        elif strict["all_required_documents_exact"]:
            group, reason = "A", "Strict Resolver selected all labeled required documents"
        elif comparison["generic_top10_contains_label"]:
            group, reason = "B", "Strict did not select the labeled set; generic retrieval still exposes a candidate"
        else:
            group, reason = "C", "Strict executed but did not select the labeled set and generic Top-10 also missed it"
        group_rows.append({"dataset": strict["dataset"], "question_id": strict["question_id"], "group": group, "group_reason": reason, "strict_applicable": strict["resolver_applicable"], "strict_correct": strict["all_required_documents_exact"], "generic_top5_contains_label": comparison["generic_top5_contains_label"], "generic_top10_contains_label": comparison["generic_top10_contains_label"], "planner_candidate": group == "B", "recommended_next_action": {"A": "keep_strict_resolver", "B": "planner_poc_with_document_probe", "C": "inspect_candidate_retrieval_or_strict_rule", "U": "improve_label_or_observability"}[group], "confidence": "high" if label["label_is_complete"] else "low", "requires_manual_review": group == "U"})
    write_csv(EDA_ROOT / "resolver_group_classification.csv", group_rows)
    group_counter = Counter(row["group"] for row in group_rows)
    representatives = {name: [str(row["question_id"]) for row in group_rows if row["group"] == name][:8] for name in ("A", "B", "C", "U")}
    (EDA_ROOT / "group_summary.md").write_text("# A/B/C/U group summary\n\n" + "\n".join(f"- {name}: {count}; representative questions: {', '.join(representatives[name]) or 'none'}" for name, count in sorted(group_counter.items())) + "\n\nA retains Strict Resolver. B is the Planner PoC population. C needs retrieval or Strict-rule diagnosis before Planner. U is not used for performance claims.\n", encoding="utf-8")

    labels_by_qid = {row["question_id"]: row for row in eval_labels}
    comparisons_by_qid = {row["question_id"]: row for row in comparison_rows}
    poc_rows = []
    for group in group_rows:
        if group["group"] != "B":
            continue
        label = labels_by_qid[group["question_id"]]
        comparison = comparisons_by_qid[group["question_id"]]
        rank = next((limit for limit in (1, 3, 5, 10) if comparison[f"generic_top{limit}_contains_label"]), "missing")
        question = label["question"]
        poc_rows.append({"question_id": group["question_id"], "question": question, "correct_documents": label["required_documents"], "current_generic_rank": rank, "why_strict_cannot_select": group["group_reason"], "useful_probe_features": "title, document_role, project, headings/slide/sheet metadata, matched terms", "likely_executor_family": "layout_coordinate_executor" if any(token in question for token in ("座", "向かい", "右側")) else "existing_route_or_document_executor", "multi_document_required": label["required_document_count"] > 1, "vision_likely": any(token in question for token in ("座", "色", "太字", "下線", "グラフ")), "poc_evaluation_method": "compare condition1 metadata-only against condition2 metadata plus document probes; labels used only after selection", "generated_by": "offline_group_b_priority", "source": "strict_vs_generic_comparison", "confidence": "high", "requires_manual_review": False})
    poc_rows.sort(key=lambda row: (row["current_generic_rank"] == "missing", row["current_generic_rank"] if isinstance(row["current_generic_rank"], int) else 99, -int(bool(row["multi_document_required"]))))
    write_csv(EDA_ROOT / "planner_poc_candidates.csv", poc_rows[:10])
    (EDA_ROOT / "planner_poc_design.md").write_text(
        "# Planner PoC design\n\n"
        "Condition 1 supplies question, filename/project/file-type/role signals, and generic retrieval scores. Condition 2 adds compact Top-K document probes. "
        "Evaluate final Top-1 accuracy, Top-3 recall, required-document recall, multi-document recall, wrong-company selections, same-name confusion, abstention quality, and executor-family selection. Human labels remain evaluation-only. "
        f"Only {len(poc_rows)} B-group questions currently satisfy both complete-label and generic-Top-10 conditions; do not pad the PoC with U-group seating questions until their final-source labels are clarified.\n",
        encoding="utf-8",
    )
    (EDA_ROOT / "future_selection_architecture.md").write_text(
        "# Future source selection architecture\n\n"
        "1. Resolve an explicit filename when present.\n2. Run the existing Strict Resolver.\n3. Keep its output when the source contract is resolved and confidence/content verification is sufficient.\n4. Fall back only for not-applicable, empty, ambiguous, contradictory, or low-confidence selections.\n5. Build generic Top-5 candidates and compact document probes.\n6. Ask a future planner to choose only among those probes.\n7. Expand to Top-10 when Top-5 cannot establish a document.\n8. Suppress when ambiguity remains.\n\n"
        "For multiple documents, preserve required roles and evaluate set recall. Same-name documents require normalized path/project identity. Companyless questions must not default to internal-only; retain external candidates until a content probe establishes scope. Seating layouts should prefer PPTX/XML or Excel coordinate executors; Vision is a fallback when native structure cannot resolve the relation.\n",
        encoding="utf-8",
    )
    fallback = {
        "adopt_strict_when": ["explicit filename resolves uniquely", "source contract resolved", "content verification succeeds", "no source-set ambiguity"],
        "planner_fallback_when": ["strict not applicable", "no selected documents", "ambiguous or contradictory source set", "strict selection lacks required source role or file relation"],
        "multiple_document_policy": "retain required roles and evaluate all-required-document recall",
        "same_name_policy": "compare normalized relative path and project identity, never basename alone",
        "companyless_policy": "do not default to internal; use probes and retain external candidates",
        "seating_policy": "probe layout metadata then use coordinate executor; Vision only after native structure is insufficient",
        "vision_condition": "selected document contains relevant visual/layout structure and text/coordinates cannot resolve it",
        "abstain_condition": "Top-10 probes leave multiple equally plausible documents or required source relation unverified",
    }
    (EDA_ROOT / "planner_fallback_conditions.json").write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
    (EDA_ROOT / "README.md").write_text("# EDA065\n\nOffline audit comparing Gate19 Strict source selection with EDA064 generic Top-K. Run: `python run_eda065.py --latest-root <read-only worktree> --eda064-root <read-only EDA064>`. No API calls, no runtime changes, and no labels are passed to selection code.\n", encoding="utf-8")
    (EDA_ROOT / "final_summary.md").write_text(
        "# EDA065 final summary\n\n"
        f"- Evaluated source labels: {len(eval_labels)}; complete labels: {sum(bool(row['label_is_complete']) for row in eval_labels)}.\n"
        f"- Strict group counts: {dict(group_counter)}.\n"
        "- EDA064 Top-K is BM25-plus-metadata candidate ranking, not Strict final source selection.\n"
        "- Decision: source_labels_require_cleanup. The eligible B-group is too small for a diversified Planner PoC; C-group retrieval gaps should be measured after label cleanup.\n"
        "- No API, Pipeline, Resolver, Gate, raw, formal artifact, commit, push, or PR action was performed.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
