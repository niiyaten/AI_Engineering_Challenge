from __future__ import annotations

import re
from pathlib import Path

ROLE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("proposal", ("00.提案", "提案書", "調査")),
    ("contract", ("01.契約", "契約書")),
    ("schedule", ("02.計画", "スケジュール", "plan")),
    ("data", ("03.データ", "train.csv", "train.xlsx", "カラム説明")),
    ("analysis", ("04.分析", "metrics.json", "leaderboard", "modeling.py", "features.py")),
    ("meeting", ("05.会議", "会議録", "報告資料")),
    ("final_report", ("06.報告書", "最終報告")),
    ("internal", ("社内管理", "社内")),
    ("questions", ("質問回答", "questions_")),
)


def infer_project(relative_path: str) -> str:
    parts = Path(relative_path).parts
    for marker in ("プロジェクト", "projects"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return ""


def infer_area(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if "プロジェクト" in parts:
        return "project"
    if "社内管理" in parts:
        return "internal"
    if "質問回答" in parts:
        return "questions"
    return "other"


def infer_role(relative_path: str) -> str:
    low = relative_path.lower()
    scores = [(sum(key.lower() in low for key in keys), role) for role, keys in ROLE_RULES]
    score, role = max(scores)
    return role if score else "other"


def infer_version(path: str) -> str:
    low = path.lower()
    if "/old/" in low or "_old" in low or "old." in low or "old版" in low:
        return "old"
    if "draft" in low or "ドラフト" in low:
        return "draft"
    m = re.search(r"(?:^|[_-])v(\d+)(?:\D|$)", low)
    if m:
        return f"v{m.group(1)}"
    m = re.search(r"_r(\d+)(?:\D|$)", low)
    if m:
        return f"r{m.group(1)}"
    return "current"
