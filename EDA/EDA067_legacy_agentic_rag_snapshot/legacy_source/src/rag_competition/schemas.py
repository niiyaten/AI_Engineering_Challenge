from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "agentic_rag_v1"
INVENTORY_VERSION = "inventory_v2"
EXTRACTOR_VERSION = "raw_extractors_v4"
PROMPT_VERSION = "agentic_rag_prompt_v1"
PLANNER_VERSION = "source_selection_planner_v2"
TOOL_REGISTRY_VERSION = "tool_registry_v9"
EXECUTOR_VERSION = "executor_v9"


@dataclass
class SourceRequirement:
    """質問が必要とする情報源の数、役割、相互関係を表す。"""

    schema_version: str = "1.0"
    source_cardinality: str = "single"
    source_relation: str = "unknown"
    required_projects: list[str] = field(default_factory=list)
    required_document_roles: list[str] = field(default_factory=list)
    required_file_types: list[str] = field(default_factory=list)
    explicit_file_names: list[str] = field(default_factory=list)
    version_constraints: list[str] = field(default_factory=list)
    relation_evidence_required: bool = True


@dataclass
class FileRecord:
    file_id: str
    raw_path: str
    relative_path: str
    file_name: str
    extension: str
    size_bytes: int
    modified_at: str
    sha1: str
    area: str
    project_name: str
    major_folder: str
    document_kind: str
    version_label: str
    date_hints: list[str] = field(default_factory=list)
    is_temp_office_file: bool = False


@dataclass
class SearchRecord:
    record_id: str
    file_id: str
    record_type: str
    raw_path: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactFileProfile:
    file_id: str
    raw_path: str
    file_name: str
    extension: str
    project_name: str
    major_folder: str
    document_kind: str
    version_label: str
    summary: str
    record_type_counts: dict[str, int] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    file_id: str
    raw_path: str
    status: str
    extractor: str
    extracted_path: str
    search_record_count: int
    table_data_paths: list[str] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class ProtectedFileRecord:
    schema_version: str
    file_id: str
    source_path: str
    protection_status: str
    detection_method: str
    is_temporary_file: bool
    requires_password: bool
    resolution_status: str
    selected_derivation_method: str = ""
    decrypted_work_path: str = ""
    attempt_count: int = 0
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    project_name: str = ""
    file_type: str = ""
    filename_password_hint_found: bool = False
    project_alias: str = ""
    project_alias_source: str = ""
    contract_start_date: str = ""
    contract_date_source: str = ""
    derivation_method: str = ""
    decryption_success: bool = False
    validation_success: bool = False
    extraction_success: bool = False
    failure_reason: str = ""


@dataclass
class PasswordCandidate:
    schema_version: str
    candidate_id: str
    file_id: str
    derivation_method: str
    project_name: str
    project_alias: str
    contract_start_date: str
    extension_code: str
    source_paths: list[str]
    confidence: float
    masked_password: str
    password_hash: str


@dataclass
class DecryptionAttempt:
    schema_version: str
    file_id: str
    candidate_id: str
    attempt_order: int
    success: bool
    validation_success: bool
    library: str
    elapsed_seconds: float
    error_type: str = ""
    error_message: str = ""


@dataclass
class QuestionAnalysis:
    index: int
    question_original: str
    question_normalized: str
    question_term_expanded: str = ""
    question_for_search: str = ""
    encoding_warning: str = ""
    identifier_output_only: bool = False
    replaced_terms: list[dict[str, Any]] = field(default_factory=list)
    project_candidates: list[str] = field(default_factory=list)
    document_hints: list[str] = field(default_factory=list)
    identifier_hints: list[str] = field(default_factory=list)
    date_hints: list[str] = field(default_factory=list)
    provisional_routes: list[str] = field(default_factory=list)
    required_file_types: list[str] = field(default_factory=list)
    needs_multiple_files: bool = False
    needs_cross_project: bool = False
    source_requirement: dict[str, Any] = field(default_factory=dict)
    planner_source: str = "heuristic"
    planner_error: str = ""


@dataclass
class CandidateFile:
    index: int
    file_id: str
    raw_path: str
    rank: int
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)
    matched_terms: list[str] = field(default_factory=list)
    candidate_reason: str = ""
    confidence: float = 0.0
    selector_source: str = "heuristic"


@dataclass
class ExecutionPlan:
    index: int
    primary_route: str
    sub_routes: list[str]
    execution_order: list[str]
    candidate_file_ids: list[str]
    candidate_search_record_ids: list[str]
    required_tools: list[str] = field(default_factory=list)
    requires_llm: bool = False
    requires_vision_model: bool = False
    requires_python_execution: bool = False
    answer_format_hint: str = ""
    plan_confidence: float = 0.0
    plan_reason: str = ""
    selector_source: str = "heuristic"
    selector_error: str = ""


@dataclass
class AnswerResult:
    """1問の実行結果と、回答を支えた根拠を保存する。"""

    question_id: int
    answer: str
    answer_type: str
    selected_files: list[str] = field(default_factory=list)
    evidence_locations: list[dict[str, Any]] = field(default_factory=list)
    operations_executed: list[str] = field(default_factory=list)
    calculation_trace: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "unsupported"
    warnings: list[str] = field(default_factory=list)
    failure_stage: str = ""
    planner_mode: str = ""
    selector_mode: str = ""
    selected_file_ids: list[str] = field(default_factory=list)
    operation_parameters: list[dict[str, Any]] = field(default_factory=list)
    executor_version: str = EXECUTOR_VERSION
    cache_key: str = ""
    gate_status: str = ""
    gate_reason: str = ""


@dataclass
class AnswerGateResult:
    question_id: int
    allow_answer: bool
    gate_status: str
    executor_name: str
    implementation_status: str
    actual_used_file_ids: list[str] = field(default_factory=list)
    evidence_present: bool = False
    evidence_verified: bool = False
    preview_only: bool = False
    ambiguity_detected: bool = False
    suppression_reason: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class RunRecord:
    run_id: str
    started_at: str
    finished_at: str
    git_commit: str
    python_version: str
    dependency_lock_hash: str
    raw_root: str
    questions_path: str
    raw_file_count: int
    raw_file_hashes: dict[str, str]
    extractor_versions: dict[str, str]
    schema_versions: dict[str, str]
    prompt_versions: dict[str, str]
    models: list[str]
    settings: dict[str, Any]
    cache_enabled: bool
    cache_hits: int
    cache_misses: int
    api_call_count: int
    warnings: list[str]
    errors: list[str]
    status: str
    protected_file_count: int = 0
    temporary_office_file_count: int = 0
    decryption_attempt_count: int = 0
    decryption_success_count: int = 0
    decryption_failure_count: int = 0
    filename_password_success_count: int = 0
    rule_derived_password_success_count: int = 0
    ambiguous_password_count: int = 0
    decrypted_file_map: dict[str, str] = field(default_factory=dict)


def to_dict(value: Any) -> dict[str, Any]:
    """dataclassをJSONL保存しやすい辞書へ変換する。"""
    return asdict(value)
