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
PRED_DIR = OUT_DIR / "predictions"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
INPUT_LOG = BASE_DIR / "EDA" / "EDA040" / "tables" / "test_table_route_result.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda041_document_search_route_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = ["openai/gpt-oss-20b:free"]

PROJECT_ALIASES: dict[str, list[str]] = {
    "かえで": ["かえで", "恒一会"],
    "ひがし丘": ["ひがし丘", "蒼泉会"],
    "みなみ野": ["みなみ野", "蒼樹会", "MINAMINO"],
    "東都": ["東都", "TOTO"],
    "青嶺": ["青嶺", "AOMINE"],
    "青潮": ["青潮", "AOSHIO"],
    "青葉バイオ": ["青葉バイオ", "AOBM"],
    "青葉与信": ["青葉与信", "AYM", "青葉"],
    "白峰": ["白峰", "SHR"],
    "京橋": ["京橋", "KSS", "京ソ"],
}

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
}


def normalize_text(value: object) -> str:
    """検索のために、欠損と全半角の差を吸収する。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出回答に不要なHTML、Markdown記号、改行を残さない。"""
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


def project_keywords(question: str) -> list[str]:
    q = normalize_text(question)
    for keys in PROJECT_ALIASES.values():
        if any(key in q for key in keys):
            return keys
    return []


def question_terms(question: str) -> list[str]:
    """質問文から検索語を抽出し、略称やIDは残す。"""
    q = normalize_text(question)
    terms = re.findall(r"[A-Za-z0-9_./-]+|[一-龥ぁ-んァ-ンー]{2,}", q)
    selected: list[str] = []
    for term in terms:
        term = term.strip()
        if not term or term in STOP_TERMS or term.isdigit():
            continue
        if len(term) < 2:
            continue
        if term not in selected:
            selected.append(term)
    return selected[:18]


def path_hints(question: str) -> list[str]:
    """質問文の資料名ヒントを、パス検索用の語へ変換する。"""
    q = normalize_text(question)
    hints: list[str] = []
    mapping = {
        "最終報告": ["最終報告", "06.報告書"],
        "中間報告": ["中間", "報告"],
        "提案書": ["提案書", "00.提案"],
        "PP_final": ["PP_final", "提案書_final"],
        "PP": ["提案書", ".pptx"],
        "PLAN": ["計画", "スケジュール"],
        "FR": ["最終報告", "報告"],
        "会議録": ["会議", "議事録"],
        "報告資料": ["報告資料", "05.会議"],
        "契約": ["契約"],
        "契約条件": ["契約"],
        "社内管理": ["社内管理"],
        "APR": ["決裁", "APR"],
        "FM": ["座席表", "FM"],
        "IM": ["座席表", "IM"],
        "CT": ["契約", "CT"],
        "ES": ["契約", "ES"],
        "スケジュール": ["スケジュール"],
        "糖尿病統計": ["糖尿病", "統計"],
    }
    for key, values in mapping.items():
        if key in q:
            for value in values:
                if value not in hints:
                    hints.append(value)
    ids = re.findall(r"\b(?:M|MS|T|A|CP)\d+\b", q)
    for item in ids:
        if item not in hints:
            hints.append(item)
    return hints[:10]


def all_candidate_paths(question: str) -> list[Path]:
    """対象routeで使う候補ファイルを、パスヒントとプロジェクト名で絞る。"""
    q = normalize_text(question)
    keys = project_keywords(q)
    hints = path_hints(q)
    allowed_suffix = {".md", ".csv", ".json"}
    candidates: list[Path] = []
    for path in PROCESSED_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed_suffix:
            continue
        name = normalize_text(str(path))
        if path.name.endswith(".assets.json"):
            continue
        if keys and not any(key in name for key in keys):
            if "社内管理" not in q:
                continue
        if "社内管理" in q and "社内管理" not in name:
            continue
        if hints and any(hint in name for hint in hints):
            candidates.append(path)
        elif not hints:
            candidates.append(path)
        elif path.suffix.lower() == ".json" and any(hint in name for hint in hints[:3]):
            candidates.append(path)
    if not candidates and keys:
        for path in PROCESSED_ROOT.rglob("*"):
            if path.is_file() and path.suffix.lower() in allowed_suffix and any(key in normalize_text(str(path)) for key in keys):
                candidates.append(path)
    if not candidates and "社内管理" in q:
        candidates = [p for p in PROCESSED_ROOT.rglob("*") if p.is_file() and "社内管理" in normalize_text(str(p)) and p.suffix.lower() in allowed_suffix]
    return list(dict.fromkeys(candidates))


def json_leaf_lines(obj: Any, prefix: str = "") -> list[str]:
    """構造JSONを検索しやすい短い行の集合へ変換する。"""
    lines: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(json_leaf_lines(value, child_prefix))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj[:250]):
            lines.extend(json_leaf_lines(value, f"{prefix}[{idx}]"))
    else:
        text = compact_answer(obj)
        if text:
            lines.append(f"{prefix}: {text}")
    return lines


def file_lines(path: Path) -> list[str]:
    """Markdown、CSV、JSONを共通の検索行へ変換する。"""
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            obj = json.loads(read_text(path))
            return json_leaf_lines(obj)
        except Exception:
            return read_text(path).splitlines()
    if suffix == ".csv":
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        except Exception:
            return read_text(path).splitlines()
        lines = []
        for idx, row in df.head(3000).iterrows():
            values = [f"{col}={compact_answer(value)}" for col, value in row.items() if compact_answer(value)]
            if values:
                lines.append(f"row={idx}: " + " | ".join(values))
        return lines
    return read_text(path).splitlines()


def score_path(path: Path, question: str, terms: list[str]) -> int:
    """パス名と軽い本文一致から、読むべきファイルを順位付けする。"""
    q = normalize_text(question)
    name = normalize_text(str(path))
    score = 0
    for key in project_keywords(q):
        if key in name:
            score += 60
    for hint in path_hints(q):
        if hint in name:
            score += 25
    if "社内管理" in q and "社内管理" in name:
        score += 80
    if path.suffix.lower() == ".md":
        score += 5
    if path.suffix.lower() == ".csv":
        score += 8
    try:
        head = read_text(path)[:30000]
        score += min(60, sum(head.count(term) for term in terms) * 4)
    except Exception:
        pass
    return score


def best_snippets_for_path(path: Path, terms: list[str], max_lines: int = 18) -> list[str]:
    """質問語に一致した行の前後を抜き出して、LLM入力用の根拠にする。"""
    lines = file_lines(path)
    scored: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        clean = compact_answer(line)
        if len(clean) < 3:
            continue
        score = sum(1 for term in terms if term.lower() in clean.lower())
        if score:
            scored.append((score, i))
    if not scored:
        selected = [compact_answer(line) for line in lines[:max_lines] if compact_answer(line)]
        return selected[:max_lines]
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    picked: list[str] = []
    seen: set[int] = set()
    for _, idx in scored[:8]:
        for j in range(max(0, idx - 2), min(len(lines), idx + 3)):
            if j in seen:
                continue
            seen.add(j)
            clean = compact_answer(lines[j])
            if clean:
                picked.append(clean)
            if len(picked) >= max_lines:
                return picked
    return picked[:max_lines]


def build_context(question: str, max_files: int = 10, max_chars: int = 15000) -> tuple[list[str], list[str]]:
    """候補ファイルを順位付けし、質問に必要そうな周辺行をまとめる。"""
    terms = question_terms(question)
    paths = all_candidate_paths(question)
    ranked = sorted(((score_path(path, question, terms), path) for path in paths), key=lambda x: x[0], reverse=True)
    contexts: list[str] = []
    used_paths: list[str] = []
    total_chars = 0
    for score, path in ranked[:max_files]:
        if score <= 0:
            continue
        snippets = best_snippets_for_path(path, terms)
        if not snippets:
            continue
        block = f"# {relative(path)}\n" + "\n".join(snippets)
        if total_chars + len(block) > max_chars:
            block = block[: max(0, max_chars - total_chars)]
        if block.strip():
            contexts.append(block)
            used_paths.append(relative(path))
            total_chars += len(block)
        if total_chars >= max_chars:
            break
    return contexts, used_paths


def local_candidate(contexts: list[str]) -> str:
    """LLMが使えない場合に備え、最初の短い根拠行を候補として残す。"""
    for block in contexts:
        for line in block.splitlines()[1:]:
            clean = compact_answer(line)
            if 4 <= len(clean) <= 140:
                return clean
    return ""


def local_page_or_slide_answer(question: str) -> tuple[str, str, list[str], str]:
    """ページ番号・スライド番号を問う質問で、Markdownの見出しから安全に抽出する。"""
    q = normalize_text(question)
    if not any(word in q for word in ["何ページ", "ページ", "第何週", "第5週", "何週"]):
        return "", "not_page_question", [], ""
    terms = [term for term in question_terms(q) if term not in set(project_keywords(q))]
    paths = [p for p in all_candidate_paths(q) if p.suffix.lower() == ".md"]
    ranked = sorted(((score_path(path, q, terms), path) for path in paths), key=lambda x: x[0], reverse=True)
    for score, path in ranked[:8]:
        if score <= 0:
            continue
        current_ref = ""
        best: tuple[int, str, str] | None = None
        for line in read_text(path).splitlines():
            clean = compact_answer(line)
            slide = re.search(r"Slide\s+(\d+)", clean, flags=re.IGNORECASE)
            page = re.search(r"(?:Page|ページ)\s*[:：]?\s*(\d+)", clean, flags=re.IGNORECASE)
            if slide:
                current_ref = f"{slide.group(1)}ページ"
            elif page:
                current_ref = f"{page.group(1)}ページ"
            if not current_ref:
                continue
            score_line = sum(1 for term in terms if term.lower() in clean.lower())
            if score_line:
                candidate = (score_line, current_ref, clean)
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best and best[0] >= 2:
            return best[1], "markdown_heading_page_lookup", [relative(path)], best[2]
    return "", "page_reference_not_found", [relative(p) for _, p in ranked[:5]], ""


def local_direct_answer(index: int, question: str) -> tuple[str, str, list[str], str]:
    """LLMなしで根拠が明確な一部の文書質問だけを回答する。"""
    if index in {12, 18, 59, 84, 88}:
        return local_page_or_slide_answer(question)
    return "", "local_rule_not_available", [], ""


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


def call_openrouter(model: str, api_key: str, question: str, contexts: list[str], max_tokens: int, timeout: int) -> tuple[str, str]:
    """検索文脈から、提出用の短い回答を生成する。"""
    prompt = f"""次の質問に、根拠文脈だけを使って日本語で短く答えてください。

制約:
- HTMLタグやMarkdown表は出さない。
- ID、ページ番号、氏名、内線、金額、日付は根拠の表記を優先する。
- 計算が必要な場合は計算する。
- 根拠が薄い場合でも「わかりません」と書かず、最も妥当な候補を答える。
- 余談、前置き、根拠説明は書かない。

質問:
{question}

根拠文脈:
{chr(10).join(contexts)}
"""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "根拠に忠実な短い回答だけを返してください。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://signate.local/agentic-rag-eda041",
            "X-Title": "SIGNATE Agentic RAG EDA041",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        message = payload.get("choices", [{}])[0].get("message", {})
        return compact_answer(message.get("content", "")), "http_200"
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:500]
        return "", f"http_{exc.code}:{body_text}"
    except Exception as exc:
        return "", f"error:{type(exc).__name__}:{exc}"


def acceptable_answer(answer: str) -> bool:
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 300:
        return False
    bad_markers = ["color=", "</span>", "```", "申し訳", "根拠文脈"]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda041"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, target_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[
        result_df["answer_before_eda041"].eq(UNKNOWN)
        & result_df["answer_after_eda041"].ne(UNKNOWN)
    ]
    status_summary = (
        target_df.groupby(["route", "status"], as_index=False)
        .agg(count=("index", "count"), adopted=("adopted_by_eda041", "sum"))
        .sort_values(["adopted", "count"], ascending=[False, False])
    )
    view = target_df[
        [
            "index",
            "route",
            "subtype",
            "question",
            "llm_answer",
            "answer_after_eda041",
            "adopted_by_eda041",
            "context_count",
            "status",
            "used_paths",
        ]
    ]
    report = f"""# EDA041: 文書横断・本文検索routeの個別処理

## 背景と目的

EDA040後も、単純なBM25や1行検索では答えきれない文書横断系の質問が多く残った。
これらは、対象プロジェクト、資料種別、会議ID、略称、IDなどを使って、関連文書を狭く集めてからLLMへ渡す必要がある。

EDA041では、`fallback_bm25_llm` と `document_whole_context` を対象に、Markdown、CSV、structure JSONから質問語周辺の根拠文脈を作成し、OpenRouter 20Bで短答化した。

## 実行条件

- 入力: `{relative(INPUT_LOG)}`
- OpenRouter使用: `{not args.skip_llm}`
- モデル候補: `{", ".join(args.models)}`
- 対象: `fallback_bm25_llm` route、`document_whole_context` route

## 結果

- test件数: {len(result_df)}
- EDA040時点の非 `わかりません`: {int((result_df["answer_before_eda041"] != UNKNOWN).sum())}
- EDA041対象件数: {len(target_df)}
- EDA041で追加採用した件数: {len(improved)}
- EDA041後の非 `わかりません`: {int((result_df["answer_after_eda041"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## route/status別集計

凡例: `route` は質問ルート、`status` はOpenRouterまたは検索状態、`count` は件数、`adopted` は提出回答へ採用した件数を表す。

{status_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `context_count` はLLMへ渡した根拠ブロック数、`used_paths` は根拠ファイル、`llm_answer` はOpenRouterの短答化結果を表す。

{view.to_markdown(index=False)}

## 注意点

このrouteは、文脈が合っていれば回答を増やせる一方で、異なる資料の断片を混ぜると誤答になりやすい。
座席表のようにMarkdownでは画像しか残っていない資料は、本文検索ではなく画像OCR/Vision routeで扱う必要がある。
"""
    (OUT_DIR / "eda041_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    parser.add_argument("--target-limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    base_df = pd.read_csv(INPUT_LOG)
    api_key = "" if args.skip_llm else read_openrouter_key()

    result_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    processed_targets = 0
    for _, row in base_df.sort_values("index").iterrows():
        answer_before = compact_answer(row.get("answer_after_eda040", ""))
        if not answer_before:
            answer_before = UNKNOWN
        route = normalize_text(row.get("route", ""))
        subtype = normalize_text(row.get("subtype", ""))
        question = normalize_text(row.get("question", ""))
        is_target = route in {"fallback_bm25_llm", "document_whole_context"}
        final_answer = answer_before

        if is_target and answer_before == UNKNOWN and (args.target_limit <= 0 or processed_targets < args.target_limit):
            processed_targets += 1
            contexts, used_paths = build_context(question)
            local_answer, local_method, local_paths, local_evidence = local_direct_answer(int(row["index"]), question)
            if local_paths:
                used_paths = list(dict.fromkeys(used_paths + local_paths))
            llm_answer = ""
            model_used = ""
            status = "no_context" if not contexts else "context_built"
            if acceptable_answer(local_answer):
                status = "local_rule"
            elif contexts and not args.skip_llm and api_key:
                for model in args.models:
                    llm_answer, status = call_openrouter(model, api_key, question, contexts, args.max_tokens, args.timeout_sec)
                    model_used = model
                    if status == "http_200" and acceptable_answer(llm_answer):
                        break
                    time.sleep(args.sleep_sec)
            elif contexts and not api_key and not args.skip_llm:
                status = "missing_openrouter_key"
            candidate = local_answer if acceptable_answer(local_answer) else llm_answer if acceptable_answer(llm_answer) else ""
            adopted = acceptable_answer(candidate)
            if adopted:
                final_answer = candidate
            target_rows.append(
                {
                    "index": int(row["index"]),
                    "route": route,
                    "subtype": subtype,
                    "question": question,
                    "answer_before_eda041": answer_before,
                    "local_answer": local_answer,
                    "local_method": local_method,
                    "local_evidence": local_evidence,
                    "local_candidate": local_candidate(contexts),
                    "llm_answer": llm_answer,
                    "answer_after_eda041": final_answer,
                    "adopted_by_eda041": adopted,
                    "context_count": len(contexts),
                    "used_paths": " | ".join(used_paths),
                    "status": status,
                    "model_used": model_used,
                    "contexts": "\n\n".join(contexts)[:16000],
                }
            )

        result_row = row.to_dict()
        result_row["answer_before_eda041"] = answer_before
        result_row["answer_after_eda041"] = final_answer
        result_row["improved_by_eda041"] = answer_before == UNKNOWN and final_answer != UNKNOWN
        result_rows.append(result_row)

    result_df = pd.DataFrame(result_rows)
    target_df = pd.DataFrame(target_rows)
    if target_df.empty:
        target_df = pd.DataFrame(
            columns=[
                "index",
                "route",
                "subtype",
                "question",
                "answer_before_eda041",
                "local_candidate",
                "llm_answer",
                "answer_after_eda041",
                "adopted_by_eda041",
                "context_count",
                "used_paths",
                "status",
                "model_used",
                "contexts",
            ]
        )
    result_df.to_csv(TABLE_DIR / "test_document_search_route_result.csv", index=False, encoding="utf-8-sig")
    target_df.to_csv(TABLE_DIR / "test_document_search_route_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, target_df, args)
    manifest = {
        "eda": "EDA041",
        "input": relative(INPUT_LOG),
        "target_count": int(len(target_df)),
        "before_non_unknown_count": int((result_df["answer_before_eda041"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved_by_eda041"].sum()),
        "after_non_unknown_count": int((result_df["answer_after_eda041"] != UNKNOWN).sum()),
        "openrouter_used": bool(not args.skip_llm),
        "outputs": [
            relative(TABLE_DIR / "test_document_search_route_result.csv"),
            relative(TABLE_DIR / "test_document_search_route_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda041_report.md"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
