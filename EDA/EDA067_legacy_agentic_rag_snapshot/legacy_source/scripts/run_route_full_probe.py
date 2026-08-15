"""既存の正式抽出キャッシュを使ったRoute接続後の回帰確認。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rag_competition.pipeline import load_dataclass_jsonl
from rag_competition.schemas import CompactFileProfile, ExtractionResult, FileRecord, QuestionAnalysis, SearchRecord
from rag_competition.tool_registry import run_answer_pipeline


ROOT = Path(__file__).resolve().parents[1]


def run(source_run: str, output_run: str) -> None:
    source = ROOT / "data/work" / source_run
    out = ROOT / "data/output" / output_run
    plans = [json.loads(line) for line in (source / "planning/final_source_plans.jsonl").read_text(encoding="utf-8").splitlines()]
    analyses = load_dataclass_jsonl(source / "planning/question_analysis.jsonl", QuestionAnalysis)
    files = load_dataclass_jsonl(source / "inventory/file_records.jsonl", FileRecord)
    records = load_dataclass_jsonl(source / "extracted/search_records.jsonl", SearchRecord)
    profiles = load_dataclass_jsonl(source / "extracted/compact_file_profiles.jsonl", CompactFileProfile)
    extractions = load_dataclass_jsonl(source / "extracted/extraction_results.jsonl", ExtractionResult)
    result = run_answer_pipeline(
        analyses, plans, files, records, profiles, out,
        extraction_results=extractions,
        project_root=ROOT,
        execution_dir=out / "execution",
        run_mode="route_full_probe",
        api_mode="off",
    )
    print(json.dumps({"source_run": source_run, "output_run": output_run, "execution_count": result["execution_count"], "answered_count": result["answered_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
