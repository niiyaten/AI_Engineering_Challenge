from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


def _safe_members(zf: zipfile.ZipFile, target: Path):
    target_resolved = target.resolve()
    for info in zf.infolist():
        destination = (target / info.filename).resolve()
        if destination != target_resolved and target_resolved not in destination.parents:
            raise ValueError(f"unsafe ZIP member: {info.filename}")
        yield info


def prepare_workspace(share_zip: Path, workspace: Path, *, refresh: bool = False) -> Path:
    if not share_zip.exists():
        raise FileNotFoundError(f"share.zip not found: {share_zip}")
    extract_root = workspace / "share"
    marker = extract_root / ".extracted_ok"
    signature = f"{share_zip.resolve()}|{share_zip.stat().st_size}|{share_zip.stat().st_mtime_ns}"
    if not refresh and marker.exists() and marker.read_text(encoding="utf-8") == signature:
        return extract_root
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(share_zip) as zf:
        zf.extractall(extract_root, members=_safe_members(zf, extract_root))
    marker.write_text(signature, encoding="utf-8")
    return extract_root


def extract_zip_safely(share_zip: Path, extract_root: Path, *, refresh: bool = False) -> Path:
    """Extract to an explicit directory, rejecting path traversal members."""
    if not share_zip.exists():
        raise FileNotFoundError(f"share.zip not found: {share_zip}")
    marker = extract_root / ".extracted_ok"
    signature = f"{share_zip.resolve()}|{share_zip.stat().st_size}|{share_zip.stat().st_mtime_ns}"
    if not refresh and marker.exists() and marker.read_text(encoding="utf-8") == signature:
        return extract_root
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(share_zip) as zf:
        zf.extractall(extract_root, members=_safe_members(zf, extract_root))
    marker.write_text(signature, encoding="utf-8")
    return extract_root
