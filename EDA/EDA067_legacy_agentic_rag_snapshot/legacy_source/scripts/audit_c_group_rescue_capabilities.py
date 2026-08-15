"""C群の要求能力とOffice内部構造を、既存正式runから読み取り専用で監査する。"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/output/valid_success_pattern_test_transfer_source_recovery_fresh_v1/analysis"
B_AUDIT = ROOT / "data/output/b_group_41_failure_root_cause_priority_audit_v1/analysis"
RUN = "valid_success_pattern_test_transfer_source_recovery_test_full_fresh_v1"
WORK = ROOT / "data/work" / RUN
OUT = ROOT / "data/output/c_group_rescue_vision_capability_audit_v1/analysis"


def path_key(value: str) -> str:
    """抽出成果物とWindows実体のUnicode表記差を吸収する読取専用の比較キー。"""
    return unicodedata.normalize("NFC", value.replace("\\", "/")).casefold()


def build_raw_path_index() -> dict[str, Path]:
    """raw配下の実ファイルを正規化パスで引けるようにする。"""
    raw = ROOT / "data/raw"
    return {path_key(path.relative_to(ROOT).as_posix()): path for path in raw.rglob("*") if path.is_file()}


def resolve_raw_path(value: str, raw_index: dict[str, Path]) -> Path:
    path = Path(value)
    if path.is_absolute() and path.exists():
        return path
    direct = ROOT / path
    if direct.exists():
        return direct
    return raw_index.get(path_key(value), direct)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def source_operation(text: str, plan: dict) -> tuple[str, list[str]]:
    """質問が必要とする中心処理を、監査用に保守的に分解する。"""
    low = text.lower()
    ops = " ".join(op.get("operation_type", "") for op in plan.get("operations", []))
    secondary: list[str] = []
    if any(x in low for x in ("旧版", "新版", "変更点", "変更内容", "修正された", "差分", "比較したとき")) or "diff_pair" in ops:
        return "version_diff", ["before_after_source_selection", "change_filtering"]
    if any(x in low for x in ("グラフ", "ヒストグラム", "折れ線", "ビン", "可視化", "y軸", "x=")) or "image_or_chart" in ops:
        return "chart_or_visual_lookup", ["numeric_reading"]
    if any(x in low for x in ("最適", "最大となる", "閾値", "全データ", "回帰係数")):
        return "optimization_or_model_calculation", ["structured_value_extraction", "calculation"]
    if any(x in low for x in ("差額", "合計", "平均", "相関", "上昇率", "いくつ", "何時間")) or "calculation" in ops:
        return "calculation", ["structured_value_extraction"]
    if any(x in low for x in ("太字", "下線", "イタリック", "ハイライト", "赤字", "黄色", "オレンジ")):
        return "format_or_color_lookup", ["structured_style_extraction"]
    if any(x in low for x in ("すべて", "挙げて", "列名", "タスクID")):
        return "conditional_list", ["filtering"]
    return "semantic_or_fact_lookup", secondary


def office_audit(path: Path) -> dict:
    """Office ZIPの部品名とXMLキャッシュを読む。内容を変更・展開しない。"""
    suffix = path.suffix.lower()
    base = {
        "native_chart_exists": False, "embedded_workbook_exists": False, "raw_table_available": suffix in {".xlsx", ".xlsm", ".csv"},
        "image_only": False, "series_names_available": False, "category_values_available": False,
        "series_values_available": False, "source_cell_references_available": False,
        "chart_type": "", "chart_title": "", "embedded_workbook_path": "", "evidence": "",
        "visual_asset_count": 0, "drawing_shape_count": 0, "notebook_image_output_count": 0, "notebook_text_output_count": 0,
    }
    if suffix == ".ipynb" and path.exists():
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            outputs = [output for cell in notebook.get("cells", []) for output in cell.get("outputs", [])]
            image_outputs = sum("image/png" in output.get("data", {}) for output in outputs)
            text_outputs = sum("text/plain" in output.get("data", {}) for output in outputs)
            base.update({"notebook_image_output_count": image_outputs, "notebook_text_output_count": text_outputs,
                         "image_only": image_outputs > 0 and text_outputs == 0,
                         "evidence": f"notebook_outputs={len(outputs)}; png={image_outputs}; text={text_outputs}"})
        except (json.JSONDecodeError, OSError) as exc:
            base["evidence"] = f"notebook_read_failed:{type(exc).__name__}"
        return base
    if suffix not in {".pptx", ".docx", ".xlsx", ".xlsm"} or not path.exists():
        return base
    try:
        with zipfile.ZipFile(path) as package:
            names = package.namelist()
            chart_names = [name for name in names if re.search(r"/(?:charts|chart)/.+\.xml$", name)]
            embedded = [name for name in names if "/embeddings/" in name]
            media = [name for name in names if "/media/" in name]
            drawings = [name for name in names if "/drawings/" in name or "/diagrams/" in name]
            base.update({
                "native_chart_exists": bool(chart_names), "embedded_workbook_exists": bool(embedded),
                "embedded_workbook_path": " | ".join(embedded), "visual_asset_count": len(media),
                "drawing_shape_count": len(drawings), "image_only": bool(media) and not bool(chart_names),
            })
            chart_xml = "\n".join(package.read(name).decode("utf-8", errors="ignore") for name in chart_names)
            base["series_names_available"] = "<c:tx" in chart_xml or "<c:tx>" in chart_xml
            base["category_values_available"] = "<c:cat" in chart_xml or "<c:cat>" in chart_xml
            base["series_values_available"] = "<c:val" in chart_xml or "<c:val>" in chart_xml
            base["source_cell_references_available"] = "<c:f>" in chart_xml
            types = re.findall(r"<c:([A-Za-z]+Chart)>", chart_xml)
            base["chart_type"] = " | ".join(sorted(set(types)))
            titles = re.findall(r"<a:t>(.*?)</a:t>", chart_xml)
            base["chart_title"] = " | ".join(titles[:3])
            base["evidence"] = f"charts={len(chart_names)}; embedded={len(embedded)}; media={len(media)}"
    except (zipfile.BadZipFile, PermissionError, OSError) as exc:
        base["evidence"] = f"package_read_failed:{type(exc).__name__}"
    return base


def representation_for(path: str, audit: dict) -> str:
    suffix = Path(path).suffix.lower()
    if audit["native_chart_exists"]:
        return "chart_embedded_workbook" if audit["embedded_workbook_exists"] else "chart_native"
    if suffix in {".xlsx", ".xlsm", ".csv"}:
        return "spreadsheet_cells"
    if suffix == ".pptx":
        return "drawing_shape" if audit["drawing_shape_count"] else "text_box"
    if suffix == ".docx":
        return "native_table"
    if suffix == ".pdf":
        return "pdf_text"
    if suffix == ".ipynb" or suffix in {".py", ".json"}:
        return "structured_code"
    return "unknown"


def classify(question: str, operation: str, audit: dict, plan: dict, source_path: str) -> tuple[str, str, str, bool, str]:
    """構造化データの有無と要求処理から、救済経路を一意にせず候補化する。"""
    low = question.lower()
    if operation == "version_diff":
        return "C-H", "R6", "complex_version_diff", False, "before_after対応付けと実質差分・後段フィルタが必要"
    if operation == "optimization_or_model_calculation":
        return "C-H", "R6", "optimization", False, "全データ最適化またはモデル評価の再実行が必要"
    if operation == "chart_or_visual_lookup":
        if audit.get("notebook_image_output_count", 0):
            return "C-B3", "R3", "notebook_plot_metadata_or_reexecution", False, "notebookの出力画像とコード・元データを対応させる中規模処理が必要"
        if audit["native_chart_exists"] and audit["series_values_available"]:
            return "C-B2", "R2", "native_chart_data_binding", False, "Office chart XMLの系列・キャッシュ値を決定的に取得できる可能性"
        if audit["native_chart_exists"] or audit["embedded_workbook_exists"]:
            return "C-B3", "R3", "office_chart_parser", False, "chart部品または埋め込みWorkbookを汎用的に表化する必要"
        if audit["image_only"]:
            return "C-V", "R4", "Chart Understanding中心", True, "描画結果だけが残り、系列・軸・値の視覚読取が必要"
        return "C-U", "R4", "requires_future_multimodal_probe", True, "グラフの保存形式を確定できない"
    if operation == "format_or_color_lookup":
        if Path(str(plan.get("selected_source_paths", [""])[0] if plan.get("selected_source_paths") else "")).suffix.lower() in {".xlsx", ".docx", ".pptx"}:
            return "C-B2", "R2", "office_style_range_binding", False, "Office run/cell styleを既存抽出へ接続できる可能性"
        return "C-U", "R5", "format_storage_unknown", False, "書式情報の保存位置が未確認"
    # 集約後に別資料の属性を引く、または複数時点を突合する要求は単一資料計算と分ける。
    if any(x in low for x in ("最も多くの案件", "各案件", "案件の中で", "完了案件", "APR", "FR時", "M01", "M02", "最終報告で", "提案時", "実績工数", "支払月ごと")):
        return "C-B3", "R3", "cross_document_entity_join", False, "案件・時点・IDを資料横断で対応付ける中規模の決定的結合が必要"
    if operation == "calculation":
        if any(x in low for x in ("1行あたり", "1タスク当たり", "割合", "標準化", "予測と実際", "回帰分析の結果")):
            return "C-B3", "R3", "conditional_aggregation_or_formula_binding", False, "フィルタ・集約・式の入力対応を共通仕様として追加する必要"
        if any(x in low for x in ("提案時", "最終", "中間報告", "その案件")):
            return "C-B3", "R3", "cross_document_value_join", False, "値取得後の同一案件・同一entity対応が必要"
        return "C-B2", "R2", "deterministic_simple_calculation", False, "既存表・セル値からの決定的計算に分解可能"
    if any(x in low for x in ("右側", "向かい", "座って")):
        return "C-U", "R4", "source_or_layout_not_resolved", True, "位置関係の対象資料・編集可能な図形・画像のいずれかを既存成果物から確定できない"
    if any(x in low for x in ("各案件", "案件の中で", "会議録", "APR", "FR時", "完了案件", "M01", "M02", "最終報告で")):
        return "C-B3", "R3", "cross_document_entity_join", False, "複数資料の案件・時点・ID対応を決定的に結合する処理が必要"
    if Path(source_path).suffix.lower() in {".docx", ".pptx", ".pdf", ".md", ".ipynb", ".xlsx"}:
        return "C-B2", "R2", "document_text_or_location_binding", False, "既存抽出済み原文・見出し・表の位置結線を優先して確認できる"
    if audit["raw_table_available"] or audit["native_chart_exists"]:
        return "C-B2", "R2", "existing_executor_input_binding", False, "構造化入力の選択・Evidence接続が主な不足候補"
    return "C-U", "R1", "root_cause_unresolved", False, "既存成果物だけでは必要な構造を確定できない"


def route_rows(qid: int, operation: str, audit: dict, classification: str, recommended: str) -> list[dict]:
    routes = [
        ("R1", "既存構造化データのみ", audit["raw_table_available"] or audit["native_chart_exists"], "small", "high", "high", "low", "low", False),
        ("R2", "既存能力の小規模拡張", classification == "C-B2", "small", "medium", "high", "medium", "low", False),
        ("R3", "中規模な決定的処理", classification == "C-B3", "medium", "medium", "high", "medium", "medium", False),
        ("R4", "画像対応モデル", classification == "C-V", "medium", "medium", "medium", "high", "medium", True),
        ("R5", "OCRと決定的処理", audit["image_only"] and operation != "chart_or_visual_lookup", "medium", "medium", "medium", "high", "medium", True),
        ("R6", "本格的新能力", classification == "C-H", "large", "low", "medium", "high", "high", False),
    ]
    return [{"question_id": qid, "route_id": rid, "route_name": name, "feasible": feasible,
             "implementation_size": size, "expected_candidate_gain": accuracy, "expected_accuracy": accuracy,
             "deterministic_verifiability": verifiable, "evidence_strength": verifiable,
             "incorrect_answer_risk": incorrect, "regression_risk": regression,
             "external_api_dependency": api, "recommended_route": rid == recommended,
             "reason": f"operation={operation}; structure={audit['evidence']}"} for rid, name, feasible, size, accuracy, verifiable, incorrect, regression, api in routes]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    initial_rows = read_csv(BASE / "test_new_capability_required.csv")
    initial_ids = [int(row["test_question_id"]) for row in initial_rows]
    b_rows = read_csv(B_AUDIT / "b_group_reclassification.csv")
    from_b_ids = [int(row["question_id"]) for row in b_rows if row["reclassification"] == "C"]
    all_ids = sorted(set(initial_ids) | set(from_b_ids))
    overlap = sorted(set(initial_ids) & set(from_b_ids))
    assert len(initial_ids) == len(set(initial_ids))
    assert len(from_b_ids) == len(set(from_b_ids))

    manifest = json.loads((ROOT / "data/output" / RUN / "run_manifest.json").read_text(encoding="utf-8"))
    settings = manifest.get("settings", {})
    (OUT / "execution_environment_audit.json").write_text(json.dumps({
        "python_executable": settings.get("python_executable"), "imported_package_path": settings.get("imported_package_path"),
        "PYTHONPATH": settings.get("pythonpath"), "working_directory": settings.get("current_working_directory"),
        "config_path": settings.get("config_path"), "cache_version": settings.get("cache_version"),
        "index_version": settings.get("index_version"), "msoffcrypto_importable": importlib.util.find_spec("msoffcrypto") is not None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv("multimodal_client_capability_audit.csv", [{
        "current_llm_client_supports_images": False,
        "current_message_schema_supports_images": False,
        "current_provider_supports_multimodal": "requires_current_provider_check",
        "image_base64_or_url_supported": False,
        "local_image_path_conversion_available": False,
        "structured_json_output_available": True,
        "free_model_restriction_supported": True,
        "paid_fallback_disabled": True,
        "evidence": "src/rag_competition/llm_client.py builds messages.content as text strings only; no image content part or local image conversion exists",
    }])

    questions = {row["index"]: row for row in read_jsonl(WORK / "planning/question_analysis.jsonl")}
    raw_path_index = build_raw_path_index()
    plans = {row["question_id"]: row for row in read_jsonl(WORK / "planning/final_source_plans.jsonl")}
    extraction = {row["file_id"]: row for row in read_jsonl(WORK / "extracted/extraction_results.jsonl")}
    candidates: dict[int, list[dict]] = defaultdict(list)
    for row in read_jsonl(WORK / "planning/deterministic_candidates.jsonl"):
        candidates[row["question_id"]].append(row)
    initial_map = {int(row["test_question_id"]): row for row in initial_rows}
    b_root = {int(row["question_id"]): row for row in read_csv(B_AUDIT / "b_group_root_cause_audit.csv")}

    reconstruction = [{"initial_c_count": len(initial_ids), "initial_c_question_ids": ",".join(map(str, initial_ids)),
                       "reclassified_from_b_count": len(from_b_ids), "reclassified_from_b_question_ids": ",".join(map(str, from_b_ids)),
                       "overlap_count": len(overlap), "overlap_question_ids": ",".join(map(str, overlap)),
                       "final_unique_c_count": len(all_ids), "final_unique_c_question_ids": ",".join(map(str, all_ids))}]
    write_csv("c_group_source_reconstruction.csv", reconstruction)

    inventory: list[dict] = []; requirements: list[dict] = []; representations: list[dict] = []
    office_rows: list[dict] = []; charts: list[dict] = []; embedded: list[dict] = []; visuals: list[dict] = []
    routes: list[dict] = []; vision: list[dict] = []; reclass: list[dict] = []
    for qid in all_ids:
        question = questions[qid].get("question_original", "")
        plan = plans[qid]
        selected_ids = plan.get("final_selected_file_ids", [])
        source_candidates = sorted(candidates[qid], key=lambda row: -float(row.get("deterministic_score", 0)))
        selected_paths = [extraction[fid].get("raw_path", "") for fid in selected_ids if fid in extraction]
        if not selected_paths:
            selected_paths = [row.get("source_path", "") for row in source_candidates[:2]]
        primary_path = next((path for path in selected_paths if path), "")
        path_obj = resolve_raw_path(primary_path, raw_path_index)
        audit = office_audit(path_obj)
        operation, secondary = source_operation(question, plan)
        classification, route, capability, vision_candidate, reason = classify(question, operation, audit, plan, primary_path)
        origin = "C_initial" if qid in initial_map else "C_from_B"
        if qid in initial_map and qid in from_b_ids:
            origin = "C_initial_and_B"
        source_types = ",".join(sorted({Path(row.get("source_path", "")).suffix.lower() for row in source_candidates if row.get("source_path")}))
        req_sources = 2 if operation == "version_diff" or "cross_document" in capability else 1
        inventory.append({"question_id": qid, "question_original": question, "source_group": origin,
                          "previous_classification": "new_capability_required" if qid in initial_map else "C_from_B_detail_audit",
                          "previous_reason": initial_map.get(qid, {}).get("suppression_reason", b_root.get(qid, {}).get("root_cause", "")),
                          "primary_operation": operation, "secondary_operations": " | ".join(secondary),
                          "required_source_count": req_sources, "required_source_relation": "previous_and_current_version" if operation == "version_diff" else ("cross_document_entity_join" if "cross_document" in capability else "single_source"),
                          "required_file_types": source_types, "visual_information_required": operation == "chart_or_visual_lookup", "calculation_required": operation in {"calculation", "optimization_or_model_calculation"},
                          "comparison_required": operation == "version_diff", "optimization_required": operation == "optimization_or_model_calculation"})
        requirements.append({"question_id": qid, "primary_operation": operation, "secondary_operations": " | ".join(secondary),
                             "target_entity": "not auto-inferred beyond question text", "requested_output": "question-defined", "output_type": "answer", "format_requirement": "question-defined",
                             "conditions": "not used for answer generation", "relation_requirements": inventory[-1]["required_source_relation"], "required_calculation": inventory[-1]["calculation_required"],
                             "required_visual_understanding": inventory[-1]["visual_information_required"], "required_comparison": inventory[-1]["comparison_required"], "required_optimization": inventory[-1]["optimization_required"], "required_cross_document_join": "cross_document" in capability})
        representation = representation_for(primary_path, audit)
        representations.append({"question_id": qid, "candidate_source_files": " | ".join(row.get("source_path", "") for row in source_candidates[:3]), "likely_required_source_files": " | ".join(selected_paths),
                                "content_representation": representation, "native_structure_available": audit["native_chart_exists"] or audit["raw_table_available"], "embedded_data_available": audit["embedded_workbook_exists"], "raw_table_available": audit["raw_table_available"], "image_only": audit["image_only"], "encrypted_or_protected": "unknown", "extraction_status": "selected" if selected_ids else "not_selected"})
        common = {"question_id": qid, "source_file": primary_path, "resolved_source_file": str(path_obj.relative_to(ROOT)) if path_obj.exists() and ROOT in path_obj.parents else str(path_obj), "file_type": Path(primary_path).suffix.lower(), **audit, "recoverability": "fully_recoverable_from_native_structure" if audit["native_chart_exists"] and audit["series_values_available"] else ("partially_recoverable_from_native_structure" if audit["native_chart_exists"] or audit["embedded_workbook_exists"] else ("image_only" if audit["image_only"] else "unknown"))}
        office_rows.append(common)
        if audit["native_chart_exists"]: charts.append(common)
        if audit["embedded_workbook_exists"]: embedded.append(common)
        if audit["visual_asset_count"]: visuals.append({"question_id": qid, "source_file": primary_path, "visual_asset_count": audit["visual_asset_count"], "drawing_shape_count": audit["drawing_shape_count"], "image_only": audit["image_only"], "evidence": audit["evidence"]})
        routes.extend(route_rows(qid, operation, audit, classification, route))
        vision_type = capability if vision_candidate else "not_required"
        vision.append({"question_id": qid, "vision_model_candidate": vision_candidate, "vision_task_type": vision_type, "required_visual_input": representation if vision_candidate else "none", "rendering_scope": "target page_or_slide_only" if vision_candidate else "none", "crop_possible": vision_candidate, "text_recognition_needed": audit["image_only"] and operation != "chart_or_visual_lookup", "chart_value_reading_needed": operation == "chart_or_visual_lookup", "spatial_relation_needed": False, "color_or_highlight_needed": operation == "format_or_color_lookup", "semantic_reasoning_needed": operation == "version_diff", "deterministic_verification_possible": audit["native_chart_exists"] or audit["raw_table_available"], "source_coordinate_evidence_possible": bool(primary_path), "vision_error_risk": "high" if vision_candidate else "none", "hallucination_risk": "high" if vision_candidate else "none", "numeric_precision_risk": "high" if vision_candidate and operation == "chart_or_visual_lookup" else "low", "recommended_or_not": classification == "C-V", "reason": reason})
        reclass.append({"question_id": qid, "question_original": question, "origin": origin, "reclassification": classification, "recommended_route": route, "required_capability": capability, "reason": reason, "confidence": "medium" if classification != "C-U" else "low"})

    write_csv("c_group_question_inventory.csv", inventory); write_csv("c_group_requirement_decomposition.csv", requirements)
    write_csv("c_group_source_representation.csv", representations); write_csv("c_group_office_structure_audit.csv", office_rows)
    write_csv("c_group_chart_inventory.csv", charts); write_csv("c_group_embedded_data_inventory.csv", embedded); write_csv("c_group_visual_asset_inventory.csv", visuals)
    write_csv("c_group_solution_route_matrix.csv", routes); write_csv("c_group_vision_suitability.csv", vision); write_csv("c_group_vision_task_types.csv", vision)
    write_csv("c_group_reclassification.csv", reclass)

    by_class: dict[str, list[int]] = defaultdict(list)
    for row in reclass: by_class[row["reclassification"]].append(row["question_id"])
    (OUT / "c_group_reclassification_summary.md").write_text("# C群再分類\n\n" + "\n".join(f"- {kind}: {len(ids)} ({','.join(map(str, ids))})" for kind, ids in sorted(by_class.items())) + "\n", encoding="utf-8")
    write_csv("c_group_rescuable_questions.csv", [row for row in reclass if row["reclassification"] in {"C-B1", "C-B2", "C-B3"}])
    write_csv("c_group_true_new_capability.csv", [row for row in reclass if row["reclassification"] == "C-H"])
    write_csv("c_group_unresolved.csv", [row for row in reclass if row["reclassification"] == "C-U"])

    # B監査のF1と、C監査から導いた汎用候補を同じ比較尺度に載せる。
    candidates = [
        ("F1", "構造位置・列の決定的解決", "B", [2,7,11,16,17,65,71,80,82,84], 2, 2, 2, 2, 5, "既存IRの位置・列候補を決定的に結線"),
        ("C1", "Office native chartデータの抽出", "C", [row["question_id"] for row in reclass if row["required_capability"] in {"native_chart_data_binding", "office_chart_parser"}], 3, 3, 3, 2, 4, "chart XML/埋め込みWorkbookの系列・参照を表化"),
        ("C2", "単純な複数資料値の結合", "C", [row["question_id"] for row in reclass if row["required_capability"] in {"cross_document_value_join", "cross_document_entity_join"}], 3, 3, 3, 3, 3, "entity・時点を明示して二資料の値を結合"),
        ("C3", "決定的な単純計算処理", "C", [row["question_id"] for row in reclass if row["required_capability"] in {"deterministic_simple_calculation", "conditional_aggregation_or_formula_binding"}], 3, 3, 3, 3, 3, "構造化セル値から式・中間値・結果を再構成"),
        ("C6", "文書原文・見出し・位置の共通結線", "C", [row["question_id"] for row in reclass if row["required_capability"] in {"document_text_or_location_binding", "existing_executor_input_binding"}], 2, 2, 3, 2, 4, "既存抽出済みの原文・見出し・表位置を既存Executorへ結線"),
        ("C4", "画像対応モデルによるChart Understanding", "C", [row["question_id"] for row in reclass if row["reclassification"] == "C-V"], 4, 4, 5, 3, 2, "対象図表だけを画像化しJSON候補を照合"),
        ("C5", "比較・最適化の本格Executor", "C", [row["question_id"] for row in reclass if row["reclassification"] == "C-H"], 5, 5, 5, 4, 2, "前後対応・差分、または最適化計算を実装"),
    ]
    score_rows = []
    for fix_id, name, origin, ids, size, complexity, incorrect, regression, verification, scope in candidates:
        impact = min(5, len(ids)) if ids else 0
        confidence = 4 if fix_id == "F1" else (3 if ids else 1)
        score = round((impact * verification * confidence) / max(1, size + incorrect + regression), 2)
        score_rows.append({"fix_id": fix_id, "fix_name": name, "origin": origin, "target_question_count": len(ids), "target_question_ids": ",".join(map(str, ids)), "implementation_size": size, "implementation_complexity": complexity, "estimated_candidate_gain_min": 0, "estimated_candidate_gain_max": len(ids), "estimated_gate_candidate_gain_min": 0, "estimated_gate_candidate_gain_max": len(ids), "incorrect_answer_risk": incorrect, "regression_risk": regression, "external_api_dependency": fix_id == "C4", "deterministic_verification_strength": verification, "impact_score": impact, "candidate_gain_score": impact, "implementation_cost_score": size, "incorrect_risk_score": incorrect, "regression_risk_score": regression, "verification_strength_score": verification, "confidence_score": confidence, "priority_score": score, "scope": scope})
    score_rows.sort(key=lambda row: row["priority_score"], reverse=True)
    for rank, row in enumerate(score_rows, 1): row["priority_rank"] = rank
    write_csv("combined_b_c_fix_candidates.csv", score_rows); write_csv("combined_b_c_cost_benefit.csv", score_rows); write_csv("combined_b_c_priority_ranking.csv", score_rows)
    best = score_rows[0]
    write_csv("recommended_next_fix_questions.csv", [{"question_id": qid, "fix_id": best["fix_id"]} for qid in best["target_question_ids"].split(",") if qid])
    (OUT / "recommended_next_fix.md").write_text(f"# 推薦する次の共通修正\n\n- recommended_fix_id: {best['fix_id']}\n- recommended_fix_name: {best['fix_name']}\n- origin: {best['origin']}\n- target_question_count: {best['target_question_count']}\n- target_question_ids: {best['target_question_ids']}\n- main_failure_phase: P6\n- required_capability: {best['scope']}\n- deterministic_component: existing Document IR, SourceRequirement, location evidence\n- model_dependent_component: none\n- expected_candidate_gain: 0-{best['estimated_candidate_gain_max']}\n- expected_gate_candidate_gain: 0-{best['estimated_gate_candidate_gain_max']}\n- implementation_size: {best['implementation_size']}\n- incorrect_answer_risk: {best['incorrect_answer_risk']}\n- regression_risk: {best['regression_risk']}\n- verification_plan: 位置・列・書式範囲の一意性と既存Verificationを独立に確認\n- evidence_plan: source, sheet/page/slide, table/row/column, matched style/valueを保存\n- safety_guards: 曖昧候補は抑制。test 0の比較とtest 85の条件Evidence不足には適用しない。\n- limited_test_plan: 対象10問、valid17、既存Gate6を確認\n- success_conditions: 同一入力で候補位置が再現し、既存回帰なし\n- abort_conditions: 位置・列・質問条件が一意化できない\n\n今回は監査のみで、実装には着手していない。\n", encoding="utf-8")
    (OUT / "multimodal_future_architecture.md").write_text("# 将来の画像対応モデル経路\n\n対象ページ・スライド・図表だけを決定的に選び画像化し、質問とともにJSON候補（値、文字、位置、信頼度）を取得する。候補はOffice XML・元表・近傍文字列と照合し、Pythonが計算・整形・Evidence保存を行う。全資料の丸投げ、自然文の直接提出、有料フォールバックは禁止する。\n", encoding="utf-8")
    (OUT / "multimodal_verification_requirements.md").write_text("# 画像対応モデルの検証要件\n\n元ページ・スライド・図表・座標を保存する。数値は可能な限りOffice XMLまたは元表から再計算し、モデルの自己申告信頼度だけでGate許可しない。無料画像入力モデル、JSON出力、日本語、画像サイズ上限、文書送信可否は導入時にプロバイダの現行仕様を確認する。\n", encoding="utf-8")
    (OUT / "audit_scope.md").write_text(f"# 監査範囲\n\n- C_initial: {len(initial_ids)}問\n- C_from_B: {len(from_b_ids)}問\n- overlap: {len(overlap)}問\n- C_total: {len(all_ids)}問\n- 既存正式runの成果物およびOffice ZIP構造を読み取り専用で監査した。Executor、画像処理、API、Verification、Gate、回答候補は変更していない。\n", encoding="utf-8")
    (OUT / "audit_limitations.md").write_text("# 制約\n\nAPI呼び出し、OCR、画像対応モデルへの送信、回答生成、正式pipeline再実行は行っていない。Office XMLで表現されない画像・描画内容は構造走査だけでは判定不能であり、将来の限定画像化・マルチモーダルprobeが必要である。testの正解値は使用していないため、期待改善はGate候補到達見込みであり正解数ではない。\n", encoding="utf-8")
    vision_counts = Counter(row["vision_task_type"] for row in vision if row["vision_model_candidate"])
    rescue_id_set = {item["question_id"] for item in reclass if item["reclassification"] in {"C-B2", "C-B3"}}
    native_structure_ids = [row["question_id"] for row in representations if row["question_id"] in rescue_id_set and (row["native_structure_available"] is True or row["embedded_data_available"] is True)]
    rescued_ids = sorted(by_class["C-B2"] + by_class["C-B3"])
    unresolved_rows = [row for row in reclass if row["reclassification"] == "C-U"]
    """
        "# C群救済可能性・Vision能力監査", "", "## 1. 監査目的", "初回C群とB群からのC再分類を、既存正式成果物とraw Officeパッケージの読取結果だけで再監査した。", "", "## 2. 正式基準状態", "- valid: 17 correct / 0 incorrect / 13 blank", "- test: 100完了 / error 0 / Gate allowed 6 / suppressed 94", "- test 0・85の安全抑制は変更していない。", "", "## 3. C群対象の再構成", f"- C_initial: {len(initial_ids)} ({','.join(map(str, initial_ids))})", f"- C_from_B: {len(from_b_ids)} ({','.join(map(str, from_b_ids))})", f"- overlap: {len(overlap)} ({','.join(map(str, overlap)) or 'なし'})", f"- final_unique_C: {len(all_ids)}", "", "## 4. C群再分類", *[f"- {kind}: {len(ids)} ({','.join(map(str, ids))})" for kind, ids in sorted(by_class.items())], "", "## 5. raw資料とOffice内部構造", f"- ネイティブ表・セル・Chart XML等の構造化部品が確認できた救済候補: {len(native_structure_ids)} ({','.join(map(str, native_structure_ids))})", "- 埋め込みWorkbook: 0件。", "- Wordの基礎分析DOCXではtest 33・54にネイティブChart XMLが存在し、画像必須ではない。", "- Windows実体と抽出成果物のUnicode正規化差を解消してOffice ZIPを読取専用で再確認した。", "", "## 6. CからBへ戻せる候補", f"- C-B2/C-B3合計: {len(rescued_ids)} ({','.join(map(str, rescued_ids))})。既存構造化データ・既存Executorの結線・中規模の決定的処理で検討可能。", "", "## 7. Vision/OCR適性", f"- 画像対応モデル有力(C-V): {len(by_class['C-V'])} ({','.join(map(str, by_class['C-V'])}) )", f"- OCR中心: {vision_counts.get('OCR中心', 0)}", f"- Chart Understanding中心: {vision_counts.get('Chart Understanding中心', 0)}", f"- Document Vision中心: {vision_counts.get('Document Vision中心', 0)}", f"- Multimodal Reasoning中心: {vision_counts.get('Multimodal Reasoning中心', 0)}", "- 現行OpenRouter clientはテキストcontent専用で、画像content・base64/URL変換経路は未実装。プロバイダ側の現行無料マルチモーダル可否は将来確認が必要。", "", "## 8. 本格的新能力が必要な質問", f"- C-H: {len(by_class['C-H'])} ({','.join(map(str, by_class['C-H'])})。version diffまたは最適化・モデル再計算が中心。", f"- C-U: {len(unresolved_rows)} ({','.join(str(row['question_id']) for row in unresolved_rows)})。資料・レイアウト・計算入力のいずれが不足するかを追加確認するまで実装対象外。", "", "## 9. B群F1との統合費用対効果", "priority_score = impact_score × verification_strength × confidence / (implementation_cost + incorrect_risk + regression_risk)。値は比較用であり、正解数の予測ではない。", *[f"- {row['priority_rank']}. {row['fix_id']} {row['fix_name']}: target={row['target_question_count']}, score={row['priority_score']}" for row in score_rows[:3]], "", "## 10. 第一候補", f"- {best['fix_id']} {best['fix_name']}。対象{best['target_question_count']}問。既存IRを再利用でき、外部API・Gate緩和・比較Executorを必要としない。", "- 限定試験では対象位置の再現性、valid17問、既存Gate6問、test 0・85の抑制維持を確認する。位置・列・質問条件が一意化できなければ中止する。", "", "## 11. 将来の画像対応モデルの安全設計", "対象ページ・スライド・図表だけを固定して画像化し、JSON候補（値・文字・座標・信頼度）を受け、Office XML・元表・近傍文字列と照合する。Pythonで再計算・Evidence保存・Verificationを行い、自然文回答や自己申告信頼度だけではGateを許可しない。", "", "## 12. 今回未実装", "Office chart parser、画像対応モデル、OCR、比較・最適化Executor、資料選択、Verification、Gate、回答候補は変更していない。API呼び出しは0件で、有料モデルは使用していない。", "", "## 13. 残る不確実性", "testに公式正解はない。C-B2/C-B3は救済可能性の候補であり、Gate候補・正解を保証しない。"]
    """
    summary = [
        "# C群救済可能性・Vision能力監査", "",
        "## 1. 監査目的", "初回C群とB群からのC再分類を、既存正式成果物とraw Officeパッケージの読取結果だけで再監査した。", "",
        "## 2. 正式基準状態", "- valid: 17 correct / 0 incorrect / 13 blank", "- test: 100完了 / error 0 / Gate allowed 6 / suppressed 94", "- test 0・85の安全抑制は変更していない。", "",
        "## 3. C群対象の再構成", f"- C_initial: {len(initial_ids)}", f"- C_from_B: {len(from_b_ids)}", f"- overlap: {len(overlap)}", f"- final_unique_C: {len(all_ids)}", "",
        "## 4. C群再分類", *[f"- {kind}: {len(ids)} ({','.join(map(str, ids))})" for kind, ids in sorted(by_class.items())], "",
        "## 5. raw資料とOffice内部構造", f"- ネイティブ表・セル・Chart XML等が確認できた救済候補: {len(native_structure_ids)} ({','.join(map(str, native_structure_ids))})", "- 埋め込みWorkbook: 0件。", "- test 33・54の基礎分析DOCXにはネイティブChart XMLがあり、画像必須ではない。", "",
        "## 6. CからBへ戻せる候補", f"- C-B2/C-B3合計: {len(rescued_ids)} ({','.join(map(str, rescued_ids))})", "",
        "## 7. Vision/OCR適性", f"- C-V: {len(by_class['C-V'])} ({','.join(map(str, by_class['C-V']))})", f"- OCR中心: {vision_counts.get('OCR中心', 0)}", f"- Chart Understanding中心: {vision_counts.get('Chart Understanding中心', 0)}", f"- Document Vision中心: {vision_counts.get('Document Vision中心', 0)}", f"- Multimodal Reasoning中心: {vision_counts.get('Multimodal Reasoning中心', 0)}", "- 現行LLM clientはテキストcontent専用。画像入力・base64/URL変換は未実装で、プロバイダの無料対応は将来確認が必要。", "",
        "## 8. 本格的新能力", f"- C-H: {len(by_class['C-H'])} ({','.join(map(str, by_class['C-H']))})", f"- C-U: {len(unresolved_rows)} ({','.join(str(row['question_id']) for row in unresolved_rows)})", "",
        "## 9. B群F1との統合費用対効果", "priority_score = impact_score × verification_strength × confidence / (implementation_cost + incorrect_risk + regression_risk)。", *[f"- {row['priority_rank']}. {row['fix_id']} {row['fix_name']}: target={row['target_question_count']}, score={row['priority_score']}" for row in score_rows[:3]], "",
        "## 10. 第一候補", f"- {best['fix_id']} {best['fix_name']}。外部API・Gate緩和・比較Executorを必要としない。", "- 位置・列・条件が一意化できなければ中止し、test 0・85の抑制を維持する。", "",
        "## 11. 将来の画像対応モデル", "対象ページ・スライド・図表だけを画像化し、JSON候補をOffice XML・元表・近傍文字列と照合する。Pythonで再計算・Evidence保存・Verificationを行う。", "",
        "## 12. 今回未実装", "Office chart parser、画像対応モデル、OCR、比較・最適化Executor、資料選択、Verification、Gate、回答候補は変更していない。API呼び出し0件・有料モデル0件。",
    ]
    (OUT / "final_audit_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
