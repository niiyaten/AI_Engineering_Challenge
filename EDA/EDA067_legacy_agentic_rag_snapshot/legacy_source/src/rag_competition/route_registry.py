"""質問要求・資料形式・資料関係から既存ExecutorへのRouteを決める。"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RouteDefinition:
    route_id: str
    capability_id: str
    description: str
    supported_operations: tuple[str, ...]
    supported_file_types: tuple[str, ...]
    supported_source_relations: tuple[str, ...]
    executor: str
    structure_resolver: str
    ambiguity_policy: str = "suppress_if_not_unique"
    implementation_status: str = "implemented"


@dataclass
class RouteDecision:
    question_intent: dict[str, Any]
    source_requirement: dict[str, Any]
    file_types: list[str]
    route_candidates: list[dict[str, Any]] = field(default_factory=list)
    selected_route: str = ""
    selection_reason: str = ""
    selection_confidence: float = 0.0
    ambiguity_reason: str = ""
    route_selected: bool = False
    executor: str = ""
    structure_resolver: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ROUTES = (
    RouteDefinition(
        "excel.regression.predict_from_coefficients", "coefficient_prediction", "Excel regression coefficient prediction",
        ("coefficient_prediction",), ("xlsx", "xlsm"), ("single_source", "unknown"), "execute_table_question", "workbook_formula_binding",
    ),
    RouteDefinition(
        "excel.chart.series.column", "chart_series_lookup", "Native Excel ChartEx series header lookup",
        ("chart_value_lookup",), ("xlsx", "xlsm"), ("single_source", "unknown"), "execute_chart_series_lookup", "chart_ooxml_relationships",
    ),
    RouteDefinition(
        "excel.single_source.table", "table_lookup", "単一XLSX/CSVの表処理", 
        ("single_value_lookup", "filtered_list", "filtered_value_lookup", "filtered_count", "count", "sum", "average", "simple_calculation", "table_calculation", "formatted_text_span"),
        ("xlsx", "xlsm", "csv", "tsv"), ("single_source", "unknown"), "execute_table_question", "table_data_loader",
    ),
    RouteDefinition(
        "document.single_source.lookup", "document_lookup", "単一文書の既存lookup", 
        ("single_document_lookup", "single_value_lookup", "heading_section_extract"),
        ("docx", "pptx", "pdf", "md", "txt", "json"), ("single_source", "unknown"), "execute_document_question", "document_ir",
    ),
    RouteDefinition(
        "notebook.output.lookup", "notebook_output_lookup", "Notebook出力の既存lookup",
        ("code_result_lookup", "notebook_output_lookup"), ("ipynb",), ("single_source", "unknown"),
        "execute_notebook_inspection", "notebook_cell_ir",
    ),
    RouteDefinition(
        "notebook.axis_ticks.replay", "notebook_axis_ticks", "Notebook visualization axis tick replay",
        ("notebook_axis_tick_lookup",), ("ipynb",), ("single_source", "unknown"),
        "execute_notebook_axis_ticks", "notebook_visualization_replay",
    ),
)


def _intent(question: str) -> dict[str, Any]:
    q = question or ""
    lower = q.lower()
    if any(token in q for token in ("目盛り", "y軸", "Y軸", "ytick", "y-tick", "y-axis", "axis tick", "tick maximum")) and any(token in q for token in ("Notebook", "notebook", "ipynb", "可視化", "グラフ", "visualization")):
        primary = "notebook_axis_tick_lookup"
    elif (
        any(token in q for token in ("\u56de\u5e30\u4fc2\u6570", "\u56de\u5e30\u5206\u6790"))
        and any(token in q for token in ("\u4e88\u6e2c", "\u4e88\u6e2c\u5024"))
    ) or ("coefficient" in lower and "predict" in lower):
        primary = "coefficient_prediction"
    elif "\u30b0\u30e9\u30d5" in q and ("\u30ab\u30e9\u30e0" in q or "\u53ef\u8996\u5316" in q or "column" in lower):
        primary = "chart_value_lookup"
    elif any(token in q for token in ("旧版", "新版", "差分", "変更内容", "変更点", "old", "new", "version_diff")):
        primary = "version_diff"
    elif any(token in q for token in ("平均", "average", "mean")):
        primary = "average"
    elif any(token in q for token in ("合計", "総計", "sum")):
        primary = "sum"
    elif any(token in q for token in ("件数", "何件", "count")):
        primary = "filtered_count" if any(token in q for token in ("条件", "該当", "期間", "フェーズ", "担当")) else "count"
    elif any(token in q for token in ("一覧", "すべて挙げ", "全て挙げ", "列挙")):
        primary = "filtered_list"
    elif any(token in q for token in ("ハイライト", "黄色", "太字", "下線", "イタリック")):
        primary = "formatted_text_span"
    elif any(token in q for token in ("Notebook", "ipynb", "コード", "出力")):
        primary = "notebook_output_lookup"
    elif any(token in q for token in ("ページ番号", "ページ数", "スライド番号")):
        primary = "single_document_lookup"
    else:
        primary = "single_value_lookup"
    # 計算要求を単純な表参照Routeへ流さない。未実装の計算は安全に抑制する。
    calculation_terms = ("平均", "合計", "割合", "比率", "差額", "最も大きい", "最も小さい", "当たり", "小数第", "計算")
    if primary not in {"coefficient_prediction", "notebook_axis_tick_lookup"} and any(token in q for token in calculation_terms):
        primary = "calculation"
    conditions: list[dict[str, Any]] = []
    for field, value in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*[=＝]\s*([A-Za-z0-9_.-]+)", q):
        conditions.append({"field": field, "operator": "equals", "value": value, "value_type": "string"})
    same_row = any(token in q for token in ("同じ行", "同一行", "同一項目", "同じ項目"))
    return {
        "primary_operation": primary,
        "secondary_operations": [],
        "target_entity": "table_record" if primary not in {"single_document_lookup", "notebook_output_lookup", "notebook_axis_tick_lookup"} else "document_item",
        "target_field": "",
        "target_section": "",
        "conditions": conditions,
        "condition_logic": "AND",
        "same_row_required": same_row,
        "same_record_required": same_row,
        "same_entity_required": same_row,
        "calculation_type": primary if primary in {"average", "sum", "filtered_count", "coefficient_prediction"} else "",
        "aggregation_type": primary if primary in {"average", "sum", "filtered_count", "count"} else "",
        "comparison_type": "version_diff" if primary == "version_diff" else "none",
        "output_type": "list" if primary == "filtered_list" else "scalar",
        "output_format": "text",
        "sort_requirement": "document_order",
        "limit_requirement": "",
        "ambiguities": [],
        "confidence": 0.8 if primary else 0.0,
    }


def _source_relation(analysis: Any) -> tuple[str, int | str]:
    req = getattr(analysis, "source_requirement", {}) or {}
    if getattr(analysis, "needs_multiple_files", False) or req.get("minimum_sources", 1) not in (None, 1):
        return "multiple_sources", req.get("minimum_sources", "multiple")
    relation = str(req.get("source_relation") or "single_source")
    if relation in {"unknown", ""}:
        relation = "single_source"
    return relation, req.get("minimum_sources", 1)


def choose_route(question: str, analysis: Any, selected_files: list[Any]) -> RouteDecision:
    intent = _intent(question)
    relation, source_count = _source_relation(analysis)
    file_types = sorted({str(getattr(item, "extension", "")).lower().lstrip(".") for item in selected_files if getattr(item, "extension", "")})
    requirement = {"source_count": source_count, "source_relation": relation, "required_file_types": file_types}
    decision = RouteDecision(intent, requirement, file_types)
    if intent["primary_operation"] == "version_diff" or relation in {"multiple_sources", "version_comparison", "source_comparison"}:
        decision.ambiguity_reason = "comparison_or_multiple_source_executor_not_implemented"
        return decision
    candidates: list[tuple[float, RouteDefinition]] = []
    for route in ROUTES:
        op_score = 1.0 if intent["primary_operation"] in route.supported_operations else 0.0
        file_score = 1.0 if file_types and all(item in route.supported_file_types for item in file_types) else 0.0
        relation_score = 1.0 if relation in route.supported_source_relations else 0.0
        if op_score and file_score and relation_score:
            candidates.append((op_score + file_score + relation_score, route))
    candidates.sort(key=lambda item: (-item[0], item[1].route_id))
    decision.route_candidates = [{"route_id": route.route_id, "score": score, "executor": route.executor} for score, route in candidates]
    if not candidates:
        decision.ambiguity_reason = "no_route_supports_operation_file_relation"
        return decision
    best_score, best = candidates[0]
    if len(candidates) > 1 and candidates[1][0] == best_score:
        decision.ambiguity_reason = "multiple_routes_same_score"
        return decision
    if len(selected_files) != 1:
        decision.ambiguity_reason = "selected_source_count_is_not_one"
        return decision
    decision.selected_route = best.route_id
    decision.selection_reason = "operation x file_type x source_relation matched uniquely"
    decision.selection_confidence = min(1.0, best_score / 3.0)
    decision.route_selected = True
    decision.executor = best.executor
    decision.structure_resolver = best.structure_resolver
    return decision
