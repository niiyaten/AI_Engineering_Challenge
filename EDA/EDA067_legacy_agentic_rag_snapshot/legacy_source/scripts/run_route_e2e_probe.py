"""既存の抽出キャッシュを使い、Route選択からAnswerResultまでを限定確認する。"""

from __future__ import annotations

import json
from pathlib import Path

from rag_competition.pipeline import load_dataclass_jsonl
from rag_competition.schemas import CompactFileProfile, ExtractionResult, FileRecord, QuestionAnalysis, SearchRecord
from rag_competition.tool_registry import run_answer_pipeline


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = ROOT / "data/work/b2_schedule_condition_targeted_v7"
OUT = ROOT / "data/output/question_file_operation_route_e2e_v1/e2e"


def main() -> None:
    plans = [json.loads(line) for line in (SOURCE_RUN / "planning/final_source_plans.jsonl").read_text(encoding="utf-8").splitlines()]
    plans = [item for item in plans if int(item["question_id"]) in {19, 89}]
    analyses = []
    for plan in plans:
        question = plan["question"]
        requirement = (plan.get("source_requirements") or [{}])[0]
        analyses.append(QuestionAnalysis(
            index=int(plan["question_id"]),
            question_original=question,
            question_normalized=question,
            question_for_search=question,
            provisional_routes=[item.get("operation_type", "table_lookup") for item in plan.get("operations", [])],
            required_file_types=requirement.get("required_file_types", []),
            source_requirement=requirement,
        ))
    files = load_dataclass_jsonl(SOURCE_RUN / "inventory/file_records.jsonl", FileRecord)
    records = load_dataclass_jsonl(SOURCE_RUN / "extracted/search_records.jsonl", SearchRecord)
    profiles = load_dataclass_jsonl(SOURCE_RUN / "extracted/compact_file_profiles.jsonl", CompactFileProfile)
    extractions = load_dataclass_jsonl(SOURCE_RUN / "extracted/extraction_results.jsonl", ExtractionResult)
    result = run_answer_pipeline(
        analyses=analyses,
        final_source_plans=plans,
        files=files,
        search_records=records,
        profiles=profiles,
        output_dir=OUT,
        extraction_results=extractions,
        project_root=ROOT,
        execution_dir=OUT / "execution",
        run_mode="route_e2e_probe",
        api_mode="off",
    )
    print(json.dumps({
        "execution_count": result["execution_count"],
        "answered_count": result["answered_count"],
        "answers": [{"question_id": item.question_id, "answer": item.answer, "status": item.status, "gate_status": item.gate_status} for item in result["answer_results"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
