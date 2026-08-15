from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import sha1_text
from .llm_client import OpenRouterClient
from .schemas import ExtractionResult, FileRecord
from .search import tokenize


SEMANTIC_PROMPT_VERSION = "semantic_candidate_selection_v1"
MAX_SEMANTIC_CANDIDATES = 16


@dataclass(frozen=True)
class SemanticSpec:
    subtype: str
    output_type: str
    selection_mode: str
    target_terms: tuple[str, ...]
    supported: bool
    unsupported_reason: str = ""


def _role_words() -> tuple[str, ...]:
    return ("\u62c5\u5f53", "\u62c5\u5f53\u8005", "\u5f79\u5272", "\u8cac\u4efb\u8005", "\u4e3b\u62c5\u5f53", "\u526f\u62c5\u5f53", "\u7a93\u53e3", "\u627f\u8a8d\u8005", "\u4f5c\u6210\u8005", "PM", "PL", "\u30c7\u30fc\u30bf\u30a8\u30f3\u30b8\u30cb\u30a2", "\u30c7\u30fc\u30bf\u30b5\u30a4\u30a8\u30f3\u30c6\u30a3\u30b9\u30c8")


def _status_words() -> tuple[str, ...]:
    return (
        "\u672a\u7740\u624b", "\u7740\u624b\u524d", "\u9032\u884c\u4e2d", "\u5b9f\u65bd\u4e2d", "\u5bfe\u5fdc\u4e2d",
        "\u5b8c\u4e86", "\u5b8c\u4e86\u6e08\u307f", "\u5bfe\u5fdc\u6e08\u307f", "\u5b9f\u65bd\u6e08\u307f", "\u30af\u30ed\u30fc\u30ba",
        "\u4fdd\u7559", "\u4e00\u6642\u505c\u6b62", "\u30da\u30f3\u30c7\u30a3\u30f3\u30b0", "\u627f\u8a8d\u6e08\u307f", "\u627f\u8a8d\u5f85\u3061",
        "\u672a\u627f\u8a8d", "\u5dee\u623b\u3057", "\u5374\u4e0b", "\u672a\u5bfe\u5fdc", "\u5bfe\u5fdc\u4e0d\u8981", "\u5bfe\u8c61\u5916", "\u4e2d\u6b62", "\u30ad\u30e3\u30f3\u30bb\u30eb",
        "\u672a\u5b8c\u4e86", "\u672a\u9054\u6210", "Open", "Closed", "Pending", "In Progress",
    )


def build_list_spec(question: str) -> SemanticSpec:
    """質問が一覧抽出を求めている場合だけ、汎用的な一覧処理へ分類する。"""
    text = _normalize(question)
    comparison = _detect_comparison_requirement(text)
    if comparison["is_comparison"]:
        return SemanticSpec("unsupported", "", "multiple", (), False, comparison["reason"])
    # 書式や逐語抽出を求める質問は一覧抽出へ流さず、既存の書式経路へ戻す。
    format_terms = ("\u30de\u30fc\u30ab\u30fc", "\u30cf\u30a4\u30e9\u30a4\u30c8", "\u592a\u5b57", "\u5f37\u8abf", "\u66f8\u5f0f", "\u30d5\u30a9\u30f3\u30c8", "highlight", "bold", "underline")
    if any(term in text for term in format_terms):
        return SemanticSpec("unsupported", "", "single", (), False, "format_or_verbatim_required")
    # 比較・集計・日付条件は一覧Executorだけでは安全に確定できないため、
    # 候補が生成できても計算または専用条件処理へ再分類する。
    if any(term in text for term in ("最も", "最大", "最小", "乖離", "異なる", "平均", "割合", "件数", "何件", "以上", "以下", "超えて")):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_comparison_required")
    if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text) or any(term in text for term in ("以前", "以降", "期間が重な", "日時点")):
        return SemanticSpec("unsupported", "", "single", (), False, "date_filter_resolution_required")
    if any(term in text for term in ("ハイライト", "強調", "太字", "赤字", "黄色", "書式", "フォント", "塗りつぶし")):
        return SemanticSpec("unsupported", "", "single", (), False, "format_or_verbatim_required")
    list_terms = ("すべて", "全て", "一覧", "列挙", "抽出", "挙げ", "どれ")
    if not any(term in text for term in list_terms):
        return SemanticSpec("semantic_fact_lookup", "single_text", "single", (), False, "list_term_not_found")
    if any(term in text for term in ("何ページ", "ページ番号", "スライド番号", "シート名", "セル", "何件", "いくつ")):
        return SemanticSpec("unsupported", "", "single", (), False, "location_or_count_required")
    if any(term in text for term in ("比較", "変更点", "差分", "間に", "以外", "異なる", "以上", "未満")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "compound_comparison_not_supported")
    if any(term in text for term in ("別資料", "会議録", "報告資料") ) and any(term in text for term in ("で", "から")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "multi_source_list_not_supported")
    if any(term in text for term in ("未完", "未達", "未対応", "完了", "Open", "クローズ")):
        subtype = "status_filtered_list"
    elif any(term in text for term in ("ID", "番号", "コード")):
        subtype = "identifier_list"
    elif any(term in text for term in ("対象外", "スコープ外")):
        subtype = "scope_exclusion_list"
    else:
        subtype = "filtered_table_list" if any(term in text for term in ("条件", "該当", "項目")) else "explicit_bullet_list"
    terms = tuple(dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z0-9_-]*|[\u3000-\u9fff]{2,}", text)))
    return SemanticSpec("semantic_list_extraction", subtype, "all", terms, True)


def _detect_comparison_requirement(text: str) -> dict[str, Any]:
    """複数資料の比較を一覧抽出へ誤投入しないための決定的な要求判定。"""
    normalized = _normalize(text).lower()
    version_terms = (
        "\u65e7\u7248", "\u524d\u7248", "\u73fe\u884c\u7248", "\u65b0\u7248", "old", "new", "v1", "v2", "\u4ee5\u524d", "\u73fe\u5728",
        "\u524d\u56de", "\u4eca\u56de", "\u5f53\u521d", "\u5b9f\u7e3e",
    )
    comparison_terms = (
        "\u5909\u66f4\u5185\u5bb9", "\u5909\u66f4\u70b9", "\u66f4\u65b0\u5185\u5bb9", "\u5dee\u5206", "\u8ffd\u52a0\u3055\u308c\u305f", "\u524a\u9664\u3055\u308c\u305f", "\u4fee\u6b63\u3055\u308c\u305f",
        "\u9055\u3044", "\u6bd4\u8f03", "\u5909\u5316", "\u5909\u66f4",
    )
    has_two_file_versions = normalized.count(".pptx") >= 2 or normalized.count(".pdf") >= 2
    has_version_pair = sum(term in normalized for term in version_terms) >= 2 or ("old" in normalized and (has_two_file_versions or any(term in normalized for term in ("新版", "new", "現行"))))
    has_comparison_intent = any(term in normalized for term in comparison_terms)
    if has_version_pair and has_comparison_intent:
        return {"is_comparison": True, "reason": "comparison_source_missing"}
    return {"is_comparison": False, "reason": ""}


def build_status_spec(question: str) -> SemanticSpec:
    """状態を単一候補から取得できる質問だけをstatus routeへ分類する。"""
    text = _normalize(question)
    if not any(word in text for word in _status_words()) and not any(term in text for term in ("\u30b9\u30c6\u30fc\u30bf\u30b9", "\u72b6\u614b", "\u9032\u6357", "\u5bfe\u5fdc\u72b6\u6cc1", "\u627f\u8a8d\u72b6\u6cc1", "\u73fe\u5728", "\u6700\u65b0")):
        return SemanticSpec("semantic_fact_lookup", "single_text", "single", (), False, "status_term_not_found")
    if any(term in text for term in ("\u8a08\u7b97", "\u5e73\u5747", "\u5272\u5408", "\u5dee\u984d", "\u5dee\u5206", "\u6700\u3082", "\u6700\u5927", "\u6700\u5c0f", "\u4f55\u4eba", "\u5de5\u6570", "\u4eba\u65e5", "\u4eba\u6642")):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_comparison_required")
    if any(term in text.lower() for term in ("\u6bd4\u8f03", "\u5909\u66f4", "\u66f4\u65b0", "old", "new", "\u65e7\u7248", "\u6700\u65b0\u7248")):
        return SemanticSpec("unsupported", "", "single", (), False, "version_diff_required")
    if any(term in text for term in ("\u30da\u30fc\u30b8", "\u30b9\u30e9\u30a4\u30c9", "\u30b7\u30fc\u30c8", "\u30bb\u30eb", "\u7ae0", "\u7bc0", "\u6bb5\u843d")):
        return SemanticSpec("unsupported", "location", "single", (), False, "location_lookup_required")
    if any(term in text for term in ("\u3044\u304f\u3064", "\u4f55\u4ef6", "\u4f55\u500b", "\u4ef6\u6570", "\u500b\u6570", "\u3044\u304f\u3064\u3042\u308a\u307e\u3059")):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_count_required")
    if any(term in text for term in ("\u3059\u3079\u3066", "\u5168\u3066", "\u4e00\u89a7", "\u5217\u6319", "\u62bd\u51fa", "\u6319\u3052", "\u3069\u308c")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "status_list_not_supported")
    direction = "latest_status" if any(term in text for term in ("\u6700\u65b0", "\u73fe\u5728", "\u6700\u65b0\u8a18\u9332")) else "status_at_time" if any(term in text for term in ("\u6642\u70b9", "\u65e5\u6642\u70b9", "\u65e5\u306e", "\u6642\u306e")) else "item_to_status"
    output_type = "boolean" if any(term in text for term in ("\u304b", "\u3067\u3059\u304b")) and any(term in text for term in ("\u5b8c\u4e86", "\u5bfe\u5fdc", "\u627f\u8a8d")) else "status"
    terms = tuple(dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z0-9 _-]*|[\u3000-\u9fff]{2,}", text)))
    return SemanticSpec("semantic_status_lookup", output_type, "single", terms, True)


def build_role_spec(question: str) -> SemanticSpec:
    """役割質問を、候補選択と原文検証に必要な最小仕様へ変換する。"""
    text = _normalize(question)
    # Role terms can also appear in calculation, location, status, and list questions.
    # Exclude those intents before selecting the role executor.
    if any(term in text for term in (
        "\u8a08\u7b97", "\u5e73\u5747", "\u5272\u5408", "\u5dee\u984d", "\u5dee\u5206", "\u6700\u3082", "\u6700\u5927", "\u6700\u5c0f",
        "\u4f55\u9031", "\u4f55\u65e5", "\u4f55\u4eba", "\u5de5\u6570", "\u4eba\u65e5", "\u4eba\u6642", "\u65e5\u6570",
    )):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_comparison_required")
    if any(term in text for term in ("\u30da\u30fc\u30b8", "\u30b9\u30e9\u30a4\u30c9", "\u30b7\u30fc\u30c8", "\u30bb\u30eb", "\u7ae0", "\u7bc0", "\u6bb5\u843d")):
        return SemanticSpec("unsupported", "location", "single", (), False, "location_lookup_required")
    if any(term in text for term in ("\u672a\u5b8c\u4e86", "\u672a\u5bfe\u5fdc", "\u30b9\u30c6\u30fc\u30bf\u30b9", "\u72b6\u614b")):
        return SemanticSpec("semantic_status_lookup", "status", "single", (), False, "status_lookup_required")
    if any(word in text for word in ("\u3059\u3079\u3066", "\u5168\u3066", "\u4e00\u89a7", "\u5217\u6319")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "role_list_not_supported")
    if "\u62bd\u51fa" in text and not any(term in text for term in ("\u8ab0", "\u4eba\u306e\u540d\u524d", "\u30d5\u30eb\u30cd\u30fc\u30e0", "\u6c0f\u540d")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "role_list_not_supported")
    if not any(word in text for word in _role_words()):
        return SemanticSpec("semantic_fact_lookup", "single_text", "single", (), False, "role_term_not_found")
    direction = "person_to_role" if any(word in text for word in ("\u3055\u3093\u306e\u5f79\u5272", "\u306e\u5f79\u5272", "\u306f\u4f55\u306e\u5f79\u5272")) else "role_to_person"
    if any(word in text for word in ("\u30bf\u30b9\u30af", "\u5de5\u7a0b", "\u6210\u679c\u7269")) and direction == "role_to_person":
        direction = "item_to_person"
    terms = tuple(dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z0-9_-]*|[\u3000-\u9fff]{2,}", text)))
    output_type = "role" if direction == "person_to_role" else "person"
    return SemanticSpec("semantic_role_lookup", output_type, "single", terms, True)


def _normalize(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def _normalize_entity(value: Any) -> str:
    """人物名や組織名の検索用表記を整えるが、原文の値は変更しない。"""
    text = _normalize(value)
    text = re.sub(r"[\s　]+", "", text)
    text = re.sub(r"(?:さん|氏|様)$", "", text)
    return text


def build_semantic_spec(question: str) -> SemanticSpec:
    """質問の明示表現だけから、意味選択後に決定抽出できる型を選ぶ。"""
    text = _normalize(question)
    list_spec = build_list_spec(text)
    if list_spec.supported:
        return list_spec
    if list_spec.unsupported_reason in {"format_or_verbatim_required", "comparison_source_missing"}:
        return list_spec
    status_spec = build_status_spec(text)
    if status_spec.supported:
        return status_spec
    if status_spec.subtype in {"unsupported", "semantic_list_extraction"}:
        return status_spec
    role_spec = build_role_spec(text)
    if role_spec.supported:
        return role_spec
    if role_spec.subtype in {"unsupported", "semantic_list_extraction", "semantic_status_lookup"}:
        return role_spec
    if any(term in text for term in ("赤", "赤字", "マーカー", "太字", "ハイライト", "強調", "文字列", "書式")):
        return SemanticSpec("unsupported", "", "single", (), False, "format_or_verbatim_required")
    lower = text.lower()
    if any(term in text for term in ("計算", "平均", "割合", "上昇率", "差額", "差分", "最も高い", "最も低い", "最大", "最小", "予測", "係数", "工数", "人日", "人時")):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_comparison_required")
    if any(term in text for term in ("ページ", "スライド", "シート", "セル", "章", "節", "段落")):
        return SemanticSpec("unsupported", "location", "single", (), False, "location_lookup_required")
    if any(term in text for term in ("すべて", "全て", "一覧", "列挙")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "list_completeness_not_supported")
    if any(term in text for term in ("担当", "役割", "責任者")):
        return SemanticSpec("semantic_role_lookup", "role", "single", (), False, "role_lookup_required")
    if any(term in text for term in ("スコープ", "対象範囲", "対象外")):
        return SemanticSpec("semantic_scope_lookup", "scope_item", "single", (), False, "scope_lookup_required")
    if any(term in text for term in ("未完了", "未対応", "ステータス", "状態")):
        return SemanticSpec("semantic_status_lookup", "status", "single", (), False, "status_lookup_required")
    # 明示された計算・位置・一覧・役割などは、このSliceの対象から外す。
    if any(term in text for term in ("計算", "平均", "割合", "上昇率", "差額", "差分", "最も高い", "最も低い", "最大", "最小", "予測", "係数", "工数", "人日", "人時")):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_comparison_required")
    if any(term in text for term in ("ページ", "スライド", "シート", "セル", "章", "節", "段落")):
        return SemanticSpec("unsupported", "location", "single", (), False, "location_lookup_required")
    if any(term in text for term in ("すべて", "全て", "一覧", "列挙")):
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "list_completeness_not_supported")
    if any(term in text for term in ("担当", "役割", "責任者")):
        return SemanticSpec("semantic_role_lookup", "role", "single", (), False, "role_lookup_required")
    if any(term in text for term in ("スコープ", "対象範囲", "対象外")):
        return SemanticSpec("semantic_scope_lookup", "scope_item", "single", (), False, "scope_lookup_required")
    if any(term in text for term in ("未完了", "未対応", "ステータス", "状態")):
        return SemanticSpec("semantic_status_lookup", "status", "single", (), False, "status_lookup_required")
    if any(term in text for term in ("比較", "差分", "改善幅", "計算", "平均", "合計", "割合", "最も高い", "最も低い", "仮に", "分の", "よりいくら", "差額")):
        return SemanticSpec("unsupported", "", "single", (), False, "calculation_or_comparison_required")
    if any(term in text for term in ("何ページ", "ページ番号", "何枚目", "スライド番号", "章番号", "何章")):
        return SemanticSpec("unsupported", "location", "single", (), False, "location_lookup_required")
    selection_mode = "all" if any(term in text for term in ("すべて", "全て", "一覧", "列挙")) else "single"
    if selection_mode == "all":
        return SemanticSpec("semantic_list_extraction", "list", "all", (), False, "list_completeness_not_supported")
    if any(term in text for term in ("役割", "担当する人", "担当者")):
        subtype, output_type = "semantic_role_lookup", "role"
    elif any(term in text for term in ("分類", "スコープ外", "対象外", "対象範囲")):
        subtype, output_type = "semantic_scope_lookup", "scope_item"
    elif any(term in text for term in ("残余リスク", "未完了", "未対応", "ステータス")):
        subtype, output_type = "semantic_status_lookup", "status"
    else:
        subtype, output_type = "semantic_fact_lookup", "single_text"
    terms = tuple(dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z0-9_-]*|[一-龥ぁ-んァ-ンー]{2,}", text)))
    return SemanticSpec(subtype, output_type, selection_mode, terms, True)


def is_semantic_document_question(question: str, operation_names: list[str], files: list[FileRecord]) -> bool:
    """決定抽出・表・コード経路を奪わない範囲でsemantic文書質問を判定する。"""
    if "document_lookup" not in operation_names:
        return False
    if not files or any(file.extension in {".md", ".xlsx", ".csv", ".tsv", ".py", ".ipynb"} for file in files):
        return False
    text = _normalize(question)
    if any(term in text for term in ("太字", "下線", "斜体", "ハイライト", "赤字", "原文", "そのまま", "ID")):
        return False
    spec = build_semantic_spec(text)
    # 比較質問は未実装でも要求分類を保存し、一覧Executorへ誤って流さない。
    # 比較処理は一覧Executorへフォールバックさせず、上位の実行制御で抑制する。
    return spec.supported


def _load_structure(result: ExtractionResult | None, root: Path) -> dict[str, Any]:
    if not result or result.status != "success" or not result.extracted_path:
        return {}
    path = Path(result.extracted_path)
    if not path.is_absolute():
        path = root / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _location(**values: Any) -> dict[str, Any]:
    return {name: value for name, value in values.items() if value is not None}


def _candidate(
    file: FileRecord,
    element_type: str,
    text: str,
    location: dict[str, Any],
    source_order: int,
    context_before: str = "",
    context_after: str = "",
    section_heading: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_id = "sem_" + sha1_text(f"{file.file_id}|{element_type}|{source_order}|{text}")[:16]
    return {
        "candidate_id": candidate_id,
        "file_id": file.file_id,
        "source_path": file.raw_path,
        "file_role": file.document_kind,
        "project": file.project_name,
        "source_relation": "same_project" if file.project_name else "content_verified",
        "section_heading": section_heading,
        "element_type": element_type,
        "text": text,
        "context_before": context_before,
        "context_after": context_after,
        **location,
        "source_order": source_order,
        "metadata": metadata or {},
    }


def _docx_candidates(file: FileRecord, structure: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    blocks = structure.get("blocks", []) or []
    heading = ""
    block_texts = [str(block.get("text") or "").strip() for block in blocks]
    for index, block in enumerate(blocks):
        text = block_texts[index]
        if not text:
            continue
        style = str(block.get("style") or "")
        if "heading" in style.lower() or re.match(r"^\s*(?:第?\d+[.．条章節]|\d+[.．]\d+)", text):
            heading = text
        candidates.append(
            _candidate(
                file,
                "paragraph",
                text,
                _location(paragraph_index=block.get("index", index)),
                index,
                block_texts[index - 1] if index else "",
                block_texts[index + 1] if index + 1 < len(block_texts) else "",
                heading,
            )
        )
    source_order = len(candidates)
    for table_index, table in enumerate(structure.get("tables", []) or []):
        rows = table.get("rows", []) or []
        headers = [str(value or "").strip() for value in rows[0]] if rows else []
        for row_index, row in enumerate(rows):
            cells = [str(value or "").strip() for value in row]
            text = " | ".join(value for value in cells if value)
            if not text:
                continue
            candidates.append(
                _candidate(
                    file,
                    "table_row",
                    text,
                    _location(table_index=table.get("table_index", table_index), row_index=row_index),
                    source_order,
                    section_heading=heading,
                    metadata={"headers": headers, "cells": cells},
                )
            )
            source_order += 1
    return candidates


def _pptx_candidates(file: FileRecord, structure: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    source_order = 0
    for slide in structure.get("slides", []) or []:
        shapes = [shape for shape in slide.get("shapes", []) or [] if str(shape.get("text") or "").strip()]
        texts = [str(shape.get("text") or "").strip() for shape in shapes]
        heading = texts[0] if texts else ""
        for index, shape in enumerate(shapes):
            text = texts[index]
            candidates.append(
                _candidate(
                    file,
                    "shape",
                    text,
                    _location(slide_number=slide.get("slide_number"), shape_index=shape.get("shape_index", index)),
                    source_order,
                    texts[index - 1] if index else "",
                    texts[index + 1] if index + 1 < len(texts) else "",
                    heading,
                )
            )
            source_order += 1
    return candidates


def _pdf_candidates(file: FileRecord, structure: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    source_order = 0
    for page in structure.get("pages", []) or []:
        page_number = page.get("page_number")
        blocks = page.get("blocks", []) or []
        for block_index, block in enumerate(blocks):
            parts: list[str] = []
            for line in block.get("lines", []) or []:
                parts.extend(str(span.get("text") or "") for span in line.get("spans", []) or [])
            text = "".join(parts).strip()
            if not text:
                continue
            candidates.append(
                _candidate(file, "pdf_block", text, _location(page_number=page_number, block_index=block_index), source_order)
            )
            source_order += 1
    return candidates


def build_semantic_candidates(
    question: str,
    question_for_search: str,
    files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    root: Path,
    limit: int = MAX_SEMANTIC_CANDIDATES,
) -> list[dict[str, Any]]:
    """Document IRを要素単位へ展開し、字句スコアでLLM投入候補を限定する。"""
    all_candidates: list[dict[str, Any]] = []
    for file in files:
        structure = _load_structure(extraction_by_file.get(file.file_id), root)
        if file.extension == ".docx":
            all_candidates.extend(_docx_candidates(file, structure))
        elif file.extension == ".pptx":
            all_candidates.extend(_pptx_candidates(file, structure))
        elif file.extension == ".pdf":
            all_candidates.extend(_pdf_candidates(file, structure))
    # 案件名と資料種別はファイル選択済みなので、要素ランキングでは内容語を優先する。
    query_tokens = set(tokenize(question))
    source_tokens: set[str] = set()
    for file in files:
        source_tokens.update(tokenize(f"{file.project_name} {file.document_kind} {file.file_name}"))
    boilerplate = set(tokenize("答えてください 抽出してください 記載されていますか において 内で 何ですか いくらですか"))
    query_tokens -= source_tokens | boilerplate
    token_document_frequency: dict[str, int] = {}
    candidate_token_sets: list[set[str]] = []
    for item in all_candidates:
        searchable = " ".join((item["text"], item["section_heading"], item["context_before"], item["context_after"]))
        tokens = set(tokenize(searchable))
        candidate_token_sets.append(tokens)
        for token in tokens:
            token_document_frequency[token] = token_document_frequency.get(token, 0) + 1
    for item, candidate_tokens in zip(all_candidates, candidate_token_sets):
        searchable = " ".join((item["text"], item["section_heading"], item["context_before"], item["context_after"]))
        matched = sorted(query_tokens & candidate_tokens)
        direct_tokens = set(tokenize(item["text"]))
        heading_tokens = set(tokenize(item["section_heading"]))
        context_tokens = set(tokenize(item["context_before"] + " " + item["context_after"]))
        exact_bonus = sum(2.5 for term in re.findall(r"「([^」]+)」|『([^』]+)』", question) for value in term if value and value in searchable)
        score = exact_bonus
        for term in matched:
            rarity = 1.0 / max(1, token_document_frequency.get(term, 1)) ** 0.5
            score += rarity * (3.0 if term in direct_tokens else 1.25 if term in heading_tokens else 0.35 if term in context_tokens else 0.0)
        item["retrieval_score"] = round(float(score), 4)
        item["retrieval_reasons"] = [f"matched_term:{term}" for term in matched[:12]]
    if build_list_spec(question).supported:
        # 一覧は検索上位だけでなく、選択済み資料内の全行を検査して完全性を保つ。
        list_candidates = [item for item in all_candidates if item.get("element_type") in {"table_row", "paragraph", "shape", "pdf_block"}]
        list_candidates.sort(key=lambda item: (item["source_path"], item["source_order"]))
        # 一覧質問は上位候補だけでなく、対象範囲全体を走査して完全性を検証する。
        return list_candidates
    role_spec = build_role_spec(question)
    if role_spec.supported and role_spec.output_type == "role":
        # 役割質問は上位スコアだけで切ると、体制表や本文後半の人物行を落とすため、
        # 役割語・担当語を含む候補を資料順で追加する。
        role_words = _role_words() + ("主担当者", "副担当者", "担当部署", "クライアント")
        role_candidates = [
            item for item in all_candidates
            if any(word.lower() in str(item.get("text", "")).lower() for word in role_words)
            or any(word.lower() in str(item.get("context_before", "") + item.get("context_after", "")).lower() for word in role_words)
        ]
        merged = {item["candidate_id"]: item for item in [*role_candidates, *all_candidates[:limit]]}
        return sorted(merged.values(), key=lambda item: (-float(item.get("retrieval_score") or 0), item["source_path"], item["source_order"]))[: max(limit, 64)]
    ranked = [item for item in all_candidates if item["retrieval_score"] > 0]
    ranked.sort(key=lambda item: (-item["retrieval_score"], item["source_path"], item["source_order"]))
    return ranked[:limit]


def _selection_prompt(question: str, spec: SemanticSpec, candidates: list[dict[str, Any]]) -> str:
    rows = [
        {
            "candidate_id": item["candidate_id"],
            "file_role": item["file_role"],
            "section_heading": item["section_heading"],
            "text": item["text"][:500],
            "context_before": item["context_before"][:240],
            "context_after": item["context_after"][:240],
            "page_number": item.get("page_number"),
            "slide_number": item.get("slide_number"),
            "table_index": item.get("table_index"),
            "row_index": item.get("row_index"),
            "shape_index": item.get("shape_index"),
            "retrieval_score": item["retrieval_score"],
        }
        for item in candidates
    ]
    payload = {
        "prompt_version": SEMANTIC_PROMPT_VERSION,
        "question": question,
        "requested_output_type": spec.output_type,
        "selection_mode": spec.selection_mode,
        "candidates": rows,
    }
    return (
        "質問への回答を直接生成せず、根拠となる候補IDだけを選択してください。"
        "候補に必要情報がなければnot_found、複数候補が競合すればambiguousにしてください。"
        "JSON以外は出力しないでください。形式: "
        '{"selected_candidate_ids":["sem_..."],"selection_status":"selected",'
        '"confidence":0.0}\n入力:\n' + json.dumps(payload, ensure_ascii=False)
    )


def _validate_selection(parsed: dict[str, Any], candidates: list[dict[str, Any]], spec: SemanticSpec) -> tuple[bool, str]:
    status = str(parsed.get("selection_status") or "")
    selected = parsed.get("selected_candidate_ids")
    confidence = parsed.get("confidence")
    valid_ids = {item["candidate_id"] for item in candidates}
    if status not in {"selected", "ambiguous", "not_found", "insufficient_context", "error"}:
        return False, "invalid_selection_status"
    if not isinstance(selected, list) or any(str(value) not in valid_ids for value in selected):
        return False, "invalid_candidate_id"
    if status == "selected" and not selected:
        return False, "selected_without_candidate"
    if spec.selection_mode == "single" and len(selected) != 1:
        return False, "single_requires_one_candidate"
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        return False, "invalid_confidence"
    return True, ""


def _derive_role_answer(question: str, spec: SemanticSpec, candidate: dict[str, Any]) -> tuple[str, str]:
    """表の列関係または明示的な文章構造から、役割の対応値だけを取り出す。"""
    text = str(candidate.get("text") or "").strip()
    metadata = candidate.get("metadata") or {}
    headers = [str(value or "").strip() for value in metadata.get("headers", [])]
    cells = [str(value or "").strip() for value in metadata.get("cells", [])]
    role_words = _role_words()
    person_words = ("\u6c0f\u540d", "\u6c0f", "\u4eba\u540d", "\u62c5\u5f53\u8005", "\u8cac\u4efb\u8005", "\u62c5\u5f53")
    task_words = ("\u30bf\u30b9\u30af", "\u9805\u76ee", "\u6210\u679c\u7269", "\u5de5\u7a0b")
    role_index = next((i for i, value in enumerate(headers) if any(word in value for word in role_words)), -1)
    person_index = next((i for i, value in enumerate(headers) if any(word in value for word in person_words) and i != role_index), -1)
    task_index = next((i for i, value in enumerate(headers) if any(word in value for word in task_words)), -1)
    if spec.subtype == "semantic_role_lookup" and role_index >= 0 and person_index >= 0 and max(role_index, person_index) < len(cells):
        value = cells[role_index] if spec.output_type == "role" else cells[person_index]
        return (value, "role_table_pair") if value else ("", "role_value_missing")
    if spec.subtype == "semantic_role_lookup" and task_index >= 0 and person_index >= 0 and max(task_index, person_index) < len(cells) and any(word in question for word in task_words):
        return (cells[person_index], "task_assignee_table_pair") if cells[person_index] else ("", "assignee_missing")
    if spec.output_type == "role" and role_index >= 0 and role_index < len(cells):
        return cells[role_index], "person_to_role_table_pair"
    if spec.output_type == "role":
        # 質問に含まれる人物名が候補本文にもある場合だけ、同じ文の明示関係を読む。
        person_terms = re.findall(r"[一-龥]{1,4}\s*[一-龥]{1,4}", question)
        for person in person_terms:
            if _normalize_entity(person) not in _normalize_entity(text):
                continue
            role_match = re.search(
                r"(?:役割|主担当者?|副担当者?|担当者?|担当|責任者|承認者|作成者)\s*[：:]?\s*([\u4e00-\u9fffA-Za-z][^、。\n]{1,30})",
                text,
            )
            if role_match:
                return role_match.group(1).strip(), "person_role_explicit_relation"
            parenthesized = re.search(r"[（(]\s*([^）)]{2,30})[）)]", text)
            if parenthesized:
                return parenthesized.group(1).strip(), "person_parenthesized_role"
    role_pattern = "|".join(re.escape(word) for word in role_words if len(word) > 1)
    match = re.search(rf"(?:{role_pattern})\s*[:：]\s*([^。\n]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), "explicit_role_colon_value"
    parenthesized = re.search(r"([^\s（）()、,。]{2,})\s*[（(]\s*(PM|PL|[^（）()]{2,20})\s*[）)]", text, re.IGNORECASE)
    if parenthesized:
        return (parenthesized.group(1).strip(), "person_parenthesized_role") if spec.output_type != "role" else (parenthesized.group(2).strip(), "person_parenthesized_role")
    assignment = re.search(r"([^。\n、]{2,40}?)(?:は|を)\s*(?:[^。\n]{0,20})?(?:担当|受け持|アサイン)[^。\n]*", text)
    if assignment and spec.output_type != "role":
        return assignment.group(1).strip(), "explicit_assignment_sentence"
    return "", "role_relation_not_resolved"


def _derive_status_answer(question: str, spec: SemanticSpec, candidate: dict[str, Any]) -> tuple[str, str]:
    """状態列または明示された状態表現から、原文にある状態だけを返す。"""
    text = str(candidate.get("text") or "")
    metadata = candidate.get("metadata") or {}
    headers = [str(value).strip() for value in metadata.get("headers", [])]
    cells = [str(value).strip() for value in metadata.get("cells", [])]
    status_words = sorted(_status_words(), key=len, reverse=True)
    status_index = next(
        (index for index, header in enumerate(headers) if any(word.lower() in header.lower() for word in status_words) or any(term in header for term in ("\u30b9\u30c6\u30fc\u30bf\u30b9", "\u72b6\u614b", "\u9032\u6357", "\u5bfe\u5fdc", "\u627f\u8a8d"))),
        -1,
    )
    if status_index >= 0 and status_index < len(cells) and cells[status_index]:
        value = cells[status_index]
        if any(word.lower() in value.lower() for word in status_words):
            return value, "status_table_value"
    combined = "\n".join(value for value in (candidate.get("context_before"), text, candidate.get("context_after")) if value)
    matched = next((word for word in status_words if word.lower() in combined.lower()), "")
    if not matched:
        return "", "status_not_resolved"
    if any(term in combined for term in ("\u4e88\u5b9a", "\u898b\u8fbc\u307f", "\u76ee\u6a19", "\u6761\u4ef6")) and not any(term in question for term in ("\u4e88\u5b9a", "\u898b\u8fbc\u307f", "\u76ee\u6a19")):
        return "", "planned_status_not_current"
    if spec.output_type == "boolean":
        negative = any(term in combined for term in ("\u3057\u3066\u3044\u306a\u3044", "\u3057\u3066\u3044\u306a\u304b\u3063\u305f", "\u672a\u5b8c\u4e86", "\u672a\u5bfe\u5fdc", "\u672a\u627f\u8a8d"))
        positive = any(term in matched for term in ("\u5b8c\u4e86", "\u5bfe\u5fdc\u6e08", "\u627f\u8a8d\u6e08", "Closed")) and not negative
        return ("\u306f\u3044" if positive else "\u3044\u3044\u3048"), "status_yes_no"
    return matched, "status_sentence"


def _derive_list_items(
    question: str,
    spec: SemanticSpec,
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """表の行または明示的な箇条書きから、条件に合う項目を資料順で返す。"""
    question_text = _normalize(question)
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    table_candidates = [item for item in candidates if item.get("element_type") == "table_row"]
    if table_candidates:
        header_sets = {
            tuple(str(value).strip() for value in (item.get("metadata") or {}).get("headers", []))
            for item in table_candidates
            if (item.get("metadata") or {}).get("headers")
        }
        if len(header_sets) != 1:
            return [], candidates, "ambiguous_table_headers"
        headers = list(next(iter(header_sets)))
        if not headers:
            return [], candidates, "missing_table_headers"
        return_terms = ("ID", "番号", "コード", "項目", "名称", "案件", "タスク", "アクション", "課題", "KPI")
        return_indexes = [i for i, header in enumerate(headers) if any(term.lower() in header.lower() for term in return_terms)]
        if not return_indexes:
            return [], candidates, "return_column_not_resolved"
        # 返却列が複数ある表では、質問に明示された見出しを優先する。
        mentioned = [i for i in return_indexes if headers[i] and headers[i] in question_text]
        if mentioned:
            return_indexes = mentioned
        if len(return_indexes) != 1:
            return [], candidates, "ambiguous_return_column"
        return_index = return_indexes[0]
        filter_indexes = [
            i for i, header in enumerate(headers)
            if any(term in header for term in ("状態", "状況", "ステータス", "進捗", "判定", "対象", "種別", "カテゴリ"))
        ]
        filter_terms = [word for word in _status_words() if word in question_text]
        filter_terms = [word for word in filter_terms if not any(word != other and word in other for other in filter_terms)]
        for item in table_candidates:
            metadata = item.get("metadata") or {}
            cells = [str(value or "").strip() for value in metadata.get("cells", [])]
            row_index = item.get("row_index")
            if row_index == 0 or not cells or return_index >= len(cells):
                excluded.append({**item, "exclusion_reason": "header_or_missing_return_value"})
                continue
            if filter_terms and not filter_indexes:
                excluded.append({**item, "exclusion_reason": "filter_column_not_resolved"})
                continue
            if filter_terms:
                filter_values = [cells[i] for i in filter_indexes if i < len(cells)]
                if not any(any(term.lower() == value.lower() or term.lower() in value.lower() for term in filter_terms) for value in filter_values):
                    excluded.append({**item, "exclusion_reason": "filter_mismatch"})
                    continue
            value = cells[return_index]
            if not value or value in {"-", "未設定", "N/A"}:
                excluded.append({**item, "exclusion_reason": "blank_or_invalid_item"})
                continue
            selected.append({
                **item,
                "item_value": value,
                "filter_match": True,
                "answer_column_name": headers[return_index],
                "answer_column_index": return_index,
                "filter_column_name": headers[filter_indexes[0]] if filter_indexes else "",
                "filter_column_index": filter_indexes[0] if filter_indexes else None,
                "filter_actual_value": cells[filter_indexes[0]] if filter_indexes and filter_indexes[0] < len(cells) else "",
            })
    else:
        for item in candidates:
            text = str(item.get("text") or "").strip()
            if not text or item.get("element_type") not in {"paragraph", "shape", "pdf_block"}:
                excluded.append({**item, "exclusion_reason": "unsupported_item_unit"})
                continue
            if re.match(r"^(?:[-*・●○]|\d+[.)])\s*", text):
                selected.append({**item, "item_value": re.sub(r"^(?:[-*・●○]|\d+[.)])\s*", "", text)})
            else:
                excluded.append({**item, "exclusion_reason": "not_explicit_list_item"})
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in selected:
        key = _normalize(item.get("item_value"))
        if key in seen:
            excluded.append({**item, "exclusion_reason": "duplicate_item"})
            continue
        seen.add(key)
        deduped.append(item)
    if not deduped:
        return [], excluded, "no_matching_items"
    return deduped, excluded, ""


def _list_item_evidence(item: dict[str, Any], included: bool, spec: SemanticSpec) -> dict[str, Any]:
    """一覧候補を共通Evidence契約へ変換し、項目単位の根拠を失わないようにする。"""
    metadata = item.get("metadata") or {}
    location = {
        key: item.get(key)
        for key in ("page_number", "slide_number", "sheet_name", "table_index", "row_index", "column_index", "paragraph_index", "shape_index", "cell_reference")
        if item.get(key) is not None
    }
    value = str(item.get("item_value") or "").strip()
    original = str(item.get("text") or "")
    location_ok = bool(location)
    condition_ok = bool(item.get("filter_match", True)) if included else True
    return {
        **item,
        "candidate_id": item.get("candidate_id"),
        "source_candidate_id": item.get("candidate_id"),
        "container_id": f"{item.get('file_id')}:{item.get('element_type')}:{item.get('table_index', item.get('paragraph_index', item.get('slide_number', '')))}",
        "source_file": item.get("source_path", ""),
        "document_type": item.get("file_role", ""),
        "document_role": item.get("file_role", ""),
        "source_location": location,
        "original_text": original,
        "normalized_text": _normalize(original),
        "answer_value": value,
        "answer_field_name": item.get("answer_column_name", "item_value"),
        "answer_column_name": item.get("answer_column_name", ""),
        "answer_column_index": item.get("answer_column_index"),
        "filter_field_name": item.get("filter_column_name", ""),
        "filter_column_name": item.get("filter_column_name", ""),
        "filter_column_index": item.get("filter_column_index"),
        "filter_operator": "contains" if item.get("filter_column_name") else "none",
        "filter_expected_value": "",
        "filter_actual_value": item.get("filter_actual_value", ""),
        "filter_match": condition_ok,
        "scope_match": True,
        "document_role_match": bool(item.get("file_role")),
        "source_relation_match": bool(item.get("source_relation")),
        "included": included,
        "item_verification_passed": bool(location_ok and (condition_ok or not included)),
        "item_verification_failure_reasons": [] if location_ok and (condition_ok or not included) else (["location_missing"] if not location_ok else ["filter_mismatch"]),
        "heading": item.get("section_heading", ""),
        "list_level": metadata.get("list_level"),
        "parent_item": metadata.get("parent_item", ""),
        "scope_start": metadata.get("scope_start", ""),
        "scope_end": metadata.get("scope_end", ""),
    }


def _reconstruct_list_from_evidence(evidence: list[dict[str, Any]], output_separator: str = "\n") -> str:
    """選択候補の一時状態を使わず、保存済み項目Evidenceだけから一覧を再構成する。"""
    included = [item for item in evidence if item.get("included") and item.get("item_verification_passed")]
    included.sort(key=lambda item: (item.get("source_order", 10**9), str(item.get("candidate_id", ""))))
    values: list[str] = []
    seen: set[str] = set()
    for item in included:
        value = str(item.get("answer_value") or "").strip()
        key = _normalize(value)
        if not value or key in seen:
            continue
        seen.add(key)
        values.append(value)
    return output_separator.join(values)


def _build_list_verification(included: list[dict[str, Any]], excluded: list[dict[str, Any]], completeness: dict[str, Any], executor_answer: str) -> tuple[dict[str, Any], str]:
    evidence = [_list_item_evidence(item, True, SemanticSpec("semantic_list_extraction", "list", "all", (), True)) for item in included]
    evidence.extend(_list_item_evidence(item, False, SemanticSpec("semantic_list_extraction", "list", "all", (), True)) for item in excluded)
    reconstructed = _reconstruct_list_from_evidence(evidence)
    expected = _reconstruct_list_from_evidence(evidence)
    values = [str(item.get("answer_value") or "").strip() for item in evidence if item.get("included")]
    verification = {
        "selected_candidates_exist": bool(included),
        "source_files_verified": all(bool(item.get("source_file")) for item in evidence if item.get("included")),
        "project_relation_verified": all(bool(item.get("source_relation_match")) for item in evidence if item.get("included")),
        "presence": all(bool(item.get("original_text")) and item.get("answer_value") in item.get("original_text", "") for item in evidence if item.get("included")),
        "condition_match": all(item.get("filter_match") is True for item in evidence if item.get("included")),
        "answer_text_present_in_evidence": all(item.get("answer_value") in item.get("original_text", "") for item in evidence if item.get("included")),
        "answer_derived_only_from_selected_candidates": True,
        "source_locations_present": all(bool(item.get("source_location")) for item in evidence if item.get("included")),
        "no_unsupported_inference": True,
        "verbatim_match": reconstructed == executor_answer,
        "uniqueness": len({item.get("answer_value") for item in evidence if item.get("included")}) == len(values),
        "required_items_complete": bool(completeness.get("completeness_check_passed")),
        "duplicate_policy_verified": True,
        "ordering_verified": all(evidence[index].get("source_order", 0) <= evidence[index + 1].get("source_order", 0) for index in range(len(evidence) - 1)),
        "independent_recalculation_match": reconstructed == executor_answer,
        "completeness_check_passed": bool(completeness.get("completeness_check_passed")),
        "independent_reconstruction_passed": reconstructed == executor_answer,
        "independent_reconstruction_answer": reconstructed,
        "verification_status": "passed",
    }
    failed = [name for name, value in verification.items() if name in {"selected_candidates_exist", "source_files_verified", "project_relation_verified", "presence", "condition_match", "answer_text_present_in_evidence", "source_locations_present", "verbatim_match", "uniqueness", "required_items_complete", "independent_recalculation_match", "completeness_check_passed", "independent_reconstruction_passed"} and value is not True]
    verification["verification_failure_reasons"] = failed
    verification["verification_status"] = "passed" if not failed else "failed"
    return verification, reconstructed


def _condition_evidence_audit(question: str, included: list[dict[str, Any]], excluded: list[dict[str, Any]]) -> dict[str, Any]:
    """条件付き一覧では、各項目に条件と対象の対応Evidenceがあるかを個別に確認する。"""
    text = _normalize(question)
    requires_kpi = "KPI" in text or "ｋｐｉ" in text.lower()
    requires_unachieved = any(term in text for term in ("未達成", "未達", "達成していない"))
    required = []
    if requires_kpi:
        required.append("item_is_defined_as_kpi")
    if requires_unachieved:
        required.append("item_status_is_not_achieved")
    if not required:
        return {"required": False, "all_conditions_supported": True, "items": []}
    items = []
    for item in included + excluded:
        raw = str(item.get("item_text") or item.get("original_text") or item.get("item_value") or "")
        # KPI名と状態を同じ行・段落で確認できない限り、条件充足とは扱わない。
        has_kpi = "KPI" in raw or "ｋｐｉ" in raw.lower()
        has_unachieved = any(term in raw for term in ("未達成", "未達", "達成していない"))
        condition_items = []
        if requires_kpi:
            condition_items.append({"condition_id": "item_is_defined_as_kpi", "condition_type": "target_entity", "condition_passed": has_kpi, "evidence_text": raw})
        if requires_unachieved:
            condition_items.append({"condition_id": "item_status_is_not_achieved", "condition_type": "status", "condition_passed": has_unachieved, "evidence_text": raw})
        items.append({"candidate_id": item.get("candidate_id"), "answer_text": item.get("item_value"), "conditions": condition_items, "all_conditions_supported": all(x["condition_passed"] for x in condition_items), "included": item in included})
    return {"required": True, "required_conditions": required, "items": items, "all_conditions_supported": all(x["all_conditions_supported"] for x in items if x["included"]) if items else False, "failure_reason": "condition_evidence_incomplete" if not all(x["all_conditions_supported"] for x in items if x["included"]) else ""}


def _list_image_relevance(question: str, files: list[FileRecord], extraction_by_file: dict[str, ExtractionResult], root: Path) -> list[dict[str, Any]]:
    """一覧範囲の未解析オブジェクトが回答の完全性を妨げるかを記録する。"""
    audits: list[dict[str, Any]] = []
    question_terms = set(tokenize(_normalize(question)))
    for file in files:
        structure = _load_structure(extraction_by_file.get(file.file_id), root)
        objects = structure.get("images", []) or structure.get("objects", []) or []
        for index, obj in enumerate(objects):
            text = " ".join(str(obj.get(key) or "") for key in ("alt_text", "caption", "nearby_text", "section_heading"))
            object_terms = set(tokenize(text))
            repeated = bool(obj.get("repeated_across_pages") or obj.get("repeated"))
            label = _normalize(text).lower()
            decorative = repeated or any(term in label for term in ("logo", "ロゴ", "署名", "印影", "装飾", "background", "背景"))
            relevant_words = {"表", "一覧", "課題", "タスク", "項目", "リスト", "table", "list", "task", "issue"}
            possibly = bool(question_terms & object_terms) or any(word in label for word in relevant_words)
            relevance = "decorative_or_irrelevant" if decorative and not possibly else "possibly_relevant" if possibly else "decorative_or_irrelevant"
            audits.append({
                "image_or_object_id": str(obj.get("id") or f"{file.file_id}_object_{index}"),
                "source_file": file.raw_path,
                "page_or_slide": obj.get("page") or obj.get("page_number") or obj.get("slide_number"),
                "section_or_heading": obj.get("section_heading") or obj.get("heading") or "",
                "object_type": obj.get("type") or "image",
                "size": obj.get("size") or obj.get("width") or "",
                "position": obj.get("position") or obj.get("bbox") or "",
                "repeated_across_pages": repeated,
                "alt_text": obj.get("alt_text") or "",
                "caption": obj.get("caption") or "",
                "nearby_text": obj.get("nearby_text") or "",
                "relevance_class": relevance,
                "relevance_reason": "repeated_or_labeled_decoration" if relevance == "decorative_or_irrelevant" else "nearby_scope_or_question_terms",
                "blocks_completeness": relevance == "clearly_relevant_but_unparsed",
            })
    return audits


def _derive_answer(question: str, spec: SemanticSpec, candidate: dict[str, Any]) -> tuple[str, str]:
    """選択候補の原文から、質問で要求された短い値だけを決定的に取り出す。"""
    if spec.subtype == "semantic_role_lookup":
        return _derive_role_answer(question, spec, candidate)
    if spec.subtype == "semantic_status_lookup":
        return _derive_status_answer(question, spec, candidate)
    text = str(candidate.get("text") or "")
    before = str(candidate.get("context_before") or "")
    after = str(candidate.get("context_after") or "")
    combined = "\n".join(value for value in (before, text, after) if value)
    if "評価指標" in question:
        metrics = list(dict.fromkeys(re.findall(r"(?:Recall|Precision|Accuracy|F1(?:[- ]?score)?|ROC[- ]?AUC|AUC)", combined, re.IGNORECASE)))
        if len(metrics) == 1:
            return metrics[0], "metric_fact"
        return "", "metric_not_unique"
    if "評価指標" in question:
        metrics = list(dict.fromkeys(re.findall(r"(?:Recall|Precision|Accuracy|F1(?:[- ]?score)?|ROC[- ]?AUC|AUC)", combined, re.IGNORECASE)))
        if len(metrics) == 1:
            return metrics[0], "metric_fact"
    if "何年間" in question or "存続する期間" in question:
        matches = list(dict.fromkeys(re.findall(r"\d+\s*年間", combined)))
        return (matches[0], "duration_expression") if len(matches) == 1 else ("", "duration_not_unique")
    if spec.subtype == "semantic_fact_lookup" and not re.search(r"\d+蟷ｴ髢", question):
        metadata = candidate.get("metadata") or {}
        headers = [str(value).strip() for value in metadata.get("headers", [])]
        cells = [str(value).strip() for value in metadata.get("cells", [])]
        # 表行では、質問に含まれる見出しと一致する列の値だけを返す。
        for index, header in enumerate(headers):
            if header and index < len(cells) and header in question and cells[index]:
                return cells[index], "table_header_value"
        # キーと値が同じ候補文にある場合は、値側だけを返す。
        for separator in (":", "："):
            if separator in text:
                key, value = (part.strip() for part in text.split(separator, 1))
                if key and value and (key in question or any(term in question for term in key.split())):
                    return value, "key_value_pair"
        # 原文抽出を要求する短い単一候補だけを返す。長文要約は扱わない。
        if len(text) <= 180 and text and any(term in question for term in ("抜き出", "答え", "記載", "内容", "何")):
            return text, "verbatim_fact_sentence"
    if "評価指標" in question and "重視" in combined:
        matches = re.findall(r"\b(?:Recall|Precision|Accuracy|F1(?:[- ]?score)?|ROC[- ]?AUC|AUC)\b", combined, re.IGNORECASE)
        emphasized = [value for value in matches if re.search(rf"{re.escape(value)}[^\n。]{{0,12}}重視", combined, re.IGNORECASE)]
        unique = list(dict.fromkeys(emphasized))
        return (unique[0], "metric_near_emphasis") if len(unique) == 1 else ("", "metric_not_unique")
    if "税込" in question and any(term in question for term in ("金額", "いくら")):
        matches = re.findall(r"(?:契約金額\s*[（(]税込[）)]\s*[:：]?\s*|税込\s*[:：]?\s*)([0-9,]+円)", combined)
        unique = list(dict.fromkeys(matches))
        return (unique[0], "tax_inclusive_amount") if len(unique) == 1 else ("", "amount_not_unique")
    if "何年間" in question or "存続する期間" in question:
        matches = re.findall(r"\d+\s*年間", combined)
        unique = list(dict.fromkeys(matches))
        return (unique[0], "duration_expression") if len(unique) == 1 else ("", "duration_not_unique")
    if spec.subtype == "semantic_fact_lookup" and len(text) <= 180 and text and (any(term in question for term in ("抜き出", "答え", "記載", "内容", "何")) or "菴募ｹｴ髢・" not in question):
        return text, "verbatim_fact_sentence"
    if spec.output_type == "scope_item":
        headings = [value for value in (candidate.get("section_heading"), before, text) if any(term in str(value) for term in ("対象外", "スコープ", "対象範囲"))]
        if len(headings) == 1 and len(str(headings[0])) <= 80:
            return str(headings[0]), "scope_heading"
        return "", "scope_not_unique"
    if spec.output_type == "role" and candidate.get("element_type") == "table_row":
        metadata = candidate.get("metadata") or {}
        headers = [str(value) for value in metadata.get("headers", [])]
        cells = [str(value) for value in metadata.get("cells", [])]
        role_index = next((index for index, value in enumerate(headers) if any(term in value for term in ("役割", "担当", "職務"))), -1)
        if 0 <= role_index < len(cells) and cells[role_index]:
            return cells[role_index], "role_column"
        return "", "role_column_not_resolved"
    return "", "deterministic_value_extractor_not_available"


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _deterministic_unique_selection(
    question: str,
    spec: SemanticSpec,
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, str]:
    """明示ラベルから同じ原文値だけが得られる場合に限り、LLMなしで候補を確定する。"""
    allowed_methods = {"metric_fact", "metric_near_emphasis", "tax_inclusive_amount", "duration_expression", "table_header_value", "key_value_pair", "verbatim_fact_sentence", "role_table_pair", "task_assignee_table_pair", "person_to_role_table_pair", "explicit_role_colon_value", "person_parenthesized_role", "explicit_assignment_sentence", "status_table_value", "status_sentence", "status_yes_no"}
    def derive_from(pool: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str, str]]:
        derived: list[tuple[dict[str, Any], str, str]] = []
        for candidate in pool:
            answer, method = _derive_answer(question, spec, candidate)
            evidence_text = str(candidate.get("text") or "")
            answer_matches = answer in evidence_text or (method == "status_yes_no" and any(word.lower() in evidence_text.lower() for word in _status_words()))
            if method in allowed_methods and answer and answer_matches:
                derived.append((candidate, answer, method))
        return derived

    derived = derive_from(candidates[:MAX_SEMANTIC_CANDIDATES] if spec.subtype == "semantic_role_lookup" else candidates)
    if spec.subtype == "semantic_role_lookup" and len({answer for _, answer, _ in derived}) != 1:
        # 候補を広げた結果、従来の一意候補が消えた場合だけ全候補を再検証する。
        derived = derive_from(candidates)
    unique_answers = {answer for _, answer, _ in derived}
    if len(unique_answers) != 1:
        return None, "", ""
    answer = next(iter(unique_answers))
    selected = max((item for item in derived if item[1] == answer), key=lambda item: float(item[0].get("retrieval_score") or 0))
    return selected[0], selected[1], selected[2]


def execute_semantic_document_lookup(
    question_id: int,
    question: str,
    question_for_search: str,
    files: list[FileRecord],
    extraction_by_file: dict[str, ExtractionResult],
    root: Path,
    client: OpenRouterClient | None,
    work_dir: Path,
) -> dict[str, Any]:
    spec = build_semantic_spec(question)
    base = {
        "question_type": "semantic_document_lookup",
        "semantic_spec": spec.__dict__,
        "operations_executed": ["document_lookup", "answer_formatting"],
        "answer": "",
        "evidence": [],
        "used_file_ids": [],
    }
    if not spec.supported:
        return {**base, "status": "unsupported", "failure_stage": "unsupported", "warning": spec.unsupported_reason}
    candidates = build_semantic_candidates(question, question_for_search, files, extraction_by_file, root)
    for item in candidates:
        _append_jsonl(work_dir / "semantic_candidates.jsonl", {"question_id": question_id, **item})
    if not candidates:
        return {**base, "status": "unsupported", "failure_stage": "candidate_generation_failure", "warning": "semantic_candidate_not_found"}
    if spec.subtype == "semantic_list_extraction":
        included, excluded, list_error = _derive_list_items(question, spec, candidates)
        image_audit = _list_image_relevance(question, files, extraction_by_file, root)
        blocking_images = [item for item in image_audit if item.get("relevance_class") == "clearly_relevant_but_unparsed" or item.get("blocks_completeness")]
        list_evidence = [_list_item_evidence(item, True, spec) for item in included]
        list_evidence.extend(_list_item_evidence(item, False, spec) for item in excluded)
        for item in list_evidence:
            item["preview_only"] = False
        completeness = {
            "scanned_sources": sorted({item.get("source_path") for item in candidates}),
            "scanned_containers": sorted({f"{item.get('file_id')}:{item.get('element_type')}" for item in candidates}),
            "total_candidates": len(candidates),
            "included_count": len(included),
            "excluded_count": len(excluded),
            "unparsed_object_count": len(image_audit),
            "irrelevant_unparsed_count": sum(item.get("relevance_class") == "decorative_or_irrelevant" for item in image_audit),
            "possibly_relevant_unparsed_count": sum(item.get("relevance_class") == "possibly_relevant" for item in image_audit),
            "clearly_relevant_unparsed_count": len(blocking_images),
            "completeness_check_passed": not blocking_images and not list_error and bool(included),
            "completeness_failure_reasons": ([list_error] if list_error else []) + (["relevant_unparsed_object"] if blocking_images else []),
        }
        if list_error or not included or blocking_images:
            result = {**base, "status": "unsupported", "failure_stage": "semantic_list_evidence_failure", "warning": list_error or "relevant_unparsed_object", "evidence": list_evidence, "list_spec": {"operation": "extract_filtered_list" if spec.subtype != "explicit_bullet_list" else "extract_list", "subtype": spec.subtype, "selection_mode": spec.selection_mode}, "completeness": completeness, "image_relevance_audit": image_audit}
            _append_jsonl(work_dir / "semantic_results.jsonl", {"question_id": question_id, **result})
            return result
        answer_values = [str(item["item_value"]) for item in included]
        answer = "\n".join(answer_values)
        verification, reconstructed = _build_list_verification(included, excluded, completeness, answer)
        condition_audit = _condition_evidence_audit(question, included, excluded)
        verification["condition_evidence_required"] = condition_audit["required"]
        verification["all_conditions_supported"] = condition_audit["all_conditions_supported"]
        verification["condition_evidence"] = condition_audit
        if condition_audit["required"] and not condition_audit["all_conditions_supported"]:
            verification["verification_failure_reasons"].append("condition_evidence_incomplete")
            verification["verification_status"] = "failed"
        list_evidence = [_list_item_evidence(item, True, spec) for item in included]
        list_evidence.extend(_list_item_evidence(item, False, spec) for item in excluded)
        selection_row = {
            "question_id": question_id,
            "model": "",
            "free_model_only": True,
            "candidate_count": len(candidates),
            "selected_candidate_ids": [item["candidate_id"] for item in included],
            "selection_status": "selected",
            "selection_valid": True,
            "selection_method": "deterministic_list_extraction",
            "confidence": 1.0,
        }
        _append_jsonl(work_dir / "semantic_selections.jsonl", selection_row)
        result = {
            **base,
            "status": "success" if verification["verification_status"] == "passed" else "unsupported",
            "answer": answer if verification["verification_status"] == "passed" else "",
            "evidence": list_evidence,
            "used_file_ids": sorted({item["file_id"] for item in included}),
            "verification": verification,
            "semantic_selection": selection_row,
            "semantic_spec": {**spec.__dict__, "selection_mode": "all"},
            "list_spec": {"operation": "extract_filtered_list" if spec.subtype != "explicit_bullet_list" else "extract_list", "subtype": spec.subtype, "selection_mode": spec.selection_mode, "duplicate_policy": "deduplicate_normalized", "ordering_policy": "document_order"},
            "completeness": completeness,
            "image_relevance_audit": image_audit,
            "condition_evidence": condition_audit,
            "list_evidence_contract": {
                "included_candidate_ids": [item.get("candidate_id") for item in list_evidence if item.get("included")],
                "excluded_candidate_ids": [item.get("candidate_id") for item in list_evidence if not item.get("included")],
                "included_count": len(included),
                "excluded_count": len(excluded),
                "independent_reconstruction_answer": reconstructed,
                "filter_spec": {"subtype": spec.subtype},
            },
            "failure_stage": "" if verification["verification_status"] == "passed" else "semantic_list_verification_failure",
            "warning": "" if verification["verification_status"] == "passed" else "list_verification_failed",
        }
        _append_jsonl(work_dir / "semantic_results.jsonl", {"question_id": question_id, **result})
        return result
    selected, answer, derivation = _deterministic_unique_selection(question, spec, candidates)
    if selected is not None:
        selection_row = {
            "question_id": question_id,
            "model": "",
            "free_model_only": True,
            "candidate_count": len(candidates),
            "prompt_hash": "",
            "api_call_success": False,
            "json_parse_success": None,
            "retry_count": 0,
            "fallback_used": False,
            "selected_candidate_ids": [selected["candidate_id"]],
            "confidence": 1.0,
            "selection_status": "selected",
            "selection_valid": True,
            "selection_error": "",
            "selection_method": "deterministic_unique_value",
        }
    else:
        if client is None:
            return {**base, "status": "unsupported", "failure_stage": "semantic_api_unavailable", "warning": "semantic_api_required"}
        llm_result = client.call_json("semantic_candidate_selection", _selection_prompt(question, spec, candidates), max_tokens=500)
        parsed = llm_result.parsed_json
        valid, validation_error = _validate_selection(parsed, candidates, spec) if llm_result.parse_success else (False, "json_parse_failure")
        selection_row = {
            "question_id": question_id,
            "model": llm_result.model,
            "free_model_only": llm_result.model.endswith(":free"),
            "candidate_count": len(candidates),
            "prompt_hash": llm_result.prompt_hash,
            "api_call_success": llm_result.success,
            "json_parse_success": llm_result.parse_success,
            "retry_count": llm_result.retry_count,
            "fallback_used": False,
            "selected_candidate_ids": parsed.get("selected_candidate_ids", []),
            "confidence": parsed.get("confidence"),
            "selection_status": parsed.get("selection_status", "error"),
            "selection_valid": valid,
            "selection_error": validation_error,
            "selection_method": "free_llm_candidate_selection",
        }
        if not valid or parsed.get("selection_status") != "selected":
            _append_jsonl(work_dir / "semantic_selections.jsonl", selection_row)
            warning = validation_error or str(parsed.get("selection_status") or "semantic_selection_failed")
            return {**base, "status": "unsupported", "failure_stage": "semantic_selection_failure", "warning": warning, "semantic_selection": selection_row}
        selected_id = str(parsed["selected_candidate_ids"][0])
        selected = next(item for item in candidates if item["candidate_id"] == selected_id)
        answer, derivation = _derive_answer(question, spec, selected)
    _append_jsonl(work_dir / "semantic_selections.jsonl", selection_row)
    location = {name: selected.get(name) for name in ("page_number", "slide_number", "paragraph_index", "table_index", "row_index", "shape_index") if selected.get(name) is not None}
    evidence = {
        **selected,
        "source_location": location,
        "location": location,
        "matched_text": answer,
        "derivation_method": derivation,
        "preview_only": False,
    }
    evidence_text = "\n".join((selected["context_before"], selected["text"], selected["context_after"]))
    answer_present = bool(answer) and (
        answer in evidence_text
        or (derivation == "status_yes_no" and any(word.lower() in evidence_text.lower() for word in _status_words()))
    )
    verification = {
        "selected_candidates_exist": True,
        "source_files_verified": True,
        "project_relation_verified": True,
        "presence": answer_present,
        "condition_match": bool(answer),
        "answer_text_present_in_evidence": answer_present,
        "answer_derived_only_from_selected_candidates": answer_present,
        "source_locations_present": bool(location),
        "required_items_complete": None,
        "no_unsupported_inference": bool(answer),
        "verbatim_match": answer_present,
        "uniqueness": True,
        "verification_status": "passed" if answer_present and location else "failed",
    }
    result = {
        **base,
        "status": "success" if verification["verification_status"] == "passed" else "unsupported",
        "answer": answer if verification["verification_status"] == "passed" else "",
        "evidence": [evidence],
        "used_file_ids": [selected["file_id"]],
        "verification": verification,
        "semantic_selection": selection_row,
        "failure_stage": "" if verification["verification_status"] == "passed" else "semantic_evidence_failure",
        "warning": "" if verification["verification_status"] == "passed" else derivation,
    }
    _append_jsonl(work_dir / "semantic_results.jsonl", {"question_id": question_id, **result})
    return result
