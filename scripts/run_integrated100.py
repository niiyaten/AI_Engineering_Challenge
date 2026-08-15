from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from rag_recovery.archive import extract_zip_safely
from rag_recovery.office_crypto import prepare_office_tree
from rag_recovery.pathing import locate_content_root


def read_questions(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [
            {"index": int(row["index"]), "question": row["question"]}
            for row in csv.DictReader(f)
        ]
    ids = [int(row["index"]) for row in rows]
    if len(rows) != 100 or len(set(ids)) != 100 or set(ids) != set(range(100)):
        raise ValueError("questions must contain unique indices 0..99")
    return sorted(rows, key=lambda row: int(row["index"]))


def run_worker(
    prepared_root: Path,
    row: dict[str, object],
    worker_dir: Path,
    timeout: int,
) -> dict:
    index = int(row["index"])
    output_path = worker_dir / f"{index:03d}.json"
    stderr_path = worker_dir / f"{index:03d}.stderr.log"
    worker_dir.mkdir(parents=True, exist_ok=True)
    for path in (output_path, output_path.with_suffix(".json.tmp")):
        if path.exists():
            path.unlink()

    cmd = [
        sys.executable,
        "-m",
        "rag_recovery.audit50_worker",
        "--prepared-root",
        str(prepared_root),
        "--index",
        str(index),
        "--question",
        str(row["question"]),
        "--output-json",
        str(output_path),
    ]
    with stderr_path.open("w", encoding="utf-8") as stderr_file:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            start_new_session=True,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if output_path.exists() and output_path.stat().st_size:
                result = json.loads(output_path.read_text(encoding="utf-8"))
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                return result
            if proc.poll() is not None:
                error = stderr_path.read_text(encoding="utf-8", errors="replace")[-3000:]
                raise RuntimeError(f"worker {index} failed rc={proc.returncode}: {error}")
            time.sleep(0.1)

        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return {
            "index": index,
            "question": row["question"],
            "answered": False,
            "answer": "わからない",
            "confidence": 0.0,
            "method": "timeout",
            "reason": f"timeout_{timeout}s",
            "route": "timeout",
            "evidence": [],
            "elapsed_seconds": timeout,
            "diagnostics": {},
            "trace": {},
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--share-zip", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--question-timeout", type=int, default=240)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    share_zip = Path(args.share_zip).resolve()
    workspace = Path(args.workspace).resolve()
    output_dir = Path(args.output_dir).resolve()
    questions_path = Path(args.questions).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    prepare_start = time.perf_counter()
    extracted = extract_zip_safely(share_zip, workspace / "extracted", refresh=args.refresh)
    content_root = locate_content_root(extracted)
    prepared_root, office_events = prepare_office_tree(content_root, workspace / "office")
    unresolved = [event for event in office_events if event.get("status") == "unresolved_encryption"]
    if unresolved:
        raise RuntimeError(f"unresolved encrypted Office documents: {unresolved}")
    prepare_seconds = time.perf_counter() - prepare_start

    questions = read_questions(questions_path)
    worker_dir = output_dir / "workers"
    raw_path = output_dir / "audit100_raw_results.jsonl"
    evidence_path = output_dir / "audit100_evidence.jsonl"
    results: list[dict] = []
    execution_start = time.perf_counter()

    with raw_path.open("w", encoding="utf-8") as raw_file, evidence_path.open(
        "w", encoding="utf-8"
    ) as evidence_file:
        for number, row in enumerate(questions, 1):
            try:
                result = run_worker(prepared_root, row, worker_dir, args.question_timeout)
            except Exception as exc:
                result = {
                    "index": int(row["index"]),
                    "question": row["question"],
                    "answered": False,
                    "answer": "わからない",
                    "confidence": 0.0,
                    "method": "orchestrator_exception",
                    "reason": repr(exc),
                    "route": "exception",
                    "evidence": [],
                    "elapsed_seconds": 0.0,
                    "diagnostics": {},
                    "trace": {},
                }
            results.append(result)
            raw_file.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
            raw_file.flush()
            for evidence in result.get("evidence", []):
                evidence_file.write(
                    json.dumps(
                        {
                            "index": int(row["index"]),
                            "question": row["question"],
                            **evidence,
                        },
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )
            evidence_file.flush()
            print(
                f"[{number:03d}/100] index={row['index']} "
                f"answered={result.get('answered')} route={result.get('route')} "
                f"method={result.get('method')} elapsed={result.get('elapsed_seconds')}s",
                flush=True,
            )

    fields = [
        "index",
        "question",
        "answered",
        "answer",
        "confidence",
        "route",
        "method",
        "reason",
        "elapsed_seconds",
        "evidence_count",
    ]
    with (output_dir / "audit100_answers.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    **{field: result.get(field, "") for field in fields},
                    "evidence_count": len(result.get("evidence", [])),
                }
            )

    with (output_dir / "predictions.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        for result in sorted(results, key=lambda item: int(item["index"])):
            writer.writerow(
                [
                    int(result["index"]),
                    result.get("answer", "わからない")
                    if result.get("answered")
                    else "わからない",
                ]
            )

    execution_seconds = time.perf_counter() - execution_start
    summary = {
        "cold_start": True,
        "question_count": 100,
        "answered_count": sum(bool(result.get("answered")) for result in results),
        "abstained_count": sum(not bool(result.get("answered")) for result in results),
        "evidence_answered_count": sum(
            bool(result.get("answered")) and bool(result.get("evidence")) for result in results
        ),
        "remaining50_route_count": sum(
            result.get("route") == "remaining50_generalization" for result in results
        ),
        "audit_route_count": sum(
            result.get("route") == "audit_generalization" for result in results
        ),
        "base_route_count": sum(result.get("route") == "base_recovery" for result in results),
        "timeout_count": sum(result.get("method") == "timeout" for result in results),
        "exception_count": sum(
            result.get("route") == "exception" or result.get("method") == "exception"
            for result in results
        ),
        "prepare_seconds": round(prepare_seconds, 3),
        "execution_wall_seconds": round(execution_seconds, 3),
        "total_wall_seconds": round(prepare_seconds + execution_seconds, 3),
        "question_elapsed_seconds": round(
            sum(float(result.get("elapsed_seconds", 0)) for result in results), 3
        ),
        "runtime_inputs": {
            "source_mode": "share_zip_cold_prepare",
            "prepared_source_tree": str(prepared_root),
            "share_zip": str(share_zip),
            "questions": str(questions_path),
            "fact_catalog": False,
            "prior_answers": False,
            "expected_answers": False,
            "external_api": False,
        },
        "office_events": office_events,
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
