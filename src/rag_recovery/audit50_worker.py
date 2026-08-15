# third_audit_executor_overlay_v2_runtime_fix
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from .executors.audit_generalization import AuditGeneralizationExecutor
from .executors.remaining50_generalization import Remaining50GeneralizationExecutor
from .executors.scoring_precision import ScoringPrecisionExecutor
from .executors.tm_invoice_difference import TMInvoiceDifferenceExecutor
from .models import QueryPlan, Question
from .runner import RecoveryRunner
from .store import DocumentStore


SPECIALIZED_EXECUTORS = (
    ScoringPrecisionExecutor(),
    TMInvoiceDifferenceExecutor(),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-root", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    payload = {"index": args.index, "question": args.question}

    try:
        store = DocumentStore(Path(args.prepared_root))
        store_seconds = time.perf_counter() - started
        question = Question("test", args.index, args.question, ())
        specialized_attempts: list[dict[str, object]] = []

        result = None
        route = ""
        audit_elapsed = 0.0
        trace: dict[str, object] = {}

        for executor in SPECIALIZED_EXECUTORS:
            attempt_started = time.perf_counter()
            candidate = executor.execute(
                question,
                QueryPlan(executor.name),
                store,
            )
            attempt_elapsed = time.perf_counter() - attempt_started
            specialized_attempts.append(
                {
                    "executor": executor.name,
                    "answered": bool(candidate.answered),
                    "reason": candidate.reason,
                    "elapsed_seconds": round(attempt_elapsed, 6),
                }
            )
            if candidate.answered:
                result = candidate
                route = executor.name
                trace = {
                    "specialized_route": executor.name,
                    "specialized_attempts": specialized_attempts,
                    "remaining50_route": False,
                    "audit_route": False,
                    "base_route": False,
                }
                break

        if result is None:
            remaining_started = time.perf_counter()
            remaining = Remaining50GeneralizationExecutor().execute(
                question,
                QueryPlan("remaining50_generalization"),
                store,
            )
            remaining_elapsed = time.perf_counter() - remaining_started

            if remaining.answered:
                result = remaining
                route = "remaining50_generalization"
                trace = {
                    "specialized_attempts": specialized_attempts,
                    "remaining50_route": True,
                    "audit_route": False,
                    "base_route": False,
                }
            else:
                audit_started = time.perf_counter()
                audit = AuditGeneralizationExecutor().execute(
                    question,
                    QueryPlan("audit_generalization"),
                    store,
                )
                audit_elapsed = time.perf_counter() - audit_started

                if audit.answered:
                    result = audit
                    route = "audit_generalization"
                    trace = {
                        "specialized_attempts": specialized_attempts,
                        "remaining50_abstain_reason": remaining.reason,
                        "remaining50_diagnostics": remaining.diagnostics,
                        "remaining50_elapsed_seconds": remaining_elapsed,
                        "audit_route": True,
                        "base_route": False,
                    }
                else:
                    base_started = time.perf_counter()
                    runner = RecoveryRunner(
                        Path(args.prepared_root),
                        min_confidence=0.80,
                        phase="phase123",
                        fact_catalog=None,
                    )
                    result, base_trace = runner.solve(question)
                    base_elapsed = time.perf_counter() - base_started
                    route = "base_recovery"
                    trace = {
                        "specialized_attempts": specialized_attempts,
                        "remaining50_abstain_reason": remaining.reason,
                        "remaining50_diagnostics": remaining.diagnostics,
                        "remaining50_elapsed_seconds": remaining_elapsed,
                        "audit_abstain_reason": audit.reason,
                        "audit_diagnostics": audit.diagnostics,
                        "base_trace": base_trace,
                        "base_elapsed_seconds": base_elapsed,
                    }

        assert result is not None
        payload.update(
            answered=bool(result.answered),
            answer=result.answer if result.answered else "わからない",
            confidence=float(result.confidence),
            method=result.method,
            reason=result.reason,
            route=route,
            evidence=[asdict(item) for item in result.evidence],
            diagnostics=result.diagnostics,
            trace=trace,
            store_seconds=store_seconds,
            audit_elapsed_seconds=audit_elapsed,
            manifest_files=len(store.records),
            projects=len(store.projects),
        )
    except Exception as exc:
        payload.update(
            answered=False,
            answer="わからない",
            confidence=0.0,
            method="exception",
            reason=repr(exc),
            route="exception",
            evidence=[],
            diagnostics={"traceback": traceback.format_exc()},
            trace={},
            store_seconds=0.0,
            audit_elapsed_seconds=0.0,
            manifest_files=0,
            projects=0,
        )

    payload["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    os.replace(temporary, output)
    os._exit(0)


if __name__ == "__main__":
    main()
