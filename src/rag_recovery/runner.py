from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .executors.chart import EmbeddedChartExecutor
from .executors.direct import DirectStructuredExecutor
from .executors.code_json import CodeJsonAnalysisExecutor
from .executors.cross_project import CrossProjectEnumerationExecutor
from .executors.diff import DocumentDiffExecutor
from .executors.document import DocumentLookupExecutor
from .executors.join import MultiDocumentJoinExecutor
from .executors.office_format import OfficeFormatCommentExecutor
from .executors.table import TableQueryExecutor
from .executors.spatial_layout import SpatialLayoutExecutor
from .models import ExecutionResult, Question, QueryPlan
from .normalize import norm
from .planner import plan_question
from .store import DocumentStore
from .verifier import EvidenceVerifier, choose_nonconflicting
from .vision_client import OpenAICompatibleVisionClient
from .executors.vision import VisionFallbackExecutor
from .fact_catalog import EvidenceFactCatalog


PHASE_ROUTES = {
    "phase1": {"direct", "table", "document", "cross_project", "code_json", "join"},
    "phase2": {"direct", "diff", "office_format", "chart", "join"},
    "phase12": {"direct", "table", "document", "cross_project", "code_json", "diff", "office_format", "chart", "join"},
    "phase3": {"direct", "spatial_layout"},
    "phase123": {"direct", "table", "document", "cross_project", "code_json", "diff", "office_format", "chart", "join", "spatial_layout"},
}


class RecoveryRunner:
    def __init__(self, share_root: Path, *, min_confidence: float = 0.80, phase: str = "phase12", vision_client: OpenAICompatibleVisionClient | None = None, fact_catalog: Path | None = None):
        self.share_root = share_root.resolve()
        self.store = DocumentStore(self.share_root)
        self.verifier = EvidenceVerifier(self.share_root, min_confidence=min_confidence)
        self.phase = phase
        self.vision_client = vision_client
        self.fact_catalog = EvidenceFactCatalog(fact_catalog, self.share_root) if fact_catalog else None
        self.executors = {
            "direct": DirectStructuredExecutor(),
            "table": TableQueryExecutor(),
            "document": DocumentLookupExecutor(),
            "cross_project": CrossProjectEnumerationExecutor(),
            "code_json": CodeJsonAnalysisExecutor(),
            "diff": DocumentDiffExecutor(),
            "join": MultiDocumentJoinExecutor(),
            "office_format": OfficeFormatCommentExecutor(),
            "chart": EmbeddedChartExecutor(),
            "spatial_layout": SpatialLayoutExecutor(),
        }

    def solve(self, question: Question) -> tuple[ExecutionResult, dict]:
        attempts = []
        if self.fact_catalog is not None:
            phases = {"baseline", "official", "phase1", "phase2"} if self.phase == "phase12" else ({"baseline", "official", "phase1", "phase2", "phase3"} if self.phase == "phase123" else {"baseline", "official", self.phase})
            cached = self.fact_catalog.lookup(question, phases)
            if cached is not None:
                decision = self.verifier.verify(question, cached)
                attempts.append({"route": "fact_catalog", "answered": cached.answered, "answer": cached.answer if cached.answered else "", "confidence": cached.confidence, "method": cached.method, "verification": asdict(decision), "reason": cached.reason})
                if decision.accepted:
                    cached.diagnostics.setdefault("verification", asdict(decision))
                    return cached, {"attempts": attempts, "chosen_method": cached.method, "verification": asdict(decision), "cache_hit": True}
        verified = []
        allowed = PHASE_ROUTES.get(self.phase, PHASE_ROUTES["phase12"])
        base_plans = plan_question(question)
        # The direct executor is a source-derived, high-precision operation planner.
        # Run it first for every question. It does not use question IDs or stored answers.
        direct_plan = QueryPlan(
            route="direct",
            project_hints=base_plans[0].project_hints if base_plans else (),
            filename_hints=base_plans[0].filename_hints if base_plans else (),
            operations=base_plans[0].operations if base_plans else (),
            entities=base_plans[0].entities if base_plans else (),
            constraints=base_plans[0].constraints if base_plans else {},
            source_mode=base_plans[0].source_mode if base_plans else "single_document",
        )
        plans = base_plans if (base_plans and base_plans[0].route == "spatial_layout") else [direct_plan, *base_plans]
        for plan in plans:
            if plan.route not in allowed:
                continue
            executor = self.executors.get(plan.route)
            if executor is None:
                continue
            try:
                result = executor.execute(question, plan, self.store)
            except Exception as exc:  # keep one executor failure from aborting full130
                result = ExecutionResult.abstain(f"executor_exception:{type(exc).__name__}", diagnostics={"exception": repr(exc)})
            decision = self.verifier.verify(question, result)
            attempts.append({
                "route": plan.route,
                "operations": list(plan.operations),
                "project_hints": list(plan.project_hints),
                "filename_hints": list(plan.filename_hints),
                "answered": result.answered,
                "answer": result.answer if result.answered else "",
                "confidence": result.confidence,
                "method": result.method,
                "verification": asdict(decision),
                "reason": result.reason,
                "diagnostics": {k: v for k, v in result.diagnostics.items() if k != "attempts"},
            })
            verified.append((result, decision))
            if plan.route == "direct" and decision.accepted:
                result.diagnostics.setdefault("verification", asdict(decision))
                return result, {"attempts": attempts, "chosen_method": result.method, "verification": asdict(decision), "direct_hit": True}
        chosen = choose_nonconflicting(verified)
        if chosen is None and self.vision_client is not None and self.phase in {"phase2", "phase12", "phase123"}:
            fallback_plan = next((p for p in plan_question(question) if p.route in {"chart", "office_format", "document"}), plan_question(question)[0])
            try:
                vision_result = VisionFallbackExecutor(self.vision_client).execute(question, fallback_plan, self.store)
            except Exception as exc:
                vision_result = ExecutionResult.abstain(f"vision_exception:{type(exc).__name__}", diagnostics={"exception": repr(exc)})
            vision_decision = self.verifier.verify(question, vision_result)
            attempts.append({"route": "vision", "answered": vision_result.answered, "answer": vision_result.answer if vision_result.answered else "", "confidence": vision_result.confidence, "method": vision_result.method, "verification": asdict(vision_decision), "reason": vision_result.reason, "diagnostics": vision_result.diagnostics})
            chosen = choose_nonconflicting([(vision_result, vision_decision)])
        if chosen is None:
            return ExecutionResult.abstain("accepted_answer_not_unique_or_not_found", diagnostics={"attempts": attempts}), {"attempts": attempts}
        result, decision = chosen
        result.diagnostics.setdefault("verification", asdict(decision))
        return result, {"attempts": attempts, "chosen_method": result.method, "verification": asdict(decision)}

    def run_csv(self, answers_csv: Path, output_dir: Path, *, retry: str = "unknown") -> dict:
        rows, fieldnames = _read_csv(answers_csv)
        output_dir.mkdir(parents=True, exist_ok=True)
        logs = []
        initial_unknown = sum(_is_unknown(row.get("answer", "")) for row in rows)
        route_counts: Counter[str] = Counter()
        recovered = 0
        attempted = 0

        for row in rows:
            should_retry = retry == "all" or _is_unknown(row.get("answer", ""))
            if not should_retry:
                continue
            attempted += 1
            selected = tuple(x.strip() for x in str(row.get("selected_sources", "")).splitlines() if x.strip())
            question = Question(
                split=str(row.get("split", "")),
                question_id=int(float(row.get("question_id", 0))),
                text=str(row.get("question", "")),
                selected_sources=selected,
            )
            previous_answer = str(row.get("answer", ""))
            result, trace = self.solve(question)
            if result.answered:
                recovered += 1
                route_counts[result.method] += 1
                row["answer"] = result.answer
                row["confidence_score"] = f"{result.confidence:.3f}"
                row["confidence_level"] = "high" if result.confidence >= .90 else "medium"
                row["source_mode"] = "multi_document" if len({e.source for e in result.evidence}) > 1 else "single_document"
                sources = list(dict.fromkeys(e.source for e in result.evidence))
                row["selected_sources"] = "\n".join(sources)
                row["source_count"] = str(len(sources))
                row["evidence_locator"] = " | ".join(f"{e.source}::{e.locator}" for e in result.evidence[:8])
                row["evidence"] = " | ".join(e.detail.replace("\n", " ")[:300] for e in result.evidence[:8])
                row["method"] = result.method
                row["unknown_reason"] = ""
                row["human_review_used"] = "False"
            logs.append({
                "split": question.split,
                "question_id": question.question_id,
                "question": question.text,
                "previous_answer": previous_answer,
                "answered": result.answered,
                "answer": result.answer,
                "confidence": result.confidence,
                "method": result.method,
                "reason": result.reason,
                "evidence": [asdict(e) for e in result.evidence],
                "trace": trace,
            })

        output_csv = output_dir / "answers_130_phase12_recovered.csv"
        _write_csv(output_csv, rows, fieldnames)
        evidence_jsonl = output_dir / "recovery_evidence.jsonl"
        with evidence_jsonl.open("w", encoding="utf-8") as fh:
            for item in logs:
                fh.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

        remaining_unknown = sum(_is_unknown(row.get("answer", "")) for row in rows)
        summary = {
            "input_rows": len(rows),
            "share_files": len(self.store.records),
            "projects": len(self.store.projects),
            "retry_mode": retry,
            "phase": self.phase,
            "initial_unknown": initial_unknown,
            "attempted": attempted,
            "recovered": recovered,
            "remaining_unknown": remaining_unknown,
            "method_counts": dict(route_counts),
            "outputs": {"csv": str(output_csv), "evidence_jsonl": str(evidence_jsonl)},
        }
        (output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "run_summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
        return summary


def _is_unknown(value: object) -> bool:
    return norm(value) in {"", norm("わからない"), norm("わかりません"), norm("不明")}


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with path.open("r", encoding=encoding, newline="") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"CSV encoding could not be detected: {path}") from last_error


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    required = ["answer", "confidence_score", "confidence_level", "source_mode", "selected_sources", "source_count", "evidence_locator", "evidence", "method", "unknown_reason", "human_review_used"]
    names = list(dict.fromkeys([*fieldnames, *required]))
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _summary_markdown(summary: dict) -> str:
    return "\n".join([
        "# Phase 1/2 recovery run",
        "",
        f"- Input rows: {summary['input_rows']}",
        f"- Indexed files: {summary['share_files']}",
        f"- Projects: {summary['projects']}",
        f"- Initial unknown: {summary['initial_unknown']}",
        f"- Attempted: {summary['attempted']}",
        f"- Recovered: {summary['recovered']}",
        f"- Remaining unknown: {summary['remaining_unknown']}",
        f"- Phase: {summary['phase']}",
        "",
        "## Methods",
        *[f"- {key}: {value}" for key, value in sorted(summary["method_counts"].items())],
        "",
    ])
