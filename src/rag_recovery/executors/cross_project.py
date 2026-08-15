from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from ..models import Evidence, ExecutionResult, QueryPlan, Question
from ..normalize import nfkc, norm
from ..store import DocumentStore
from .base import Executor
from .utils import DATE_RE, format_number, parse_date, parse_number

MONEY_RE = re.compile(r"(?:税込|契約金額[^\n]{0,30}|合計[^\n]{0,20})?\s*[¥￥]?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,})(?:円)?")
PERSON_RE = re.compile(r"(?:[一-龥]{1,4}\s+[一-龥]{1,4}|[一-龥]{2,5})(?=\s*(?:さん|氏|\t|／|/|役割|担当|リード|データ|プロジェクト))")


@dataclass
class ProjectFacts:
    project: str
    alias: str
    sample_rows: int | None = None
    missing_rows: int | None = None
    contract_amount_tax_included: float | None = None
    contract_type: str = ""
    contract_start: date | None = None
    contract_end: date | None = None
    payment_dates: tuple[date, ...] = ()
    complete: bool = False
    people: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()


@dataclass
class CrossProjectEnumerationExecutor(Executor):
    name: str = "cross_project"

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        q = nfkc(question.text)
        facts = self._build_facts(store)
        if not facts:
            return ExecutionResult.abstain("案件別ファクトを構築できない")
        if "欠損" in q and "最も多" in q:
            return self._rank_metric(q, facts, "missing_rows")
        if any(k in q for k in ("サンプル数", "行数")) and any(k in q for k in ("最も多", "10000行以上", "以上")):
            return self._sample_filter(q, facts, store)
        if "1行あたり" in q and "契約金額" in q:
            return self._amount_per_row(q, facts)
        if "契約期間" in q or "時点で存在する案件" in q:
            return self._contract_period_query(q, facts)
        if "支払月" in q and ("上位" in q or "総額" in q):
            return self._payment_month_ranking(q, facts)
        if "もっとも多くの案件にかかわっている人" in q or "最も多くの案件" in q and "人" in q:
            return self._most_involved_person(q, facts, store)
        return ExecutionResult.abstain("案件横断集計の意味を確定できない", diagnostics={"project_count": len(facts)})

    def _build_facts(self, store: DocumentStore) -> list[ProjectFacts]:
        evidence_by_project: dict[str, list[Evidence]] = defaultdict(list)
        raw: dict[str, dict[str, Any]] = {project: {} for project in store.projects}
        for project in store.projects:
            # Dataset facts: prefer canonical 03.データ/train.csv, then train.xlsx.
            data_records = store.find(project_hint=project, roles={"data"}, extensions={".csv", ".xlsx", ".xlsm"}, limit=12)
            canonical = sorted(data_records, key=lambda r: (0 if "/03.データ/" in r.relative_path and r.filename.lower() == "train.csv" else 1, len(r.relative_path)))
            for rec in canonical:
                try:
                    if rec.extension == ".csv":
                        df = store.read_csv(rec)
                    else:
                        tables = []
                        wb = store.load_workbook(rec, data_only=True)
                        for ws in wb.worksheets:
                            values = list(ws.values)
                            if values and len(values) > 1:
                                tables.append(pd.DataFrame(values[1:], columns=values[0]))
                        df = max(tables, key=len) if tables else pd.DataFrame()
                    if not df.empty:
                        raw[project]["sample_rows"] = len(df)
                        raw[project]["missing_rows"] = int(df.isna().any(axis=1).sum())
                        evidence_by_project[project].append(Evidence(rec.relative_path, "dataset", f"rows={len(df)}, missing_rows={raw[project]['missing_rows']}"))
                        break
                except Exception:
                    continue
            # Contracts.
            contracts = store.find(project_hint=project, roles={"contract"}, extensions={".docx", ".pdf", ".pptx"}, limit=8)
            for rec in contracts:
                text = "\n".join(unit.text for unit in store.extract_text_units(rec))
                if not text.strip():
                    continue
                amounts = [float(x.replace(",", "")) for x in MONEY_RE.findall(text)]
                tax_lines = [line for line in text.splitlines() if "税込" in line and MONEY_RE.search(line)]
                tax_amounts = [float(MONEY_RE.search(line).group(1).replace(",", "")) for line in tax_lines if MONEY_RE.search(line)]
                if tax_amounts:
                    raw[project]["contract_amount_tax_included"] = max(tax_amounts)
                elif amounts:
                    raw[project]["contract_amount_tax_included"] = max(amounts)
                low = text.lower()
                raw[project]["contract_type"] = "fixed" if any(k in low for k in ("固定金額", "一式", "fixed")) else "time_material" if any(k in low for k in ("実績工数", "時間単価", "準委任")) else ""
                dates = [date(*map(int, m)) for m in DATE_RE.findall(text)]
                plausible = [(a, b) for a in dates for b in dates if a <= b and 1 <= (b - a).days + 1 <= 730]
                if plausible:
                    start, end = max(plausible, key=lambda p: (p[1] - p[0]).days)
                    raw[project]["contract_start"], raw[project]["contract_end"] = start, end
                payment_dates = []
                for line in text.splitlines():
                    if any(k in line for k in ("支払", "精算", "請求")):
                        payment_dates.extend(date(*map(int, m)) for m in DATE_RE.findall(line))
                raw[project]["payment_dates"] = tuple(sorted(set(payment_dates)))
                evidence_by_project[project].append(Evidence(rec.relative_path, "contract", f"amount={raw[project].get('contract_amount_tax_included')}, period={raw[project].get('contract_start')}..{raw[project].get('contract_end')}, type={raw[project].get('contract_type')}"))
                break
            # Completion and people from proposals/final reports/schedules.
            people: set[str] = set()
            for rec in store.find(project_hint=project, roles={"proposal", "schedule", "final_report"}, extensions={".docx", ".pptx", ".pdf", ".xlsx"}, limit=16):
                text = "\n".join(unit.text for unit in store.extract_text_units(rec))
                if rec.role == "final_report" and any(k in text for k in ("完了", "検収", "最終報告")):
                    raw[project]["complete"] = True
                for name in PERSON_RE.findall(text):
                    if 2 <= len(norm(name)) <= 12:
                        people.add(name.strip())
            raw[project]["people"] = tuple(sorted(people))
        facts = []
        for project, values in raw.items():
            alias = self._alias(project, store)
            facts.append(ProjectFacts(project, alias, evidence=tuple(evidence_by_project[project]), **values))
        return facts

    def _rank_metric(self, q, facts, attr):
        rows = [(getattr(f, attr), f) for f in facts if getattr(f, attr) is not None]
        if not rows:
            return ExecutionResult.abstain(f"{attr}を取得できない")
        rows.sort(key=lambda x: x[0], reverse=True)
        if len(rows) > 1 and rows[0][0] == rows[1][0]:
            return ExecutionResult.abstain("同率首位", diagnostics={f.alias: value for value, f in rows})
        value, winner = rows[0]
        return ExecutionResult(True, winner.alias, .98, f"cross_project_{attr}_ranking", [e for _, f in rows for e in f.evidence if attr.split("_")[0] in e.detail or e.locator == "dataset"])

    def _sample_filter(self, q, facts, store):
        threshold_match = re.search(r"([0-9,]+)行以上", q)
        threshold = int(threshold_match.group(1).replace(",", "")) if threshold_match else None
        selected = [f for f in facts if f.sample_rows is not None and (threshold is None or f.sample_rows >= threshold)]
        if "完了案件" in q:
            selected = [f for f in selected if f.complete]
        # APR criteria are resolved from internal documents by project/alias mentions.
        apr_match = re.search(r"APR[-_A-Za-z0-9]+", q, re.I)
        if apr_match:
            target = norm(apr_match.group())
            matching_projects = set()
            for rec in store.find(roles={"internal"}, extensions={".md", ".docx", ".xlsx", ".csv"}, limit=20):
                for unit in store.extract_text_units(rec):
                    for line in unit.text.splitlines():
                        if target in norm(line):
                            for f in facts:
                                if norm(f.alias) in norm(line) or norm(f.project) in norm(line):
                                    matching_projects.add(f.project)
            selected = [f for f in selected if f.project in matching_projects]
        if not selected:
            return ExecutionResult.abstain("条件を満たす案件がない、またはAPR対応を解決できない")
        return ExecutionResult(True, "、".join(sorted(f.alias for f in selected)), .88, "cross_project_project_filter", [e for f in selected for e in f.evidence])

    def _amount_per_row(self, q, facts):
        rows = []
        for f in facts:
            if f.contract_amount_tax_included is None or not f.sample_rows or ("固定金額契約" in q and f.contract_type != "fixed"):
                continue
            rows.append((f.contract_amount_tax_included / f.sample_rows, f))
        if not rows:
            return ExecutionResult.abstain("契約金額とデータ行数を結合できない")
        rows.sort(reverse=True, key=lambda x: x[0])
        value, winner = rows[0]
        answer = f"{winner.alias}、{format_number(value, q, unit='円')}"
        return ExecutionResult(True, answer, .94, "cross_project_amount_per_row", list(winner.evidence), diagnostics={f.alias: v for v, f in rows})

    def _contract_period_query(self, q, facts):
        dates = [date(*map(int, m)) for m in DATE_RE.findall(q)]
        if "時点で存在する案件" in q and dates:
            target = dates[0]
            active = [f for f in facts if f.contract_start and f.contract_end and f.contract_start <= target <= f.contract_end]
            if not active:
                return ExecutionResult(True, f"{target.year}年{target.month}月{target.day}日時点で存在する案件はない", .96, "cross_project_active_contracts", [e for f in facts for e in f.evidence if e.locator == "contract"])
            return ExecutionResult(True, "、".join(sorted(f.alias for f in active)), .95, "cross_project_active_contracts", [e for f in active for e in f.evidence if e.locator == "contract"])
        if len(dates) >= 2:
            start, end = dates[:2]
            duration_match = re.search(r"(\d+)日(?:を)?超", q)
            min_days = int(duration_match.group(1)) if duration_match else 0
            selected = []
            for f in facts:
                if not f.contract_start or not f.contract_end:
                    continue
                overlap = f.contract_start <= end and f.contract_end >= start
                duration = (f.contract_end - f.contract_start).days + 1
                if overlap and duration > min_days:
                    selected.append(f)
            if selected:
                return ExecutionResult(True, "、".join(sorted(f.alias for f in selected)), .91, "cross_project_contract_overlap", [e for f in selected for e in f.evidence if e.locator == "contract"])
        return ExecutionResult.abstain("契約期間条件を解析できない")

    def _payment_month_ranking(self, q, facts):
        totals: dict[str, float] = defaultdict(float)
        evidence = []
        for f in facts:
            if f.contract_amount_tax_included is None or not f.payment_dates:
                continue
            # Multiple payment dates are treated as equal installments unless the document gives separate amounts.
            per_payment = f.contract_amount_tax_included / len(f.payment_dates)
            for d in f.payment_dates:
                key = f"{d.year}年{d.month}月"
                totals[key] += per_payment
                evidence.extend(e for e in f.evidence if e.locator == "contract")
        if not totals:
            return ExecutionResult.abstain("支払月と精算額を結合できない")
        topn_match = re.search(r"上位\s*(\d+)", q)
        topn = int(topn_match.group(1)) if topn_match else 3
        ranked = sorted(totals.items(), key=lambda x: (-x[1], x[0]))[:topn]
        return ExecutionResult(True, "、".join(f"{month}: {format_number(value, q, unit='円')}" for month, value in ranked), .84, "cross_project_payment_month_ranking", evidence, diagnostics={"monthly_totals": totals})

    def _most_involved_person(self, q, facts, store):
        counts = Counter()
        for f in facts:
            for person in set(f.people):
                counts[person] += 1
        if not counts:
            return ExecutionResult.abstain("案件メンバーを抽出できない")
        max_count = max(counts.values())
        winners = sorted(name for name, count in counts.items() if count == max_count)
        if len(winners) != 1:
            return ExecutionResult.abstain("最多関与者が同率", diagnostics={x: counts[x] for x in winners})
        person = winners[0]
        # Resolve extension from internal contact/seat documents.
        extensions = []
        for rec in store.find(roles={"internal"}, extensions={".docx", ".xlsx", ".csv", ".md", ".pptx"}, limit=30):
            for unit in store.extract_text_units(rec):
                for line in unit.text.splitlines():
                    if norm(person) in norm(line):
                        nums = re.findall(r"\b\d{3,6}\b", line)
                        if nums:
                            extensions.append((nums[-1], rec.relative_path, unit.locator, line))
        unique = {x[0] for x in extensions}
        if len(unique) == 1:
            value = next(iter(unique))
            return ExecutionResult(True, value, .9, "cross_project_member_count_then_extension_join", [Evidence(src, loc, line) for _, src, loc, line in extensions], diagnostics={"person": person, "project_count": max_count})
        return ExecutionResult.abstain("最多関与者の内線番号を一意に解決できない", diagnostics={"person": person, "project_count": max_count, "extensions": sorted(unique)})

    @staticmethod
    def _alias(project: str, store: DocumentStore) -> str:
        for alias_norm, target in store.aliases.items():
            if target == project and alias_norm.isascii() and 2 <= len(alias_norm) <= 16:
                return alias_norm.upper()
        compact = re.sub(r"株式会社|医療法人社団", "", project).strip()
        return compact
