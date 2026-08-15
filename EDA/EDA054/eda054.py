from __future__ import annotations

import base64
import csv
import json
import os
import re
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
PRED_DIR = OUT_DIR / "predictions"
RAW_DIR = OUT_DIR / "raw_responses"
PROCESSED = ROOT / "data" / "processed" / "share" / "share" / "共有ドライブ"
BASE_PRED = ROOT / "EDA" / "EDA053" / "predictions" / "eda053_safe_unknown_reduction_predictions.csv"
DIAGNOSIS = ROOT / "EDA" / "EDA048" / "tables" / "remaining_unknown_diagnosis.csv"


TARGET_INDICES = [33, 38, 44, 46, 49, 52, 58, 62, 75, 79, 80, 83, 95, 96]


@dataclass
class Candidate:
    index: int
    route: str
    candidate_answer: str
    evidence: str
    source_paths: list[str]
    confidence: str
    needs_review: bool
    llm_answer: str = ""
    adopted_answer: str = ""
    adopted: bool = False


def norm(value: object) -> str:
    """検索・比較を安定させるために、Unicode表記と改行をそろえる。"""
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compact(value: object, limit: int = 1200) -> str:
    """LLMやCSVに載せやすいよう、空白を詰めた短い根拠文にする。"""
    text = re.sub(r"\s+", " ", norm(value)).strip()
    return text[:limit]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def read_text(path: Path) -> str:
    return norm(path.read_text(encoding="utf-8", errors="ignore"))


def find_files(*keywords: str, suffix: str | None = None) -> list[Path]:
    """processed/shareから、全キーワードを含むファイルを探す。"""
    hits: list[Path] = []
    for path in PROCESSED.rglob("*"):
        if not path.is_file():
            continue
        path_text = norm(path).replace("\\", "/")
        if suffix and not path_text.endswith(suffix):
            continue
        if all(norm(keyword) in path_text for keyword in keywords):
            hits.append(path)
    return sorted(hits, key=lambda p: norm(p))


def load_api_key() -> str:
    """プロジェクト直下の.apikeyからOpenRouterのキーだけを読む。"""
    api_path = ROOT / ".apikey"
    if not api_path.exists():
        return ""
    for line in api_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key_name = line.split("=", 1)[0].strip().lower() if "=" in line else ""
        if key_name in {"openrouter_api_key", "openrouter"}:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def openrouter_short_answer(question: str, candidate: Candidate, api_key: str) -> tuple[str, dict[str, Any]]:
    """長い候補を最終回答だけへ短答化する。失敗時は空文字を返す。"""
    if not api_key or not candidate.candidate_answer:
        return "", {"skipped": True, "reason": "missing_api_key_or_candidate"}
    prompt = (
        "次の質問に対し、根拠候補だけを使って日本語で最終回答だけを返してください。\n"
        "説明、引用符、前置き、HTMLタグは不要です。根拠が足りない場合は「わかりません」と返してください。\n\n"
        f"質問: {question}\n\n"
        f"回答候補: {candidate.candidate_answer}\n\n"
        f"根拠: {candidate.evidence[:5000]}"
    )
    payload = {
        "model": "openai/gpt-oss-20b:free",
        "messages": [{"role": "user", "content": prompt}],
        "reasoning": {"enabled": True},
        "max_tokens": 700,
        "temperature": 0,
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=180,
    )
    data = response.json()
    data["_http_status"] = response.status_code
    if response.status_code != 200:
        return "", data
    message = (data.get("choices") or [{}])[0].get("message") or {}
    answer = norm(message.get("content") or "").strip()
    return answer, data


def make_candidate(index: int, route: str, answer: str, evidence: str, sources: list[Path | str], confidence: str, needs_review: bool) -> Candidate:
    source_paths = [rel(s) if isinstance(s, Path) else norm(s) for s in sources]
    return Candidate(index, route, norm(answer).strip(), compact(evidence, 5000), source_paths, confidence, needs_review)


def context_lines(paths: list[Path], keywords: list[str], width: int = 1) -> tuple[str, list[str]]:
    """キーワード周辺行だけを集め、長文文書から質問に関係する部分を切り出す。"""
    snippets: list[str] = []
    used: list[str] = []
    for path in paths:
        lines = read_text(path).splitlines()
        hit_indices = [i for i, line in enumerate(lines) if any(k in norm(line) for k in keywords)]
        if not hit_indices:
            continue
        used.append(rel(path))
        for i in hit_indices[:8]:
            start = max(0, i - width)
            end = min(len(lines), i + width + 1)
            snippets.append(f"[{rel(path)}:{i + 1}]\n" + "\n".join(lines[start:end]))
    return "\n\n".join(snippets), used


def candidate_49_comment() -> Candidate:
    paths = find_files("東都人材プラットフォーム", "05.会議", "会議録", suffix=".docx.structure.json")
    comments: list[str] = []
    evidence: list[str] = []
    for path in paths:
        obj = json.loads(path.read_text(encoding="utf-8"))
        for block in obj.get("blocks", []):
            block_text = norm(block.get("text") or block.get("markdown") or "")
            if "コメント" in block_text or "comment" in block_text.lower():
                comments.append(block_text)
                evidence.append(f"{rel(path)} block={block.get('block_index')}: {block_text}")
            for run in block.get("runs", []):
                run_text = norm(run.get("text", ""))
                if "コメント" in run_text or "comment" in run_text.lower():
                    comments.append(run_text)
                    evidence.append(f"{rel(path)} block={block.get('block_index')}: {run_text}")
    answer = " / ".join(dict.fromkeys(compact(x, 300) for x in comments if x))
    return make_candidate(49, "meeting_comment_extraction", answer, "\n".join(evidence), paths, "medium" if answer else "none", not bool(answer))


def candidate_52_clause() -> Candidate:
    paths = find_files("みなみ野女性医療センター", "提案書.pptx", suffix=".md") + find_files("みなみ野女性医療センター", "契約書.docx", suffix=".md")
    evidence, used = context_lines(paths, ["別契約", "今後の運用", "運用", "データアステル"], width=2)
    # 根拠は節単位でLLMに短答化させるため、候補には関連行をそのまま入れる。
    return make_candidate(52, "proposal_operation_clause_lookup", evidence, evidence, used, "medium" if evidence else "none", not bool(evidence))


def candidate_75_plan_week() -> Candidate:
    schedule_paths = find_files("みなみ野女性医療センター", "スケジュール.xlsx.sheets", "スケジュール管理表.csv")
    if schedule_paths:
        df = pd.read_csv(schedule_paths[0], dtype=str).fillna("")
        hit = df[df.apply(lambda r: "モデル構築" in " ".join(r.astype(str).tolist()), axis=1)]
        if not hit.empty:
            # 契約開始日2025-04-03を第1週起点として、モデル構築フェーズの開始週を答える。
            start = pd.to_datetime(hit.iloc[0]["開始日"])
            week = ((start - pd.Timestamp("2025-04-03")).days // 7) + 1
            evidence = hit.to_csv(index=False)
            return make_candidate(75, "proposal_plan_week_lookup", f"第{week}週", evidence, schedule_paths, "high", False)
    paths = find_files("みなみ野女性医療センター", "提案書.pptx", suffix=".md") + find_files("みなみ野女性医療センター", "スケジュール.xlsx", suffix=".md")
    evidence, used = context_lines(paths, ["モデル構築", "PL案", "週", "第"], width=3)
    return make_candidate(75, "proposal_plan_week_lookup", evidence, evidence, used, "low" if evidence else "none", True)


def candidate_80_yellow_sheet() -> Candidate:
    paths = find_files("東都人材プラットフォーム", "train.xlsx.structure.json")
    evidence_parts: list[str] = []
    answer_parts: list[str] = []
    for path in paths:
        obj = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(obj, ensure_ascii=False)
        for m in re.finditer(r"[^{}]{0,220}(?:FFFF00|黄色|yellow|highlight)[^{}]{0,500}", text, flags=re.I):
            chunk = compact(m.group(0), 700)
            evidence_parts.append(f"{rel(path)}: {chunk}")
            answer_parts.append(chunk)
    answer = "\n".join(answer_parts[:4])
    return make_candidate(80, "spreadsheet_format_semantic_context", answer, "\n".join(evidence_parts[:8]), paths, "low" if answer else "none", True)


def candidate_96_checkpoint() -> Candidate:
    path = ROOT / "EDA" / "EDA050" / "tables" / "checkpoint_task_inventory.csv"
    if not path.exists():
        return make_candidate(96, "checkpoint_task_lookup", "", "", [], "none", True)
    df = pd.read_csv(path, dtype=str).fillna("")
    hit = df[df["project"].str.contains("青葉与信", na=False) & (df["checkpoint_ids"].str.contains("CP2", na=False) | df["text"].str.contains("チェックポイント2|MS2", na=False))]
    task_ids = sorted(set(re.findall(r"\bT\d{2}\b", " ".join(hit["task_ids"].tolist() + hit["text"].tolist())))) if not hit.empty else []
    schedule_paths = find_files("青葉与信マネジメント", "スケジュール.xlsx.sheets", "Sheet2.csv")
    if not task_ids and schedule_paths:
        ms_df = pd.read_csv(schedule_paths[0], dtype=str).fillna("")
        ms2 = ms_df[ms_df.apply(lambda r: "MS2" in " ".join(r.astype(str).tolist()) or "データ理解完了" in " ".join(r.astype(str).tolist()), axis=1)]
        task_ids = sorted(set(re.findall(r"\bT\d{2}\b", " ".join(ms2.astype(str).agg(" ".join, axis=1).tolist()))))
        if any("T05～T08" in text or "T05~T08" in text for text in ms2.astype(str).agg(" ".join, axis=1).tolist()):
            task_ids = ["T05", "T06", "T07", "T08"]
        evidence = ms2.to_csv(index=False)
        return make_candidate(96, "checkpoint_task_lookup", "、".join(task_ids), evidence, [path] + schedule_paths, "high" if task_ids else "none", not bool(task_ids))
    if hit.empty:
        return make_candidate(96, "checkpoint_task_lookup", "", "", [path], "none", True)
    evidence = "\n".join(hit["text"].head(5).tolist())
    return make_candidate(96, "checkpoint_task_lookup", "、".join(task_ids), evidence, [path], "high", False)


def candidate_38_apr() -> Candidate:
    project_path = ROOT / "EDA" / "EDA051" / "tables" / "project_master_aggregation.csv"
    if not project_path.exists():
        return make_candidate(38, "cross_project_contract_aggregation", "", "", [], "none", True)
    df = pd.read_csv(project_path, dtype=str).fillna("")
    hit = df[df["approval_level"].eq("本部長承認")]
    if hit.empty:
        return make_candidate(38, "cross_project_contract_aggregation", "", "APR-M3相当の本部長承認案件なし", [project_path], "none", True)
    total = pd.to_numeric(hit["contract_amount_tax_in"], errors="coerce").fillna(0).astype(int).sum()
    names = hit["project"].tolist()
    answer = f"{'、'.join(names)}、合計{total:,}円"
    evidence = hit[["project", "contract_type", "contract_amount_tax_in", "is_medical", "approval_level"]].to_csv(index=False)
    return make_candidate(38, "cross_project_contract_aggregation", answer, evidence, [project_path], "medium", True)


def candidate_46_es_ext() -> Candidate:
    project_path = ROOT / "EDA" / "EDA051" / "tables" / "project_master_aggregation.csv"
    role_path = ROOT / "EDA" / "EDA051" / "tables" / "role_assignment_inventory.csv"
    seat_path = ROOT / "EDA" / "EDA049" / "tables" / "seat_coordinate_table.csv"
    evidence_parts: list[str] = []
    answer = ""
    if project_path.exists():
        df = pd.read_csv(project_path, dtype=str).fillna("")
        df["upfront_num"] = pd.to_numeric(df["upfront_amount"], errors="coerce")
        top = df.dropna(subset=["upfront_num"]).sort_values("upfront_num", ascending=False).head(1)
        if not top.empty:
            project = top.iloc[0]["project"]
            evidence_parts.append(f"max_upfront_project={project}, upfront={top.iloc[0]['upfront_amount']}")
            if role_path.exists():
                roles = pd.read_csv(role_path, dtype=str).fillna("")
                role_hit = roles[roles["project"].eq(project) & roles["role"].str.contains("エグゼクティブスポンサー|ES", na=False)]
                evidence_parts.append(role_hit.to_csv(index=False))
                if not role_hit.empty and seat_path.exists():
                    name = role_hit.iloc[0]["name"].replace(" ", "")
                    seats = pd.read_csv(seat_path, dtype=str).fillna("")
                    seat_hit = seats[seats.apply(lambda r: name in (r.astype(str).str.cat(sep=" ")).replace(" ", ""), axis=1)]
                    evidence_parts.append(seat_hit.to_csv(index=False))
                    for col in ["ext", "EXT", "extension", "内線"]:
                        if col in seat_hit.columns and not seat_hit.empty:
                            answer = str(seat_hit.iloc[0][col])
                            break
    return make_candidate(46, "contract_alias_contact_lookup", answer, "\n".join(evidence_parts), [project_path, role_path, seat_path], "low" if answer else "none", True)


def candidate_79_kaede_hours() -> Candidate:
    resource_path = ROOT / "EDA" / "EDA051" / "tables" / "schedule_resource_inventory.csv"
    if not resource_path.exists():
        return make_candidate(79, "kaede_resource_hour_lookup", "", "", [], "none", True)
    df = pd.read_csv(resource_path, dtype=str).fillna("")
    hit = df[df["project"].str.contains("かえで|恒一会", na=False)]
    # 鍵付き計画表が未抽出の場合は、契約書や提案書から工数だけ拾っても担当タスク数が不明なので採用しない。
    if hit.empty:
        evidence = "かえで総合病院の計画フォルダ由来のschedule_resource行が0件。鍵付き計画ファイルが未抽出の可能性が高い。"
        return make_candidate(79, "kaede_resource_hour_lookup", "", evidence, [resource_path], "none", True)
    return make_candidate(79, "kaede_resource_hour_lookup", "", hit.head(20).to_csv(index=False), [resource_path], "low", True)


def candidate_95_schedule_diff() -> Candidate:
    r1_paths = find_files("青嶺不動産", "スケジュール_r1.xlsx.sheets", "スケジュール.csv")
    r2_paths = find_files("青嶺不動産", "スケジュール_r2.xlsx.sheets", "スケジュール.csv")
    if not r1_paths or not r2_paths:
        return make_candidate(95, "structured_diff_semantic_filter", "", "", r1_paths + r2_paths, "none", True)
    old = pd.read_csv(r1_paths[0], dtype=str).fillna("")
    new = pd.read_csv(r2_paths[0], dtype=str).fillna("")
    key_col = "タスクID" if "タスクID" in old.columns else old.columns[0]
    # タスクIDが重複しているシートでも止まらないよう、同じIDは先頭行を代表として比較する。
    old_map = old.drop_duplicates(subset=[key_col], keep="first").set_index(key_col).to_dict("index")
    changes: list[str] = []
    for _, row in new.iterrows():
        task_id = str(row.get(key_col, ""))
        if task_id not in old_map:
            continue
        before = old_map[task_id]
        after = row.to_dict()
        if str(before.get("ステータス", "")) == "未着手" and str(after.get("ステータス", "")) == "完了":
            continue
        diffs = []
        for col in new.columns:
            b = norm(before.get(col, "")).strip()
            a = norm(after.get(col, "")).strip()
            if b != a and col not in {"No.", "ステータス"}:
                diffs.append(f"{col}: {b} -> {a}")
        if diffs:
            changes.append(f"{task_id} {after.get('タスク名', '')}: " + "; ".join(diffs))
    answer = " / ".join(changes[:8])
    evidence = "\n".join(changes)
    return make_candidate(95, "structured_diff_semantic_filter", answer, evidence, r1_paths + r2_paths, "medium" if answer else "none", not bool(answer))


def candidate_62_model_diff() -> Candidate:
    paths = find_files("青葉与信マネジメント", "最終報告", suffix=".md") + find_files("青葉与信マネジメント", "metrics", suffix=".json") + find_files("青葉与信マネジメント", "leaderboard", suffix=".md")
    evidence, used = context_lines(paths, ["上位", "差分", "モデル比較", "score", "F1", "設定", "best"], width=3)
    return make_candidate(62, "model_comparison_setting_diff", evidence, evidence, used, "low" if evidence else "none", True)


def candidate_83_formula() -> Candidate:
    paths = find_files("みなみ野女性医療センター", "train.xlsx", suffix=".md") + find_files("みなみ野女性医療センター", "run_train.py", suffix=".md")
    evidence, used = context_lines(paths, ["係数", "coef", "intercept", "1770", "回帰分析", "Prediction"], width=3)
    return make_candidate(83, "model_formula_recompute", evidence, evidence, used, "low" if evidence else "none", True)


def candidate_33_chart() -> Candidate:
    paths = find_files("青潮モビリティサービス", "基礎分析", suffix=".docx.structure.json") + find_files("青潮モビリティサービス", "基礎分析", suffix=".md")
    evidence, used = context_lines(paths, ["グラフ2", "青色", "x=3", "x = 3", "折れ線"], width=5)
    return make_candidate(33, "chart_value_extraction", evidence, evidence, used, "low" if evidence else "none", True)


def build_candidates() -> list[Candidate]:
    return [
        candidate_33_chart(),
        candidate_38_apr(),
        candidate_46_es_ext(),
        candidate_49_comment(),
        candidate_52_clause(),
        candidate_62_model_diff(),
        candidate_75_plan_week(),
        candidate_79_kaede_hours(),
        candidate_80_yellow_sheet(),
        candidate_83_formula(),
        candidate_95_schedule_diff(),
        candidate_96_checkpoint(),
    ]


def load_questions() -> dict[int, str]:
    df = pd.read_csv(DIAGNOSIS, dtype=str).fillna("")
    return {int(row["index"]): row["question"] for _, row in df.iterrows() if str(row["index"]).isdigit()}


def should_ask_llm(candidate: Candidate) -> bool:
    """候補が長文または低/中信頼の場合だけLLM短答化を使う。"""
    if not candidate.candidate_answer or candidate.confidence == "none":
        return False
    if candidate.index in {49, 52, 62, 75, 80, 83, 95}:
        return True
    return len(candidate.candidate_answer) > 120


def final_answer(candidate: Candidate) -> str:
    if should_ask_llm(candidate) and not candidate.llm_answer:
        return ""
    answer = norm(candidate.llm_answer or candidate.candidate_answer).strip()
    answer = re.sub(r"<[^>]+>", "", answer).strip()
    if not answer or "わかりません" in answer or "情報が不足" in answer:
        return ""
    return answer


def apply_candidates(candidates: list[Candidate]) -> pd.DataFrame:
    pred = pd.read_csv(BASE_PRED, header=None, names=["index", "answer"], dtype={0: int, 1: str}).fillna("")
    answers = pred.set_index("index")["answer"].to_dict()
    rows = []
    for cand in candidates:
        answer = final_answer(cand)
        # 高信頼でレビュー不要のものだけ提出候補に採用する。
        cand.adopted = bool(answer and not cand.needs_review and cand.confidence in {"high", "medium"})
        cand.adopted_answer = answer if cand.adopted else ""
        if cand.adopted:
            answers[cand.index] = answer
        rows.append(cand.__dict__)
    out = pd.DataFrame({"index": sorted(answers), "answer": [answers[i] for i in sorted(answers)]})
    out_path = PRED_DIR / "eda054_remaining_unknown_submission_predictions.csv"
    zip_path = PRED_DIR / "eda054_remaining_unknown_submission.zip"
    out.to_csv(out_path, index=False, header=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_path, arcname="predictions.csv")
    return pd.DataFrame(rows)


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    questions = load_questions()
    candidates = build_candidates()
    api_key = load_api_key()
    attempt_rows = []
    for cand in candidates:
        if should_ask_llm(cand):
            answer, raw = openrouter_short_answer(questions.get(cand.index, ""), cand, api_key)
            cand.llm_answer = answer
            raw_path = RAW_DIR / f"index_{cand.index:03d}.json"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            attempt_rows.append({"index": cand.index, "http_status": raw.get("_http_status", ""), "llm_answer": answer, "raw_path": rel(raw_path)})
            time.sleep(1)
        else:
            attempt_rows.append({"index": cand.index, "http_status": "skipped", "llm_answer": "", "raw_path": ""})

    result_df = apply_candidates(candidates)
    result_df.to_csv(TABLE_DIR / "eda054_candidate_answers.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(attempt_rows).to_csv(TABLE_DIR / "eda054_openrouter_attempts.csv", index=False, encoding="utf-8-sig")

    base_unknown = pd.read_csv(BASE_PRED, header=None, names=["index", "answer"], dtype=str).query("answer == 'わかりません'").shape[0]
    pred_path = PRED_DIR / "eda054_remaining_unknown_submission_predictions.csv"
    new_unknown = pd.read_csv(pred_path, header=None, names=["index", "answer"], dtype=str).query("answer == 'わかりません'").shape[0]
    adopted_count = int(result_df["adopted"].sum()) if not result_df.empty else 0
    report = f"""# EDA054: 残り `わかりません` の追加候補化

## 背景と目的

EDA053 safe版で残った `わかりません` 14件を対象に、既存の前処理成果から追加で採用できる回答を探す。
OpenRouterは、長い候補の短答化に限定して使う。

## 方針

- EDA053 safe版をベースにする。
- ローカルで根拠候補を作る。
- 長文候補はOpenRouter `openai/gpt-oss-20b:free` で最終回答へ短答化する。
- 提出候補へ採用するのは、`needs_review=False` かつ `confidence` が `high` または `medium` のものだけにする。

## 結果

- EDA053 safe版の `わかりません`: {base_unknown}
- EDA054後の `わかりません`: {new_unknown}
- 追加採用: {adopted_count}

## 出力

- 候補ログ: `EDA/EDA054/tables/eda054_candidate_answers.csv`
- OpenRouter試行ログ: `EDA/EDA054/tables/eda054_openrouter_attempts.csv`
- 提出候補zip: `EDA/EDA054/predictions/eda054_remaining_unknown_submission.zip`

## 注意

横断集計、座席表、モデル再計算、Excel黄色セルの候補は、根拠がまだ弱いものは採用しない。
"""
    (OUT_DIR / "eda054_report.md").write_text(report, encoding="utf-8")
    manifest = {
        "eda": "EDA054",
        "base_unknown": int(base_unknown),
        "new_unknown": int(new_unknown),
        "adopted_count": adopted_count,
        "submission_zip": "EDA/EDA054/predictions/eda054_remaining_unknown_submission.zip",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
