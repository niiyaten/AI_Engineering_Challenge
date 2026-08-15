from __future__ import annotations

import re
from typing import Any


DATE_PATTERN = re.compile(r"^(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日|\d{8}|\d{1,2}月\d{1,2}日)(?:\s+.*)?$")


def verify_document_extraction(answer: str, items: list[dict[str, Any]], spec: Any, scanned_count: int, total_count: int, question_type: str = "") -> dict[str, Any]:
    texts = [str(item.get("text", "")) for item in items]
    presence = bool(answer.strip()) and bool(items) and all(text in answer for text in texts if text)
    condition_match = all(all(item.get("matched_format_conditions", {}).get(key) for key, value in spec.format_conditions.items() if value is True and key in {"bold", "italic", "underline"}) for item in items)
    exclusion_match = True
    if any(condition.get("type") == "date" for condition in spec.exclude_conditions):
        exclusion_match = not any(DATE_PATTERN.match(text.strip()) for text in texts)
    location_match = all(bool(item.get("location")) for item in items)
    completeness = scanned_count >= total_count if spec.selection_mode == "all" else True
    uniqueness = True if question_type == "format_only" else len(items) == 1 if spec.selection_mode == "single" else True
    verbatim_match = answer == "\n".join(texts) or answer == "".join(texts) if spec.verbatim else True
    passed = all((presence, condition_match, exclusion_match, location_match, completeness, uniqueness, verbatim_match))
    warnings: list[str] = []
    if not completeness: warnings.append("全対象範囲の走査を確認できません")
    if not uniqueness: warnings.append("候補が一意ではありません")
    if not verbatim_match: warnings.append("原文一致を確認できません")
    return {"presence": presence, "condition_match": condition_match, "exclusion_match": exclusion_match, "location_match": location_match, "completeness": completeness, "uniqueness": uniqueness, "verbatim_match": verbatim_match, "verification_status": "passed" if passed else "failed", "warnings": warnings}
