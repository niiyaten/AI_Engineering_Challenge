from __future__ import annotations

import json
import math
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
    """表記ゆれを抑えて検索・正規表現を安定させる。"""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def compact(value: object, limit: int = 500) -> str:
    return " ".join(norm(value).split())[:limit]


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


def yen_to_int(text: str) -> int | None:
    """日本円表記を整数へ変換する。"""
    if not text:
        return None
    m = re.search(r"([0-9,]+)\s*円", text)
    if not m:
        m = re.search(r"¥\s*([0-9,]+)", text)
    return int(m.group(1).replace(",", "")) if m else None


def extract_money(text: str, keyword: str) -> int | None:
    """キーワード周辺の金額を拾う。"""
    for m in re.finditer(re.escape(keyword), text):
        window = text[m.start() : m.start() + 160]
        value = yen_to_int(window)
        if value is not None:
            return value
    return None


def extract_contract_type(text: str) -> str:
    if "time_and_materials" in text or "実績工数" in text and "時間単価" in text:
        return "time_and_materials"
    if "固定価格" in text or "固定金額" in text:
        return "fixed_price"
    return ""


def extract_roles(text: str, project: str, source_path: str) -> list[dict[str, Any]]:
    """契約書内の乙側体制を役割・氏名テーブルにする。"""
    roles = [
        "エグゼクティブスポンサー",
        "プロジェクトマネージャー",
        "リードデータサイエンティスト",
        "データエンジニア",
        "ビジネスアナリスト",
        "QAレビューアー",
        "QAレビューア",
        "QA",
    ]
    rows: list[dict[str, Any]] = []
    for role in roles:
        pattern = role + r"[：:]\s*([一-龥ぁ-んァ-ヶーA-Za-z ]{2,20})"
        for m in re.finditer(pattern, text):
            rows.append({"project": project, "role": role, "name": m.group(1).strip(), "source_path": source_path})
    # Markdown表の体制も拾う。
    for line in text.splitlines():
        if "|" not in line:
            continue
        if any(role in line for role in roles):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3:
                role = next((r for r in roles if r in line), "")
                name_candidates = [c for c in cells if re.search(r"[一-龥]{2,}\s*[一-龥]{1,}", c)]
                if role and name_candidates:
                    rows.append({"project": project, "role": role, "name": name_candidates[0], "source_path": source_path})
    return rows


def build_contract_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    contract_rows: list[dict[str, Any]] = []
    role_rows: list[dict[str, Any]] = []
    for path in PROCESSED_ROOT.rglob("01.契約/*.md"):
        text = norm(path.read_text(encoding="utf-8", errors="ignore"))
        project = project_name(path)
        source_path = relative(path)
        amount_tax_in = extract_money(text, "税込") or extract_money(text, "契約金額")
        amount_tax_ex = extract_money(text, "税抜")
        upfront = extract_money(text, "着手金")
        contract_rows.append(
            {
                "project": project,
                "source_path": source_path,
                "contract_type": extract_contract_type(text),
                "contract_amount_tax_in": amount_tax_in,
                "contract_amount_tax_ex": amount_tax_ex,
                "upfront_amount": upfront,
                "is_medical": any(k in project for k in ["医療", "病院", "診療所"]),
                "text_preview": compact(text, 1200),
            }
        )
        role_rows.extend(extract_roles(text, project, source_path))
    return pd.DataFrame(contract_rows), pd.DataFrame(role_rows).drop_duplicates()


def build_schedule_resource_table() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in PROCESSED_ROOT.rglob("02.計画/*.sheets/*.csv"):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            continue
        project = project_name(path)
        for row_idx, row in df.iterrows():
            values = row.to_dict()
            joined = " ".join(map(str, values.values()))
            if not re.search(r"T\d{2}|工数|担当|Owner|担当者", joined):
                continue
            hours = []
            for val in values.values():
                for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*(?:h|時間)", str(val)):
                    hours.append(float(m.group(1)))
            rows.append(
                {
                    "project": project,
                    "source_path": relative(path),
                    "row_index": row_idx,
                    "task_ids": " | ".join(sorted(set(re.findall(r"\bT\d{2}\b", joined)))),
                    "person_names": " | ".join(sorted(set(re.findall(r"[一-龥]{2,}\s[一-龥]{1,}", joined)))),
                    "hours_candidates": " | ".join(str(h) for h in hours),
                    "text": compact(joined, 900),
                }
            )
    return pd.DataFrame(rows)


def approval_level(amount: float | int | None, is_medical: bool, contract_type: str) -> str:
    """社内決裁基準に基づく簡易APRレベルを付与する。"""
    if amount is None or (isinstance(amount, float) and math.isnan(amount)):
        base = ""
    elif amount < 3_000_000:
        base = "主任承認"
    elif amount < 5_000_000:
        base = "課長承認"
    elif amount < 8_000_000:
        base = "部長承認"
    else:
        base = "本部長承認"
    levels = ["主任承認", "課長承認", "部長承認", "本部長承認"]
    if not base:
        return ""
    idx = levels.index(base)
    if is_medical:
        idx = min(idx + 1, len(levels) - 1)
    if contract_type == "time_and_materials":
        idx = max(idx, levels.index("部長承認"))
    return levels[idx]


def make_project_master(contract_df: pd.DataFrame, role_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in contract_df.iterrows():
        project = row["project"]
        roles = role_df[role_df["project"].eq(project)] if not role_df.empty else pd.DataFrame()
        rows.append(
            {
                "project": project,
                "contract_type": row.get("contract_type", ""),
                "contract_amount_tax_in": row.get("contract_amount_tax_in", ""),
                "upfront_amount": row.get("upfront_amount", ""),
                "is_medical": row.get("is_medical", False),
                "approval_level": approval_level(
                    pd.to_numeric(row.get("contract_amount_tax_in"), errors="coerce"),
                    bool(row.get("is_medical")),
                    str(row.get("contract_type", "")),
                ),
                "role_names": " | ".join((roles["role"].astype(str) + ":" + roles["name"].astype(str)).drop_duplicates().tolist()) if not roles.empty else "",
            }
        )
    return pd.DataFrame(rows)


def build_probe_answers(project_df: pd.DataFrame, role_df: pd.DataFrame, resource_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    apr_m3 = project_df[project_df["approval_level"].eq("本部長承認")]
    rows.append(
        {
            "index": 38,
            "question": "社内管理のAPRに照らして、APR-M3が必要な案件を主略称ですべて挙げ、それらの契約金額(税込)の合計を答えてください。",
            "candidate_answer": f"{'、'.join(apr_m3['project'].astype(str).tolist())}; 合計 {int(pd.to_numeric(apr_m3['contract_amount_tax_in'], errors='coerce').fillna(0).sum()):,}円"
            if not apr_m3.empty
            else "",
            "needs_review": True,
        }
    )
    max_upfront = project_df.copy()
    max_upfront["upfront_amount_num"] = pd.to_numeric(max_upfront["upfront_amount"], errors="coerce")
    max_upfront = max_upfront.dropna(subset=["upfront_amount_num"]).sort_values("upfront_amount_num", ascending=False)
    rows.append(
        {
            "index": 46,
            "question": "着手金が最も高い案件について、その案件のESの内線番号を教えてください。",
            "candidate_answer": max_upfront.iloc[0]["project"] if not max_upfront.empty else "",
            "needs_review": True,
        }
    )
    kaede_resources = resource_df[resource_df["project"].str.contains("かえで", na=False)] if not resource_df.empty else pd.DataFrame()
    rows.append(
        {
            "index": 79,
            "question": "かえで総合病院の計画フォルダ内で、1タスク当たりの想定工数が最も大きい人と工数を答える。",
            "candidate_answer": "resource rows: " + str(len(kaede_resources)),
            "needs_review": True,
        }
    )
    return pd.DataFrame(rows)


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    contract_df, role_df = build_contract_tables()
    resource_df = build_schedule_resource_table()
    project_df = make_project_master(contract_df, role_df)
    probe_df = build_probe_answers(project_df, role_df, resource_df)

    contract_path = TABLE_DIR / "contract_terms_inventory.csv"
    role_path = TABLE_DIR / "role_assignment_inventory.csv"
    resource_path = TABLE_DIR / "schedule_resource_inventory.csv"
    project_path = TABLE_DIR / "project_master_aggregation.csv"
    probe_path = TABLE_DIR / "cross_project_question_probe.csv"
    contract_df.to_csv(contract_path, index=False, encoding="utf-8-sig")
    role_df.to_csv(role_path, index=False, encoding="utf-8-sig")
    resource_df.to_csv(resource_path, index=False, encoding="utf-8-sig")
    project_df.to_csv(project_path, index=False, encoding="utf-8-sig")
    probe_df.to_csv(probe_path, index=False, encoding="utf-8-sig")

    report = f"""# EDA051: 全案件横断集計テーブル

## 背景と目的

EDA048では、全案件横断集計が残件16件中3件を占めた。
検索文脈だけでは全件比較が保証できないため、契約条件、金額、担当体制、計画リソースを案件単位のテーブルへ正規化する。

## 結果

- 契約条件レコード数: {len(contract_df)}
- 役割/担当者レコード数: {len(role_df)}
- 計画/リソース候補レコード数: {len(resource_df)}
- 案件マスター行数: {len(project_df)}
- 残件候補行数: {len(probe_df)}

## 残件候補

凡例: `candidate_answer` は横断テーブルから作った候補、`needs_review` は提出採用前に確認が必要かを表す。

{probe_df.to_markdown(index=False)}

## 出力

- 契約条件: `{contract_path.relative_to(BASE_DIR).as_posix()}`
- 役割/担当者: `{role_path.relative_to(BASE_DIR).as_posix()}`
- 計画/リソース候補: `{resource_path.relative_to(BASE_DIR).as_posix()}`
- 案件マスター: `{project_path.relative_to(BASE_DIR).as_posix()}`
- 残件候補: `{probe_path.relative_to(BASE_DIR).as_posix()}`

## 注意

契約金額や着手金はMarkdown本文から正規表現で抽出している。
最終提出用では、抽出元の構造JSONや契約書表を併用し、金額の取り違えを検査する必要がある。
ESなどの役割略称と内線番号を結びつけるには、EDA049の座席表テーブルと役割テーブルを結合する。
"""
    report_path = OUT_DIR / "eda051_report.md"
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "eda": "EDA051",
        "contract_record_count": int(len(contract_df)),
        "role_record_count": int(len(role_df)),
        "resource_record_count": int(len(resource_df)),
        "project_master_count": int(len(project_df)),
        "outputs": [
            contract_path.relative_to(BASE_DIR).as_posix(),
            role_path.relative_to(BASE_DIR).as_posix(),
            resource_path.relative_to(BASE_DIR).as_posix(),
            project_path.relative_to(BASE_DIR).as_posix(),
            probe_path.relative_to(BASE_DIR).as_posix(),
            report_path.relative_to(BASE_DIR).as_posix(),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
