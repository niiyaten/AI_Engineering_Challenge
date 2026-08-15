from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import unicodedata
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda007.py は「プロジェクト直下 / EDA / EDA007 / eda007.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
EDA006_DIR = BASE_DIR / "EDA" / "EDA006"
EDA005_DIR = BASE_DIR / "EDA" / "EDA005"

OUTPUT_DIR = Path(__file__).resolve().parent
CONTEXT_DIR = OUTPUT_DIR / "contexts"
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda007_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "eda007.log"

VALID_READINESS_PATH = EDA006_DIR / "tables" / "valid_llm_readiness.csv"
VALID_TOP_SOURCES_PATH = EDA006_DIR / "tables" / "valid_top_sources.csv"
TEST_ANSWER_LOG_PATH = EDA005_DIR / "tables" / "test_answer_log.csv"
TEST_RETRIEVAL_LOG_PATH = EDA005_DIR / "tables" / "test_retrieval_log.csv"

DEFAULT_TOP_K = 5
DEFAULT_MAX_CHARS_PER_EVIDENCE = 1800


# =============================================================================
# 基本ユーティリティ
# =============================================================================


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    logging.captureWarnings(True)
    warnings.simplefilter("always")
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


_HASH_U_PATTERN = re.compile(r"#U([0-9a-fA-F]{4})")


def decode_hash_u_text(text: str) -> str:
    """#U5171 のように展開された日本語パスを通常の日本語へ戻す。"""

    def repl(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return unicodedata.normalize("NFC", _HASH_U_PATTERN.sub(repl, str(text)))


def normalize_text(text: Any) -> str:
    """Markdown出力用にUnicode表記揺れを軽く整える。"""
    return unicodedata.normalize("NFC", decode_hash_u_text(str(text)))


def clean_line(text: Any) -> str:
    """コンテキスト内の1行を読みやすく整える。"""
    text = normalize_text(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", text).strip()


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """Excelでも開きやすいようにUTF-8 BOM付きでCSV保存する。"""
    df.to_csv(path, index=False, encoding="utf-8-sig")


def df_to_markdown(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """tabulateに依存せずDataFrameをMarkdown表に変換する。"""
    if df.empty:
        return "該当データはありません。"
    view = df if max_rows is None else df.head(max_rows)
    columns = [str(col) for col in view.columns]

    def fmt(value: Any) -> str:
        if pd.isna(value):
            text = ""
        else:
            text = str(value)
        return text.replace("\n", " ").replace("\r", " ").replace("|", "\\|")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in view.columns) + " |")
    return "\n".join(lines)


def file_sha1(path: Path) -> str:
    """入力成果物の追跡用にSHA1を計算する。"""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def relative(path: Path) -> str:
    """manifestやレポートでプロジェクト相対パスを表示する。"""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# =============================================================================
# Markdownコンテキスト整形
# =============================================================================


NOISE_PREFIXES = (
    "# source_path:",
    "# file_name:",
    "# extension:",
    "# area:",
    "# project_name:",
    "# major_folder:",
    "# DOCXファイル:",
    "# PPTXファイル:",
    "# XLSXファイル:",
    "# PDFファイル:",
)


def normalize_evidence_text(text: Any, max_chars: int) -> tuple[str, int, int]:
    """検索プレビューをLLMに渡しやすいMarkdown本文へ整形する。"""
    raw = normalize_text(text)
    raw = raw.replace("\\n", "\n")
    raw = re.sub(r"\s*##\s+", "\n\n## ", raw)
    raw = re.sub(r"\s*###\s+", "\n\n### ", raw)
    raw = re.sub(r"\s*row_(\d{3,5}):", r"\nrow_\1:", raw)
    raw = re.sub(r"\s*styles:", "\nstyles:", raw)

    lines: list[str] = []
    removed_noise = 0
    for line in raw.splitlines():
        line = clean_line(line)
        if not line:
            continue
        if any(line.startswith(prefix) for prefix in NOISE_PREFIXES):
            removed_noise += 1
            continue
        if re.fullmatch(r"#+", line):
            removed_noise += 1
            continue
        lines.append(line)

    text_out = "\n".join(lines)
    original_len = len(text_out)
    truncated = 0
    if len(text_out) > max_chars:
        text_out = text_out[:max_chars].rstrip() + "\n...[truncated]"
        truncated = original_len - max_chars
    return text_out, removed_noise, truncated


def context_header(row: pd.Series) -> list[str]:
    """質問・正解・診断情報をMarkdownヘッダーとして整形する。"""
    return [
        f"# valid_{int(row['index']):03d} LLM Context",
        "",
        "## Question",
        str(row["question"]),
        "",
        "## Validation Answer",
        str(row.get("answer", "")),
        "",
        "## Diagnosis",
        f"- required_capability: {row.get('required_capability', '')}",
        f"- context_quality_for_llm: {row.get('context_quality_for_llm', '')}",
        f"- answer_hit_top5: {row.get('answer_hit_top5', '')}",
        f"- recommended_next_step: {row.get('recommended_next_step', '')}",
        "",
        "## Retrieved Evidence",
        "",
    ]


def build_context_for_question(
    diagnosis_row: pd.Series,
    retrieval_df: pd.DataFrame,
    top_k: int,
    max_chars_per_evidence: int,
) -> tuple[str, dict[str, Any]]:
    """1問分のLLM向けMarkdownコンテキストを作る。"""
    q_index = int(diagnosis_row["index"])
    hits = retrieval_df[retrieval_df["index"].astype(int) == q_index].sort_values("rank").head(top_k)
    lines = context_header(diagnosis_row)

    total_chars = 0
    total_noise = 0
    total_truncated = 0
    evidence_count = 0
    source_paths: list[str] = []

    for _, hit in hits.iterrows():
        content, removed_noise, truncated = normalize_evidence_text(hit.get("preview", ""), max_chars_per_evidence)
        if not content:
            continue
        evidence_count += 1
        total_chars += len(content)
        total_noise += removed_noise
        total_truncated += truncated
        source_paths.append(str(hit.get("relative_path", "")))
        lines.extend(
            [
                f"### Evidence {int(hit['rank'])}",
                f"- score: {hit.get('score', '')}",
                f"- source_eda: {hit.get('source_eda', '')}",
                f"- extension: {hit.get('extension', '')}",
                f"- project_name: {hit.get('project_name', '')}",
                f"- major_folder: {hit.get('major_folder', '')}",
                f"- relative_path: {hit.get('relative_path', '')}",
                "",
                "```text",
                content,
                "```",
                "",
            ]
        )

    metadata = {
        "index": q_index,
        "context_file": f"valid_{q_index:03d}_context.md",
        "context_quality_for_llm": diagnosis_row.get("context_quality_for_llm", ""),
        "required_capability": diagnosis_row.get("required_capability", ""),
        "answer_hit_top5": diagnosis_row.get("answer_hit_top5", ""),
        "evidence_count": evidence_count,
        "context_chars": total_chars,
        "removed_noise_lines": total_noise,
        "truncated_chars": total_truncated,
        "source_paths": " || ".join(source_paths),
    }
    return "\n".join(lines), metadata


def build_contexts(
    diagnosis: pd.DataFrame,
    retrieval: pd.DataFrame,
    top_k: int,
    max_chars_per_evidence: int,
) -> pd.DataFrame:
    """valid全問のLLM向けMarkdownコンテキストを生成する。"""
    rows: list[dict[str, Any]] = []
    for _, row in diagnosis.sort_values("index").iterrows():
        markdown, metadata = build_context_for_question(row, retrieval, top_k, max_chars_per_evidence)
        out_path = CONTEXT_DIR / metadata["context_file"]
        out_path.write_text(markdown, encoding="utf-8")
        metadata["context_path"] = relative(out_path)
        rows.append(metadata)
    return pd.DataFrame(rows)


def build_test_contexts_if_available(
    top_k: int,
    max_chars_per_evidence: int,
) -> pd.DataFrame:
    """参考用にtest質問のコンテキストも作る。EDA005ログがない場合は空で返す。"""
    if not TEST_ANSWER_LOG_PATH.exists() or not TEST_RETRIEVAL_LOG_PATH.exists():
        return pd.DataFrame()
    test_answer = pd.read_csv(TEST_ANSWER_LOG_PATH)
    test_retrieval = pd.read_csv(TEST_RETRIEVAL_LOG_PATH)
    out_dir = CONTEXT_DIR / "test"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for _, row in test_answer.sort_values("index").iterrows():
        q_index = int(row["index"])
        hits = test_retrieval[test_retrieval["index"].astype(int) == q_index].sort_values("rank").head(top_k)
        lines = [
            f"# test_{q_index:03d} LLM Context",
            "",
            "## Question",
            str(row["question"]),
            "",
            "## Retrieved Evidence",
            "",
        ]
        context_chars = 0
        for _, hit in hits.iterrows():
            content, _, _ = normalize_evidence_text(hit.get("preview", ""), max_chars_per_evidence)
            if not content:
                continue
            context_chars += len(content)
            lines.extend(
                [
                    f"### Evidence {int(hit['rank'])}",
                    f"- score: {hit.get('score', '')}",
                    f"- source_eda: {hit.get('source_eda', '')}",
                    f"- extension: {hit.get('extension', '')}",
                    f"- relative_path: {hit.get('relative_path', '')}",
                    "",
                    "```text",
                    content,
                    "```",
                    "",
                ]
            )
        context_file = f"test_{q_index:03d}_context.md"
        out_path = out_dir / context_file
        out_path.write_text("\n".join(lines), encoding="utf-8")
        rows.append(
            {
                "index": q_index,
                "context_file": context_file,
                "context_path": relative(out_path),
                "context_chars": context_chars,
                "top1_relative_path": row.get("top1_relative_path", ""),
            }
        )
    return pd.DataFrame(rows)


# =============================================================================
# レポートと追跡情報
# =============================================================================


def write_manifest(args: argparse.Namespace, outputs: dict[str, Path | list[Path]]) -> None:
    """提出用コード化に備え、入力・出力・パラメータを追跡できるmanifestを保存する。"""
    input_paths = [
        VALID_READINESS_PATH,
        VALID_TOP_SOURCES_PATH,
        TEST_ANSWER_LOG_PATH,
        TEST_RETRIEVAL_LOG_PATH,
    ]
    existing_inputs = [path for path in input_paths if path.exists()]
    manifest = {
        "eda": "EDA007",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Create LLM-ready Markdown contexts from EDA006/EDA005 retrieval logs.",
        "parameters": {
            "top_k": args.top_k,
            "max_chars_per_evidence": args.max_chars_per_evidence,
            "build_test_contexts": bool(args.build_test_contexts),
        },
        "inputs": [
            {
                "path": relative(path),
                "sha1": file_sha1(path),
                "bytes": path.stat().st_size,
            }
            for path in existing_inputs
        ],
        "outputs": {
            key: [relative(p) for p in value] if isinstance(value, list) else relative(value)
            for key, value in outputs.items()
        },
        "repro_steps": [
            "uv run python EDA/EDA006/eda006.py",
            "uv run python EDA/EDA007/eda007.py",
        ],
        "notes": [
            "This EDA does not call an LLM API.",
            "Validation answers are included only for context quality diagnosis, not for hard-coded test answering.",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(context_quality: pd.DataFrame, test_contexts: pd.DataFrame, args: argparse.Namespace) -> None:
    """EDA007のMarkdownレポートを生成する。"""
    ready_contexts = int((context_quality["context_quality_for_llm"] == "ready_for_llm").sum())
    total_contexts = len(context_quality)
    mean_chars = float(context_quality["context_chars"].mean()) if total_contexts else 0.0
    quality_counts = (
        context_quality["context_quality_for_llm"]
        .value_counts()
        .rename_axis("context_quality_for_llm")
        .reset_index(name="context_count")
    )
    capability_counts = (
        context_quality["required_capability"]
        .value_counts()
        .rename_axis("required_capability")
        .reset_index(name="context_count")
    )

    lines: list[str] = []
    lines.append("# EDA007: LLM向けMarkdownコンテキスト生成")
    lines.append("")
    lines.append("## 目的・背景")
    lines.append("")
    lines.append(
        "EDA006では、valid 30問について、検索TopKがLLMに渡せる根拠になっているかを診断しました。"
        "その結果、`ready_for_llm` が10件あり、検索根拠はあるものの、EDA005のテンプレ回答では十分に抽出・整形できないことが分かりました。"
    )
    lines.append("")
    lines.append(
        "EDA007では、LLM APIやローカルLLMをまだ呼び出さず、検索根拠をLLMへ渡しやすいMarkdown形式に整形します。"
        "これにより、将来OpenRouterやOllamaなどを導入する場合に、`Question + Retrieved Evidence Markdown -> LLM -> Answer` の形へ差し替えやすくします。"
    )
    lines.append("")
    lines.append(
        "また、最終的にコード提出が必要になるため、入力ファイル、ハッシュ、パラメータ、出力ファイル、再実行手順を `manifest.json` に保存します。"
        "これにより、提出用パイプラインに移す際も、データ作成の流れを追跡できます。"
    )
    lines.append("")
    lines.append("## 手法")
    lines.append("")
    lines.append(f"- 入力: `{relative(VALID_READINESS_PATH)}`")
    lines.append(f"- 入力: `{relative(VALID_TOP_SOURCES_PATH)}`")
    lines.append(f"- valid各問についてTop {args.top_k}件の検索根拠をMarkdown化")
    lines.append(f"- 1根拠あたり最大 {args.max_chars_per_evidence} 文字に制限")
    lines.append("- メタ行や重複しやすいノイズ行を軽く除去")
    lines.append("- LLM呼び出し、外部送信、提出ファイル作成は行わない")
    lines.append("")
    lines.append("## 全体サマリ")
    lines.append("")
    lines.append(f"- validコンテキスト数: {total_contexts}")
    lines.append(f"- ready_for_llmコンテキスト数: {ready_contexts}")
    lines.append(f"- 平均コンテキスト文字数: {mean_chars:.1f}")
    lines.append(f"- manifest: `{relative(MANIFEST_PATH)}`")
    if not test_contexts.empty:
        lines.append(f"- 参考用testコンテキスト数: {len(test_contexts)}")
    lines.append("")
    lines.append("## 文脈品質別コンテキスト数")
    lines.append("")
    lines.append(df_to_markdown(quality_counts))
    lines.append("")
    lines.append("凡例: `context_quality_for_llm` はEDA006のLLM文脈品質分類、`context_count` は生成したMarkdownコンテキスト数を表します。")
    lines.append("")
    lines.append("## 必要能力別コンテキスト数")
    lines.append("")
    lines.append(df_to_markdown(capability_counts))
    lines.append("")
    lines.append("凡例: `required_capability` は質問に答えるために必要そうな汎用能力、`context_count` は生成したMarkdownコンテキスト数を表します。")
    lines.append("")
    lines.append("## コンテキスト品質サンプル")
    lines.append("")
    sample_cols = [
        "index", "context_quality_for_llm", "required_capability", "answer_hit_top5",
        "evidence_count", "context_chars", "removed_noise_lines", "truncated_chars", "context_path",
    ]
    lines.append(df_to_markdown(context_quality[sample_cols].head(30)))
    lines.append("")
    lines.append("凡例: `evidence_count` はMarkdownに含めた根拠数、`context_chars` は根拠本文の文字数、`removed_noise_lines` は除去したメタ行数、`truncated_chars` は文字数上限で切り落とした文字数を表します。")
    lines.append("")
    lines.append("## 考察")
    lines.append("")
    lines.append(
        "EDA007で作成したMarkdownコンテキストは、LLM導入時の入力テンプレートとして使えます。"
        "`ready_for_llm` の問題では、このコンテキストをLLMに渡して短い回答を生成するだけで改善できる可能性があります。"
    )
    lines.append("")
    lines.append(
        "一方で、`needs_table_tool`、`needs_format_extraction`、`needs_image_ocr`、`needs_diff_tool` は、"
        "Markdown整形だけでは根拠が不足する可能性があります。これらは表計算、書式抽出、画像読み取り、差分比較の専用処理と組み合わせる必要があります。"
    )
    lines.append("")
    lines.append("## 次にやること")
    lines.append("")
    lines.append("1. `ready_for_llm` のvalidコンテキストに対して、LLM回答生成を試す。")
    lines.append("2. LLMを使う場合は、モデル名、プロンプト、入力コンテキスト、出力回答をログに保存する。")
    lines.append("3. `needs_table_tool` 向けにCSV/XLSX直接集計処理を作る。")
    lines.append("4. 提出用コード化では、manifestに記録した入力・処理順・出力を再現できるように整理する。")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_eda_summary(context_quality: pd.DataFrame) -> None:
    """EDA総括にEDA007の概要を追記する。"""
    summary_path = BASE_DIR / "EDA" / "eda_summary.md"
    text = summary_path.read_text(encoding="utf-8")
    if "## EDA007の要点" in text:
        return
    marker = "## 現時点の総合判断"
    ready_count = int((context_quality["context_quality_for_llm"] == "ready_for_llm").sum())
    addition = f"""
## EDA007の要点

EDA007では、EDA006のvalid診断と検索TopKログをもとに、LLMへ渡すためのMarkdownコンテキストを生成しました。LLM APIやローカルLLMはまだ呼び出さず、`Question + Retrieved Evidence Markdown` の入力形式を整えることを目的にしています。

valid 30問分のコンテキストを `EDA/EDA007/contexts/` に保存し、そのうち `ready_for_llm` は {ready_count} 件です。将来のコード提出に備え、入力ファイル、SHA1、パラメータ、出力、再実行手順を `EDA/EDA007/manifest.json` に記録しました。

"""
    summary_path.write_text(text.replace(marker, addition + marker), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を読む。"""
    parser = argparse.ArgumentParser(description="EDA007: create LLM-ready Markdown contexts.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--max-chars-per-evidence", type=int, default=DEFAULT_MAX_CHARS_PER_EVIDENCE)
    parser.add_argument("--build-test-contexts", action="store_true", help="Also create test contexts from EDA005 logs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup()

    diagnosis = pd.read_csv(VALID_READINESS_PATH)
    retrieval = pd.read_csv(VALID_TOP_SOURCES_PATH)
    context_quality = build_contexts(
        diagnosis,
        retrieval,
        top_k=args.top_k,
        max_chars_per_evidence=args.max_chars_per_evidence,
    )
    save_csv(context_quality, TABLE_DIR / "context_quality.csv")

    test_contexts = pd.DataFrame()
    if args.build_test_contexts:
        test_contexts = build_test_contexts_if_available(args.top_k, args.max_chars_per_evidence)
        if not test_contexts.empty:
            save_csv(test_contexts, TABLE_DIR / "test_context_quality.csv")

    write_report(context_quality, test_contexts, args)
    write_manifest(
        args,
        outputs={
            "report": REPORT_PATH,
            "manifest": MANIFEST_PATH,
            "context_quality": TABLE_DIR / "context_quality.csv",
            "contexts_dir": CONTEXT_DIR,
        },
    )
    update_eda_summary(context_quality)

    print(f"EDA007 finished: {REPORT_PATH}")
    print(f"contexts: {CONTEXT_DIR}")
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
