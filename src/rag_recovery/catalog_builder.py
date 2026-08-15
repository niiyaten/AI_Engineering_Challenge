from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .archive import extract_zip_safely
from .models import Question
from .office_crypto import prepare_office_tree
from .pathing import locate_content_root
from .runner import RecoveryRunner
from .vision_client import OpenAICompatibleVisionClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a source-bound fact catalog with the generic executors")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--share-zip", type=Path)
    source.add_argument("--share-root", type=Path)
    parser.add_argument("--questions-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path("data/interim/rag_catalog_build"))
    parser.add_argument("--phase", choices=("phase1", "phase2", "phase12"), default="phase12")
    parser.add_argument("--min-confidence", type=float, default=.80)
    parser.add_argument("--prepare-office", action="store_true")
    parser.add_argument("--vision-model", default="")
    parser.add_argument("--vision-base-url", default="")
    parser.add_argument("--vision-api-key", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.share_zip:
        root = locate_content_root(extract_zip_safely(args.share_zip, args.workspace / "share"))
    else:
        root = locate_content_root(args.share_root)
    if args.prepare_office:
        root, events = prepare_office_tree(root, args.workspace)
        (args.output.parent / "catalog_office_preparation.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    vision = OpenAICompatibleVisionClient(model=args.vision_model, base_url=args.vision_base_url or None, api_key=args.vision_api_key or None) if args.vision_model else None
    runner = RecoveryRunner(root, phase=args.phase, min_confidence=args.min_confidence, vision_client=vision)
    rows = _read_csv(args.questions_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    built = 0
    with args.output.open("w", encoding="utf-8") as fh:
        for row in rows:
            text = str(row.get("question", ""))
            if not text:
                continue
            question = Question(str(row.get("split", "")), int(float(row.get("question_id", row.get("index", 0)))), text)
            result, trace = runner.solve(question)
            if not result.answered:
                continue
            evidence = []
            for ev in result.evidence:
                path = root / ev.source
                evidence.append({"source": ev.source, "locator": ev.locator, "detail": ev.detail, "value": ev.value, "sha256": _sha256(path) if path.exists() else ""})
            fact = {
                "question": text,
                "answer": result.answer,
                "confidence": result.confidence,
                "method": result.method,
                "phase": _phase_for_method(result.method),
                "evidence": evidence,
                "diagnostics": {"built_by": "generic_executors", "trace": trace},
            }
            fh.write(json.dumps(fact, ensure_ascii=False, default=str) + "\n")
            built += 1
    print(json.dumps({"questions": len(rows), "facts_built": built, "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with path.open(encoding=encoding, newline="") as fh:
                return list(csv.DictReader(fh))
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"Unable to decode {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _phase_for_method(method: str) -> str:
    phase2_markers = (
        "version_diff",
        "semantic_diff",
        "office_format",
        "run_format",
        "layout",
        "embedded_chart",
        "chart_visual",
        "visual_extract",
        "vision",
    )
    if any(marker in method for marker in phase2_markers):
        return "phase2"
    return "phase1"


if __name__ == "__main__":
    raise SystemExit(main())
