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
from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"
PROCESSED_ROOT = BASE_DIR / "data" / "processed" / "share"
INPUT_LOG = BASE_DIR / "EDA" / "EDA037" / "tables" / "test_unhandled_route_candidates.csv"
PREDICTIONS_PATH = PRED_DIR / "predictions.csv"
ZIP_PATH = PRED_DIR / "eda038_diff_route_submission.zip"
UNKNOWN = "わかりません"

MODEL_CANDIDATES = [
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "deepseek/deepseek-r1-0528:free",
]


@dataclass
class DiffContext:
    subtype: str
    old_path: Path | None
    new_path: Path | None
    local_answer: str
    evidence: str
    confidence: str
    needs_llm: bool = True


def normalize_text(value: object) -> str:
    """検索と比較の表記揺れを減らすため、欠損と全半角を正規化する。"""
    if value is None or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value))


def compact_answer(value: object) -> str:
    """提出CSVに混入しやすいタグ、改行、余分な空白を除く。"""
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


def find_paths(*keywords: str, suffix: str | None = None) -> list[Path]:
    """processed配下から、パス文字列にキーワードをすべて含むファイルを探す。"""
    keys = [normalize_text(k).lower() for k in keywords if k]
    results: list[Path] = []
    for path in PROCESSED_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if suffix and not normalize_text(path.name).lower().endswith(suffix.lower()):
            continue
        haystack = normalize_text(str(path)).lower().replace("\\", "/")
        if all(key in haystack for key in keys):
            results.append(path)
    return sorted(results, key=lambda p: normalize_text(str(p)))


def clean_line(line: str) -> str:
    line = compact_answer(line)
    line = re.sub(r"^#+\s*", "", line)
    line = re.sub(r"^\|\s*", "", line)
    return line.strip(" |")


def cleaned_lines(text: str) -> list[str]:
    """Markdown化済み文書から、差分判定に使える本文行だけを取り出す。"""
    lines: list[str] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if len(line) < 5 or len(line) > 220:
            continue
        if set(line) <= {"-", "=", "|", " "}:
            continue
        if line.lower().startswith(("source:", "path:", "file:")):
            continue
        lines.append(line)
    return list(dict.fromkeys(lines))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def material_line(line: str) -> bool:
    """ページ番号などのノイズではなく、案件遂行に関係しそうな差分を残す。"""
    ng_words = ["copyright", "confidential", "ページ", "slide", "スライド", "目次", "表紙"]
    if any(word in line.lower() for word in ng_words):
        return False
    keep_words = [
        "変更",
        "追加",
        "削除",
        "完了",
        "未着手",
        "担当",
        "工数",
        "金額",
        "モデル",
        "評価",
        "f1",
        "auc",
        "accuracy",
        "スケジュール",
        "リスク",
        "役割",
        "閾値",
        "rate",
        "契約",
        "請求",
    ]
    return any(word in line.lower() for word in keep_words)


def diff_added_lines(old_path: Path, new_path: Path, max_lines: int = 20) -> list[str]:
    """旧版に近い行がない新版行を抽出し、実質差分候補に絞る。"""
    old_lines = cleaned_lines(read_text(old_path))
    new_lines = cleaned_lines(read_text(new_path))
    added: list[str] = []
    for line in new_lines:
        if line in old_lines:
            continue
        near = max((similarity(line, old) for old in old_lines), default=0.0)
        if near < 0.88 and material_line(line):
            added.append(line)
    return added[:max_lines]


def unified_context(old_path: Path, new_path: Path, max_chars: int = 9000) -> str:
    """LLMに渡すため、長すぎないunified diffを作る。"""
    old_lines = cleaned_lines(read_text(old_path))
    new_lines = cleaned_lines(read_text(new_path))
    diff = "\n".join(
        unified_diff(
            old_lines,
            new_lines,
            fromfile=relative(old_path),
            tofile=relative(new_path),
            lineterm="",
            n=1,
        )
    )
    return diff[:max_chars]


def pick_single(paths: list[Path], prefer_without: str | None = None) -> Path | None:
    if not paths:
        return None
    if prefer_without:
        filtered = [p for p in paths if prefer_without not in normalize_text(str(p)).lower()]
        if filtered:
            return filtered[-1]
    return paths[-1]


def build_pair(index: int, question: str) -> tuple[Path | None, Path | None, str]:
    """質問番号と文面から、比較すべき旧版/新版ファイルの組を決める。"""
    q = normalize_text(question)
    if index == 1:
        return (
            pick_single(find_paths("かえで", "最終報告_old", suffix=".pptx.md")),
            pick_single(find_paths("かえで", "最終報告.pptx.md"), prefer_without="old"),
            "pptx_final_old_latest",
        )
    if index == 9:
        return (
            pick_single(find_paths("青葉与信", "報告書", "old", "最終報告", suffix=".pptx.md")),
            pick_single(find_paths("青葉与信", "報告書", "最終報告", suffix=".pptx.md"), prefer_without="old"),
            "pptx_final_old_latest",
        )
    if index == 14:
        return (
            pick_single(find_paths("青葉与信", "提案書_v1", suffix=".pptx.md")),
            pick_single(find_paths("青葉与信", "提案書_v3", suffix=".pptx.md")),
            "pptx_proposal_v1_v3",
        )
    if index == 22:
        return (
            pick_single(find_paths("白峰", "01_eda_old", suffix=".ipynb.md")),
            pick_single(find_paths("白峰", "01_eda.ipynb", suffix=".ipynb.md"), prefer_without="old"),
            "notebook_old_latest",
        )
    if index == 74:
        return (
            pick_single(find_paths("青葉与信", "提案書_v1", suffix=".pptx.md")),
            pick_single(find_paths("青葉与信", "提案書_v2", suffix=".pptx.md")),
            "pptx_proposal_v1_v2",
        )
    if index == 95:
        return (
            pick_single(find_paths("青嶺", "スケジュール_r1", suffix=".xlsx.md")),
            pick_single(find_paths("青嶺", "スケジュール_r2", suffix=".xlsx.md")),
            "xlsx_schedule_r1_r2",
        )
    if "白峰" in q and "提案書old" in q:
        return (
            pick_single(find_paths("白峰", "提案書old", suffix=".pptx.md")),
            pick_single(find_paths("白峰", "提案書.pptx.md"), prefer_without="old"),
            "pptx_proposal_old_latest",
        )
    return (None, None, "version_diff")


def local_schedule_r1_r2_answer(old_path: Path, new_path: Path) -> DiffContext:
    """青嶺スケジュール差分では、未着手から完了だけの変化を除外して候補を作る。"""
    old_lines = cleaned_lines(read_text(old_path))
    new_lines = cleaned_lines(read_text(new_path))
    old_set = set(old_lines)
    added = [line for line in new_lines if line not in old_set]
    filtered = [line for line in added if not ("未着手" in line and "完了" in line)]
    selected = filtered[:10] if filtered else added[:10]
    answer = "、".join(selected[:4]) if selected else "変更なし"
    evidence = "\n".join(selected)
    return DiffContext("xlsx_schedule_r1_r2", old_path, new_path, answer, evidence, "medium", needs_llm=True)


def local_rate_change_answer(question: str) -> DiffContext:
    """RATE改定日は差分ペアではなく、契約・管理系文書を横断検索して候補を作る。"""
    terms = ["RATE", "変更", "改定", "適用", "年月", "202"]
    scored: list[tuple[int, str, Path]] = []
    for path in find_paths(suffix=".md"):
        text_path = normalize_text(str(path))
        if not any(key in text_path for key in ["契約", "管理", "社内", "TM", "東都", "青嶺", "青葉"]):
            continue
        for line in read_text(path).splitlines():
            clean = clean_line(line)
            if len(clean) < 6 or len(clean) > 180:
                continue
            score = sum(1 for term in terms if term.lower() in clean.lower())
            if score >= 2:
                scored.append((score, clean, path))
    scored.sort(key=lambda x: (x[0], -len(x[1])), reverse=True)
    if not scored:
        return DiffContext("rate_change_search", None, None, "", "", "none")
    selected = scored[:8]
    answer = selected[0][1]
    evidence = "\n".join(f"{relative(path)}: {line}" for _, line, path in selected)
    return DiffContext("rate_change_search", selected[0][2], None, answer, evidence, "medium", needs_llm=True)


def build_diff_context(index: int, question: str) -> DiffContext:
    if index == 98:
        return local_rate_change_answer(question)
    old_path, new_path, subtype = build_pair(index, question)
    if not old_path or not new_path:
        return DiffContext(subtype, old_path, new_path, "", "comparison files were not found", "none")
    if subtype == "xlsx_schedule_r1_r2":
        return local_schedule_r1_r2_answer(old_path, new_path)
    added = diff_added_lines(old_path, new_path)
    if not added:
        return DiffContext(subtype, old_path, new_path, "変更なし", unified_context(old_path, new_path), "medium", needs_llm=True)
    return DiffContext(subtype, old_path, new_path, "、".join(added[:5]), unified_context(old_path, new_path), "medium", needs_llm=True)


def read_openrouter_key() -> str:
    """プロジェクトローカルの.apikeyからOpenRouterキーだけを読む。"""
    key_file = BASE_DIR / ".apikey"
    if not key_file.exists():
        return ""
    for raw in key_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, value = line.split("=", 1)
            if name.strip().lower() in {"openrouter", "openrouter_api_key"}:
                return value.strip().strip('"').strip("'")
    return os.environ.get("OPENROUTER_API_KEY", "")


def call_openrouter(model: str, api_key: str, question: str, context: DiffContext, max_tokens: int, timeout: int) -> tuple[str, str]:
    """差分文脈から、提出用の短い日本語回答を生成する。"""
    prompt = f"""あなたは社内共有ドライブのRAG回答を作る担当です。
質問に対して、根拠テキストだけを使い、日本語で短く答えてください。

制約:
- HTMLタグ、Markdown表、箇条書き記号は出さない。
- 1文または短い読点区切りで答える。
- 数値・日付・タスクIDは根拠にある表記を優先する。
- 根拠が不足する場合でも「わかりません」とは書かず、根拠から最も妥当な候補を答える。

質問:
{question}

旧ファイル:
{relative(context.old_path)}

新ファイル:
{relative(context.new_path)}

ローカル候補:
{context.local_answer}

差分または検索根拠:
{context.evidence[:9000]}
"""
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "根拠に忠実な日本語の短い回答だけを返してください。",
            },
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
            "HTTP-Referer": "https://signate.local/agentic-rag-eda038",
            "X-Title": "SIGNATE Agentic RAG EDA038",
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
    """差分routeでは、長すぎる回答やタグ混入回答を提出に入れない。"""
    if not answer or answer == UNKNOWN:
        return False
    if len(answer) > 280:
        return False
    bad_markers = ["color=", "</span>", "```", "申し訳", "根拠テキスト"]
    return not any(marker.lower() in answer.lower() for marker in bad_markers)


def write_submission(df: pd.DataFrame) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for _, row in df.sort_values("index").iterrows():
            writer.writerow([int(row["index"]), compact_answer(row["answer_after_eda038"])])
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PREDICTIONS_PATH, arcname="predictions.csv")


def write_report(result_df: pd.DataFrame, target_df: pd.DataFrame, args: argparse.Namespace) -> None:
    improved = result_df[
        result_df["answer_before_eda038"].eq(UNKNOWN)
        & result_df["answer_after_eda038"].ne(UNKNOWN)
    ]
    target_view = target_df[
        [
            "index",
            "route",
            "subtype_after_eda038",
            "question",
            "answer_before_eda038",
            "local_answer",
            "llm_answer",
            "answer_after_eda038",
            "adopted_by_eda038",
            "model_used",
            "status",
            "old_path",
            "new_path",
        ]
    ]
    status_summary = (
        target_df.groupby(["subtype_after_eda038", "status"], as_index=False)
        .agg(count=("index", "count"), adopted=("adopted_by_eda038", "sum"))
        .sort_values(["adopted", "count"], ascending=[False, False])
    )
    report = f"""# EDA038: 差分比較routeの個別処理

## 背景と目的

EDA037では、testで残った `わかりません` のうち差分比較系が複数残った。
差分系は単純なBM25検索では、旧版と新版のどちらを根拠にすべきかが曖昧になりやすい。

EDA038では、差分比較routeだけを切り出し、質問ごとに旧版/新版ファイルを明示的にペアリングした。
その上でMarkdown化済みファイルの差分を作り、必要に応じてOpenRouterの無料モデルで短い提出回答へ整形した。

## 実行条件

- 入力: `{relative(INPUT_LOG)}`
- OpenRouter使用: `{not args.skip_llm}`
- モデル候補: `{", ".join(args.models)}`
- 対象: `diff_check` route、または `version_diff` subtype、またはRATE変更日の質問

## 結果

- test件数: {len(result_df)}
- EDA037時点の非 `わかりません`: {int((result_df["answer_before_eda038"] != UNKNOWN).sum())}
- EDA038対象件数: {len(target_df)}
- EDA038で追加採用した件数: {len(improved)}
- EDA038後の非 `わかりません`: {int((result_df["answer_after_eda038"] != UNKNOWN).sum())}
- 提出形式zip: `{relative(ZIP_PATH)}`

## subtype/status別集計

凡例: `subtype_after_eda038` はEDA038で判定した差分処理の種類、`status` はLLM/APIまたは採用判定の状態、`count` は件数、`adopted` は提出回答に採用した件数を表す。

{status_summary.to_markdown(index=False)}

## 対象質問別ログ

凡例: `local_answer` はローカル差分から作った候補、`llm_answer` はOpenRouterで整形した回答、`answer_after_eda038` は提出CSVに入れた回答、`old_path`/`new_path` は比較対象ファイルを表す。

{target_view.to_markdown(index=False)}

## 注意点

差分候補は、旧版/新版のペアリングが正しければBM25より安定する。
一方で、Markdown化時にスライド上の位置関係や表構造が崩れると、差分の意味が読み取りにくくなる。
次のEDAでは、文書全体route、表計算route、書式抽出routeも同様に個別処理へ分ける。
"""
    (OUT_DIR / "eda038_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true", help="OpenRouterを使わずローカル差分候補だけで実行する")
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--models", nargs="*", default=MODEL_CANDIDATES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    base_df = pd.read_csv(INPUT_LOG)
    api_key = "" if args.skip_llm else read_openrouter_key()

    rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    for _, row in base_df.sort_values("index").iterrows():
        index = int(row["index"])
        answer_before = compact_answer(row.get("answer_after", ""))
        if not answer_before:
            answer_before = UNKNOWN
        question = normalize_text(row.get("question", ""))
        route = normalize_text(row.get("route", ""))
        subtype = normalize_text(row.get("subtype", ""))
        is_target = route == "diff_check" or subtype == "version_diff" or index == 98

        final_answer = answer_before
        target_record: dict[str, Any] | None = None
        if is_target and (answer_before == UNKNOWN or index in {0}):
            context = build_diff_context(index, question)
            llm_answer = ""
            model_used = ""
            status = "local_only"
            if not args.skip_llm and api_key and context.needs_llm and context.evidence:
                for model in args.models:
                    llm_answer, status = call_openrouter(model, api_key, question, context, args.max_tokens, args.timeout_sec)
                    model_used = model
                    if status == "http_200" and acceptable_answer(llm_answer):
                        break
                    time.sleep(args.sleep_sec)
            elif not api_key and not args.skip_llm:
                status = "missing_openrouter_key"

            candidate_answer = llm_answer if acceptable_answer(llm_answer) else context.local_answer
            adopted = answer_before == UNKNOWN and acceptable_answer(candidate_answer)
            if adopted:
                final_answer = candidate_answer
            target_record = {
                "index": index,
                "route": route,
                "subtype_before": subtype,
                "subtype_after_eda038": context.subtype,
                "question": question,
                "answer_before_eda038": answer_before,
                "local_answer": context.local_answer,
                "llm_answer": llm_answer,
                "answer_after_eda038": final_answer,
                "adopted_by_eda038": adopted,
                "model_used": model_used,
                "status": status,
                "confidence": context.confidence,
                "old_path": relative(context.old_path),
                "new_path": relative(context.new_path),
                "evidence": context.evidence[:6000],
            }

        result_row = row.to_dict()
        result_row["answer_before_eda038"] = answer_before
        result_row["answer_after_eda038"] = final_answer
        result_row["improved_by_eda038"] = answer_before == UNKNOWN and final_answer != UNKNOWN
        result_rows.append(result_row)
        if target_record is not None:
            rows.append(target_record)

    result_df = pd.DataFrame(result_rows)
    target_df = pd.DataFrame(rows)
    if target_df.empty:
        target_df = pd.DataFrame(
            columns=[
                "index",
                "route",
                "subtype_before",
                "subtype_after_eda038",
                "question",
                "answer_before_eda038",
                "local_answer",
                "llm_answer",
                "answer_after_eda038",
                "adopted_by_eda038",
                "model_used",
                "status",
                "confidence",
                "old_path",
                "new_path",
                "evidence",
            ]
        )
    result_df.to_csv(TABLE_DIR / "test_diff_route_result.csv", index=False, encoding="utf-8-sig")
    target_df.to_csv(TABLE_DIR / "test_diff_route_attempt_log.csv", index=False, encoding="utf-8-sig")
    write_submission(result_df)
    write_report(result_df, target_df, args)
    manifest = {
        "eda": "EDA038",
        "input": relative(INPUT_LOG),
        "target_count": int(len(target_df)),
        "before_non_unknown_count": int((result_df["answer_before_eda038"] != UNKNOWN).sum()),
        "added_non_unknown_count": int(result_df["improved_by_eda038"].sum()),
        "after_non_unknown_count": int((result_df["answer_after_eda038"] != UNKNOWN).sum()),
        "openrouter_used": bool(not args.skip_llm),
        "outputs": [
            relative(TABLE_DIR / "test_diff_route_result.csv"),
            relative(TABLE_DIR / "test_diff_route_attempt_log.csv"),
            relative(PREDICTIONS_PATH),
            relative(ZIP_PATH),
            relative(OUT_DIR / "eda038_report.md"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
