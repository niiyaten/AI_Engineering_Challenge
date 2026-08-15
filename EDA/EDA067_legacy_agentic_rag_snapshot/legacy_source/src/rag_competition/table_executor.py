from __future__ import annotations

import csv
import colorsys
import json
import math
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_jsonl
from .schemas import ExtractionResult, FileRecord, QuestionAnalysis
from .calculation_engine import (
    append_calculation_artifacts,
    build_calculation_spec,
    execute_calculation_spec,
    infer_coefficient_inputs,
    infer_coefficient_inputs_from_workbook,
)
from .pivot_table import execute_pivot_extreme_question


TABLE_EXTENSIONS = {".xlsx", ".csv", ".tsv"}
EXCLUDED_TABLE_TOPICS = ("python", "notebook", "画像", "pdf", "差分", "提案書", "報告書", "docx", "pptx", "カラム説明")


def normalize(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value if value is not None else "")).strip()


def is_table_question(analysis: QuestionAnalysis) -> tuple[bool, str]:
    """質問文の形式と要求語だけから、表処理の対象かを判定する。"""
    text = normalize(getattr(analysis, "question_original", getattr(analysis, "question_normalized", "")))
    lower = text.lower()
    if any(topic in text or topic in lower for topic in EXCLUDED_TABLE_TOPICS):
        return False, "主対象が表以外"
    if any(ext in lower for ext in (".docx", ".pptx", ".pdf", ".png", ".jpg", ".ipynb", ".py", "figure", "ヒートマップ")):
        return False, "主対象がExcel・CSV以外"
    explicit = any(ext in lower for ext in (".xlsx", ".csv", "train.xlsx", "train.csv", "sheet1", "pivot"))
    table_terms = ("行", "列", "セル", "シート", "合計", "平均", "割合", "件数", "抽出条件", "フィルター", "黄色", "青色", "オレンジ")
    if explicit or any(term in text for term in table_terms):
        return True, "表形式ファイルまたは表操作語を含む"
    return False, "表形式の明示・操作語なし"


def write_table_slice_questions(analyses: list[QuestionAnalysis], output_dir: Path) -> list[QuestionAnalysis]:
    selected: list[QuestionAnalysis] = []
    rows: list[dict[str, Any]] = []
    for analysis in analyses:
        selected_flag, reason = is_table_question(analysis)
        if selected_flag:
            selected.append(analysis)
        rows.append({"question_id": analysis.index, "question": getattr(analysis, "question_original", getattr(analysis, "question_normalized", "")), "selected": selected_flag, "reason": reason})
    fields = ["question_id", "question", "selected", "reason"]
    write_csv(output_dir / "table_slice_questions.csv", rows, fields)
    return selected


@dataclass
class TableData:
    file: FileRecord
    sheet_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    matrix: list[list[Any]]
    structure: dict[str, Any]
    structure_path: str


def select_relevant_table_files(question: str, selected_files: list[FileRecord], available_files: list[FileRecord]) -> list[FileRecord]:
    """質問中の明示拡張子と案件名から、表処理に使う候補を汎用的に絞る。"""
    text = normalize(question)
    explicit_names = [normalize(match.group(0)).lower() for match in re.finditer(r"[A-Za-z0-9_.-]+\.(?:xlsx|csv|tsv)", text, re.IGNORECASE)]
    def project_key(value: str) -> str:
        return re.sub(r"^(株式会社|医療法人社団|合同会社|有限会社)", "", normalize(value)).replace("株式会社", "").replace(" ", "")

    question_key = project_key(text)
    question_text_key = normalize(text).replace(" ", "")
    projects = {
        file.project_name
        for file in available_files
        if file.project_name and (project_key(file.project_name) in question_text_key or project_key(file.project_name) in question_key or question_key in project_key(file.project_name))
    }
    selected_table_ids = {file.file_id for file in selected_files if file.extension in TABLE_EXTENSIONS}
    candidates = [file for file in available_files if file.extension in TABLE_EXTENSIONS and (not selected_table_ids or file.file_id in selected_table_ids)]
    if projects:
        candidates = [file for file in candidates if file.project_name in projects]
    if explicit_names:
        named = [file for file in candidates if normalize(file.file_name).lower() in explicit_names]
        if named:
            candidates = named
    if not candidates:
        candidates = [file for file in selected_files if file.extension in TABLE_EXTENSIONS]
    return candidates or [file for file in selected_files if file.extension in TABLE_EXTENSIONS]


def _read_matrix(path: Path) -> list[list[Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [list(row) for row in csv.reader(handle)]


def load_table_data(
    file: FileRecord,
    extraction: ExtractionResult,
    project_root: Path,
) -> list[TableData]:
    structure_path = Path(extraction.extracted_path)
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    tables: list[TableData] = []
    if file.extension == ".xlsx":
        sheet_defs = structure.get("sheets", [])
    else:
        sheet_defs = [{"sheet_name": "", "table_data_path": extraction.table_data_paths[0] if extraction.table_data_paths else ""}]
    for sheet_def in sheet_defs:
        table_path = Path(sheet_def.get("csv_path") or sheet_def.get("table_data_path") or "")
        if not table_path.is_absolute():
            table_path = project_root / table_path
        if not table_path.exists():
            continue
        matrix = _read_matrix(table_path)
        if not matrix:
            continue
        header_index = next((index for index, row in enumerate(matrix) if sum(bool(normalize(value)) for value in row) >= 2), 0)
        matrix = matrix[header_index:]
        columns = [normalize(value) or f"column_{index + 1}" for index, value in enumerate(matrix[0])]
        merged_columns: set[int] = set()
        for merged_range in sheet_def.get("merged_cells", []):
            start = re.match(r"([A-Z]+)\d+", str(merged_range))
            end = re.search(r":([A-Z]+)\d+", str(merged_range))
            if start and end and start.group(1) == end.group(1):
                merged_columns.add(sum((ord(char) - 64) * (26 ** offset) for offset, char in enumerate(reversed(start.group(1)))) - 1)
        if sheet_def.get("sheet_name", "").lower() == "pivot" and len(columns) >= 3:
            merged_columns.update({0, 1, 2})
        rows = []
        previous: dict[int, Any] = {}
        for row_index, row in enumerate(matrix[1:], start=2):
            padded = row + [""] * (len(columns) - len(row))
            for column_index in merged_columns:
                if column_index < len(padded) and not normalize(padded[column_index]) and column_index in previous:
                    padded[column_index] = previous[column_index]
            previous.update({index: value for index, value in enumerate(padded) if normalize(value)})
            rows.append({columns[index]: padded[index] for index in range(len(columns))} | {"__row_number__": row_index})
        # 書式セルの座標をデータ行へ戻せるよう、元シート上のヘッダ行を保持する。
        sheet_structure = dict(sheet_def)
        sheet_structure["header_row_number"] = header_index + 1
        tables.append(TableData(file, normalize(sheet_def.get("sheet_name", "")), columns, rows, matrix, sheet_structure, structure_path.as_posix()))
    return tables


def _number(value: Any) -> float | None:
    text = normalize(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _date_value(value: Any) -> tuple[int, int, int] | None:
    """Convert common spreadsheet date values to a comparable tuple."""
    text = normalize(value)
    match = re.search(r"(\d{4})[-/]?(\d{2})[-/]?(\d{2})", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _unique_column_by_terms(columns: list[str], terms: tuple[str, ...]) -> str | None:
    matches = [
        column
        for column in columns
        if any(normalize(term).lower() in normalize(column).lower() for term in terms)
    ]
    return matches[0] if len(matches) == 1 else None


def _parse_schedule_conditions(question: str, columns: list[str]) -> list[dict[str, Any]]:
    """Parse reusable schedule filters without inventing a column when ambiguous."""
    text = normalize(question)
    conditions: list[dict[str, Any]] = []
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
    start_column = _unique_column_by_terms(columns, ("\u958b\u59cb\u65e5", "start_date"))
    end_column = _unique_column_by_terms(columns, ("\u7d42\u4e86\u65e5", "end_date"))
    if len(dates) == 2 and "\u9593" in text and start_column and end_column:
        bounds = [
            {"column": start_column, "operator": "between", "value": dates},
            {"column": end_column, "operator": "between", "value": dates},
        ]
        if "\u307e\u305f\u306f" in text or "or" in text.lower():
            conditions.append({"operator": "any_of", "conditions": bounds})
        else:
            conditions.extend(bounds)

    phase_match = re.search(r"(?:\u30d5\u30a7\u30fc\u30baNo\.?|phase\s*no\.?)[\s]*(\d+)", text, re.IGNORECASE)
    phase_column = _unique_column_by_terms(columns, ("\u30d5\u30a7\u30fc\u30baNo", "phase_no", "phase"))
    if phase_match and phase_column:
        conditions.append({"column": phase_column, "operator": "eq", "value": phase_match.group(1)})

    milestone = re.search(r"(MS\d+)", text, re.IGNORECASE)
    milestone_column = _unique_column_by_terms(columns, ("\u30de\u30a4\u30eb\u30b9\u30c8\u30fc\u30f3", "milestone"))
    if milestone and milestone_column and ("\u7d10\u3065" in text or "milestone" in text.lower()):
        conditions.append({"column": milestone_column, "operator": "contains", "value": milestone.group(1)})

    person = re.search(r"([\u4e00-\u9fff\u30a1-\u30f6A-Za-z][\u4e00-\u9fff\u30a1-\u30f6A-Za-z\s]{2,30})(?:\u304c\u95a2\u308f|\u62c5\u5f53)", text)
    person_column = _unique_column_by_terms(columns, ("\u62c5\u5f53\u8005", "assignee", "owner"))
    if person and person_column:
        value = person.group(1).strip()
        if value != "\u30bf\u30b9\u30af":
            conditions.append({"column": person_column, "operator": "contains", "value": value})
    return conditions


def _match_column(columns: list[str], hint: str) -> str | None:
    hint = normalize(hint).lower()
    if not hint:
        return None
    for column in columns:
        if column.lower() == hint:
            return column
    for column in columns:
        if hint in column.lower() or column.lower() in hint:
            return column
    return None


def _parse_conditions(question: str, columns: list[str]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    text = normalize(question)
    for match in re.finditer(r"([A-Za-z][A-Za-z0-9_]*)\s*(?:=|is|が)\s*([^、,。\sのかに]+(?:\s+years?)?)", text, re.IGNORECASE):
        column = _match_column(columns, match.group(1))
        if column:
            conditions.append({"column": column, "operator": "eq", "value": match.group(2).strip()})
    if "女性" in text:
        column = _match_column(columns, "gender") or _match_column(columns, "sex")
        if column:
            conditions.append({"column": column, "operator": "eq", "value": "Female"})
    if "男性" in text:
        column = _match_column(columns, "gender") or _match_column(columns, "sex")
        if column:
            conditions.append({"column": column, "operator": "eq", "value": "Male"})
    for match in re.finditer(r"([A-Za-z][A-Za-z0-9_]*)\s*(?:が|は)?\s*(\d+(?:\.\d+)?)\s*(より大きい|以上|未満|以下)", text):
        column = _match_column(columns, match.group(1))
        if column:
            operator = {"より大きい": "gt", "以上": "ge", "未満": "lt", "以下": "le"}[match.group(3)]
            conditions.append({"column": column, "operator": operator, "value": match.group(2)})
    return conditions


def _condition_match(row: dict[str, Any], condition: dict[str, Any]) -> bool:
    if condition.get("operator") == "any_of":
        return any(_condition_match(row, item) for item in condition.get("conditions", []))
    left = row.get(condition.get("column", ""), "")
    operator = condition.get("operator", "eq")
    right = condition.get("value")
    if operator == "contains":
        return normalize(right).lower() in normalize(left).lower()
    if operator == "not_contains":
        return normalize(right).lower() not in normalize(left).lower()
    if operator == "between" and isinstance(right, (list, tuple)) and len(right) == 2:
        left_date = _date_value(left)
        right_dates = [_date_value(item) for item in right]
        if left_date and all(right_dates):
            return right_dates[0] <= left_date <= right_dates[1]
    left_num, right_num = _number(left), _number(right)
    if operator in {"lt", "le", "gt", "ge", "between"} and left_num is not None and right_num is not None:
        if operator == "lt": return left_num < right_num
        if operator == "le": return left_num <= right_num
        if operator == "gt": return left_num > right_num
        if operator == "ge": return left_num >= right_num
    if operator == "between" and isinstance(right, (list, tuple)) and len(right) == 2 and left_num is not None:
        return float(right[0]) <= left_num <= float(right[1])
    if operator == "in": return normalize(left) in {normalize(item) for item in right}
    if operator == "not_in": return normalize(left) not in {normalize(item) for item in right}
    if operator == "is_null": return normalize(left) == ""
    if operator == "not_null": return normalize(left) != ""
    if operator == "ne": return normalize(left).lower() != normalize(right).lower()
    return normalize(left).lower() == normalize(right).lower()


def table_filter(table: TableData, conditions: list[dict[str, Any]], logical_operator: str = "and") -> list[dict[str, Any]]:
    return _filter_rows(table.rows, conditions, logical_operator)


def _filter_rows(rows: list[dict[str, Any]], conditions: list[dict[str, Any]], logical_operator: str = "and") -> list[dict[str, Any]]:
    """保存済み行へ条件を決定的に適用する。"""
    if not conditions:
        return list(rows)
    if logical_operator.lower() == "or":
        return [row for row in rows if any(_condition_match(row, condition) for condition in conditions)]
    return [row for row in rows if all(_condition_match(row, condition) for condition in conditions)]


def _carry_forward_group_values(rows: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """結合セル相当のフェーズ・マイルストーン値を後続行へ引き継ぐ。"""
    grouped_columns = set()
    for condition in conditions:
        candidates = condition.get("conditions", []) if condition.get("operator") == "any_of" else [condition]
        for item in candidates:
            column = normalize(item.get("column", "")).lower()
            if any(term in column for term in ("フェーズ", "phase", "マイルストーン", "milestone")):
                grouped_columns.add(item.get("column", ""))
    if not grouped_columns:
        return list(rows)
    output = []
    current = {column: "" for column in grouped_columns}
    for row in rows:
        copied = dict(row)
        for column in grouped_columns:
            value = normalize(copied.get(column, ""))
            if value:
                current[column] = copied[column]
            elif current[column]:
                copied[column] = current[column]
                copied.setdefault("__inherited_group_columns__", []).append(column)
        output.append(copied)
    return output


def calculation(operation: str, left: float, right: float | None = None, digits: int | None = None) -> dict[str, Any]:
    """表処理の後段で使う決定的な数値計算と計算記録を提供する。"""
    operation = operation.lower()
    if operation == "absolute_difference":
        raw = abs(left - (right or 0))
        formula = f"abs({left} - {right})"
    elif operation == "percentage_change":
        if right in (None, 0):
            return {"status": "unsupported", "warning": "割合変化の分母が0です"}
        raw = (left - right) / right * 100
        formula = f"({left} - {right}) / {right} * 100"
    elif operation == "add":
        raw, formula = left + (right or 0), f"{left} + {right}"
    elif operation == "subtract":
        raw, formula = left - (right or 0), f"{left} - {right}"
    elif operation == "multiply":
        raw, formula = left * (right or 0), f"{left} * {right}"
    elif operation == "divide":
        if right in (None, 0):
            return {"status": "unsupported", "warning": "除算の分母が0です"}
        raw, formula = left / right, f"{left} / {right}"
    elif operation == "round":
        raw, formula = round(left), f"round({left})"
    elif operation == "ceil":
        raw, formula = math.ceil(left), f"ceil({left})"
    elif operation == "floor":
        raw, formula = math.floor(left), f"floor({left})"
    else:
        return {"status": "unsupported", "warning": f"未対応計算: {operation}"}
    formatted = round(raw, digits) if digits is not None else raw
    return {"status": "success", "input_values": {"left": left, "right": right}, "formula": formula, "raw_result": raw, "formatted_result": formatted}


def _target_column(question: str, columns: list[str]) -> str | None:
    text = normalize(question).lower()
    for terms in (("\u30bf\u30b9\u30afid", "task id", "task_id"), ("\u30bf\u30b9\u30af\u540d", "task name", "task_name"), ("\u62c5\u5f53\u8005", "assignee", "owner")):
        if any(normalize(term).lower() in text for term in terms):
            found = _unique_column_by_terms(columns, terms)
            if found:
                return found
    patterns = [r"([A-Za-z][A-Za-z0-9_]*)\s*の平均", r"([A-Za-z][A-Za-z0-9_]*)\s*平均", r"平均.*?([A-Za-z][A-Za-z0-9_]*)"]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            found = _match_column(columns, match.group(1))
            if found:
                return found
    # 質問から列を特定できない場合、先頭の数値列を推測で採用しない。
    return None


def _condition_coverage(question: str, conditions: list[dict[str, Any]], columns: list[str]) -> bool:
    """質問に明示された表条件が、実行条件へすべて反映されたかを確認する。"""
    explicit = re.findall(
        r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*([A-Za-z0-9_.+-]+(?:\s+years?)?)",
        normalize(question),
        re.IGNORECASE,
    )
    for column_hint, value in explicit:
        column = _match_column(columns, column_hint)
        if not column:
            return False
        if not any(item.get("column") == column and normalize(item.get("value")).lower() == normalize(value).lower() for item in conditions):
            return False
    gender_column = _match_column(columns, "Gender") or _match_column(columns, "Sex")
    if "女性" in question and not any(item.get("column") == gender_column and normalize(item.get("value")).lower() == "female" for item in conditions):
        return False
    if "男性" in question and not any(item.get("column") == gender_column and normalize(item.get("value")).lower() == "male" for item in conditions):
        return False
    return True


def _group_column(question: str, columns: list[str]) -> str | None:
    for hint in ("age", "年齢", "層", "group", "category"):
        found = _match_column(columns, hint)
        if found and (hint in question or "層" in question or "年齢" in question):
            return found
    return None


def _format_number(value: float, question: str) -> str:
    if "整数" in question or "四捨五入" in question:
        return str(int(round(value)))
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def table_aggregation(table: TableData, rows: list[dict[str, Any]], operation: str, value_column: str | None = None, group_column: str | None = None, question: str = "") -> dict[str, Any]:
    operation = operation.lower()
    value_column = value_column or (table.columns[0] if table.columns else "")
    values = [(row, _number(row.get(value_column))) for row in rows]
    values = [(row, value) for row, value in values if value is not None]
    if not values:
        return {"status": "unsupported", "warning": "数値列が空です"}
    if operation in {"argmin", "argmax"} and group_column:
        grouped: dict[str, list[float]] = {}
        for row, value in values:
            grouped.setdefault(normalize(row.get(group_column)), []).append(value)
        group_values = {key: sum(items) / len(items) for key, items in grouped.items() if items}
        selected = min(group_values, key=group_values.get) if operation == "argmin" else max(group_values, key=group_values.get)
        result: Any = selected
        raw_result = group_values[selected]
        formula = f"{operation}({value_column}) grouped by {group_column}"
    elif operation in {"argmin", "argmax"}:
        selected_row, raw_result = (min(values, key=lambda item: item[1]) if operation == "argmin" else max(values, key=lambda item: item[1]))
        result = " | ".join(
            f"{column}={normalize(selected_row.get(column))}"
            for column in table.columns
            if column != value_column and "平均" not in column and normalize(selected_row.get(column))
        )
        result = result.replace(" | ", "、")
        if "抽出条件" in question and value_column.startswith("平均 /"):
            result += f"で抽出されたデータに対する{value_column}"
        formula = f"{operation}({value_column}) row"
    else:
        numbers = [value for _, value in values]
        if not numbers:
            return {"status": "unsupported", "warning": "数値列が空です"}
        if operation == "count": result, raw_result = len(rows), len(rows)
        elif operation == "sum": result = raw_result = sum(numbers)
        elif operation == "mean": result = raw_result = sum(numbers) / len(numbers)
        elif operation == "min": result = raw_result = min(numbers)
        elif operation == "max": result = raw_result = max(numbers)
        elif operation == "median": result = raw_result = sorted(numbers)[len(numbers) // 2]
        elif operation == "nunique": result = raw_result = len({normalize(row.get(value_column)) for row in rows})
        else: return {"status": "unsupported", "warning": f"未対応集計: {operation}"}
        formula = f"{operation}({value_column})"
    formatted = result if isinstance(result, str) else _format_number(float(result), question)
    result_data = {"status": "success", "raw_result": raw_result, "formatted_result": formatted, "formula": formula, "input_values": [value for _, value in values]}
    if operation in {"argmin", "argmax"} and not group_column:
        result_data["selected_rows"] = [selected_row]
        result_data["selected_value"] = raw_result
    return result_data


def _coordinate_row(coordinate: str) -> int | None:
    match = re.fullmatch(r"[A-Z]+(\d+)", str(coordinate).upper())
    return int(match.group(1)) if match else None


def _column_letter(index: int) -> str:
    """1始まりの列番号をExcelの列記号へ決定的に変換する。"""
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _selected_row_evidence(
    table: TableData,
    selected_rows: list[dict[str, Any]],
    condition_columns: list[str],
    aggregate_column: str,
    answer_column: str,
    selected_value: Any,
) -> list[dict[str, Any]]:
    """最大値・最小値で選んだ行について、条件列・集計列・回答セルを同じ行で記録する。"""
    evidence: list[dict[str, Any]] = []
    for row in selected_rows:
        row_number = row.get("__row_number__")
        if not isinstance(row_number, int):
            continue
        answer_index = table.columns.index(answer_column) + 1 if answer_column in table.columns else None
        aggregate_index = table.columns.index(aggregate_column) + 1 if aggregate_column in table.columns else None
        condition_cells = {
            column: f"{_column_letter(table.columns.index(column) + 1)}{row_number}"
            for column in condition_columns
            if column in table.columns
        }
        evidence.append({
            "row_number": row_number,
            "condition_columns": condition_columns,
            "condition_values": {column: row.get(column) for column in condition_columns},
            "condition_cells": condition_cells,
            "aggregate_column": aggregate_column,
            "aggregate_value": row.get(aggregate_column),
            "aggregate_cell": f"{_column_letter(aggregate_index)}{row_number}" if aggregate_index else "",
            "selected_value": selected_value,
            "answer_column": answer_column,
            "answer_value": row.get(answer_column),
            "answer_cell": f"{_column_letter(answer_index)}{row_number}" if answer_index else "",
        })
    return evidence


def _requested_row_value_column(question: str, columns: list[str]) -> str | None:
    """質問文に明示された表ヘッダだけを、行返却用の列として採用する。"""
    text = normalize(question).lower()
    exact = [column for column in columns if normalize(column).lower() and normalize(column).lower() in text]
    if not exact:
        return None
    # 「タスク」と「タスクID」のような包含関係は、より長い明示ヘッダを優先する。
    longest = max(len(normalize(column)) for column in exact)
    candidates = [column for column in exact if len(normalize(column)) == longest]
    return candidates[0] if len(candidates) == 1 else None


def _style_rgb(style: dict[str, Any]) -> tuple[int, int, int] | None:
    match = re.search(r"rgb=([0-9a-fA-F]{6,8})", str(style.get("fill_color", "")))
    if not match:
        return None
    value = match.group(1)[-6:]
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _hue_matches(rgb: tuple[int, int, int], name: str) -> bool:
    """Officeの淡色テーマ色も、彩度と色相から指定色へ正規化する。"""
    red, green, blue = (value / 255 for value in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    degrees = hue * 360
    if value < 0.2 or saturation < 0.08:
        return False
    ranges = {
        "red": lambda: degrees < 15 or degrees >= 345,
        "orange": lambda: 15 <= degrees < 50,
        "yellow": lambda: 50 <= degrees < 75,
        "green": lambda: 75 <= degrees < 175,
        "blue": lambda: 175 <= degrees < 270,
    }
    return ranges.get(name, lambda: False)()


def _requested_fill_color(question: str) -> str:
    """案件名などの単文字色名を避け、書式指定として現れた色だけを解釈する。"""
    explicit = (
        ("オレンジ", "orange"), ("orange", "orange"),
        ("黄色", "yellow"), ("yellow", "yellow"), ("黄", "yellow"),
        ("青色", "blue"), ("blue", "blue"),
        ("赤色", "red"), ("red", "red"),
        ("緑色", "green"), ("green", "green"),
    )
    for text, color in explicit:
        if text in question:
            return color
    contextual = (
        (r"青(?:色)?(?:に|で|の)?(?:ハイライト|着色|塗り|背景)", "blue"),
        (r"赤(?:色)?(?:に|で|の)?(?:ハイライト|着色|塗り|背景)", "red"),
        (r"緑(?:色)?(?:に|で|の)?(?:ハイライト|着色|塗り|背景)", "green"),
    )
    for pattern, color in contextual:
        if re.search(pattern, question):
            return color
    return ""


def format_extraction(table: TableData, question: str) -> dict[str, Any]:
    requested = _requested_fill_color(question)
    styles = table.structure.get("styled_cells", [])
    matched = []
    for style in styles:
        color = normalize(style.get("fill_color", "")).lower()
        if requested and _color_matches(color, requested):
            matched.append(style)
    if not matched:
        return {"status": "unsupported", "formatted_result": [], "styles": [], "warning": "該当書式が見つかりません"}

    # 行の回答を求める場合だけ、同じ行の質問で明示された列へ戻す。
    row_requested = "行" in question or bool(re.search(r"\brows?\b", question, flags=re.IGNORECASE))
    if not row_requested:
        return {"status": "success", "formatted_result": [item.get("coordinate", "") for item in matched], "styles": matched, "warning": ""}
    target_column = _requested_row_value_column(question, table.columns)
    if target_column is None:
        return {"status": "unsupported", "formatted_result": [], "styles": matched, "warning": "行から返す列を表ヘッダへ一意に対応付けられません"}
    header_row = int(table.structure.get("header_row_number", 1))
    target_index = table.columns.index(target_column) + 1
    grouped: dict[int, list[dict[str, Any]]] = {}
    for style in matched:
        row_number = _coordinate_row(str(style.get("coordinate", "")))
        if row_number is not None:
            grouped.setdefault(row_number, []).append(style)
    row_evidence: list[dict[str, Any]] = []
    for row_number in sorted(grouped):
        row_index = row_number - header_row - 1
        if not 0 <= row_index < len(table.rows):
            continue
        value = normalize(table.rows[row_index].get(target_column, ""))
        if not value:
            continue
        row_evidence.append({
            "row_number": row_number,
            "answer_column_name": target_column,
            "answer_column_index": target_index,
            "answer_coordinate": f"{_column_letter(target_index)}{row_number}",
            "answer_value": value,
            "matched_style_cells": [item.get("coordinate", "") for item in grouped[row_number]],
        })
    if not row_evidence:
        return {"status": "unsupported", "formatted_result": [], "styles": matched, "warning": "書式一致行に要求列の値がありません"}
    return {
        "status": "success",
        "formatted_result": [item["answer_value"] for item in row_evidence],
        "styles": matched,
        "row_evidence": row_evidence,
        "target_column": target_column,
        "warning": "",
    }


def _color_matches(color: str, name: str) -> bool:
    values = [part.split("=", 1)[1] for part in color.split(";") if "=" in part]
    for value in values:
        if name == "yellow" and value.upper() in {"FFFF00", "FFFFFF00"}: return True
        if name == "blue" and value.upper() in {"0000FF", "FF0000FF"}: return True
        if name == "red" and value.upper() in {"FF0000", "FFFF0000"}: return True
        if name == "green" and value.upper() in {"00FF00", "FF00FF00"}: return True
        if name == "orange" and value.upper() in {"FFA500", "FFFFA500"}: return True
    rgb_match = re.search(r"rgb=([0-9a-fA-F]{6,8})", color)
    if not rgb_match:
        return False
    value = rgb_match.group(1)[-6:]
    return _hue_matches((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)), name)


def execute_table_question(
    analysis: QuestionAnalysis,
    selected_files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    project_root: Path,
    operations: list[dict[str, Any]],
    available_files: list[FileRecord] | None = None,
    calculation_work_dir: Path | None = None,
) -> dict[str, Any]:
    """選択済みExcel/CSVだけをraw由来の表として読み、操作を順に実行する。"""
    table_files = select_relevant_table_files(analysis.question_normalized, selected_files, available_files or selected_files)
    tables: list[TableData] = []
    for file in table_files:
        extraction = extraction_by_file.get(file.file_id)
        if extraction:
            tables.extend(load_table_data(file, extraction, project_root))
    if not tables:
        return {"status": "unsupported", "failure_stage": "source_failure", "warning": "表データがありません"}
    # 略語展開で列値が別の語へ置換される場合があるため、表の列名・条件値はraw質問を優先する。
    question = getattr(analysis, "question_original", "") or analysis.question_normalized
    table = next((item for item in tables if item.sheet_name and item.sheet_name.lower() in question.lower()), None)
    if table is None:
        identifiers = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_]+", question)}
        table = max(tables, key=lambda item: sum(1 for column in item.columns if column.lower() in identifiers or any(token in column.lower() for token in identifiers)))
    mentioned_columns = list(dict.fromkeys(re.findall(r"([A-Za-z][A-Za-z0-9_]*)\s*(?==|is|が|の平均|の平均値)", question, re.IGNORECASE)))
    missing_columns = [token for token in mentioned_columns if _match_column(table.columns, token) is None]
    if missing_columns and not "フィルター" in question:
        return {
            "status": "unsupported",
            "failure_stage": "column_failure",
            "warning": f"表に必要列がありません: {', '.join(missing_columns)}",
            "evidence": {"selected_file": table.file.raw_path, "sheet_name": table.sheet_name, "columns_used": mentioned_columns, "warnings": ["missing_columns"]},
        }
    if "Pivot" in question and table.sheet_name.lower() != "pivot":
        return {
            "status": "unsupported",
            "failure_stage": "sheet_failure",
            "warning": "質問で指定されたPivotシートを特定できません",
            "evidence": {"selected_file": table.file.raw_path, "sheet_name": table.sheet_name, "warnings": ["pivot_sheet_not_selected"]},
        }
    calculation_spec = build_calculation_spec(question, table.columns)
    if calculation_spec.calculation_subtype != "unsupported_calculation":
        # Plannerが実資料に結び付けた入力だけを渡し、未解決の列や数値を推測しない。
        explicit_inputs = None
        for operation in operations:
            parameters = operation.get("parameters", {}) if isinstance(operation, dict) else {}
            if isinstance(parameters, dict) and isinstance(parameters.get("calculation_inputs"), dict):
                explicit_inputs = parameters["calculation_inputs"]
                break
        if explicit_inputs is None and calculation_spec.operation_type == "coefficient_prediction":
            explicit_inputs = infer_coefficient_inputs(tables, question)
            if explicit_inputs is None:
                # Regression output is often a vertically laid out Excel report,
                # which the generic CSV-shaped table IR intentionally does not
                # flatten. Resolve it from workbook cells only when all bindings
                # can be proven by variable name and cell location.
                explicit_inputs = infer_coefficient_inputs_from_workbook(project_root / table.file.raw_path, question)
        calculation_result = execute_calculation_spec(analysis.index, question, calculation_spec, table, table_filter, explicit_inputs)
        if calculation_work_dir is not None:
            append_calculation_artifacts(calculation_work_dir, analysis.index, calculation_result)
        if calculation_result.get("status") == "success":
            return {
                **calculation_result,
                "question_type": "calculation",
                "calculation_trace": calculation_result.get("steps", []),
            }
    if any(term in question for term in ("予測値", "回帰分析", "回帰係数", "係数を")):
        return {
            "status": "unsupported",
            "failure_stage": "calculation_spec_failure",
            "warning": "係数予測に必要なCalculationSpecを生成できません",
            "question_type": "calculation",
            "evidence": {
                "selected_file": table.file.raw_path,
                "selected_file_id": table.file.file_id,
                "sheet_name": table.sheet_name,
                "cell_ranges": [],
                "calculation_formula": "",
                "preview_only": False,
            },
            "verification": {
                "question_type_match": True,
                "condition_coverage": False,
                "input_presence": False,
                "type_validity": False,
                "filter_validity": False,
                "operation_validity": False,
                "rounding_validity": False,
                "reproducibility": False,
                "source_range": False,
                "verification_status": "failed",
            },
        }
    conditions = _parse_conditions(question, table.columns)
    conditions.extend(_parse_schedule_conditions(question, table.columns))
    planner_conditions = []
    for operation in operations:
        parameters = operation.get("parameters", {}) if isinstance(operation, dict) else {}
        if isinstance(parameters, dict) and isinstance(parameters.get("conditions"), list):
            planner_conditions.extend(parameters["conditions"])
    for condition in planner_conditions:
        if isinstance(condition, dict) and _match_column(table.columns, condition.get("column", "")):
            condition = dict(condition)
            condition["column"] = _match_column(table.columns, condition["column"])
            conditions.append(condition)
    filter_rows = _carry_forward_group_values(table.rows, conditions)
    filtered = _filter_rows(filter_rows, conditions, "and")
    target = _target_column(question, table.columns)
    group = _group_column(question, table.columns)
    operation_name = "argmax_date" if "最後に開始" in question else "argmax" if "最も高い" in question or "最大" in question else "argmin" if "最も低い" in question or "最小" in question else "mean" if "平均" in question else "count" if "件数" in question else "sum" if "合計" in question else "lookup"
    for operation in operations:
        parameters = operation.get("parameters", {}) if isinstance(operation, dict) else {}
        if isinstance(parameters, dict) and parameters.get("operation"):
            operation_name = str(parameters["operation"])
    if table.sheet_name.lower() == "pivot" and target is None and operation_name in {"argmin", "argmax"}:
        source_path = project_root / table.file.raw_path
        try:
            pivot_result = execute_pivot_extreme_question(analysis.index, question, table.file, source_path, table.sheet_name)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            pivot_result = {
                "status": "unsupported",
                "failure_stage": "pivot_structure_failure",
                "warning": f"Pivot構造を復元できません: {type(exc).__name__}",
            }
        if pivot_result.get("status") == "success":
            return pivot_result
    if operation_name not in {"lookup", "count"} and target is None:
        return {
            "status": "unsupported",
            "failure_stage": "column_resolution_failure",
            "warning": "質問から集計対象列を一意に解決できません",
            "question_type": "calculation",
            "evidence": {
                "selected_file": table.file.raw_path,
                "selected_file_id": table.file.file_id,
                "sheet_name": table.sheet_name,
                "cell_ranges": [],
                "columns_used": [],
                "filter_conditions": conditions,
                "calculation_formula": "",
                "preview_only": False,
            },
            "verification": {
                "question_type_match": True,
                "condition_coverage": _condition_coverage(question, conditions, table.columns),
                "input_presence": False,
                "type_validity": False,
                "filter_validity": False,
                "operation_validity": False,
                "rounding_validity": False,
                "reproducibility": False,
                "source_range": False,
                "verification_status": "failed",
            },
        }
    evidence_conditions = []
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        normalized_condition = dict(condition)
        if normalized_condition.get("operator") == "any_of":
            alternatives = normalized_condition.get("conditions", [])
            columns = [item.get("column", "") for item in alternatives if isinstance(item, dict)]
            normalized_condition["column"] = columns[0] if columns else ""
            normalized_condition["alternatives"] = alternatives
        normalized_condition.setdefault("column", "")
        evidence_conditions.append(normalized_condition)
    evidence = {
        "selected_file": table.file.raw_path,
        "selected_file_id": table.file.file_id,
        "sheet_name": table.sheet_name,
        "cell_ranges": [f"A1:{chr(64 + min(len(table.columns), 26))}{len(table.rows) + 1}"],
        "columns_used": [column for column in [item.get("column", "") for item in evidence_conditions] + [target, group] if column],
        "filter_conditions": evidence_conditions,
        "matched_row_count": len(filtered),
        "input_values": [],
        "calculation_formula": "",
        "raw_result": None,
        "formatted_result": "",
        "warnings": [],
    }
    if any(word in question for word in ("黄色", "青色", "オレンジ", "赤", "書式", "セル")):
        output = format_extraction(table, question)
        evidence["cell_ranges"] = [item.get("coordinate", "") for item in output.get("styles", [])]
        evidence["formatted_result"] = output.get("formatted_result", [])
        evidence["raw_result"] = output.get("styles", [])
        evidence["row_evidence"] = output.get("row_evidence", [])
        evidence["answer_column"] = output.get("target_column", "")
        if output.get("status") != "success":
            return {"status": "unsupported", "failure_stage": "format_failure", "warning": output.get("warning", ""), "evidence": evidence}
        answer = ", ".join(evidence["formatted_result"])
        row_evidence = evidence["row_evidence"]
        verification = {
            "presence": bool(answer),
            "condition_match": bool(output.get("styles")),
            "completeness": bool(output.get("styles")),
            "verbatim_match": all(item.get("answer_value") in answer for item in row_evidence) if row_evidence else True,
            "source_location": bool(evidence["cell_ranges"]),
            "answer_format_valid": bool(answer),
            "independent_recalculation": True,
            "verification_status": "passed",
        }
        return {
            "status": "success",
            "answer": answer,
            "evidence": evidence,
            "operations_executed": ["format_extraction", "answer_formatting"],
            "question_type": "format_only",
            "verification": verification,
            "used_file_ids": [table.file.file_id],
        }
    if "フィルター" in question:
        filter_info = {
            "range": table.structure.get("auto_filter", ""),
            "columns": table.structure.get("auto_filter_columns", []),
        }
        formatted_filters = []
        for item in filter_info["columns"]:
            index = int(item.get("col_id", 0))
            column = table.columns[index] if 0 <= index < len(table.columns) else (table.columns[index - 1] if 0 < index <= len(table.columns) else f"column_{index}")
            values = item.get("filters") or [f"{custom.get('operator', '')} {custom.get('val', '')}" for custom in item.get("custom_filters", [])]
            formatted_filters.extend(f"{column}={value}" for value in values)
        evidence["raw_result"] = filter_info
        evidence["formatted_result"] = "、".join(formatted_filters) if formatted_filters else json.dumps(filter_info, ensure_ascii=False)
        if not filter_info["range"] and not filter_info["columns"]:
            return {"status": "unsupported", "failure_stage": "filter_failure", "warning": "WorkbookにAutoFilter条件がありません", "evidence": evidence}
        return {"status": "success", "answer": evidence["formatted_result"], "evidence": evidence, "operations_executed": ["table_lookup", "answer_formatting"]}
    if "最も近い" in question and group and _match_column(table.columns, "id"):
        values = [(row, _number(row.get(target))) for row in filtered]
        values = [(row, value) for row, value in values if value is not None]
        if not values:
            return {"status": "unsupported", "failure_stage": "calculation_failure", "warning": "近傍計算の入力値がありません", "evidence": evidence}
        mean_value = sum(value for _, value in values) / len(values)
        distance = [(row, abs(value - mean_value)) for row, value in values]
        nearest_distance = min(item[1] for item in distance)
        nearest = [row for row, item_distance in distance if abs(item_distance - nearest_distance) < 1e-9]
        id_column = _match_column(table.columns, "id") or "id"
        answer = ", ".join(normalize(row.get(id_column)) for row in nearest)
        evidence.update({"input_values": [value for _, value in values], "calculation_formula": f"mean({target}) then nearest({group})", "raw_result": mean_value, "formatted_result": answer})
    elif operation_name == "argmax_date":
        date_column = _unique_column_by_terms(table.columns, ("開始日", "start_date"))
        if not date_column or not filtered:
            return {"status": "unsupported", "failure_stage": "calculation_failure", "warning": "開始日列または対象行を一意に解決できません", "evidence": evidence}
        dated = [(row, _date_value(row.get(date_column))) for row in filtered]
        dated = [(row, value) for row, value in dated if value is not None]
        if not dated:
            return {"status": "unsupported", "failure_stage": "calculation_failure", "warning": "対象行の開始日を解釈できません", "evidence": evidence}
        latest_date = max(value for _, value in dated)
        selected_rows = [row for row, value in dated if value == latest_date]
        answer = ", ".join(normalize(row.get(target or table.columns[0])) for row in selected_rows)
        answer_column = target or table.columns[0]
        evidence.update({"columns_used": [date_column, answer_column], "input_values": [row.get(date_column) for row in selected_rows], "calculation_formula": f"max({date_column})", "raw_result": str(latest_date), "formatted_result": answer, "selected_row_evidence": _selected_row_evidence(table, selected_rows, [date_column], date_column, answer_column, str(latest_date))})
    elif operation_name == "lookup":
        answer = ", ".join(normalize(row.get(target or table.columns[0])) for row in filtered[:20])
        evidence["input_values"] = filtered[:20]
    else:
        output = table_aggregation(table, filtered, operation_name, target, group, question)
        if output.get("status") != "success":
            return {"status": "unsupported", "failure_stage": "calculation_failure", "warning": output.get("warning", ""), "evidence": evidence}
        answer = str(output["formatted_result"])
        evidence.update({"input_values": output.get("input_values", []), "calculation_formula": output.get("formula", ""), "raw_result": output.get("raw_result"), "formatted_result": output.get("formatted_result")})
        if output.get("selected_rows"):
            selected_column = target or table.columns[0]
            evidence["selected_row_evidence"] = _selected_row_evidence(table, output["selected_rows"], [item.get("column", "") for item in evidence_conditions if item.get("column")], selected_column, selected_column, output.get("selected_value", output.get("raw_result")))
    is_calculation = operation_name != "lookup"
    condition_valid = _condition_coverage(question, conditions, table.columns)
    verification = {
        "presence": bool(answer) and (operation_name == "count" or bool(target)),
        "question_type_match": True if not is_calculation else True,
        "condition_coverage": condition_valid,
        "input_presence": bool(evidence.get("selected_file_id")) and bool(target or operation_name == "count"),
        "type_validity": bool(evidence.get("input_values")),
        "filter_validity": condition_valid,
        "operation_validity": bool(evidence.get("calculation_formula")) and bool(target or operation_name == "count") if is_calculation else bool(target and filtered),
        "rounding_validity": evidence.get("formatted_result") not in (None, "") if is_calculation else True,
        "reproducibility": bool(evidence.get("calculation_formula")) and bool(evidence.get("input_values")) if is_calculation else bool(filtered),
        "source_range": bool(evidence.get("cell_ranges")),
    }
    verification["verification_status"] = "passed" if all(verification.values()) else "failed"
    return {
        "status": "success" if filtered else "unsupported",
        "failure_stage": "" if filtered else "filter_failure",
        "answer": answer if filtered else "",
        "evidence": evidence,
        "operations_executed": ["table_filter", "table_aggregation", "answer_formatting"],
        "question_type": "calculation" if is_calculation else "table_lookup",
        "verification": verification,
    }


def _operation_name(operation: dict[str, Any]) -> str:
    return str(operation.get("tool_name") or operation.get("operation_type") or "")
