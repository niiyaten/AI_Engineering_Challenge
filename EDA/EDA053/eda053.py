from __future__ import annotations

import csv
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"

BASE_RESULT = BASE_DIR / "EDA" / "EDA046" / "tables" / "test_all_remaining_routes_result.csv"
SEAT_PROBE = BASE_DIR / "EDA" / "EDA049" / "tables" / "seat_question_probe.csv"
PDF_PROBE = BASE_DIR / "EDA" / "EDA052" / "tables" / "no_text_pdf_question_probe.csv"

UNKNOWN = "\u308f\u304b\u308a\u307e\u305b\u3093"


def norm(value: object) -> str:
    """回答の空白と文字種をそろえる。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def is_unknown(value: object) -> bool:
    """未回答扱いの回答かどうかを判定する。"""
    text = norm(value)
    return text == "" or text == UNKNOWN or "情報が不足" in text


def truthy(value: object) -> bool:
    return norm(value).lower() in {"true", "1", "yes"}


def shorten_pdf_answer(index: int, answer: str) -> str:
    """OCR候補の長文から、提出向けの短い回答へ整える。"""
    text = norm(answer)
    if index == 18:
        return text
    if index == 93:
        # A10の内容をそのまま答える問題なので、JSON風断片からcontentだけを抜く。
        m = re.search(r'"action_id"\s*:\s*"A10".{0,120}?"content"\s*:\s*"([^"]+)"', text)
        if m:
            return m.group(1)
        m = re.search(r"A10[^。]*?([^\s。]*index再実験[^\s。]*)", text)
        if m:
            return m.group(1)
        if "index再実験の結果反映" in text:
            return "index再実験の結果反映"
    return text[:300]


def load_candidates() -> pd.DataFrame:
    """EDA049/EDA052の候補を統合し、安全度を付ける。"""
    rows: list[dict[str, Any]] = []
    if PDF_PROBE.exists():
        pdf_df = pd.read_csv(PDF_PROBE, encoding="utf-8-sig", dtype=str).fillna("")
        for _, row in pdf_df.iterrows():
            index = int(row["index"])
            answer = shorten_pdf_answer(index, row.get("candidate_answer", ""))
            if answer:
                rows.append(
                    {
                        "index": index,
                        "candidate_answer": answer,
                        "source": "EDA052_pdf_vision_ocr",
                        "needs_review": truthy(row.get("needs_review")),
                        "safe_to_use": not truthy(row.get("needs_review")),
                        "evidence": row.get("evidence", ""),
                    }
                )
    if SEAT_PROBE.exists():
        seat_df = pd.read_csv(SEAT_PROBE, encoding="utf-8-sig", dtype=str).fillna("")
        for _, row in seat_df.iterrows():
            answer = norm(row.get("candidate_answer", ""))
            if answer:
                rows.append(
                    {
                        "index": int(row["index"]),
                        "candidate_answer": answer,
                        "source": "EDA049_seat_coordinate_seed",
                        "needs_review": True,
                        "safe_to_use": False,
                        "evidence": "EDA/EDA049/tables/seat_coordinate_table.csv",
                    }
                )
    return pd.DataFrame(rows)


def apply_candidates(base_df: pd.DataFrame, candidates: pd.DataFrame, aggressive: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """base回答に候補を上書きし、採用ログを返す。"""
    out = base_df.copy()
    out["answer_eda053"] = out["answer_after_eda046"].map(norm)
    logs: list[dict[str, Any]] = []
    for _, cand in candidates.iterrows():
        idx = int(cand["index"])
        row_mask = out["index"].astype(int).eq(idx)
        if not row_mask.any():
            continue
        before = out.loc[row_mask, "answer_eda053"].iloc[0]
        can_use = bool(cand["safe_to_use"]) or aggressive
        adopted = is_unknown(before) and can_use and bool(norm(cand["candidate_answer"]))
        if adopted:
            out.loc[row_mask, "answer_eda053"] = norm(cand["candidate_answer"])
        logs.append(
            {
                "index": idx,
                "question": out.loc[row_mask, "question"].iloc[0],
                "answer_before": before,
                "candidate_answer": cand["candidate_answer"],
                "source": cand["source"],
                "safe_to_use": cand["safe_to_use"],
                "aggressive_mode": aggressive,
                "adopted": adopted,
                "evidence": cand.get("evidence", ""),
            }
        )
    return out, pd.DataFrame(logs)


def write_prediction_files(df: pd.DataFrame, stem: str) -> tuple[Path, Path]:
    """SIGNATE提出用のCSVとzipを作る。"""
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PRED_DIR / f"{stem}_predictions.csv"
    zip_path = PRED_DIR / f"{stem}_submission.zip"
    pred = df[["index", "answer_eda053"]].copy()
    pred["index"] = pred["index"].astype(int)
    pred = pred.sort_values("index")
    pred.to_csv(csv_path, index=False, header=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, arcname="predictions.csv")
    return csv_path, zip_path


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    base_df = pd.read_csv(BASE_RESULT, encoding="utf-8-sig", dtype=str).fillna("")
    candidates = load_candidates()

    safe_df, safe_log = apply_candidates(base_df, candidates, aggressive=False)
    aggressive_df, aggressive_log = apply_candidates(base_df, candidates, aggressive=True)

    safe_csv, safe_zip = write_prediction_files(safe_df, "eda053_safe_unknown_reduction")
    aggressive_csv, aggressive_zip = write_prediction_files(aggressive_df, "eda053_aggressive_unknown_reduction")

    candidate_path = TABLE_DIR / "eda053_candidate_pool.csv"
    safe_log_path = TABLE_DIR / "eda053_safe_adoption_log.csv"
    aggressive_log_path = TABLE_DIR / "eda053_aggressive_adoption_log.csv"
    candidates.to_csv(candidate_path, index=False, encoding="utf-8-sig")
    safe_log.to_csv(safe_log_path, index=False, encoding="utf-8-sig")
    aggressive_log.to_csv(aggressive_log_path, index=False, encoding="utf-8-sig")

    before_unknown = int(base_df["answer_after_eda046"].map(is_unknown).sum())
    safe_unknown = int(safe_df["answer_eda053"].map(is_unknown).sum())
    aggressive_unknown = int(aggressive_df["answer_eda053"].map(is_unknown).sum())

    report = f"""# EDA053: `わかりません` 候補統合

## 背景と目的

EDA046時点でtest 100件中16件が `わかりません` のまま残っている。
EDA049の座席表候補とEDA052のPDF Vision OCR候補を使い、未回答をどこまで減らせるか確認する。

## 方針

- safe版: `needs_review=False` の候補だけを採用する。
- aggressive版: 座席表の検証用候補も採用する。
- EDA051の横断集計候補はまだ回答として不完全なため、今回は採用しない。

## 結果

- EDA046時点の `わかりません`: {before_unknown}
- safe版の `わかりません`: {safe_unknown}
- aggressive版の `わかりません`: {aggressive_unknown}
- safe版の追加採用: {int(safe_log["adopted"].sum()) if not safe_log.empty else 0}
- aggressive版の追加採用: {int(aggressive_log["adopted"].sum()) if not aggressive_log.empty else 0}

## 出力

- 候補プール: `{candidate_path.relative_to(BASE_DIR).as_posix()}`
- safe採用ログ: `{safe_log_path.relative_to(BASE_DIR).as_posix()}`
- aggressive採用ログ: `{aggressive_log_path.relative_to(BASE_DIR).as_posix()}`
- safe提出zip: `{safe_zip.relative_to(BASE_DIR).as_posix()}`
- aggressive提出zip: `{aggressive_zip.relative_to(BASE_DIR).as_posix()}`

## 注意

座席表候補は検証用seed由来であり、提出採用前に画像と照合する必要がある。
PDF Vision OCR候補もraw responseとページ画像を確認してから提出判断する。
"""
    report_path = OUT_DIR / "eda053_report.md"
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "eda": "EDA053",
        "before_unknown": before_unknown,
        "safe_unknown": safe_unknown,
        "aggressive_unknown": aggressive_unknown,
        "safe_zip": safe_zip.relative_to(BASE_DIR).as_posix(),
        "aggressive_zip": aggressive_zip.relative_to(BASE_DIR).as_posix(),
        "outputs": [
            candidate_path.relative_to(BASE_DIR).as_posix(),
            safe_log_path.relative_to(BASE_DIR).as_posix(),
            aggressive_log_path.relative_to(BASE_DIR).as_posix(),
            safe_csv.relative_to(BASE_DIR).as_posix(),
            safe_zip.relative_to(BASE_DIR).as_posix(),
            aggressive_csv.relative_to(BASE_DIR).as_posix(),
            aggressive_zip.relative_to(BASE_DIR).as_posix(),
            report_path.relative_to(BASE_DIR).as_posix(),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
