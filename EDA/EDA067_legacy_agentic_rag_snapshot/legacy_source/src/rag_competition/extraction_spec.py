from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExtractionSpec:
    schema_version: str = "1.0"
    target_type: str = "text"
    selection_mode: str = "single"
    match_mode: str = "contains"
    verbatim: bool = False
    output_scope: str = "paragraph"
    search_terms: list[str] = field(default_factory=list)
    identifier_terms: list[str] = field(default_factory=list)
    format_conditions: dict[str, Any] = field(default_factory=lambda: {"bold": None, "italic": None, "underline": None, "font_color": None, "highlight_color": None, "fill_color": None, "comment_present": None})
    exclude_conditions: list[dict[str, Any]] = field(default_factory=list)
    location_requirement: str | None = None
    location_hints: list[int] = field(default_factory=list)
    identifier_output_only: bool = False
    preserve_line_breaks: bool = True
    preserve_punctuation: bool = True
    deduplicate: bool = True
    sort_order: str = "document_order"
    answer_constraints: dict[str, Any] = field(default_factory=lambda: {"answer_type": "text", "list_required": False, "extract_all": False})
    analysis_source: str = "mechanical"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _has(question: str, *terms: str) -> bool:
    return any(term in question for term in terms)


def _color(question: str, mapping: dict[str, str]) -> str | None:
    lowered = question.lower()
    for label, normalized in mapping.items():
        if label in lowered:
            return normalized
    return None


def normalize_identifier(value: str) -> str:
    return re.sub(r"[-_\s:：]", "", unicodedata.normalize("NFKC", value or "")).upper()


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", unicodedata.normalize("NFKC", value or "")).upper()


def build_extraction_spec(question: str, llm_spec: dict[str, Any] | None = None) -> ExtractionSpec:
    q = unicodedata.normalize("NFKC", question or "")
    spec = ExtractionSpec()
    spec.verbatim = _has(q, "\u305d\u306e\u307e\u307e", "\u539f\u6587", "\u629c\u304d\u51fa", "\u5168\u6587")
    spec.selection_mode = "all" if _has(q, "\u3059\u3079\u3066", "\u5168\u3066", "\u8a72\u5f53\u7b87\u6240\u3092\u6319", "\u3059\u3079\u3066\u6319") else "single"
    spec.answer_constraints["extract_all"] = spec.selection_mode == "all"
    spec.answer_constraints["list_required"] = spec.selection_mode == "all" or _has(q, "\u4e00\u89a7", "\u7b87\u6761\u66f8")
    spec.output_scope = "page" if _has(q, "\u30da\u30fc\u30b8", "\u4f55\u30da\u30fc\u30b8") else "slide" if _has(q, "\u30b9\u30e9\u30a4\u30c9", "\u4f55\u679a") else "comment" if _has(q, "\u30b3\u30e1\u30f3\u30c8") else "paragraph"
    spec.location_requirement = "page" if spec.output_scope == "page" else "slide" if spec.output_scope == "slide" else None
    spec.location_hints = [int(value) for value in re.findall(r"P\s*(\d{1,3})", q, re.IGNORECASE)]
    if spec.location_requirement:
        spec.target_type = "location"
    elif _has(q, "\u898b\u51fa\u3057", "\u7ae0", "\u9805\u76ee"):
        spec.target_type = "heading"
    elif _has(q, "ID", "id", "\u30bf\u30b9\u30af", "\u30a2\u30af\u30b7\u30e7\u30f3", "\u30de\u30a4\u30eb\u30b9\u30c8\u30fc\u30f3"):
        spec.target_type = "identifier_record"
    elif _has(q, "\u30b3\u30e1\u30f3\u30c8"):
        spec.target_type = "comment"
    if _has(q, "\u592a\u5b57", "bold"):
        spec.format_conditions["bold"] = True
    if _has(q, "\u659c\u4f53", "\u30a4\u30bf\u30ea\u30c3\u30af", "italic"):
        spec.format_conditions["italic"] = True
    if _has(q, "\u4e0b\u7dda", "underline"):
        spec.format_conditions["underline"] = True
    spec.format_conditions["font_color"] = _color(q, {"\u8d64": "red", "red": "red", "\u9752": "blue", "blue": "blue", "\u9ed2": "black", "black": "black"})
    if _has(q, "\u8d64\u3067\u5f37\u8abf", "\u8d64\u8272\u3067\u5f37\u8abf", "red emphasis"):
        spec.format_conditions["font_color"] = None
        spec.format_conditions["fill_color"] = "red"
    spec.format_conditions["highlight_color"] = _color(q, {"\u9ec4\u8272": "yellow", "\u9ec4": "yellow", "yellow": "yellow", "\u7dd1": "green", "green": "green", "\u9752": "blue", "blue": "blue"})
    if _has(q, "\u65e5\u4ed8\u4ee5\u5916", "\u65e5\u4ed8\u3092\u9664"):
        spec.exclude_conditions.append({"type": "date"})
    if _has(q, "\u30b3\u30e1\u30f3\u30c8\u304c\u3064\u3044\u3066", "\u30b3\u30e1\u30f3\u30c8\u4ed8\u304d"):
        spec.format_conditions["comment_present"] = True
    if spec.verbatim and any(value is not None for value in spec.format_conditions.values()):
        spec.output_scope = "continuous_runs"
    quoted = re.findall(r"[\u300c\u300e\"']([^\u300d\u300f\"']+)[\u300d\u300f\"']", q)
    identifiers = re.findall(r"(?:[A-Za-z]{1,8}\d{1,4}|\d{1,3}\.)", q)
    spec.search_terms = list(dict.fromkeys(quoted))
    spec.identifier_terms = list(dict.fromkeys(normalize_identifier(value) for value in identifiers))
    if spec.target_type == "identifier_record" and not identifiers and _has(q, "\u30bf\u30b9\u30afID", "\u30a2\u30af\u30b7\u30e7\u30f3ID"):
        spec.identifier_output_only = True
    # M02資料のような資料略称は、format抽出の識別子ではないためID条件にしない。
    if any(value is not None for value in spec.format_conditions.values()) and not _has(q, "ID", "id", "タスク", "アクション", "マイルストーン"):
        spec.identifier_terms = []
    if not spec.search_terms:
        phrase_match = re.search(r"([^、。\n]{2,40})(?:に)?一致", q)
        if phrase_match:
            spec.search_terms = [phrase_match.group(1).strip()]
    if spec.target_type == "identifier_record" and _has(q, "\u30bf\u30b9\u30afID", "\u30a2\u30af\u30b7\u30e7\u30f3ID"):
        phase_match = re.search(r"(.{2,40}?)(?:に一致する|に対応する).{0,12}(?:タスクID|アクションID)", q)
        if phase_match:
            phase = phase_match.group(1).strip().rstrip("に")
            if "において、" in phase:
                phase = phase.split("において、")[-1]
            phase = phase.removesuffix("フェーズ").strip()
            spec.search_terms = [phase]
    if not spec.search_terms and not spec.identifier_terms and not any(value is not None for value in spec.format_conditions.values()):
        spec.search_terms = list(dict.fromkeys(re.findall(r"\b[A-Za-z][A-Za-z0-9_./-]{2,}\b", q)))
    if _has(q, "\u307e\u305f\u306f", "or"):
        spec.match_mode = "any"
    elif spec.search_terms or spec.identifier_terms:
        spec.match_mode = "all"
    if llm_spec:
        for key in ("target_type", "output_scope", "location_requirement", "search_terms", "identifier_terms"):
            if getattr(spec, key) in (None, "", []) and llm_spec.get(key) not in (None, "", []):
                value = llm_spec[key]
                setattr(spec, key, [normalize_identifier(item) for item in value] if key == "identifier_terms" else value)
        spec.analysis_source = "mechanical+llm"
    return spec
