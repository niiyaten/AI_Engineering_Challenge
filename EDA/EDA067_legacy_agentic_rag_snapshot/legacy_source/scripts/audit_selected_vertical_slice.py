from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/output/remaining_calculation_selected_capability_fresh_v1/analysis"
STATUS_INVENTORY = ROOT / "data/output/semantic_status_lookup_capability_final_fresh_v2/analysis/semantic_status_question_inventory.csv"
MATRIX = ROOT / "data/output/remaining_semantic_role_lookup_capability_test_full_fresh_v4/analysis/capability_matrix_after_remaining_semantic_role.csv"
CALC_INVENTORY = ROOT / "data/output/remaining_calculation_capability_final_fresh_v1/analysis/calculation_question_inventory.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["dataset", "question_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def matrix_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("dataset", ""), row.get("question_id", "")


def current_capability(row: dict[str, str]) -> str:
    return row.get("primary_question_type") or row.get("primary_capability") or row.get("capability") or "unknown"


def status_pattern(row: dict[str, str]) -> str:
    current = current_capability(row)
    if current in {"location_lookup", "calculation", "semantic_list_extraction", "version_diff"}:
        return f"reclassified_to_{current}"
    return "status_candidate_reclassified_or_unsupported"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matrix_rows = read_csv(MATRIX)
    matrix = {matrix_key(row): row for row in matrix_rows}
    status_rows = read_csv(STATUS_INVENTORY)

    transition_rows: list[dict[str, object]] = []
    for old in status_rows:
        current = matrix.get((old.get("dataset", ""), old.get("question_id", "")), {})
        previous = old.get("current_capability", "semantic_status_lookup")
        now = current_capability(current)
        transition_rows.append(
            {
                "dataset": old.get("dataset", ""),
                "question_id": old.get("question_id", ""),
                "question_original": old.get("question_original", ""),
                "previous_capability": previous,
                "current_capability": now,
                "classification_changed": previous != now,
                "previous_failure_stage": old.get("failure_stage", "") or old.get("current_failure_stage", ""),
                "current_failure_stage": current.get("failure_stage", "") or current.get("primary_failure_stage", ""),
                "status_pattern": status_pattern(current),
                "target_entity": old.get("target_entity", ""),
                "target_status": old.get("target_status", ""),
                "target_time_or_version": old.get("target_time", "") or old.get("target_version", ""),
                "implementation_needed": False,
                "deterministic_possible": old.get("deterministic_possible", ""),
                "semantic_selection_required": old.get("semantic_selection_required", ""),
                "reclassification_reason": f"最新Matrixでは{now}として実行・評価されているため、純粋なStatus残件ではない",
                "recommended_executor": now,
            }
        )
    write_csv(OUT / "semantic_status_transition_audit.csv", transition_rows)

    calc_rows = [row for row in read_csv(CALC_INVENTORY) if row.get("primary_calculation_pattern") or row.get("current_pattern")]
    patterns: dict[str, dict[str, object]] = defaultdict(lambda: {"valid": 0, "test": 0, "unresolved": 0, "questions": []})
    for row in calc_rows:
        pattern = row.get("reclassified_pattern") or row.get("primary_calculation_pattern") or "unknown"
        item = patterns[pattern]
        dataset = row.get("dataset", "")
        item[dataset] = int(item[dataset]) + 1
        if row.get("current_answer", "") in {"", "blank"} or row.get("gate_status", "") == "suppressed":
            item["unresolved"] = int(item["unresolved"]) + 1
        item["questions"].append(row.get("question_id", ""))

    priority_rows: list[dict[str, object]] = []
    for pattern, item in sorted(patterns.items()):
        valid = int(item["valid"])
        test = int(item["test"])
        unresolved = int(item["unresolved"])
        if pattern == "coefficient_prediction":
            difficulty, risk, reusability, measurability, reason = 3, 3, 5, 2, "係数名と特徴量名の対応をEvidence付きで決定的に検証でき、複数testへ再利用可能"
        elif pattern in {"ratio_or_percentage", "difference", "ranking_or_argmin", "schedule_effort"}:
            difficulty, risk, reusability, measurability, reason = 3, 3, 4, 2, "既存Engineを再利用できるが、入力列または条件の特定が残る"
        else:
            difficulty, risk, reusability, measurability, reason = 4, 4, 3, 1, "質問ごとに入力仕様の確認が必要"
        priority = (test + valid * 2) * reusability * measurability / max(difficulty * risk, 1)
        priority_rows.append(
            {
                "capability": pattern,
                "valid_total": valid,
                "valid_unresolved": unresolved if valid else 0,
                "test_total": test,
                "test_unresolved": unresolved if test else 0,
                "implementation_needed": unresolved > 0,
                "implementation_difficulty": difficulty,
                "error_risk": risk,
                "reusability": reusability,
                "valid_measurability": measurability,
                "priority_score": round(priority, 4),
                "selection_reason": reason,
                "question_ids": ",".join(item["questions"]),
            }
        )
    # Status is intentionally included with zero implementation-needed rows.
    priority_rows.append(
        {
            "capability": "semantic_status_lookup",
            "valid_total": 0,
            "valid_unresolved": 0,
            "test_total": 0,
            "test_unresolved": 0,
            "implementation_needed": False,
            "implementation_difficulty": 3,
            "error_risk": 4,
            "reusability": 4,
            "valid_measurability": 0,
            "priority_score": 0,
            "selection_reason": "旧Status候補は全件がlocation/calculation/list/version_diffへ再分類済み",
            "question_ids": "",
        }
    )
    priority_rows.sort(key=lambda row: float(row["priority_score"]), reverse=True)
    for index, row in enumerate(priority_rows, 1):
        row["recommended_order"] = index
    write_csv(OUT / "capability_priority_transition_audit.csv", priority_rows)

    unresolved_status = [row for row in transition_rows if row["current_capability"] == "semantic_status_lookup" and row["implementation_needed"]]
    calc_summary = Counter((row.get("reclassified_pattern") or row.get("primary_calculation_pattern") or "unknown") for row in calc_rows)
    report = [
        "# 次Vertical Slice決定",
        "",
        "## Status監査",
        f"旧Status候補は{len(status_rows)}問。最新Matrixで純粋なsemantic_status_lookupとして残る実装必要質問は{len(unresolved_status)}問。",
        "11問はlocation_lookup、calculation、semantic_list_extraction、version_diffへ再分類されており、Status Executorの未実装脱落ではない。",
        "したがってsemantic_status_lookupは今回実装しない。",
        "",
        "## 選択",
        "remaining_calculation",
        "",
        "理由: 複数の未解決計算質問が存在し、既存Calculation Engine、名前ベースの係数照合、独立再計算、Evidenceを再利用できる。",
        "今回の実装範囲はcoefficient_predictionの入力仕様解決と検証に限定し、Statusや他の計算パターンは同時に変更しない。",
        "",
        "## Calculationパターン分布",
    ]
    report.extend(f"- {name}: {count}問" for name, count in sorted(calc_summary.items()))
    report += [
        "",
        "## 実装しない範囲",
        "ratio、difference、ranking、schedule、cross-file計算は今回のSlice外。入力仕様が一意でない質問は抑制する。",
        "test 41・72・92、format待ち2問、role test 43の人間確認状態は正式入力・正解データとして使用しない。",
    ]
    (OUT / "next_vertical_slice_decision.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
