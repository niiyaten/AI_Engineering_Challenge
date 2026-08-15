from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

from .extractors import extract_all
from .inventory import build_inventory
from .io_utils import (
    FORBIDDEN_INPUT_PREFIXES,
    dependency_lock_hash,
    get_git_commit,
    now_iso,
    python_version,
    relative_to_root,
    write_json,
)
from .llm_client import OpenRouterClient
from .paths import project_root
from .protected_files import ProtectedResolutionResult, masked_path, resolve_protected_files, update_extraction_status
from .questions import analyze_questions, find_glossary_doc, read_glossary, read_questions
from .source_selection import run_source_selection_planning
from .table_executor import is_table_question, select_relevant_table_files
from .tool_registry import run_answer_pipeline
from .schemas import (
    EXTRACTOR_VERSION,
    INVENTORY_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    CompactFileProfile,
    ExtractionResult,
    FileRecord,
    RunRecord,
    SearchRecord,
    to_dict,
)


def default_run_id(split: str) -> str:
    return now_iso().replace(":", "").replace("-", "").replace("+", "_").replace("T", "_") + f"_{split}_source_selection"


def load_dataclass_jsonl(path: Path, cls: type) -> list:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(cls(**json.loads(line)))
    return rows


def questions_path_for_split(root: Path, split: str) -> Path:
    return root / "data" / "raw" / "share" / "share" / "質問回答" / f"questions_{split}.csv"


def make_client(args: argparse.Namespace, root: Path, logs_dir: Path) -> OpenRouterClient | None:
    if args.api_mode == "off":
        return None
    key_path = root / ".apikey"
    if args.api_mode == "auto" and not key_path.exists():
        return None
    return OpenRouterClient(
        project_root=root,
        output_dir=logs_dir,
        model=args.model,
        temperature=args.temperature,
        seed=None if args.seed < 0 else args.seed,
        timeout_sec=args.timeout_sec,
        max_retries=args.max_retries,
        use_cache=not args.no_api_cache,
    )


def make_semantic_client(args: argparse.Namespace, root: Path, logs_dir: Path) -> OpenRouterClient | None:
    """無料モデルだけを許可する設定を検証してsemantic候補選択用Clientを作る。"""
    if args.semantic_api_mode == "off":
        return None
    config_path = args.semantic_config
    if not config_path.is_absolute():
        config_path = root / config_path
    config = json.loads(config_path.read_text(encoding="utf-8"))
    allowed = [str(value) for value in config.get("allowed_models", [])]
    if not config.get("enabled") or not config.get("free_models_only") or config.get("allow_paid_fallback"):
        raise ValueError("semantic OpenRouter設定は無料モデル限定・有料fallback無効である必要があります")
    model = args.semantic_model or (allowed[0] if allowed else "")
    if not model or model not in allowed or not model.endswith(":free"):
        raise ValueError("semantic modelは設定ファイルで許可された:freeモデルに限定されます")
    if args.semantic_api_mode == "auto" and not (root / ".apikey").exists():
        return None
    return OpenRouterClient(
        project_root=root,
        output_dir=logs_dir / "semantic_api",
        model=model,
        temperature=0.0,
        seed=None if args.seed < 0 else args.seed,
        timeout_sec=args.timeout_sec,
        max_retries=args.max_retries,
        use_cache=not args.no_api_cache,
    )


def stage_inventory(args: argparse.Namespace, root: Path, run_dir: Path) -> tuple[list[FileRecord], int, int]:
    out_dir = run_dir / "inventory"
    jsonl_path = out_dir / "file_records.jsonl"
    manifest_path = out_dir / "inventory_cache_manifest.json"
    expected_manifest = {
        "inventory_version": INVENTORY_VERSION,
        "schema_version": SCHEMA_VERSION,
        "raw_root": relative_to_root(args.raw_root, root),
    }
    manifest_matches = False
    if manifest_path.exists():
        try:
            manifest_matches = json.loads(manifest_path.read_text(encoding="utf-8")) == expected_manifest
        except (OSError, json.JSONDecodeError):
            manifest_matches = False
    if args.use_cache and manifest_matches and jsonl_path.exists():
        return load_dataclass_jsonl(jsonl_path, FileRecord), 1, 0
    records = build_inventory(args.raw_root, root, out_dir)
    write_json(manifest_path, expected_manifest)
    if args.max_files > 0:
        records = records[: args.max_files]
    return records, 0, 1


def empty_protected_result() -> ProtectedResolutionResult:
    return ProtectedResolutionResult([], [], [], {})


def stage_protected_files(args: argparse.Namespace, root: Path, run_dir: Path, records: list[FileRecord]) -> tuple[ProtectedResolutionResult, int, int]:
    if not args.resolve_protected_files:
        return empty_protected_result(), 0, 0
    return resolve_protected_files(
        records,
        project_root=root,
        raw_root=args.raw_root,
        run_dir=run_dir,
        strict=args.strict_protected_files,
    ), 0, 1


def stage_extract(
    args: argparse.Namespace,
    root: Path,
    run_dir: Path,
    records: list[FileRecord],
    input_path_overrides: dict[str, Path] | None = None,
) -> tuple[list[ExtractionResult], list[SearchRecord], list[CompactFileProfile], int, int]:
    out_dir = run_dir / "extracted"
    result_path = out_dir / "extraction_results.jsonl"
    search_path = out_dir / "search_records.jsonl"
    profile_path = out_dir / "compact_file_profiles.jsonl"
    cache_manifest_path = out_dir / "extraction_cache_manifest.json"
    expected_cache = {
        "raw_file_hashes": {record.file_id: record.sha1 for record in records},
        "inventory_version": INVENTORY_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "render_pdf_pages": args.render_pdf_pages,
        "max_pdf_render_pages": args.max_pdf_render_pages,
    }
    cache_valid = False
    if args.use_cache and cache_manifest_path.exists():
        try:
            cache_valid = json.loads(cache_manifest_path.read_text(encoding="utf-8")) == expected_cache
        except (OSError, json.JSONDecodeError):
            cache_valid = False
    if args.use_cache and cache_valid and result_path.exists() and search_path.exists() and profile_path.exists():
        return (
            load_dataclass_jsonl(result_path, ExtractionResult),
            load_dataclass_jsonl(search_path, SearchRecord),
            load_dataclass_jsonl(profile_path, CompactFileProfile),
            1,
            0,
        )
    results, search_records, profiles = extract_all(
        records,
        root,
        out_dir,
        render_pdf_pages=args.render_pdf_pages,
        max_pdf_render_pages=args.max_pdf_render_pages,
        input_path_overrides=input_path_overrides,
    )
    write_json(cache_manifest_path, expected_cache)
    return results, search_records, profiles, 0, 1


def stage_questions(args: argparse.Namespace, root: Path, run_dir: Path) -> tuple[list, int, int]:
    out_dir = run_dir / "planning"
    path = out_dir / "question_analysis.jsonl"
    if args.use_cache and args.use_plan_cache and not args.no_plan_cache and path.exists():
        from .schemas import QuestionAnalysis

        return load_dataclass_jsonl(path, QuestionAnalysis), 1, 0
    raw_questions = read_questions(args.questions_path, root)
    glossary = read_glossary(find_glossary_doc(args.raw_root, root), root)
    return analyze_questions(raw_questions, glossary, out_dir), 0, 1


def write_index_outputs(run_dir: Path, search_records: list[SearchRecord]) -> None:
    by_type: dict[str, int] = {}
    for record in search_records:
        by_type[record.record_type] = by_type.get(record.record_type, 0) + 1
    write_json(run_dir / "indexes" / "search_index_summary.json", {"record_count": len(search_records), "record_type_counts": by_type})


def write_forbidden_input_check(logs_dir: Path) -> None:
    write_json(
        logs_dir / "forbidden_input_check.json",
        {
            "status": "passed",
            "checked_forbidden_prefixes": list(FORBIDDEN_INPUT_PREFIXES),
            "note": "formal pipeline stages guard raw inputs and did not use EDA, data/processed, or submissions as inputs",
        },
    )


def run_source_selection(args: argparse.Namespace) -> dict[str, object]:
    root = project_root()
    # 正式runが作業ツリーの実装と復号依存を使っているかを成果物から再確認できるようにする。
    package_spec = importlib.util.find_spec("rag_competition")
    package_path = str(Path(package_spec.origin).resolve()) if package_spec and package_spec.origin else ""
    msoffcrypto_available = importlib.util.find_spec("msoffcrypto") is not None
    run_id = args.run_id or default_run_id(args.split)
    run_dir = root / "data" / "work" / run_id
    output_dir = root / "data" / "output" / run_id
    logs_dir = run_dir / "logs"

    if args.fresh and run_dir.exists():
        shutil.rmtree(run_dir)
    if args.fresh and output_dir.exists():
        shutil.rmtree(output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    if args.cache_source_run and args.use_cache:
        cache_source = root / "data" / "work" / args.cache_source_run
        for stage_name in ("inventory", "extracted"):
            source_stage = cache_source / stage_name
            target_stage = run_dir / stage_name
            if source_stage.exists() and not target_stage.exists():
                shutil.copytree(source_stage, target_stage)

    started_at = now_iso()
    warnings: list[str] = []
    errors: list[str] = []
    cache_hits = 0
    cache_misses = 0
    api_call_count = 0
    status = "completed"
    planning_stats: dict[str, object] = {}
    answer_stats: dict[str, object] = {}
    client: OpenRouterClient | None = None
    semantic_client: OpenRouterClient | None = None

    try:
        files, hit, miss = stage_inventory(args, root, run_dir)
        cache_hits += hit
        cache_misses += miss
        preselected_analyses = None
        if args.table_slice_only:
            preselected_analyses, hit, miss = stage_questions(args, root, run_dir)
            cache_hits += hit
            cache_misses += miss
            table_analyses = [analysis for analysis in preselected_analyses if is_table_question(analysis)[0]]
            selected_file_ids: set[str] = set()
            for analysis in table_analyses:
                selected_file_ids.update(file.file_id for file in select_relevant_table_files(analysis.question_original, [], files))
            files = [file for file in files if file.file_id in selected_file_ids]
        protected_result, hit, miss = stage_protected_files(args, root, run_dir, files)
        cache_hits += hit
        cache_misses += miss
        extraction_results, search_records, profiles, hit, miss = stage_extract(args, root, run_dir, files, protected_result.input_path_overrides)
        cache_hits += hit
        cache_misses += miss
        if protected_result.records:
            extraction_status = {result.file_id: (result.status == "success", result.error) for result in extraction_results}
            update_extraction_status(
                run_dir / "protected_files",
                protected_result.records,
                protected_result.candidates,
                protected_result.attempts,
                extraction_status,
            )
        write_index_outputs(run_dir, search_records)
        analyses, hit, miss = stage_questions(args, root, run_dir)
        cache_hits += hit
        cache_misses += miss
        if args.table_slice_only and preselected_analyses is not None:
            table_ids = {item.index for item in preselected_analyses if is_table_question(item)[0]}
            analyses = [analysis for analysis in analyses if analysis.index in table_ids]
        client = make_client(args, root, logs_dir)
        semantic_client = make_semantic_client(args, root, logs_dir)
        planning_result = run_source_selection_planning(
            analyses,
            files,
            search_records,
            profiles,
            run_dir / "planning",
            client=client,
            planner_model=args.planner_model,
            selector_model=args.selector_model,
            top_n=args.candidate_top_n,
            selector_candidate_limit=args.selector_candidate_limit,
            max_additional_searches=args.max_additional_searches,
            question_ids=args.question_ids,
            limit=args.limit,
        )
        analyses = planning_result.analyses
        candidates = planning_result.candidates
        plans = planning_result.plans
        planning_stats = planning_result.stats
        if args.mode == "end-to-end":
            answer_stats = run_answer_pipeline(
                analyses,
                planning_stats.get("final_source_plans", []),
                files,
                search_records,
                profiles,
                output_dir,
                extraction_results=extraction_results,
                project_root=root,
                table_executor_enabled=not args.disable_table_executor,
                dry_run=args.dry_run,
                execution_dir=run_dir / "execution",
                run_mode=args.mode,
                api_mode=args.api_mode,
                document_work_dir=run_dir / "document_extraction",
                semantic_client=semantic_client,
                semantic_work_dir=run_dir / "semantic",
            )
        api_call_count = (client.api_call_count if client else 0) + (semantic_client.api_call_count if semantic_client else 0)
        if args.api_mode == "on" and args.no_api_cache and api_call_count == 0:
            raise RuntimeError("api-mode on with --no-api-cache did not call OpenRouter API")
        warnings.extend(warning for result in extraction_results for warning in result.warnings)
        errors.extend(result.error for result in extraction_results if result.error)
        write_forbidden_input_check(logs_dir)
    except Exception as exc:
        status = "failed"
        errors.append(f"{type(exc).__name__}: {exc}")
        files = []
        protected_result = empty_protected_result()
        extraction_results = []
        search_records = []
        analyses = []
        candidates = []
        plans = []
        planning_stats = {}

    raw_hashes = {masked_path(record.raw_path): record.sha1 for record in files}
    source_planner_success_count = len(analyses) if status == "completed" else 0
    candidate_selector_success_count = sum(1 for plan in plans if plan.candidate_file_ids)
    final_source_plans = planning_stats.get("final_source_plans", []) if isinstance(planning_stats, dict) else []
    source_planner_llm_count = sum(1 for row in final_source_plans if row.get("planner_mode") == "llm")
    source_planner_fallback_count = sum(1 for row in final_source_plans if "fallback" in str(row.get("planner_mode", "")))
    candidate_selector_llm_count = sum(1 for plan in plans if plan.selector_source == "llm")
    candidate_selector_fallback_count = sum(1 for plan in plans if "fallback" in plan.selector_source)
    metrics = planning_stats.get("metrics", {}) if isinstance(planning_stats, dict) else {}
    api_failure_count = int(metrics.get("planner_fallback_count") or 0) + int(metrics.get("selector_fallback_count") or 0)
    protected_file_count = sum(1 for record in protected_result.records if record.requires_password)
    temporary_office_file_count = sum(1 for record in protected_result.records if record.is_temporary_file)
    decryption_attempt_count = len(protected_result.attempts)
    decryption_success_count = sum(1 for record in protected_result.records if record.decryption_success)
    decryption_failure_count = sum(1 for record in protected_result.records if record.requires_password and not record.decryption_success)
    filename_password_success_count = sum(1 for record in protected_result.records if record.resolution_status == "resolved_from_filename")
    rule_derived_password_success_count = sum(1 for record in protected_result.records if record.resolution_status == "resolved_from_rule")
    ambiguous_password_count = sum(1 for record in protected_result.records if record.resolution_status.startswith("ambiguous"))
    decrypted_file_map = {record.file_id: relative_to_root(Path(record.decrypted_work_path), root) for record in protected_result.records if record.decrypted_work_path}
    manifest = RunRecord(
        run_id=run_id,
        started_at=started_at,
        finished_at=now_iso(),
        git_commit=get_git_commit(root),
        python_version=python_version(),
        dependency_lock_hash=dependency_lock_hash(root),
        raw_root=relative_to_root(args.raw_root, root),
        questions_path=relative_to_root(args.questions_path, root),
        raw_file_count=len(files),
        raw_file_hashes=raw_hashes,
        extractor_versions={"all": EXTRACTOR_VERSION},
        schema_versions={"source_selection": SCHEMA_VERSION},
        prompt_versions={"source_selection": PROMPT_VERSION},
        models=sorted(
            ({args.planner_model, args.selector_model} if args.api_mode != "off" else set())
            | ({semantic_client.model} if semantic_client else set())
        ),
        settings={
            "split": args.split,
            "mode": args.mode,
            "fresh": args.fresh,
            "use_cache": args.use_cache,
            "api_mode": args.api_mode,
            "semantic_api_mode": args.semantic_api_mode,
            "semantic_model": semantic_client.model if semantic_client else "",
            "semantic_free_models_only": True,
            "semantic_allow_paid_fallback": False,
            "model": args.model,
            "planner_model": args.planner_model,
            "selector_model": args.selector_model,
            "temperature": args.temperature,
            "seed": None if args.seed < 0 else args.seed,
            "candidate_top_n": args.candidate_top_n,
            "selector_candidate_limit": args.selector_candidate_limit,
            "max_additional_searches": args.max_additional_searches,
            "limit": args.limit,
            "question_ids": args.question_ids,
            "api_cache": not args.no_api_cache,
            "cache_source_run": args.cache_source_run,
            "table_slice_only": args.table_slice_only,
            "use_plan_cache": args.use_plan_cache and not args.no_plan_cache,
            "execution_cache": False,
            "answer_cache": False,
            "render_pdf_pages": args.render_pdf_pages,
            "max_pdf_render_pages": args.max_pdf_render_pages,
            "max_files": args.max_files,
            "resolve_protected_files": args.resolve_protected_files,
            "strict_protected_files": args.strict_protected_files,
            "python_executable": sys.executable,
            "imported_package_path": package_path,
            "git_worktree_path": str(root.resolve()),
            "pythonpath": os.environ.get("PYTHONPATH", ""),
            "current_working_directory": str(Path.cwd().resolve()),
            "config_path": str(args.semantic_config),
            "cache_version": "pipeline_cache_v1",
            "index_version": f"search_index_{SCHEMA_VERSION}",
            "msoffcrypto_available": msoffcrypto_available,
        },
        cache_enabled=args.use_cache,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        api_call_count=api_call_count,
        warnings=warnings[:200],
        errors=errors[:200],
        status=status,
        protected_file_count=protected_file_count,
        temporary_office_file_count=temporary_office_file_count,
        decryption_attempt_count=decryption_attempt_count,
        decryption_success_count=decryption_success_count,
        decryption_failure_count=decryption_failure_count,
        filename_password_success_count=filename_password_success_count,
        rule_derived_password_success_count=rule_derived_password_success_count,
        ambiguous_password_count=ambiguous_password_count,
        decrypted_file_map=decrypted_file_map,
    )
    write_json(run_dir / "run_manifest.json", to_dict(manifest))
    write_json(output_dir / "run_manifest.json", to_dict(manifest))
    summary = {
        "run_id": run_id,
        "status": status,
        "run_dir": relative_to_root(run_dir, root),
        "output_dir": relative_to_root(output_dir, root),
        "raw_file_count": len(files),
        "file_record_count": len(files),
        "extraction_success_count": sum(1 for item in extraction_results if item.status == "success"),
        "extraction_error_count": sum(1 for item in extraction_results if item.status == "error"),
        "search_record_count": len(search_records),
        "candidate_file_count": len(candidates),
        "execution_plan_count": len(plans),
        "source_planner_success_count": source_planner_success_count,
        "source_planner_llm_count": source_planner_llm_count,
        "source_planner_fallback_count": source_planner_fallback_count,
        "candidate_selector_success_count": candidate_selector_success_count,
        "candidate_selector_llm_count": candidate_selector_llm_count,
        "candidate_selector_fallback_count": candidate_selector_fallback_count,
        "api_failure_count": api_failure_count,
        "api_call_count": api_call_count,
        "planner_api_call_count": metrics.get("planner_api_call_count"),
        "selector_api_call_count": metrics.get("selector_api_call_count"),
        "planner_fallback_count": metrics.get("planner_fallback_count"),
        "selector_fallback_count": metrics.get("selector_fallback_count"),
        "planner_parse_success_rate": metrics.get("planner_parse_success_rate"),
        "selector_parse_success_rate": metrics.get("selector_parse_success_rate"),
        "exact_file_hit_at_1": metrics.get("exact_file_hit_at_1"),
        "exact_file_hit_at_5": metrics.get("exact_file_hit_at_5"),
        "exact_file_hit_at_10": metrics.get("exact_file_hit_at_10"),
        "project_hit_rate": metrics.get("project_hit_rate"),
        "wrong_project_selection_rate": metrics.get("wrong_project_selection_rate"),
        "pair_coverage_rate": metrics.get("pair_coverage_rate"),
        "content_verification_success_count": metrics.get("content_verification_success_count"),
        "additional_search_count": metrics.get("additional_search_count"),
        "ambiguous_count": metrics.get("ambiguous_count"),
        "not_found_count": metrics.get("not_found_count"),
        "answer_count": answer_stats.get("execution_count", 0),
        "answered_count": answer_stats.get("answered_count", 0),
        "generated_python_count": answer_stats.get("generated_python_count", 0),
        "dry_run": args.dry_run,
        "protected_file_count": protected_file_count,
        "temporary_office_file_count": temporary_office_file_count,
        "decryption_attempt_count": decryption_attempt_count,
        "decryption_success_count": decryption_success_count,
        "decryption_failure_count": decryption_failure_count,
        "filename_password_success_count": filename_password_success_count,
        "rule_derived_password_success_count": rule_derived_password_success_count,
        "ambiguous_password_count": ambiguous_password_count,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "forbidden_input_prefixes": list(FORBIDDEN_INPUT_PREFIXES),
        "forbidden_input_check_path": relative_to_root(logs_dir / "forbidden_input_check.json", root),
    }
    write_json(output_dir / "source_selection_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="Run raw-to-Agentic-RAG pipeline.")
    parser.add_argument("--mode", choices=["source-selection", "end-to-end"], default="source-selection")
    parser.add_argument("--split", choices=["valid", "test"], default="valid")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--use-cache", action="store_true")
    parser.add_argument("--reuse-extraction-cache", action="store_true", help="--use-cacheと同じくraw抽出・復号成果物だけを再利用する")
    parser.add_argument("--cache-source-run", default="", help="rawから生成済みのwork runを明示的なキャッシュ元として使う")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--raw-root", type=Path, default=root / "data" / "raw" / "share" / "share" / "共有ドライブ")
    parser.add_argument("--questions-path", type=Path, default=None)
    parser.add_argument("--api-mode", choices=["off", "auto", "on"], default="off")
    parser.add_argument("--semantic-api-mode", choices=["off", "auto", "on"], default="off")
    parser.add_argument("--semantic-config", type=Path, default=Path("config/openrouter_free.json"))
    parser.add_argument("--semantic-model", default="")
    parser.add_argument("--model", default="openai/gpt-oss-20b:free")
    parser.add_argument("--planner-model", default="")
    parser.add_argument("--selector-model", default="")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--candidate-top-n", type=int, default=12)
    parser.add_argument("--selector-candidate-limit", type=int, default=12)
    parser.add_argument("--max-additional-searches", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--question-ids", default="")
    parser.add_argument("--no-api-cache", action="store_true")
    parser.add_argument("--use-plan-cache", action="store_true")
    parser.add_argument("--no-plan-cache", action="store_true", default=True)
    parser.add_argument("--no-execution-cache", action="store_true", default=True)
    parser.add_argument("--no-answer-cache", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", help="計画とツール一覧だけ作成し、回答本文は生成しない")
    parser.add_argument("--disable-table-executor", action="store_true", help="表処理Vertical Sliceを無効化し、比較用の旧経路を使う")
    parser.add_argument("--table-slice-only", action="store_true", help="質問文から表対象を抽出し、関連raw表だけをfresh再抽出する")
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--max-pdf-render-pages", type=int, default=0)
    parser.add_argument("--render-pdf-pages", dest="render_pdf_pages", action="store_true", default=True)
    parser.add_argument("--no-render-pdf-pages", dest="render_pdf_pages", action="store_false")
    parser.add_argument("--resolve-protected-files", dest="resolve_protected_files", action="store_true", default=True)
    parser.add_argument("--skip-protected-files", dest="resolve_protected_files", action="store_false")
    parser.add_argument("--strict-protected-files", action="store_true")
    args = parser.parse_args()
    if args.reuse_extraction_cache:
        args.use_cache = True
    if args.questions_path is None:
        args.questions_path = questions_path_for_split(root, args.split)
    args.planner_model = args.planner_model or args.model
    args.selector_model = args.selector_model or args.model
    if isinstance(args.question_ids, str):
        raw_ids = [part.strip() for part in args.question_ids.split(",") if part.strip()]
        args.question_ids = [int(part) for part in raw_ids]
    if not args.fresh and not args.use_cache:
        args.fresh = True
    return args


def main() -> None:
    args = parse_args()
    summary = run_source_selection(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
