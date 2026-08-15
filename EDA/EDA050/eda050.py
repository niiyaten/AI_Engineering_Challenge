from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"


def norm(value: object) -> str:
    """検索しやすいように空白と文字種をそろえる。"""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def compact(value: object, limit: int = 500) -> str:
    text = " ".join(norm(value).split())
    return text[:limit]


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def project_name(path: Path) -> str:
    parts = list(path.parts)
    if "プロジェクト" in parts:
        idx = parts.index("プロジェクト")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def document_kind(path: Path) -> str:
    text = str(path)
    if "会議録" in text:
        return "meeting_minutes"
    if "報告資料" in text:
        return "report_pack"
    return "meeting_related"


def split_pages(text: str) -> list[dict[str, Any]]:
    """Markdown内のPage見出しでページ単位に分ける。Wordは1ページ扱いにする。"""
    matches = list(re.finditer(r"^### Page\s+(\d+)\s*$", text, flags=re.MULTILINE))
    if not matches:
        return [{"page": 1, "text": text}]
    pages: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        pages.append({"page": int(match.group(1)), "text": text[start:end]})
    return pages


def extract_meeting_id(text: str, path: Path) -> str:
    candidates = [
        r"会議\s*ID\s*[:：]\s*(M\d+)",
        r"会議ID\s*[:：]\s*(M\d+)",
        r"チェックポイント\s*[:：]?\s*(M\d+)",
        r"対象チェックポイント\s*[:：]?\s*(M\d+)",
        r"\b(M\d+)\b",
    ]
    full = norm(text)
    for pattern in candidates:
        m = re.search(pattern, full)
        if m:
            return m.group(1)
    return ""


def extract_date(text: str, path: Path) -> str:
    m = re.search(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2})", path.name)
    if m:
        return m.group(1).replace("/", "-")
    m = re.search(r"(日時|会議日|チェックポイント日付)\s*[:：]\s*(20\d{2}[-/]\d{1,2}[-/]\d{1,2})", norm(text))
    return m.group(2).replace("/", "-") if m else ""


def extract_page_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    rows = []
    full_meeting_id = extract_meeting_id(text, path)
    date = extract_date(text, path)
    for page in split_pages(text):
        page_text = norm(page["text"])
        rows.append(
            {
                "project": project_name(path),
                "document_kind": document_kind(path),
                "source_path": relative(path),
                "file_name": path.name,
                "meeting_id": extract_meeting_id(page_text, path) or full_meeting_id,
                "date": date,
                "page": page["page"],
                "has_progress_summary": "進捗サマリ" in page_text,
                "has_action": bool(re.search(r"\bA\d{2}\b", page_text)),
                "has_comment": "コメント" in page_text or "comment" in page_text.lower(),
                "has_checkpoint": "チェックポイント" in page_text or re.search(r"\bCP\d+\b", page_text) is not None,
                "text": compact(page_text, 1200),
            }
        )
    return rows


def action_rows_from_page(page_row: dict[str, Any]) -> list[dict[str, Any]]:
    """A01などの周辺文脈をアクション台帳にする。"""
    text = page_row["text"]
    rows = []
    for m in re.finditer(r"\b(A\d{2})\b", text):
        start = max(0, m.start() - 120)
        end = min(len(text), m.end() + 260)
        rows.append(
            {
                **{k: page_row[k] for k in ["project", "document_kind", "source_path", "file_name", "meeting_id", "date", "page"]},
                "action_id": m.group(1),
                "context": compact(text[start:end], 500),
            }
        )
    return rows


def checkpoint_task_rows() -> pd.DataFrame:
    """計画CSVからチェックポイントとタスクIDの対応候補を拾う。"""
    rows: list[dict[str, Any]] = []
    for path in PROCESSED_ROOT.rglob("02.計画/*.sheets/*.csv"):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            continue
        for row_idx, row in df.iterrows():
            joined = " ".join(map(str, row.to_dict().values()))
            if "チェックポイント" not in joined and not re.search(r"\bCP\d+\b", joined):
                continue
            rows.append(
                {
                    "project": project_name(path),
                    "source_path": relative(path),
                    "row_index": row_idx,
                    "task_ids": " | ".join(sorted(set(re.findall(r"\bT\d{2}\b", joined)))),
                    "checkpoint_ids": " | ".join(sorted(set(re.findall(r"\bCP\d+\b", joined)))),
                    "text": compact(joined, 800),
                }
            )
    return pd.DataFrame(rows)


def build_probe_answers(page_df: pd.DataFrame, action_df: pd.DataFrame, checkpoint_df: pd.DataFrame) -> pd.DataFrame:
    """EDA048で残った会議/アクション系質問に対する候補回答を作る。"""
    rows = []
    shiramine = page_df[
        page_df["project"].str.contains("白峰", na=False)
        & page_df["meeting_id"].eq("M04")
        & page_df["has_progress_summary"].astype(bool)
    ]
    rows.append(
        {
            "index": 18,
            "question": "白峰信用リスク評価の会議ID:M04の会議録にて、進捗サマリが記載されているページ番号を答えてください。",
            "candidate_answer": "、".join(map(str, sorted(shiramine["page"].unique()))) if not shiramine.empty else "",
            "evidence": " | ".join(shiramine["source_path"].head(3).tolist()),
            "needs_review": shiramine.empty,
        }
    )
    toto_comments = page_df[
        page_df["project"].str.contains("東都", na=False)
        & page_df["document_kind"].eq("meeting_minutes")
        & page_df["has_comment"].astype(bool)
    ]
    rows.append(
        {
            "index": 49,
            "question": "東都人材プラットフォームの会議録において、コメントがついている部分をそのまま抽出してください。",
            "candidate_answer": " / ".join(toto_comments["text"].head(3).tolist()),
            "evidence": " | ".join(toto_comments["source_path"].head(3).tolist()),
            "needs_review": toto_comments.empty,
        }
    )
    minamino_a10 = action_df[action_df["project"].str.contains("みなみ野", na=False) & action_df["action_id"].eq("A10")]
    rows.append(
        {
            "index": 93,
            "question": "蒼樹会 みなみ野女性医療センターのアクションIDA10の内容をそのまま抜き出してください。",
            "candidate_answer": " / ".join(minamino_a10["context"].head(3).tolist()),
            "evidence": " | ".join(minamino_a10["source_path"].head(3).tolist()),
            "needs_review": minamino_a10.empty,
        }
    )
    aoba_cp2 = checkpoint_df[
        checkpoint_df["project"].str.contains("青葉与信", na=False)
        & (checkpoint_df["checkpoint_ids"].str.contains("CP2", na=False) | checkpoint_df["text"].str.contains("チェックポイント2", na=False))
    ]
    rows.append(
        {
            "index": 96,
            "question": "青葉与信マネジメントのチェックポイント2として設定されている内容に関連するタスクIDを教えてください。",
            "candidate_answer": " | ".join(sorted(set(" | ".join(aoba_cp2["task_ids"].tolist()).split(" | ")))) if not aoba_cp2.empty else "",
            "evidence": " | ".join(aoba_cp2["source_path"].head(3).tolist()),
            "needs_review": aoba_cp2.empty,
        }
    )
    return pd.DataFrame(rows)


def no_text_pdf_inventory(page_df: pd.DataFrame) -> pd.DataFrame:
    """PDF抽出で本文が取れなかったページをファイル単位で集計する。"""
    if page_df.empty:
        return pd.DataFrame()
    tmp = page_df.copy()
    tmp["is_no_text_page"] = tmp["text"].astype(str).str.contains(r"\[no text extracted\]", regex=True)
    grouped = (
        tmp.groupby(["project", "source_path", "file_name"], as_index=False)
        .agg(page_count=("page", "count"), no_text_page_count=("is_no_text_page", "sum"))
    )
    return grouped[grouped["no_text_page_count"] > 0].sort_values(["project", "file_name"])


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    page_rows: list[dict[str, Any]] = []
    for path in PROCESSED_ROOT.rglob("05.会議/**/*.md"):
        page_rows.extend(extract_page_rows(path))
    page_df = pd.DataFrame(page_rows)

    action_rows: list[dict[str, Any]] = []
    for row in page_rows:
        action_rows.extend(action_rows_from_page(row))
    action_df = pd.DataFrame(action_rows)
    checkpoint_df = checkpoint_task_rows()
    probe_df = build_probe_answers(page_df, action_df, checkpoint_df)
    no_text_df = no_text_pdf_inventory(page_df)

    page_path = TABLE_DIR / "meeting_page_inventory.csv"
    action_path = TABLE_DIR / "meeting_action_inventory.csv"
    checkpoint_path = TABLE_DIR / "checkpoint_task_inventory.csv"
    probe_path = TABLE_DIR / "meeting_action_question_probe.csv"
    no_text_path = TABLE_DIR / "no_text_pdf_inventory.csv"
    page_df.to_csv(page_path, index=False, encoding="utf-8-sig")
    action_df.to_csv(action_path, index=False, encoding="utf-8-sig")
    checkpoint_df.to_csv(checkpoint_path, index=False, encoding="utf-8-sig")
    probe_df.to_csv(probe_path, index=False, encoding="utf-8-sig")
    no_text_df.to_csv(no_text_path, index=False, encoding="utf-8-sig")

    family_summary = probe_df[["index", "candidate_answer", "needs_review"]].copy()
    report = f"""# EDA050: 会議録/アクションID台帳

## 背景と目的

EDA048では、会議録/アクションID構造化が残件16件中4件を占めた。
EDA050では、`05.会議` 配下の会議録と報告資料をページ単位に分解し、meeting_id、日付、ページ、アクションID、コメント、チェックポイントを台帳化する。

## 結果

- ページレコード数: {len(page_df)}
- アクションID周辺レコード数: {len(action_df)}
- チェックポイント/タスク候補レコード数: {len(checkpoint_df)}
- no text PDFファイル数: {len(no_text_df)}
- 残件4問の候補生成数: {len(probe_df)}

## 残件候補

凡例: `candidate_answer` はローカル台帳から抽出した回答候補、`needs_review` は提出採用前に確認が必要かを表す。

{family_summary.to_markdown(index=False)}

## 出力

- ページ台帳: `{page_path.relative_to(BASE_DIR).as_posix()}`
- アクション台帳: `{action_path.relative_to(BASE_DIR).as_posix()}`
- チェックポイント/タスク台帳: `{checkpoint_path.relative_to(BASE_DIR).as_posix()}`
- no text PDF台帳: `{no_text_path.relative_to(BASE_DIR).as_posix()}`
- 残件候補: `{probe_path.relative_to(BASE_DIR).as_posix()}`

## 注意

PDF由来のアクション表は改行で崩れている箇所がある。
提出用に使う場合は、今回の周辺文脈候補をさらに表形式へ整形するか、該当ページだけLLMへ渡して短答化する。
"""
    report_path = OUT_DIR / "eda050_report.md"
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "eda": "EDA050",
        "page_record_count": int(len(page_df)),
        "action_record_count": int(len(action_df)),
        "checkpoint_task_record_count": int(len(checkpoint_df)),
        "no_text_pdf_count": int(len(no_text_df)),
        "probe_count": int(len(probe_df)),
        "outputs": [
            page_path.relative_to(BASE_DIR).as_posix(),
            action_path.relative_to(BASE_DIR).as_posix(),
            checkpoint_path.relative_to(BASE_DIR).as_posix(),
            no_text_path.relative_to(BASE_DIR).as_posix(),
            probe_path.relative_to(BASE_DIR).as_posix(),
            report_path.relative_to(BASE_DIR).as_posix(),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
