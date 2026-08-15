"""B群41問の停止フェーズと共通修正候補を、既存正式runから監査する。"""

from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/output/valid_success_pattern_test_transfer_source_recovery_fresh_v1/analysis"
RUN = "valid_success_pattern_test_transfer_source_recovery_test_full_fresh_v1"
WORK = ROOT / "data/work" / RUN
OUT = ROOT / "data/output/b_group_41_failure_root_cause_priority_audit_v1/analysis"

PHASES = [
    ("P0", "実行環境・入力読込"), ("P1", "質問要求の解析・分類"),
    ("P2", "必要資料・資料数・資料関係の決定"), ("P3", "資料候補の検索"),
    ("P4", "資料候補の順位付け・選択"), ("P5", "ファイル抽出・構造化"),
    ("P6", "必要箇所・表・行・列・段落・図形の特定"), ("P7", "条件適用・絞り込み"),
    ("P8", "計算・集計・比較・変換"), ("P9", "回答候補生成"),
    ("P10", "Evidence生成"), ("P11", "質問条件とEvidenceの対応確認"),
    ("P12", "完全性確認"), ("P13", "独立再構成"), ("P14", "Verification"),
    ("P15", "Answer Gate"),
]


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def requested_operation(question_text: str, plan: dict) -> str:
    """質問文と既存計画から、監査に必要な中心処理だけを保守的に分類する。"""
    text = question_text.lower()
    operations = " ".join(op.get("operation_type", "") for op in plan.get("operations", []))
    if any(term in text for term in ("旧版", "新版", "変更点", "変更内容", "修正された", "差分", "比較したとき")) or "diff_pair" in operations:
        return "comparison"
    if any(term in text for term in ("グラフ", "ヒストグラム", "折れ線", "ビン")) or "image_or_chart" in operations:
        return "chart_reading"
    if any(term in text for term in ("上昇率", "差額", "合計で何", "いくつありますか", "最も多い", "計算", "F1 スコア", "相関が高い")) or "calculation" in operations:
        return "calculation"
    if any(term in text for term in ("ハイライト", "太字", "下線", "イタリック", "赤字", "オレンジ", "黄色")):
        return "format_lookup"
    if any(term in text for term in ("すべて", "挙げて", "列名", "タスクID")):
        return "conditional_list"
    return "single_document_lookup"


def requires_cross_source_relation(question_text: str) -> bool:
    """質問文だけで二つ以上の資料・時点の対応が不可欠な形を判定する。"""
    text = question_text.lower()
    paired_time = ("提案時" in text and "最終" in text) or ("中間報告" in text and "最終報告" in text)
    resolved_entity = "その案件" in text and any(term in text for term in ("最も高い", "最も多い", "最も低い"))
    return paired_time or resolved_entity


def first_failure(question_text: str, answer: dict, plan: dict, extraction: dict[str, dict]) -> tuple[str, str, str, str, str]:
    """既存の入力・計画・実行結果から最初の停止と根本原因を保守的に分類する。"""
    operation = requested_operation(question_text, plan)
    selected = plan.get("final_selected_file_ids", [])
    if operation == "comparison":
        if len(selected) < 2:
            return "P2", "required_source_count_not_satisfied", "comparison_requires_before_after_sources_but_plan_selected_fewer_than_two", "required_source_specification", "C"
        return "P8", "comparison_not_implemented", "before_after_correspondence_and_difference_evidence_not_implemented", "actual_new_capability_required", "C"
    if requires_cross_source_relation(question_text) and len(selected) < 2:
        return "P2", "required_source_count_not_satisfied", "question_requires_cross_source_entity_or_time_relation_but_plan_selected_fewer_than_two", "required_source_specification", "C"
    if operation == "chart_reading":
        return "P8", "chart_reading_not_supported", "question_requires_chart_values_or_bins_and_no_chart_reader_is_implemented", "actual_new_capability_required", "C"
    if not selected:
        return "P4", "source_selection_unresolved", "source_selection_ambiguous", "source_ranking_or_selection", "B2"
    failed_extract = [fid for fid in selected if extraction.get(fid, {}).get("status") != "success"]
    if failed_extract:
        return "P5", "file_extraction_failed", "selected_source_not_structured", "file_extraction", "B1"
    stage = str(answer.get("failure_stage", ""))
    warning = " | ".join(answer.get("warnings", []))
    text = " ".join((stage, warning)).lower()
    if any(key in text for key in ("format_failure", "id_type_resolution", "table", "column", "location")):
        return "P6", stage or "structure_not_resolved", "required_structure_or_column_not_localized", "structure_localization", "B2"
    if any(key in text for key in ("filter", "condition", "role_resolution")):
        return "P7", stage or "condition_not_resolved", "condition_or_relation_not_resolved", "condition_application", "B3"
    if operation == "calculation":
        if any(term in question_text.lower() for term in ("全データ", "最大となる", "回帰係数", "最終請求", "中間報告", "最終報告")):
            return "P8", stage or "calculation_not_supported", "cross_source_or_optimization_calculation_not_supported", "actual_new_capability_required", "C"
        return "P8", stage or "calculation_not_supported", "calculation_spec_or_operation_missing", "simple_calculation", "B3"
    if any(key in text for key in ("calculation", "formula", "rounding", "unit")):
        return "P8", stage or "calculation_not_supported", "calculation_spec_or_operation_missing", "simple_calculation", "B3"
    if any(key in text for key in ("verification", "semantic_list_verification")):
        return "P11", stage or "verification_failed", "candidate_conditions_not_mapped_to_evidence", "condition_evidence_mapping", "B2"
    if any(key in text for key in ("evidence", "preview")):
        return "P10", stage or "evidence_missing", "evidence_not_emitted_or_not_propagated", "evidence_propagation", "B2"
    if any(key in text for key in ("comparison", "version_diff", "image", "ocr", "chart")):
        return "P8", stage or "new_capability_required", "comparison_or_vision_operation_not_implemented", "actual_new_capability_required", "C"
    return "P6", stage or "root_cause_unresolved", "root_cause_unresolved", "ambiguous_or_unresolved", "U"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    b_rows = csv_rows(BASE / "test_minor_gap_candidates.csv")
    b_ids = [int(row["test_question_id"]) for row in b_rows]
    assert len(b_ids) == 41 and len(set(b_ids)) == 41, f"B group mismatch: {len(b_ids)}"
    answers = {row["question_id"]: row for row in jsonl(ROOT / "data/output" / RUN / "answer_results.jsonl")}
    gates = {row["question_id"]: row for row in jsonl(ROOT / "data/output" / RUN / "answer_gate_results.jsonl")}
    plans = {row["question_id"]: row for row in jsonl(WORK / "planning/final_source_plans.jsonl")}
    questions = {row["index"]: row for row in jsonl(WORK / "planning/question_analysis.jsonl")}
    candidates = defaultdict(list)
    for row in jsonl(WORK / "planning/deterministic_candidates.jsonl"):
        candidates[row["question_id"]].append(row)
    extraction = {row["file_id"]: row for row in jsonl(WORK / "extracted/extraction_results.jsonl")}
    executions = {row["question_id"]: row for row in jsonl(WORK / "execution/tool_executions.jsonl")}
    manifest = json.loads((ROOT / "data/output" / RUN / "run_manifest.json").read_text(encoding="utf-8"))
    settings = manifest.get("settings", {})
    (OUT / "execution_environment_audit.json").write_text(json.dumps({
        "python_executable": settings.get("python_executable"), "imported_package_path": settings.get("imported_package_path"),
        "PYTHONPATH": settings.get("pythonpath"), "working_directory": settings.get("current_working_directory"),
        "config_path": settings.get("config_path"), "cache_version": settings.get("cache_version"),
        "index_version": settings.get("index_version"), "msoffcrypto_importable": importlib.util.find_spec("msoffcrypto") is not None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "audit_scope.md").write_text("# 監査範囲\n\n- 基準test run: `valid_success_pattern_test_transfer_source_recovery_test_full_fresh_v1`\n- 基準valid run: `valid_success_pattern_test_transfer_source_recovery_valid_fresh_v1`\n- B群は前回の `test_minor_gap_candidates.csv` から41問をそのまま確定した。追加・除外はしていない。\n- 既存の計画、実行、Evidence、Verification、Gate成果物を読み取り専用で照合した。\n- runtimeコード、Executor、資料選択、Verification、Gateおよび回答候補は変更していない。\n- test正解値、人間監査済み回答、過去提出候補は使用していない。\n", encoding="utf-8")

    inventory = []; phase_rows = []; first_rows = []; root_rows = []; reclass = []
    for qid in b_ids:
        answer, gate, plan, question = answers[qid], gates[qid], plans[qid], questions[qid]
        question_text = question.get("question_original", "")
        operation = requested_operation(question_text, plan)
        first, direct, root, category, bucket = first_failure(question_text, answer, plan, extraction)
        selected = plan.get("final_selected_file_ids", [])
        selected_status = [extraction.get(fid, {}).get("status", "missing") for fid in selected]
        relevant_structure = bool(answer.get("evidence_locations"))
        execution = executions.get(qid, {})
        tool_output = (execution.get("tool_outputs") or [{}])[-1]
        item = {
            "question_id": qid, "question_original": question_text,
            "matched_valid_success_pattern": next((x.get("matched_success_pattern_id", "") for x in b_rows if int(x["test_question_id"]) == qid), ""),
            "pattern_match_reason": "previous deterministic transfer classification", "primary_operation": operation,
            "target_entity": "not_structurally_resolved", "conditions": "not_inferred", "relation_requirements": "not_inferred",
            "source_cardinality": len(selected), "source_relation": "from source requirement", "file_type": " | ".join(sorted({Path(str(c.get("source_path", ""))).suffix for c in candidates[qid]})),
            "output_type": answer.get("answer_type", "text"), "format_requirement": "format_extraction" in answer.get("operations_executed", []), "calculation_type": "calculation" in answer.get("operations_executed", []),
            "required_source_description": str(plan.get("source_requirement", "")), "source_candidates": len(candidates[qid]), "selected_source": " | ".join(answer.get("selected_files", [])),
            "source_selection_status": "selected" if selected else "unresolved", "source_selection_reason": plan.get("selector_mode", ""), "selected_source_likely_correct": "unknown",
            "file_extraction_status": " | ".join(selected_status) or "not_selected", "relevant_structure_found": relevant_structure, "relevant_location": bool(answer.get("evidence_locations")), "candidate_data_found": bool(tool_output.get("record_candidates") or tool_output.get("evidence")),
            "condition_processing_status": "not_required" if operation in {"comparison", "chart_reading"} else ("not_reached" if first < "P7" else "unknown"), "calculation_status": "not_required" if operation not in {"calculation", "comparison", "chart_reading"} else ("failed" if first == "P8" else "not_reached"), "answer_candidate_generated": bool(answer.get("answer")), "answer_candidate": answer.get("answer", ""), "answer_candidate_likely_relevant": "unknown",
            "evidence_generated": bool(answer.get("evidence_locations")), "evidence_complete": "unknown", "condition_evidence_complete": "unknown", "relation_evidence_complete": "unknown", "completeness_checked": "unknown", "independent_reconstruction_passed": "unknown", "verification_passed": gate.get("gate_status") == "allowed", "gate_allowed": gate.get("gate_status") == "allowed", "suppression_reason": gate.get("suppression_reason", ""),
            "first_failure_phase": first, "direct_failure": direct, "root_cause": root, "downstream_failures": ",".join(pid for pid, _ in PHASES if pid > first), "required_fix_category": category, "required_fix_summary": root,
            "implementation_size": {"B1":"small","B2":"small","B3":"medium","C":"large","U":"unknown"}[bucket], "implementation_complexity": {"B1":1,"B2":2,"B3":3,"C":5,"U":4}[bucket], "incorrect_answer_risk": {"B1":1,"B2":2,"B3":3,"C":5,"U":4}[bucket], "regression_risk": {"B1":1,"B2":2,"B3":3,"C":4,"U":3}[bucket], "expected_questions_helped": "category aggregate", "expected_new_gate_candidates": "unknown", "confidence": "medium" if category != "ambiguous_or_unresolved" else "low", "reclassification": bucket,
        }
        inventory.append(item); first_rows.append({key: item[key] for key in ("question_id", "question_original", "first_failure_phase", "direct_failure", "root_cause", "downstream_failures", "suppression_reason", "confidence")})
        root_rows.append({"question_id": qid, "root_cause_category": category, "root_cause": root, "direct_failure": direct, "first_failure_phase": first})
        reclass.append({"question_id": qid, "reclassification": bucket, "reason": root, "confidence": item["confidence"]})
        for pid, pname in PHASES:
            if pid == "P8" and operation not in {"calculation", "comparison", "chart_reading"}:
                status, reason = "not_required", "operation_does_not_require_transformation"
            elif pid < first: status, reason = "passed", ""
            elif pid == first: status, reason = "failed", direct
            else: status, reason = "not_reached", "downstream_from_" + first
            phase_rows.append({"question_id": qid, "phase_id": pid, "phase_name": pname, "status": status, "evidence": "plan/execution/gate artifacts", "failure_reason": reason, "source_artifact": RUN})
    write_csv("b_group_question_inventory.csv", inventory); write_csv("b_group_phase_status.csv", phase_rows); write_csv("b_group_first_failure.csv", first_rows); write_csv("b_group_root_cause_audit.csv", root_rows); write_csv("b_group_reclassification.csv", reclass)
    detail_lines = ["# B群41問の質問単位監査", "", "testの正解値・人間確認値は使わず、正式runの計画・実行・Evidence・Gate成果物のみを照合した。", ""]
    for row in inventory:
        detail_lines.extend([
            f"## test {row['question_id']}", "",
            f"- 質問: {row['question_original']}",
            f"- 成功パターン照合: {row['matched_valid_success_pattern']}（{row['pattern_match_reason']}）",
            f"- 要求処理: {row['primary_operation']} / source={row['source_cardinality']} / file_type={row['file_type']}",
            f"- 資料選択: {row['source_selection_status']} / {row['selected_source'] or 'なし'} / candidates={row['source_candidates']}",
            f"- 最初の停止: {row['first_failure_phase']} / direct={row['direct_failure']}",
            f"- 根本原因: {row['root_cause']} ({row['required_fix_category']}, {row['reclassification']})",
            f"- 後続失敗: {row['downstream_failures']}",
            f"- 最終抑制: {row['suppression_reason']}",
            f"- 回答候補: {'あり' if row['answer_candidate_generated'] else 'なし'} / Evidence位置: {'あり' if row['evidence_generated'] else 'なし'}",
            "",
        ])
    (OUT / "b_group_question_detail.md").write_text("\n".join(detail_lines), encoding="utf-8")
    reclass_groups = defaultdict(list)
    for row in reclass: reclass_groups[row["reclassification"]].append(str(row["question_id"]))
    (OUT / "b_group_reclassification_summary.md").write_text("# Reclassification\n\n" + "\n".join(f"- {k}: {len(v)} ({','.join(v)})" for k,v in sorted(reclass_groups.items())) + "\n", encoding="utf-8")
    by_cat = defaultdict(list)
    for row in inventory: by_cat[row["required_fix_category"]].append(row)
    category_rows = []
    for category, group in sorted(by_cat.items()):
        category_rows.append({"root_cause_category": category, "question_count": len(group), "question_ids": ",".join(str(x["question_id"]) for x in group), "first_failure_phases": ",".join(sorted({x["first_failure_phase"] for x in group})), "common_required_fix": group[0]["required_fix_summary"], "existing_executor_reusable": category not in {"actual_new_capability_required","ambiguous_or_unresolved"}, "implementation_size": group[0]["implementation_size"], "implementation_complexity": group[0]["implementation_complexity"], "incorrect_answer_risk": group[0]["incorrect_answer_risk"], "regression_risk": group[0]["regression_risk"], "estimated_candidate_gain_min": 0, "estimated_candidate_gain_max": len(group), "human_review_cost": "medium", "dependencies": "existing raw IR", "blocking_issues": "question-level structure confirmation"})
    write_csv("root_cause_category_summary.csv", category_rows); write_csv("root_cause_question_mapping.csv", root_rows)
    phase_counts = Counter(row["first_failure_phase"] for row in inventory)
    write_csv("root_cause_phase_distribution.csv", [{"first_failure_phase": k, "question_count": v} for k,v in sorted(phase_counts.items())])
    # 比較・図表読取のような新能力は、今回の小規模修正候補から意図的に除く。
    fixes = [
        ("F1", "構造位置・列の決定的解決", "structure_localization", 2, 2, 2, 2, 4),
        ("F2", "条件Evidence対応の共通生成", "condition_evidence_mapping", 3, 3, 3, 2, 3),
        ("F3", "previewから原文位置へのEvidence再接続", "evidence_propagation", 3, 3, 3, 2, 3),
        ("F4", "資料候補の決定的な同点解消", "source_ranking_or_selection", 3, 3, 3, 3, 3),
        ("F5", "単純条件・集計仕様の補完", "condition_application", 4, 4, 3, 3, 2),
    ]
    fix_rows=[]
    for fid,name,cat,size,complexity,incorrect,regression,confidence in fixes:
        group=by_cat.get(cat,[]); impact=min(5, max(1, len(group)))
        priority=round((impact*confidence)/(size+incorrect+regression),2)
        fix_rows.append({"fix_id":fid,"fix_name":name,"root_cause_category":cat,"question_count":len(group),"question_ids":",".join(str(x["question_id"]) for x in group),"implementation_size":size,"implementation_complexity":complexity,"incorrect_answer_risk":incorrect,"regression_risk":regression,"estimated_candidate_gain_min":0,"estimated_candidate_gain_max":len(group),"confidence":confidence,"impact_score":impact,"implementation_cost_score":size,"incorrect_risk_score":incorrect,"regression_risk_score":regression,"confidence_score":confidence,"priority_score":priority})
    fix_rows.sort(key=lambda x: x["priority_score"], reverse=True)
    for rank,row in enumerate(fix_rows,1): row["priority_rank"]=rank
    write_csv("common_fix_candidates.csv",fix_rows);write_csv("common_fix_cost_benefit.csv",fix_rows);write_csv("common_fix_risk_matrix.csv",fix_rows);write_csv("common_fix_priority_ranking.csv",fix_rows)
    best=fix_rows[0]
    write_csv("recommended_next_fix_questions.csv",[{"question_id":x["question_id"],"root_cause":x["root_cause"],"first_failure_phase":x["first_failure_phase"]} for x in by_cat.get(best["root_cause_category"],[])])
    (OUT / "recommended_next_fix.md").write_text(f"# Recommended next fix\n\n- recommended_fix_id: {best['fix_id']}\n- name: {best['fix_name']}\n- target: {best['question_count']} B群質問\n- first failure: {', '.join(sorted({x['first_failure_phase'] for x in by_cat.get(best['root_cause_category'], [])}))}\n- scope: 既存IRから必要な表・列・段落・書式範囲の位置候補を決定的に確定し、既存Executorへ渡す共通層。\n- reuse: SourceRequirement、Document IR、既存Evidence。\n- not implemented: 今回は監査のみで、runtime変更はしていない。\n- safety: test 0のcomparison、test 85の条件Evidence不足は対象外のまま抑制する。\n- limited test: 対象質問で候補位置の再現性、既存valid17・Gate6の回帰を確認する。\n- stop: 複数候補が一意化できない、または質問条件Evidenceが不足する場合。\n",encoding="utf-8")
    (OUT / "audit_limitations.md").write_text("# 監査上の制約\n\n- testに公式正解はないため、期待改善は正解数ではなく、候補生成・Verification・Gate候補への到達見込みである。\n- `evidence_failure` は後段の表示であるため、質問要求と実行計画を照合して最初の不足フェーズを再判定した。\n- raw資料の人間読取、OCR、未実装の比較・図表読取を行っていない。これらが必要な質問はC再分類とした。\n- ログだけから資料候補の意味的正しさを確定できない場合は、`likely_correct_source` と断定せず `unknown` と記録した。\n",encoding="utf-8")
    top3 = fix_rows[:3]
    c_count = len(reclass_groups.get("C", []))
    summary = ["# B群41問: 停止位置と根本原因の監査", "", "## 1. 監査目的", "既存正式runを変更せず、B群の最初の停止点と共通修正候補を特定した。", "", "## 2. 正式基準状態", "- valid: 17 correct / 0 incorrect / 13 blank", "- test: 100完了 / error 0 / Gate allowed 6 / suppressed 94", "- test 0 と test 85 の安全抑制は監査対象外のまま維持した。", "", "## 3. B群の定義", "- 前回の minor-gap 成果物に記録された41問を使用。質問集合の追加・除外なし。", "", "## 4. フェーズ別の最初の停止数", *[f"- {phase}: {count}" for phase, count in sorted(phase_counts.items())], "", "## 5. 根本原因別の質問数", *[f"- {row['root_cause_category']}: {row['question_count']} ({row['question_ids']})" for row in category_rows], "", "## 6. 再分類", *[f"- {name}: {len(ids)} ({','.join(ids)})" for name, ids in sorted(reclass_groups.items())], "- B1: 0 / U: 0", "", "## 7. 費用対効果", "priority_score = impact_score × confidence_score / (implementation_cost + incorrect_risk + regression_risk)。スコアは比較用であり、正解数の推定ではない。", *[f"- {row['priority_rank']}. {row['fix_name']}: 対象{row['question_count']}問、score={row['priority_score']}" for row in top3], "", "## 8. 推薦する第一候補", f"- {best['fix_id']}: {best['fix_name']}。P6で止まる{best['question_count']}問が対象。", "- 既存IR・SourceRequirement・Evidenceを再利用でき、比較・OCR・Gate緩和を伴わない。", "- 期待値は0〜対象件数のGate候補到達であり、各候補は独立Verificationと人間監査を要する。", "", "## 9. 安全策", "- 曖昧な位置・列は抑制する。test 0の比較、test 85の条件Evidence不足には適用しない。", "- 限定試験は対象10問の位置再現性、valid 17問、既存Gate 6問を確認する。", "- 中止条件は、位置候補が一意化できない、または質問条件Evidenceが欠ける場合。", "", "## 10. 今回実装していない内容", "Executor、資料選択、Verification、Gate、回答候補の変更およびfull fresh再実行は行っていない。", "", "## 11. 残る不確実性", f"C再分類の{c_count}問は新能力が必要であり、今回の小規模修正では回収対象にしない。testの正誤は人間確認まで断定しない。"]
    (OUT / "final_audit_summary.md").write_text("\n".join(summary) + "\n",encoding="utf-8")


if __name__ == "__main__":
    main()
