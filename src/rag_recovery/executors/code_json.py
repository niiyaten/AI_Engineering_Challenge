from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any

from ..models import Evidence, ExecutionResult, QueryPlan, Question
from ..normalize import nfkc, norm
from ..store import DocumentStore
from .base import Executor
from .utils import format_number, parse_number


@dataclass
class CodeJsonAnalysisExecutor(Executor):
    name: str = "code_json"

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        q = nfkc(question.text)
        project = plan.project_hints[0] if plan.project_hints else ""
        selected = question.selected_sources
        records = store.find(project_hint=project, extensions={".json", ".py", ".ipynb", ".csv"}, selected_sources=selected, limit=20)
        if not records:
            return ExecutionResult.abstain("コード・JSON資料を特定できない")
        if "selected_columns" in q or "生成された特徴量" in q or "ENG-FT" in q:
            return self._selected_columns(q, records, store)
        if "max_depth" in q or "最良モデル" in q or "F1" in q:
            return self._best_experiment(q, records, store)
        if "関数" in q or ".py" in q:
            return self._python_symbol_lookup(q, records)
        return ExecutionResult.abstain("コード・JSON操作を確定できない")

    def _selected_columns(self, q, records, store):
        json_records = [r for r in records if r.extension == ".json"]
        code_records = [r for r in records if r.extension == ".py"]
        for rec in json_records:
            try:
                data = json.loads(rec.path.read_text(encoding="utf-8"))
            except Exception:
                continue
            selected = self._find_key(data, "selected_columns")
            if not isinstance(selected, list):
                continue
            convention = ""
            for code in code_records:
                text = code.path.read_text(encoding="utf-8", errors="replace")
                if "__x__" in text:
                    convention = "__x__"
                    break
            if "ENG-FT" in q or "生成された" in q or "交互作用特徴量" in q:
                engineered = [x for x in selected if isinstance(x, str) and ((convention and convention in x) or (not convention and "__" in x))]
                wants_names = any(key in q for key in ("列名", "すべて答", "すべて挙げ", "特徴量をすべて"))
                answer = "、".join(engineered) if wants_names else str(len(engineered))
                method = "json_code_generated_feature_names" if wants_names else "json_code_generated_feature_count"
                return ExecutionResult(True, answer, .96, method, [Evidence(rec.relative_path, "selected_columns", str(selected)), *([Evidence(code.relative_path, "naming_rule", convention) for code in code_records[:1]] if convention else [])], diagnostics={"engineered": engineered})
            return ExecutionResult(True, "、".join(map(str, selected)), .94, "json_path_extract", [Evidence(rec.relative_path, "selected_columns", str(selected))])
        return ExecutionResult.abstain("selected_columnsを配列として取得できない")

    def _best_experiment(self, q, records, store):
        rows = []
        for rec in records:
            if rec.extension == ".json":
                try:
                    data = json.loads(rec.path.read_text(encoding="utf-8"))
                    rows.extend(self._flatten_json_records(data, rec.relative_path))
                except Exception:
                    continue
            elif rec.extension == ".csv":
                try:
                    df = store.read_csv(rec)
                    for _, row in df.iterrows():
                        rows.append((rec.relative_path, row.to_dict()))
                except Exception:
                    continue
        score_key = next((key for key in ("f1", "f1_score", "valid_f1", "score") if any(key in {norm(k) for k in row} for _, row in rows)), None)
        if not score_key:
            return ExecutionResult.abstain("実験スコア列を特定できない")
        scored = []
        for source, row in rows:
            mapping = {norm(k): (k, v) for k, v in row.items()}
            if score_key in mapping:
                value = parse_number(mapping[score_key][1])
                if value is not None:
                    scored.append((value, source, row))
        if not scored:
            return ExecutionResult.abstain("数値スコアを取得できない")
        best = max(scored, key=lambda x: x[0])
        if "max_depth" in q:
            for key, value in best[2].items():
                if norm(key) == norm("max_depth"):
                    return ExecutionResult(True, str(value), .96, "best_experiment_parameter_lookup", [Evidence(best[1], "best-row", str(best[2]), best[0])])
        return ExecutionResult(True, format_number(best[0], q), .94, "best_experiment_score", [Evidence(best[1], "best-row", str(best[2]), best[0])])

    def _python_symbol_lookup(self, q, records):
        names = re.findall(r"`([^`]+)`|\b([A-Za-z_][A-Za-z0-9_]*)\b", q)
        targets = [a or b for a, b in names if (a or b) not in {"py", "Python"}]
        for rec in records:
            if rec.extension != ".py":
                continue
            text = rec.path.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and any(norm(node.name) == norm(t) for t in targets):
                    segment = ast.get_source_segment(text, node) or node.name
                    return ExecutionResult(True, segment, .95, "python_ast_symbol_extract", [Evidence(rec.relative_path, f"line:{node.lineno}", segment[:500])])
        return ExecutionResult.abstain("対象Pythonシンボルを特定できない")

    def _find_key(self, obj: Any, key: str):
        if isinstance(obj, dict):
            for k, value in obj.items():
                if norm(k) == norm(key):
                    return value
                found = self._find_key(value, key)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for value in obj:
                found = self._find_key(value, key)
                if found is not None:
                    return found
        return None

    def _flatten_json_records(self, obj: Any, source: str):
        out = []
        if isinstance(obj, list):
            for value in obj:
                if isinstance(value, dict):
                    out.append((source, value))
                out.extend(self._flatten_json_records(value, source))
        elif isinstance(obj, dict):
            if any(not isinstance(v, (dict, list)) for v in obj.values()):
                out.append((source, obj))
            for value in obj.values():
                out.extend(self._flatten_json_records(value, source))
        return out
