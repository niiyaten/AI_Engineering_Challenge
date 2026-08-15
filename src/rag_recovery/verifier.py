from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import ExecutionResult, Question
from .normalize import norm

_NUM_RE = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?")


@dataclass(frozen=True)
class VerificationDecision:
    accepted: bool
    reason: str
    score: float


class EvidenceVerifier:
    """Executor共通の最終Gate。

    回答値やquestion_idは参照せず、回答・根拠・再計算可能性・競合だけを見る。
    """

    def __init__(self, root: Path, *, min_confidence: float = 0.80):
        self.root = root.resolve()
        self.min_confidence = min_confidence

    def verify(self, question: Question, result: ExecutionResult) -> VerificationDecision:
        if not result.answered:
            return VerificationDecision(False, result.reason or "executor_abstained", 0.0)
        if not result.answer.strip() or norm(result.answer) in {norm("わからない"), norm("不明")}:
            return VerificationDecision(False, "empty_or_unknown_answer", 0.0)
        if result.confidence < self.min_confidence:
            return VerificationDecision(False, f"confidence_below_threshold:{result.confidence:.3f}", result.confidence)
        if not result.evidence:
            return VerificationDecision(False, "missing_evidence", result.confidence)

        source_ok = 0
        for ev in result.evidence:
            candidate = (self.root / ev.source).resolve()
            if candidate.is_relative_to(self.root) and candidate.exists():
                source_ok += 1
        if source_ok == 0:
            return VerificationDecision(False, "evidence_source_not_found", result.confidence)

        if result.diagnostics.get("ambiguous"):
            return VerificationDecision(False, "executor_reported_ambiguity", result.confidence)

        type_reason = self._answer_type_reason(question, result.answer)
        if type_reason is not None:
            return VerificationDecision(False, type_reason, result.confidence)

        numeric_check = self._numeric_consistency(question, result)
        if numeric_check is False:
            return VerificationDecision(False, "numeric_independent_check_failed", result.confidence)

        coverage = source_ok / max(1, len(result.evidence))
        score = min(1.0, result.confidence * (0.90 + 0.10 * coverage))
        return VerificationDecision(True, "accepted", score)


    @staticmethod
    def _answer_type_reason(question: Question, answer: str) -> str | None:
        """Reject obvious answer-shape mismatches before confidence is trusted.

        This deliberately checks only high-precision surface constraints. It does
        not compare against a stored answer or question ID.
        """
        q = question.text
        a = answer.strip()
        compact = re.sub(r"\s+", "", a)

        scalar_markers = (
            "何歳", "何ページ", "何件", "何個", "いくつ", "何項目", "何日",
            "いくら", "何円", "何ドル", "何倍", "割合", "何%", "何％",
            "最も高い", "最も低い", "最大", "最小", "最後に", "誰", "役職",
        )
        if any(marker in q for marker in scalar_markers) and len(a) > 320:
            return "answer_too_long_for_scalar_question"

        if "何ページ" in q or "ページ番号" in q or "何ページですか" in q:
            if not re.search(r"\d+\s*ページ", a):
                return "page_answer_shape_mismatch"

        if "何歳" in q and not re.search(r"[-+]?\d+(?:\.\d+)?\s*歳?", a):
            return "age_answer_shape_mismatch"

        if any(x in q for x in ("いくら", "何円", "何ドル", "何倍", "何%", "何％", "割合")):
            if not _NUM_RE.search(a):
                return "numeric_answer_required"

        if any(x in q for x in ("何件", "何個", "いくつ", "何項目")):
            if not _NUM_RE.search(a):
                return "count_answer_required"

        if "タスクID" in q or "Task ID" in q or "アクションID" in q or "マイルストーンID" in q:
            # A task-ID request should not be answered by a lone descriptive paragraph.
            if not re.search(r"\b(?:MS|CP|T|A|AI|M|B)\d+\b", a, re.I):
                return "id_answer_shape_mismatch"

        if "役職" in q:
            if len(a) > 80 or "\n" in a:
                return "role_answer_shape_mismatch"

        if any(x in q for x in ("誰", "担当者", "氏名")) and not any(x in q for x in ("すべて", "一覧", "挙げ")):
            if len(a) > 100 or a.count("\n") > 1:
                return "person_answer_shape_mismatch"

        if "条件" in q and re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:%|％)?", compact):
            return "condition_question_returned_lone_number"

        # Generic extractors sometimes return an entire document. Keep list/diff
        # questions permissive, but reject clearly unbounded text otherwise.
        if len(a) > 1400:
            return "answer_excessively_long"
        return None

    @staticmethod
    def _numeric_consistency(question: Question, result: ExecutionResult) -> bool | None:
        answer_match = _NUM_RE.search(result.answer)
        if not answer_match:
            return None
        answer_value = float(answer_match.group().replace(",", ""))
        raw_candidates: list[float] = []
        for key, value in result.diagnostics.items():
            if not str(key).startswith("raw_"):
                continue
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                raw_candidates.append(float(value))
        if not raw_candidates:
            return None
        raw = raw_candidates[0]
        q = question.text
        if "切り上げ" in q:
            expected = math.ceil(raw)
        elif "切り捨て" in q:
            expected = math.floor(raw)
        elif "四捨五入" in q:
            expected = math.floor(raw + 0.5) if raw >= 0 else math.ceil(raw - 0.5)
        else:
            m = re.search(r"小数第(\d+)位", q)
            expected = round(raw, int(m.group(1))) if m else raw
        return math.isclose(answer_value, expected, rel_tol=1e-8, abs_tol=1e-8)


def choose_nonconflicting(results: Iterable[tuple[ExecutionResult, VerificationDecision]]) -> tuple[ExecutionResult, VerificationDecision] | None:
    accepted = [(r, d) for r, d in results if d.accepted]
    if not accepted:
        return None
    accepted.sort(key=lambda x: (x[1].score, len(x[0].evidence)), reverse=True)
    best = accepted[0]
    for other in accepted[1:]:
        if norm(other[0].answer) != norm(best[0].answer) and abs(other[1].score - best[1].score) < 0.035:
            return None
    return best
