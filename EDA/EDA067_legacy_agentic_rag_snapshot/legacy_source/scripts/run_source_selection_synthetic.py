from __future__ import annotations

from types import SimpleNamespace

from rag_competition.source_selection_resolution import build_source_selection_spec, normalize_entity, resolve_source_selection


def fake_file(file_id, project, kind, name):
    return SimpleNamespace(
        file_id=file_id,
        raw_path=f"data/raw/{project}/{name}",
        file_name=name,
        extension="." + name.rsplit(".", 1)[-1],
        project_name=project,
        major_folder=kind,
        document_kind=kind,
        version_label="",
        date_hints=[],
    )


def main():
    analysis = SimpleNamespace(index=7, question_normalized="Find schedule", provisional_routes=["document_qa"], needs_cross_project=False)
    plan = {"source_requirements": [{"requirement_id": "src_1", "document_roles": ["schedule"], "required_file_types": ["xlsx"], "project_candidates": ["Project A"], "source_cardinality": "single", "source_relation": "same_project", "date_hints": [], "version_hints": []}], "operations": []}
    good = fake_file("f1", "Project A", "schedule", "schedule.xlsx")
    common = dict(analysis=analysis, source_plan=plan, candidates_by_requirement={"src_1": [{"candidate_file_id": "f1", "deterministic_score": 90}]}, final_file_ids=["f1"], files_by_id={"f1": good}, profiles_by_file={"f1": SimpleNamespace(summary="Project A schedule", keywords=[], record_type_counts={})}, selection_status="selected")
    result = resolve_source_selection(**common)
    assert result["resolved"] and result["selected_source_set_id"] == "source_set_q7"
    bad = fake_file("f2", "Project B", "schedule", "schedule.xlsx")
    common["final_file_ids"] = ["f2"]
    common["files_by_id"] = {"f2": bad}
    common["candidates_by_requirement"] = {"src_1": [{"candidate_file_id": "f2", "deterministic_score": 90}]}
    common["profiles_by_file"] = {"f2": SimpleNamespace(summary="Project B schedule", keywords=[], record_type_counts={})}
    result = resolve_source_selection(**common)
    assert not result["resolved"] and not result["selected_source_ids"]
    multi = build_source_selection_spec(analysis, {"source_requirements": [{"document_roles": ["contract", "schedule"], "required_file_types": ["docx", "xlsx"], "project_candidates": ["Project A"], "multiple_files_required": True, "source_cardinality": "multiple", "source_relation": "referenced_resource"}]})
    assert multi["source_cardinality"] == "multiple_required_sources" and multi["source_relation"] == "summary_then_source"
    assert normalize_entity(" Project A ") == "projecta"
    print("synthetic_positive=2 synthetic_negative=1 spec_checks=1 status=passed")


if __name__ == "__main__":
    main()
