from __future__ import annotations

import csv
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "EDA" / "EDA056"
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"
BASE_PREDICTIONS = ROOT / "EDA" / "EDA055" / "predictions" / "eda055_chart_format_formula_predictions.csv"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


@dataclass
class RouteResult:
    index: int
    route: str
    candidate_answer: str
    adopted: bool
    confidence: str
    needs_review: bool
    evidence: dict
    source_paths: list[str]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def norm_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace(" 00:00:00", "").strip()


def read_predictions(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                rows.append([row[0], row[1]])
    return rows


def write_predictions(rows: list[list[str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(rows)


def find_processed_path(*keywords: str, suffix: str) -> Path:
    """日本語パスの表記揺れを避けるため、部分一致で対象ファイルを探す。"""
    candidates = []
    for path in (ROOT / "data" / "processed").rglob(f"*{suffix}"):
        text = path.as_posix()
        if all(keyword in text for keyword in keywords):
            candidates.append(path)
    if not candidates:
        raise FileNotFoundError(f"processed file not found: keywords={keywords}, suffix={suffix}")
    return sorted(candidates, key=lambda p: len(p.as_posix()))[0]


def extract_docx_comment_ranges(docx_path: Path) -> list[dict]:
    """Wordのコメント本文と、コメントが付いた本文範囲をdocx内部XMLから復元する。"""
    with zipfile.ZipFile(docx_path) as z:
        comments_root = ET.fromstring(z.read("word/comments.xml"))
        comment_text_by_id: dict[str, str] = {}
        for comment in comments_root.findall(f"{W}comment"):
            comment_id = comment.attrib.get(f"{W}id", "")
            text = "".join(t.text or "" for t in comment.findall(f".//{W}t")).strip()
            if comment_id:
                comment_text_by_id[comment_id] = text

        document_root = ET.fromstring(z.read("word/document.xml"))
        active_ids: set[str] = set()
        range_text_by_id = {comment_id: [] for comment_id in comment_text_by_id}
        all_text_parts: list[str] = []

        for elem in document_root.iter():
            if elem.tag == f"{W}commentRangeStart":
                comment_id = elem.attrib.get(f"{W}id", "")
                if comment_id in range_text_by_id:
                    active_ids.add(comment_id)
                continue
            if elem.tag == f"{W}commentRangeEnd":
                comment_id = elem.attrib.get(f"{W}id", "")
                active_ids.discard(comment_id)
                continue
            if elem.tag == f"{W}t":
                text = elem.text or ""
                all_text_parts.append(text)
                for comment_id in active_ids:
                    range_text_by_id[comment_id].append(text)

        all_text = "".join(all_text_parts)
        records: list[dict] = []
        for comment_id, comment_text in comment_text_by_id.items():
            target_text = "".join(range_text_by_id.get(comment_id, [])).strip()
            pos = all_text.find(target_text) if target_text else -1
            records.append(
                {
                    "file": rel(docx_path),
                    "comment_id": comment_id,
                    "comment_text": comment_text,
                    "target_text": target_text,
                    "context": all_text[max(0, pos - 80) : pos + len(target_text) + 80] if pos >= 0 else "",
                }
            )
        return records


def answer_toto_meeting_comment() -> RouteResult:
    docs = sorted((ROOT / "data" / "raw").rglob("株式会社東都人材*/*/会議録/*.docx"))
    comment_records: list[dict] = []
    for docx_path in docs:
        with zipfile.ZipFile(docx_path) as z:
            if "word/comments.xml" not in z.namelist():
                continue
        comment_records.extend(extract_docx_comment_ranges(docx_path))

    useful = [r for r in comment_records if r["target_text"]]
    if not useful:
        return RouteResult(49, "docx_comment_range_extraction", "わかりません", False, "none", True, {"comments": comment_records}, [rel(p) for p in docs])

    # 質問はコメント本文ではなく「コメントがついている部分」を聞いているため、本文範囲を回答にする。
    answer = "、".join(record["target_text"] for record in useful)
    return RouteResult(
        index=49,
        route="docx_comment_range_extraction",
        candidate_answer=answer,
        adopted=True,
        confidence="high",
        needs_review=False,
        evidence={"comment_records": useful},
        source_paths=[record["file"] for record in useful],
    )


def answer_minamino_operation_clause() -> RouteResult:
    proposal = find_processed_path("蒼樹会", "みなみ野女性医療センター", "00.提案", suffix="提案書.pptx.md")
    contract = find_processed_path("蒼樹会", "みなみ野女性医療センター", "01.契約", suffix="契約書.docx.md")
    texts = {
        rel(proposal): proposal.read_text(encoding="utf-8"),
        rel(contract): contract.read_text(encoding="utf-8"),
    }

    patterns = [
        "契約範囲外の追加対応は別途対応とし",
        "契約範囲外の追加対応は、別紙見積にて金額・納期を事前合意のうえ実施する",
        "契約スコープ外の要望が発生した場合",
    ]
    hits: list[dict] = []
    for source, text in texts.items():
        for pattern in patterns:
            idx = text.find(pattern)
            if idx >= 0:
                line_no = text[:idx].count("\n") + 1
                line = text[idx : text.find("\n", idx) if text.find("\n", idx) >= 0 else idx + 120].strip("* \n")
                hits.append({"source": source, "line_no": line_no, "matched": pattern, "line": line})

    if not hits:
        return RouteResult(52, "operation_clause_lookup", "わかりません", False, "none", True, {}, list(texts))

    answer = "契約範囲外の追加対応"
    return RouteResult(
        index=52,
        route="operation_clause_lookup",
        candidate_answer=answer,
        adopted=True,
        confidence="medium",
        needs_review=True,
        evidence={
            "note": "質問文の「別契約」と完全一致する語は見つからないが、別途対応・別紙見積として明記された契約範囲外対応を採用候補にした。",
            "hits": hits,
        },
        source_paths=sorted(set(hit["source"] for hit in hits)),
    )


def load_schedule(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None, dtype=str).fillna("")
    header_index = None
    for i, row in raw.iterrows():
        if "タスクID" in [norm_text(v) for v in row.tolist()]:
            header_index = i
            break
    if header_index is None:
        raise ValueError(f"header row not found: {path}")

    header = [norm_text(v) for v in raw.iloc[header_index].tolist()]
    df = raw.iloc[header_index + 1 :].copy()
    df.columns = header
    df = df[[c for c in df.columns if c]]
    for col in df.columns:
        df[col] = df[col].map(norm_text)
    df = df[df["タスクID"].str.match(r"^T\d+")]
    return df.set_index("タスクID", drop=False)


def answer_seiryo_schedule_diff() -> RouteResult:
    r1 = find_processed_path("青嶺不動産アセットマネジメント", "02.計画", "スケジュール_r1.xlsx.sheets", suffix="スケジュール.csv")
    r2 = find_processed_path("青嶺不動産アセットマネジメント", "02.計画", "スケジュール_r2.xlsx.sheets", suffix="スケジュール.csv")
    before = load_schedule(r1)
    after = load_schedule(r2)

    ignored: list[dict] = []
    meaningful: list[dict] = []
    common_columns = sorted(set(before.columns) & set(after.columns))
    for task_id in sorted(set(before.index) & set(after.index)):
        for col in common_columns:
            old_value = norm_text(before.at[task_id, col])
            new_value = norm_text(after.at[task_id, col])
            if old_value == new_value:
                continue
            if col == "No." and old_value.rstrip(".0") == new_value.rstrip(".0"):
                ignored.append({"task_id": task_id, "field": col, "old": old_value, "new": new_value, "reason": "番号の表記差"})
                continue
            if col == "ステータス" and old_value == "未着手" and new_value == "完了":
                ignored.append({"task_id": task_id, "field": col, "old": old_value, "new": new_value, "reason": "質問で除外された状態変更"})
                continue
            meaningful.append({"task_id": task_id, "field": col, "old": old_value, "new": new_value})

    if not meaningful:
        return RouteResult(95, "structured_schedule_diff_filter", "わかりません", False, "none", True, {"ignored": ignored}, [rel(r1), rel(r2)])

    parts: list[str] = []
    for change in meaningful:
        task = after.loc[change["task_id"]]
        parts.append(
            f"{change['task_id']}「{task['タスク名']}」の{change['field']}が、{change['old']}から{change['new']}に変更された。"
        )
    return RouteResult(
        index=95,
        route="structured_schedule_diff_filter",
        candidate_answer=" ".join(parts),
        adopted=True,
        confidence="high",
        needs_review=False,
        evidence={"meaningful_changes": meaningful, "ignored_changes": ignored[:10]},
        source_paths=[rel(r1), rel(r2)],
    )


def apply_results(rows: list[list[str]], results: list[RouteResult]) -> list[list[str]]:
    answer_by_index = {str(result.index): result.candidate_answer for result in results if result.adopted}
    updated: list[list[str]] = []
    for row in rows:
        index, answer = row[0], row[1]
        updated.append([index, answer_by_index.get(index, answer)])
    return updated


def write_zip(csv_path: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(csv_path, arcname="predictions.csv")


def write_route_table(results: list[RouteResult]) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLE_DIR / "eda056_route_results.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["index", "route", "candidate_answer", "adopted", "confidence", "needs_review", "evidence", "source_paths"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for result in results:
            row = asdict(result)
            row["evidence"] = json.dumps(row["evidence"], ensure_ascii=False)
            row["source_paths"] = json.dumps(row["source_paths"], ensure_ascii=False)
            writer.writerow(row)


def count_unknown(rows: list[list[str]]) -> int:
    return sum(1 for _, answer in rows if answer == "わかりません")


def write_report(results: list[RouteResult], before_unknown: int, after_unknown: int) -> None:
    adopted = [r for r in results if r.adopted]
    table_rows = "\n".join(
        f"| {r.index} | {r.route} | {r.candidate_answer} | {r.confidence} | {str(r.needs_review)} |"
        for r in results
    )
    report = f"""# EDA056: 会議録コメント・運用条項・スケジュール差分route

## 背景と目的

EDA055後に残った `わかりません` 9件のうち、会議録コメント、運用条項、スケジュール差分に該当する3件をローカル処理で確認した。
LLMには投げず、raw docx、processed Markdown、processed CSVを直接読んで、提出候補として採用できる回答だけをEDA055候補に上書きする。

## 結果

- EDA055時点の `わかりません`: {before_unknown}
- EDA056後の `わかりません`: {after_unknown}
- 追加採用: {len(adopted)}

| index | route | 採用回答 | confidence | needs_review |
| --- | --- | --- | --- | --- |
{table_rows}

凡例: `index` はtest質問ID、`route` は今回の処理名、`採用回答` は提出候補に反映した回答、`confidence` は根拠の強さ、`needs_review` は最終提出前に人手確認したい候補かどうかを表す。

## 処理内容

- index 49: raw docxの `word/comments.xml` と `word/document.xml` を対応付け、コメント本文ではなく、コメント範囲が付与された本文を抽出した。
- index 52: みなみ野の提案書と契約書から、契約範囲外の追加対応が別途対応・別紙見積で扱われる条項を抽出した。ただし、資料内では「別契約」という完全一致語ではなく「別途対応」「別紙見積」と表現されているため、needs_review=Trueとした。
- index 95: `スケジュール_r1.xlsx` と `スケジュール_r2.xlsx` をタスクIDで比較し、未着手から完了へのステータス変更と番号表記差を除外して、案件遂行に関連する差分だけを残した。

## 出力

- route結果: `EDA/EDA056/tables/eda056_route_results.csv`
- 提出候補CSV: `EDA/EDA056/predictions/eda056_meeting_operation_schedule_predictions.csv`
- 提出候補zip: `EDA/EDA056/predictions/eda056_meeting_operation_schedule_submission.zip`

## 注意

index 52は「別契約」という語が直接資料に見つからないため、完全に安全な採用ではない。提出スコアを見る前に、`契約範囲外の追加対応` で評価されそうかを確認する余地がある。
"""
    (OUT_DIR / "eda056_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    base_rows = read_predictions(BASE_PREDICTIONS)
    results = [
        answer_toto_meeting_comment(),
        answer_minamino_operation_clause(),
        answer_seiryo_schedule_diff(),
    ]
    updated_rows = apply_results(base_rows, results)

    pred_csv = PRED_DIR / "eda056_meeting_operation_schedule_predictions.csv"
    pred_zip = PRED_DIR / "eda056_meeting_operation_schedule_submission.zip"
    write_predictions(updated_rows, pred_csv)
    write_zip(pred_csv, pred_zip)
    write_route_table(results)

    manifest = {
        "eda": "EDA056",
        "base": rel(BASE_PREDICTIONS),
        "before_unknown": count_unknown(base_rows),
        "after_unknown": count_unknown(updated_rows),
        "adopted_count": sum(1 for r in results if r.adopted),
        "submission_zip": rel(pred_zip),
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(results, manifest["before_unknown"], manifest["after_unknown"])
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
