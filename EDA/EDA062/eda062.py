from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PROJECTS = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ" / "プロジェクト"
OUTPUT_DIR = ROOT / "data" / "processed" / "share" / "share" / "契約管理"
PERIOD_CSV = OUTPUT_DIR / "project_contract_periods.csv"
PAYMENT_CSV = OUTPUT_DIR / "project_payment_schedule.csv"
MONTHLY_CSV = OUTPUT_DIR / "payment_monthly_totals.csv"
AMOUNT_CSV = OUTPUT_DIR / "project_amount_comparison.csv"
DECISION_POLICY = ROOT / "data" / "raw" / "share" / "share" / "共有ドライブ" / "社内管理" / "データアステル社内管理_決裁基準.md"
EDA_DIR = ROOT / "EDA" / "EDA062"
REPORT_MD = EDA_DIR / "eda062_report.md"

DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def project_name_from_path(path: Path) -> str:
    """契約書パスのプロジェクト直下から案件名を取得する。"""
    parts = path.parts
    project_index = parts.index("プロジェクト")
    return parts[project_index + 1]


def choose_contract_files() -> list[Path]:
    """各案件の契約書を1件選び、draftなどの比較用ファイルは除外する。"""
    candidates = [
        path
        for path in PROCESSED_PROJECTS.rglob("01.契約/*.md")
        if "draft" not in path.name.lower() and "old" not in path.name.lower()
    ]
    selected: dict[str, Path] = {}
    for path in sorted(candidates):
        project = project_name_from_path(path)
        selected.setdefault(project, path)
    return list(selected.values())


def choose_project_document(project: str, major_folder: str, exclude_old: bool = True) -> Path | None:
    """案件の提案書または最終報告書から、比較対象の最新版候補を選ぶ。"""
    folder = PROCESSED_PROJECTS / project / major_folder
    candidates = [path for path in folder.glob("*.md") if not (exclude_old and "old" in str(path).lower())]
    if not candidates:
        return None

    # 同じフォルダに調査資料などがある場合は、比較対象の正式文書を優先する。
    if major_folder == "00.提案":
        named = [path for path in candidates if "提案書" in path.name]
        if named:
            candidates = named
    elif major_folder == "06.報告書":
        named = [path for path in candidates if "最終報告" in path.name]
        if named:
            candidates = named

    def version_key(path: Path) -> tuple[int, str]:
        match = re.search(r"[_-]v(\d+)", path.stem, flags=re.IGNORECASE)
        return (int(match.group(1)) if match else 0, path.name)

    return sorted(candidates, key=version_key)[-1]


def extract_gross_amount(text: str, preferred_labels: list[str]) -> tuple[int | None, str]:
    """税込・最終請求に関するラベルの近傍から金額と抽出根拠を取得する。"""
    lines = text.splitlines()
    for label in preferred_labels:
        for index, line in enumerate(lines):
            if label not in line:
                continue
            window = "\n".join(lines[index : index + 3])
            before_tax = re.search(r"(?:税込(?:金額|合計|見込額)?|金額\s*[（(]税込[）)])[^0-9]{0,30}([0-9][0-9,]*)", window)
            after_tax = re.search(r"([0-9][0-9,]*)\s*(?:円|JPY)?\s*[（(]\s*税込\s*[）)]", window)
            # 同じ行に「4,620,000（税込）」がある場合を優先し、後続行の日付を拾わない。
            match = after_tax or before_tax
            if match:
                return int(match.group(1).replace(",", "")), label
    return None, "未抽出"


def required_approval_level(project: str, amount: int | None, contract_type: str, amount_kind: str) -> tuple[str, str]:
    """決裁基準Markdownに従い、金額・案件種別・契約形態から必要承認を判定する。"""
    if amount is None:
        return "判定不能", "税込金額を抽出できないため判定不能"
    levels = ["主任承認", "課長承認", "部長承認", "本部長承認"]
    if amount < 3_000_000:
        index = 0
        band = "3,000,000円未満"
    elif amount < 5_000_000:
        index = 1
        band = "3,000,000円以上5,000,000円未満"
    elif amount < 8_000_000:
        index = 2
        band = "5,000,000円以上8,000,000円未満"
    else:
        index = 3
        band = "8,000,000円以上"
    reasons = [f"通常基準: {band} -> {levels[index]}"]
    is_medical = bool(re.search(r"医療|病院|診療所|クリニック", project))
    if is_medical:
        index = min(index + 1, len(levels) - 1)
        reasons.append("医療案件のため1段階引き上げ")
    if contract_type == "time_and_materials" and index < 2:
        index = 2
        reasons.append("time_and_materials契約のため部長承認以上")
    if amount_kind == "提案時見込金額":
        reasons.insert(0, "提案時見込金額へ決裁基準を仮適用")
    else:
        reasons.insert(0, "最終報告時金額を契約金額として決裁基準を適用")
    return levels[index], "、".join(reasons)


def build_amount_comparison(project: str, contract_type: str) -> dict[str, object]:
    """提案書と最終報告書の税込金額を比較し、根拠ファイルも残す。"""
    proposal_path = choose_project_document(project, "00.提案")
    final_path = choose_project_document(project, "06.報告書")
    proposal_amount, proposal_basis = (None, "提案書未発見")
    final_amount, final_basis = (None, "最終報告書未発見")
    proposal_approval_level, proposal_approval_basis = required_approval_level(project, None, contract_type, "提案時見込金額")
    final_approval_level, final_approval_basis = required_approval_level(project, None, contract_type, "最終報告時金額")
    if proposal_path:
        proposal_text = proposal_path.read_text(encoding="utf-8")
        proposal_amount, proposal_basis = extract_gross_amount(
            proposal_text,
            ["契約金額（税込）", "見込金額（税込）", "金額（税込）", "契約金額"],
        )
    if final_path:
        final_text = final_path.read_text(encoding="utf-8")
        final_amount, final_basis = extract_gross_amount(
            final_text,
            ["最終請求金額（税込）", "税込金額", "契約金額（税込）", "契約金額", "固定価格契約", "固定価格"],
        )
    proposal_approval_level, proposal_approval_basis = required_approval_level(project, proposal_amount, contract_type, "提案時見込金額")
    final_approval_level, final_approval_basis = required_approval_level(project, final_amount, contract_type, "最終報告時金額")
    difference = ""
    differs = "比較不能"
    status = "比較不能"
    if proposal_amount is not None and final_amount is not None:
        difference = final_amount - proposal_amount
        differs = bool(difference != 0)
        status = "比較完了"
    return {
        "project_name": project,
        "proposal_amount_gross_yen": proposal_amount if proposal_amount is not None else "",
        "proposal_amount_basis": proposal_basis,
        "proposal_source_file": str(proposal_path.relative_to(ROOT)) if proposal_path else "",
        "proposal_approval_level": proposal_approval_level,
        "proposal_approval_basis": proposal_approval_basis,
        "final_report_amount_gross_yen": final_amount if final_amount is not None else "",
        "final_report_amount_basis": final_basis,
        "final_report_source_file": str(final_path.relative_to(ROOT)) if final_path else "",
        "final_report_approval_level": final_approval_level,
        "final_report_approval_basis": final_approval_basis,
        "amount_difference_yen": difference,
        "amount_differs": differs,
        "amount_comparison_status": status,
    }


def extract_period(text: str) -> dict[str, object]:
    """契約期間を明示日付、または開始日と週数から抽出する。"""
    direct = re.search(
        rf"(?:契約期間|有効期間|本契約の期間)[^\n]*?{DATE_PATTERN}\s*\*{{0,2}}\s*(?:から|〜|～)\s*\*{{0,2}}\s*{DATE_PATTERN}",
        text,
    )
    if direct:
        start = parse_date(direct.group(1))
        end = parse_date(direct.group(2))
        return {
            "contract_start_date": start.isoformat(),
            "contract_end_date": end.isoformat(),
            "period_basis": "契約書に開始日・終了日が明記",
        }

    derived = re.search(rf"(?:契約期間|有効期間)[^\n]*?{DATE_PATTERN}\s*\*{{0,2}}\s*から起算して(\d+)週間", text)
    if derived:
        start = parse_date(derived.group(1))
        weeks = int(derived.group(2))
        end = start + timedelta(weeks=weeks) - timedelta(days=1)
        return {
            "contract_start_date": start.isoformat(),
            "contract_end_date": end.isoformat(),
            "period_basis": f"契約書の開始日と{weeks}週間から終了日を導出",
        }

    return {
        "contract_start_date": "",
        "contract_end_date": "",
        "period_basis": "契約期間を自動抽出できず",
    }


def extract_contract_type(text: str) -> str:
    if "time_and_materials" in text.lower():
        return "time_and_materials"
    if "固定価格" in text:
        return "固定価格"
    return ""


def parse_yen(value: str) -> int | None:
    match = re.search(r"([0-9][0-9,]*)円", value.replace(" ", ""))
    return int(match.group(1).replace(",", "")) if match else None


def extract_payment_rows(text: str, project: str, source_path: Path) -> list[dict[str, object]]:
    """契約書の支払条件表から支払期日と税込金額を行単位で抽出する。"""
    lines = text.splitlines()
    rows: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        if not line.startswith("|") or not ("支払期日" in line or "支払期限" in line):
            continue
        headers = [cell.strip() for cell in line.strip().strip("|").split("|")]
        gross_indexes = [i for i, header in enumerate(headers) if "税込" in header]
        condition_indexes = [i for i, header in enumerate(headers) if "支払条件" in header]
        if not gross_indexes:
            continue
        gross_index = gross_indexes[0]
        row_index = index + 2
        while row_index < len(lines) and lines[row_index].startswith("|"):
            cells = [cell.strip() for cell in lines[row_index].strip().strip("|").split("|")]
            if len(cells) != len(headers) or all(set(cell) <= {"-", " "} for cell in cells):
                row_index += 1
                continue
            payment_dates = re.findall(DATE_PATTERN, cells[-1])
            if payment_dates:
                gross_amount = parse_yen(cells[gross_index])
                rows.append(
                    {
                        "project_name": project,
                        "payment_sequence": cells[0],
                        "payment_date": payment_dates[-1],
                        "payment_month": payment_dates[-1][:7],
                        "gross_amount_yen": gross_amount,
                        "payment_condition": cells[condition_indexes[0]] if condition_indexes else "",
                        "source_file": str(source_path.relative_to(ROOT)),
                    }
                )
            row_index += 1
        break
    return rows


def build_ledgers() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    period_rows: list[dict[str, object]] = []
    payment_rows: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    amount_rows: list[dict[str, object]] = []
    for path in choose_contract_files():
        project = project_name_from_path(path)
        text = path.read_text(encoding="utf-8")
        period = extract_period(text)
        start = period["contract_start_date"]
        end = period["contract_end_date"]
        duration_days = ""
        if start and end:
            duration_days = (parse_date(str(end)) - parse_date(str(start))).days + 1
        period_rows.append(
            {
                "project_name": project,
                **period,
                "contract_duration_days_inclusive": duration_days,
                "contract_type": extract_contract_type(text),
                "contract_started_by_2026-07-01": bool(start and parse_date(str(start)) <= date(2026, 7, 1)),
                "source_file": str(path.relative_to(ROOT)),
            }
        )
        amount_rows.append(build_amount_comparison(project, extract_contract_type(text)))
        payments = extract_payment_rows(text, project, path)
        payment_rows.extend(payments)
        if not period["contract_start_date"] or not period["contract_end_date"]:
            diagnostics.append({"project_name": project, "issue": "契約期間の日付を抽出できませんでした", "source_file": str(path.relative_to(ROOT))})
        if not payments:
            diagnostics.append({"project_name": project, "issue": "支払条件表から支払行を抽出できませんでした", "source_file": str(path.relative_to(ROOT))})
    return pd.DataFrame(period_rows), pd.DataFrame(payment_rows), pd.DataFrame(amount_rows), diagnostics


def build_report(
    periods: pd.DataFrame,
    payments: pd.DataFrame,
    monthly_totals: pd.DataFrame,
    amounts: pd.DataFrame,
    diagnostics: list[dict[str, object]],
) -> str:
    lines = [
        "# EDA062 案件契約期間・支払予定台帳",
        "",
        "## 目的",
        "",
        "index 40の質問で必要となる各案件の契約期間を案件横断で整理した。支払月ごとの精算総額も確認できるよう、契約書の支払期日と税込金額を別台帳にした。さらにindex 67のように提案時と最終報告時の金額差を問う質問に備え、正式な提案書と最終報告書の税込金額を案件単位で比較した。承認レベルは社内決裁基準Markdownの金額帯、医療案件、time_and_materials契約の規則から算出した。",
        "",
        "## 出力ファイル",
        "",
        f"- 契約期間台帳: `{PERIOD_CSV.relative_to(ROOT)}`",
        f"- 支払予定台帳: `{PAYMENT_CSV.relative_to(ROOT)}`",
        f"- 支払月別集計: `{MONTHLY_CSV.relative_to(ROOT)}`",
        f"- 提案時・最終報告時の金額比較: `{AMOUNT_CSV.relative_to(ROOT)}`",
        f"- 承認レベルの根拠: `{DECISION_POLICY.relative_to(ROOT)}`",
        "",
        "凡例: 契約期間台帳の `project_name` は案件名、`contract_start_date`/`contract_end_date` は契約期間、`contract_duration_days_inclusive` は開始日と終了日を含む日数、`contract_started_by_2026-07-01` は質問の基準日までに契約開始済みか、`source_file` は根拠契約書を表す。支払予定台帳の `payment_month` は支払期日の年月、`gross_amount_yen` は税込金額である。",
        "",
        "## 集計結果",
        "",
        f"- 契約案件数: {len(periods)}",
        f"- 支払予定行数: {len(payments)}",
        f"- 支払月数: {payments['payment_month'].nunique() if not payments.empty else 0}",
        f"- 提案・最終報告の金額比較完了案件数: {(amounts['amount_comparison_status'] == '比較完了').sum()}",
        f"- 提案時と最終報告時で金額が異なる案件数: {(amounts['amount_differs'] == True).sum()}",
        f"- 金額比較不能案件数: {(amounts['amount_comparison_status'] == '比較不能').sum()}",
        "",
        "### 契約期間台帳",
        "",
    ]
    lines.extend(periods.to_markdown(index=False).splitlines())
    lines.extend(["", "凡例: 表の各行は1案件、日付は契約書から抽出または導出した契約期間を表す。", "", "### 支払予定台帳", ""])
    lines.extend(payments.to_markdown(index=False).splitlines())
    lines.extend(["", "凡例: 表の各行は契約書の1支払回、`payment_month` は月別集計のキー、`gross_amount_yen` は税込支払額を表す。"])
    lines.extend(["", "### 支払月別集計", ""])
    lines.extend(monthly_totals.to_markdown(index=False).splitlines())
    lines.extend(["", "凡例: `payment_month` ごとに支払回数と税込支払予定額を合計した表である。"])
    lines.extend(["", "### 提案時金額と最終報告時金額の比較", ""])
    lines.extend(amounts.to_markdown(index=False).splitlines())
    lines.extend(["", "凡例: `proposal_amount_gross_yen` は提案書の税込金額、`final_report_amount_gross_yen` は最終報告書の税込・最終請求金額、`amount_difference_yen` は最終報告時金額から提案時金額を引いた差額、`amount_differs` は差額が0でないか、`amount_comparison_status` は比較可否を表す。`proposal_approval_level` と `final_report_approval_level` は、決裁基準に基づく必要承認レベル、`*_approval_basis` は金額帯・医療案件・契約形態による判定理由である。提案時金額には見込金額へ基準を仮適用し、最終報告時金額には契約金額として基準を適用している。金額が見つからない案件は判定不能としている。"])
    if diagnostics:
        lines.extend(["", "## 要確認", "", "| project_name | issue | source_file |", "|:---|:---|:---|"])
        lines.extend(f"| {row['project_name']} | {row['issue']} | `{row['source_file']}` |" for row in diagnostics)
        lines.extend(["", "凡例: 自動抽出できなかった項目を記録している。"])
    return "\n".join(lines) + "\n"


def main() -> None:
    periods, payments, amounts, diagnostics = build_ledgers()
    periods = periods.merge(
        amounts[
            [
                "project_name",
                "proposal_amount_gross_yen",
                "proposal_amount_basis",
                "proposal_source_file",
                "proposal_approval_level",
                "proposal_approval_basis",
                "final_report_amount_gross_yen",
                "final_report_amount_basis",
                "final_report_source_file",
                "final_report_approval_level",
                "final_report_approval_basis",
                "amount_difference_yen",
                "amount_differs",
                "amount_comparison_status",
            ]
        ],
        on="project_name",
        how="left",
    )
    if payments.empty:
        monthly_totals = pd.DataFrame(columns=["payment_month", "payment_count", "total_gross_amount_yen"])
    else:
        payments["gross_amount_yen"] = pd.to_numeric(payments["gross_amount_yen"], errors="coerce")
        monthly_totals = (
            payments.groupby("payment_month", as_index=False)
            .agg(payment_count=("gross_amount_yen", "size"), total_gross_amount_yen=("gross_amount_yen", "sum"))
            .sort_values("payment_month")
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EDA_DIR.mkdir(parents=True, exist_ok=True)
    periods.to_csv(PERIOD_CSV, index=False, encoding="utf-8-sig")
    payments.to_csv(PAYMENT_CSV, index=False, encoding="utf-8-sig")
    monthly_totals.to_csv(MONTHLY_CSV, index=False, encoding="utf-8-sig")
    amounts.to_csv(AMOUNT_CSV, index=False, encoding="utf-8-sig")
    REPORT_MD.write_text(build_report(periods, payments, monthly_totals, amounts, diagnostics), encoding="utf-8")
    manifest = {
        "eda": "EDA062",
        "period_csv": str(PERIOD_CSV.relative_to(ROOT)),
        "payment_csv": str(PAYMENT_CSV.relative_to(ROOT)),
        "monthly_totals_csv": str(MONTHLY_CSV.relative_to(ROOT)),
        "amount_comparison_csv": str(AMOUNT_CSV.relative_to(ROOT)),
        "decision_policy": str(DECISION_POLICY.relative_to(ROOT)),
        "report": str(REPORT_MD.relative_to(ROOT)),
        "project_count": int(len(periods)),
        "payment_row_count": int(len(payments)),
        "amount_comparison_complete_count": int((amounts["amount_comparison_status"] == "比較完了").sum()),
        "amount_differs_count": int((amounts["amount_differs"] == True).sum()),
        "amount_comparison_unavailable_count": int((amounts["amount_comparison_status"] == "比較不能").sum()),
        "diagnostic_count": len(diagnostics),
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
