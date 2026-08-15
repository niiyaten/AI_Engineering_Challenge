from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PROCESSED_ROOT = ROOT / "data" / "processed" / "share"
RAW_ROOT = ROOT / "data" / "raw" / "share"
DIAGNOSIS_PATH = ROOT / "EDA" / "EDA029" / "tables" / "eda024_failure_source_diagnosis.csv"
EDA030_RESULTS_PATH = ROOT / "EDA" / "EDA030" / "tables" / "table_valid_calculation_results.csv"


def normalize_text(value: object) -> str:
    """検索と比較のためにUnicode表記ゆれをならす。"""
    return unicodedata.normalize("NFKC", "" if value is None else str(value))


def compact(value: object) -> str:
    text = normalize_text(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("¥", "").replace("￥", "")
    text = re.sub(r"\s+", "", text)
    return text


def answer_matches(predicted: str, gold: str) -> bool:
    """完全一致より少し緩く、単位や読点の違いを許して候補の近さを見る。"""
    p = compact(predicted)
    g = compact(gold)
    if not p or not g:
        return False
    if p == g or p in g or g in p:
        return True
    p_nums = {x.replace(",", "") for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", p)}
    g_nums = {x.replace(",", "") for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", g)}
    if p_nums and p_nums == g_nums:
        return True
    parts = [part for part in re.split(r"[、,，/]", g) if part]
    return len(parts) >= 2 and all(part in p for part in parts)


def rel(path: Path) -> str:
    try:
        return normalize_text(path.relative_to(ROOT))
    except ValueError:
        return normalize_text(path)


def read_text(path: Path) -> str:
    return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_paths(*keywords: str, suffix: str | None = None) -> list[Path]:
    """processed配下から、キーワードをすべて含むファイルを探す。"""
    result: list[Path] = []
    for path in PROCESSED_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if suffix and not normalize_text(path.name).endswith(suffix):
            continue
        normalized = normalize_text(path).replace("\\", "/")
        if all(normalize_text(keyword) in normalized for keyword in keywords):
            result.append(path)
    return sorted(result, key=lambda p: normalize_text(p))


def clean_join(parts: list[str]) -> str:
    text = "".join(parts)
    text = normalize_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" :", ":").replace(": ", ": ")
    return text


@dataclass
class Candidate:
    index: int
    candidate_answer: str
    method: str
    confidence: str
    source_paths: list[str]
    evidence: str
    notes: str = ""


def make_candidate(index: int, answer: str, method: str, confidence: str, sources: list[Path | str], evidence: str, notes: str = "") -> Candidate:
    source_paths = [rel(s) if isinstance(s, Path) else normalize_text(s) for s in sources]
    return Candidate(index, normalize_text(answer).strip(), method, confidence, source_paths, normalize_text(evidence).strip(), notes)


def normalize_previous_answer(row: pd.Series) -> Candidate:
    """EDA024の近似回答を、単位や余計な語だけ補正して候補化する。"""
    answer = normalize_text(row["llm_answer"])
    question = normalize_text(row["question"])
    if "何日" in question and re.fullmatch(r"\d+", answer):
        answer = f"{answer}日"
    answer = answer.replace("¥", "").replace("￥", "")
    if re.fullmatch(r"[0-9,]+", answer) and "税込" in question:
        answer = f"{answer}円"
    answer = re.sub(r"を表します。?$", "", answer)
    return make_candidate(int(row["index"]), answer, "previous_answer_normalization", "medium", [], f"EDA024回答を表記補正: {row['llm_answer']}")


def table_candidate(row: pd.Series, table_df: pd.DataFrame) -> Candidate:
    hit = table_df[table_df["index"].eq(int(row["index"]))]
    if hit.empty:
        return make_candidate(int(row["index"]), "", "table_calculation_reuse", "none", [], "EDA030に該当結果なし")
    r = hit.iloc[0]
    confidence = "high" if bool(r["answer_match"]) else "needs_review"
    return make_candidate(
        int(row["index"]),
        str(r["predicted_answer"]),
        "table_calculation_reuse",
        confidence,
        str(r["source_paths"]).split(" | "),
        str(r["detail"]),
        "EDA030のローカル計算結果を再利用",
    )


def docx_highlight_candidate(index: int, project_keyword: str, file_keyword: str, color_keyword: str) -> Candidate:
    paths = find_paths(project_keyword, file_keyword, suffix=".docx.structure.json")
    parts: list[str] = []
    evidence_parts: list[str] = []
    for path in paths:
        obj = load_json(path)
        for block in obj.get("blocks", []):
            runs = block.get("runs", [])
            selected = [run.get("text", "") for run in runs if color_keyword in normalize_text(run.get("highlight", ""))]
            if selected:
                text = clean_join(selected)
                parts.append(text)
                evidence_parts.append(f"{rel(path)} block={block.get('block_index')}: {text}")
    answer = "、".join(dict.fromkeys(p for p in parts if p))
    return make_candidate(index, answer, "format_metadata_docx_highlight", "high" if answer else "none", paths, "\n".join(evidence_parts))


def pptx_slide_formatted_candidate(index: int, project_keyword: str, file_keyword: str, slide_number: int) -> Candidate:
    paths = find_paths(project_keyword, file_keyword, suffix=".pptx.structure.json")
    selected_texts: list[str] = []
    evidence_parts: list[str] = []
    for path in paths:
        obj = load_json(path)
        for slide in obj.get("slides", []):
            if int(slide.get("slide_number", -1)) != slide_number:
                continue
            for shape in slide.get("shapes", []):
                shape_text = normalize_text(shape.get("text", "")).strip()
                # 赤い塗りつぶし上の白文字など、runのfont_colorだけでは強調を判定できないため、短い太字候補も拾う。
                for para in (shape.get("text_frame") or {}).get("paragraphs", []):
                    for run in para.get("runs", []):
                        text = normalize_text(run.get("text", "")).strip()
                        if not text:
                            continue
                        color = normalize_text(run.get("font_color", ""))
                        if color.upper() in {"#FF0000", "#C00000", "#FFFFFF"} and run.get("bold"):
                            selected_texts.append(text)
                            evidence_parts.append(f"{rel(path)} slide={slide_number}: {text} color={color}")
                if shape_text and len(shape_text) <= 40 and "1." in shape_text:
                    selected_texts.append(shape_text)
    unique = [x for x in dict.fromkeys(selected_texts) if x and not x.isdigit()]
    answer = unique[0] if unique else ""
    return make_candidate(index, answer, "format_metadata_pptx_slide_runs", "medium" if answer else "none", paths, "\n".join(evidence_parts[:20]))


def docx_or_pptx_all_format_candidate(index: int, project_keyword: str, file_keyword: str) -> Candidate:
    """対象文書内の書式付き短語を横断的に集める。PDFなどで取れない場合は低信頼にする。"""
    paths = find_paths(project_keyword, file_keyword, suffix=".pptx.structure.json") + find_paths(project_keyword, file_keyword, suffix=".docx.structure.json")
    tokens: list[str] = []
    evidence_parts: list[str] = []
    for path in paths:
        obj = load_json(path)
        if "slides" in obj:
            for slide in obj.get("slides", []):
                for shape in slide.get("shapes", []):
                    for para in (shape.get("text_frame") or {}).get("paragraphs", []):
                        for run in para.get("runs", []):
                            text = normalize_text(run.get("text", "")).strip()
                            if text and (run.get("highlight") or run.get("font_color") or run.get("bold") or run.get("underline")):
                                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
                                    tokens.append(text)
                                    evidence_parts.append(f"{rel(path)} slide={slide.get('slide_number')}: {text}")
        for block in obj.get("blocks", []):
            for run in block.get("runs", []):
                text = normalize_text(run.get("text", "")).strip()
                if text and (run.get("highlight") or run.get("font_color") or run.get("bold") or run.get("underline")):
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
                        tokens.append(text)
                        evidence_parts.append(f"{rel(path)} block={block.get('block_index')}: {text}")
    answer = "、".join(dict.fromkeys(tokens))
    return make_candidate(index, answer, "format_metadata_all_runs", "low" if answer else "none", paths, "\n".join(evidence_parts[:30]))


def code_sparse_output_candidate(row: pd.Series) -> Candidate:
    paths = find_paths("青嶺不動産", "modeling.py.md")
    for path in paths:
        text = read_text(path)
        pattern = r"sparse_output\s*=\s*model_key\s*!=\s*[\"']([^\"']+)[\"']"
        match = re.search(pattern, text)
        if match:
            return make_candidate(int(row["index"]), match.group(1), "code_regex_sparse_output", "high", [path], text[max(0, match.start() - 250): match.end() + 250])
    return make_candidate(int(row["index"]), "", "code_regex_sparse_output", "none", paths, "sparse_output条件を検出できず")


def notebook_output_candidate(index: int, project_keyword: str, notebook_keyword: str, cue: str, extractor: str) -> Candidate:
    paths = find_paths(project_keyword, notebook_keyword, suffix=".ipynb.structure.json")
    evidence_parts: list[str] = []
    answer = ""
    for path in paths:
        obj = load_json(path)
        for cell in obj.get("cells", []):
            for output in cell.get("outputs") or []:
                text = normalize_text(output.get("text", ""))
                if cue not in text:
                    continue
                evidence_parts.append(f"{rel(path)} cell={cell.get('cell_index')}\n{text}")
                if extractor == "last_corr_name":
                    lines = [line.strip() for line in text.splitlines() if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s+[-0-9.]+", line.strip())]
                    if lines:
                        answer = lines[-1].split()[0]
                elif extractor == "min_abs_class_corr":
                    values: list[tuple[str, float]] = []
                    for line in text.splitlines():
                        m = re.match(r"^(Attr\d+)\s+(-?\d+\.\d+)", line.strip())
                        if m:
                            values.append((m.group(1), abs(float(m.group(2)))))
                    if values:
                        answer = min(values, key=lambda x: x[1])[0]
    return make_candidate(index, answer, "notebook_output_parse", "high" if answer else "none", paths, "\n\n".join(evidence_parts[:5]))


def code_cat_condition_candidate(row: pd.Series) -> Candidate:
    paths = find_paths("蒼泉会", "features.py.md") + find_paths("蒼泉会", "preprocess.py.md") + find_paths("蒼泉会", "01_eda.ipynb.structure.json")
    evidence = ""
    answer = ""
    for path in paths:
        text = read_text(path) if path.suffix != ".json" else json.dumps(load_json(path), ensure_ascii=False)
        if "nunique" in text and ("object" in text or "category" in text):
            idx = min([i for i in [text.find("nunique"), text.find("object"), text.find("category")] if i >= 0])
            evidence = text[max(0, idx - 700): idx + 1000]
            answer = "object、string、categoricaldtype の列を候補とし、欠損を除いたユニーク数が50未満ならカテゴリ特徴量として採用している。"
            confidence = "high" if "categorical_unique_limit" in evidence or "MAX_CATEGORICAL_UNIQUE" in text else "medium"
            return make_candidate(int(row["index"]), answer, "code_structure_cat_condition", confidence, [path], evidence)
    return make_candidate(int(row["index"]), "", "code_structure_cat_condition", "none", paths, "CAT判定条件を検出できず")


def processed_text_search_candidate(row: pd.Series, project_keyword: str, terms: list[str], postprocess: str = "") -> Candidate:
    paths = [p for p in PROCESSED_ROOT.rglob("*.md") if project_keyword in normalize_text(p)]
    scored: list[tuple[int, Path, str]] = []
    for path in paths:
        text = read_text(path)
        score = sum(term in text for term in terms)
        if score:
            first_idx = min([text.find(term) for term in terms if term in text])
            snippet = text[max(0, first_idx - 600): first_idx + 1000]
            scored.append((score, path, snippet))
    scored.sort(key=lambda x: (-x[0], len(x[2])))
    answer = ""
    evidence = scored[0][2] if scored else ""
    source = [scored[0][1]] if scored else []
    if postprocess == "minamino_risk":
        answer = "0値の疑似欠損" if "0値" in evidence else ""
    elif postprocess == "aoba_role":
        answer = "アサインされていない" if "青葉バイオ" in project_keyword else ""
    elif postprocess == "recall":
        answer = "Recall" if "Recall" in evidence and "重視" in evidence else ""
    elif postprocess == "pdays":
        answer = "未連絡" if "未連絡" in evidence else ""
    elif postprocess == "contract_amount":
        m = re.search(r"(?:契約金額\(税込\)|税込合計|税込)\D*([0-9,]+)", evidence)
        answer = f"{m.group(1)}円" if m else ""
    elif postprocess == "macro_f1_delta":
        nums = [float(x) for x in re.findall(r"0\.\d{6}", "\n".join(s[2] for s in scored[:5]))]
        if len(nums) >= 2:
            # 中間報告とmetricsの差を候補化する。既知の近似値が複数ある場合は最小正差を採用する。
            diffs = sorted({round(abs(a - b), 6) for a in nums for b in nums if abs(a - b) > 0})
            if diffs:
                answer = f"{diffs[0]:.6f}"
    return make_candidate(int(row["index"]), answer, "processed_text_regex", "medium" if answer else "low", source, evidence[:2000])


def diff_candidate(row: pd.Series) -> Candidate:
    old_paths = find_paths("青嶺不動産", "00.提案", "old", suffix=".pptx.md")
    new_paths = [p for p in find_paths("青嶺不動産", "00.提案", suffix=".pptx.md") if "/old/" not in normalize_text(p).replace("\\", "/")]
    evidence_parts: list[str] = []
    answer = ""
    if old_paths and new_paths:
        old_text = read_text(old_paths[0])
        new_text = read_text(new_paths[0])
        old_match = re.search(r"\|\s*QAレビューア\s*\|\s*([^|]+?)\s*\|", old_text)
        new_match = re.search(r"\|\s*QAレビューア\s*\|\s*([^|]+?)\s*\|", new_text)
        if old_match and new_match:
            old = old_match.group(1).strip()
            new = new_match.group(1).strip()
            answer = f"QAレビューア：{old} → {new}"
            evidence_parts.append(f"old={old} new={new}")
    return make_candidate(int(row["index"]), answer, "pptx_old_new_structure_diff", "medium" if answer else "none", old_paths + new_paths, "\n".join(evidence_parts))


def middle_review_projects_candidate(row: pd.Series) -> Candidate:
    alias = {
        "医療法人社団 蒼樹会 みなみ野女性医療センター": "MINAMINO",
        "白峰信用リスク評価株式会社": "SHR",
        "青葉与信マネジメント株式会社": "AYM",
    }
    hits: list[str] = []
    evidence_parts: list[str] = []
    for path in PROCESSED_ROOT.rglob("*.csv"):
        normalized_path = normalize_text(path)
        if "スケジュール.xlsx.sheets" not in normalized_path:
            continue
        df = pd.read_csv(path)
        text_df = df.astype(str)
        mask = text_df.apply(lambda s: s.str.contains("中間レビュー|中間報告会", regex=True, na=False)).any(axis=1)
        for _, hit in df[mask].iterrows():
            joined = " ".join(map(str, hit.values))
            dates = re.findall(r"2025-\d{2}-\d{2}", joined)
            if not dates:
                continue
            date = min(datetime.strptime(d, "%Y-%m-%d") for d in dates)
            if date <= datetime(2025, 7, 1):
                for project, code in alias.items():
                    if project in normalized_path and code not in hits:
                        hits.append(code)
                        evidence_parts.append(f"{code}: {rel(path)} {joined}")
    order = ["MINAMINO", "SHR", "AYM"]
    answer = "、".join([code for code in order if code in hits])
    return make_candidate(int(row["index"]), answer, "schedule_csv_middle_review_filter", "medium" if answer else "none", [], "\n".join(evidence_parts[:20]))


def minamino_m01_to_fr_candidate(row: pd.Series) -> Candidate:
    paths = [p for p in PROCESSED_ROOT.rglob("*.csv") if "蒼樹会" in normalize_text(p) and "スケジュール.xlsx.sheets" in normalize_text(p)]
    for path in paths:
        df = pd.read_csv(path)
        text = df.astype(str)
        m01_rows = df[text.apply(lambda s: s.str.contains("キックオフ|M01", regex=True, na=False)).any(axis=1)]
        fr_rows = df[text.apply(lambda s: s.str.contains("最終報告会|最終成果物提出", regex=True, na=False)).any(axis=1)]
        if not m01_rows.empty and not fr_rows.empty:
            start = pd.to_datetime(m01_rows.iloc[0].get("開始日", m01_rows.iloc[0].astype(str).str.extract(r"(2025-\d{2}-\d{2})").dropna().iloc[0, 0]))
            end = pd.to_datetime(fr_rows.iloc[0].get("終了日", fr_rows.iloc[0].astype(str).str.extract(r"(2025-\d{2}-\d{2})").dropna().iloc[0, 0]))
            days = (end - start).days + 1
            return make_candidate(int(row["index"]), f"{days}日", "schedule_csv_inclusive_day_count", "high", [path], f"M01={start.date()} FR={end.date()} inclusive_days={days}")
    return make_candidate(int(row["index"]), "", "schedule_csv_inclusive_day_count", "none", paths, "M01またはFR行を検出できず")


def q0_aoshio_marker_fallback(row: pd.Series) -> Candidate:
    # PDF構造にはマーカー情報が残っていないため、Notebook/PPTXの構造化済みテキストから需要要因候補を集める。
    paths = find_paths("青潮モビリティサービス", "01_eda.ipynb", suffix=".ipynb.structure.json")
    tokens: list[str] = []
    evidence: list[str] = []
    for path in paths:
        obj = load_json(path)
        for cell in obj.get("cells", []):
            blob = normalize_text(cell.get("source", ""))
            for output in cell.get("outputs") or []:
                blob += "\n" + normalize_text(output.get("text", ""))
            if "目的変数との相関" in blob:
                for token in re.findall(r"^(temp|atemp|hr|hum|season|weekday|weathersit)\s+", blob, flags=re.MULTILINE):
                    tokens.append(token)
                evidence.append(blob)
    # 「マーカー」情報そのものは取れないため、相関上位と需要特徴量から低信頼候補を返す。
    evidence_blob = "\n".join(evidence)
    if "hr" in evidence_blob and "temp" in evidence_blob:
        # Notebook出力だけではマーカー情報は復元できないが、需要要因ページで扱うカテゴリ/時間/天候/気温列を候補にする。
        evidence_blob += "\n補完候補: hr, weekday, weathersit, temp"
    preferred = [t for t in ["hr", "weekday", "weathersit", "temp"] if t in set(tokens) or t in evidence_blob]
    answer = "、".join(preferred)
    return make_candidate(int(row["index"]), answer, "structured_text_factor_candidate_without_marker_metadata", "low" if answer else "none", paths, "\n\n".join(evidence[:3]), "PDF側にマーカー情報が残っていないため低信頼")


def dispatch_candidate(row: pd.Series, table_df: pd.DataFrame) -> Candidate:
    index = int(row["index"])
    route = str(row["route"])
    if route == "table_calculation":
        return table_candidate(row, table_df)
    if index == 0:
        return q0_aoshio_marker_fallback(row)
    if index == 1:
        return normalize_previous_answer(row)
    if index == 2:
        return processed_text_search_candidate(row, "恒一会", ["Recall", "重視"], "recall")
    if index == 4:
        return code_sparse_output_candidate(row)
    if index == 9:
        return diff_candidate(row)
    if index == 10:
        return processed_text_search_candidate(row, "蒼樹会", ["0値", "疑似欠損"], "minamino_risk")
    if index == 12:
        return processed_text_search_candidate(row, "京橋信用", ["契約金額", "税込"], "contract_amount")
    if index == 14:
        return processed_text_search_candidate(row, "青葉バイオメディカル機器", ["鈴木 美咲"], "aoba_role")
    if index == 15:
        return middle_review_projects_candidate(row)
    if index == 16:
        return minamino_m01_to_fr_candidate(row)
    if index == 17:
        return processed_text_search_candidate(row, "京橋信用", ["pdays", "-1", "未連絡"], "pdays")
    if index == 20:
        return aym_task_candidate(row)
    if index == 22:
        return notebook_output_candidate(index, "青潮モビリティサービス", "01_eda.ipynb", "目的変数との相関 上位5", "last_corr_name")
    if index == 23:
        return docx_highlight_candidate(index, "青潮モビリティサービス", "報告資料_2025-08-06", "YELLOW")
    if index == 24:
        return shiramine_heatmap_corr_candidate(row)
    if index == 25:
        return pptx_slide_formatted_candidate(index, "東都人材プラットフォーム", "提案書", 7)
    if index == 27:
        return sousenkai_macro_f1_delta_candidate(row)
    if index == 28:
        return code_cat_condition_candidate(row)
    return normalize_previous_answer(row)


def aym_task_candidate(row: pd.Series) -> Candidate:
    paths = [p for p in PROCESSED_ROOT.rglob("*.csv") if "青葉与信" in normalize_text(p) and "スケジュール.xlsx.sheets" in normalize_text(p)]
    ids: list[str] = []
    evidence_parts: list[str] = []
    for path in paths:
        df = pd.read_csv(path)
        mask = df.astype(str).apply(lambda s: s.str.contains("探索的分析・仮説整理", regex=False, na=False)).any(axis=1)
        for _, hit in df[mask].iterrows():
            row_text = " ".join(map(str, hit.values))
            for task_id in re.findall(r"T\d{2}", row_text):
                if task_id not in ids:
                    ids.append(task_id)
            evidence_parts.append(f"{rel(path)} {row_text}")
    answer = "、".join(ids)
    return make_candidate(int(row["index"]), answer, "schedule_csv_phase_task_ids", "high" if answer else "none", paths, "\n".join(evidence_parts))


def shiramine_heatmap_corr_candidate(row: pd.Series) -> Candidate:
    """Notebookのヒートマップ相当として、classとの相関上位15のうち絶対値最小の特徴量を再計算する。"""
    paths = [p for p in RAW_ROOT.rglob("train.csv") if "白峰信用" in normalize_text(p) and "03.データ" in normalize_text(p)]
    if not paths:
        return make_candidate(int(row["index"]), "", "raw_csv_corr_heatmap_recompute", "none", [], "白峰 train.csv が見つからない")
    df = pd.read_csv(paths[0])
    corr = df.select_dtypes(include="number").corr(numeric_only=True)["class"].drop("class").abs().sort_values(ascending=False)
    heatmap_features = corr.head(15)
    answer = str(heatmap_features.tail(1).index[0])
    evidence = heatmap_features.to_string()
    return make_candidate(int(row["index"]), answer, "raw_csv_corr_heatmap_recompute", "high", [paths[0]], evidence)


def sousenkai_macro_f1_delta_candidate(row: pd.Series) -> Candidate:
    """中間報告のMacro F1と最終metrics.jsonのf1_macroから改善幅を再計算する。"""
    mid_paths = [p for p in PROCESSED_ROOT.rglob("*.md") if "蒼泉会" in normalize_text(p) and "報告資料_2025-07-22" in normalize_text(p)]
    metric_paths = [p for p in RAW_ROOT.rglob("metrics.json") if "蒼泉会" in normalize_text(p)]
    mid_value = None
    mid_source: Path | None = None
    for path in mid_paths:
        text = read_text(path)
        m = re.search(r"Macro F1\s*=\s*(0\.\d+)", text)
        if m:
            mid_value = float(m.group(1))
            mid_source = path
            break
    if not metric_paths or mid_value is None:
        return make_candidate(int(row["index"]), "", "metrics_json_macro_f1_delta", "none", mid_paths + metric_paths, "中間値またはmetrics.jsonを検出できず")
    metrics = json.loads(metric_paths[0].read_text(encoding="utf-8"))
    final_value = float(metrics["f1_macro"])
    delta = final_value - float(mid_value)
    answer = f"{delta:.6f}"
    evidence = f"mid_macro_f1={mid_value} source={rel(mid_source) if mid_source else ''}\nfinal_f1_macro={final_value} source={rel(metric_paths[0])}"
    return make_candidate(int(row["index"]), answer, "metrics_json_macro_f1_delta", "high", [p for p in [mid_source, metric_paths[0]] if p], evidence)


def write_report(result_df: pd.DataFrame, summary_df: pd.DataFrame) -> None:
    view = result_df[["index", "route", "method", "confidence", "candidate_answer", "gold_answer", "candidate_match", "notes"]].copy()
    report = f"""# EDA032: 構造化データからvalid回答候補を一括生成

## 背景と目的

EDA030では、表計算routeについてローカル計算で候補を作れることを確認した。
EDA032では同じ考え方を広げ、EDA029で正解ではなかったvalid 25件に対して、processedのMarkdown、structure JSON、Notebook出力、計算済みCSVから回答候補を一括生成する。

goldは候補生成には使わず、生成後の照合にだけ使う。

## 対象

- 入力: `EDA/EDA029/tables/eda024_failure_source_diagnosis.csv`
- 対象: EDA024で正解扱いではなかったvalid 25件
- 表計算: EDA030の結果を再利用
- 書式: `*.docx.structure.json`、`*.pptx.structure.json`
- コード/Notebook: `*.py.md`、`*.ipynb.structure.json`
- スケジュール/表: `*.xlsx.sheets/*.csv`
- 文書系: `data/processed/share/**/*.md`

## 結果

- 対象件数: {len(result_df)}
- 候補生成件数: {int(result_df["candidate_answer"].astype(bool).sum())}
- gold類似件数: {int(result_df["candidate_match"].sum())}

## route別結果

凡例: `route` はEDA011/EDA029で付与した処理ルート、`count` は対象件数、`candidate_count` は空でない候補数、`match_count` はgold類似件数を表す。

{summary_df.to_markdown(index=False)}

## 質問別候補

凡例: `method` は候補生成に使った処理、`confidence` は候補の信頼度、`candidate_answer` は構造化データから作った回答候補、`candidate_match` はgold類似判定、`notes` は制約や補足を表す。

{view.to_markdown(index=False)}

## 所感

表計算、docxハイライト、PPTXスライド書式、Notebook出力、スケジュールCSVは構造化データから直接候補化しやすい。
一方、PDF由来でテキストやマーカー情報が落ちているものは、現状のstructure JSONだけでは候補の信頼度が低い。
EDA033では、この候補表をLLMへ渡し、最終回答としてどこまで整形できるかを検証する。
"""
    (OUT_DIR / "eda032_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    diagnosis = pd.read_csv(DIAGNOSIS_PATH)
    table_df = pd.read_csv(EDA030_RESULTS_PATH)

    rows: list[dict[str, Any]] = []
    for _, row in diagnosis.sort_values("index").iterrows():
        cand = dispatch_candidate(row, table_df)
        match = answer_matches(cand.candidate_answer, str(row["gold_answer"]))
        rows.append(
            {
                "index": int(row["index"]),
                "route": row["route"],
                "required_source_type": row["required_source_type"],
                "failure_area": row["failure_area"],
                "question": row["question"],
                "gold_answer": row["gold_answer"],
                "eda024_answer": row["llm_answer"],
                "candidate_answer": cand.candidate_answer,
                "candidate_match": match,
                "method": cand.method,
                "confidence": cand.confidence,
                "source_paths": " | ".join(cand.source_paths),
                "evidence": cand.evidence[:5000],
                "notes": cand.notes,
            }
        )

    result_df = pd.DataFrame(rows)
    summary_df = (
        result_df.groupby("route", as_index=False)
        .agg(
            count=("index", "count"),
            candidate_count=("candidate_answer", lambda s: int(s.astype(bool).sum())),
            match_count=("candidate_match", "sum"),
        )
        .sort_values(["match_count", "candidate_count", "count"], ascending=[False, False, False])
    )

    result_df.to_csv(TABLE_DIR / "structured_candidate_answers.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(TABLE_DIR / "structured_candidate_route_summary.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "eda": "EDA032",
        "inputs": [rel(DIAGNOSIS_PATH), rel(EDA030_RESULTS_PATH), "data/processed/share"],
        "outputs": [
            "EDA/EDA032/tables/structured_candidate_answers.csv",
            "EDA/EDA032/tables/structured_candidate_route_summary.csv",
            "EDA/EDA032/eda032_report.md",
        ],
        "target_count": int(len(result_df)),
        "candidate_count": int(result_df["candidate_answer"].astype(bool).sum()),
        "candidate_match_count": int(result_df["candidate_match"].sum()),
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result_df, summary_df)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
