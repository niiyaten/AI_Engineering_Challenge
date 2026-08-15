from __future__ import annotations

import argparse
import json
from pathlib import Path

from .archive import extract_zip_safely
from .pathing import locate_content_root
from .office_crypto import prepare_office_tree
from .runner import RecoveryRunner
from .vision_client import OpenAICompatibleVisionClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generic deterministic Phase 1/2/3 recovery runner")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--share-zip", type=Path, help="Original share.zip")
    source.add_argument("--share-root", type=Path, help="Already extracted share directory")
    parser.add_argument("--answers-csv", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("data/interim/rag_recovery_phase12"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--retry", choices=("unknown", "all"), default="unknown")
    parser.add_argument("--phase", choices=("phase1", "phase2", "phase3", "phase12", "phase123"), default="phase12")
    parser.add_argument("--min-confidence", type=float, default=0.80)
    parser.add_argument("--vision-model", default="", help="Optional OpenAI-compatible vision model")
    parser.add_argument("--vision-base-url", default="", help="OpenAI-compatible API base URL")
    parser.add_argument("--vision-api-key", default="", help="API key; prefer environment variables")
    parser.add_argument("--fact-catalog", type=Path, default=None, help="Optional source-hash-bound fact cache from a previous deterministic run")
    parser.add_argument("--prepare-office", action="store_true", help="Ignore Office temp files and decrypt rule-protected documents into the workspace")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.share_zip:
        share_root = locate_content_root(extract_zip_safely(args.share_zip, args.workspace / "share"))
    else:
        share_root = locate_content_root(args.share_root)
    crypto_events = []
    if args.prepare_office:
        share_root, crypto_events = prepare_office_tree(share_root, args.workspace)
    vision_client = None
    if args.vision_model:
        vision_client = OpenAICompatibleVisionClient(model=args.vision_model, base_url=args.vision_base_url or None, api_key=args.vision_api_key or None)
    runner = RecoveryRunner(share_root, min_confidence=args.min_confidence, phase=args.phase, vision_client=vision_client, fact_catalog=args.fact_catalog)
    summary = runner.run_csv(args.answers_csv, args.output_dir, retry=args.retry)
    if crypto_events:
        summary["office_preparation"] = crypto_events
        (args.output_dir / "office_preparation.json").write_text(json.dumps(crypto_events, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
