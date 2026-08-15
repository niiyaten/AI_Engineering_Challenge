from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .schemas import FileRecord


def _terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    terms = re.findall(r"[a-z][a-z0-9_./-]{1,}|[0-9]{2,}|[\u3040-\u30ff\u3400-\u9fff]{2,}", normalized)
    stop = {"について", "ください", "教えて", "資料", "内容", "抽出", "すべて", "そのまま"}
    return list(dict.fromkeys(term for term in terms if term not in stop))


def _matches(text: str, terms: list[str]) -> list[str]:
    lowered = unicodedata.normalize("NFKC", text or "").lower()
    return [term for term in terms if term in lowered]


def _load_structure(extraction: Any, root: Path) -> dict[str, Any] | None:
    if extraction is None or not extraction.extracted_path:
        return None
    path = Path(extraction.extracted_path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _markdown_definition_lookup(question: str, files: list[FileRecord], root: Path) -> dict[str, Any] | None:
    """raw Markdown表から、項目名と特殊値に対応する説明を原文で取得する。"""
    if not any(token in question for token in ("カラム説明", "項目説明", "定義表")):
        return None
    column_match = re.search(r"(?:カラム名|列名|項目名)\s*[:：]?\s*([A-Za-z_][A-Za-z0-9_]*)", question, re.IGNORECASE)
    value_match = re.search(r"(?:値|value)\s*[:：=]?\s*(-?\d+(?:\.\d+)?)", question, re.IGNORECASE)
    if not column_match:
        return None
    target_column = column_match.group(1)
    target_value = value_match.group(1) if value_match else ""
    matches: list[dict[str, Any]] = []
    for file in files:
        if file.extension.lower() != ".md":
            continue
        path = Path(file.raw_path)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        header: list[str] = []
        for line_number, line in enumerate(lines, start=1):
            if "|" not in line:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if any("カラム名" in cell or "列名" in cell or "項目名" in cell for cell in cells):
                header = cells
                continue
            if not header or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell):
                continue
            if len(cells) < len(header):
                cells.extend([""] * (len(header) - len(cells)))
            name_index = next((index for index, cell in enumerate(header) if any(token in cell for token in ("カラム名", "列名", "項目名"))), 0)
            description_index = next((index for index, cell in enumerate(header) if any(token in cell for token in ("説明", "意味", "定義"))), -1)
            raw_name = re.sub(r"[`*_]", "", cells[name_index]).strip()
            if unicodedata.normalize("NFKC", raw_name).lower() != unicodedata.normalize("NFKC", target_column).lower():
                continue
            description = cells[description_index].strip() if 0 <= description_index < len(cells) else ""
            answer = description
            if target_value:
                escaped = re.escape(target_value)
                special = re.search(rf"{escaped}\s*(?:は|=|:|：)\s*([^）、,;；]+)", description)
                if not special:
                    continue
                answer = special.group(1).strip()
            matches.append(
                {
                    "answer": answer,
                    "file_id": file.file_id,
                    "source_path": file.raw_path,
                    "line_number": line_number,
                    "source_text": line,
                    "target_column": target_column,
                    "target_value": target_value,
                }
            )
    unique_answers = {item["answer"] for item in matches if item["answer"]}
    if not matches:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "Markdown定義表に対象項目と値の組がありません", "failure_stage": "evidence_failure", "operations_executed": ["document_lookup"], "used_file_ids": []}
    if len(unique_answers) != 1:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "Markdown定義表に異なる説明候補があります", "failure_stage": "uniqueness_failure", "ambiguous": True, "operations_executed": ["document_lookup"], "used_file_ids": list(dict.fromkeys(item["file_id"] for item in matches))}
    item = matches[0]
    evidence = {
        "file_id": item["file_id"],
        "source_path": item["source_path"],
        "source_location": {"line_number": item["line_number"]},
        "location": {"line_number": item["line_number"]},
        "source_text": item["source_text"],
        "matched_text": item["answer"],
        "preview_only": False,
    }
    return {
        "status": "success",
        "answer": item["answer"],
        "evidence": [evidence],
        "operations_executed": ["document_lookup", "verbatim_extraction"],
        "used_file_ids": [item["file_id"]],
        "question_type": "verbatim_extraction",
        "verification": {
            "presence": True,
            "condition_match": True,
            "location_match": True,
            "verbatim_match": True,
            "verification_status": "passed",
        },
    }
def _docx_sections(file: FileRecord, structure: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for block in structure.get("blocks", []):
        text = str(block.get("text", ""))
        matched = _matches(text, terms)
        if matched:
            for run in block.get("runs", []) or [{}]:
                run_text = str(run.get("text", ""))
                if not run_text or not _matches(run_text, terms):
                    continue
                sections.append({"file_id": file.file_id, "source_path": file.raw_path, "file_type": "docx", "text": run_text, "normalized_text": unicodedata.normalize("NFKC", run_text), "location": {"paragraph_index": block.get("index"), "run_index": run.get("run_index"), "style_name": block.get("style", "")}, "format": {"bold": run.get("bold"), "italic": run.get("italic"), "underline": run.get("underline"), "font_color": run.get("font_color", "")}, "matched_terms": _matches(run_text, terms)})
            if not block.get("runs"):
                sections.append({"file_id": file.file_id, "source_path": file.raw_path, "file_type": "docx", "text": text, "normalized_text": unicodedata.normalize("NFKC", text), "location": {"paragraph_index": block.get("index"), "style_name": block.get("style", "")}, "format": {}, "matched_terms": matched})
    for table in structure.get("tables", []):
        for row_index, row in enumerate(table.get("rows", [])):
            text = " | ".join(str(value) for value in row)
            matched = _matches(text, terms)
            if matched:
                sections.append({"file_id": file.file_id, "source_path": file.raw_path, "file_type": "docx", "text": text, "normalized_text": unicodedata.normalize("NFKC", text), "location": {"table_index": table.get("table_index"), "row_index": row_index}, "format": {}, "matched_terms": matched})
    return sections


def _pptx_sections(file: FileRecord, structure: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for slide in structure.get("slides", []):
        for shape in slide.get("shapes", []) or []:
            text = str(shape.get("text", ""))
            matched = _matches(text, terms)
            if matched:
                sections.append({"file_id": file.file_id, "source_path": file.raw_path, "file_type": "pptx", "text": text, "normalized_text": unicodedata.normalize("NFKC", text), "location": {"slide_number": slide.get("slide_number"), "shape_index": shape.get("shape_index")}, "format": {"runs": shape.get("runs", [])}, "matched_terms": matched})
        if not slide.get("shapes"):
            for text in slide.get("texts", []):
                matched = _matches(text, terms)
                if matched:
                    sections.append({"file_id": file.file_id, "source_path": file.raw_path, "file_type": "pptx", "text": text, "normalized_text": unicodedata.normalize("NFKC", text), "location": {"slide_number": slide.get("slide_number")}, "format": {}, "matched_terms": matched})
    return sections


def _pdf_sections(file: FileRecord, structure: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for page in structure.get("pages", []):
        blocks = page.get("blocks", []) or []
        if not blocks:
            blocks = [{"lines": [{"spans": [{"text": page.get("text", "")}]}]}]
        for block_index, block in enumerate(blocks):
            text_parts = []
            for line in block.get("lines", []) or []:
                text_parts.extend(str(span.get("text", "")) for span in line.get("spans", []) or [])
            text = "".join(text_parts).strip()
            matched = _matches(text, terms)
            if matched:
                sections.append({"file_id": file.file_id, "source_path": file.raw_path, "file_type": "pdf", "text": text, "normalized_text": unicodedata.normalize("NFKC", text), "location": {"page_number": page.get("page_number"), "block_index": block_index, "bounding_box": block.get("bbox")}, "format": {"spans": block.get("lines", [])}, "matched_terms": matched})
    return sections


def execute_document_question(question: str, operation_names: list[str], files: list[FileRecord], extraction_by_file: dict[str, Any], root: Path) -> dict[str, Any]:
    terms = _terms(question)
    all_sections: list[dict[str, Any]] = []
    for file in files:
        structure = _load_structure(extraction_by_file.get(file.file_id), root)
        if not structure:
            continue
        if file.extension == ".docx":
            all_sections.extend(_docx_sections(file, structure, terms))
        elif file.extension == ".pptx":
            all_sections.extend(_pptx_sections(file, structure, terms))
        elif file.extension == ".pdf":
            all_sections.extend(_pdf_sections(file, structure, terms))
    if not all_sections:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "文書中に一致する位置付き根拠がありません", "failure_stage": "evidence_failure", "operations_executed": operation_names}
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for section in all_sections:
        key = (section["file_id"], json.dumps(section["location"], ensure_ascii=False, sort_keys=True))
        unique[key] = section
    sections = list(unique.values())
    format_terms = {"bold": any(word in question for word in ("太字", "bold")), "italic": any(word in question for word in ("斜体", "italic")), "underline": any(word in question for word in ("下線", "underline"))}
    if "format_extraction" in operation_names and any(format_terms.values()):
        filtered = []
        for section in sections:
            runs = section.get("format", {}).get("runs", []) or [section.get("format", {})]
            if any(all(not wanted or bool(run.get(name)) for name, wanted in format_terms.items()) for run in runs):
                filtered.append(section)
        sections = filtered
    if not sections:
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "指定された書式条件に一致する根拠がありません", "failure_stage": "format_failure", "operations_executed": operation_names}
    allow_multiple = any(word in question for word in ("すべて", "全て", "すべて抜き出", "すべて挙げ"))
    if allow_multiple and "cross_file_aggregation" not in operation_names:
        return {"status": "ambiguous", "answer": "", "evidence": [{**section, "preview_only": False, "source_location": section["location"]} for section in sections[:20]], "warning": "全件抽出には複数資料の横断確認が必要です", "failure_stage": "evidence_failure", "ambiguous": True, "operations_executed": operation_names}
    if len(sections) > 1 and not allow_multiple:
        return {"status": "ambiguous", "answer": "", "evidence": [{**section, "preview_only": False, "source_location": section["location"]} for section in sections[:20]], "warning": "複数の位置付き候補が残り一意に決定できません", "failure_stage": "evidence_failure", "ambiguous": True, "operations_executed": operation_names}
    answer = "\n".join(section["text"] for section in sections[:20])
    if len(answer) > 200 and not allow_multiple:
        return {"status": "ambiguous", "answer": "", "evidence": [{**section, "preview_only": False, "source_location": section["location"]} for section in sections[:20]], "warning": "抽出範囲が広く質問への一意な回答と確認できません", "failure_stage": "evidence_failure", "ambiguous": True, "operations_executed": operation_names}
    evidence = [{**section, "preview_only": False, "source_location": section["location"]} for section in sections[:20]]
    return {"status": "success", "answer": answer, "evidence": evidence, "operations_executed": operation_names, "calculation_trace": []}


# 条件付き抽出の正式経路。上の互換実装は既存デバッグ結果を読む用途に残す。
def execute_document_question(
    question: str,
    operation_names: list[str],
    files: list[FileRecord],
    extraction_by_file: dict[str, Any],
    root: Path,
    work_dir: Path | None = None,
    question_id: int | None = None,
    available_files: list[FileRecord] | None = None,
    search_question: str | None = None,
) -> dict[str, Any]:
    from .extraction_spec import build_extraction_spec
    from .question_conditioned_extractor import extract_conditioned

    markdown_result = _markdown_definition_lookup(question, files, root)
    if markdown_result is not None:
        return markdown_result
    spec = build_extraction_spec(question)
    files = _resolve_document_files(search_question or question, files, available_files or files)
    if "location_lookup" in operation_names:
        from .location_executor import resolve_location_files

        files = resolve_location_files(search_question or question, files, available_files or files)
    structures: dict[str, dict[str, Any]] = {}
    for file in files:
        structure = _load_structure(extraction_by_file.get(file.file_id), root)
        if structure:
            structures[file.file_id] = structure
    if "format_extraction" in operation_names:
        from .format_executor import execute_format_question

        format_output = execute_format_question(question, files, structures, operation_names)
        if format_output.get("status") == "success" or format_output.get("failure_stage") in {"format_failure", "spec_generation_failure", "uniqueness_failure"}:
            if work_dir:
                import json
                work_dir.mkdir(parents=True, exist_ok=True)
                with (work_dir / "format_execution_evidence.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"question_id": question_id, **format_output}, ensure_ascii=False) + "\n")
            return format_output
    if "location_lookup" in operation_names:
        from .location_executor import execute_location_question

        location_result = execute_location_question(search_question or question, files, structures, available_files or files)
        # 旧来の章番号抽出が再現可能な場合は、そのEvidenceを保ったまま利用する。
        # 新しい位置単位の候補が失敗したときだけ、既存の章位置経路を確認する。
        if location_result.get("status") != "success":
            from .location_executor import execute_heading_location

            legacy_location = execute_heading_location(search_question or question, files, structures)
            if legacy_location and legacy_location.get("status") == "success":
                location_result = legacy_location
        if work_dir:
            import json
            work_dir.mkdir(parents=True, exist_ok=True)
            with (work_dir / "location_execution_evidence.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"question_id": question_id, **location_result}, ensure_ascii=False) + "\n")
        return location_result

    from .location_executor import execute_heading_location

    location_result = execute_heading_location(question, files, structures)
    if location_result is not None:
        return location_result
    has_explicit_target = bool(spec.search_terms or spec.identifier_terms or spec.location_requirement)
    has_format_target = any(value is not None for value in spec.format_conditions.values())
    if (spec.target_type in {"text", "heading"} and not has_explicit_target and not spec.verbatim) or (has_format_target and not has_explicit_target and not spec.verbatim) or (spec.verbatim and not has_explicit_target and not has_format_target) or ("format_extraction" in operation_names and not spec.verbatim and not (spec.identifier_terms or spec.search_terms)):
        if work_dir:
            import json
            work_dir.mkdir(parents=True, exist_ok=True)
            with (work_dir / "extraction_specs.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"question_id": question_id, "question": question, "spec": spec.to_dict()}, ensure_ascii=False) + "\n")
        return {"status": "unsupported", "answer": "", "evidence": [], "warning": "意味解釈だけでは抽出対象を一意に構造化できません", "failure_stage": "spec_generation_failure", "operations_executed": operation_names, "extraction_spec": spec.to_dict(), "question_type": _question_type(spec), "used_file_ids": [file.file_id for file in files]}
    result = extract_conditioned(question, spec, files, structures)
    verification = result.get("verification", {})
    evidence = []
    for item in result.get("items", []):
        evidence.append({**item, "source_location": item.get("location", {}), "preview_only": False})
    if work_dir:
        import json

        def append_jsonl(path: Path, row: dict[str, Any]) -> None:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

        work_dir.mkdir(parents=True, exist_ok=True)
        append_jsonl(work_dir / "extraction_specs.jsonl", {"question_id": question_id, "question": question, "spec": spec.to_dict()})
        for item in result.get("items", []):
            item["question_id"] = question_id
            append_jsonl(work_dir / "extraction_candidates.jsonl", item)
            append_jsonl(work_dir / "reconstructed_items.jsonl", item)
        append_jsonl(work_dir / "document_verification.jsonl", {"question_id": question_id, **verification})
    if not result.get("answer"):
        return {"status": "unsupported", "answer": "", "evidence": evidence, "warning": "条件付き抽出またはEvidence Verificationに失敗しました", "failure_stage": "verification_failure", "ambiguous": verification.get("uniqueness") is False, "operations_executed": operation_names, "extraction_spec": spec.to_dict(), "extraction_result": result, "verification": verification, "question_type": _question_type(spec), "used_file_ids": [file.file_id for file in files]}
    return {"status": "success", "answer": result["answer"], "evidence": evidence, "operations_executed": operation_names, "calculation_trace": [], "extraction_spec": spec.to_dict(), "extraction_result": result, "verification": verification, "question_type": _question_type(spec), "used_file_ids": [file.file_id for file in files]}


def _question_type(spec: Any) -> str:
    if spec.target_type == "location" or spec.location_requirement:
        return "location"
    if spec.target_type == "identifier_record":
        return "identifier_verbatim"
    if any(value is not None for value in spec.format_conditions.values()):
        return "format_only"
    return "semantic_document_lookup"


def _resolve_document_files_legacy(question: str, selected_files: list[FileRecord], available_files: list[FileRecord]) -> list[FileRecord]:
    """同一案件内で質問の明示資料種別に一致するraw文書へ再解決する。"""
    q = question.lower()
    hints: list[str] = []
    if any(token in question for token in ("最終報告", "最終分析", "報告書")):
        hints.extend(["06.", "報告書", "最終"])
    elif "スケジュール" in question or "タスクID" in question or "タスクＩＤ" in question:
        hints.extend(["02.", "スケジュール", "計画"])
    elif "契約書" in question:
        hints.extend(["01.", "契約"])
    elif "提案書" in question:
        hints.extend(["00.", "提案"])
    elif "中間報告" in question:
        hints.extend(["中間", "報告資料", "05."])
    if not hints:
        return selected_files
    project_names = {file.project_name for file in selected_files if file.project_name}
    pool = [file for file in available_files if file.extension in {".docx", ".pptx", ".pdf", ".xlsx"} and (not project_names or file.project_name in project_names)]
    scored: list[tuple[int, FileRecord]] = []
    for file in pool:
        path_text = file.raw_path.lower()
        score = sum(2 if hint.lower() in path_text else 0 for hint in hints)
        if score:
            scored.append((score, file))
    if not scored:
        return selected_files
    best = max(score for score, _ in scored)
    resolved = [file for score, file in scored if score == best]
    return resolved[:8]


def _resolve_document_files(question: str, selected_files: list[FileRecord], available_files: list[FileRecord]) -> list[FileRecord]:
    """質問の資料種別・拡張子を同一案件のraw資料へ決定的に反映する。"""
    import unicodedata

    q = unicodedata.normalize("NFKC", question or "").lower()
    if any(token in q for token in ("最終報告", "最終報告書", "報告書")):
        hints = ["06.", "最終報告"]
    elif any(token in q for token in ("スケジュール", "タスクid", "タスクＩＤ")):
        hints = ["02.", "スケジュール"]
    elif "契約書" in q:
        hints = ["01.", "契約書"]
    elif "提案書" in q:
        hints = ["00.", "提案書"]
    elif any(token in q for token in ("中間報告", "中間レビュー", "中間報告資料")):
        hints = ["05.", "報告資料"]
    else:
        return selected_files

    if "docx" in q:
        allowed_types = {".docx"}
    elif "pptx" in q:
        allowed_types = {".pptx"}
    elif "pdf" in q:
        allowed_types = {".pdf"}
    else:
        allowed_types = {".docx", ".pptx", ".pdf", ".xlsx"}

    project_names = {file.project_name for file in selected_files if file.project_name}
    compact_question = re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龯]", "", q)
    inferred_projects: set[str] = set()
    inferred_folders: set[str] = set()
    for file in available_files:
        compact_project = re.sub(
            r"[^0-9a-zぁ-んァ-ヶ一-龯]",
            "",
            unicodedata.normalize("NFKC", file.project_name or "").lower(),
        )
        # 法人格を省いた案件名でも、質問内の案件名と照合できるようにする。
        for prefix in ("株式会社", "医療法人社団"):
            compact_project = compact_project.replace(prefix.lower(), "")
        if compact_project and compact_project in compact_question:
            inferred_projects.add(file.project_name)
        parts = [part for part in unicodedata.normalize("NFC", file.raw_path).replace("\\", "/").split("/") if part]
        if "プロジェクト" in parts:
            folder = parts[parts.index("プロジェクト") + 1] if parts.index("プロジェクト") + 1 < len(parts) else ""
            compact_folder = re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龯]", "", unicodedata.normalize("NFC", folder).lower())
            for prefix in ("株式会社", "医療法人社団"):
                compact_folder = compact_folder.replace(prefix.lower(), "")
            if compact_folder and compact_folder in compact_question:
                inferred_folders.add(folder)
    if inferred_projects:
        project_names = inferred_projects

    pool = [
        file for file in available_files
        if file.extension.lower() in allowed_types and not file.is_temp_office_file
        and (not inferred_folders and (not project_names or file.project_name in project_names) or inferred_folders and any(unicodedata.normalize("NFC", folder) in unicodedata.normalize("NFC", file.raw_path) for folder in inferred_folders))
    ]
    scored: list[tuple[int, FileRecord]] = []
    for file in pool:
        path_text = unicodedata.normalize("NFKC", file.raw_path).lower()
        score = sum(3 if hint.lower() in path_text else 0 for hint in hints)
        if "提案書" in q and "提案書" in path_text:
            score += 2
        if "中間報告資料" in q and "報告資料" in path_text:
            score += 2
        if score:
            scored.append((score, file))
    if not scored:
        return selected_files
    best = max(score for score, _ in scored)
    return sorted(
        (file for score, file in scored if score == best),
        key=lambda file: (unicodedata.normalize("NFKC", file.raw_path).casefold(), file.file_id),
    )[:8]
