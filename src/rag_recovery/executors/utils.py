from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from ..normalize import nfkc, norm

DATE_RE = re.compile(r"(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})日?")
NUMBER_RE = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?")
CONDITION_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_./-]*|[一-龥ぁ-んァ-ヶー]+)\s*(=|==|>=|<=|>|<|≧|≦|以上|以下|未満|超)\s*([^、。\s]+)")


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    m = DATE_RE.search(nfkc(value))
    if m:
        return date(*map(int, m.groups()))
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, np.number)) and np.isfinite(value):
        return float(value)
    m = NUMBER_RE.search(nfkc(value).replace("円", "").replace("ドル", ""))
    return float(m.group().replace(",", "")) if m else None


def format_number(value: float, question: str, *, unit: str = "") -> str:
    q = nfkc(question)
    digits_match = re.search(r"小数第(\d+)位", q)
    if digits_match:
        digits = int(digits_match.group(1))
        return f"{value:.{digits}f}{unit}"
    if "切り上げ" in q:
        value = math.ceil(value)
    elif "切り捨て" in q:
        value = math.floor(value)
    elif "四捨五入" in q:
        value = math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)
    if abs(value - round(value)) < 1e-10:
        iv = int(round(value))
        return f"{iv:,}{unit}" if unit in {"円", "ドル", "USD"} or any(k in q for k in ("円", "ドル", "金額", "総額")) else f"{iv}{unit}"
    return f"{value:g}{unit}"


def normalize_columns(df: pd.DataFrame) -> dict[str, str]:
    return {norm(col): str(col) for col in df.columns}


def resolve_column(df: pd.DataFrame, hint: str) -> str | None:
    mapping = normalize_columns(df)
    nh = norm(hint)
    if nh in mapping:
        return mapping[nh]
    matches = [original for key, original in mapping.items() if nh and (nh in key or key in nh)]
    return matches[0] if len(matches) == 1 else None


def parse_explicit_conditions(question: str, df: pd.DataFrame) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for raw_col, op, raw_value in CONDITION_RE.findall(nfkc(question)):
        col = resolve_column(df, raw_col)
        if col:
            out.append((col, op, raw_value.strip("'\"」』")))
    return out


def apply_conditions(df: pd.DataFrame, conditions: list[tuple[str, str, str]]) -> tuple[pd.DataFrame, list[str]]:
    mask = pd.Series(True, index=df.index)
    notes: list[str] = []
    for col, op, raw in conditions:
        series = df[col]
        num = parse_number(raw)
        if num is not None and pd.api.types.is_numeric_dtype(series):
            s = pd.to_numeric(series, errors="coerce")
            if op in ("=", "=="):
                current = s.eq(num)
            elif op in (">", "超"):
                current = s.gt(num)
            elif op in (">=", "≧", "以上"):
                current = s.ge(num)
            elif op in ("<", "未満"):
                current = s.lt(num)
            else:
                current = s.le(num)
        else:
            sval = series.astype(str).map(norm)
            target = norm(raw)
            current = sval.eq(target) if op in ("=", "==") else sval.str.contains(target, regex=False)
        mask &= current.fillna(False)
        notes.append(f"{col}{op}{raw}: {int(current.fillna(False).sum())} rows")
    return df.loc[mask].copy(), notes


def read_table_file(rec, store):
    if rec.extension in {".csv", ".tsv"}:
        return [("file", store.read_csv(rec))]
    if rec.extension in {".xlsx", ".xlsm"}:
        wb = store.load_workbook(rec, data_only=True)
        out = []
        for ws in wb.worksheets:
            values = list(ws.values)
            if not values:
                continue
            # Try likely header rows in first 30 rows; maximize unique nonempty strings.
            best_row = 0
            best_score = -1
            for i, row in enumerate(values[:30]):
                score = len({norm(v) for v in row if v not in (None, "")})
                if score > best_score:
                    best_score, best_row = score, i
            header = [str(v) if v not in (None, "") else f"column_{j+1}" for j, v in enumerate(values[best_row])]
            data = values[best_row + 1 :]
            if data:
                out.append((ws.title, pd.DataFrame(data, columns=header)))
        return out
    return []
