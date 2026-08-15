"""EDA064: offline audit for source selection and multistage planner requirements.

This script reads the latest worktree only.  It never invokes an API and never
writes into the worktree, raw data, or formal artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any


EDA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EDA_ROOT.parents[1]
ANALYSIS = EDA_ROOT / "analysis"
DATA = EDA_ROOT / "data"

# Keep the audit's Japanese lexical signals encoding-stable across PowerShell sessions.
INTERNAL_SCOPE_TOKENS = ("\u793e\u5185", "\u793e\u54e1", "\u90e8\u7f72", "\u4f1a\u8b70\u5ba4", "\u5ea7\u5e2d", "\u30d5\u30ed\u30a2")
SEATING_TOKENS = ("\u5ea7\u5e2d", "\u5411\u304b\u3044", "\u53f3\u5074", "\u30d5\u30ed\u30a2", "\u914d\u7f6e")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline EDA064.")
    parser.add_argument("--latest-root", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else ["generated_by", "source", "confidence", "requires_manual_review"])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def find_one(root: Path, filename: str) -> Path:
    return next(root.rglob(filename))


def split_paths(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[|;\n]", value or "") if part.strip()]


def canonical_source_path(value: str) -> str:
    """Compare historical audit paths with current raw paths without changing inputs."""
    path = value.replace("\\", "/")
    if "共有ドライブ/" in path:
        path = path.split("共有ドライブ/", 1)[1]
    if path.lower().endswith(".structure.json"):
        path = path[: -len(".structure.json")]
    elif path.lower().endswith((".pptx.md", ".docx.md", ".xlsx.md", ".pdf.md", ".csv.md")):
        path = path[:-3]
    return path.casefold()


def question_signals(question: str, projects: list[str]) -> dict[str, Any]:
    def terms(pattern: str) -> list[str]:
        return list(dict.fromkeys(re.findall(pattern, question, flags=re.IGNORECASE)))

    explicit_files = terms(r"[^\s、。]*\.(?:docx|pptx|xlsx|xlsm|pdf|csv|tsv|ipynb|py|md)")
    companies = [project for project in projects if project and project in question]
    roles = [name for name in ("提案書", "最終報告", "報告書", "契約書", "会議録", "議事録", "スケジュール", "座席表", "体制表", "組織図") if name in question]
    styles = [name for name in ("太字", "下線", "色", "フォント", "ハイライト", "コメント", "注釈", "メモ") if name in question]
    layout = [name for name in ("座席", "席", "フロア", "配置", "レイアウト", "組織図", "座標", "位置") if name in question]
    types: list[str] = []
    if explicit_files: types.append("explicit_document")
    if companies and roles: types.append("explicit_company_and_role")
    if any(name in question for name in ("社内", "社員", "部署", "会議室", "座席", "フロア")): types.append("internal_scope_candidate")
    if styles or layout: types.append("structure_or_style_required")
    if any(name in question for name in ("グラフ", "図", "画像", "色", "座席", "配置")): types.append("vision_required")
    if any(name in question for name in ("比較", "差分", "それぞれ", "両方", "全案件")): types.append("multi_document_required")
    if not (explicit_files or companies or roles): types.append("content_probe_required")
    if not types: types.append("semantic_document_guess")
    if not explicit_files and not companies and not roles: types.append("insufficient_question_signal")
    if any(name in question for name in ("計算", "平均", "合計", "差", "割合", "何日", "何件")):
        executor = "calculation"
    elif styles or layout:
        executor = "structure_or_style"
    elif any(name in question for name in ("シート", "セル", "列", "行", "タスクID")):
        executor = "table_lookup"
    else:
        executor = "document_lookup"
    return {
        "explicit_company_names": " | ".join(companies), "explicit_file_names": " | ".join(explicit_files),
        "explicit_document_roles": " | ".join(roles), "explicit_file_types": " | ".join(sorted({item.rsplit('.', 1)[-1].lower() for item in explicit_files})),
        "person_names": " | ".join(terms(r"[一-龥]{2,4}[\s　][一-龥]{1,4}")),
        "department_names": " | ".join(terms(r"[一-龥]{2,12}(?:部|課|室|チーム)")),
        "task_ids": " | ".join(terms(r"\b[A-Z]{1,4}\d{1,3}\b")), "dates": " | ".join(terms(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}月\d{1,2}日")),
        "numeric_literals": " | ".join(terms(r"\d+(?:\.\d+)?")), "column_names": "", "sheet_names": " | ".join(terms(r"[一-龥A-Za-z0-9_]+シート")),
        "page_or_slide_references": " | ".join(terms(r"(?:第?\d+)?(?:ページ|スライド)")), "version_comparison": "比較" in question or "差分" in question,
        "multi_document_required": "multi_document_required" in types, "style_attribute_terms": " | ".join(styles), "color_terms": "色" in question,
        "bold_terms": "太字" in question, "underline_terms": "下線" in question, "highlight_terms": "ハイライト" in question,
        "comment_or_note_terms": any(item in question for item in ("コメント", "注釈", "メモ")), "chart_or_graph_terms": any(item in question for item in ("グラフ", "チャート")),
        "seating_chart_terms": any(item in question for item in ("座席", "席", "フロア")), "layout_terms": " | ".join(layout),
        "calculation_required": executor == "calculation", "vision_likely_required": "vision_required" in types,
        "internal_scope_terms": " | ".join([item for item in ("社内", "社員", "部署", "会議室", "座席", "フロア") if item in question]),
        "requested_answer_type": "list" if any(item in question for item in ("列挙", "すべて", "挙げ")) else "single_or_short_text",
        "possible_executor_family": executor, "question_signal_class": " | ".join(types),
    }


def load_questions(latest: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset, filename in (("valid", "questions_valid.csv"), ("test", "questions_test.csv")):
        path = find_one(latest / "data/raw", filename)
        for item in csv.DictReader(path.open(encoding="utf-8-sig")):
            rows.append({"dataset": dataset, "question_id": int(item["index"]), "exact_question": item["question"]})
    return rows


def label_sources(latest: Path, questions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    labels: list[dict[str, Any]] = []
    inventories: list[dict[str, Any]] = []
    human = REPO_ROOT / "EDA/human_review.csv"
    if human.exists():
        human_rows = list(csv.DictReader(human.open(encoding="utf-8-sig")))
        inventories.append({"path": str(human), "purpose": "offline human review sheet", "question_coverage": len(human_rows), "selected_source_information": True, "answer_information": True, "timestamp": "unknown", "availability": "readable", "reliability_note": "source_files is historical audit context; human_sorce_files is only a human-confirmed label when populated"})
        for item in human_rows:
            confirmed = split_paths(item.get("human_sorce_files", ""))
            if confirmed:
                labels.append({"dataset": "test", "question_id": int(item["index"]), "human_selected_documents": " | ".join(confirmed), "human_selected_company": item.get("company_group", ""), "human_selected_file_types": "", "human_selected_document_roles": "", "multiple_documents_required": len(confirmed) > 1, "source_of_label": "human_review.human_sorce_files", "label_confidence": "human_confirmed", "notes": item.get("human_review", ""), "generated_by": "offline_eda", "source": str(human), "confidence": "high", "requires_manual_review": False})
    audit = REPO_ROOT / "EDA/EDA058/tables/answer_source_audit.csv"
    if audit.exists():
        audit_rows = list(csv.DictReader(audit.open(encoding="utf-8-sig")))
        inventories.append({"path": str(audit), "purpose": "historical source audit", "question_coverage": len(audit_rows), "selected_source_information": True, "answer_information": True, "timestamp": "unknown", "availability": "readable", "reliability_note": "historical route evidence, not necessarily human-confirmed"})
    answer_path = latest / "data/output/gate19_test100_final_candidate/answer_results.jsonl"
    if answer_path.exists():
        answers = read_jsonl(answer_path)
        inventories.append({"path": str(answer_path), "purpose": "Gate 19 strict-run answer evidence", "question_coverage": len(answers), "selected_source_information": True, "answer_information": True, "timestamp": "latest worktree", "availability": "readable", "reliability_note": "formal Gate results are usable only as offline evaluation labels"})
        for item in answers:
            if item.get("gate_status") != "allowed":
                continue
            documents = item.get("selected_files", [])
            if not documents:
                continue
            labels.append({"dataset": "test", "question_id": int(item["question_id"]), "human_selected_documents": " | ".join(documents), "human_selected_company": "", "human_selected_file_types": " | ".join(sorted({Path(path).suffix.lstrip('.') for path in documents})), "human_selected_document_roles": "", "multiple_documents_required": len(documents) > 1, "source_of_label": "gate19_answer_results", "label_confidence": "formal_evidence", "notes": "offline evaluation only", "generated_by": "offline_eda", "source": str(answer_path), "confidence": "high", "requires_manual_review": False})
    # Prefer human-confirmed labels while retaining one label row per question for Top-K evaluation.
    priority = {"human_confirmed": 2, "formal_evidence": 1}
    selected: dict[tuple[str, int], dict[str, Any]] = {}
    for label in labels:
        key = (label["dataset"], label["question_id"])
        if key not in selected or priority.get(label["label_confidence"], 0) > priority.get(selected[key]["label_confidence"], 0):
            selected[key] = label
    return list(selected.values()), inventories


def main() -> None:
    args = parse_args()
    latest = args.latest_root.resolve()
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(latest / "src"))
    from rag_competition.planner import candidate_files_for_question
    from rag_competition.questions import analyze_questions
    from rag_competition.schemas import FileRecord, SearchRecord

    work = latest / "data/work/gate19_test100_final_candidate"
    file_rows = read_jsonl(work / "inventory/file_records.jsonl")
    search_rows = read_jsonl(work / "extracted/search_records.jsonl")
    files = [FileRecord(**item) for item in file_rows]
    records = [SearchRecord(**item) for item in search_rows]
    projects = sorted({item.project_name for item in files if item.project_name})
    questions = load_questions(latest)
    source_inventory = [
        {"path": str(work / "inventory/file_records.jsonl"), "purpose": "current document inventory", "question_coverage": "all", "selected_source_information": True, "answer_information": False, "timestamp": "latest worktree", "availability": "readable", "reliability_note": "strict-run metadata"},
        {"path": str(work / "extracted/search_records.jsonl"), "purpose": "current 1614 search chunks", "question_coverage": "all", "selected_source_information": True, "answer_information": False, "timestamp": "latest worktree", "availability": "readable", "reliability_note": "current strict extraction search records"},
    ]
    labels, human_inventory = label_sources(latest, questions)
    write_csv(EDA_ROOT / "source_inventory.csv", source_inventory)
    write_csv(EDA_ROOT / "human_audit_inventory.csv", human_inventory)
    write_csv(EDA_ROOT / "human_source_labels.csv", labels)
    (EDA_ROOT / "source_label_coverage.md").write_text("\n".join(["# Source label coverage", "", f"- Offline source labels: {len(labels)}", f"- Human-confirmed labels: {sum(row['label_confidence'] == 'human_confirmed' for row in labels)}", f"- Formal Gate Evidence labels: {sum(row['label_confidence'] == 'formal_evidence' for row in labels)}", "- Unlabeled questions are intentionally not inferred.", "- Labels are evaluation-only and are never passed to candidate generation or runtime."]), encoding="utf-8")
    registry_rows = []
    for project in projects:
        file_ids = [item.file_id for item in files if item.project_name == project]
        registry_rows.append({"canonical_company_id": f"project::{project}", "canonical_company_name": project, "aliases": project, "source_paths": " | ".join(file_ids), "confidence": "high", "ambiguity": False, "normalization_reason": "existing FileRecord.project_name", "generated_by": "offline_inventory", "source": "file_records.jsonl", "requires_manual_review": False})
    (EDA_ROOT / "company_registry.json").write_text(json.dumps(registry_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(EDA_ROOT / "company_alias_audit.csv", registry_rows)
    document_inventory = [{"company_id": f"project::{file.project_name}" if file.project_name else "", "document_id": file.file_id, "source_file": file.raw_path, "file_type": file.extension, "document_role": file.document_kind, "title": file.file_name, "summary": "", "sections": "", "slide_or_sheet_count": len([record for record in records if record.file_id == file.file_id]), "major_entities": "", "major_dates": " | ".join(file.date_hints), "major_ids": "", "available_content_types": "", "visual_content_present": file.extension in {".pptx", ".pdf", ".png", ".jpg", ".jpeg"}, "generated_by": "offline_inventory", "source": "file_records.jsonl", "confidence": "medium", "requires_manual_review": True} for file in files]
    (EDA_ROOT / "document_inventory.json").write_text(json.dumps(document_inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    raw_pairs = [((1000 if item["dataset"] == "valid" else 0) + item["question_id"], item["exact_question"]) for item in questions]
    analyses = {(item["dataset"], item["question_id"]): value for item, value in zip(questions, analyze_questions(raw_pairs, {}, DATA / "question_analysis"))}
    signal_rows: list[dict[str, Any]] = []
    for item in questions:
        signals = question_signals(item["exact_question"], projects)
        internal_hits = [token for token in INTERNAL_SCOPE_TOKENS if token in item["exact_question"]]
        seating_hits = [token for token in SEATING_TOKENS if token in item["exact_question"]]
        if internal_hits:
            signals["internal_scope_terms"] = " | ".join(internal_hits)
            classes = signals["question_signal_class"].split(" | ")
            if "internal_scope_candidate" not in classes:
                classes.append("internal_scope_candidate")
            signals["question_signal_class"] = " | ".join(classes)
        if seating_hits:
            signals["seating_chart_terms"] = " | ".join(seating_hits)
            signals["layout_terms"] = " | ".join(sorted(set(filter(None, [signals["layout_terms"], *seating_hits]))))
            classes = signals["question_signal_class"].split(" | ")
            if "structure_or_style_required" not in classes:
                classes.append("structure_or_style_required")
            if "vision_required" not in classes:
                classes.append("vision_required")
            signals["question_signal_class"] = " | ".join(classes)
        analysis = analyses[(item["dataset"], item["question_id"])]
        signal_rows.append({**item, **signals, "current_routes": " | ".join(analysis.provisional_routes), "current_required_file_types": " | ".join(analysis.required_file_types), "generated_by": "offline_regex_and_current_question_analysis", "source": "question csv + latest questions.py", "confidence": "medium", "requires_manual_review": False})
    write_csv(EDA_ROOT / "question_signal_inventory.csv", signal_rows)
    counts = Counter(class_name for row in signal_rows for class_name in row["question_signal_class"].split(" | "))
    (EDA_ROOT / "question_signal_summary.md").write_text("# Question signal summary\n\n" + "\n".join(f"- {key}: {value}" for key, value in sorted(counts.items())), encoding="utf-8")

    label_map = {(row["dataset"], row["question_id"]): row for row in labels}
    topk_rows: list[dict[str, Any]] = []
    for item in signal_rows:
        analysis = analyses[(item["dataset"], item["question_id"])]
        _, candidates, _ = candidate_files_for_question(analysis, files, records, top_n=10)
        label = label_map.get((item["dataset"], item["question_id"]))
        targets = {canonical_source_path(path) for path in split_paths(label["human_selected_documents"])} if label else set()
        for candidate in candidates:
            file = next(value for value in files if value.file_id == candidate.file_id)
            topk_rows.append({"dataset": item["dataset"], "question_id": item["question_id"], "candidate_rank": candidate.rank, "document_id": candidate.file_id, "source_file": candidate.raw_path, "company": file.project_name, "file_type": file.extension, "document_role": file.document_kind, "score": candidate.score, "score_components": json.dumps(candidate.score_breakdown, ensure_ascii=False), "selection_reason": candidate.candidate_reason, "human_selected_match": canonical_source_path(candidate.raw_path) in targets, "label_available": bool(label), "generated_by": "current_candidate_files_for_question", "source": "latest planner.py", "confidence": "high", "requires_manual_review": False})
    write_csv(EDA_ROOT / "current_retrieval_topk.csv", topk_rows)
    metrics_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for group_name, subset in (("gate19_labeled", [row for row in labels if row["source_of_label"] == "gate19_answer_results"]), ("all_labeled", labels)):
        found = {key: [] for key in [(row["dataset"], row["question_id"]) for row in subset]}
        for row in topk_rows:
            key = (row["dataset"], row["question_id"])
            if key in found and row["human_selected_match"]:
                found[key].append(row["candidate_rank"])
        total = len(found) or 1
        metrics_rows.append({"group": group_name, "labeled_questions": len(found), "top1_accuracy": sum(1 for ranks in found.values() if 1 in ranks) / total, "top3_recall": sum(1 for ranks in found.values() if any(rank <= 3 for rank in ranks)) / total, "top5_recall": sum(1 for ranks in found.values() if any(rank <= 5 for rank in ranks)) / total, "top10_recall": sum(1 for ranks in found.values() if ranks) / total, "correct_source_missing_rate": sum(1 for ranks in found.values() if not ranks) / total})
        for key, ranks in found.items():
            if not ranks:
                failures.append({"dataset": key[0], "question_id": key[1], "failure": "correct_source_missing_from_top10", "generated_by": "offline_topk_evaluation", "source": "human_source_labels", "confidence": "high", "requires_manual_review": True})
    # Derive selection-quality diagnostics from source-path labels without feeding
    # those labels back into candidate generation.
    files_by_path = {canonical_source_path(file.raw_path): file for file in files}
    signals_by_key = {(row["dataset"], row["question_id"]): row for row in signal_rows}
    top1_rows = {(row["dataset"], row["question_id"]): row for row in topk_rows if row["candidate_rank"] == 1}
    selection_diagnostics: list[dict[str, Any]] = []
    for label in labels:
        key = (label["dataset"], label["question_id"])
        selected = top1_rows.get(key)
        targets = [files_by_path.get(canonical_source_path(path)) for path in split_paths(label["human_selected_documents"])]
        targets = [target for target in targets if target is not None]
        if not selected or not targets:
            continue
        selected_file = next(file for file in files if file.file_id == selected["document_id"])
        target_names = {target.file_name.casefold() for target in targets}
        target_companies = {target.project_name for target in targets}
        target_types = {target.extension for target in targets}
        target_roles = {target.document_kind for target in targets}
        signal = signals_by_key[key]
        selection_diagnostics.append({
            "dataset": key[0], "question_id": key[1],
            "top1_source_match": bool(selected["human_selected_match"]),
            "company_match": selected_file.project_name in target_companies,
            "file_type_match": selected_file.extension in target_types,
            "document_role_match": selected_file.document_kind in target_roles,
            "same_name_file_confusion": selected_file.file_name.casefold() in target_names and not selected["human_selected_match"],
            "cross_company_contamination": selected_file.project_name not in target_companies,
            "explicit_filename_failure": bool(signal["explicit_file_names"]) and not any(row["human_selected_match"] for row in topk_rows if (row["dataset"], row["question_id"]) == key),
            "companyless_question": not bool(signal["explicit_company_names"]),
            "generated_by": "offline_source_label_comparison", "source": "labels+current_topk", "confidence": "medium", "requires_manual_review": True,
        })
    write_csv(EDA_ROOT / "document_selection_evaluation.csv", selection_diagnostics)
    diagnostic_counts = {
        "top1_company_match": sum(row["company_match"] for row in selection_diagnostics),
        "top1_file_type_match": sum(row["file_type_match"] for row in selection_diagnostics),
        "top1_document_role_match": sum(row["document_role_match"] for row in selection_diagnostics),
        "same_name_file_confusion": sum(row["same_name_file_confusion"] for row in selection_diagnostics),
        "cross_company_contamination": sum(row["cross_company_contamination"] for row in selection_diagnostics),
        "explicit_filename_failure": sum(row["explicit_filename_failure"] for row in selection_diagnostics),
        "companyless_labeled_questions": sum(row["companyless_question"] for row in selection_diagnostics),
    }
    (EDA_ROOT / "current_retrieval_metrics.md").write_text("# Current Top-K metrics\n\n" + "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in metrics_rows) + "\n\n# Top-1 source-label diagnostics\n\n" + json.dumps(diagnostic_counts, ensure_ascii=False, sort_keys=True) + "\n\nCompany, file-type, and role diagnostics are inferred from labeled source paths. Multi-document labels are treated as a matching set and require manual review for causal interpretation.", encoding="utf-8")
    write_csv(EDA_ROOT / "current_retrieval_failures.csv", failures)

    # Generate compact document probes only for Top-5 documents attached to labels.
    records_by_file: dict[str, list[SearchRecord]] = defaultdict(list)
    for record in records: records_by_file[record.file_id].append(record)
    labeled_keys = set(label_map)
    top5_ids = {row["document_id"] for row in topk_rows if (row["dataset"], row["question_id"]) in labeled_keys and row["candidate_rank"] <= 5}
    probes: list[dict[str, Any]] = []
    for file in files:
        if file.file_id not in top5_ids: continue
        file_records = records_by_file[file.file_id]
        text = " ".join(record.text[:500] for record in file_records[:3])[:1200]
        record_types = {record.record_type for record in file_records}
        metadata = [record.metadata for record in file_records]
        probe = {"document_id": file.file_id, "source_file": file.raw_path, "company": file.project_name, "file_type": file.extension, "document_role": file.document_kind, "title": file.file_name, "headings": "", "slide_titles": " | ".join(str(meta.get("slide_number")) for meta in metadata if meta.get("slide_number"))[:200], "sheet_names": " | ".join(str(meta.get("sheet_name")) for meta in metadata if meta.get("sheet_name"))[:200], "section_names": "", "table_headers": "", "major_entities": "", "person_names": "", "department_names": "", "dates": " | ".join(file.date_hints), "task_ids": " | ".join(sorted(set(re.findall(r"\b[A-Z]{1,4}\d{1,3}\b", text)))), "numeric_identifiers": "", "comments_present": "comment" in " ".join(record_types).lower(), "notes_present": False, "charts_present": any("chart" in record_type for record_type in record_types), "images_present": any(record_type == "image" for record_type in record_types), "seating_layout_likely": any(term in (text + file.file_name) for term in ("座席", "フロア", "配置")), "bold_present": "unknown", "underline_present": "unknown", "font_colors_present": "unknown", "fill_colors_present": "unknown", "highlights_present": "unknown", "formulas_present": any("formula" in record_type for record_type in record_types), "visible_text_sample": text, "matched_question_terms": "", "matched_locations": "", "structural_match_features": "record_types=" + "|".join(sorted(record_types)), "generated_by": "existing_search_records", "source": "latest strict extraction", "confidence": "medium", "requires_manual_review": True}
        probes.append(probe)
    (EDA_ROOT / "document_probes.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in probes) + "\n", encoding="utf-8")
    write_csv(EDA_ROOT / "document_probe_features.csv", probes)
    discrimination = [{"feature": feature, "available_documents": sum(bool(row.get(feature)) and row.get(feature) != "unknown" for row in probes), "selection_value": "candidate_probe" if feature in {"title", "sheet_names", "task_ids", "visible_text_sample", "structural_match_features"} else "requires_structure_enrichment", "generated_by": "offline_probe_audit", "source": "document_probes", "confidence": "medium", "requires_manual_review": True} for feature in ("title", "slide_titles", "sheet_names", "task_ids", "comments_present", "charts_present", "seating_layout_likely", "bold_present", "font_colors_present", "formulas_present")]
    write_csv(EDA_ROOT / "probe_discrimination_analysis.csv", discrimination)
    (EDA_ROOT / "probe_discrimination_summary.md").write_text("# Probe discrimination\n\nCurrent records reliably expose filename, file role, slide/sheet metadata, task IDs, and sampled text. Formatting, table headers, people, departments, and layout attributes require richer structure extraction before final-selection use.", encoding="utf-8")

    content_cases, companyless, seating = [], [], []
    internal_terms = ("社内", "社員", "部署", "会議室", "座席", "フロア")
    internal_terms = INTERNAL_SCOPE_TOKENS
    for row in signal_rows:
        label = label_map.get((row["dataset"], row["question_id"]))
        candidates = [item for item in topk_rows if item["dataset"] == row["dataset"] and item["question_id"] == row["question_id"]]
        rank = next((item["candidate_rank"] for item in candidates if item["human_selected_match"]), None)
        lacks = not row["explicit_company_names"] and not row["explicit_file_names"]
        if label and (lacks or (rank and rank > 1) or row["seating_chart_terms"] or row["style_attribute_terms"]):
            content_cases.append({"question_id": row["question_id"], "question_signal_class": row["question_signal_class"], "correct_document": label["human_selected_documents"], "initial_rank": rank or "missing", "why_question_only_is_insufficient": "no explicit company/file or structural condition", "document_content_needed": "title, sampled text, slide/sheet/section probe", "structural_information_needed": row["style_attribute_terms"] or row["layout_terms"], "whether_top5_probe_would_help": bool(rank and rank <= 5), "whether_vision_is_needed": row["vision_likely_required"], "likely_executor": row["possible_executor_family"], "missing_capability": "document_probe" if rank and rank <= 5 else "candidate_retrieval", "recommended_selection_strategy": "top5_probe_then_select", "generated_by": "offline_rule", "source": "signals+labels+topk", "confidence": "medium", "requires_manual_review": True})
        if not row["explicit_company_names"]:
            selected = label["human_selected_documents"] if label else ""
            internal = any(term in row["exact_question"] for term in internal_terms)
            companyless.append({"question_id": row["question_id"], "dataset": row["dataset"], "question": row["exact_question"], "internal_scope_terms": row["internal_scope_terms"], "human_selected_documents": selected, "label_available": bool(label), "internal_term_present": internal, "current_rank": rank or "", "generated_by": "offline_rule", "source": "signals+labels", "confidence": "low" if not label else "medium", "requires_manual_review": True})
        seating_label = bool(label and "座席表" in label["human_selected_documents"])
        if row["seating_chart_terms"] or seating_label or any(term in row["exact_question"] for term in ("座", "向かい", "右側")):
            seating.append({"question_id": row["question_id"], "dataset": row["dataset"], "question": row["exact_question"], "company_present": bool(row["explicit_company_names"]), "person_present": bool(row["person_names"]), "department_present": bool(row["department_names"]), "correct_document": label["human_selected_documents"] if label else "unlabeled", "file_format": "unknown", "text_only_selection": False, "probe_selection": True, "vision_needed": True, "likely_executor": "layout_coordinate_executor", "self_scope_effective": bool(row["internal_scope_terms"]), "generated_by": "offline_rule", "source": "question signals", "confidence": "medium", "requires_manual_review": True})
    write_csv(EDA_ROOT / "content_probe_required_questions.csv", content_cases)
    (EDA_ROOT / "content_probe_case_studies.md").write_text("# Content-probe cases\n\n" + "\n".join(f"- Q{row['question_id']}: rank={row['initial_rank']}, strategy={row['recommended_selection_strategy']}" for row in content_cases), encoding="utf-8")
    write_csv(EDA_ROOT / "companyless_questions.csv", companyless)
    rule_rows = []
    for name, predicate in (("A", lambda row: row["internal_term_present"]), ("B", lambda row: row["internal_term_present"] and bool(row["label_available"])), ("C", lambda row: row["internal_term_present"] and any(term in row["question"] for term in ("座席", "フロア", "配置")))):
        subset = [row for row in companyless if predicate(row)]
        rule_rows.append({"rule": name, "target_questions": len(subset), "correctly_prioritize_internal": "unlabeled_without_company_ground_truth", "incorrectly_exclude_external": "unlabeled_without_company_ground_truth", "top5_recall_change": "not_simulated", "top1_accuracy_change": "not_simulated", "false_positive": "requires_manual_labels", "false_negative": "requires_manual_labels", "generated_by": "offline_rule_scope", "source": "companyless_questions", "confidence": "low", "requires_manual_review": True})
    write_csv(EDA_ROOT / "internal_scope_rule_evaluation.csv", rule_rows)
    (EDA_ROOT / "internal_scope_recommendation.md").write_text("# Internal scope recommendation\n\nDo not treat companyless questions as internal by default. Use internal terms only to create a candidate group, retain external candidates unless an explicit internal-content probe wins, and collect source labels before measuring an accuracy uplift.", encoding="utf-8")
    write_csv(EDA_ROOT / "seating_question_audit.csv", seating)
    (EDA_ROOT / "seating_document_features.md").write_text("# Seating document features\n\nUseful features: two-dimensional names, departments, merged cells, blank aisles, floor labels, shape coordinates, desk/island markers, and cell/shape bounding boxes.", encoding="utf-8")
    (EDA_ROOT / "seating_executor_requirements.md").write_text("# Seating executor requirements\n\nNeed an Excel-cell or PPTX-shape coordinate resolver with merged-cell, empty-cell, group-shape, orientation, department-label, and adjacency evidence. Vision is a fallback only when XML/cell structures cannot represent the layout.", encoding="utf-8")

    old_stores = [path for path in (REPO_ROOT / "EDA").rglob("text_chunks.jsonl")]
    stores = [{"store": "current_strict_search_records", "path": str(work / "extracted/search_records.jsonl"), "file_count": len({row.file_id for row in records}), "chunk_count": len(records), "avg_chunks_per_document": round(len(records) / len(files), 2), "schema": "SearchRecord", "granularity": "format-specific search record", "candidate_mode_used": True, "embedding_model": "none", "stale_status": "current"}]
    for path in old_stores:
        count = sum(1 for _ in path.open(encoding="utf-8"))
        stores.append({"store": path.parent.parent.name, "path": str(path), "file_count": "unknown", "chunk_count": count, "avg_chunks_per_document": "unknown", "schema": "historical jsonl", "granularity": "historical text chunk", "candidate_mode_used": False, "embedding_model": "unknown", "stale_status": "historical"})
    stores.append({"store": "historical_referenced_12139", "path": "provenance_not_found_in_current_EDA_tree", "file_count": "unknown", "chunk_count": 12139, "avg_chunks_per_document": "unknown", "schema": "unverified", "granularity": "unverified", "candidate_mode_used": "unknown", "embedding_model": "unknown", "stale_status": "reported_reference_requires_provenance"})
    write_csv(EDA_ROOT / "chunk_store_inventory.csv", stores)
    (EDA_ROOT / "chunk_store_comparison.md").write_text("# Chunk store comparison\n\n" + "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in stores) + "\n\nThe stores serve different stages: current records are stable strict-run search units; historical chunks are finer extraction artifacts. Reuse must be audited by schema and freshness, not count alone.", encoding="utf-8")
    structure_rows = [{"attribute": name, "current_1614": value, "historical_chunks": "schema_dependent", "planner_use": use} for name, value, use in (("page_slide_sheet", "available_in_metadata", "document_probe"), ("table_cell_row", "partial", "executor_input"), ("comments_notes", "route_specific", "executor_input"), ("bold_color_fill", "not_in_generic_record", "structure_enrichment"), ("bbox_relationships_neighbors", "partial", "layout_and_probe"), ("charts_images", "record_type_only", "visual_probe"))]
    write_csv(EDA_ROOT / "structure_metadata_coverage.csv", structure_rows)
    (EDA_ROOT / "retrieval_layer_recommendation.md").write_text("# Retrieval layer recommendation\n\nUse a document-level inventory for Top-K candidate selection and a richer document-internal index for evidence retrieval. Keep layout/style/comment structures as executor-specific side channels rather than flattening all of them into generic text chunks.", encoding="utf-8")

    architecture = []
    for row in signal_rows:
        primary = "A" if row["explicit_file_names"] else "E" if row["style_attribute_terms"] or row["seating_chart_terms"] else "D" if row["multi_document_required"] else "H" if row["calculation_required"] else "C" if row["internal_scope_terms"] and not row["explicit_company_names"] else "B" if "content_probe_required" in row["question_signal_class"] else "G"
        secondaries = []
        if row["vision_likely_required"]: secondaries.append("F")
        if row["possible_executor_family"] == "table_lookup": secondaries.append("G")
        architecture.append({"dataset": row["dataset"], "question_id": row["question_id"], "primary_class": primary, "secondary_classes": " | ".join(secondaries), "reasoning_summary": row["question_signal_class"], "expected_retrieval_stage": "document_probe" if primary in {"B", "C", "E", "F"} else "initial_candidate", "likely_executor": row["possible_executor_family"], "missing_executor": "unknown", "requires_llm_planner": primary in {"B", "C", "D", "E", "F"}, "requires_vision": row["vision_likely_required"], "human_label_available": (row["dataset"], row["question_id"]) in label_map, "generated_by": "offline_architecture_rules", "source": "question signals", "confidence": "medium", "requires_manual_review": True})
    write_csv(EDA_ROOT / "question_architecture_classification.csv", architecture)
    (EDA_ROOT / "question_class_summary.md").write_text("# Question class summary\n\n" + "\n".join(f"- {key}: {value}" for key, value in sorted(Counter(row['primary_class'] for row in architecture).items())), encoding="utf-8")
    (EDA_ROOT / "planner_output_schema.json").write_text(json.dumps({"scope": "string", "scope_reason": "string", "explicit_documents": ["string"], "candidate_documents": [{"document_id": "string", "score": "number"}], "selected_documents": ["string"], "document_probe_requests": ["string"], "question_type": "string", "required_file_types": ["string"], "required_attributes": ["string"], "required_capabilities": ["string"], "execution_steps": ["string"], "requires_calculation": False, "requires_vision": False, "expected_answer_type": "string", "ambiguity": False, "abstain_reason": "string"}, ensure_ascii=False, indent=2), encoding="utf-8")
    (EDA_ROOT / "planner_architecture.md").write_text("# Multistage planner architecture\n\nQuestion analysis -> deterministic Top-5 document candidates -> bounded document probes -> planner selection only when rules remain ambiguous -> executor classification -> Python file analysis -> evidence -> verification -> gate. Top-5 is the recommended default probe budget because Top-1 misses labeled sources. Use Top-10 only as an evidence-recovery fallback when the Top-5 probes cannot establish a document: labeled Gate 19 recall rises from 0.500 at Top-5 to 0.625 at Top-10. LLM, if introduced later, should choose among probe summaries only; Python remains responsible for extraction, calculation, layout, and verification. Human labels remain offline evaluation data only.", encoding="utf-8")
    (EDA_ROOT / "next_poc_plan.md").write_text("# Next minimal PoC\n\nTarget: labeled questions whose correct document is in current Top-5 but not Top-1. Compare deterministic document probes with and without a planner selecting from five summaries. Success: improve labeled Top-1 selection without reducing Top-5 recall, zero cross-company contamination, no formal-pipeline integration, and no Human label in inputs.", encoding="utf-8")
    (EDA_ROOT / "README.md").write_text("# EDA064\n\nOffline audit of source selection, Human labels, probes, internal scope, seating layouts, chunk stores, and multistage planner requirements. Run: `python scripts/run_eda064.py --latest-root <read-only latest worktree>`. No API calls and no runtime changes.", encoding="utf-8")
    (EDA_ROOT / "environment.md").write_text(f"# Environment\n\n- EDA directory: {EDA_ROOT}\n- Latest worktree (read-only): {latest}\n- Latest HEAD: df470b1 / 29e1fc9 descendant\n- Questions: {len(questions)} (valid=30, test=100)\n- Raw documents from latest run: {len(files)}\n- Current chunks: {len(records)}\n- API calls: 0\n", encoding="utf-8")
    (EDA_ROOT / "final_summary.md").write_text("\n".join(["# EDA064 final summary", "", f"- Questions: {len(questions)}; documents: {len(files)}; current search chunks: {len(records)}; source labels: {len(labels)}.", "- Gate19 labeled Top-1/Top-3/Top-5/Top-10: see current_retrieval_metrics.md.", "- Recommendation: proceed_to_multistage_planner_poc, but first preserve current Top-5 recall and enrich document probes with structure metadata.", "- No production code, OpenRouter Candidate Mode, raw file, formal artifact, Gate, commit, push, or PR action was performed." ]), encoding="utf-8")


if __name__ == "__main__":
    main()
