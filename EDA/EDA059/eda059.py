from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EDA_DIR = ROOT / "EDA" / "EDA059"
TABLE_DIR = EDA_DIR / "tables"
SOURCE_AUDIT = ROOT / "EDA" / "EDA058" / "tables" / "answer_source_audit.csv"
SUMMARY_CSV = TABLE_DIR / "question_answer_source_confidence.csv"
REPORT_MD = EDA_DIR / "eda059_report.md"


def split_source_paths(value: object) -> list[str]:
    """監査CSVの複数パス表記を、Markdownで扱いやすい配列に分ける。"""
    if pd.isna(value) or not str(value).strip():
        return []
    return [part.strip() for part in str(value).split(" | ") if part.strip()]


def build_summary(audit: pd.DataFrame) -> pd.DataFrame:
    """質問・回答・ソース・確度を一覧用の列へ整理する。"""
    rows = []
    for _, row in audit.sort_values("index").iterrows():
        paths = split_source_paths(row.get("source_paths"))
        rows.append(
            {
                "index": int(row["index"]),
                "question": row.get("question", ""),
                "answer": row.get("answer", ""),
                "source_files": " | ".join(paths),
                "source_confidence": row.get("source_confidence", ""),
                "answer_status": row.get("answer_status", ""),
                "source_count": len(paths),
            }
        )
    return pd.DataFrame(rows)


def build_report(summary: pd.DataFrame) -> str:
    """CSVと同じ情報を、質問ごとのMarkdown一覧として出力する。"""
    lines = [
        "# EDA059 質問・回答・ソース確度一覧",
        "",
        "## 目的",
        "",
        "EDA058の提出回答を変更せず、質問文、回答、参照したソースファイル、source_confidenceを質問単位で照合できるように整理した。",
        "",
        "## 生成元と列の説明",
        "",
        "生成元は `EDA/EDA058/tables/answer_source_audit.csv` である。回答の修正や再評価は行っていない。",
        "",
        "凡例: `index` は質問ID、`question` は質問文、`answer` はEDA058の回答、`source_files` は参照ファイル、`source_confidence` はソース確度、`answer_status` は回答状態、`source_count` は参照ファイル数を表す。",
        "",
        "## 件数サマリ",
        "",
    ]
    confidence_summary = (
        summary.groupby(["answer_status", "source_confidence"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["answer_status", "source_confidence"])
    )
    lines.extend(confidence_summary.to_markdown(index=False).splitlines())
    lines.extend(
        [
            "",
            "凡例: `answer_status` と `source_confidence` の組み合わせごとに、該当する質問数を示す。",
            "",
            "## 質問・回答・ソースファイル一覧",
            "",
        ]
    )
    for _, row in summary.iterrows():
        lines.extend(
            [
                f"### index {int(row['index'])}",
                "",
                f"- 質問: {row['question']}",
                f"- 回答: {row['answer']}",
                f"- source_confidence: `{row['source_confidence']}`",
                f"- answer_status: `{row['answer_status']}`",
                "- ソースファイル:",
            ]
        )
        paths = split_source_paths(row["source_files"])
        lines.extend(f"  - `{path}`" for path in paths) if paths else lines.append("  - ソースファイル未確定")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    audit = pd.read_csv(SOURCE_AUDIT, encoding="utf-8-sig")
    summary = build_summary(audit)
    summary.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
    REPORT_MD.write_text(build_report(summary), encoding="utf-8")
    manifest = {
        "eda": "EDA059",
        "source_audit": str(SOURCE_AUDIT.relative_to(ROOT)),
        "summary_csv": str(SUMMARY_CSV.relative_to(ROOT)),
        "report": str(REPORT_MD.relative_to(ROOT)),
        "row_count": int(len(summary)),
        "unknown_indices": summary.loc[summary["answer_status"].eq("unknown"), "index"].astype(int).tolist(),
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
