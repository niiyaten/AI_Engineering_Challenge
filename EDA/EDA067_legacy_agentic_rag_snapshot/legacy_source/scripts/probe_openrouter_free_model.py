from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rag_competition.llm_client import OpenRouterClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", type=Path, default=Path("config/openrouter_free.json"))
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    models = config.get("allowed_models", [])
    if not config.get("free_models_only") or not models or any(not str(model).endswith(":free") for model in models):
        raise SystemExit("free-model-only configuration is invalid")
    model = str(models[0])
    run_dir = Path("data/work") / args.run_id
    output_dir = Path("data/output") / args.run_id / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    client = OpenRouterClient(project_root=Path.cwd(), output_dir=run_dir / "logs", model=model, temperature=0.0, timeout_sec=30, max_retries=1, use_cache=False)
    rows = []
    for index in range(args.attempts):
        started = time.perf_counter()
        prompt = (
            'Choose the candidate described as a yellow fruit. '
            'Candidates: cand_1=apple, cand_2=banana. '
            'Return exactly {"selected_candidate_ids":["cand_2"]}.'
        )
        result = client.call_json("free_model_probe_%d" % (index + 1), prompt, max_tokens=400)
        selected = result.parsed_json.get("selected_candidate_ids", []) if result.parse_success else []
        rows.append({
            "configured_model": model, "actual_model": result.model, "free_model_only": True,
            "request_success": result.success, "http_status": result.http_status or "", "response_received": bool(result.raw_response_path),
            "json_parse_success": result.parse_success, "latency": round(time.perf_counter() - started, 3),
            "candidate_id_valid": selected == ["cand_2"],
            "retry_count": result.retry_count, "fallback_used": False, "error_type": result.error,
        })
    path = output_dir / "openrouter_free_model_probe.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (output_dir / "openrouter_free_model_probe.md").write_text(
        "# OpenRouter free model probe\n\n"
        f"- configured model: {model}\n- free-only: true\n- paid fallback: false\n"
        f"- calls: {len(rows)}\n- successes: {sum(bool(row['request_success']) for row in rows)}\n"
        f"- JSON parses: {sum(bool(row['json_parse_success']) for row in rows)}\n",
        encoding="utf-8",
    )
    print(json.dumps({"model": model, "calls": len(rows), "successes": sum(bool(row["request_success"]) for row in rows), "parse_successes": sum(bool(row["json_parse_success"]) for row in rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
