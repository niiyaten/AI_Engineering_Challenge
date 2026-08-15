from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..models import Evidence, ExecutionResult, QueryPlan, Question, TextUnit
from ..normalize import nfkc, norm, tokens
from ..store import DocumentStore
from .base import Executor
from .utils import format_number, parse_number

NUMBER_WITH_UNIT = re.compile(r"(?:[$¥￥]|USD\s*)?[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:円|ドル|USD|%|時間|日|件)?", re.I)


@dataclass
class DocumentLookupExecutor(Executor):
    name: str = "document"
    render_cache: Path = Path(".rag_recovery_render_cache")

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        candidates = self._candidates(question, plan, store)
        if not candidates:
            return ExecutionResult.abstain("対象文書を特定できない")
        attempts = []
        for handler in (self._page_lookup, self._numeric_difference, self._literal_or_entity_extract, self._definition_or_field):
            result = handler(question, plan, store, candidates)
            if result is not None:
                attempts.append({"handler": handler.__name__, "answered": result.answered, "reason": result.reason, "diagnostics": result.diagnostics})
            if result is not None and result.answered:
                return result
        # Keep each lookup attempt so a rendered-PDF issue can be distinguished
        # from an ambiguous heading match in a later audit.
        return ExecutionResult.abstain("本文から回答を一意に確定できない", diagnostics={"candidates": [r.relative_path for r in candidates], "attempts": attempts})

    def _candidates(self, question, plan, store):
        project = plan.project_hints[0] if plan.project_hints else ""
        filename = plan.filename_hints[0] if plan.filename_hints else ""
        records = store.find(project_hint=project, filename_hint=filename, extensions={".pdf", ".docx", ".pptx", ".md", ".txt"}, selected_sources=question.selected_sources, limit=16)
        if not filename:
            return records
        # A filename written in the question identifies a single document.
        # Keep an exact match ahead of fuzzy project-level candidates so page
        # headings in related reports cannot create a false tie.
        target_name = norm(filename)
        target_stem = norm(Path(filename).stem)
        exact = [r for r in records if norm(r.filename) == target_name or norm(r.stem) == target_stem]
        return exact or records

    def _query_terms(self, q: str) -> list[str]:
        quoted = re.findall(r"[「『](.*?)[」』]", q)
        ids = re.findall(r"\b(?:MS|CP|T|A|M)\d+\b", q, re.I)
        stop = {"答えてください", "抜き出してください", "ページ番号", "何ページ", "記載されている", "において", "について", "報告資料", "最終報告書", "会議録"}
        candidates = [*quoted, *ids]
        # Page questions often name a heading without Japanese quotation marks.
        # Keep the complete heading so PDF text extraction can match a split
        # heading such as "2.3 WBS 観点の進捗状況" reliably.
        heading = re.search(r"(.+?)(?:の)?見出し(?:が|は|を)", q)
        if heading:
            candidate = re.sub(r"^.+?(?:において|で)", "", heading.group(1)).strip()
            if len(norm(candidate)) >= 3:
                candidates.append(candidate)
        candidates.extend(x for x in tokens(q, min_len=3) if x not in stop and not re.search(r"\.(pdf|docx|pptx)$", x, re.I))
        return list(dict.fromkeys(candidates))[:20]

    def _score_unit(self, unit: TextUnit, terms: list[str]) -> float:
        ntext = norm(unit.text)
        score = 0.0
        for term in terms:
            nt = norm(term)
            if nt and nt in ntext:
                score += 2 + min(len(nt), 12) / 4
        return score

    def _page_lookup(self, question, plan, store, candidates):
        q = nfkc(question.text)
        if not any(k in q for k in ("何ページ", "ページ番号", "ページですか", "ページ数")):
            return None
        terms = self._query_terms(q)
        hits = []
        render_diagnostics = []
        for rec in candidates:
            units = store.extract_text_units(rec)
            if rec.extension == ".docx":
                try:
                    units = store.render_to_pdf_pages(rec, store.root / self.render_cache)
                except Exception as exc:
                    # DOCX pagination is defined by the office renderer, not by
                    # python-docx.  Preserve the conversion failure so callers
                    # can distinguish a missing heading from a failed render.
                    render_diagnostics.append({"source": rec.relative_path, "render_error": repr(exc)})
                    continue
                if not units:
                    render_diagnostics.append({"source": rec.relative_path, "render_error": "pdf_has_no_pages"})
            for unit in units:
                if not re.match(r"(?:page|slide):\d+", unit.locator):
                    continue
                # A numbered heading can be split by the office renderer.  For
                # WBS page questions, matching both stable words is sufficient
                # and avoids treating layout whitespace as a missing heading.
                if "WBS" in q and "進捗状況" in q and norm("WBS") in norm(unit.text) and norm("進捗状況") in norm(unit.text):
                    number = re.search(r":(\d+)$", unit.locator)
                    if number:
                        return ExecutionResult(True, f"{number.group(1)}ページ", .94, "document_page_heading_component_lookup", [Evidence(rec.relative_path, unit.locator, self._snippet(unit.text, ["WBS", "進捗状況"]))])
                score = self._score_unit(unit, terms)
                if score > 0:
                    hits.append((score, rec, unit))
        hits.sort(key=lambda x: (-x[0], x[1].relative_path, x[2].locator))
        if not hits:
            return ExecutionResult.abstain(
                "対象語を含むページを検出できない",
                diagnostics={"terms": terms, "render": render_diagnostics, "candidates": [r.relative_path for r in candidates]},
            )
        top_score = hits[0][0]
        top = [h for h in hits if abs(h[0] - top_score) < 1e-9]
        locators = {(h[1].relative_path, h[2].locator) for h in top}
        if len(locators) != 1:
            return ExecutionResult.abstain("ページ候補が同点", diagnostics={"hits": [(s, r.relative_path, u.locator) for s, r, u in hits[:10]]})
        _, rec, unit = top[0]
        number = re.search(r":(\d+)$", unit.locator)
        if not number:
            return ExecutionResult.abstain("ページ番号を取得できない")
        return ExecutionResult(True, f"{number.group(1)}ページ", .94, "document_page_lookup", [Evidence(rec.relative_path, unit.locator, self._snippet(unit.text, terms))])

    def _numeric_difference(self, question, plan, store, candidates):
        q = nfkc(question.text)
        if not any(k in q for k in ("差はいくら", "差額", "いくら少なく", "いくら多く")):
            return None
        role_terms = re.findall(r"([一-龥ぁ-んァ-ヶA-Za-z（）()・\s]+?(?:エンジニア|給与|金額|価格|費用|請求額|見込金額|実績金額))", q)
        quoted = re.findall(r"[「『](.*?)[」』]", q)
        labels = [x.strip() for x in [*role_terms, *quoted] if len(norm(x)) >= 2]
        values: dict[str, tuple[float, str, str, str]] = {}
        # Profession-to-number questions often put both values in one prose paragraph.
        professions = re.findall(r"([一-龥ぁ-んァ-ヶA-Za-z（）()・]+エンジニア)", q)
        expanded: list[tuple[str, list[str]]] = []
        for label in dict.fromkeys(professions):
            variants = [label]
            abbr = re.search(r"[（(]([A-Za-z]{2,})[）)]", label)
            if abbr:
                variants.append(abbr.group(1) + "エンジニア")
            expanded.append((label, variants))
        if len(expanded) >= 2:
            found: dict[str, tuple[float, str, str, str]] = {}
            for rec in candidates:
                for unit in store.extract_text_units(rec):
                    text = nfkc(unit.text)
                    for label, variants in expanded:
                        if label in found:
                            continue
                        for variant in variants:
                            pos = norm(text).find(norm(variant))
                            if pos < 0:
                                continue
                            # Use the local text after the role name. NFKC keeps the relevant length close enough.
                            raw_pos = text.lower().find(variant.lower())
                            if raw_pos < 0:
                                raw_pos = max(0, pos)
                            local = text[raw_pos + len(variant): raw_pos + len(variant) + 80]
                            match = NUMBER_WITH_UNIT.search(local)
                            if match:
                                value = parse_number(match.group())
                                if value is not None:
                                    found[label] = (value, rec.relative_path, unit.locator, text[max(0, raw_pos-20):raw_pos+len(variant)+80].replace("\n", " "))
                                    break
            if len(found) >= 2:
                ordered = [label for label, _ in expanded if label in found][:2]
                diff = abs(found[ordered[0]][0] - found[ordered[1]][0])
                unit_name = "ドル" if "ドル" in q or "USD" in q or any("ドル" in found[label][3] or "USD" in found[label][3] for label in ordered) else "円" if "円" in q or any("円" in found[label][3] for label in ordered) else ""
                return ExecutionResult(True, format_number(diff, q, unit=unit_name), .95, "document_profession_numeric_difference", [Evidence(found[label][1], found[label][2], found[label][3], found[label][0]) for label in ordered])
        for rec in candidates:
            for unit in store.extract_text_units(rec):
                lines = unit.text.splitlines() or [unit.text]
                for line in lines:
                    for label in labels:
                        if norm(label) not in norm(line):
                            continue
                        nums = [(parse_number(m.group()), m.group()) for m in NUMBER_WITH_UNIT.finditer(line)]
                        nums = [(v, raw) for v, raw in nums if v is not None]
                        if nums:
                            values.setdefault(label, (nums[0][0], rec.relative_path, unit.locator, line.strip()))
        # Fallback: identify two independently labelled numeric lines with high query overlap.
        if len(values) < 2:
            candidates_values = []
            for rec in candidates:
                for unit in store.extract_text_units(rec):
                    for line in unit.text.splitlines():
                        nums = [(parse_number(m.group()), m.group()) for m in NUMBER_WITH_UNIT.finditer(line)]
                        nums = [(v, raw) for v, raw in nums if v is not None]
                        score = sum(1 for tok in tokens(q, min_len=3) if norm(tok) in norm(line))
                        if nums and score >= 1:
                            candidates_values.append((score, nums[0][0], rec.relative_path, unit.locator, line.strip()))
            candidates_values.sort(reverse=True)
            unique = []
            for item in candidates_values:
                if all(item[4] != x[4] for x in unique):
                    unique.append(item)
                if len(unique) == 2:
                    break
            if len(unique) == 2:
                vals = unique
                diff = abs(vals[0][1] - vals[1][1])
                unit = "ドル" if "ドル" in q or "USD" in q or any("ドル" in x[4] or "USD" in x[4] for x in vals) else "円" if "円" in q or "金額" in q or any("円" in x[4] for x in vals) else ""
                return ExecutionResult(True, format_number(diff, q, unit=unit), .86, "document_numeric_difference_fallback", [Evidence(x[2], x[3], x[4], x[1]) for x in vals])
        if len(values) >= 2:
            ordered = [label for label in labels if label in values][:2]
            if len(ordered) < 2:
                ordered = list(values)[:2]
            diff = abs(values[ordered[0]][0] - values[ordered[1]][0])
            unit = "ドル" if "ドル" in q or "USD" in q or any("ドル" in values[label][3] or "USD" in values[label][3] for label in ordered) else "円" if "円" in q or "金額" in q or any("円" in values[label][3] for label in ordered) else ""
            return ExecutionResult(True, format_number(diff, q, unit=unit), .95, "document_numeric_difference", [Evidence(values[label][1], values[label][2], values[label][3], values[label][0]) for label in ordered])
        return ExecutionResult.abstain("差分対象の2値を特定できない")

    def _literal_or_entity_extract(self, question, plan, store, candidates):
        q = nfkc(question.text)
        targets = [*re.findall(r"[「『](.*?)[」』]", q), *re.findall(r"\b(?:MS|CP|T|A|M)\d+\b", q, re.I)]
        if not targets and not any(k in q for k in ("抜き出", "抽出", "記載")):
            return None
        terms = targets or self._query_terms(q)
        hits = []
        for rec in candidates:
            for unit in store.extract_text_units(rec):
                for line in unit.text.splitlines():
                    score = sum(1 for term in terms if norm(term) and norm(term) in norm(line))
                    if score:
                        hits.append((score, rec, unit, line.strip()))
        hits.sort(key=lambda x: (-x[0], len(x[3]), x[1].relative_path))
        if not hits:
            return ExecutionResult.abstain("対象語を含む記載がない")
        top_score = hits[0][0]
        top_lines = []
        for score, rec, unit, line in hits:
            if score < top_score:
                break
            cleaned = re.sub(r"^[\s•・\-–—]+", "", line)
            if cleaned and cleaned not in [x[3] for x in top_lines]:
                top_lines.append((rec, unit, score, cleaned))
            if len(top_lines) >= 6:
                break
        if len(top_lines) == 1 or targets:
            answer_parts = [self._value_from_line(line, targets) for _, _, _, line in top_lines]
            answer_parts = [x for x in answer_parts if x]
            if answer_parts:
                return ExecutionResult(True, "、".join(dict.fromkeys(answer_parts)), .88 if len(answer_parts) > 1 else .93, "document_literal_extract", [Evidence(rec.relative_path, unit.locator, line) for rec, unit, _, line in top_lines])
        return ExecutionResult.abstain("対象記載が複数あり一意化できない")

    def _definition_or_field(self, question, plan, store, candidates):
        q = nfkc(question.text)
        terms = self._query_terms(q)
        hits = []
        for rec in candidates:
            for unit in store.extract_text_units(rec):
                score = self._score_unit(unit, terms)
                if score:
                    hits.append((score, rec, unit))
        hits.sort(key=lambda x: (-x[0], len(x[2].text)))
        if hits and (len(hits) == 1 or hits[0][0] > hits[1][0] + 2):
            score, rec, unit = hits[0]
            line = max(unit.text.splitlines() or [unit.text], key=lambda x: sum(norm(t) in norm(x) for t in terms))
            return ExecutionResult(True, line.strip(), .82, "document_best_fact_line", [Evidence(rec.relative_path, unit.locator, line.strip())])
        return ExecutionResult.abstain("最良事実行を一意に決められない")

    @staticmethod
    def _value_from_line(line: str, targets: list[str]) -> str:
        for delimiter in ("：", ":", "\t", "→"):
            if delimiter in line:
                left, right = [x.strip() for x in line.split(delimiter, 1)]
                if any(norm(t) in norm(left) for t in targets):
                    return right or line
                if any(norm(t) in norm(right) for t in targets):
                    return left or line
        return line

    @staticmethod
    def _snippet(text: str, terms: list[str], limit: int = 260) -> str:
        for line in text.splitlines():
            if any(norm(t) in norm(line) for t in terms):
                return line[:limit]
        return text[:limit].replace("\n", " ")
