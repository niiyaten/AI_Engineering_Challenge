from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


FORBIDDEN_INPUT_PREFIXES = ("EDA", "data/processed", "submissions")


class ProhibitedInputError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def assert_formal_input_allowed(path: Path, root: Path) -> None:
    """正式パイプラインが禁止済み成果物を入力として読まないように検査する。"""
    rel = relative_to_root(path, root).replace("\\", "/")
    for prefix in FORBIDDEN_INPUT_PREFIXES:
        if rel == prefix or rel.startswith(prefix + "/"):
            raise ProhibitedInputError(f"正式パイプラインの入力として禁止されたパスです: {rel}")


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def read_text_allowed(path: Path, root: Path, encoding: str = "utf-8") -> str:
    assert_formal_input_allowed(path, root)
    return path.read_text(encoding=encoding, errors="replace")


def read_json_allowed(path: Path, root: Path) -> Any:
    return json.loads(read_text_allowed(path, root))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl_allowed(path: Path, root: Path) -> list[dict[str, Any]]:
    assert_formal_input_allowed(path, root)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_allowed(path: Path, root: Path) -> list[dict[str, str]]:
    assert_formal_input_allowed(path, root)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def get_git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=5,
        )
        stdout = result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else str(result.stdout)
        return stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def dependency_lock_hash(root: Path) -> str:
    lock_path = root / "uv.lock"
    return sha1_file(lock_path) if lock_path.exists() else ""


def python_version() -> str:
    return sys.version.replace("\n", " ")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        for child in path.iterdir():
            if child.is_dir():
                import shutil

                shutil.rmtree(child)
            else:
                child.unlink()
    path.mkdir(parents=True, exist_ok=True)


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
