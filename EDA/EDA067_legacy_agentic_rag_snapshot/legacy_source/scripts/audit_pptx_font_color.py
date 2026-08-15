from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rag_competition.pptx_colors import slide_color_map


def jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--run-id", required=True); args = parser.parse_args()
    root = Path.cwd(); run_dir = root / "data/work" / args.run_id; out_dir = root / "data/output" / args.run_id / "analysis"; out_dir.mkdir(parents=True, exist_ok=True); trace_dir = run_dir / "pptx_color"; trace_dir.mkdir(parents=True, exist_ok=True)
    records = {row["file_id"]: row for row in csv.DictReader((run_dir / "inventory/file_records.csv").open(encoding="utf-8-sig"))}
    specs = {int(row["question_id"]): row for row in jsonl(run_dir / "document_extraction/extraction_specs.jsonl")}
    answers = {int(row["question_id"]): row for row in jsonl(root / "data/output" / args.run_id / "answer_results.jsonl")}
    structures = {path.stem: json.load(path.open(encoding="utf-8")) for path in (run_dir / "extracted/extracted").glob("*.json")}
    comparison = []; raw_elements = []; resolved = []
    for question_id, spec_row in specs.items():
        spec = spec_row.get("spec", {}); condition = spec.get("format_conditions", {}); answer = answers.get(question_id, {})
        for file_id in answer.get("selected_file_ids", []):
            record = records.get(file_id, {}); source_path = root / record.get("raw_path", "")
            if record.get("extension", "").lower() != ".pptx" or not source_path.exists(): continue
            raw_map = slide_color_map(source_path); structure = structures.get(file_id, {})
            for slide in structure.get("slides", []):
                slide_number = int(slide.get("slide_number", 0)); raw_shapes = raw_map.get(slide_number, [])
                for shape in slide.get("shapes", []):
                    shape_index = int(shape.get("shape_index", 0));
                    for run in shape.get("runs", []):
                        paragraph_index = int(run.get("paragraph_index", 0)); run_index = int(run.get("run_index", 0)); color = raw_shapes[shape_index] [paragraph_index][run_index] if shape_index < len(raw_shapes) and paragraph_index < len(raw_shapes[shape_index]) and run_index < len(raw_shapes[shape_index][paragraph_index]) else {}
                        actual = run.get("font_color_normalized_name", run.get("font_color", "unknown")); fill = run.get("fill_color", "unknown"); expected = condition.get("font_color") or condition.get("fill_color"); matched = actual == expected or fill == expected if expected else False
                        row = {"question_id": question_id, "source_path": record.get("raw_path", ""), "slide_number": slide_number, "shape_index": shape_index, "paragraph_index": paragraph_index, "run_index": run_index, "text": run.get("text", ""), "raw_color_type": color.get("raw_color_type", ""), "raw_color_value": color.get("raw_color_value", ""), "raw_scheme_color": color.get("scheme_color_name", ""), "raw_transforms": json.dumps(color.get("color_transforms", []), ensure_ascii=False), "resolved_base_rgb": color.get("base_rgb", ""), "resolved_final_rgb": color.get("resolved_rgb", ""), "normalized_color_name": color.get("normalized_color_name", "unknown"), "color_source": color.get("color_source", "unknown"), "resolution_status": color.get("resolution_status", "not_specified"), "document_ir_rgb": run.get("font_color_resolved_rgb", ""), "document_ir_color_name": actual, "shape_fill_rgb": run.get("fill_color_resolved_rgb", ""), "question_color_condition": expected or "", "condition_match": matched, "mismatch_reason": "" if matched else "condition_not_matched"}
                        comparison.append(row); raw_elements.append({"question_id": question_id, "file_id": file_id, **row}); resolved.append({"question_id": question_id, "file_id": file_id, **row})
    fields = list(comparison[0]) if comparison else ["question_id"]
    with (out_dir / "pptx_font_color_raw_ir_comparison.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(comparison)
    summary = []
    for question_id in sorted({row["question_id"] for row in comparison}):
        subset = [row for row in comparison if row["question_id"] == question_id]
        summary.append({"question_id": question_id, "total_text_runs": len(subset), "explicit_color_runs": sum(bool(row["raw_color_value"]) for row in subset), "theme_color_runs": sum(bool(row["raw_scheme_color"]) for row in subset), "resolved_color_runs": sum(row["resolution_status"] in {"resolved", "partially_resolved"} for row in subset), "unresolved_color_runs": sum(row["resolution_status"] not in {"resolved", "partially_resolved"} for row in subset), "red_runs": sum(bool(row["normalized_color_name"] == "red" or row["shape_fill_rgb"]) for row in subset), "question_condition_match_runs": sum(bool(row["condition_match"]) for row in subset), "reconstructed_items": len([x for x in jsonl(run_dir / "document_extraction/reconstructed_items.jsonl") if x.get("question_id") == question_id])})
    for name, data in (("pptx_font_color_summary.csv", summary), ("pptx_font_color_failure_summary.csv", [{"mismatch_reason": key, "count": value} for key, value in Counter(row["mismatch_reason"] for row in comparison if row["mismatch_reason"]).items()])):
        with (out_dir / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]) if data else ["question_id"]); writer.writeheader(); writer.writerows(data)
    for path, data in ((trace_dir / "pptx_raw_color_elements.jsonl", raw_elements), (trace_dir / "pptx_resolved_colors.jsonl", resolved)):
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in data) + ("\n" if data else ""), encoding="utf-8")
    print(json.dumps({"comparison_rows": len(comparison), "summary_rows": len(summary)}, ensure_ascii=False))


if __name__ == "__main__": main()
