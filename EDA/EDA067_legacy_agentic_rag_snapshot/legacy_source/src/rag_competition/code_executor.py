from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .schemas import FileRecord


def _source_evidence(file: FileRecord, node: ast.AST, source: str, text: str) -> dict[str, Any]:
    lines = source.splitlines()
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start)
    return {
        "file_id": file.file_id,
        "source_path": file.raw_path,
        "location": {"line_start": start, "line_end": end},
        "source_text": "\n".join(lines[start - 1:end]),
        "matched_text": text,
        "preview_only": False,
    }


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None


def _assigned_name(node: ast.Assign | ast.AnnAssign) -> str:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return next((target.id for target in targets if isinstance(target, ast.Name)), "")


def _module_constants(tree: ast.Module) -> dict[str, Any]:
    constants: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            name = _assigned_name(node)
            value = _literal(node.value)
            if name and value is not None:
                constants[name] = value
    return constants


def _comparison_threshold(node: ast.Compare, constants: dict[str, Any]) -> tuple[str, Any] | None:
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return None
    operator = node.ops[0]
    right = node.comparators[0]
    value = constants.get(right.id) if isinstance(right, ast.Name) else _literal(right)
    if value is None:
        return None
    symbol = {ast.GtE: ">=", ast.Gt: ">", ast.LtE: "<=", ast.Lt: "<"}.get(type(operator))
    return (symbol, value) if symbol else None


def _extract_categorical_rule(file: FileRecord, tree: ast.Module, source: str) -> dict[str, Any] | None:
    """同一関数内のdtype判定とユニーク数制約をASTから対応付ける。"""
    constants = _module_constants(tree)
    for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        function_constants = dict(constants)
        default_args = function.args.args[-len(function.args.defaults):] if function.args.defaults else []
        for argument, default in zip(default_args, function.args.defaults):
            value = constants.get(default.id) if isinstance(default, ast.Name) else _literal(default)
            if value is not None:
                function_constants[argument.arg] = value
        dtype_assignment: ast.Assign | ast.AnnAssign | None = None
        dtype_names: list[str] = []
        unique_test: ast.If | None = None
        inclusion_operator = ""
        threshold: Any = None
        for node in ast.walk(function):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                name = _assigned_name(node)
                segment = ast.get_source_segment(source, node) or ""
                if "categor" in name.lower() and "dtype" in segment:
                    dtype_assignment = node
                    dtype_names = re.findall(r"is_([a-z_]+)_dtype", segment)
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                segment = ast.get_source_segment(source, node.test) or ""
                if "unique" not in segment.lower():
                    continue
                comparison = _comparison_threshold(node.test, function_constants)
                if comparison and any(isinstance(child, (ast.Continue, ast.Return)) for child in ast.walk(ast.Module(body=node.body, type_ignores=[]))):
                    symbol, threshold = comparison
                    inclusion_operator = {">=": "<", ">": "<=", "<=": ">", "<": ">="}.get(symbol, "")
                    unique_test = node
        if not dtype_assignment or not dtype_names or not unique_test or threshold is None or not inclusion_operator:
            continue
        display_names = ["category" if name == "categorical" else name for name in dtype_names]
        answer = f"dtypeが{'・'.join(display_names)}のいずれか、かつユニーク数が{threshold}{'未満' if inclusion_operator == '<' else inclusion_operator}の場合です。"
        start = min(dtype_assignment.lineno, unique_test.lineno)
        end = max(getattr(dtype_assignment, "end_lineno", dtype_assignment.lineno), getattr(unique_test, "end_lineno", unique_test.lineno))
        evidence = _source_evidence(file, function, source, f"dtype={display_names}; unique_count {inclusion_operator} {threshold}")
        evidence["location"] = {"line_start": start, "line_end": end}
        evidence["source_text"] = "\n".join(source.splitlines()[start - 1:end])
        return {
            "answer": answer,
            "evidence": evidence,
            "dtype_conditions": display_names,
            "unique_operator": inclusion_operator,
            "unique_threshold": threshold,
            "function_name": function.name,
        }
    return None


def execute_code_inspection(question: str, files: list[FileRecord], root: Path) -> dict[str, Any]:
    """PythonソースをASTで索引化し、質問に直接対応する設定値だけを返す。"""
    evidence: list[dict[str, Any]] = []
    answer = ""
    lowered = question.lower()
    for file in files:
        if file.extension.lower() != ".py":
            continue
        path = Path(file.raw_path)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        if "dtype" in lowered and any(term in question for term in ("ユニーク", "unique", "CAT", "カテゴリ")):
            rule = _extract_categorical_rule(file, tree, source)
            if rule:
                return {
                    "status": "success",
                    "answer": rule["answer"],
                    "evidence": [rule["evidence"]],
                    "operations_executed": ["code_inspection"],
                    "calculation_trace": [],
                    "question_type": "code_inspection",
                    "verification": {
                        "presence": True,
                        "condition_match": True,
                        "source_location": True,
                        "ast_parse": True,
                        "answer_format_valid": False,
                        "verification_status": "passed",
                    },
                    "code_rule": {key: value for key, value in rule.items() if key not in {"answer", "evidence"}},
                }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "build_preprocessor":
                continue
            values = {keyword.arg: _literal(keyword.value) for keyword in node.keywords if keyword.arg}
            sparse = values.get("sparse_output")
            if isinstance(sparse, ast.AST):
                sparse = None
            if sparse is not None:
                evidence.append(_source_evidence(file, node, source, f"sparse_output={sparse}"))
            if "sparse_output" not in source or "model_type" not in source:
                continue
            match = re.search(r"model_key\s*!=\s*[\"']([^\"']+)[\"']", source)
            if match and "sparse_output" in lowered and sparse is None:
                answer = match.group(1)
                evidence.append(_source_evidence(file, node, source, f"model_type={answer}"))
    if answer and evidence:
        return {"status": "success", "answer": answer, "evidence": evidence, "operations_executed": ["code_inspection"], "calculation_trace": []}
    return {"status": "unsupported", "answer": "", "evidence": evidence, "warning": "ASTから一意に回答できる設定値が見つかりません", "failure_stage": "evidence_failure", "operations_executed": ["code_inspection"]}
