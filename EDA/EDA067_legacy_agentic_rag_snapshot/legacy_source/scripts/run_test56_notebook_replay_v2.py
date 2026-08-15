"""Run the generic notebook axis route twice and save audit evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from pathlib import Path

from rag_competition.notebook_executor import execute_notebook_axis_ticks
from rag_competition.schemas import FileRecord


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "output" / "test56_notebook_replay_v2"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    raw_root = ROOT / "data" / "raw" / "share" / "share"
    project = next(path for path in raw_root.rglob("01_eda.ipynb") if "蒼泉会" in str(path))
    questions_path = next(raw_root.rglob("questions_test.csv"))
    with questions_path.open(encoding="utf-8-sig", newline="") as handle:
        question = next(row["question"] for row in csv.DictReader(handle) if int(row["index"]) == 56)
    tracked = [project, project.parent.parent / "data" / "train.csv", project.parent.parent / "pyproject.toml", project.parent.parent / "uv.lock"]
    before = {str(path): file_hash(path) for path in tracked}
    record = FileRecord("notebook_axis_probe", str(project), str(project.relative_to(ROOT)), project.name, ".ipynb", project.stat().st_size, "", file_hash(project)[:40], "", "", "", "notebook", "")
    results = []
    for run_number in (1, 2):
        result = execute_notebook_axis_ticks(question, [record], {}, ROOT)
        result_path = OUT / "evidence" / f"evidence_run{run_number}.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence = (result.get("evidence") or [{}])[0]
        image = Path(evidence.get("image_path", ""))
        copied = OUT / "images" / f"replay_run{run_number}.png"
        copied.parent.mkdir(parents=True, exist_ok=True)
        if image.exists():
            shutil.copy2(image, copied)
        results.append({"status": result.get("status"), "answer": result.get("answer"), "evidence": evidence, "image_hash": file_hash(copied) if copied.exists() else ""})
    after = {str(path): file_hash(path) for path in tracked}
    comparable = ("answer", "title", "xlabel", "ylabel", "figsize", "dpi", "xlim", "ylim", "xticks", "yticks", "visible_yticks", "max_visible_ytick", "patches", "patch_count")
    consistent = all(results[0]["evidence"].get(key) == results[1]["evidence"].get(key) for key in comparable) and results[0]["image_hash"] == results[1]["image_hash"]
    final = {"question": question, "source_notebook": str(project), "raw_hashes_before": before, "raw_hashes_after": after, "raw_files_unchanged": before == after, "run1": results[0], "run2": results[1], "rerun_consistent": consistent, "gate_allowed": bool(consistent and results[0]["status"] == "success"), "gate_reason": "deterministic_replay_and_evidence_verified" if consistent else "rerun_mismatch"}
    (OUT / "evidence" / "final_evidence.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "logs" / "replay_summary.log").write_text(json.dumps({"run1": results[0]["answer"], "run2": results[1]["answer"], "consistent": consistent}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"answer": results[0]["answer"], "consistent": consistent, "raw_files_unchanged": before == after, "gate_allowed": final["gate_allowed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
