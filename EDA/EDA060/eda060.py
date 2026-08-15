from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EDA_DIR = ROOT / "EDA" / "EDA060"
SOURCE_CSV = ROOT / "EDA" / "EDA059" / "tables" / "question_answer_source_confidence.csv"
OUTPUT_CSV = ROOT / "EDA" / "human_review.csv"
REPORT_MD = EDA_DIR / "eda060_report.md"


def split_paths(value: object) -> list[str]:
    """複数の参照ファイルを、会社名抽出に使える個別パスへ分ける。"""
    if pd.isna(value) or not str(value).strip():
        return []
    return [part.strip() for part in str(value).split(" | ") if part.strip()]


def extract_companies(source_files: object) -> list[str]:
    """参照パスのプロジェクト配下から会社名を抽出する。"""
    companies = []
    for path in split_paths(source_files):
        match = re.search(r"プロジェクト[\\/]([^\\/]+)", path)
        if match:
            company = unicodedata.normalize("NFC", match.group(1))
            if company not in companies:
                companies.append(company)
    return companies


def build_review_table(source: pd.DataFrame) -> pd.DataFrame:
    """会社を第一キー、元のindexを第二キーとして人手評価用の行を作る。"""
    rows = []
    for _, row in source.iterrows():
        companies = extract_companies(row.get("source_files"))
        rows.append(
            {
                "company_group": companies[0] if companies else "会社特定不可",
                "related_companies": " / ".join(companies[1:]),
                "index": int(row["index"]),
                "question": row.get("question", ""),
                "current_answer": row.get("answer", ""),
                "source_files": row.get("source_files", ""),
                "source_confidence": row.get("source_confidence", ""),
                "answer_status": row.get("answer_status", ""),
                "human_answer": "",
                "human_review": "",
            }
        )
    review = pd.DataFrame(rows)
    return review.sort_values(["company_group", "index"], kind="stable").reset_index(drop=True)


def build_report(review: pd.DataFrame) -> str:
    """人手評価CSVの並び順と入力列を説明するレポートを作る。"""
    company_counts = review.groupby("company_group", sort=True).size().reset_index(name="question_count")
    lines = [
        "# EDA060 人手評価用CSV",
        "",
        "## 目的",
        "",
        "EDA059の質問・回答・参照ファイル一覧を、人手で正誤確認しやすいよう同じ会社の質問が連続する順序に並べ替えた。回答生成や既存回答の変更は行っていない。",
        "",
        "## CSV",
        "",
        "`EDA/human_review.csv` をExcelなどで開き、`human_answer` と `human_review` を記入する。元回答は `current_answer` に保存しているため、元の回答を上書きしない。",
        "",
        "凡例: `company_group` は参照ファイルの最初のプロジェクト配下から抽出した主な会社名、`related_companies` は同じ質問の他の参照ファイルに現れる会社名、`index` は元の質問ID、`question` は質問文、`current_answer` は現在の回答、`source_files` は参照ファイル、`source_confidence` はソース確度、`answer_status` は現在の回答状態、`human_answer` は人手で確認した正解、`human_review` は正解/誤答や理由などの評価メモを表す。",
        "",
        "## 会社別件数",
        "",
    ]
    lines.extend(company_counts.to_markdown(index=False).splitlines())
    lines.extend(
        [
            "",
            "凡例: 各行は会社グループ、`question_count` はその会社に属する質問数を表す。複数会社の参照ファイルがある質問は、主な会社で並べ、他の会社を `related_companies` に残している。",
            "",
            "## 評価の記入例",
            "",
            "`human_answer` には正解または正解候補を記入し、`human_review` には `正解`、`部分正解`、`不明`、`誤答` と、必要に応じて理由を記入する。",
            "",
            f"全質問数: {len(review)}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    source = pd.read_csv(SOURCE_CSV, encoding="utf-8-sig")
    review = build_review_table(source)
    review.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    REPORT_MD.write_text(build_report(review), encoding="utf-8")
    manifest = {
        "eda": "EDA060",
        "source_csv": str(SOURCE_CSV.relative_to(ROOT)),
        "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
        "report": str(REPORT_MD.relative_to(ROOT)),
        "row_count": int(len(review)),
        "company_group_count": int(review["company_group"].nunique()),
        "human_answer_empty_count": int(review["human_answer"].eq("").sum()),
        "human_review_empty_count": int(review["human_review"].eq("").sum()),
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
