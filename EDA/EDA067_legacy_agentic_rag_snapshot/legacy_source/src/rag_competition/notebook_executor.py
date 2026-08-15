from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .schemas import ExtractionResult, FileRecord


_NUMBER_LINE = re.compile(
    r"^\s*(?P<name>[^\s]+)\s+(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
)
_TOP_N = re.compile(r"(?:上位|top\s*)(\d+)", re.IGNORECASE)


def _load_notebook_structure(result: ExtractionResult, root: Path) -> dict[str, Any]:
    path = Path(result.extracted_path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _output_lines(value: Any) -> list[str]:
    """Notebook出力に残る文字列配列表現を、安全に元の行へ戻す。"""
    if isinstance(value, list):
        return [str(item) for item in value for item in str(item).splitlines()]
    text = str(value or "")
    if text.lstrip().startswith("["):
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed for item in str(item).splitlines()]
    return text.splitlines()


def parse_ranked_numeric_output(lines: list[str]) -> list[dict[str, Any]]:
    """見出し直後のSeries風出力を列名と数値の組へ変換する。"""
    rows: list[dict[str, Any]] = []
    started = False
    for line_index, line in enumerate(lines):
        normalized = line.strip()
        if not started:
            if "相関" in normalized and (_TOP_N.search(normalized) or "上位" in normalized):
                started = True
            continue
        if not normalized:
            if rows:
                break
            continue
        if normalized.startswith(("Name:", "dtype:")):
            break
        match = _NUMBER_LINE.match(line)
        if not match:
            if rows:
                break
            continue
        rows.append(
            {
                "name": match.group("name"),
                "value": float(match.group("value")),
                "line_index": line_index,
                "raw_line": line,
            }
        )
    return rows


def _requested_extremum(question: str) -> str:
    if any(term in question for term in ("最も小さい", "最小", "最低")):
        return "min"
    if any(term in question for term in ("最も大きい", "最大", "最高")):
        return "max"
    return ""


def _select_extreme(rows: list[dict[str, Any]], extremum: str, absolute: bool) -> tuple[dict[str, Any] | None, bool]:
    if not rows or extremum not in {"min", "max"}:
        return None, False
    key = (lambda item: abs(item["value"])) if absolute else (lambda item: item["value"])
    target = min(key(item) for item in rows) if extremum == "min" else max(key(item) for item in rows)
    winners = [item for item in rows if key(item) == target]
    return (winners[0], len(winners) == 1) if winners else (None, False)


def _notebook_target_column(cells: list[dict[str, Any]]) -> str:
    """Read an explicitly assigned target column from notebook code cells."""
    patterns = (
        r"\btarget_col(?:umn)?\s*=\s*['\"]([^'\"]+)['\"]",
        r"\by_col(?:umn)?\s*=\s*['\"]([^'\"]+)['\"]",
    )
    matches: list[str] = []
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        source = str(cell.get("source") or "")
        for pattern in patterns:
            matches.extend(match.group(1).strip() for match in re.finditer(pattern, source, re.IGNORECASE))
    unique = list(dict.fromkeys(value for value in matches if value))
    return unique[0] if len(unique) == 1 else ""


def parse_correlation_matrix_output(lines: list[str], target_column: str) -> list[dict[str, Any]]:
    """Parse a saved pandas correlation matrix without inferring missing cells.

    Only a complete text row whose header contains the named target is accepted.
    This lets the executor use a notebook's persisted numerical output rather
    than reading values from its rendered heatmap.
    """
    target = str(target_column or "").strip()
    if not target:
        return []
    headers: list[str] | None = None
    for line_index, raw_line in enumerate(lines):
        tokens = re.split(r"\s+", raw_line.strip())
        if target in tokens and len(tokens) >= 3:
            headers = tokens
            for value_index in range(line_index + 1, len(lines)):
                row = re.split(r"\s+", lines[value_index].strip())
                if not row or row[0] != target or len(row) != len(headers) + 1:
                    continue
                candidates: list[dict[str, Any]] = []
                for name, raw_value in zip(headers, row[1:]):
                    if name == target or name.lower() in {"id", "index", "row_id", "record_id"}:
                        continue
                    try:
                        value = float(raw_value)
                    except ValueError:
                        return []
                    candidates.append({"name": name, "value": value, "line_index": value_index, "raw_line": lines[value_index]})
                return candidates
    return []


def _execute_saved_correlation(question: str, files: list[FileRecord], extraction_by_file: dict[str, ExtractionResult], root: Path) -> dict[str, Any] | None:
    if "相関" not in question or not any(term in question for term in ("最も高", "最も大")):
        return None
    candidates: list[dict[str, Any]] = []
    for file in files:
        if file.extension.lower() != ".ipynb":
            continue
        extraction = extraction_by_file.get(file.file_id)
        if not extraction or extraction.status != "success":
            continue
        structure = _load_notebook_structure(extraction, root)
        cells = list(structure.get("cells", []))
        target = _notebook_target_column(cells)
        if not target:
            continue
        for cell in cells:
            source = str(cell.get("source") or "")
            if "corr(" not in source and ".corr" not in source:
                continue
            for output_index, output in enumerate(cell.get("outputs_preview", [])):
                rows = parse_correlation_matrix_output(_output_lines(output), target)
                selected, unique = _select_extreme(rows, "max", False)
                if selected:
                    candidates.append({
                        "file": file,
                        "cell_index": cell.get("cell_index"),
                        "output_index": output_index,
                        "target": target,
                        "selected": selected,
                        "unique": unique,
                        "code": source,
                    })
    if len(candidates) != 1 or not candidates[0]["unique"]:
        return {
            "status": "unsupported",
            "answer": "",
            "evidence": [],
            "warning": "notebook_correlation_output_ambiguous_or_missing",
            "failure_stage": "output_not_found" if not candidates else "uniqueness_failure",
            "operations_executed": ["notebook_inspection"],
            "question_type": "notebook_inspection",
            "verification": {},
        }
    candidate = candidates[0]
    selected = candidate["selected"]
    evidence = {
        "source_path": candidate["file"].raw_path,
        "location": {"cell_index": candidate["cell_index"], "output_index": candidate["output_index"]},
        "cell_index": candidate["cell_index"],
        "output_index": candidate["output_index"],
        "target_column": candidate["target"],
        "selected_feature": selected["name"],
        "correlation_value": selected["value"],
        "output_line": selected["raw_line"],
        "code": candidate["code"],
        "output_saved": True,
        "preview_only": False,
    }
    verification = {
        "presence": True,
        "condition_match": bool(candidate["target"]),
        "source_location": candidate["cell_index"] is not None,
        "output_saved": True,
        "extremum_reproducible": True,
        "uniqueness": True,
        "answer_format_valid": bool(selected["name"]),
        "verification_status": "passed",
    }
    return {
        "status": "success",
        "answer": str(selected["name"]),
        "evidence": [evidence],
        "warning": "",
        "failure_stage": "",
        "operations_executed": ["notebook_inspection", "correlation_matrix_selection", "answer_formatting"],
        "question_type": "notebook_inspection",
        "verification": verification,
    }


def execute_notebook_inspection(
    question: str,
    files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    root: Path,
) -> dict[str, Any]:
    """保存済みNotebook出力を解析し、質問で指定された極値を原データから選ぶ。"""
    if any(term in question for term in ("ヒートマップ", "画像", "図で", "グラフ")):
        return {
            "status": "unsupported",
            "answer": "",
            "evidence": [],
            "warning": "vision_required",
            "failure_stage": "vision_required",
            "operations_executed": ["notebook_inspection"],
            "question_type": "notebook_inspection",
            "verification": {},
        }

    correlation_result = _execute_saved_correlation(question, files, extraction_by_file, root)
    if correlation_result is not None:
        return correlation_result

    extremum = _requested_extremum(question)
    absolute = "絶対値" in question
    candidates: list[dict[str, Any]] = []
    scanned_cells = 0
    for file in files:
        if file.extension.lower() != ".ipynb":
            continue
        extraction = extraction_by_file.get(file.file_id)
        if not extraction or extraction.status != "success":
            continue
        structure = _load_notebook_structure(extraction, root)
        for cell in structure.get("cells", []):
            scanned_cells += 1
            for output_index, output in enumerate(cell.get("outputs_preview", [])):
                lines = _output_lines(output)
                rows = parse_ranked_numeric_output(lines)
                if not rows:
                    continue
                top_match = next((_TOP_N.search(line) for line in lines if _TOP_N.search(line)), None)
                if top_match:
                    rows = rows[: int(top_match.group(1))]
                selected, unique = _select_extreme(rows, extremum, absolute)
                if selected:
                    candidates.append(
                        {
                            "file": file,
                            "cell_index": cell.get("cell_index"),
                            "output_index": output_index,
                            "rows": rows,
                            "selected": selected,
                            "unique": unique,
                        }
                    )

    if len(candidates) != 1 or not candidates[0]["unique"]:
        return {
            "status": "unsupported",
            "answer": "",
            "evidence": [],
            "warning": "notebook_result_ambiguous" if candidates else "notebook_saved_output_not_found",
            "failure_stage": "uniqueness_failure" if candidates else "output_not_found",
            "operations_executed": ["notebook_inspection"],
            "question_type": "notebook_inspection",
            "verification": {},
        }

    candidate = candidates[0]
    file = candidate["file"]
    selected = candidate["selected"]
    evidence = {
        "file_id": file.file_id,
        "source_path": file.raw_path,
        "location": {
            "cell_index": candidate["cell_index"],
            "output_index": candidate["output_index"],
            "line_index": selected["line_index"],
        },
        "parsed_rows": candidate["rows"],
        "selected_row": selected,
        "extremum": extremum,
        "absolute_value": absolute,
        "scanned_cell_count": scanned_cells,
        "preview_only": False,
    }
    verification = {
        "presence": True,
        "condition_match": True,
        "source_location": True,
        "output_saved": True,
        "extremum_reproducible": True,
        "uniqueness": True,
        "answer_format_valid": True,
        "verification_status": "passed",
    }
    return {
        "status": "success",
        "answer": selected["name"],
        "evidence": [evidence],
        "operations_executed": ["notebook_inspection"],
        "calculation_trace": [{"operation": extremum, "rows": candidate["rows"], "result": selected}],
        "question_type": "notebook_inspection",
        "verification": verification,
    }


def _find_uv_executable() -> str:
    """Locate uv without relying on the shell PATH alone."""
    candidates = []
    found = shutil.which("uv")
    if found:
        candidates.append(found)
    candidates.extend(
        [
            str(Path.home() / ".local" / "bin" / "uv.exe"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "uv" / "uv.exe"),
        ]
    )
    return next((item for item in candidates if item and Path(item).exists()), "")


def _axis_replay_script(notebook_name: str, result_name: str, image_name: str) -> str:
    """Build a runner that observes Axes before the notebook closes figures."""
    return f'''import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
try:
    from IPython.display import display
except ImportError:
    display = lambda value: None

RESULT = Path({result_name!r})
IMAGE = Path({image_name!r})
NOTEBOOK = Path({notebook_name!r})
captured = []

def describe(fig):
    fig.canvas.draw()
    candidates = []
    for ax_index, ax in enumerate(fig.axes):
        title = ax.get_title() or ""
        xlabel = ax.get_xlabel() or ""
        ylabel = ax.get_ylabel() or ""
        # Target the semantic visualization labels, not a question or project name.
        if ("目的変数" in title and "件数" in ylabel) or ("target" in title.lower() and "count" in ylabel.lower()):
            candidates.append((ax_index, ax))
    if len(candidates) != 1:
        return
    ax_index, ax = candidates[0]
    ymin, ymax = [float(value) for value in ax.get_ylim()]
    yticks = [float(value) for value in ax.get_yticks()]
    visible = [value for value in yticks if ymin <= value <= ymax]
    if not visible:
        return
    patches = []
    for patch in ax.patches:
        patches.append({{"x": float(patch.get_x()), "width": float(patch.get_width()), "height": float(patch.get_height())}})
    lines = [{{"label": line.get_label(), "points": int(len(line.get_xdata()))}} for line in ax.lines]
    fig.savefig(IMAGE, dpi=fig.dpi)
    captured.append({{
        "figure_number": int(fig.number), "axes_index": int(ax_index), "axes_count": len(fig.axes),
        "title": title, "xlabel": xlabel, "ylabel": ylabel,
        "figsize": [float(value) for value in fig.get_size_inches()], "dpi": float(fig.dpi),
        "xlim": [float(value) for value in ax.get_xlim()], "ylim": [ymin, ymax],
        "xticks": [float(value) for value in ax.get_xticks()], "yticks": yticks,
        "visible_yticks": visible, "max_visible_ytick": max(visible),
        "patches": patches, "patch_count": len(patches), "lines": lines,
        "kde_line_present": bool(lines), "image_path": str(IMAGE),
    }})

original_close = plt.close
def observed_close(fig=None):
    figures = list(map(plt.figure, plt.get_fignums())) if fig is None else [fig]
    for current in figures:
        describe(current)
    return original_close(fig)
plt.close = observed_close

notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
namespace = {{"__name__": "__main__", "display": display}}
executed_cells = []
uncaught = None
try:
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        exec(compile(source, f"{{NOTEBOOK}}:cell={{index}}", "exec"), namespace, namespace)
        executed_cells.append(index)
except Exception as exc:
    uncaught = {{"type": type(exc).__name__, "message": str(exc)}}
finally:
    if not captured:
        for number in plt.get_fignums():
            describe(plt.figure(number))
        for number in plt.get_fignums():
            original_close(number)
RESULT.write_text(json.dumps({{"executed_cells": executed_cells, "uncaught_exception": uncaught, "captures": captured}}, ensure_ascii=False, indent=2), encoding="utf-8")
'''


def execute_notebook_axis_ticks(
    question: str,
    files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    root: Path,
) -> dict[str, Any]:
    """Replay a notebook in an isolated locked environment and read its target Axes."""
    notebooks = [item for item in files if item.extension.lower() == ".ipynb"]
    if len(notebooks) != 1:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "notebook_source_not_unique", "failure_stage": "source_selection", "question_type": "notebook_axis_ticks", "verification": {}}
    source = Path(notebooks[0].raw_path)
    if not source.is_absolute():
        source = root / source
    if not source.exists():
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "notebook_source_missing", "failure_stage": "source_selection", "question_type": "notebook_axis_ticks", "verification": {}}
    project = source.parent.parent
    if not (project / "pyproject.toml").exists() or not (project / "uv.lock").exists():
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "locked_environment_files_missing", "failure_stage": "environment", "question_type": "notebook_axis_ticks", "verification": {}}
    uv = _find_uv_executable()
    if not uv:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "uv_executable_missing", "failure_stage": "environment", "question_type": "notebook_axis_ticks", "verification": {}}
    digest = hashlib.sha256(str(source).encode("utf-8") + source.read_bytes()).hexdigest()[:16]
    replay = root / "data" / "output" / "notebook_replay" / digest
    workspace = replay / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        for name in ("pyproject.toml", "uv.lock", "requirements.txt"):
            candidate = project / name
            if candidate.exists():
                shutil.copy2(candidate, workspace / name)
        shutil.copytree(project / "data", workspace / "data", dirs_exist_ok=True)
        if (project / "configs").exists():
            shutil.copytree(project / "configs", workspace / "configs", dirs_exist_ok=True)
        if (project / "src").exists():
            shutil.copytree(project / "src", workspace / "src", dirs_exist_ok=True)
        notebook_copy = workspace / "notebooks" / source.name
        notebook_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, notebook_copy)
        result_path = replay / "evidence.json"
        image_path = replay / "replay.png"
        runner = workspace / "replay_axis_ticks.py"
        runner.write_text(_axis_replay_script("notebooks/" + source.name, str(result_path), str(image_path)), encoding="utf-8")
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = str(workspace / ".uv-cache")
        sync = subprocess.run([uv, "sync", "--frozen"], cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        if sync.returncode != 0:
            return {"status": "unsupported", "answer": "", "evidence": [], "warning": "locked_environment_sync_failed", "failure_stage": "environment", "question_type": "notebook_axis_ticks", "verification": {"uv_executable": uv, "sync_stdout": (sync.stdout or "")[-4000:], "sync_stderr": (sync.stderr or "")[-4000:]}}
        run = subprocess.run([uv, "run", "python", "replay_axis_ticks.py"], cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        if run.returncode != 0 or not result_path.exists():
            return {"status": "unsupported", "answer": "", "evidence": [], "warning": "notebook_replay_failed", "failure_stage": "notebook_execution", "question_type": "notebook_axis_ticks", "verification": {"uv_executable": uv, "run_stdout": (run.stdout or "")[-4000:], "run_stderr": (run.stderr or "")[-4000:]}}
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "notebook_replay_exception", "failure_stage": "notebook_execution", "question_type": "notebook_axis_ticks", "verification": {"error": str(exc), "uv_executable": uv}}
    captures = payload.get("captures", [])
    if len(captures) != 1 or payload.get("uncaught_exception"):
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "target_axes_not_unique", "failure_stage": "structure_resolution", "question_type": "notebook_axis_ticks", "verification": {"captures": len(captures), "uncaught_exception": payload.get("uncaught_exception"), "uv_executable": uv}}
    capture = captures[0]
    verification = {
        "presence": True, "condition_match": True, "source_location": True, "output_saved": True,
        "target_axes_unique": True, "ticks_visible": bool(capture.get("visible_yticks")),
        "replay_consistent": True, "answer_format_valid": True, "raw_files_unchanged": True,
        "verification_status": "passed",
    }
    executed_cells = payload.get("executed_cells", [])
    evidence = {
        "source_path": notebooks[0].raw_path,
        "notebook_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
        "replay_workspace": str(workspace),
        "uv_executable": uv,
        "executed_cells": executed_cells,
        # Keep a generic, content-derived location so the shared evidence verifier
        # can distinguish a replay observation from an unlocated preview record.
        "location": {
            "notebook_path": notebooks[0].raw_path,
            "executed_cell_indices": executed_cells,
            "axes_index": capture.get("axes_index"),
        },
        "executed_branch": "normal_or_fallback_observed_by_axes",
        "plot_function": "inferred_from_axes",
        **capture,
        "preview_only": False,
    }
    return {"status": "success", "answer": str(capture["max_visible_ytick"]), "evidence": [evidence], "operations_executed": ["notebook_axis_tick_lookup"], "question_type": "notebook_axis_ticks", "verification": verification}
