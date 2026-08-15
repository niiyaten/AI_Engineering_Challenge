from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CAPABILITY_COLUMNS = [
    "dataset", "question_id", "question_original", "primary_question_type",
    "secondary_question_types", "required_file_types", "required_document_roles",
    "required_operations", "source_cardinality", "source_relation", "required_projects",
    "semantic_reasoning_required", "calculation_required", "vision_required",
    "multimodal_required", "current_executor", "current_status", "failure_stage",
    "candidate_file_count", "selected_file_count", "valid_answer_available",
    "current_valid_result", "estimated_implementation_difficulty", "estimated_error_risk",
    "estimated_reusability", "estimated_test_frequency", "priority_score",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = columns or (list(rows[0]) if rows else ["status"])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text or "")).strip()


def has(text: str, *terms: str) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def infer_file_types(question: str) -> list[str]:
    text = question.lower()
    found = [ext for ext in ("docx", "pptx", "xlsx", "csv", "tsv", "pdf", "py", "ipynb", "md", "json", "png", "jpg") if f".{ext}" in text]
    rules = (
        (("提案書", "最終報告", "報告資料"), ["pptx", "pdf", "docx"]),
        (("契約書",), ["docx"]), (("スケジュール", "train.xlsx", "シート", "セル", "pivot"), ["xlsx"]),
        (("会議録",), ["docx", "pdf"]), (("分析コード", "コード", "関数", "実装設定"), ["py"]),
        (("notebook", "ipynb", "ノートブック"), ["ipynb"]), (("マークダウン", "カラム説明"), ["md"]),
        (("グラフ", "ヒートマップ", "画像", "座席"), ["png", "jpg", "pptx", "pdf", "xlsx", "ipynb"]),
    )
    for terms, types in rules:
        if has(text, *terms):
            found.extend(types)
    return list(dict.fromkeys(found))


def infer_roles(question: str) -> list[str]:
    mapping = {
        "proposal": ("提案書", "PP"), "contract": ("契約書", "契約条件", "CT"),
        "schedule": ("スケジュール", "PLAN", "PL"), "report": ("最終報告", "報告資料", "FR"),
        "minutes": ("会議録", "MM"), "analysis_data": ("train.xlsx", "train.csv", "分析対象データ", "顧客データ"),
        "analysis_code": ("分析コード", "modeling.py", "コード", "実装設定"),
        "notebook": ("ipynb", "Notebook", "ノートブック"), "internal_master": ("社内管理", "APR", "座席", "FM"),
    }
    return [role for role, terms in mapping.items() if has(question, *terms)]


def infer_source_shape(question: str) -> tuple[str, str]:
    text = normalize(question)
    if has(text, "比較", "変更内容", "変更点", "更新内容", "旧版", "最新版") and has(text, "old", "v1", "v2", "v3", "r1", "r2", "変更前", "変更後"):
        return "pair", "version_pair"
    if has(text, "全案件", "各案件", "完了案件", "最も多くの案件", "案件を", "案件のうち"):
        return "all_matching", "cross_project"
    if has(text, "PP・契約書・PLAN・FR", "複数資料", "照合", "会議録において", "提案時", "最終報告時点", "中間報告時点"):
        return "multiple", "aggregate_sources"
    explicit = re.findall(r"[^\s、。]+\.(?:docx|pptx|xlsx|pdf|csv|py|ipynb|json)", text, flags=re.I)
    if len(explicit) >= 2:
        return "multiple", "referenced_resource"
    if has(text, "社内管理", "APR", "FM") and has(text, "案件", "契約", "内線"):
        return "multiple", "shared_resource"
    return "single", "same_project"


def classify(question: str) -> tuple[str, list[str], list[str]]:
    """valid/test共通の表現規則から、主能力・副能力・操作を推定する。"""
    q = normalize(question)
    secondary: list[str] = []
    operations: list[str] = []
    version = has(q, "比較", "更新内容", "変更点", "変更された", "修正された", "old", "旧版", "最新版")
    chart = has(q, "グラフ", "ヒストグラム", "ヒートマップ", "折れ線", "可視化", "figure_")
    spatial = has(q, "右側", "向かい", "配置", "座席")
    location = has(q, "何ページ", "ページ番号", "何章", "章番号", "何枚目")
    format_extract = has(q, "太字", "下線", "イタリック", "ハイライト", "赤字", "赤で強調", "マーカー", "コメントがついて")
    notebook = has(q, ".ipynb", "notebook", "ノートブック")
    code = has(q, ".py", "分析コード", "コードにおいて", "実装設定", "関数", "dtype")
    identifier = bool(re.search(r"(?:ID|ＩＤ|マイルストーン|アクション|タスク)\s*[:：]?\s*[A-Z]{1,5}[-_ ]?\d+", q, re.I))
    calc = has(q, "計算", "算出", "合計", "平均", "割合", "差額", "何倍", "改善幅", "相関係数", "最も高い", "最も低い", "カウント数", "上昇率", "予測値", "F1 スコア", "いくつありますか", "全部で何人", "合計でいくつ")
    cross = infer_source_shape(q)[0] in {"multiple", "all_matching"}

    if version:
        primary = "version_diff"; operations = ["version_diff", "evidence_verification"]
    elif spatial:
        primary = "vision_spatial"; operations = ["vision_spatial", "evidence_verification"]
    elif chart:
        primary = "chart_reading"; operations = ["chart_reading"] + (["calculation"] if calc else []) + ["evidence_verification"]
    elif location:
        primary = "location_lookup"; operations = ["document_lookup", "location_lookup", "evidence_verification"]
    elif format_extract:
        primary = "format_extraction"; operations = ["format_extraction"] + (["calculation"] if calc else ["verbatim_extraction"]) + ["evidence_verification"]
    elif notebook:
        primary = "notebook_inspection"; operations = ["notebook_inspection"] + (["calculation"] if calc else []) + ["evidence_verification"]
    elif code:
        primary = "code_inspection"; operations = ["code_inspection"] + (["calculation"] if calc else []) + ["evidence_verification"]
    elif identifier and has(q, "そのまま", "抜き出", "内容"):
        primary = "identifier_verbatim"; operations = ["identifier_lookup", "verbatim_extraction", "evidence_verification"]
    elif calc and cross:
        primary = "cross_file_calculation"; operations = ["cross_file_aggregation", "calculation", "evidence_verification"]
    elif calc:
        primary = "calculation"; operations = ["table_lookup", "table_filter", "table_aggregation", "calculation", "evidence_verification"]
    elif has(q, "役割", "担当する人", "担当者", "主担当者", "フルネーム"):
        primary = "semantic_role_lookup"; operations = ["semantic_document_lookup", "verbatim_extraction", "evidence_verification"]
    elif has(q, "未完", "未達成", "open", "完了となっていない", "ステータス", "残余リスク"):
        primary = "semantic_status_lookup"; operations = ["semantic_document_lookup", "list_extraction", "evidence_verification"]
    elif has(q, "スコープ", "対象外", "対象範囲", "分類"):
        primary = "semantic_scope_lookup"; operations = ["semantic_document_lookup", "verbatim_extraction", "evidence_verification"]
    elif has(q, "すべて", "一覧", "全部", "挙げて", "抽出してください"):
        primary = "semantic_list_extraction"; operations = ["semantic_document_lookup", "list_extraction", "evidence_verification"]
    else:
        primary = "semantic_fact_lookup"; operations = ["semantic_document_lookup", "verbatim_extraction", "evidence_verification"]

    if calc and primary != "calculation" and "calculation" not in operations:
        secondary.append("calculation")
    if cross and primary != "cross_file_calculation":
        secondary.append("multi_source_resolution")
    if format_extract and primary != "format_extraction":
        secondary.append("format_extraction")
    if notebook and primary != "notebook_inspection":
        secondary.append("notebook_inspection")
    if code and primary != "code_inspection":
        secondary.append("code_inspection")
    return primary, list(dict.fromkeys(secondary)), operations


def capability_group(primary: str) -> str:
    if primary.startswith("semantic_"):
        return "external_llm_semantic_candidate_selection"
    if primary == "cross_file_calculation":
        return "cross_file_calculation"
    if primary == "calculation":
        return "remaining_calculation"
    if primary in {"chart_reading", "vision_spatial"}:
        return "vision_chart_reading"
    if primary == "notebook_inspection":
        return "notebook_remaining"
    return primary


DIFFICULTY = {
    "external_llm_semantic_candidate_selection": 4, "remaining_calculation": 3,
    "cross_file_calculation": 5, "version_diff": 5, "vision_chart_reading": 5,
    "notebook_remaining": 3, "location_lookup": 2, "format_extraction": 2,
    "code_inspection": 2, "identifier_verbatim": 2,
}
RISK = {
    "external_llm_semantic_candidate_selection": 4, "remaining_calculation": 2,
    "cross_file_calculation": 3, "version_diff": 4, "vision_chart_reading": 4,
    "notebook_remaining": 2, "location_lookup": 2, "format_extraction": 2,
    "code_inspection": 2, "identifier_verbatim": 2,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--valid-run", default="semantic_phase_fresh_v2")
    parser.add_argument("--test-run", default="semantic_phase_test_shadow_v2")
    parser.add_argument("--run-id", default="capability_matrix_130_v1")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "data/output" / args.run_id / "analysis"
    output.mkdir(parents=True, exist_ok=True)

    datasets = {
        "valid": root / "data/raw/share/share/質問回答/questions_valid.csv",
        "test": root / "data/raw/share/share/質問回答/questions_test.csv",
    }
    run_names = {"valid": args.valid_run, "test": args.test_run}
    rows: list[dict[str, Any]] = []
    questions_by_capability: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for dataset, question_path in datasets.items():
        run = run_names[dataset]
        questions = read_csv(question_path)
        analyses = {int(item["index"]): item for item in read_jsonl(root / "data/work" / run / "planning/question_analysis.jsonl")}
        plans = {int(item["question_id"]): item for item in read_jsonl(root / "data/work" / run / "planning/final_source_plans.jsonl")}
        answers = {int(item["question_id"]): item for item in read_jsonl(root / "data/output" / run / "answer_results.jsonl")}
        evaluations = {int(item["question_id"]): item for item in read_csv(root / "data/output" / run / "evaluation/valid_evaluation.csv")} if dataset == "valid" else {}
        candidate_counts = Counter(int(item["question_id"]) for item in read_jsonl(root / "data/work" / run / "planning/deterministic_candidates.jsonl"))

        for raw in questions:
            qid = int(raw["index"]); question = raw["question"]; analysis = analyses.get(qid, {}); plan = plans.get(qid, {}); answer = answers.get(qid, {})
            primary, secondary, operations = classify(question)
            group = capability_group(primary)
            source_cardinality, source_relation = infer_source_shape(question)
            source_reqs = plan.get("source_requirements") or []
            required_projects = list(dict.fromkeys(project for req in source_reqs for project in req.get("project_candidates", [])))
            roles = list(dict.fromkeys(infer_roles(question) + [role for req in source_reqs for role in req.get("document_roles", []) if role]))
            file_types = list(dict.fromkeys(infer_file_types(question) + analysis.get("required_file_types", [])))
            selected = plan.get("final_selected_file_ids") or answer.get("selected_file_ids") or []
            valid_eval = evaluations.get(qid, {})
            if dataset == "valid":
                if str(valid_eval.get("normalized_match", "")).lower() == "true": result = "correct"
                elif str(valid_eval.get("answered", "")).lower() == "true": result = "incorrect"
                else: result = "blank"
            else:
                result = "not_applicable"
            semantic = primary.startswith("semantic_") or primary == "version_diff"
            calculation = "calculation" in operations
            vision = primary in {"chart_reading", "vision_spatial"}
            difficulty = DIFFICULTY.get(group, 3); risk = RISK.get(group, 3)
            reuse = 5 if group in {"external_llm_semantic_candidate_selection", "remaining_calculation", "cross_file_calculation", "vision_chart_reading"} else 4
            matrix_row = {
                "dataset": dataset, "question_id": qid, "question_original": question,
                "primary_question_type": primary, "secondary_question_types": " | ".join(secondary),
                "required_file_types": " | ".join(file_types), "required_document_roles": " | ".join(roles),
                "required_operations": " | ".join(operations), "source_cardinality": source_cardinality,
                "source_relation": source_relation, "required_projects": " | ".join(required_projects),
                "semantic_reasoning_required": semantic, "calculation_required": calculation,
                "vision_required": vision, "multimodal_required": vision and any(t in file_types for t in ("pptx", "pdf", "xlsx", "ipynb")),
                "current_executor": " | ".join(answer.get("operations_executed", [])),
                "current_status": answer.get("status", "not_run"), "failure_stage": answer.get("failure_stage", ""),
                "candidate_file_count": candidate_counts[qid], "selected_file_count": len(selected),
                "valid_answer_available": dataset == "valid", "current_valid_result": result,
                "estimated_implementation_difficulty": difficulty, "estimated_error_risk": risk,
                "estimated_reusability": reuse, "estimated_test_frequency": 0, "priority_score": 0.0,
            }
            rows.append(matrix_row); questions_by_capability[group].append(matrix_row)

    test_frequency = Counter(capability_group(row["primary_question_type"]) for row in rows if row["dataset"] == "test")
    for row in rows:
        group = capability_group(row["primary_question_type"])
        row["estimated_test_frequency"] = test_frequency[group]
        measurable = 1.0 if any(item["dataset"] == "valid" for item in questions_by_capability[group]) else 0.45
        deterministic = 0.95 if group in {"remaining_calculation", "location_lookup", "code_inspection", "notebook_remaining"} else 0.75 if group in {"cross_file_calculation", "version_diff"} else 0.55
        row["priority_score"] = round((test_frequency[group] + 1) * measurable * row["estimated_reusability"] * deterministic / (row["estimated_error_risk"] * row["estimated_implementation_difficulty"]), 4)
    write_csv(output / "capability_matrix_all_130.csv", rows, CAPABILITY_COLUMNS)

    summary_rows: list[dict[str, Any]] = []
    groups = sorted({capability_group(row["primary_question_type"]) for row in rows})
    for group in groups:
        items = questions_by_capability[group]
        valid_items = [r for r in items if r["dataset"] == "valid"]
        test_items = [r for r in items if r["dataset"] == "test"]
        correct = sum(r["current_valid_result"] == "correct" for r in valid_items)
        summary_rows.append({
            "capability": group, "valid_question_count": len(valid_items), "test_question_count": len(test_items),
            "valid_correct_count": correct, "valid_blank_or_incorrect_count": len(valid_items) - correct,
            "current_coverage": round(correct / len(valid_items), 3) if valid_items else 0.0,
            "implementation_status": "implemented" if valid_items and correct == len(valid_items) else "partial" if correct else "not_verified",
            "vision_required_count": sum(bool(r["vision_required"]) for r in items),
            "multi_source_count": sum(r["source_cardinality"] != "single" for r in items),
        })
    write_csv(output / "capability_summary.csv", summary_rows)

    comparison = [{
        "capability": row["capability"], "valid_count": row["valid_question_count"], "valid_share": round(row["valid_question_count"] / 30, 3),
        "test_count": row["test_question_count"], "test_share": round(row["test_question_count"] / 100, 3),
        "test_minus_valid_share": round(row["test_question_count"] / 100 - row["valid_question_count"] / 30, 3),
    } for row in summary_rows]
    write_csv(output / "valid_test_distribution_comparison.csv", comparison)

    priority_rows: list[dict[str, Any]] = []
    candidate_groups = ["external_llm_semantic_candidate_selection", "remaining_calculation", "cross_file_calculation", "version_diff", "vision_chart_reading", "notebook_remaining"]
    for group in candidate_groups:
        items = questions_by_capability.get(group, [])
        valid_items = [r for r in items if r["dataset"] == "valid"]
        test_items = [r for r in items if r["dataset"] == "test"]
        correct = sum(r["current_valid_result"] == "correct" for r in valid_items)
        difficulty = DIFFICULTY[group]; risk = RISK[group]
        valid_measurability = 1.0 if valid_items else 0.35
        synthetic = 0.9 if group != "external_llm_semantic_candidate_selection" else 0.7
        silver = 0.9 if group in {"remaining_calculation", "cross_file_calculation", "notebook_remaining"} else 0.6
        verifiability = 0.95 if group in {"remaining_calculation", "cross_file_calculation", "notebook_remaining"} else 0.75 if group == "version_diff" else 0.6
        success = 0.85 if group in {"remaining_calculation", "notebook_remaining"} else 0.7 if group in {"cross_file_calculation", "version_diff"} else 0.55
        reuse = 5
        unresolved_valid = max(0, len(valid_items) - correct)
        score = (len(test_items) + 1) * valid_measurability * reuse * verifiability * success / (difficulty * risk)
        priority_rows.append({
            "capability": group, "valid_question_count": len(valid_items), "test_question_count": len(test_items),
            "current_coverage": round(correct / len(valid_items), 3) if valid_items else 0.0,
            "valid_measurability": valid_measurability, "synthetic_testability": synthetic,
            "silver_testability": silver, "shadow_gold_required": group in {"external_llm_semantic_candidate_selection", "version_diff", "vision_chart_reading"},
            "implementation_difficulty": difficulty, "error_risk": risk,
            "expected_score_gain": round(unresolved_valid * success, 2), "expected_test_coverage_gain": round(len(test_items) * success, 2),
            "priority_score": round(score, 4), "recommended_order": 0,
        })
    priority_rows.sort(key=lambda row: row["priority_score"], reverse=True)
    for order, row in enumerate(priority_rows, 1): row["recommended_order"] = order
    write_csv(output / "vertical_slice_priority.csv", priority_rows)

    by_valid = Counter(row["primary_question_type"] for row in rows if row["dataset"] == "valid")
    by_test = Counter(row["primary_question_type"] for row in rows if row["dataset"] == "test")
    vision_count = sum(bool(row["vision_required"]) for row in rows)
    multi_count = sum(row["source_cardinality"] != "single" for row in rows)
    calc_count = sum(bool(row["calculation_required"]) for row in rows)
    semantic_count = sum(bool(row["semantic_reasoning_required"]) for row in rows)
    valid_overrepresented = sorted(comparison, key=lambda row: row["test_minus_valid_share"])[:3]
    test_overrepresented = sorted(comparison, key=lambda row: row["test_minus_valid_share"], reverse=True)[:3]
    gap_lines = [
        "# Capability Gap Analysis", "",
        "## 集計の読み方", "", "件数は質問の主能力で集計し、副能力はCapability Matrixのsecondary列に保持しています。validの正解は開発・回帰指標であり、汎化性能の証明には使用しません。", "",
        "## validに多い能力", "", *[f"- {key}: {value}問" for key, value in by_valid.most_common()], "",
        "## testに多い能力", "", *[f"- {key}: {value}問" for key, value in by_test.most_common()], "",
        "## 主要ギャップ", "",
        f"- Vision必須: {vision_count}問", f"- 複数資料必須: {multi_count}問", f"- 計算必須: {calc_count}問", f"- Semantic LLMが有効: {semantic_count}問", "",
        "### validに比べtestで比率が高い能力", "", *[f"- {row['capability']}: {row['test_minus_valid_share']:+.3f}" for row in test_overrepresented], "",
        "### testに比べvalidで比率が高い能力", "", *[f"- {row['capability']}: {row['test_minus_valid_share']:+.3f}" for row in valid_overrepresented], "",
        "- testでは、版差分、図表読取、意味選択、書式抽出の比重が相対的に高い。", "- validだけでは、Vision、複数資料の関係解決、版差分の誤許可率を十分に評価できない。", "",
        "## 評価セット方針", "", "- Synthetic: 版ペア、曖昧候補、複数資料関係、Vision負例。", "- Silver: 表計算、Pivot、Notebook、コード設定、単一資料の位置抽出。", "- Shadow Gold: semantic意味選択、Vision、業務上の実質変更判定。", "",
        "## 現在の対応状況", "", "- 対応済み: 表計算、書式抽出、識別子原文、コードAST、Pivot、Markdown定義、Notebook保存出力、決定的semantic fact、章位置。", "- 部分対応: semantic role/status/scope/list、残り計算、Notebook。", "- 未対応: cross-file calculation、version diff、Vision/chart reading、複数資料semantic照合。",
    ]
    (output / "capability_gap_analysis.md").write_text("\n".join(gap_lines) + "\n", encoding="utf-8")

    top = priority_rows[0]
    report = [
        "# Recommended Next Phase", "", f"## 推奨能力: {top['capability']}", "",
        f"- 対象valid: {top['valid_question_count']}問", f"- 対象test: {top['test_question_count']}問",
        f"- 優先度スコア: {top['priority_score']}", f"- 期待valid増分: {top['expected_score_gain']}", f"- 期待testカバレッジ増分: {top['expected_test_coverage_gain']}", "",
        "## 選定理由", "", "test出現頻度、validでの測定可能性、再利用性、Evidenceによる検証可能性を、実装難度と誤答リスクで割った共通式で最上位になりました。", "",
        "## 必要な評価", "", "- valid回帰: 既存16問を維持し誤答0。", "- Synthetic: 正例に加え、曖昧な資料関係と入力不足を抑制。", "- Silver: raw資料から別条件を自動生成し、決定的正解と照合。", "- test Shadow Gold: Gate許可回答の意味的妥当性を正式パイプライン外で確認。", "",
        "## 注意", "", "この推奨はCapability Matrixの集計結果であり、本スクリプトは新規Executorを実装・有効化していません。",
    ]
    (output / "recommended_next_phase.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    git_base = ["git", "-c", "safe.directory=E:/PC/デスクトップ/SIGNATE/SIGNATE_Agentic_RAG"]
    commands = {
        "pre_capability_git_status.txt": git_base + ["status", "--short"],
        "pre_capability_diff_stat.txt": git_base + ["diff", "--stat"],
        "pre_capability_diff.patch": git_base + ["diff"],
        "pre_capability_changed_files.txt": git_base + ["diff", "--name-only"],
    }
    for name, command in commands.items():
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (output / name).write_text(completed.stdout + completed.stderr, encoding="utf-8")

    print(json.dumps({"run_id": args.run_id, "matrix_rows": len(rows), "valid_rows": sum(r['dataset'] == 'valid' for r in rows), "test_rows": sum(r['dataset'] == 'test' for r in rows), "recommended": top['capability'], "output": str(output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
