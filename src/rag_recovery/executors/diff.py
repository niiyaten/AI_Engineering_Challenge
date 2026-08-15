from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any

from ..models import Evidence, ExecutionResult, QueryPlan, Question
from ..normalize import nfkc, norm
from ..store import DocumentStore
from .base import Executor
from .table import _find_col, _header_map

RELEVANT_TERMS = ("担当", "責任", "期限", "開始", "終了", "工数", "タスク", "成果物", "スコープ", "対象", "役割", "体制", "リスク", "レビュー", "会議", "契約", "支払", "モデル", "評価", "データ", "計画")
STATUS_VALUES = {"未着手", "着手中", "進行中", "完了", "対応中", "済"}


@dataclass
class DocumentDiffExecutor(Executor):
    name: str = "diff"

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        pair = self._resolve_pair(question, plan, store)
        if not pair:
            return ExecutionResult.abstain("比較対象2ファイルを一意に特定できない")
        old, new = pair
        if old.extension != new.extension:
            return ExecutionResult.abstain("異なる形式間の差分は未対応", diagnostics={"old": old.relative_path, "new": new.relative_path})
        if old.extension in {".xlsx", ".xlsm"}:
            changes = self._xlsx_diff(old, new, store)
        elif old.extension in {".pptx", ".docx", ".pdf", ".md", ".txt", ".ipynb", ".py", ".json"}:
            changes = self._text_diff(old, new, store)
        else:
            changes = []
        changes = self._filter_changes(changes, nfkc(question.text))
        if not changes:
            return ExecutionResult.abstain("案件遂行に関連する実質差分を検出できない", diagnostics={"old": old.relative_path, "new": new.relative_path})
        answer = "；".join(change["summary"] for change in changes[:12])
        evidence = [Evidence(old.relative_path, change.get("old_locator", ""), change.get("old", "")) for change in changes[:12]]
        evidence += [Evidence(new.relative_path, change.get("new_locator", ""), change.get("new", "")) for change in changes[:12]]
        confidence = .95 if len(changes) <= 5 else .87
        return ExecutionResult(True, answer, confidence, f"{old.extension[1:]}_semantic_diff", evidence, diagnostics={"change_count": len(changes), "old": old.relative_path, "new": new.relative_path})

    def _resolve_pair(self, question, plan, store):
        selected = [x for x in question.selected_sources if x.strip()]
        exact = []
        for source in selected:
            rec = store.by_relative.get(norm(source))
            if rec is None:
                rec = next((r for r in store.records if norm(source).endswith(norm(r.relative_path)) or norm(r.relative_path).endswith(norm(source))), None)
            if rec is not None and rec not in exact:
                exact.append(rec)
        if len(exact) == 2 and exact[0].extension == exact[1].extension and exact[0].project == exact[1].project:
            a, b = exact
            def order_key(rec):
                version_num = int(re.sub(r"\D", "", rec.version) or 0)
                old_rank = 0 if rec.version in {"old", "draft"} else 1
                return (old_rank, version_num, rec.relative_path)
            return tuple(sorted((a, b), key=order_key))
        records = store.find(project_hint=plan.project_hints[0] if plan.project_hints else "", extensions={".xlsx", ".xlsm", ".pptx", ".docx", ".pdf", ".md", ".txt", ".ipynb", ".py", ".json"}, selected_sources=selected, limit=20)
        if plan.filename_hints:
            explicit = []
            for hint in plan.filename_hints:
                candidates = store.find(project_hint=plan.project_hints[0] if plan.project_hints else "", filename_hint=hint, extensions={".xlsx", ".xlsm", ".pptx", ".docx", ".pdf", ".md", ".txt", ".ipynb", ".py", ".json"}, selected_sources=selected, limit=4)
                if candidates:
                    explicit.append(candidates[0])
            records = list(dict.fromkeys(explicit + records))
        if len(records) < 2:
            return None
        # Prefer same stem/role/project and a clear old/new or version ordering.
        scored = []
        for a in records:
            for b in records:
                if a == b or a.extension != b.extension or a.project != b.project:
                    continue
                score = 0
                if norm(a.stem) == norm(b.stem): score += 10
                if a.role == b.role: score += 8
                if a.version != b.version: score += 12
                if a.version in {"old", "draft"}: score += 8
                if b.version == "current": score += 8
                if "r1" in a.version and "r2" in b.version: score += 12
                if "v" in a.version and "v" in b.version:
                    try:
                        if int(re.sub(r"\D", "", a.version)) < int(re.sub(r"\D", "", b.version)): score += 10
                    except ValueError: pass
                scored.append((score, a, b))
        if not scored:
            return None
        scored.sort(key=lambda x: (-x[0], x[1].relative_path, x[2].relative_path))
        if scored[0][0] <= 0 or (len(scored) > 1 and scored[0][0] == scored[1][0] and {scored[0][1], scored[0][2]} != {scored[1][1], scored[1][2]}):
            return None
        return scored[0][1], scored[0][2]

    def _xlsx_diff(self, old, new, store):
        wb_old = store.load_workbook(old, data_only=True)
        wb_new = store.load_workbook(new, data_only=True)
        changes = []
        common_sheets = [name for name in wb_old.sheetnames if name in wb_new.sheetnames]
        for sheet in common_sheets:
            a, b = wb_old[sheet], wb_new[sheet]
            hm_a, hm_b = _header_map(a), _header_map(b)
            if hm_a and hm_b:
                hrow_a, map_a = hm_a; hrow_b, map_b = hm_b
                key_a = _find_col(map_a, ["Task ID", "タスクID", "Action ID", "アクションID", "Milestone ID", "マイルストーンID", "ID", "No.", "No"])
                key_b = _find_col(map_b, ["Task ID", "タスクID", "Action ID", "アクションID", "Milestone ID", "マイルストーンID", "ID", "No.", "No"])
                common_headers = [(header_a, col_a, map_b[header_a]) for header_a, col_a in map_a.items() if header_a in map_b]
                if key_a and key_b and common_headers:
                    rows_a = {str(a.cell(r, key_a).value): r for r in range(hrow_a + 1, a.max_row + 1) if a.cell(r, key_a).value not in (None, "")}
                    rows_b = {str(b.cell(r, key_b).value): r for r in range(hrow_b + 1, b.max_row + 1) if b.cell(r, key_b).value not in (None, "")}
                    for key in sorted(set(rows_a) & set(rows_b)):
                        for header, col_a, col_b in common_headers:
                            va, vb = a.cell(rows_a[key], col_a).value, b.cell(rows_b[key], col_b).value
                            if self._equal(va, vb): continue
                            changes.append({"summary": f"{key}の{a.cell(hrow_a, col_a).value}が「{va}」から「{vb}」に変更された。", "old": f"{key}: {va}", "new": f"{key}: {vb}", "old_locator": f"{sheet}!{a.cell(rows_a[key], col_a).coordinate}", "new_locator": f"{sheet}!{b.cell(rows_b[key], col_b).coordinate}", "field": str(a.cell(hrow_a, col_a).value), "old_value": va, "new_value": vb})
                    continue
            # Fallback by coordinates.
            max_row, max_col = max(a.max_row, b.max_row), max(a.max_column, b.max_column)
            for r in range(1, max_row + 1):
                for c in range(1, max_col + 1):
                    va, vb = a.cell(r, c).value, b.cell(r, c).value
                    if not self._equal(va, vb):
                        changes.append({"summary": f"{sheet}!{a.cell(r,c).coordinate}が「{va}」から「{vb}」に変更された。", "old": str(va), "new": str(vb), "old_locator": f"{sheet}!{a.cell(r,c).coordinate}", "new_locator": f"{sheet}!{b.cell(r,c).coordinate}", "field": "cell", "old_value": va, "new_value": vb})
        return changes

    def _text_diff(self, old, new, store):
        old_units = store.extract_text_units(old)
        new_units = store.extract_text_units(new)
        old_lines = [(u.locator, line.strip()) for u in old_units for line in u.text.splitlines() if line.strip()]
        new_lines = [(u.locator, line.strip()) for u in new_units for line in u.text.splitlines() if line.strip()]
        matcher = difflib.SequenceMatcher(a=[norm(x[1]) for x in old_lines], b=[norm(x[1]) for x in new_lines], autojunk=False)
        changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal": continue
            before = " / ".join(x[1] for x in old_lines[i1:i2])
            after = " / ".join(x[1] for x in new_lines[j1:j2])
            if tag == "replace": summary = f"「{before}」から「{after}」に変更された。"
            elif tag == "delete": summary = f"「{before}」が削除された。"
            else: summary = f"「{after}」が追加された。"
            changes.append({"summary": summary, "old": before, "new": after, "old_locator": old_lines[i1][0] if i1 < len(old_lines) else "", "new_locator": new_lines[j1][0] if j1 < len(new_lines) else "", "field": "text", "old_value": before, "new_value": after})
        return changes

    def _filter_changes(self, changes, q):
        out = []
        ignore_status = "未着手から完了への変更を除" in q
        for change in changes:
            oldv, newv = str(change.get("old_value", "")), str(change.get("new_value", ""))
            if ignore_status and oldv in STATUS_VALUES and newv in STATUS_VALUES:
                continue
            text = f"{change.get('field','')} {oldv} {newv} {change.get('summary','')}"
            if "案件遂行" in q and not any(term in text for term in RELEVANT_TERMS):
                continue
            if norm(oldv) == norm(newv):
                continue
            out.append(change)
        return out

    @staticmethod
    def _equal(a: Any, b: Any) -> bool:
        if a is None and b in (None, ""): return True
        if b is None and a in (None, ""): return True
        return norm(a) == norm(b)
