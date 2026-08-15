"""Deterministic conversion from numeric evidence values to submission strings."""

from __future__ import annotations

import math
import re
from decimal import Decimal


_DECIMAL_REQUEST = re.compile(r"(?:小数|decimal|decimal places|digits after the decimal point)", re.IGNORECASE)
_SCIENTIFIC_NOTATION = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+$")


def normalize_submission_number(value: object, question: str = "") -> tuple[str, str]:
    """Remove a meaningless trailing .0 without changing requested precision."""
    # Preserve a caller's explicit scientific-notation representation.  This
    # function only removes the trailing .0 produced by an integer-like float.
    if isinstance(value, str) and _SCIENTIFIC_NOTATION.fullmatch(value.strip()):
        return value, "unchanged_scientific_notation"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value), "unchanged_non_numeric"
    if not math.isfinite(number):
        return str(value), "unchanged_non_finite"
    if _DECIMAL_REQUEST.search(question or ""):
        return str(value), "unchanged_requested_precision"
    if number.is_integer():
        return str(int(number)), "integer_like_float"
    return str(value), "unchanged_fractional"


def normalize_submission_value(value: object, question: str = "") -> dict[str, object]:
    """Keep the raw value and the separately normalized submission string."""
    submission, normalization = normalize_submission_number(value, question)
    return {"raw_answer_value": value, "submission_answer": submission, "normalization": normalization}
