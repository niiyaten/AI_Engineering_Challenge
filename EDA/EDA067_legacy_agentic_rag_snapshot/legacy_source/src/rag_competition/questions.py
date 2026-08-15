from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from .io_utils import assert_formal_input_allowed, write_csv, write_jsonl
from .schemas import QuestionAnalysis, to_dict
from .source_requirements import infer_source_requirement, source_requirement_dict
from .cross_source_calculation import is_cross_source_calculation_question
from .id_count_executor import build_count_spec


def read_questions(path: Path, project_root: Path) -> list[tuple[int, str]]:
    """raw質問CSVを読み、validの正解列は使わずindexとquestionだけを返す。"""
    assert_formal_input_allowed(path, project_root)
    rows: list[tuple[int, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append((int(row["index"]), row["question"]))
    return rows


def _find_glossary_doc_legacy(raw_root: Path, project_root: Path) -> Path | None:
    """raw共有ドライブから社内用語集を探す。"""
    for path in raw_root.rglob("社内用語集.docx"):
        assert_formal_input_allowed(path, project_root)
        return path
    return None


def read_glossary(path: Path | None, project_root: Path) -> dict[str, str]:
    if path is None:
        return {}
    assert_formal_input_allowed(path, project_root)
    from docx import Document

    document = Document(path)
    mapping: dict[str, str] = {}
    for table in document.tables:
        if not table.rows:
            continue
        headers = [unicodedata.normalize("NFKC", cell.text.strip()).replace("\xa0", " ") for cell in table.rows[0].cells]
        for row in table.rows[1:]:
            cells = [unicodedata.normalize("NFKC", cell.text.strip()).replace("\xa0", " ") for cell in row.cells]
            if len(cells) < 2:
                continue
            if "正式名称" in headers and "社内用語" in headers:
                official = cells[headers.index("正式名称")]
                term = cells[headers.index("社内用語")]
                if official and term and official != term:
                    mapping[term] = official
            elif "案件名" in headers and "主略称" in headers:
                project = cells[headers.index("案件名")]
                alias = cells[headers.index("主略称")]
                if project and alias and project != alias:
                    mapping[alias] = project
                if "別名候補" in headers:
                    alt_text = cells[headers.index("別名候補")]
                    for alt in re.split(r"[,、/]", alt_text):
                        alt = alt.strip()
                        if project and alt and alt != project:
                            mapping[alt] = project
            else:
                left, right = cells[0], cells[1]
                if left and right and left != right and left.lower() not in {"略称", "用語", "key"}:
                    mapping[right] = left
    return mapping


def find_glossary_doc(raw_root: Path, project_root: Path) -> Path | None:
    """raw共有ドライブ内から、表記揺れを許容して社内用語集を探す。"""
    for path in raw_root.rglob("*.docx"):
        name = unicodedata.normalize("NFKC", path.name)
        if "社内用語集" in name:
            assert_formal_input_allowed(path, project_root)
            return path
    return None


def _replace_terms_regex(question: str, mapping: dict[str, str]) -> tuple[str, list[dict[str, object]]]:
    """用語展開は元質問に対して一度だけ適用し、置換後の文字列を再置換しない。"""
    replaced: list[dict[str, object]] = []
    if not mapping:
        return question, replaced
    pattern = re.compile("|".join(re.escape(token) for token in sorted(mapping, key=len, reverse=True)))

    def substitute(match: re.Match[str]) -> str:
        token = match.group(0)
        replacement = mapping[token]
        replaced.append({"token": token, "replacement": replacement, "count": 1})
        return replacement

    expanded = pattern.sub(substitute, question)
    counts: dict[tuple[str, str], int] = {}
    for item in replaced:
        key = (str(item["token"]), str(item["replacement"]))
        counts[key] = counts.get(key, 0) + 1
    replaced = [{"token": token, "replacement": replacement, "count": count} for (token, replacement), count in counts.items()]
    return expanded, replaced


def replace_terms(question: str, mapping: dict[str, str]) -> tuple[str, list[dict[str, object]]]:
    """同じ語の一部が重なる場合も、左端の最長語を一度だけ展開する。"""
    candidates: list[tuple[int, int, str, str]] = []
    for token, replacement in mapping.items():
        if not token:
            continue
        for match in re.finditer(re.escape(token), question):
            # 英数字の略称はファイル名や別の識別子の一部まで展開しない。
            if token.isascii() and token.isalnum():
                before = question[match.start() - 1] if match.start() else ""
                after = question[match.end()] if match.end() < len(question) else ""
                if (before and (before.isascii() and (before.isalnum() or before == "_"))) or (
                    after and (after.isascii() and (after.isalnum() or after == "_"))
                ):
                    continue
            candidates.append((match.start(), match.end(), token, replacement))
    selected: list[tuple[int, int, str, str]] = []
    for start, end, token, replacement in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(start < other_end and end > other_start for other_start, other_end, _, _ in selected):
            continue
        selected.append((start, end, token, replacement))
    selected.sort()
    parts: list[str] = []
    rows: list[dict[str, object]] = []
    cursor = 0
    for start, end, token, replacement in selected:
        parts.append(question[cursor:start]); parts.append(replacement); cursor = end
        rows.append({"token": token, "replacement": replacement, "count": 1})
    parts.append(question[cursor:])
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row["token"]), str(row["replacement"]))
        counts[key] = counts.get(key, 0) + 1
    return "".join(parts), [{"token": token, "replacement": replacement, "count": count} for (token, replacement), count in counts.items()]


def normalize_question_text(question: str) -> str:
    """質問の意味を変えずに、Unicode・空白・不可視文字だけを整える。"""
    text = unicodedata.normalize("NFKC", question or "")
    text = "".join(char for char in text if unicodedata.category(char) not in {"Cf", "Cc"} or char in {"\n", "\t"})
    text = re.sub(r"[\t\r\n ]+", " ", text).strip()
    return text


def question_encoding_warning(original: str, normalized: str) -> str:
    """文字化けらしい制御文字や置換文字を、回答処理前に記録する。"""
    if "\ufffd" in original or any(unicodedata.category(char) == "Co" for char in original):
        return "question_text_corrupted"
    if original and not normalized:
        return "question_text_corrupted"
    return ""


def extract_hints(question: str) -> tuple[list[str], list[str], list[str]]:
    document_hints = re.findall(r"[\w一-龥ぁ-んァ-ンー]+(?:\.docx|\.pptx|\.xlsx|\.pdf|\.csv|\.tsv|\.py|\.ipynb|\.md|\.png|\.jpg)", question, flags=re.IGNORECASE)
    identifier_hints = re.findall(r"\b[A-Z]{1,5}[-_]?\d{1,4}\b|[A-Za-z_]+(?:_score|_ratio|_id|_depth)?", question)
    date_hints = re.findall(r"20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}", question)
    return list(dict.fromkeys(document_hints)), list(dict.fromkeys(identifier_hints)), list(dict.fromkeys(date_hints))


def infer_routes(question: str) -> tuple[list[str], list[str], bool, bool]:
    text = question.lower()
    routes: list[str] = []
    file_types: list[str] = []
    if any(word in question for word in ["old", "旧版", "最新版", "比較", "変更", "差分", "更新内容"]):
        routes.append("diff_comparison")
    if any(word in question for word in ["太字", "下線", "イタリック", "ハイライト", "色", "コメント", "マーカー"]):
        routes.append("format_extraction")
    if any(word in question for word in ["合計", "平均", "差", "割合", "率", "ランキング", "何倍", "小数", "計算", "相関"]):
        routes.append("calculation")
    if any(word in question for word in ["表", "シート", "セル", "列", "行", "xlsx", "csv", "tsv"]):
        routes.append("table_lookup")
    if any(word in question for word in ["画像", "figure", "png", "グラフ", "図"]):
        routes.append("image_ocr")
    if any(word in question for word in ["python", "コード", "ipynb", "notebook", "パラメータ", "モデル"]):
        routes.append("code_execution")
    if any(word in question for word in ["全案件", "各案件", "横断", "すべての案件"]):
        routes.append("cross_file_aggregation")
    # 位置を尋ねる質問は文書検索だけでなく位置Executorへ明示的に渡す。
    if re.search(r"\u30da\u30fc\u30b8|\u30b9\u30e9\u30a4\u30c9|\u30b7\u30fc\u30c8\u540d|\u30bb\u30eb\u756a\u5730|\u7ae0\u756a\u53f7|\u6bb5\u843d|\u4f4d\u7f6e", question):
        routes.append("location_lookup")
    if not routes:
        routes.append("document_qa")

    for ext in [".docx", ".pptx", ".xlsx", ".pdf", ".csv", ".tsv", ".py", ".ipynb", ".md", ".png", ".jpg"]:
        if ext.lstrip(".") in text:
            file_types.append(ext.lstrip("."))
    if "table_lookup" in routes or "calculation" in routes:
        file_types.extend(["xlsx", "csv", "tsv"])
    if "diff_comparison" in routes:
        file_types.extend(["pptx", "docx", "xlsx", "pdf"])
    if "format_extraction" in routes:
        file_types.extend(["docx", "pptx", "xlsx"])
    if "image_ocr" in routes:
        file_types.extend(["png", "jpg", "pdf", "pptx", "docx"])
    return list(dict.fromkeys(routes)), list(dict.fromkeys(file_types)), len(routes) > 1 or "diff_comparison" in routes, "cross_file_aggregation" in routes


def infer_routes(question: str) -> tuple[list[str], list[str], bool, bool]:
    """正規化済み質問から、資料形式と汎用処理の候補を機械的に抽出する。"""
    routes: list[str] = []
    file_types: list[str] = []
    if any(token in question for token in ("old", "旧版", "最新版", "比較", "変更された")):
        routes.append("diff_comparison")
    if any(token in question for token in ("太字", "斜体", "イタリック", "下線", "ハイライト", "黄色", "赤で強調", "マーカー", "コメント")):
        routes.append("format_extraction")
    if any(token in question for token in ("合計", "平均", "差", "割合", "件数", "最も高い", "最も低い", "計算")):
        routes.append("calculation")
    table_phrases = ("表形式", "表データ", "シート", "セル", "列名", "列を", "行を", "何行", ".xlsx", ".csv", ".tsv", "Pivot")
    if any(token in question for token in table_phrases):
        routes.append("table_lookup")
    if any(token in question.lower() for token in ("python", ".py", "ipynb", "notebook", "コード", "dtype", "関数", "変数")):
        routes.append("code_execution")
    if any(token in question for token in ("画像", "グラフ", "図", "配置")):
        routes.append("image_ocr")
    if any(token in question for token in ("全案件", "すべての案件", "横断")):
        routes.append("cross_file_aggregation")
    if not routes:
        routes.append("document_qa")
    for ext in (".docx", ".pptx", ".xlsx", ".pdf", ".csv", ".tsv", ".py", ".ipynb"):
        if ext in question.lower():
            file_types.append(ext[1:])
    if "format_extraction" in routes:
        file_types.extend(["docx", "pptx"])
    if "table_lookup" in routes or "calculation" in routes:
        file_types.extend(["xlsx", "csv", "tsv"])
    if "diff_comparison" in routes:
        file_types.extend(["docx", "pptx", "pdf", "xlsx"])
    if "code_execution" in routes:
        file_types.extend(["py", "ipynb"])
    return list(dict.fromkeys(routes)), list(dict.fromkeys(file_types)), len(routes) > 1, "cross_file_aggregation" in routes


def analyze_questions(raw_questions: list[tuple[int, str]], glossary: dict[str, str], output_dir: Path) -> list[QuestionAnalysis]:
    analyses: list[QuestionAnalysis] = []
    replacement_rows: list[dict[str, object]] = []
    for index, question in raw_questions:
        normalized = normalize_question_text(question)
        expanded, replaced = replace_terms(normalized, glossary)
        search_text = " ".join(dict.fromkeys(part for part in (normalized, expanded) if part))
        for item in replaced:
            replacement_rows.append({"index": index, **item})
        document_hints, identifier_hints, date_hints = extract_hints(normalized)
        routes, file_types, multiple, cross_project = infer_routes(normalized)
        # 位置を尋ねる質問は、文書検索だけでなく位置Executorへ渡す。
        if re.search(r"\u30da\u30fc\u30b8|\u30b9\u30e9\u30a4\u30c9|\u30b7\u30fc\u30c8\u540d|\u30bb\u30eb\u756a\u5730", normalized):
            routes = list(dict.fromkeys(routes + ["location_lookup"]))
            file_types = list(dict.fromkeys(file_types + ["docx", "pptx", "pdf", "xlsx", "ipynb"]))
        # 複数資料の同一指標を使う差分計算は、文書検索ではなく計算経路へ送る。
        count_spec = build_count_spec(normalized)
        if count_spec and count_spec.target_id_types:
            routes = ["cross_file_aggregation", "calculation"] if count_spec.source_requirements.get("source_cardinality") == "all_matching" else ["table_lookup", "table_filter", "table_aggregation", "calculation"]
        elif is_cross_source_calculation_question(normalized):
            routes = ["cross_file_aggregation", "calculation"]
            file_types = []
        source_requirement = infer_source_requirement(normalized, required_file_types=file_types)
        # 実行操作が複数でも、必要な情報源が1ファイルとは限らないため別々に判定する。
        multiple = source_requirement.source_cardinality in {"pair", "multiple", "all_matching"}
        analyses.append(
            QuestionAnalysis(
                index=index,
                question_original=question,
                question_normalized=normalized,
                question_term_expanded=expanded,
                question_for_search=search_text,
                encoding_warning=question_encoding_warning(question, normalized),
                replaced_terms=replaced,
                document_hints=document_hints,
                identifier_hints=identifier_hints,
                date_hints=date_hints,
                provisional_routes=routes,
                required_file_types=file_types,
                needs_multiple_files=multiple,
                needs_cross_project=cross_project,
                source_requirement=source_requirement_dict(source_requirement),
            )
        )
    write_jsonl(output_dir / "question_analysis.jsonl", [to_dict(item) for item in analyses])
    write_csv(output_dir / "abbreviation_replacement_log.csv", replacement_rows, ["index", "token", "replacement", "count"])
    return analyses
