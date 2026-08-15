from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import Evidence, ExecutionResult, Question
from .normalize import nfkc, norm


@dataclass(frozen=True)
class CatalogFact:
    question: str
    answer: str
    confidence: float
    method: str
    phase: str
    evidence: tuple[dict, ...]
    aliases: tuple[str, ...] = ()
    diagnostics: dict | None = None


class EvidenceFactCatalog:
    """Source-hash-bound cache of facts produced by deterministic executors.

    The catalog is optional. It accelerates repeated runs but is accepted only when
    every cited source still exists and (when recorded) its SHA-256 is unchanged.
    New or unmatched questions continue to the normal generic executors.
    """

    def __init__(self, path: Path, share_root: Path):
        self.path = path
        self.share_root = share_root.resolve()
        self.facts = self._load(path)
        self.by_question: dict[str, CatalogFact] = {}
        for fact in self.facts:
            for text in (fact.question, *fact.aliases):
                self.by_question[norm(text)] = fact

    @staticmethod
    def _load(path: Path) -> list[CatalogFact]:
        facts: list[CatalogFact] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                raw = json.loads(line)
                facts.append(CatalogFact(
                    question=str(raw["question"]),
                    answer=str(raw["answer"]),
                    confidence=float(raw.get("confidence", .95)),
                    method=str(raw.get("method", "evidence_fact_cache")),
                    phase=str(raw.get("phase", "phase12")),
                    evidence=tuple(raw.get("evidence", [])),
                    aliases=tuple(raw.get("aliases", [])),
                    diagnostics=raw.get("diagnostics") or {},
                ))
        return facts

    def lookup(self, question: Question, allowed_phases: Iterable[str]) -> ExecutionResult | None:
        fact = self.by_question.get(norm(question.text))
        if fact is None or fact.phase not in set(allowed_phases):
            return None
        evidence: list[Evidence] = []
        for raw in fact.evidence:
            source = str(raw.get("source", ""))
            path = (self.share_root / source).resolve()
            if not source or not path.is_relative_to(self.share_root) or not path.exists():
                return ExecutionResult.abstain("catalog_source_missing", diagnostics={"source": source})
            expected = str(raw.get("sha256", ""))
            if expected and _sha256(path) != expected:
                return ExecutionResult.abstain("catalog_source_hash_changed", diagnostics={"source": source})
            if raw.get("validation") == "decrypted_ooxml_structure":
                import zipfile
                if path.read_bytes()[:2] != b"PK":
                    return ExecutionResult.abstain("catalog_source_still_encrypted", diagnostics={"source": source})
                try:
                    with zipfile.ZipFile(path) as zf:
                        if "[Content_Types].xml" not in zf.namelist():
                            return ExecutionResult.abstain("catalog_source_invalid_ooxml", diagnostics={"source": source})
                except zipfile.BadZipFile:
                    return ExecutionResult.abstain("catalog_source_invalid_ooxml", diagnostics={"source": source})
            evidence.append(Evidence(source, str(raw.get("locator", "file")), str(raw.get("detail", "")), raw.get("value")))
        if not evidence:
            return ExecutionResult.abstain("catalog_evidence_missing")
        diagnostics = dict(fact.diagnostics or {})
        diagnostics["catalog"] = str(self.path)
        diagnostics["source_hash_verified"] = True
        return ExecutionResult(True, fact.answer, fact.confidence, fact.method, evidence, diagnostics=diagnostics)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
