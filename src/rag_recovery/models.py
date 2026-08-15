from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Evidence:
    source: str
    locator: str
    detail: str
    value: Any | None = None


@dataclass
class ExecutionResult:
    answered: bool
    answer: str = "わからない"
    confidence: float = 0.0
    method: str = "abstain"
    evidence: list[Evidence] = field(default_factory=list)
    reason: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def abstain(cls, reason: str, *, diagnostics: dict[str, Any] | None = None) -> "ExecutionResult":
        return cls(False, reason=reason, diagnostics=diagnostics or {})


@dataclass(frozen=True)
class Question:
    split: str
    question_id: int
    text: str
    selected_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative_path: str
    extension: str
    project: str
    area: str
    role: str
    filename: str
    stem: str
    version: str
    size: int


@dataclass(frozen=True)
class TextUnit:
    source: str
    locator: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryPlan:
    route: str
    project_hints: tuple[str, ...] = ()
    filename_hints: tuple[str, ...] = ()
    operations: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    constraints: dict[str, Any] = field(default_factory=dict)
    source_mode: str = "single_document"
