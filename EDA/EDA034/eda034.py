from __future__ import annotations

import csv
import json
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"

QUESTIONS_VALID_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_valid.csv"
QUESTIONS_TEST_PATH = BASE_DIR / "data" / "raw" / "share" / "share" / "質問回答" / "questions_test.csv"
ROUTES_PATH = BASE_DIR / "EDA" / "EDA011" / "tables" / "question_routes.csv"
EDA024_VALID_PATH = BASE_DIR / "EDA" / "EDA024" / "tables" / "valid_llm_answer_log.csv"
EDA033_VALID_PATH = BASE_DIR / "EDA" / "EDA033" / "tables" / "llm_structured_candidate_answer_log.csv"
EDA027_TEST_PATH = BASE_DIR / "EDA" / "EDA027" / "tables" / "test_unknown_allowed_answer_log.csv"
EDA021_TEST_PRED_PATH = BASE_DIR / "EDA" / "EDA021" / "predictions" / "predictions.csv"

PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda034_structured_safe_submission.zip"

UNKNOWN = "わかりません"


def normalize_text(value: object) -> str:
    """比較・保存の前にUnicode表記とHTMLタグをそろえる。"""
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("`", "")
    return text


def compact_answer(value: object) -> str:
    """提出用に改行や余分な空白を1行へまとめる。"""
    text = normalize_text(value)
    text = re.sub(r"\s*\n\s*", "、", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("、、", "、").strip(" 、")
    return text.strip()


def compact_for_match(value: object) -> str:
    """valid評価用に表記差を少し吸収する。"""
    text = compact_answer(value)
    text = text.replace("¥", "").replace("円", "").replace("。", "")
    return re.sub(r"\s+", "", text)


def answer_matches(predicted: str, gold: str) -> bool:
    """厳密一致だけでなく、単位や列挙順の軽い差を含めて類似判定する。"""
    p = compact_for_match(predicted)
    g = compact_for_match(gold)
    if not p or not g:
        return False
    if p == g or p in g or g in p:
        return True

    p_nums = {x.replace(",", "") for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", p)}
    g_nums = {x.replace(",", "") for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", g)}
    if p_nums and p_nums == g_nums:
        return True

    gold_parts = [part for part in re.split(r"[、,，/・\s]+", g) if part]
    return len(gold_parts) >= 2 and all(part in p for part in gold_parts)


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_unknown(value: object) -> bool:
    text = compact_answer(value)
    return not text or text == UNKNOWN or "わかりません" in text


def is_bad_submission_answer(value: object) -> bool:
    """提出リスクが高い長文・タグ混入・根拠丸写しを除外する。"""
    text = compact_answer(value)
    if is_unknown(text):
        return True
    if len(text) > 180:
        return True
    bad_markers = [
        "color=",
        "style=",
        "</span>",
        "open actions",
        "prior_state",
        "Report facts JSON",
        "```",
        "| ---",
    ]
    return any(marker.lower() in text.lower() for marker in bad_markers)


def load_routes(split: str) -> dict[int, str]:
    if not ROUTES_PATH.exists():
        return {}
    df = pd.read_csv(ROUTES_PATH)
    return {int(row["index"]): str(row["route"]) for _, row in df[df["split"].eq(split)].iterrows()}


def load_eda021_predictions() -> dict[int, str]:
    """EDA021の提出CSVを、フォールバック候補として読み込む。"""
    if not EDA021_TEST_PRED_PATH.exists():
        return {}
    rows: dict[int, str] = {}
    with EDA021_TEST_PRED_PATH.open("r", encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                rows[int(row[0])] = compact_answer(row[1])
    return rows


def allow_local_fallback(route: str, question: str, answer: str) -> bool:
    """BM25抽出回答は誤答リスクが高いので、短く明確な候補だけ採用する。"""
    if is_bad_submission_answer(answer):
        return False
    if route not in {"code_reading", "table_calculation", "format_extraction", "image_ocr"}:
        return False
    if len(answer) > 80:
        return False
    # 日本語の長い文や会社名は根拠文の冒頭を拾っている可能性が高い。
    # ローカルフォールバックでは、ID、列名、数値、単位だけで構成される短い候補に限定する。
    safe_pattern = r"^[A-Za-z0-9_.,:+\-/%\s、，()（）=年月日時分秒円ドル歳週第個件]+$"
    if not re.fullmatch(safe_pattern, answer):
        return False
    question_markers = ["いくつ", "何", "すべて", "抽出", "計算", "小数", "答えて"]
    return any(marker in question for marker in question_markers)


def build_valid_log() -> pd.DataFrame:
    """EDA024の全valid回答に、EDA033の構造化対策結果を上書きして評価する。"""
    valid_questions = pd.read_csv(QUESTIONS_VALID_PATH)
    routes = load_routes("valid")
    base = pd.read_csv(EDA024_VALID_PATH)
    improved = pd.read_csv(EDA033_VALID_PATH) if EDA033_VALID_PATH.exists() else pd.DataFrame()
    improved_by_index = {int(row["index"]): row for _, row in improved.iterrows()}

    rows: list[dict[str, Any]] = []
    for _, q in valid_questions.sort_values("index").iterrows():
        index = int(q["index"])
        base_row = base[base["index"].eq(index)].iloc[0]
        if index in improved_by_index:
            improved_row = improved_by_index[index]
            answer = compact_answer(improved_row.get("llm_answer", ""))
            source_stage = "eda033_structured_candidate"
            method = str(improved_row.get("candidate_method", ""))
        else:
            answer = compact_answer(base_row.get("llm_answer", ""))
            source_stage = "eda024_llm_rag"
            method = "previous_llm_rag"

        gold = str(base_row.get("gold_answer", ""))
        rows.append(
            {
                "index": index,
                "route": routes.get(index, ""),
                "question": q["question"],
                "gold_answer": gold,
                "pipeline_answer": answer,
                "answer_match": answer_matches(answer, gold),
                "source_stage": source_stage,
                "method": method,
            }
        )
    return pd.DataFrame(rows)


def select_test_answer(
    index: int,
    question: str,
    route: str,
    eda027_row: pd.Series | None,
    eda021_predictions: dict[int, str],
) -> dict[str, Any]:
    """testでは低信頼の長文回答を避け、20B回答を優先しつつ安全側へ倒す。"""
    if eda027_row is not None:
        answer = compact_answer(eda027_row.get("answer", ""))
        if not is_bad_submission_answer(answer):
            return {
                "answer": answer,
                "source_stage": "eda027_openrouter_20b",
                "confidence": "medium",
                "top1_source_path": eda027_row.get("top1_source_path", ""),
                "notes": "EDA027のunknown許容LLM回答を採用",
            }

    local_answer = compact_answer(eda021_predictions.get(index, ""))
    if allow_local_fallback(route, question, local_answer):
        return {
            "answer": local_answer,
            "source_stage": "eda021_local_bm25_fallback",
            "confidence": "low",
            "top1_source_path": "",
            "notes": "短く明確なBM25抽出候補のみ採用",
        }

    return {
        "answer": UNKNOWN,
        "source_stage": "safe_unknown",
        "confidence": "none",
        "top1_source_path": "" if eda027_row is None else eda027_row.get("top1_source_path", ""),
        "notes": "誤答リスクが高い候補は提出用では不採用",
    }


def build_test_log() -> pd.DataFrame:
    questions = pd.read_csv(QUESTIONS_TEST_PATH)
    routes = load_routes("test")
    eda027 = pd.read_csv(EDA027_TEST_PATH) if EDA027_TEST_PATH.exists() else pd.DataFrame()
    eda027_by_index = {int(row["index"]): row for _, row in eda027.iterrows()}
    eda021_predictions = load_eda021_predictions()

    rows: list[dict[str, Any]] = []
    for _, q in questions.sort_values("index").iterrows():
        index = int(q["index"])
        question = str(q["question"])
        route = routes.get(index, "")
        selected = select_test_answer(index, question, route, eda027_by_index.get(index), eda021_predictions)
        rows.append(
            {
                "index": index,
                "route": route,
                "question": question,
                "answer": selected["answer"],
                "source_stage": selected["source_stage"],
                "confidence": selected["confidence"],
                "top1_source_path": selected["top1_source_path"],
                "notes": selected["notes"],
            }
        )
    return pd.DataFrame(rows)


def write_submission(test_df: pd.DataFrame) -> None:
    """SIGNATE提出形式のpredictions.csvとzipを生成する。"""
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in test_df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer"])])

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "該当データなし"
    return df.to_markdown(index=False)


def write_report(valid_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    valid_summary = (
        valid_df.groupby("route", as_index=False)
        .agg(count=("index", "count"), match_count=("answer_match", "sum"))
        .sort_values(["match_count", "count"], ascending=[False, False])
    )
    test_stage_summary = (
        test_df.groupby(["source_stage", "confidence"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["source_stage", "confidence"])
    )
    test_route_summary = (
        test_df.groupby("route", as_index=False)
        .agg(count=("index", "count"), non_unknown_count=("answer", lambda s: int((s != UNKNOWN).sum())))
        .sort_values(["non_unknown_count", "count"], ascending=[False, False])
    )

    report = f"""# EDA034: valid改善結果をtest提出用パイプラインへ反映

## 背景と目的
EDA032/033では、validで失敗していた25件に対して、構造化データから回答候補を作り、LLMで最終回答に整える方針が有効だった。
EDA034では、その考え方を提出用の実行単位に寄せ、validではEDA024の全体回答にEDA033の改善結果を上書きし、testではEDA027の20B回答を安全側に採用して提出zipを作成した。

金額差の未解決メモ: valid index=3の消費税額は、ローカル再構成では4,384,250円、goldは4,394,250円で、差額10,000円が残っている。今回は提出パイプライン化を優先し、この差は既知課題として扱う。

## 入力
- valid基準回答: `{relative(EDA024_VALID_PATH)}`
- valid構造化改善: `{relative(EDA033_VALID_PATH)}`
- test 20B回答: `{relative(EDA027_TEST_PATH)}`
- test BM25候補: `{relative(EDA021_TEST_PRED_PATH)}`
- route定義: `{relative(ROUTES_PATH)}`

## 出力
- valid統合評価ログ: `{relative(TABLE_DIR / 'valid_pipeline_answer_log.csv')}`
- test回答ログ: `{relative(TABLE_DIR / 'test_pipeline_answer_log.csv')}`
- 提出CSV: `{relative(PREDICTIONS_PATH)}`
- 提出zip: `{relative(ZIP_PATH)}`

## valid結果
- valid件数: {len(valid_df)}
- 類似正解数: {int(valid_df["answer_match"].sum())}
- 類似正解率: {int(valid_df["answer_match"].sum()) / max(len(valid_df), 1):.3f}

凡例: `route` は質問の処理ルート、`count` はvalid質問数、`match_count` はgold類似判定がTrueの件数を表す。

{markdown_table(valid_summary)}

## test提出候補の内訳
凡例: `source_stage` は採用した回答元、`confidence` は提出時の信頼度、`count` はtest質問数を表す。

{markdown_table(test_stage_summary)}

凡例: `route` は質問の処理ルート、`count` はtest質問数、`non_unknown_count` は「わかりません」以外の回答数を表す。

{markdown_table(test_route_summary)}

## 判断
今回は、低信頼の長文BM25回答を提出に混ぜると-1リスクが大きいため、EDA027の20B回答で短く明確なものを優先し、それ以外は「わかりません」とした。
EDA021で見られたHTMLタグ混入、根拠文の長文丸写し、別案件の管理文言混入は提出用では除外している。

次はEDA035として、testの「わかりません」になった質問をroute別に分け、table_calculation、format_extraction、diff_checkの順に構造化処理を増やすのが妥当。
"""
    (OUT_DIR / "eda034_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    valid_df = build_valid_log()
    test_df = build_test_log()

    valid_df.to_csv(TABLE_DIR / "valid_pipeline_answer_log.csv", index=False, encoding="utf-8-sig")
    test_df.to_csv(TABLE_DIR / "test_pipeline_answer_log.csv", index=False, encoding="utf-8-sig")
    write_submission(test_df)
    write_report(valid_df, test_df)

    manifest = {
        "eda": "EDA034",
        "purpose": "Merge valid structured improvements and create a safe test submission candidate.",
        "valid_count": int(len(valid_df)),
        "valid_match_count": int(valid_df["answer_match"].sum()),
        "test_count": int(len(test_df)),
        "test_non_unknown_count": int((test_df["answer"] != UNKNOWN).sum()),
        "outputs": [
            relative(TABLE_DIR / "valid_pipeline_answer_log.csv"),
            relative(TABLE_DIR / "test_pipeline_answer_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda034_report.md"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
