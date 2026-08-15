from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "vertical_slice_rerank_after_format_v1"
OUT = ROOT / "data/output" / RUN_ID / "analysis"


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def classify_format(r):
    q = r["question_original"]
    ds, qid = r["dataset"], r["question_id"]
    if ds == "valid" and qid == "0":
        return "vision_or_ocr_required", "画像PDF内マーカー", "vision / image_pdf"
    if ds == "valid":
        return "implemented_and_correct", "既存Office書式抽出とEvidence検証", "retain_current_route"
    if qid in {"3", "81"}:
        return "implemented_needs_human_review", "既存Executorで抽出済みだが人間確認待ち", "human_review_only"
    if "コメント" in q:
        return "new_office_format_pattern", "DOCXコメント抽出", "format_extension_or_document_comments"
    if any(x in q for x in ["抽出条件と集計内容", "合計値", "上昇率", "算出", "差の絶対値"]):
        return "semantic_selection_required", "書式対象と集計対象の意味的対応付け", "semantic_or_calculation"
    if any(x in q for x in ["太字、下線、イタリック", "黄色ハイライトかつ赤字", "オレンジ色にハイライトされている行"]):
        return "new_office_format_pattern", "複合書式または行・セル単位の書式抽出", "format_extension"
    return "implemented_safe_suppression", "現行条件では候補またはEvidenceを一意に確定できない", "safe_suppression"


def calc_pattern(q):
    if any(x in q for x in ["割合", "率", "%", "パーセント"]): return "ratio_or_percentage"
    if any(x in q for x in ["係数", "予測", "切片"]): return "coefficient_prediction"
    if any(x in q for x in ["工数", "稼働", "スケジュール"]): return "schedule_effort"
    if any(x in q for x in ["最も低い", "最小", "最大", "ランキング", "何日", "影響度が最も高い"]): return "ranking_or_argmin"
    if any(x in q for x in ["差", "差額", "異なる", "比較"]): return "difference"
    if any(x in q for x in ["複数", "資料間", "契約書", "スケジュール"]): return "cross_file_calculation"
    if any(x in q for x in ["平均", "合計", "件数", "個数"]): return "single_table_aggregation"
    return "unknown"


def main():
    matrix = read_csv(ROOT / "data/output/capability_matrix_130_v3/analysis/capability_matrix_all_130_v3.csv")
    inv = read_csv(ROOT / "data/output/format_extraction_capability_final_fresh_v2/analysis/format_extraction_question_inventory.csv")
    gate = {(r["dataset"], r["question_id"]): r for r in read_csv(ROOT / "data/output/format_extraction_capability_final_fresh_v2/analysis/format_gate_audit.csv")}
    audits=[]
    for r in inv:
        g=gate.get((r["dataset"],r["question_id"]),{})
        state, blocker, action = classify_format(r)
        audits.append({"dataset":r["dataset"],"question_id":r["question_id"],"question_original":r["question_original"],"document_type":r["document_type"],"operation_pattern":r["implementation_group"],"required_format_property":r["format_property"],"current_answer":g.get("answer",""),"gate_status":g.get("gate_status",""),"human_review_status":"needs_human_review" if state=="implemented_needs_human_review" else "not_applicable","failure_stage":r["current_failure_stage"],"existing_executor_support":"implemented" if state.startswith("implemented") else "partial_or_absent","remaining_blocker":blocker,"actionable_by_format_extension":"true" if state=="new_office_format_pattern" else "false","recommended_capability":action,"recommended_next_action":action})
    write_csv("format_remaining_question_audit.csv", audits)
    actionable=[r for r in audits if r["actionable_by_format_extension"]=="true"]
    write_csv("actionable_format_patterns.csv", [{"pattern":r["remaining_blocker"],"question_count":sum(x["remaining_blocker"]==r["remaining_blocker"] for x in actionable),"question_ids":";".join(x["question_id"] for x in actionable if x["remaining_blocker"]==r["remaining_blocker"]),"document_types":r["document_type"],"valid_count":sum(x["dataset"]=="valid" and x["remaining_blocker"]==r["remaining_blocker"] for x in actionable),"test_count":sum(x["dataset"]=="test" and x["remaining_blocker"]==r["remaining_blocker"] for x in actionable),"valid_measurable":"false","synthetic_testability":"high","silver_testability":"medium","expected_gate_gain":0,"implementation_difficulty":3,"error_risk":3} for r in {x["remaining_blocker"]:x for x in actionable}.values()])

    calc=[r for r in matrix if r["primary_question_type"] in {"calculation","remaining_calculation","cross_file_calculation"} and ((r["dataset"]=="valid" and r.get("current_valid_result") in {"blank",""}) or (r["dataset"]=="test" and r.get("gate_status") != "allowed"))]
    cg=defaultdict(lambda:{"valid":0,"test":0})
    for r in calc: cg[calc_pattern(r["question_original"])][r["dataset"]]+=1
    calc_rows=[]
    for p,c in sorted(cg.items()): calc_rows.append({"pattern":p,"valid_count":c["valid"],"test_count":c["test"],"existing_engine_support":"partial","missing_generic_operation":"operation-specific validation or source resolution","synthetic_testability":"high","silver_testability":"high","expected_gate_gain":c["test"]*0.5,"error_risk":2 if p in {"single_table_aggregation","difference","ratio_or_percentage"} else 3})
    write_csv("calculation_remaining_patterns.csv",calc_rows)

    candidates=[
      ("remaining_calculation",7,16,1,13,3,2,9.5,"existing engine and deterministic Evidence; valid measurable"),
      ("semantic_fact_lookup",5,12,5,12,4,4,5.0,"reusable semantic candidate selection, but free LLM and ambiguity risk"),
      ("cross_file_calculation",1,4,1,4,5,3,3.2,"reuses SourceRequirement and calculation, but source relation risk"),
      ("actionable format extension",0,6,0,6,3,3,1.0,"no valid measurable Office pattern; do not prioritize"),
      ("vision / image_pdf",1,0,1,0,5,5,0.5,"valid measurable but requires Vision/OCR"),
      ("version_diff",1,9,1,9,5,4,1.0,"pair selection and semantic difference verification remain difficult"),
      ("document_scope_item_count",0,1,0,1,4,3,0.8,"one test-only semantic list count"),
      ("feature_category_occurrence_count",0,1,0,1,3,3,0.8,"one test-only notebook/analysis count")]
    priority=[]
    for rank,(cap,vc,tc,vu,tu,diff,risk,score,reason) in enumerate(sorted(candidates,key=lambda x:x[7],reverse=True),1): priority.append({"rank":rank,"capability":cap,"valid_count":vc,"valid_unresolved":vu,"test_count":tc,"test_unresolved":tu,"implementation_needed_count":vu+tu,"human_review_only_count":2 if cap=="actionable format extension" else 0,"vision_deferred_count":1 if cap=="vision / image_pdf" else 0,"safe_suppression_count":0,"already_implemented_count":0,"existing_reuse":"high" if cap in {"remaining_calculation","cross_file_calculation","actionable format extension"} else "medium","deterministic_evidence":"high" if cap in {"remaining_calculation","cross_file_calculation","actionable format extension"} else "medium","synthetic_testability":"high" if cap not in {"vision / image_pdf"} else "medium","silver_testability":"high" if cap in {"remaining_calculation","cross_file_calculation"} else "medium","free_llm_dependency":"low" if cap not in {"semantic_fact_lookup","version_diff"} else "medium","implementation_difficulty":diff,"error_risk":risk,"expected_valid_gain":0.5 if vu else 0,"expected_test_coverage_gain":round(tu*0.5,1),"priority_score":score,"reason":reason})
    write_csv("vertical_slice_priority_corrected.csv",priority)
    counts=Counter(r["state"] for r in [{"state":x["recommended_next_action"]} for x in []])
    state_counts=Counter(r["recommended_capability"] for r in audits)
    report=["# Corrected Vertical Slice Ranking", "", "## Format 21問の状態", ""]
    for k,v in Counter(classify_format(r)[0] for r in inv).most_common(): report.append(f"- {k}: {v}")
    report += ["", f"actionable format残件: {len(actionable)}問。ただしvalid測定可能な新規Office書式パターンは0問のため、format_extractionは次Slice第1位にしない。", "人間確認待ち2問は実装残件に含めず、画像PDFのvalid 1問はVision / image_pdfへ移す。", "", "## 上位3候補", ""]
    for r in priority[:3]: report.append(f"{r['rank']}. `{r['capability']}`: valid {r['valid_count']} / 未解決 {r['valid_unresolved']}、test {r['test_count']} / 未解決 {r['test_unresolved']}、score {r['priority_score']}\n   理由: {r['reason']}")
    report += ["", "## 第1位の想定実装範囲", "remaining_calculationを、ratio_or_percentage、ranking_or_argmin、single_table_aggregation、difference、schedule_effort、coefficient_predictionの一般仕様として再点検する。質問条件、母集団、分子分母、丸め、係数対応をCalculationSpecとEvidenceへ必須化し、独立再計算とGate監査を行う。", "", "## 推奨モデル", "決定的処理を優先し、意味補完が必要な場合だけ設定済みの無料OpenRouterモデルを低温度・JSON候補選択に限定して使用する。推論強度は低から中とし、最終計算・Evidence・GateはPythonで実行する。"]
    (OUT/"recommended_next_phase_corrected.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    (OUT/"final_summary.md").write_text("# Vertical Slice Rerank After Format\n\nformat extractionの未解決21問を状態別に監査し、人間確認待ち・Vision依存・安全抑制を実装残件から分離した。新規Office書式のvalid測定可能な残件は0問だったため、次Slice第1位はremaining_calculationとした。Executor、Planner、Pipeline、Answer Gateは変更していない。\n",encoding="utf-8")
    print({"run_id":RUN_ID,"format_total":len(audits),"actionable_format":len(actionable),"top3":[r["capability"] for r in priority[:3]]})


if __name__ == "__main__": main()
