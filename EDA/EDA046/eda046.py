from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
RAW_DIR = OUT_DIR / "raw_responses"
PRED_DIR = OUT_DIR / "predictions"

PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
INPUT_RESULT = BASE_DIR / "EDA" / "EDA044" / "tables" / "test_format_table_image_result.csv"
INPUT_GAP = BASE_DIR / "EDA" / "EDA045" / "tables" / "remaining_route_gap_inventory.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda046_all_remaining_routes_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = ["openai/gpt-oss-20b:free"]


PROJECT_ALIASES: dict[str, list[str]] = {
    "白峰": ["白峰", "白峰信用", "SHR"],
    "青潮": ["青潮", "青潮モビリティ", "AOSHIO", "AOS"],
    "東都": ["東都", "東都人材", "TOTO", "TTP"],
    "みなみ野": ["みなみ野", "蒼樹会", "MINAMINO"],
    "青葉与信": ["青葉与信", "AYM"],
    "青葉バイオ": ["青葉バイオ", "AOBM"],
    "青嶺": ["青嶺", "青嶺不動産", "AOMINE"],
    "かえで": ["かえで", "恒一会", "KAEDE"],
    "社内管理": ["社内管理", "共有ドライブ"],
}


ROUTE_KEYWORDS: dict[str, list[str]] = {
    "meeting_action_status_lookup": ["会議録", "報告資料", "進捗サマリ", "M04", "A10", "CP2", "チェックポイント", "コメント", "タスクID", "Action"],
    "chart_value_extraction": ["基礎分析", "グラフ", "グラフ2", "chart", "series", "青色", "折れ線", "x=3", "Sheet"],
    "cross_project_contract_aggregation": ["社内管理", "決裁基準", "APR", "APR-M3", "契約金額", "税込", "着手金", "想定工数", "担当タスク数"],
    "contract_alias_contact_lookup": ["社内用語集", "契約書", "CT", "ES", "主担当者", "内線", "EXT", "着手金", "体制"],
    "proposal_operation_clause_lookup": ["提案書", "契約書", "今後の運用", "別契約", "PL案", "モデル構築", "第", "週"],
    "seating_chart_spatial_ocr": ["座席表", "FM", "EXT", "佐藤", "井上", "右側", "向かい", "席", "image_path"],
    "model_formula_recompute": ["train", "回帰係数", "係数", "予測値", "F1", "閾値", "id=0", "index=1770", "analysis"],
    "spreadsheet_format_semantic_context": ["train.xlsx", "黄色", "ハイライト", "fill_color", "FFFF", "Sheet2", "相関係数", "条件", "集計"],
    "structured_diff_semantic_filter": ["old", "最新版", "r1", "r2", "変更", "差分", "モデル比較", "スコア", "未着手", "完了", "設定"],
}


def normalize_text(value: object) -> str:
    """検索と回答整形のために文字種と空白をそろえる。"""
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compact_answer(value: object) -> str:
    """提出に不要なタグや長い空白を落として短い回答に整える。"""
    text = normalize_text(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"\s*\n\s*", "、", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip(" 、")


def relative(path: Path | str | None) -> str:
    if path is None:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_openrouter_key() -> str:
    """プロジェクトローカルの.apikeyからOpenRouterキーを読む。"""
    key_file = BASE_DIR / ".apikey"
    if key_file.exists():
        for raw in key_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip().lower() in {"openrouter", "openrouter_api_key"}:
                return value.strip().strip('"').strip("'")
    return os.environ.get("OPENROUTER_API_KEY", "")


def question_project_terms(question: str) -> list[str]:
    """質問文から案件名や略称を取り出し、パス検索用の候補を返す。"""
    q = normalize_text(question)
    found: list[str] = []
    for aliases in PROJECT_ALIASES.values():
        if any(alias in q for alias in aliases):
            found.extend(aliases)
    if "社内管理" in q or "IM" in q:
        found.extend(PROJECT_ALIASES["社内管理"])
    return list(dict.fromkeys(found))


def question_terms(question: str, route: str) -> list[str]:
    """質問語とroute固有語を合わせて、根拠抽出に使う語を作る。"""
    q = normalize_text(question)
    tokens = re.findall(r"[A-Za-z0-9_-]+|[一-龥ぁ-んァ-ンー]+", q)
    keep = [t for t in tokens if len(t) >= 2]
    terms = keep + ROUTE_KEYWORDS.get(route, []) + question_project_terms(q)
    return list(dict.fromkeys(terms))


def allowed_suffix(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".csv", ".json", ".txt"}


def looks_binary_or_base64(line: str) -> bool:
    if len(line) > 1200:
        dense = re.sub(r"[A-Za-z0-9+/=]", "", line)
        return len(dense) < len(line) * 0.05
    return False


def path_score(path: Path, terms: list[str], route: str, project_terms: list[str]) -> int:
    """ファイルパスだけで関連度を粗く評価する。"""
    hay = normalize_text(str(path)).lower().replace("\\", "/")
    score = 0
    for term in terms:
        t = normalize_text(term).lower()
        if t and t in hay:
            score += 4
    for term in project_terms:
        t = normalize_text(term).lower()
        if t and t in hay:
            score += 10
    if "社内管理" in hay:
        score += 3
    if route == "cross_project_contract_aggregation" and any(x in hay for x in ["契約", "決裁", "スケジュール", "計画"]):
        score += 8
    if route == "seating_chart_spatial_ocr" and any(x in hay for x in ["座席表", "社内用語集"]):
        score += 20
    return score


def select_candidate_files(question: str, route: str, max_files: int) -> list[Path]:
    """processed配下からrouteに関係しそうなMarkdown/CSV/JSONを選ぶ。"""
    terms = question_terms(question, route)
    project_terms = question_project_terms(question)
    all_project = route == "cross_project_contract_aggregation" or "社内管理" in question
    scored: list[tuple[int, Path]] = []

    for path in PROCESSED_ROOT.rglob("*"):
        if not path.is_file() or not allowed_suffix(path):
            continue
        path_text = normalize_text(str(path))
        if not all_project and project_terms and not any(term in path_text for term in project_terms + ["社内管理"]):
            continue
        score = path_score(path, terms, route, project_terms)
        if score > 0:
            scored.append((score, path))

    scored.sort(key=lambda x: (-x[0], len(str(x[1]))))
    return [p for _, p in scored[:max_files]]


def line_matches(line: str, terms: list[str]) -> int:
    text = normalize_text(line).lower()
    score = 0
    for term in terms:
        t = normalize_text(term).lower()
        if t and t in text:
            score += 1
    return score


def extract_text_snippets(path: Path, terms: list[str], route: str, max_chars: int) -> str:
    """ファイルから検索語の周辺行だけを抜き出し、LLMに渡す文脈を小さくする。"""
    try:
        raw_lines = read_text(path).splitlines()
    except Exception:
        return ""

    if not raw_lines:
        return ""

    matched: set[int] = set()
    for i, line in enumerate(raw_lines):
        if looks_binary_or_base64(line):
            continue
        score = line_matches(line, terms)
        if score:
            window = 2 if route in {"meeting_action_status_lookup", "proposal_operation_clause_lookup"} else 1
            for j in range(max(0, i - window), min(len(raw_lines), i + window + 1)):
                matched.add(j)

    if not matched:
        # 表やスケジュールではヘッダだけでも列名の意味が効くため、短く先頭を入れる。
        matched.update(range(min(8, len(raw_lines))))

    pieces: list[str] = []
    for i in sorted(matched):
        line = raw_lines[i].strip()
        if not line or looks_binary_or_base64(line):
            continue
        pieces.append(f"L{i + 1}: {line[:600]}")
        if sum(len(x) for x in pieces) > max_chars:
            break
    return "\n".join(pieces)[:max_chars]


def build_context(index: int, question: str, route: str, max_files: int, max_chars: int) -> tuple[str, list[str]]:
    """質問ごとにroute別の圧縮文脈を組み立てる。"""
    terms = question_terms(question, route)
    paths = select_candidate_files(question, route, max_files)
    sections: list[str] = []
    used: list[str] = []

    for path in paths:
        snippet = extract_text_snippets(path, terms, route, max_chars=max(1000, max_chars // max(1, max_files)))
        if not snippet:
            continue
        used.append(relative(path))
        sections.append(f"## source: {relative(path)}\n{snippet}")
        if sum(len(s) for s in sections) > max_chars:
            break

    if route == "seating_chart_spatial_ocr":
        sections.append(
            "## route note\n"
            "このrouteは座席表画像の空間関係を扱う。既存前処理で画像文字起こしがない場合、"
            "Markdown/structure JSON上のimage_pathと社内用語集だけでは回答不能になる可能性がある。"
        )

    return "\n\n".join(sections)[:max_chars], used


def acceptable_answer(answer: object) -> bool:
    """提出に採用してよい回答かを保守的に判定する。"""
    text = compact_answer(answer)
    if not text:
        return False
    bad = [
        "わかりません",
        "不明",
        "情報不足",
        "情報が不足",
        "確認できません",
        "見つかりません",
        "判断できません",
        "特定できません",
        "該当なし",
        "ありません",
        "存在しません",
        "回答不能",
        "不十分",
    ]
    return not any(x in text for x in bad)


def parse_json_answer(content: str) -> str:
    """OpenRouterの出力からanswerだけを取り出す。"""
    text = normalize_text(content).strip()
    if not text:
        return ""
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return compact_answer(obj.get("answer", ""))
    except Exception:
        pass
    return compact_answer(text)


def build_prompt(question: str, context: str, route: str) -> str:
    return f"""あなたは社内共有ドライブを読むRAG回答エンジンです。
根拠コンテキストだけを使い、質問に対する最終回答を短く返してください。

必ずJSONのみで返してください:
{{"answer":"短い回答"}}

ルール:
- 根拠にない推測はしない。
- 計算が必要なら、根拠内の数値を使って計算する。
- ファイル名、ページ番号、セル、ID、金額、単位は省略しない。
- HTMLタグやMarkdown装飾は出さない。
- answerは原則320文字以内。ただし「そのまま抽出」系は必要な範囲で原文を保つ。
- 「わかりません」「不明」「確認できません」などの逃げ回答は禁止。

route: {route}

質問:
{question}

根拠コンテキスト:
{context}
"""


def call_openrouter(model: str, api_key: str, question: str, context: str, route: str, max_tokens: int, timeout: int) -> tuple[str, dict[str, Any]]:
    """圧縮文脈をOpenRouter 20Bへ渡して回答候補を得る。"""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "あなたは日本語のRAG回答エンジンです。JSONだけを返します。"},
            {"role": "user", "content": build_prompt(question, context, route)},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning": {"enabled": True},
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.local/agentic-rag-eda046",
            "X-Title": "SIGNATE Agentic RAG EDA046",
        },
        method="POST",
    )
    meta: dict[str, Any] = {
        "model": model,
        "status": "",
        "finish_reason": "",
        "content_length": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "raw": None,
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        meta["raw"] = payload
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {}) or {}
        usage = payload.get("usage", {}) or {}
        details = usage.get("completion_tokens_details", {}) or {}
        content = normalize_text(message.get("content", ""))
        meta["status"] = "http_200"
        meta["finish_reason"] = choice.get("finish_reason", "")
        meta["content_length"] = len(content)
        meta["prompt_tokens"] = int(usage.get("prompt_tokens", 0) or 0)
        meta["completion_tokens"] = int(usage.get("completion_tokens", 0) or 0)
        meta["reasoning_tokens"] = int(details.get("reasoning_tokens", 0) or 0)
        return parse_json_answer(content), meta
    except urllib.error.HTTPError as exc:
        meta["status"] = f"http_{exc.code}"
        meta["raw"] = {"error_body": exc.read().decode("utf-8", errors="replace")[:2000]}
        return "", meta
    except Exception as exc:
        meta["status"] = f"error:{type(exc).__name__}"
        meta["raw"] = {"error": str(exc)}
        return "", meta


def write_raw_response(index: int, meta: dict[str, Any]) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"index_{index:03d}.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return relative(path)


def write_submission(result_df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in result_df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda046"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, attempt_df: pd.DataFrame, args: argparse.Namespace) -> None:
    route_summary = attempt_df.groupby(["new_route_candidate", "status"], as_index=False).agg(
        count=("index", "count"),
        adopted=("adopted_by_eda046", "sum"),
    )
    view_cols = [
        "index",
        "new_route_candidate",
        "question",
        "answer_after_eda046",
        "adopted_by_eda046",
        "status",
        "finish_reason",
        "used_paths",
    ]
    view = attempt_df[view_cols].copy()
    report = f"""# EDA046: remaining 20 route 一括試行

## 背景と目的

EDA045で、EDA044提出時点でも `わかりません` のまま残った20件を9種類のroute候補に分類した。
EDA046では、その20件を一括で処理し、routeごとに関連ファイルを圧縮抽出してOpenRouter 20Bへ渡すことで、追加採用できる回答候補を作成した。

## 実施内容

- 入力: `{relative(INPUT_RESULT)}`
- route候補: `{relative(INPUT_GAP)}`
- 対象件数: {len(attempt_df)}
- モデル候補: `{", ".join(args.models)}`
- max_tokens: {args.max_tokens}
- context最大文字数: {args.max_context_chars}
- EDA044時点の非 `わかりません`: {int((result_df["answer_before_eda046"] != UNKNOWN).sum())}
- EDA046で追加採用: {int(result_df["improved_by_eda046"].sum())}
- EDA046後の非 `わかりません`: {int((result_df["answer_after_eda046"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## route別集計

凡例: `new_route_candidate` はEDA045で提案した新route、`status` はAPIまたは文脈生成の状態、`count` は件数、`adopted` は回答として採用した件数を表す。

{route_summary.to_markdown(index=False)}

## 対象20件ログ

凡例: `answer_after_eda046` はEDA046後の回答、`adopted_by_eda046` はEDA046で新規採用したか、`used_paths` は根拠抽出に使った主なファイルを表す。

{view.to_markdown(index=False)}

## メモ

- 画像の空間関係を読む `seating_chart_spatial_ocr` とグラフ画像値を読む `chart_value_extraction` は、既存のMarkdown/structure JSONに十分なOCR結果がない場合、text-onlyの20Bでは限界が残る。
- `content` 空や429が出た場合はraw responseを `raw_responses` に保存している。
"""
    (OUT_DIR / "eda046_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--max-context-chars", type=int, default=12000)
    parser.add_argument("--max-files", type=int, default=12)
    parser.add_argument("--sleep-sec", type=float, default=3.0)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    parser.add_argument("--no-api", action="store_true")
    parser.add_argument("--reuse-attempt-log", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    api_key = read_openrouter_key()
    if not api_key and not args.no_api:
        raise RuntimeError("OpenRouter API key was not found in .apikey or environment")

    base_df = pd.read_csv(INPUT_RESULT)
    if args.reuse_attempt_log:
        log_path = TABLE_DIR / "test_all_remaining_routes_attempt_log.csv"
        if not log_path.exists():
            raise FileNotFoundError(log_path)
        attempt_df = pd.read_csv(log_path)
        answer_map = {int(row["index"]): compact_answer(row.get("answer_after_eda044", UNKNOWN)) for _, row in base_df.iterrows()}
        for i, row in attempt_df.iterrows():
            index = int(row["index"])
            candidate = compact_answer(row.get("llm_answer", ""))
            adopted = acceptable_answer(candidate)
            if adopted:
                answer_map[index] = candidate
            attempt_df.loc[i, "adopted_by_eda046"] = adopted
            attempt_df.loc[i, "answer_after_eda046"] = answer_map.get(index, UNKNOWN)

        output_rows: list[dict[str, Any]] = []
        for _, row in base_df.sort_values("index").iterrows():
            before = compact_answer(row.get("answer_after_eda044", UNKNOWN)) or UNKNOWN
            after = answer_map.get(int(row["index"]), before)
            out = row.to_dict()
            out["answer_before_eda046"] = before
            out["answer_after_eda046"] = after
            out["improved_by_eda046"] = before == UNKNOWN and after != UNKNOWN
            output_rows.append(out)

        result_df = pd.DataFrame(output_rows)
        result_df.to_csv(TABLE_DIR / "test_all_remaining_routes_result.csv", index=False, encoding="utf-8-sig")
        attempt_df.to_csv(TABLE_DIR / "test_all_remaining_routes_attempt_log.csv", index=False, encoding="utf-8-sig")
        write_submission(result_df)
        write_report(result_df, attempt_df, args)
        manifest = {
            "eda": "EDA046",
            "input_result": relative(INPUT_RESULT),
            "input_gap": relative(INPUT_GAP),
            "target_count": int(len(attempt_df)),
            "before_non_unknown_count": int((result_df["answer_before_eda046"] != UNKNOWN).sum()),
            "added_non_unknown_count": int(result_df["improved_by_eda046"].sum()),
            "after_non_unknown_count": int((result_df["answer_after_eda046"] != UNKNOWN).sum()),
            "reuse_attempt_log": True,
            "outputs": [
                relative(TABLE_DIR / "test_all_remaining_routes_result.csv"),
                relative(TABLE_DIR / "test_all_remaining_routes_attempt_log.csv"),
                relative(PREDICTIONS_PATH),
                relative(ZIP_PATH),
                relative(OUT_DIR / "eda046_report.md"),
                relative(RAW_DIR),
            ],
        }
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return

    gap_df = pd.read_csv(INPUT_GAP)
    target_df = gap_df.sort_values("index").copy()
    answer_map = {int(row["index"]): compact_answer(row.get("answer_after_eda044", UNKNOWN)) for _, row in base_df.iterrows()}
    question_map = {int(row["index"]): normalize_text(row.get("question", "")) for _, row in base_df.iterrows()}

    attempt_rows: list[dict[str, Any]] = []
    for _, row in target_df.iterrows():
        index = int(row["index"])
        route = normalize_text(row.get("new_route_candidate", ""))
        question = normalize_text(row.get("question", "")) or question_map.get(index, "")
        context, used_paths = build_context(index, question, route, args.max_files, args.max_context_chars)

        llm_answer = ""
        status = "no_context"
        finish_reason = ""
        raw_path = ""
        adopted = False

        if context and not args.no_api:
            for model in args.models:
                candidate, meta = call_openrouter(model, api_key, question, context, route, args.max_tokens, args.timeout_sec)
                raw_path = write_raw_response(index, meta)
                status = normalize_text(meta.get("status", ""))
                finish_reason = normalize_text(meta.get("finish_reason", ""))
                if acceptable_answer(candidate):
                    llm_answer = candidate
                    adopted = True
                    answer_map[index] = llm_answer
                    break
                time.sleep(args.sleep_sec)
        elif context:
            status = "context_only_no_api"

        attempt_rows.append(
            {
                "index": index,
                "old_route": normalize_text(row.get("old_route", "")),
                "old_subtype": normalize_text(row.get("old_subtype", "")),
                "new_route_candidate": route,
                "question": question,
                "llm_answer": llm_answer,
                "answer_after_eda046": answer_map.get(index, UNKNOWN),
                "adopted_by_eda046": adopted,
                "status": status,
                "finish_reason": finish_reason,
                "used_paths": " | ".join(used_paths[:10]),
                "context_chars": len(context),
                "context_preview": context[:5000],
                "raw_response_path": raw_path,
            }
        )
        time.sleep(args.sleep_sec)

    output_rows: list[dict[str, Any]] = []
    for _, row in base_df.sort_values("index").iterrows():
        before = compact_answer(row.get("answer_after_eda044", UNKNOWN)) or UNKNOWN
        after = answer_map.get(int(row["index"]), before)
        out = row.to_dict()
        out["answer_before_eda046"] = before
        out["answer_after_eda046"] = after
        out["improved_by_eda046"] = before == UNKNOWN and after != UNKNOWN
        output_rows.append(out)

    result_df = pd.DataFrame(output_rows)
    attempt_df = pd.DataFrame(attempt_rows)
    result_df.to_csv(TABLE_DIR / "test_all_remaining_routes_result.csv", index=False, encoding="utf-8-sig")
    attempt_df.to_csv(TABLE_DIR / "test_all_remaining_routes_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, attempt_df, args)

    manifest = {
        "eda": "EDA046",
        "input_result": relative(INPUT_RESULT),
        "input_gap": relative(INPUT_GAP),
        "target_count": int(len(attempt_df)),
        "before_non_unknown_count": int((result_df["answer_before_eda046"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved_by_eda046"].sum()),
        "after_non_unknown_count": int((result_df["answer_after_eda046"] != UNKNOWN).sum()),
        "outputs": [
            relative(TABLE_DIR / "test_all_remaining_routes_result.csv"),
            relative(TABLE_DIR / "test_all_remaining_routes_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda046_report.md"),
            relative(RAW_DIR),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
