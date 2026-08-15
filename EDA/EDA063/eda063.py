from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
API_KEY_PATH = ROOT / ".apikey"
QUESTIONS_CSV = ROOT / "data" / "processed" / "share" / "share" / "質問回答" / "questions_test_expanded.csv"
EDA_DIR = ROOT / "EDA" / "EDA063"
TABLE_DIR = EDA_DIR / "tables"
OUTPUT_CSV = TABLE_DIR / "test_question_classification.csv"
ATTEMPT_CSV = TABLE_DIR / "openrouter_classification_attempts.csv"
REPORT_MD = EDA_DIR / "eda063_report.md"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-20b:free"

PRIMARY_ROUTES = {
    "document_qa": "文書本文から事実や記述を探す",
    "format_extraction": "太字・下線・色・コメント・ハイライトなど書式情報を抽出する",
    "table_lookup": "ExcelやCSVの表・フィルター・Pivot・セルを読む",
    "calculation": "数値を集計、比較、割合、差分、閾値最適化する",
    "code_execution": "コードやNotebookを読み、実行または再計算して答える",
    "diff_comparison": "旧版・新版、複数時点、複数資料の差分を比較する",
    "cross_project_aggregation": "複数案件や社内管理台帳を横断して集計する",
    "image_ocr": "画像、グラフ、図、座席表など視覚情報を読む",
    "schedule_query": "スケジュール、WBS、マイルストーン、タスク期間を調べる",
    "contract_query": "契約期間、契約金額、支払、精算、承認条件を調べる",
    "mixed": "上記の複数routeが同程度に必要",
    "unknown": "質問だけでは分類できない",
}


def read_api_key() -> str:
    """プロジェクト直下の.apikeyからキーを読み、成果物には保存しない。"""
    for line in API_KEY_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("openrouter") and "=" in line:
            return line.split("=", 1)[1].strip().strip("\"'")
    raise ValueError(".apikeyにopenrouterキーがありません。")


def compact(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def prompt_for(batch: list[dict[str, Any]]) -> str:
    route_text = "\n".join(f"- {key}: {value}" for key, value in PRIMARY_ROUTES.items())
    return f"""あなたはRAGシステムの質問ルーターです。回答そのものは作らず、質問ごとに後続処理を設計してください。

利用可能なprimary_route:
{route_text}

判定規則:
- primary_routeは最も重要な1つを選ぶ。複数処理が不可欠な場合だけmixedを選ぶ。
- required_file_typesは必要そうな拡張子を小文字で配列にする。例: [\"xlsx\", \"csv\"]。
- requires_calculationは四則演算、集計、割合、差分、ランキング、閾値探索が必要ならtrue。
- requires_code_executionはコードやNotebookの実行、再計算、係数適用、データ再処理が必要ならtrue。
- requires_llm_answerは文書の意味理解、曖昧な抽出、最終回答の文章化が必要ならtrue。単純な表計算だけならfalseでもよい。
- confidenceは0から1の数値にする。
- reasonは分類根拠を日本語で短く書く。
- 入力のindexを必ず維持し、全入力について1件ずつ返す。

JSON配列だけを返してください。Markdownのコードフェンスや説明文は付けないでください。
各要素の形式:
{{"index":0,"primary_route":"calculation","sub_route":"metric_aggregation","required_file_types":["xlsx"],"requires_calculation":true,"requires_code_execution":false,"requires_llm_answer":true,"confidence":0.9,"reason":"..."}}

入力質問:
{json.dumps(batch, ensure_ascii=False)}
"""


def call_openrouter(api_key: str, batch: list[dict[str, Any]], timeout_sec: int) -> tuple[int, str, str]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "質問の分類だけを行い、指定されたJSON配列を返してください。"},
            {"role": "user", "content": prompt_for(batch)},
        ],
        "temperature": 0,
        "max_tokens": 12000,
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8")
            return response.status, body, ""
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return error.code, body, f"HTTPError: {error.reason}"
    except Exception as error:  # ネットワーク失敗も分類ログに残す
        return 0, "", f"{type(error).__name__}: {error}"


def parse_json_array(content: str) -> list[dict[str, Any]]:
    """LLMが付けた説明やコードフェンスを除き、JSON配列を取り出す。"""
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("JSON配列が見つかりません")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("JSON配列ではありません")
    return [item for item in parsed if isinstance(item, dict)]


def validate_item(item: dict[str, Any], expected_index: int) -> dict[str, Any]:
    route = str(item.get("primary_route", "unknown"))
    if route not in PRIMARY_ROUTES:
        route = "unknown"
    file_types = item.get("required_file_types", [])
    if not isinstance(file_types, list):
        file_types = []
    confidence = item.get("confidence", 0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "index": expected_index,
        "primary_route": route,
        "sub_route": compact(item.get("sub_route", "")),
        "required_file_types": json.dumps([str(value).lower() for value in file_types], ensure_ascii=False),
        "requires_calculation": bool(item.get("requires_calculation", False)),
        "requires_code_execution": bool(item.get("requires_code_execution", False)),
        "requires_llm_answer": bool(item.get("requires_llm_answer", True)),
        "confidence": confidence,
        "reason": compact(item.get("reason", "")),
    }


def classify_batch(
    start: int,
    batch: list[dict[str, Any]],
    api_key: str,
    args: argparse.Namespace,
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    """1バッチをAPIへ送り、分類結果と試行ログを返す。"""
    classifications: dict[int, dict[str, Any]] = {}
    attempts: list[dict[str, Any]] = []
    batch_indices = [item["index"] for item in batch]
    for attempt in range(1, args.max_retries + 2):
        status, body, error = call_openrouter(api_key, batch, args.timeout_sec)
        content = ""
        try:
            if status == 200:
                response_json = json.loads(body)
                content = response_json["choices"][0]["message"].get("content") or ""
                parsed = parse_json_array(content)
                by_index = {int(item["index"]): item for item in parsed if "index" in item}
                missing = [index for index in batch_indices if index not in by_index]
                if missing:
                    raise ValueError(f"分類結果にindexがありません: {missing}")
                for index in batch_indices:
                    classifications[index] = validate_item(by_index[index], index)
                error = ""
            else:
                error = error or f"HTTP {status}"
        except Exception as parse_error:
            error = f"{type(parse_error).__name__}: {parse_error}"
        attempts.append(
            {
                "batch_start": start,
                "batch_indices": ",".join(map(str, batch_indices)),
                "attempt": attempt,
                "model": MODEL,
                "http_status": status,
                "success": not error,
                "error": error,
                "response_chars": len(body),
                "content_chars": len(content),
            }
        )
        if not error:
            break
        if attempt <= args.max_retries:
            time.sleep(args.retry_wait_sec * attempt)
    return classifications, attempts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--retry-wait-sec", type=float, default=4)
    args = parser.parse_args()

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    questions = pd.read_csv(QUESTIONS_CSV, encoding="utf-8-sig")
    api_key = read_api_key()
    batches: list[tuple[int, list[dict[str, Any]]]] = []
    for start in range(0, len(questions), args.batch_size):
        batch_df = questions.iloc[start : start + args.batch_size]
        batch = [{"index": int(row["index"]), "question": str(row["question"])} for _, row in batch_df.iterrows()]
        batches.append((start, batch))

    classifications: dict[int, dict[str, Any]] = {}
    attempts: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(5, len(batches))) as executor:
        futures = [executor.submit(classify_batch, start, batch, api_key, args) for start, batch in batches]
        for future in futures:
            batch_classifications, batch_attempts = future.result()
            classifications.update(batch_classifications)
            attempts.extend(batch_attempts)
    attempts.sort(key=lambda row: (int(row["batch_start"]), int(row["attempt"])))

    output_rows = []
    for _, question in questions.sort_values("index").iterrows():
        index = int(question["index"])
        result = classifications.get(index, validate_item({}, index))
        output_rows.append({"index": index, "question": question["question"], **result, "classification_status": "classified" if index in classifications else "api_error"})
    output = pd.DataFrame(output_rows)
    output.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame(attempts).to_csv(ATTEMPT_CSV, index=False, encoding="utf-8-sig")

    route_summary = output["primary_route"].value_counts().rename_axis("primary_route").reset_index(name="count")
    route_definition = pd.DataFrame(
        [{"primary_route": route, "処理内容": description} for route, description in PRIMARY_ROUTES.items()]
    )
    question_classification = output.copy()
    question_classification["処理内容"] = question_classification["primary_route"].map(PRIMARY_ROUTES).fillna("")
    question_classification = question_classification[
        [
            "index",
            "question",
            "primary_route",
            "sub_route",
            "処理内容",
            "required_file_types",
            "requires_calculation",
            "requires_code_execution",
            "requires_llm_answer",
            "confidence",
            "classification_status",
        ]
    ]
    question_classification["question"] = question_classification["question"].map(lambda value: compact(value).replace("|", "\\|"))
    question_classification["処理内容"] = question_classification["処理内容"].map(lambda value: compact(value).replace("|", "\\|"))
    error_count = int((output["classification_status"] != "classified").sum())
    lines = [
        "# EDA063 LLM質問分類",
        "",
        "## 目的",
        "",
        "EDA061の略語展開済みtest質問100件をGPT-OSS-20Bへ渡し、後続routeに必要な処理をJSON形式で分類した。回答本文や共有ドライブ本文はLLMへ送っていない。",
        "",
        "## 出力",
        "",
        f"- 分類CSV: `{OUTPUT_CSV.relative_to(ROOT)}`",
        f"- API試行ログ: `{ATTEMPT_CSV.relative_to(ROOT)}`",
        "",
        "凡例: `primary_route` は主処理route、`sub_route` は細分類、`required_file_types` は必要ファイル形式、`requires_calculation` は計算要否、`requires_code_execution` はコード実行要否、`requires_llm_answer` は最終回答のLLM整形要否、`confidence` はLLM自己申告の確信度、`classification_status` は分類成功/失敗を表す。",
        "",
        "## 結果",
        "",
        f"- 質問数: {len(output)}",
        f"- 分類成功: {len(output) - error_count}",
        f"- APIまたはJSON失敗: {error_count}",
        f"- API試行数: {len(attempts)}",
        "",
        route_summary.to_markdown(index=False),
        "",
        "凡例: `primary_route` ごとの質問件数を表す。分類結果は後続routeの候補であり、実行前に必要ファイルの存在確認を行う。",
        "",
        "## primary_routeの処理内容",
        "",
        route_definition.to_markdown(index=False),
        "",
        "凡例: `primary_route` はLLMが選んだ主route、`処理内容` はそのrouteで実施する処理の概要を表す。",
        "",
        "## 質問ごとの分類一覧",
        "",
        question_classification.to_markdown(index=False),
        "",
        "凡例: 各行は1質問の分類結果を表す。`required_file_types` は必要ファイル形式、`requires_calculation` と `requires_code_execution` は計算・コード実行の要否、`requires_llm_answer` は最終回答のLLM整形要否、`confidence` はLLM自己申告の確信度である。",
        "",
        "## 注意",
        "",
        f"- 使用モデル: `{MODEL}`",
        "- APIキーは `.apikey` から読み込むだけで、CSV・ログ・manifestには保存していない。",
        "- LLMの分類誤りに備え、`confidence` が低い質問や `mixed`/`unknown` は後段で再確認する。",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "eda": "EDA063",
        "input_csv": str(QUESTIONS_CSV.relative_to(ROOT)),
        "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
        "attempt_csv": str(ATTEMPT_CSV.relative_to(ROOT)),
        "report": str(REPORT_MD.relative_to(ROOT)),
        "model": MODEL,
        "question_count": int(len(output)),
        "classified_count": int(len(output) - error_count),
        "api_error_count": error_count,
        "api_key": ".apikey (not stored)",
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
