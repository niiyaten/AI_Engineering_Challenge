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
INPUT_RESULT = BASE_DIR / "EDA" / "EDA042" / "tables" / "test_document_retry_result.csv"
INPUT_RETRY = BASE_DIR / "EDA" / "EDA042" / "tables" / "test_document_retry_attempt_log.csv"
INPUT_CONTEXT = BASE_DIR / "EDA" / "EDA041" / "tables" / "test_document_search_route_attempt_log.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda043_compressed_context_retry_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = ["openai/gpt-oss-20b:free"]

STOP_TERMS = {
    "について",
    "ください",
    "答えて",
    "すべて",
    "案件",
    "資料",
    "ファイル",
    "フォルダ",
    "おいて",
    "されて",
    "あります",
    "ですか",
    "もの",
    "こと",
    "教えて",
    "ください",
    "います",
    "ますか",
    "場合",
    "答え",
}


def normalize_text(value: object) -> str:
    """検索語と回答の表記揺れを抑える。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出回答からHTMLやMarkdown記号を除去する。"""
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


def question_terms(question: str) -> list[str]:
    """質問文から文脈圧縮に使う語を取り出す。"""
    q = normalize_text(question)
    terms = re.findall(r"[A-Za-z0-9_./+-]+|[一-龥ぁ-んァ-ンー]{2,}", q)
    selected: list[str] = []
    for term in terms:
        term = term.strip()
        if not term or term in STOP_TERMS or term.isdigit():
            continue
        if len(term) < 2:
            continue
        if term not in selected:
            selected.append(term)
    return selected[:24]


def split_context_blocks(contexts: str) -> list[tuple[str, list[str]]]:
    """EDA041の文脈を、ファイルブロックと行に分解する。"""
    blocks: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    for raw in normalize_text(contexts).splitlines():
        line = raw.strip()
        if line.startswith("# "):
            if current_title or current_lines:
                blocks.append((current_title, current_lines))
            current_title = line[2:].strip()
            current_lines = []
        elif line:
            current_lines.append(line)
    if current_title or current_lines:
        blocks.append((current_title, current_lines))
    return blocks


def noise_line(line: str, terms: list[str]) -> bool:
    """図形座標やsha1など、回答に寄与しにくい行を落とす。"""
    low = line.lower()
    noisy = [
        "source_sha1",
        "width_pt",
        "height_pt",
        "left_pt",
        "top_pt",
        "shape_id",
        "shape_index",
        "font_name",
        "font_size",
        "raw_relative_path",
        "processed_",
        "image_path",
        "content_type",
    ]
    if any(key in low for key in noisy) and not any(term.lower() in low for term in terms):
        return True
    return False


def score_line(line: str, question: str, terms: list[str]) -> int:
    """質問語、数値、IDを含む行を優先する。"""
    clean = normalize_text(line)
    low = clean.lower()
    score = 0
    for term in terms:
        if term.lower() in low:
            score += 8
    if re.search(r"\b(?:MS|T|A|M|CP)\d+\b", clean):
        score += 5
    if re.search(r"\d", clean):
        score += 3
    if "ページ" in question or "何ページ" in question:
        if re.search(r"Slide\s+\d+|Page\s*\d+|ページ", clean, flags=re.IGNORECASE):
            score += 10
    if "内線" in question or "EXT" in question:
        if re.search(r"EXT|内線|\d{3,4}", clean, flags=re.IGNORECASE):
            score += 10
    if "契約" in question or "金額" in question or "税込" in question:
        if any(word in clean for word in ["契約", "税込", "税抜", "金額", "ACTH", "ESTH", "RATE"]):
            score += 8
    if "担当" in question or "実施体制" in question:
        if any(word in clean for word in ["担当", "体制", "役割", "DA", "データアステル"]):
            score += 8
    return score


def compress_context(question: str, contexts: str, max_blocks: int = 4, max_lines: int = 28, max_chars: int = 5500) -> tuple[str, int, int]:
    """LLMが考え込みにくいよう、質問に強い行だけへ文脈を圧縮する。"""
    terms = question_terms(question)
    scored_blocks: list[tuple[int, str, list[tuple[int, str]]]] = []
    for title, lines in split_context_blocks(contexts):
        scored_lines: list[tuple[int, str]] = []
        for line in lines:
            clean = compact_answer(line)
            if not clean or noise_line(clean, terms):
                continue
            score = score_line(clean, question, terms)
            if score > 0:
                scored_lines.append((score, clean))
        title_score = score_line(title, question, terms)
        block_score = title_score + sum(score for score, _ in scored_lines[:12])
        if block_score > 0:
            scored_lines.sort(key=lambda x: (x[0], -len(x[1])), reverse=True)
            scored_blocks.append((block_score, title, scored_lines))
    scored_blocks.sort(key=lambda x: x[0], reverse=True)

    output: list[str] = []
    line_count = 0
    for _, title, lines in scored_blocks[:max_blocks]:
        output.append(f"# {title}")
        for _, line in lines[: max(4, max_lines // max_blocks)]:
            if line in output:
                continue
            output.append(line)
            line_count += 1
            if line_count >= max_lines:
                break
        if line_count >= max_lines:
            break
    compressed = "\n".join(output)
    if len(compressed) > max_chars:
        compressed = compressed[:max_chars]
    return compressed, len(scored_blocks), line_count


def acceptable_answer(answer: str) -> bool:
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 320:
        return False
    bad_markers = [
        "color=",
        "</span>",
        "```",
        "申し訳",
        "根拠",
        "json",
        "情報不足",
        "情報が不足",
        "不明",
        "見つかりません",
        "確認できません",
        "不足しています",
    ]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def parse_json_answer(content: str) -> str:
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


def read_openrouter_key() -> str:
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


def build_prompt(question: str, compressed_context: str) -> str:
    """短い文脈だけを渡し、回答形式を固定する。"""
    return f"""根拠は短く圧縮済みです。長く考えず、該当する値だけを返してください。

出力は必ずこのJSONのみ:
{{"answer":"短い回答"}}

禁止:
- 説明文
- Markdown
- 根拠の引用
- わかりません

質問:
{question}

圧縮済み根拠:
{compressed_context}
"""


def call_openrouter(model: str, api_key: str, question: str, compressed_context: str, max_tokens: int, timeout: int) -> tuple[str, dict[str, Any]]:
    """圧縮文脈でOpenRouterへ再投入する。"""
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "短いJSONだけを返す日本語QAエンジンです。"},
            {"role": "user", "content": build_prompt(question, compressed_context)},
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
            "HTTP-Referer": "https://signate.local/agentic-rag-eda043",
            "X-Title": "SIGNATE Agentic RAG EDA043",
        },
        method="POST",
    )
    meta: dict[str, Any] = {
        "model": model,
        "status": "",
        "finish_reason": "",
        "message_keys": [],
        "content_length": 0,
        "reasoning_present": False,
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
        meta["message_keys"] = sorted(message.keys())
        meta["content_length"] = len(content)
        meta["reasoning_present"] = bool(message.get("reasoning") or message.get("reasoning_details"))
        meta["prompt_tokens"] = int(usage.get("prompt_tokens", 0) or 0)
        meta["completion_tokens"] = int(usage.get("completion_tokens", 0) or 0)
        meta["reasoning_tokens"] = int(details.get("reasoning_tokens", 0) or 0)
        return parse_json_answer(content), meta
    except urllib.error.HTTPError as exc:
        meta["status"] = f"http_{exc.code}"
        meta["raw"] = {"error_body": exc.read().decode("utf-8", errors="replace")[:1000]}
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


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda043"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, retry_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[
        result_df["answer_before_eda043"].eq(UNKNOWN)
        & result_df["answer_after_eda043"].ne(UNKNOWN)
    ]
    status_summary = (
        retry_df.groupby(["status", "finish_reason"], as_index=False)
        .agg(count=("index", "count"), adopted=("adopted_by_eda043", "sum"), content_empty=("content_empty", "sum"))
        .sort_values(["adopted", "count"], ascending=[False, False])
    )
    view = retry_df[
        [
            "index",
            "question",
            "answer",
            "adopted_by_eda043",
            "status",
            "finish_reason",
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "compressed_chars",
            "compressed_line_count",
        ]
    ]
    report = f"""# EDA043: length空contentの圧縮文脈再試行

## 背景と目的

EDA042では、15件が `finish_reason=length` かつ `content` 空のまま残った。
raw responseから、`max_tokens=900` のほぼすべてを reasoning が消費していることが分かった。

EDA043では、この15件だけを対象に、EDA041の文脈を質問語に一致する行へ圧縮し、`max_tokens={args.max_tokens}` で再投入した。

## 結果

- test件数: {len(result_df)}
- EDA042時点の非 `わかりません`: {int((result_df["answer_before_eda043"] != UNKNOWN).sum())}
- EDA043対象件数: {int(len(retry_df))}
- EDA043で追加採用した件数: {int(len(improved))}
- EDA043後の非 `わかりません`: {int((result_df["answer_after_eda043"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## status別集計

凡例: `status` はHTTP/API状態、`finish_reason` はOpenRouterの終了理由、`count` は試行件数、`adopted` は提出回答に採用した件数、`content_empty` はcontent空件数を表す。

{status_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `compressed_chars` は圧縮後文脈の文字数、`compressed_line_count` は圧縮後に残した根拠行数、`reasoning_tokens` は推論で消費したcompletion token数を表す。

{view.to_markdown(index=False)}
"""
    (OUT_DIR / "eda043_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--target-limit", type=int, default=0)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    parser.add_argument("--reuse-existing", action="store_true", help="既存のattempt logを使い、APIを呼ばず採用判定だけ再計算する")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    api_key = read_openrouter_key()
    if not api_key and not args.reuse_existing:
        raise RuntimeError("OpenRouter API key was not found in .apikey or environment")

    result_df = pd.read_csv(INPUT_RESULT)
    retry_df = pd.read_csv(INPUT_RETRY)
    context_df = pd.read_csv(INPUT_CONTEXT)
    context_map = {int(row["index"]): normalize_text(row.get("contexts", "")) for _, row in context_df.iterrows()}
    targets = retry_df[
        retry_df["finish_reason"].fillna("").eq("length")
        & retry_df["content_length"].fillna(0).astype(int).eq(0)
    ].copy()
    if args.target_limit > 0:
        targets = targets.head(args.target_limit)

    answer_map = {
        int(row["index"]): compact_answer(row.get("answer_after_eda042", ""))
        for _, row in result_df.iterrows()
    }
    retry_rows: list[dict[str, Any]] = []
    existing_attempt_path = TABLE_DIR / "test_compressed_context_retry_attempt_log.csv"
    if args.reuse_existing and existing_attempt_path.exists():
        existing_attempt = pd.read_csv(existing_attempt_path)
        if args.target_limit > 0:
            existing_attempt = existing_attempt.head(args.target_limit)
        for _, row in existing_attempt.iterrows():
            index = int(row["index"])
            answer = compact_answer(row.get("answer", ""))
            adopted = acceptable_answer(answer)
            if adopted:
                answer_map[index] = answer
            retry_row = row.to_dict()
            retry_row["answer"] = answer
            retry_row["adopted_by_eda043"] = adopted
            retry_row["content_empty"] = int(not bool(int(row.get("content_length", 0) or 0)))
            retry_rows.append(retry_row)
    else:
        for _, row in targets.sort_values("index").iterrows():
            index = int(row["index"])
            question = normalize_text(row.get("question", ""))
            compressed, block_count, line_count = compress_context(question, context_map.get(index, ""))
            answer = ""
            chosen_meta: dict[str, Any] | None = None
            raw_path = ""
            for model in args.models:
                candidate, meta = call_openrouter(model, api_key, question, compressed, args.max_tokens, args.timeout_sec)
                raw_path = write_raw_response(index, meta)
                chosen_meta = meta
                if acceptable_answer(candidate):
                    answer = candidate
                    break
                time.sleep(args.sleep_sec)
            if chosen_meta is None:
                chosen_meta = {}
            adopted = acceptable_answer(answer)
            if adopted:
                answer_map[index] = answer
            retry_rows.append(
                {
                    "index": index,
                    "question": question,
                    "answer": answer,
                    "adopted_by_eda043": adopted,
                    "status": chosen_meta.get("status", ""),
                    "finish_reason": chosen_meta.get("finish_reason", ""),
                    "message_keys": json.dumps(chosen_meta.get("message_keys", []), ensure_ascii=False),
                    "content_length": int(chosen_meta.get("content_length", 0) or 0),
                    "content_empty": int(not bool(chosen_meta.get("content_length", 0))),
                    "reasoning_present": bool(chosen_meta.get("reasoning_present", False)),
                    "prompt_tokens": int(chosen_meta.get("prompt_tokens", 0) or 0),
                    "completion_tokens": int(chosen_meta.get("completion_tokens", 0) or 0),
                    "reasoning_tokens": int(chosen_meta.get("reasoning_tokens", 0) or 0),
                    "compressed_chars": len(compressed),
                    "compressed_block_count": block_count,
                    "compressed_line_count": line_count,
                    "raw_response_path": raw_path,
                    "compressed_context": compressed,
                }
            )

    output_rows: list[dict[str, Any]] = []
    for _, row in result_df.sort_values("index").iterrows():
        before = compact_answer(row.get("answer_after_eda042", ""))
        if not before:
            before = UNKNOWN
        after = answer_map.get(int(row["index"]), before)
        out = row.to_dict()
        out["answer_before_eda043"] = before
        out["answer_after_eda043"] = after
        out["improved_by_eda043"] = before == UNKNOWN and after != UNKNOWN
        output_rows.append(out)

    out_df = pd.DataFrame(output_rows)
    retry_out_df = pd.DataFrame(retry_rows)
    out_df.to_csv(TABLE_DIR / "test_compressed_context_retry_result.csv", index=False, encoding="utf-8-sig")
    retry_out_df.to_csv(TABLE_DIR / "test_compressed_context_retry_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(out_df)
    write_report(out_df, retry_out_df, args)
    manifest = {
        "eda": "EDA043",
        "input_result": relative(INPUT_RESULT),
        "input_retry": relative(INPUT_RETRY),
        "input_context": relative(INPUT_CONTEXT),
        "target_count": int(len(retry_out_df)),
        "before_non_unknown_count": int((out_df["answer_before_eda043"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(out_df["improved_by_eda043"].sum()),
        "after_non_unknown_count": int((out_df["answer_after_eda043"] != UNKNOWN).sum()),
        "outputs": [
            relative(TABLE_DIR / "test_compressed_context_retry_result.csv"),
            relative(TABLE_DIR / "test_compressed_context_retry_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda043_report.md"),
            relative(RAW_DIR),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
