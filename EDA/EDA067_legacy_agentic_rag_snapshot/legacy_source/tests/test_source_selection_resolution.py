from types import SimpleNamespace

from rag_competition.source_selection_resolution import (
    build_source_selection_spec,
    normalize_entity,
    resolve_source_selection,
)


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


def fake_analysis():
    return SimpleNamespace(
        index=7,
        question_normalized="Find the schedule for Project A",
        provisional_routes=["document_qa"],
        needs_cross_project=False,
    )


def test_normalization_is_conservative_but_stable():
    assert normalize_entity(" Project A ") == "projecta"
    assert normalize_entity("Project-B") == "project-b"


def test_unique_same_project_source_set_is_resolved():
    analysis = fake_analysis()
    source_plan = {
        "source_requirements": [{
            "requirement_id": "src_1",
            "document_roles": ["schedule"],
            "required_file_types": ["xlsx"],
            "project_candidates": ["Project A"],
            "source_cardinality": "single",
            "source_relation": "same_project",
            "date_hints": [],
            "version_hints": [],
        }],
        "operations": [],
    }
    file = fake_file("f1", "Project A", "schedule", "schedule.xlsx")
    result = resolve_source_selection(
        analysis,
        source_plan,
        {"src_1": [{"candidate_file_id": "f1", "deterministic_score": 90}]},
        ["f1"],
        {"f1": file},
        {"f1": SimpleNamespace(summary="Project A schedule", keywords=[], record_type_counts={})},
        "selected",
    )
    assert result["resolved"] is True
    assert result["selected_source_set_id"] == "source_set_q7"
    assert result["source_relation"] == "same_project"


def test_missing_project_relation_is_suppressed():
    analysis = fake_analysis()
    source_plan = {
        "source_requirements": [{
            "requirement_id": "src_1",
            "document_roles": ["schedule"],
            "required_file_types": ["xlsx"],
            "project_candidates": ["Project A"],
            "source_cardinality": "single",
            "source_relation": "same_project",
            "date_hints": [],
            "version_hints": [],
        }],
        "operations": [],
    }
    file = fake_file("f1", "Project B", "schedule", "schedule.xlsx")
    result = resolve_source_selection(
        analysis,
        source_plan,
        {"src_1": [{"candidate_file_id": "f1", "deterministic_score": 90}]},
        ["f1"],
        {"f1": file},
        {"f1": SimpleNamespace(summary="Project B schedule", keywords=[], record_type_counts={})},
        "selected",
    )
    assert result["resolved"] is False
    assert result["selected_source_ids"] == []


def test_source_spec_expands_multiple_source_requirement():
    spec = build_source_selection_spec(
        SimpleNamespace(question_normalized="q", provisional_routes=["cross_file_aggregation"], needs_cross_project=False),
        {"source_requirements": [{
            "document_roles": ["contract", "schedule"],
            "required_file_types": ["docx", "xlsx"],
            "project_candidates": ["Project A"],
            "multiple_files_required": True,
            "source_cardinality": "multiple",
            "source_relation": "referenced_resource",
        }]},
    )
    assert spec["source_cardinality"] == "multiple_required_sources"
    assert spec["source_relation"] == "summary_then_source"
