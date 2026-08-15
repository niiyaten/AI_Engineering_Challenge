from __future__ import annotations

import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EDA_DIR = ROOT / "EDA" / "EDA057"
TABLE_DIR = EDA_DIR / "tables"
PRED_DIR = EDA_DIR / "predictions"

BASE_PREDICTIONS = ROOT / "EDA" / "EDA056" / "predictions" / "eda056_meeting_operation_schedule_predictions.csv"
QUESTIONS_TEST = ROOT / "data" / "raw" / "share" / "share" / "質問回答" / "questions_test.csv"
CONTRACTS = ROOT / "EDA" / "EDA051" / "tables" / "contract_terms_inventory.csv"
ROLES = ROOT / "EDA" / "EDA051" / "tables" / "role_assignment_inventory.csv"
SEATS = ROOT / "EDA" / "EDA049" / "tables" / "seat_coordinate_table.csv"


PROJECT_ABBREVIATIONS = {
    "京橋信用ソリューションズ株式会社": "KSS",
    "青葉与信マネジメント株式会社": "AYM",
    "白峰信用リスク評価株式会社": "SHR",
    "株式会社青潮モビリティサービス": "AOSHIO",
    "医療法人社団 蒼泉会 ひがし丘総合病院": "SOHK",
    "株式会社東都人材プラットフォーム": "TOTO",
    "株式会社青嶺不動産アセットマネジメント": "AOMINE",
    "医療法人社団 恒一会 かえで総合病院": "KAEDE",
    "株式会社青葉バイオメディカル機器": "AOBM",
    "医療法人社団 蒼樹会 みなみ野女性医療センター": "MINAMINO",
}

APPROVAL_LEVELS = ["主任承認", "課長承認", "部長承認", "本部長承認"]
APPROVAL_CODES = {
    "主任承認": "APR-M0",
    "課長承認": "APR-M1",
    "部長承認": "APR-M2",
    "本部長承認": "APR-M3",
}
DATA_ASTER_KAEDE_STAFF = {"佐藤 健一", "山本 彩乃", "斎藤 悠斗", "松本 真央", "山田 直樹", "池田 直哉"}


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)


def yen(value: float | int) -> str:
    return f"{int(round(float(value))):,}円"


def normal_approval(amount: float) -> str:
    if amount < 3_000_000:
        return "主任承認"
    if amount < 5_000_000:
        return "課長承認"
    if amount < 8_000_000:
        return "部長承認"
    return "本部長承認"


def raise_one_level(level: str) -> str:
    idx = APPROVAL_LEVELS.index(level)
    return APPROVAL_LEVELS[min(idx + 1, len(APPROVAL_LEVELS) - 1)]


def max_level(left: str, right: str) -> str:
    return APPROVAL_LEVELS[max(APPROVAL_LEVELS.index(left), APPROVAL_LEVELS.index(right))]


def apply_apr_rule(row: pd.Series) -> str:
    # 社内決裁基準に従い、金額、医療案件、time_and_materialsの順に承認レベルを決める。
    level = normal_approval(float(row["contract_amount_tax_in"]))
    if bool(row["is_medical"]):
        level = raise_one_level(level)
    if str(row["contract_type"]) == "time_and_materials":
        level = max_level(level, "部長承認")
    return level


def load_contract_master() -> pd.DataFrame:
    df = pd.read_csv(CONTRACTS)
    df = df.sort_values(["project", "source_path"]).drop_duplicates("project", keep="first").copy()
    df["computed_approval"] = df.apply(apply_apr_rule, axis=1)
    df["approval_code"] = df["computed_approval"].map(APPROVAL_CODES)
    df["project_abbreviation"] = df["project"].map(PROJECT_ABBREVIATIONS)
    return df


def answer_apr_m3(contract_master: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    m3 = contract_master[contract_master["approval_code"].eq("APR-M3")].copy()
    if m3.empty:
        return "該当なし。合計0円", m3
    codes = "、".join(m3["project_abbreviation"].fillna(m3["project"]).tolist())
    total = m3["contract_amount_tax_in"].sum()
    return f"{codes}。合計{yen(total)}", m3


def answer_highest_upfront_extension(contract_master: pd.DataFrame) -> tuple[str, dict[str, object]]:
    candidates = contract_master.dropna(subset=["upfront_amount"]).copy()
    target = candidates.sort_values("upfront_amount", ascending=False).iloc[0]

    roles = pd.read_csv(ROLES)
    es_row = roles[
        roles["project"].eq(target["project"])
        & roles["role"].astype(str).str.contains("エグゼクティブスポンサー", na=False)
    ].iloc[0]
    es_name = str(es_row["name"])
    family_name = es_name.split()[0]

    seats = pd.read_csv(SEATS)
    seat_hits = seats[
        seats["name"].astype(str).eq(family_name)
        & seats["role"].astype(str).str.contains("Exec", na=False)
    ].copy()
    if seat_hits.empty:
        raise ValueError(f"ESの内線が座席表から見つかりません: {es_name}")
    seat = seat_hits.iloc[0]

    evidence = {
        "project": target["project"],
        "project_abbreviation": target["project_abbreviation"],
        "upfront_amount": float(target["upfront_amount"]),
        "es_name": es_name,
        "seat_family_name": family_name,
        "extension": int(seat["ext"]),
        "seat_source": seat["source"],
    }
    return str(int(seat["ext"])), evidence


def find_kaede_schedule_status() -> dict[str, str]:
    raw_root = ROOT / "data" / "raw" / "share" / "share" / "共有ドライブ" / "プロジェクト"
    matches = [p for p in raw_root.rglob("*.xlsx") if "かえ" in str(p) and "スケ" in p.name and not p.name.startswith("~$")]
    if not matches:
        return {"status": "not_found", "path": "", "error": ""}

    path = matches[0]
    try:
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=False, read_only=True)
        return {"status": "opened", "path": str(path.relative_to(ROOT)), "error": ",".join(wb.sheetnames)}
    except Exception as exc:  # 鍵付きまたは通常xlsxでない場合は代替資料へ回す。
        return {"status": type(exc).__name__, "path": str(path.relative_to(ROOT)), "error": str(exc)}


def extract_action_records_from_markdown() -> list[dict[str, object]]:
    kaede_root = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ" / "プロジェクト" / "医療法人社団 恒一会 かえで総合病院"
    source_files = [
        kaede_root / "05.会議" / "会議録" / "会議録_2025-09-02.docx.md",
        kaede_root / "05.会議" / "報告資料" / "報告資料_2025-09-16.docx.md",
        kaede_root / "05.会議" / "会議録" / "会議録_2025-09-30.docx.md",
    ]
    records_by_action: dict[str, dict[str, object]] = {}
    action_pattern = re.compile(r"\b(A\d{2})\b")
    name_pattern = re.compile(r"(佐藤 健一|山本 彩乃|斎藤 悠斗|松本 真央|山田 直樹|池田 直哉|柴田 海斗)")

    for source in source_files:
        if not source.exists():
            continue
        for line_no, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            action_match = action_pattern.search(line)
            if not action_match:
                continue
            action_id = action_match.group(1)
            owners = [name for name in name_pattern.findall(line) if name in DATA_ASTER_KAEDE_STAFF]
            if not owners:
                continue
            # 同じAction IDが資料間で重複するため、Action ID単位で重複排除する。
            records_by_action[action_id] = {
                "action_id": action_id,
                "owners": sorted(set(owners)),
                "source_path": str(source.relative_to(ROOT)),
                "line_no": line_no,
                "line": line.strip(),
            }
    return [records_by_action[k] for k in sorted(records_by_action)]


def extract_total_hours() -> tuple[float, str]:
    kaede_root = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ" / "プロジェクト" / "医療法人社団 恒一会 かえで総合病院"
    candidates = [
        kaede_root / "06.報告書" / "医療法人社団 恒一会 かえで総合病院_最終報告.pptx.md",
        kaede_root / "05.会議" / "報告資料" / "報告資料_2025-09-16.docx.md",
    ]
    pattern = re.compile(r"想定(?:総)?工数[：:]\s*([0-9]+(?:\.[0-9]+)?)\s*時間")
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if match:
            return float(match.group(1)), str(path.relative_to(ROOT))
    raise ValueError("かえで案件の想定工数が見つかりません")


def answer_kaede_hours_per_task() -> tuple[str, pd.DataFrame, dict[str, object]]:
    schedule_status = find_kaede_schedule_status()
    action_records = extract_action_records_from_markdown()
    total_hours, hours_source = extract_total_hours()

    counts: Counter[str] = Counter()
    source_lines: defaultdict[str, list[str]] = defaultdict(list)
    for record in action_records:
        for owner in record["owners"]:
            counts[owner] += 1
            source_lines[owner].append(f"{record['action_id']}:{record['source_path']}:{record['line_no']}")

    rows = []
    for owner, task_count in sorted(counts.items()):
        hours_per_task = total_hours / task_count
        rows.append(
            {
                "name": owner,
                "task_count": int(task_count),
                "total_estimated_hours": total_hours,
                "hours_per_task": hours_per_task,
                "evidence_lines": " | ".join(source_lines[owner]),
            }
        )
    owner_df = pd.DataFrame(rows).sort_values(["hours_per_task", "name"], ascending=[False, True])
    winner = owner_df.iloc[0]
    answer = f"{winner['name']}、{winner['hours_per_task']:.2f}時間"
    evidence = {
        "schedule_status": schedule_status,
        "total_hours_source": hours_source,
        "action_record_count": len(action_records),
    }
    return answer, owner_df, evidence


def write_report(
    route_results: pd.DataFrame,
    contract_master: pd.DataFrame,
    kaede_owner_counts: pd.DataFrame,
    evidence: dict[str, object],
) -> None:
    lines = [
        "# EDA057 全案件横断ルート",
        "",
        "## 目的",
        "",
        "EDA056で残った `わかりません` のうち、全案件横断の契約・担当者・社内管理情報を組み合わせる必要がある質問を個別ルートで処理した。",
        "",
        "## 対象質問",
        "",
        route_results[["index", "question", "answer", "route", "needs_review"]].to_markdown(index=False),
        "",
        "凡例: `index` は質問ID、`question` はtest質問文、`answer` はEDA057で採用した回答、`route` は回答生成方法、`needs_review` は根拠が代替資料または不完全抽出に依存するかを表す。",
        "",
        "## APR-M3判定",
        "",
        contract_master[
            [
                "project",
                "project_abbreviation",
                "contract_type",
                "contract_amount_tax_in",
                "is_medical",
                "computed_approval",
                "approval_code",
            ]
        ].to_markdown(index=False),
        "",
        "凡例: `project` は案件名、`project_abbreviation` は社内用語集の主略称、`contract_type` は契約形態、`contract_amount_tax_in` は税込契約金額、`is_medical` は医療案件判定、`computed_approval` と `approval_code` は決裁基準から再計算した承認レベルを表す。",
        "",
        "## 着手金とES内線",
        "",
        f"- 最大着手金案件: {evidence['upfront']['project']} ({yen(evidence['upfront']['upfront_amount'])})",
        f"- ES: {evidence['upfront']['es_name']}",
        f"- 内線: {evidence['upfront']['extension']}",
        f"- 座席表ソース: {evidence['upfront']['seat_source']}",
        "",
        "## かえで案件の工数/担当タスク数",
        "",
        kaede_owner_counts.to_markdown(index=False),
        "",
        "凡例: `name` はデータアステル側担当者、`task_count` はAction ID単位で重複排除した担当タスク数、`total_estimated_hours` は報告資料/最終報告の想定総工数、`hours_per_task` は想定工数を担当タスク数で割った値、`evidence_lines` は根拠行を表す。",
        "",
        "### 鍵付き計画ファイルの扱い",
        "",
        f"- raw schedule path: `{evidence['kaede']['schedule_status']['path']}`",
        f"- open status: `{evidence['kaede']['schedule_status']['status']}`",
        f"- error/detail: `{evidence['kaede']['schedule_status']['error']}`",
        "",
        "計画フォルダの `スケジュール.xlsx` は `BadZipFile` で開けなかったため、問題文の指示に従い、社内用語集で案件略称を確認したうえで、会議録・報告資料・最終報告にあるAction IDと想定工数から代替集計した。",
    ]
    (EDA_DIR / "eda057_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()

    predictions = pd.read_csv(BASE_PREDICTIONS, header=None, names=["index", "answer"])
    questions = pd.read_csv(QUESTIONS_TEST)
    contract_master = load_contract_master()

    answer38, apr_m3 = answer_apr_m3(contract_master)
    answer46, upfront_evidence = answer_highest_upfront_extension(contract_master)
    answer79, kaede_owner_counts, kaede_evidence = answer_kaede_hours_per_task()

    updates = {
        38: {
            "answer": answer38,
            "route": "cross_project_apr_rule",
            "needs_review": False,
            "evidence": {"apr_m3_projects": apr_m3.to_dict(orient="records")},
        },
        46: {
            "answer": answer46,
            "route": "upfront_es_extension_join",
            "needs_review": True,
            "evidence": upfront_evidence,
        },
        79: {
            "answer": answer79,
            "route": "kaede_locked_schedule_fallback_actions",
            "needs_review": True,
            "evidence": kaede_evidence,
        },
    }

    route_rows = []
    for index, info in updates.items():
        predictions.loc[predictions["index"].eq(index), "answer"] = info["answer"]
        question = questions.loc[questions["index"].eq(index), "question"].iloc[0]
        route_rows.append(
            {
                "index": index,
                "question": question,
                "answer": info["answer"],
                "route": info["route"],
                "needs_review": info["needs_review"],
                "evidence_json": json.dumps(info["evidence"], ensure_ascii=False),
            }
        )

    route_results = pd.DataFrame(route_rows).sort_values("index")
    contract_master.to_csv(TABLE_DIR / "cross_project_contract_master.csv", index=False, encoding="utf-8-sig")
    kaede_owner_counts.to_csv(TABLE_DIR / "kaede_task_owner_counts.csv", index=False, encoding="utf-8-sig")
    route_results.to_csv(TABLE_DIR / "eda057_route_results.csv", index=False, encoding="utf-8-sig")

    output_csv = PRED_DIR / "eda057_cross_project_predictions.csv"
    output_zip = PRED_DIR / "eda057_cross_project_submission.zip"
    predictions.to_csv(output_csv, index=False, header=False, encoding="utf-8")
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(output_csv, arcname="predictions.csv")

    write_report(
        route_results=route_results,
        contract_master=contract_master,
        kaede_owner_counts=kaede_owner_counts,
        evidence={"upfront": upfront_evidence, "kaede": kaede_evidence},
    )
    manifest = {
        "eda": "EDA057",
        "purpose": "全案件横断の契約・担当者・社内管理情報を用いて残未回答を削減",
        "base_predictions": str(BASE_PREDICTIONS.relative_to(ROOT)),
        "output_csv": str(output_csv.relative_to(ROOT)),
        "output_zip": str(output_zip.relative_to(ROOT)),
        "updated_indices": sorted(updates),
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
