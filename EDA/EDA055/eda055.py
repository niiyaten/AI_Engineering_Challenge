from __future__ import annotations

import csv
import json
import re
import unicodedata
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"
BASE_PRED = ROOT / "EDA" / "EDA054" / "predictions" / "eda054_remaining_unknown_submission_predictions.csv"
PROCESSED = ROOT / "data" / "processed" / "share"
RAW_SHARE = ROOT / "data" / "raw" / "share"


@dataclass
class RouteResult:
    index: int
    route: str
    candidate_answer: str
    adopted: bool
    confidence: str
    needs_review: bool
    evidence: str
    source_paths: list[str]


def norm(value: object) -> str:
    """検索とCSV出力を安定させるために、Unicode表記と改行をそろえる。"""
    text = "" if value is None else str(value)
    return unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def compact(value: object, limit: int = 1200) -> str:
    """根拠欄が巨大にならないよう、空白を詰めて上限長に収める。"""
    return re.sub(r"\s+", " ", norm(value)).strip()[:limit]


def find_first_file(root: Path, file_name: str, required_text: str | None = None) -> Path:
    """ファイル名で候補を探し、必要なら中身に特定文字列を含むものだけに絞る。"""
    for path in root.rglob(file_name):
        if required_text is None:
            return path
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except UnicodeDecodeError:
            continue
        if required_text in text:
            return path
    raise FileNotFoundError(file_name)


def answer_chart2_blue_line() -> RouteResult:
    """Word内chart2.xmlから、青色既定系列のx=3に相当する値を取り出す。"""
    docx_path = find_first_file(RAW_SHARE, "基礎分析.docx")
    ns = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
    with zipfile.ZipFile(docx_path) as zf:
        chart_xml = zf.read("word/charts/chart2.xml")
    root = ET.fromstring(chart_xml)
    series = root.findall(".//c:ser", ns)
    first_series = series[0]
    values = [float(v.text) for v in first_series.findall(".//c:val//c:pt/c:v", ns) if v.text is not None]
    x_value = 3
    # chart2はx=0から6までの7点で、1本目の系列がOffice既定の青線に対応する。
    y_value = values[x_value]
    answer = f"{y_value:.5f}"
    evidence = {
        "chart_xml": "word/charts/chart2.xml",
        "series_index": 1,
        "x_value": x_value,
        "raw_y_value": y_value,
        "series_values": values,
    }
    return RouteResult(
        index=33,
        route="docx_chart_xml_value_extraction",
        candidate_answer=answer,
        adopted=True,
        confidence="high",
        needs_review=False,
        evidence=json.dumps(evidence, ensure_ascii=False),
        source_paths=[rel(docx_path)],
    )


def find_structure_with_text(file_name: str, required_text: str) -> Path:
    for path in PROCESSED.rglob(file_name):
        if required_text in path.read_text(encoding="utf-8", errors="ignore"):
            return path
    raise FileNotFoundError(file_name)


def answer_toto_yellow_cell() -> RouteResult:
    """黄色セルの座標から、前方補完したピボット表の条件と集計値を復元する。"""
    structure_path = find_structure_with_text("train.xlsx.structure.json", "E1409")
    obj = json.loads(structure_path.read_text(encoding="utf-8"))
    styled_sheet: dict[str, Any] | None = None
    styled_cell: dict[str, Any] | None = None
    for sheet in obj.get("sheets", []):
        for cell in sheet.get("styled_cells", []):
            if cell.get("coordinate") == "E1409" and cell.get("fill_color") == "FFFFFF00":
                styled_sheet = sheet
                styled_cell = cell
                break
        if styled_sheet:
            break
    if styled_sheet is None or styled_cell is None:
        raise RuntimeError("E1409の黄色セルが見つかりません。")

    csv_path = ROOT / styled_sheet["exported_csv_path"]
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig").fillna("")
    filled = df.replace("", pd.NA).ffill()
    # Excel行番号は1行目がヘッダーなので、pandasの0始まりindexへ変換する。
    excel_row = 1409
    row_idx = excel_row - 2
    row = filled.iloc[row_idx].to_dict()
    answer = (
        f"抽出条件はGender={row['Gender']}、target={row['target']}、Age={row['Age']}、"
        f"Country={row['Country']}。集計内容は個数={int(float(row['個数']))}。"
    )
    evidence = {
        "sheet_name": styled_sheet.get("sheet_name"),
        "styled_cell": styled_cell,
        "excel_row": excel_row,
        "filled_row": row,
        "near_rows": filled.iloc[row_idx - 3 : row_idx + 4].to_dict(orient="records"),
    }
    return RouteResult(
        index=80,
        route="xlsx_yellow_cell_semantic_extraction",
        candidate_answer=answer,
        adopted=True,
        confidence="high",
        needs_review=False,
        evidence=json.dumps(evidence, ensure_ascii=False),
        source_paths=[rel(structure_path), rel(csv_path)],
    )


def answer_minamino_regression_prediction() -> RouteResult:
    """Excel回帰係数をindex=1770の行に当てはめ、予測値を再計算する。"""
    coef_path = find_first_file(PROCESSED, "Sheet1.csv", required_text="DiabetesPedigreeFunction")
    train_path = coef_path.parent / "train.csv"
    coef_df = pd.read_csv(coef_path)
    train_df = pd.read_csv(train_path)
    target_row = train_df[train_df["index"].eq(1770)].iloc[0]
    feature_names = [
        "DiabetesPedigreeFunction",
        "Pregnancies",
        "BMI",
        "Age",
        "Glucose",
        "Insulin",
        "BloodPressure",
        "SkinThickness",
    ]
    start_idx = coef_df.index[coef_df["col_1"].astype(str).eq("DiabetesPedigreeFunction")][0]
    coef_block = coef_df.loc[start_idx : start_idx + len(feature_names)]

    terms: list[dict[str, float | str]] = []
    intercept = 0.0
    for _, row in coef_block.iterrows():
        name = str(row["col_1"])
        coef = float(row["col_2"])
        if name in feature_names:
            value = float(target_row[name])
            terms.append({"feature": name, "coef": coef, "value": value, "product": coef * value})
        else:
            intercept = coef
    prediction = intercept + sum(float(term["product"]) for term in terms)
    answer = f"{prediction:.5f}"
    evidence = {
        "target_index": 1770,
        "intercept": intercept,
        "terms": terms,
        "prediction": prediction,
    }
    return RouteResult(
        index=83,
        route="xlsx_regression_formula_recompute",
        candidate_answer=answer,
        adopted=True,
        confidence="high",
        needs_review=False,
        evidence=json.dumps(evidence, ensure_ascii=False),
        source_paths=[rel(coef_path), rel(train_path)],
    )


def build_results() -> list[RouteResult]:
    return [
        answer_chart2_blue_line(),
        answer_toto_yellow_cell(),
        answer_minamino_regression_prediction(),
    ]


def write_submission(results: list[RouteResult]) -> tuple[int, int]:
    pred_df = pd.read_csv(BASE_PRED, header=None, names=["index", "answer"], dtype={0: int, 1: str}).fillna("")
    before_unknown = int(pred_df["answer"].eq("わかりません").sum())
    answer_map = pred_df.set_index("index")["answer"].to_dict()
    for result in results:
        if result.adopted:
            answer_map[result.index] = result.candidate_answer
    out_df = pd.DataFrame({"index": sorted(answer_map), "answer": [answer_map[i] for i in sorted(answer_map)]})
    after_unknown = int(out_df["answer"].eq("わかりません").sum())

    pred_path = PRED_DIR / "eda055_chart_format_formula_predictions.csv"
    zip_path = PRED_DIR / "eda055_chart_format_formula_submission.zip"
    out_df.to_csv(pred_path, index=False, header=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(pred_path, arcname="predictions.csv")
    return before_unknown, after_unknown


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    results = build_results()
    before_unknown, after_unknown = write_submission(results)
    result_df = pd.DataFrame([asdict(result) for result in results])
    result_df.to_csv(TABLE_DIR / "eda055_route_results.csv", index=False, encoding="utf-8-sig")

    adopted = int(result_df["adopted"].sum())
    report = f"""# EDA055: グラフ値・黄色セル・回帰係数route

## 背景と目的

EDA054後に残った `わかりません` のうち、ローカルで再現しやすい3件を個別route化する。
対象は、index 33のWordグラフ値、index 80のExcel黄色セル、index 83のExcel回帰係数再計算。

## 方針

- OpenRouterは使わず、元ファイルまたはprocessed表から再計算する。
- 提出候補へ採用するのは、根拠ファイルと計算手順が明確なものだけにする。
- EDA054の提出候補をベースに、今回の3件だけを上書きする。

## 結果

- EDA054時点の `わかりません`: {before_unknown}
- EDA055後の `わかりません`: {after_unknown}
- 追加採用: {adopted}

| index | route | 採用回答 | 根拠 |
| --- | --- | --- | --- |
| 33 | docx_chart_xml_value_extraction | {results[0].candidate_answer} | `基礎分析.docx` 内の `word/charts/chart2.xml` から1本目の系列を抽出し、x=3の値を取得。 |
| 80 | xlsx_yellow_cell_semantic_extraction | {results[1].candidate_answer} | `train.xlsx.structure.json` の黄色セル `E1409` と、前方補完したSheet1集計表から条件と個数を復元。 |
| 83 | xlsx_regression_formula_recompute | {results[2].candidate_answer} | `train.xlsx.sheets/Sheet1.csv` の回帰係数をindex=1770の行に適用して再計算。 |

凡例: `index` はtest質問ID、`route` は今回の処理名、`採用回答` は提出候補に反映した回答、`根拠` は採用判断に使ったファイルと計算内容を表す。

## 出力

- route結果: `EDA/EDA055/tables/eda055_route_results.csv`
- 提出候補CSV: `EDA/EDA055/predictions/eda055_chart_format_formula_predictions.csv`
- 提出候補zip: `EDA/EDA055/predictions/eda055_chart_format_formula_submission.zip`

## 注意

index 80は質問文ではSheet2とあるが、raw xlsxをopenpyxlで確認したところ、シートは `Sheet1`, `Sheet2`, `train` の3枚で、黄色セルは `Sheet1!E1409` の1件だけだった。
そのため、提出候補では実ファイル上の黄色セルを優先して `Sheet1!E1409` 由来の条件と個数を採用する。
"""
    (OUT_DIR / "eda055_report.md").write_text(report, encoding="utf-8")
    manifest = {
        "eda": "EDA055",
        "before_unknown": before_unknown,
        "after_unknown": after_unknown,
        "adopted_count": adopted,
        "submission_zip": "EDA/EDA055/predictions/eda055_chart_format_formula_submission.zip",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
