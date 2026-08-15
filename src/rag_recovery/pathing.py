from __future__ import annotations

from pathlib import Path


def locate_content_root(root: Path) -> Path:
    """Find the directory whose children contain 共有ドライブ / 質問回答.

    ZIPs may contain share/share/... or a single flat root. The resolver is
    structure-based, so additional wrapper directories do not require code changes.
    """
    root = root.resolve()
    candidates = [root, *[p for p in root.rglob("*") if p.is_dir() and len(p.relative_to(root).parts) <= 4]]
    scored: list[tuple[int, int, Path]] = []
    for p in candidates:
        score = int((p / "共有ドライブ").is_dir()) * 10 + int((p / "質問回答").is_dir()) * 5
        if score:
            scored.append((score, -len(p.parts), p))
    return max(scored)[2] if scored else root
