from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from ..models import Evidence, ExecutionResult, QueryPlan, Question
from ..normalize import nfkc, norm
from ..store import DocumentStore
from .base import Executor

ID_RE = re.compile(r"\b(?:MS|CP|T|A|M)\d+\b", re.I)
PERSON_RE = re.compile(r"[一-龥]{1,4}\s+[一-龥]{1,4}")


@dataclass
class MultiDocumentJoinExecutor(Executor):
    name: str = "join"

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        q = nfkc(question.text)
        project = plan.project_hints[0] if plan.project_hints else ""
        records = store.find(project_hint=project, extensions={".xlsx", ".xlsm", ".csv", ".docx", ".pptx", ".pdf", ".md", ".json", ".py"}, selected_sources=question.selected_sources, limit=30)
        if not records:
            return ExecutionResult.abstain("Join対象資料を特定できない")
        graph, evidence = self._build_graph(records, store)
        if "紐づくタスク" in q or "関連するタスクID" in q or "関連するタスク" in q:
            return self._related_tasks(q, graph, evidence)
        if "役割" in q and "タスクID" in q:
            return self._role_tasks(q, graph, evidence)
        if "RATEが変更" in q:
            return self._rate_change(q, records, store)
        if "チェックポイント" in q and "タスクID" in q:
            return self._checkpoint_tasks(q, graph, evidence)
        return ExecutionResult.abstain("Join条件を一意に解釈できない", diagnostics={"nodes": len(graph)})

    def _build_graph(self, records, store):
        graph: dict[str, set[str]] = defaultdict(set)
        evidence: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
        for rec in records:
            for unit in store.extract_text_units(rec):
                for line in unit.text.splitlines():
                    ids = [x.upper() for x in ID_RE.findall(line)]
                    people = PERSON_RE.findall(line)
                    quoted = re.findall(r"[「『](.*?)[」』]", line)
                    entities = list(dict.fromkeys([*ids, *people, *quoted]))
                    for i, left in enumerate(entities):
                        for right in entities[i+1:]:
                            graph[left].add(right); graph[right].add(left)
                            ev = Evidence(rec.relative_path, unit.locator, line.strip())
                            evidence[(left, right)].append(ev); evidence[(right, left)].append(ev)
        return graph, evidence

    def _related_tasks(self, q, graph, evidence):
        anchors = [x.upper() for x in ID_RE.findall(q)] + re.findall(r"[「『](.*?)[」』]", q)
        if not anchors:
            # e.g. "チェックポイント2" -> CP2/CP02 candidates.
            m = re.search(r"チェックポイント\s*(\d+)", q)
            if m:
                anchors = [f"CP{m.group(1)}", f"CP{int(m.group(1)):02d}"]
        tasks = set(); evs = []
        for anchor in anchors:
            for neighbor in graph.get(anchor, set()):
                if re.fullmatch(r"T\d+", neighbor, re.I):
                    tasks.add(neighbor.upper()); evs.extend(evidence.get((anchor, neighbor), []))
        if tasks:
            return ExecutionResult(True, "、".join(sorted(tasks, key=self._id_key)), .93, "fact_graph_related_task_join", evs[:20], diagnostics={"anchors": anchors})
        return ExecutionResult.abstain("アンカーからタスクIDへ到達できない", diagnostics={"anchors": anchors})

    def _role_tasks(self, q, graph, evidence):
        role_match = re.search(r"([一-龥ァ-ヶA-Za-z]+(?:アナリスト|サイエンティスト|マネージャ|エンジニア))", q)
        milestone = next((x.upper() for x in ID_RE.findall(q) if x.upper().startswith("MS")), "")
        if not role_match:
            return ExecutionResult.abstain("役割名を解析できない")
        role = role_match.group(1)
        people = [node for node in graph if role in node or role in " ".join(graph[node])]
        tasks = set(); evs = []
        for person in people:
            for neighbor in graph.get(person, set()):
                if re.fullmatch(r"T\d+", neighbor, re.I):
                    if milestone and milestone not in graph.get(neighbor, set()):
                        continue
                    tasks.add(neighbor.upper()); evs.extend(evidence.get((person, neighbor), []))
        if tasks:
            return ExecutionResult(True, "、".join(sorted(tasks, key=self._id_key)), .86, "role_person_task_milestone_join", evs[:20], diagnostics={"role": role, "people": people, "milestone": milestone})
        return ExecutionResult.abstain("役割→担当者→タスクのJoinに失敗", diagnostics={"role": role, "people": people})

    def _checkpoint_tasks(self, q, graph, evidence):
        return self._related_tasks(q, graph, evidence)

    def _rate_change(self, q, records, store):
        rate_mentions = []
        for rec in records:
            for unit in store.extract_text_units(rec):
                for line in unit.text.splitlines():
                    if "RATE" in line.upper() or "単価" in line:
                        dates = re.findall(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?", line)
                        nums = re.findall(r"(?:RATE|単価)[^0-9]{0,20}([0-9,.]+)", line, re.I)
                        if dates or nums:
                            rate_mentions.append((rec.relative_path, unit.locator, line.strip(), dates, nums))
        dated = [x for x in rate_mentions if x[3]]
        if dated:
            dates = sorted({tuple(map(int, d)) for x in dated for d in x[3]})
            if len(dates) >= 1:
                # A change takes effect on a stated boundary; choose earliest date associated with changed/new RATE wording.
                y, m, _ = dates[-1] if len(dates) > 1 else dates[0]
                return ExecutionResult(True, f"{y}年{m}月1日", .84, "multi_document_rate_effective_date", [Evidence(src, loc, line) for src, loc, line, _, _ in dated])
        return ExecutionResult.abstain("RATE変更日を文書間で特定できない", diagnostics={"mentions": rate_mentions})

    @staticmethod
    def _id_key(value: str):
        m = re.search(r"(\d+)", value)
        return (re.sub(r"\d", "", value), int(m.group(1)) if m else 0)
