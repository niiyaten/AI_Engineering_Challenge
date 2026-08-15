from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ExecutionResult, QueryPlan, Question
from ..store import DocumentStore


class Executor(ABC):
    name: str

    @abstractmethod
    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        raise NotImplementedError
