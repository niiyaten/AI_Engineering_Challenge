from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from openpyxl.utils.cell import coordinate_to_tuple


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
RAW_ROOT = BASE_DIR / "data" / "raw" / "share"
INPUT_LOG = BASE_DIR / "EDA" / "EDA036" / "tables" / "test_openrouter_structured_answer_log.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda037_unhandled_routes_submission.zip"
UNKNOWN = "わかりません"


@dataclass
class Candidate:
    answer: str
    method: str
    confidence: str
    source_paths: list[str]
    evidence: str
    subtype: str
    needs_review: bool = False


PROJECT_ALIASES: dict[str, list[str]] = {
    "かえで": ["かえで", "恒一会"],
    "ひがし丘": ["ひがし丘", "蒼泉会"],
    "みなみ野": ["みなみ野", "蒼樹会", "MINAMINO"],
    "東都": ["東都", "TOTO"],
    "青嶺": ["青嶺", "AOMINE"],
    "青潮": ["青潮", "AOSHIO"],
    "青葉バイオ": ["青葉バイオ", "AOBM"],
    "青葉与信": ["青葉与信", "AYM", "青葉"],
    "白峰": ["白峰", "SHR"],
    "京橋": ["京橋", "KSS", "京ソ"],
}


def normalize_text(value: object) -> str:
    """検索や比較で使う文字列を、欠損を空文字として正規化する。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出CSVへ入れる回答から、タグ、改行、余分な空白を除く。"""
    text = normalize_text(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"\s*\n\s*", "、", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip(" 、")


def relative(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path)


def make_candidate(
    answer: object,
    method: str,
    confidence: str,
    sources: list[Path | str],
    evidence: object,
    subtype: str,
    needs_review: bool = False,
) -> Candidate:
    return Candidate(
        answer=compact_answer(answer),
        method=method,
        confidence=confidence,
        source_paths=[relative(p) for p in sources],
        evidence=normalize_text(evidence)[:6000],
        subtype=subtype,
        needs_review=needs_review,
    )


def empty_candidate(subtype: str, method: str = "not_implemented") -> Candidate:
    return make_candidate("", method, "none", [], "", subtype, True)


def is_usable(candidate: Candidate) -> bool:
    """誤答混入を抑えるため、短く根拠が明確な候補だけを提出へ反映する。"""
    if not candidate.answer or candidate.answer == UNKNOWN:
        return False
    if candidate.confidence not in {"high", "medium"}:
        return False
    if candidate.needs_review and candidate.confidence != "high":
        return False
    if len(candidate.answer) > 260:
        return False
    if re.search(r"=[\s、/]*($|条件)", candidate.answer):
        return False
    bad = ["color=", "</span>", "```", "nan"]
    return not any(marker.lower() in candidate.answer.lower() for marker in bad)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_keywords(question: str) -> list[str]:
    q = normalize_text(question)
    for keys in PROJECT_ALIASES.values():
        if any(k in q for k in keys):
            return keys
    return []


def find_paths(*keywords: str, suffix: str | None = None, root: Path = PROCESSED_ROOT) -> list[Path]:
    """processed/raw配下から、キーワードをすべて含むファイルを探す。"""
    keys = [normalize_text(k).lower() for k in keywords if k]
    results: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if suffix and not normalize_text(path.name).lower().endswith(suffix.lower()):
            continue
        haystack = normalize_text(str(path)).lower().replace("\\", "/")
        if all(key in haystack for key in keys):
            results.append(path)
    return sorted(results, key=lambda p: normalize_text(str(p)))


def token_terms(question: str) -> list[str]:
    """質問文から本文検索に使う語を粗く取り出す。"""
    q = normalize_text(question)
    terms = re.findall(r"[A-Za-z0-9_一-龥ぁ-んァ-ンー]{2,}", q)
    stop = {
        "について", "ください", "答えて", "すべて", "案件", "資料", "ファイル", "フォルダ",
        "おいて", "されて", "あります", "ありますか", "ですか", "もの", "こと",
    }
    selected = []
    for term in terms:
        if term in stop or term.isdigit():
            continue
        if len(term) >= 2 and term not in selected:
            selected.append(term)
    return selected[:12]


def line_search_candidate(question: str, extra_terms: list[str] | None = None) -> Candidate:
    """対象プロジェクト内のMarkdown/JSONから、質問語を多く含む行を抜き出す。"""
    keys = project_keywords(question)
    terms = token_terms(question)
    for alias in keys:
        terms = [t for t in terms if t not in alias]
    if extra_terms:
        terms = list(dict.fromkeys(extra_terms + terms))
    paths: list[Path] = []
    for key in (keys[:1] or [""]):
        paths.extend(find_paths(key, suffix=".md"))
        paths.extend(find_paths(key, suffix=".json"))
    if not paths:
        paths = list(PROCESSED_ROOT.rglob("*.md"))[:300]
    scored: list[tuple[int, str, Path]] = []
    for path in paths:
        text = read_text(path)
        for line in text.splitlines():
            clean = compact_answer(line)
            if len(clean) < 4 or len(clean) > 220:
                continue
            score = sum(1 for term in terms if term.lower() in clean.lower())
            if score:
                scored.append((score, clean, path))
    scored.sort(key=lambda x: (x[0], -len(x[1])), reverse=True)
    if not scored:
        return empty_candidate("line_search")
    best = []
    sources = []
    for _, line, path in scored[:5]:
        if line not in best:
            best.append(line)
            sources.append(path)
    answer = best[0]
    return make_candidate(answer, "generic_line_search", "medium", sources, "\n".join(best), "line_search", needs_review=True)


def load_xlsx_sheets(structure_path: Path) -> list[tuple[dict[str, Any], pd.DataFrame | None]]:
    obj = load_json(structure_path)
    sheets: list[tuple[dict[str, Any], pd.DataFrame | None]] = []
    for sheet in obj.get("sheets", []):
        csv_path = Path(sheet.get("exported_csv_path", ""))
        df = None
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
            except Exception:
                df = None
        sheets.append((sheet, df))
    return sheets


def yellow_cell_context(question: str) -> Candidate:
    """黄色セルの座標だけでなく、同じ行と列の見出しから条件を復元する。"""
    if "train.xlsx" not in question:
        return empty_candidate("xlsx_yellow_cell_context")
    keys = project_keywords(question)
    paths: list[Path] = []
    for key in keys[:1]:
        paths.extend(find_paths(key, "train.xlsx", suffix=".xlsx.structure.json"))
    yellow = {"FFFFFF00", "FFFFEB9C", "FFFFF2CC", "FFFFFF99"}
    rows: list[str] = []
    evidence: list[str] = []
    used: list[Path] = []
    sheet_hint = re.search(r"Sheet\d+", question)
    for path in paths:
        for sheet, df in load_xlsx_sheets(path):
            if df is None:
                continue
            if sheet_hint and sheet.get("sheet_name") != sheet_hint.group(0):
                continue
            for cell in sheet.get("styled_cells", []):
                fill = normalize_text(cell.get("fill_color", "")).upper()
                if fill not in yellow:
                    continue
                row_num, col_num = coordinate_to_tuple(cell["coordinate"])
                if row_num <= 1 or row_num - 2 >= len(df) or col_num - 1 >= len(df.columns):
                    continue
                value = str(df.iloc[row_num - 2, col_num - 1])
                if not value.strip():
                    continue
                col_name = str(df.columns[col_num - 1])
                row_values = {str(k): str(v) for k, v in df.iloc[row_num - 2].to_dict().items() if str(v)}
                label_bits = []
                for k, v in row_values.items():
                    if k != col_name and len(label_bits) < 3:
                        label_bits.append(f"{k}={v}")
                answer = f"{sheet.get('sheet_name')}!{cell['coordinate']}={value}"
                if label_bits:
                    answer += f"、条件: {'、'.join(label_bits)}、集計: {col_name}"
                rows.append(answer)
                evidence.append(f"{relative(path)} {answer}")
                used.append(path)
    unique = list(dict.fromkeys(rows))
    if not unique:
        return empty_candidate("xlsx_yellow_cell_context")
    if len(unique) > 3:
        return make_candidate(" / ".join(unique[:5]), "xlsx_yellow_context_rebuild", "medium", used, "\n".join(evidence), "xlsx_yellow_cell_context", needs_review=True)
    return make_candidate(" / ".join(unique[:3]), "xlsx_yellow_context_rebuild", "medium", used, "\n".join(evidence), "xlsx_yellow_cell_context")


def histogram_range_candidate(question: str) -> Candidate:
    keys = project_keywords(question)
    column_match = re.search(r"AG_ratio|TP|[A-Za-z_]+", question)
    column = column_match.group(0) if column_match else ""
    rank = 3 if "3番目" in question else 1
    paths: list[Path] = []
    for key in keys[:1]:
        paths.extend(find_paths(key, "train.csv.data.csv", suffix=".csv"))
        paths.extend(find_paths(key, "train.xlsx.sheets", "train.csv", suffix=".csv"))
    for path in paths:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            continue
        counts, edges = np.histogram(values, bins=10)
        order = np.argsort(counts)[::-1]
        idx = int(order[rank - 1])
        if "範囲" in question or "ビン" in question:
            answer = f"{edges[idx]:.6f}以上{edges[idx + 1]:.6f}未満"
        else:
            answer = str(int(counts[idx]))
        return make_candidate(answer, "numpy_histogram_10bins", "high", [path], f"column={column}, counts={counts.tolist()}, edges={edges.tolist()}", "histogram_recompute")
    return empty_candidate("histogram_recompute")


def schedule_role_candidate(question: str) -> Candidate:
    keys = project_keywords(question)
    ms = re.search(r"MS\d+", question)
    role = "ビジネスアナリスト" if "ビジネスアナリスト" in question else ""
    paths: list[Path] = []
    for key in keys[:1]:
        paths.extend(find_paths(key, "スケジュール.xlsx.sheets", suffix=".csv"))
    answers: list[str] = []
    evidence: list[str] = []
    for path in paths:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        except Exception:
            continue
        cols = list(df.columns)
        text_df = df.astype(str)
        mask = pd.Series([True] * len(df))
        if ms:
            mask &= text_df.apply(lambda r: r.str.contains(ms.group(0), regex=False).any(), axis=1)
        if role:
            mask &= text_df.apply(lambda r: r.str.contains(role, regex=False).any(), axis=1)
        hit = df[mask]
        id_cols = [c for c in cols if "タスクID" in c or c in {"ID", "TaskID"}]
        for _, row in hit.iterrows():
            if id_cols:
                value = str(row[id_cols[0]])
            else:
                value = next((str(v) for v in row if re.fullmatch(r"T\d+", str(v))), "")
            if value and value not in answers:
                answers.append(value)
                evidence.append(f"{relative(path)}: {row.to_dict()}")
    if not answers:
        return empty_candidate("schedule_ms_role_filter")
    return make_candidate("、".join(answers), "schedule_csv_role_filter", "high", paths, "\n".join(evidence), "schedule_ms_role_filter")


def pptx_all_format_candidate(question: str) -> Candidate:
    keys = project_keywords(question)
    paths: list[Path] = []
    file_hint = ""
    if "会議録" in question:
        file_hint = "会議"
    elif "報告" in question:
        file_hint = "報告"
    for key in keys[:1]:
        if file_hint:
            paths.extend(find_paths(key, file_hint, suffix=".pptx.structure.json"))
            paths.extend(find_paths(key, file_hint, suffix=".docx.structure.json"))
        else:
            paths.extend(find_paths(key, suffix=".pptx.structure.json"))
            paths.extend(find_paths(key, suffix=".docx.structure.json"))
    tokens: list[str] = []
    evidence: list[str] = []
    for path in paths:
        obj = load_json(path)
        for slide in obj.get("slides", []):
            for shape in slide.get("shapes", []):
                for para in (shape.get("text_frame") or {}).get("paragraphs", []):
                    for run in para.get("runs", []):
                        text = compact_answer(run.get("text", ""))
                        if not text:
                            continue
                        if run.get("bold") and run.get("underline") and run.get("italic"):
                            tokens.append(text)
                            evidence.append(f"{relative(path)} slide={slide.get('slide_number')}: {text}")
        for block in obj.get("blocks", []):
            for run in block.get("runs", []):
                text = compact_answer(run.get("text", ""))
                if text and run.get("bold") and run.get("underline") and run.get("italic"):
                    tokens.append(text)
                    evidence.append(f"{relative(path)} block={block.get('block_index')}: {text}")
    unique = [x for x in dict.fromkeys(tokens) if len(x) > 1]
    if not unique:
        return empty_candidate("format_metadata")
    return make_candidate("、".join(unique), "all_bold_underline_italic_runs", "high", paths, "\n".join(evidence), "format_metadata")


def document_page_candidate(question: str) -> Candidate:
    terms = []
    if "WBS" in question:
        terms = ["WBS", "進捗状況"]
    elif "進捗サマリ" in question:
        terms = ["進捗サマリ"]
    elif "F1スコア" in question and "ページ" in question:
        terms = ["F1", "ランキング"]
    elif "第5週" in question:
        terms = ["第5週", "W5", "モデル構築"]
    else:
        terms = token_terms(question)[:4]
    keys = project_keywords(question)
    paths: list[Path] = []
    for key in keys[:1]:
        paths.extend(find_paths(key, suffix=".md"))
    hits: list[str] = []
    sources: list[Path] = []
    for path in paths:
        text = read_text(path)
        if not all(t.lower() in text.lower() for t in terms[:1]):
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if all(t.lower() in line.lower() for t in terms if t):
                context = " ".join(compact_answer(x) for x in lines[max(0, i - 2): i + 3] if compact_answer(x))
                hits.append(context)
                sources.append(path)
                page = re.search(r"(?:page|ページ|p\.)\s*[:：]?\s*(\d+)", context, re.IGNORECASE)
                if page and ("何ページ" in question or "ページ" in question):
                    return make_candidate(f"{page.group(1)}ページ", "document_page_context_search", "high", [path], context, "document_whole_context")
    if hits:
        return make_candidate(hits[0], "document_context_search", "medium", sources[:3], "\n".join(hits[:5]), "document_whole_context", needs_review=True)
    return empty_candidate("document_whole_context")


def diff_candidate(question: str) -> Candidate:
    keys = project_keywords(question)
    q = normalize_text(question)
    paths: list[Path] = []
    if "_v1" in q or "_v2" in q or "_v3" in q:
        for key in keys[:1]:
            paths.extend(find_paths(key, "提案", suffix=".pptx.md"))
    elif "スケジュール_r" in q:
        for key in keys[:1]:
            paths.extend(find_paths(key, "スケジュール_r", suffix=".xlsx.md"))
            paths.extend(find_paths(key, "スケジュール_r", suffix=".csv"))
    elif "old" in q or "最新版" in q:
        for key in keys[:1]:
            paths.extend(find_paths(key, "old", suffix=".md"))
            paths.extend(find_paths(key, "最終報告", suffix=".md"))
    old_paths = [p for p in paths if "old" in normalize_text(p).lower() or "_v1" in normalize_text(p).lower() or "r1" in normalize_text(p).lower()]
    new_paths = [p for p in paths if p not in old_paths]
    if not old_paths or not new_paths:
        return empty_candidate("version_diff")
    old_lines = clean_lines(read_text(old_paths[0]))
    new_lines = clean_lines(read_text(new_paths[-1]))
    diffs = []
    old_set = set(old_lines)
    for line in new_lines:
        if line not in old_set and interesting_diff_line(line):
            diffs.append(line)
    selected = diffs[:4]
    if not selected:
        return make_candidate("変更なし", "text_diff_no_material_change", "medium", [old_paths[0], new_paths[-1]], "material diff lines not found", "version_diff")
    return make_candidate("、".join(selected), "text_diff_added_lines", "medium", [old_paths[0], new_paths[-1]], "\n".join(selected), "version_diff", needs_review=True)


def clean_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        line = compact_answer(line)
        if 6 <= len(line) <= 180 and not line.startswith("|") and not set(line) <= {"-", "#"}:
            lines.append(line)
    return list(dict.fromkeys(lines))


def interesting_diff_line(line: str) -> bool:
    ng = ["ページ", "スライド", "更新", "目次", "会社", "Copyright"]
    if any(x in line for x in ng):
        return False
    return any(x in line for x in ["変更", "追加", "削除", "完了", "未着手", "担当", "工数", "金額", "モデル", "評価", "スケジュール", "リスク"])


def correlation_candidate(question: str) -> Candidate:
    keys = project_keywords(question)
    paths = []
    for key in keys[:1]:
        paths.extend(find_paths(key, "train.csv.data.csv", suffix=".csv"))
    for path in paths:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        nums = df.select_dtypes(include=[np.number])
        if nums.shape[1] < 2:
            continue
        target_cols = [c for c in nums.columns if c.lower() in {"target", "y", "目的変数"} or "target" in c.lower()]
        if not target_cols:
            target_cols = [nums.columns[-1]]
        target = target_cols[0]
        corr = nums.corr(numeric_only=True)[target].drop(labels=[target], errors="ignore").dropna()
        if "負" in question:
            col = corr.idxmin()
        else:
            col = corr.abs().idxmax()
        return make_candidate(col, "raw_csv_correlation", "medium", [path], corr.sort_values().to_string(), "fallback_bm25_llm")
    return empty_candidate("fallback_bm25_llm")


def fallback_dispatch(index: int, question: str, route: str, subtype: str) -> Candidate:
    q = normalize_text(question)
    if "ヒストグラム" in q:
        return histogram_range_candidate(q)
    if "黄色" in q or "ハイライト" in q:
        return yellow_cell_context(q)
    if "太字" in q and "下線" in q and "イタリック" in q:
        return pptx_all_format_candidate(q)
    if "MS3" in q and "ビジネスアナリスト" in q:
        return schedule_role_candidate(q)
    if route == "diff_check" or "比較" in q or "変更" in q:
        return diff_candidate(q)
    if "ページ" in q or "第5週" in q or "進捗サマリ" in q or "WBS" in q:
        return document_page_candidate(q)
    if "相関" in q:
        return correlation_candidate(q)
    return line_search_candidate(q)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame) -> None:
    improved = result_df[result_df["improved"].eq(True)]
    route_summary = (
        result_df.groupby(["route", "subtype"], as_index=False)
        .agg(count=("index", "count"), improved_count=("improved", "sum"))
        .sort_values(["improved_count", "count"], ascending=[False, False])
    )
    view = result_df[result_df["answer_before"].eq(UNKNOWN)][
        ["index", "route", "subtype", "question", "candidate_answer", "answer_after", "improved", "method", "confidence", "needs_review"]
    ]
    report = f"""# EDA037: 未対応routeのローカル候補生成

## 背景と目的

EDA036後もtest 100件中67件が `わかりません` のまま残った。
その多くはLLMが失敗したのではなく、LLMへ渡す構造化候補がまだ作れていないことが原因だった。

EDA037では、未対応routeをまとめて対象にし、差分、文書全体、表計算、書式、fallback検索のローカル候補生成を追加した。

## 結果

- 入力: `EDA/EDA036/tables/test_openrouter_structured_answer_log.csv`
- test件数: {len(result_df)}
- EDA036時点の非 `わかりません`: {int((result_df["answer_before"] != UNKNOWN).sum())}
- EDA037で追加採用した件数: {len(improved)}
- EDA037後の非 `わかりません`: {int((result_df["answer_after"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## route/subtype別集計

凡例: `route` は質問ルート、`subtype` は処理サブタイプ、`count` は件数、`improved_count` はEDA037で新たに非不明回答へ変わった件数を表す。

{route_summary.to_markdown(index=False)}

## unknown質問別ログ

凡例: `candidate_answer` はEDA037で生成した候補、`answer_after` は提出CSVへ入れた回答、`improved` はEDA036の `わかりません` から改善したか、`needs_review` は根拠確認が必要な候補を表す。

{view.to_markdown(index=False)}

## 注意点

差分系と汎用本文検索は、候補生成としては有用だが、誤答混入リスクが高い。
そのため、`needs_review=True` の候補は原則採用していない。
次に精度を上げるには、差分routeをファイル形式別に分け、PPTXスライド、xlsx行、Notebookセルの比較を個別実装する必要がある。
"""
    (OUT_DIR / "eda037_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    base_df = pd.read_csv(INPUT_LOG)

    rows: list[dict[str, Any]] = []
    for _, row in base_df.sort_values("index").iterrows():
        answer_before = compact_answer(row.get("final_answer", ""))
        if not answer_before:
            answer_before = UNKNOWN
        candidate = empty_candidate(str(row.get("subtype", "")))
        answer_after = answer_before
        improved = False
        adopted = False
        if answer_before == UNKNOWN:
            candidate = fallback_dispatch(int(row["index"]), str(row["question"]), str(row["route"]), str(row["subtype"]))
            adopted = is_usable(candidate)
            if adopted:
                answer_after = candidate.answer
                improved = True
        rows.append(
            {
                "index": int(row["index"]),
                "route": row["route"],
                "subtype": candidate.subtype if candidate.subtype else row["subtype"],
                "question": row["question"],
                "answer_before": answer_before,
                "candidate_answer": candidate.answer,
                "answer_after": answer_after,
                "improved": improved,
                "adopted": adopted,
                "method": candidate.method,
                "confidence": candidate.confidence,
                "needs_review": candidate.needs_review,
                "source_paths": " | ".join(candidate.source_paths),
                "evidence": candidate.evidence,
            }
        )

    result_df = pd.DataFrame(rows)
    result_df.to_csv(TABLE_DIR / "test_unhandled_route_candidates.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df)
    manifest = {
        "eda": "EDA037",
        "input": relative(INPUT_LOG),
        "test_count": int(len(result_df)),
        "before_non_unknown_count": int((result_df["answer_before"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved"].sum()),
        "after_non_unknown_count": int((result_df["answer_after"] != UNKNOWN).sum()),
        "outputs": [
            relative(TABLE_DIR / "test_unhandled_route_candidates.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda037_report.md"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
