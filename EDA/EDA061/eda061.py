from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
from docx import Document


ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "share" / "share"
PROCESSED_ROOT = ROOT / "data" / "processed" / "share" / "share"
QUESTIONS_RAW = next(RAW_ROOT.rglob("questions_test.csv"))
PROCESSED_DIR = PROCESSED_ROOT / "質問回答"
OUTPUT_CSV = PROCESSED_DIR / "questions_test_expanded.csv"
EDA_DIR = ROOT / "EDA" / "EDA061"
REPLACEMENT_CSV = EDA_DIR / "abbreviation_replacement_log.csv"
REPORT_MD = EDA_DIR / "eda061_report.md"
GLOSSARY_DIR = next(p.parent for p in RAW_ROOT.rglob("*.md") if p.stat().st_size == 2090)


def find_management_doc(keyword: str) -> Path:
    """Unicode表記の揺れを吸収して社内管理Word文書を探す。"""
    for path in GLOSSARY_DIR.glob("*.docx"):
        normalized = unicodedata.normalize("NFC", path.name)
        if keyword in normalized:
            return path
    raise FileNotFoundError(f"社内管理文書が見つかりません: {keyword}")


def read_glossary() -> tuple[dict[str, str], Path, Path]:
    """社内用語集の全表から、正式名称と略語の対応を読み取る。"""
    glossary_path = find_management_doc("社内用語集")
    password_rule_path = find_management_doc("パスワード導出規則")
    mapping: dict[str, str] = {}
    document = Document(glossary_path)
    for table in document.tables:
        if not table.rows or len(table.rows[0].cells) < 2:
            continue
        headers = [unicodedata.normalize("NFC", cell.text.strip()) for cell in table.rows[0].cells]
        if headers[:2] == ["正式名称", "社内用語"]:
            for row in table.rows[1:]:
                formal = unicodedata.normalize("NFC", row.cells[0].text.strip())
                short = unicodedata.normalize("NFC", row.cells[1].text.strip())
                if formal and short:
                    mapping[short] = formal
        elif headers[:2] == ["案件名", "主略称"]:
            for row in table.rows[1:]:
                formal = unicodedata.normalize("NFC", row.cells[0].text.strip())
                primary = unicodedata.normalize("NFC", row.cells[1].text.strip())
                aliases = unicodedata.normalize("NFC", row.cells[2].text.strip()) if len(row.cells) > 2 else ""
                if formal and primary:
                    # 完全な正式名称を保護し、正式名称の内部に含まれる別名を二重展開しない。
                    mapping[formal] = formal
                    mapping[primary] = formal
                    variants = [formal]
                    if formal.startswith("株式会社"):
                        variants.append(formal.removeprefix("株式会社"))
                    if formal.endswith("株式会社"):
                        variants.append(formal.removesuffix("株式会社"))
                    if formal.startswith("医療法人社団 "):
                        variants.append(formal.removeprefix("医療法人社団 "))
                    for variant in variants:
                        if variant:
                            mapping[variant] = formal
                for alias in re.split(r"[,、、]\s*", aliases):
                    alias = alias.strip()
                    if formal and alias:
                        mapping[alias] = formal
    return mapping, glossary_path, password_rule_path


def compile_replacer(mapping: dict[str, str]) -> re.Pattern[str]:
    """長い略語を先に評価し、英数字の一部だけを誤置換しない正規表現を作る。"""
    tokens = sorted((token for token in mapping if token not in {"B", "U", "I"}), key=len, reverse=True)
    alternatives = "|".join(re.escape(token) for token in tokens)
    # アンダースコアはファイル名の区切りとして正式名称の直後に現れるため、境界判定から除外する。
    return re.compile(rf"(?<![A-Za-z0-9])(?P<token>{alternatives})(?P<suffix>書)?(?![A-Za-z0-9])")


def compile_style_replacer(mapping: dict[str, str]) -> re.Pattern[str]:
    """B/U/IはフェーズBなどの通常表記を壊さないよう単独文字だけに限定する。"""
    return re.compile(r"(?<![A-Za-z0-9_一-龯ぁ-んァ-ヶ])(?P<style_token>B|U|I)(?![A-Za-z0-9_一-龯ぁ-んァ-ヶ])")


def expand_question(
    question: str,
    replacer: re.Pattern[str],
    style_replacer: re.Pattern[str],
    mapping: dict[str, str],
) -> tuple[str, list[tuple[str, str]]]:
    replacements: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group("token")
        replacement = mapping[token]
        if token != replacement:
            replacements.append((token, replacement))
        return replacement

    def replace_style(match: re.Match[str]) -> str:
        token = match.group("style_token")
        replacement = mapping[token]
        if token != replacement:
            replacements.append((token, replacement))
        return replacement

    expanded = replacer.sub(replace, question)
    return style_replacer.sub(replace_style, expanded), replacements


def build_replacement_log(rows: list[dict[str, object]]) -> pd.DataFrame:
    """質問ごとの置換内容を監査用CSVにまとめる。"""
    return pd.DataFrame(rows, columns=["index", "token", "replacement", "count"])


def build_report(
    questions: pd.DataFrame,
    expanded: pd.DataFrame,
    replacement_log: pd.DataFrame,
    glossary_path: Path,
    password_rule_path: Path,
) -> str:
    lines = [
        "# EDA061 質問文の社内略語展開",
        "",
        "## 目的",
        "",
        "社内用語集に基づき、test質問文に含まれる社内略語を正式名称へ展開した。rawの質問CSVは変更せず、処理済みCSVを `data/processed` に保存した。",
        "",
        "## 使用した社内管理資料",
        "",
        f"- 略語辞書: `{glossary_path.relative_to(ROOT)}`",
        f"- パスワード導出規則: `{password_rule_path.relative_to(ROOT)}`",
        "",
        "パスワード導出規則は `DA-[案件略号]-[契約開始日YYYYMMDD]-[拡張子コード]` 形式である。今回の質問文展開ではパスワード付きファイルを直接読み直していないが、かえで総合病院のExcelについては同規則に基づく `DA-KAEDE-20250902-xlsx` のパスワードファイルがraw内に存在することを確認した。",
        "",
        "## 出力",
        "",
        f"- 入力: `{QUESTIONS_RAW.relative_to(ROOT)}`",
        f"- 展開後test CSV: `{OUTPUT_CSV.relative_to(ROOT)}`",
        f"- 置換ログ: `{REPLACEMENT_CSV.relative_to(ROOT)}`",
        "",
        "凡例: 展開後CSVの `question` が正式名称へ展開した質問文、`index` は元質問IDを表す。置換ログの `token` は略語、`replacement` は正式名称、`count` は質問単位の置換回数である。",
        "",
        "## 件数",
        "",
        f"- 質問数: {len(questions)}",
        f"- 略語が1つ以上展開された質問数: {int((expanded['question'] != questions['question']).sum())}",
        f"- 置換総数: {int(replacement_log['count'].sum()) if not replacement_log.empty else 0}",
        f"- 使用した略語数: {replacement_log['token'].nunique() if not replacement_log.empty else 0}",
        "",
        "## 略語別の展開件数",
        "",
    ]
    if replacement_log.empty:
        lines.append("略語の置換はありませんでした。")
    else:
        summary = (
            replacement_log.groupby(["token", "replacement"], as_index=False)["count"]
            .sum()
            .sort_values("count", ascending=False)
        )
        lines.extend(summary.to_markdown(index=False).splitlines())
    lines.extend(["", "凡例: 表の各行は略語と正式名称の対応、`count` は全test質問での展開回数を表す。"])
    return "\n".join(lines) + "\n"


def main() -> None:
    mapping, glossary_path, password_rule_path = read_glossary()
    replacer = compile_replacer(mapping)
    style_replacer = compile_style_replacer(mapping)
    questions = pd.read_csv(QUESTIONS_RAW, encoding="utf-8-sig")
    expanded = questions.copy()
    replacement_rows: list[dict[str, object]] = []
    for idx, question in questions["question"].items():
        expanded_question, replacements = expand_question(str(question), replacer, style_replacer, mapping)
        expanded.at[idx, "question"] = expanded_question
        counts: dict[tuple[str, str], int] = {}
        for token, replacement in replacements:
            counts[(token, replacement)] = counts.get((token, replacement), 0) + 1
        for (token, replacement), count in counts.items():
            replacement_rows.append({"index": int(questions.at[idx, "index"]), "token": token, "replacement": replacement, "count": count})
    replacement_log = build_replacement_log(replacement_rows)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    EDA_DIR.mkdir(parents=True, exist_ok=True)
    expanded.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    replacement_log.to_csv(REPLACEMENT_CSV, index=False, encoding="utf-8-sig")
    REPORT_MD.write_text(build_report(questions, expanded, replacement_log, glossary_path, password_rule_path), encoding="utf-8")
    manifest = {
        "eda": "EDA061",
        "input_csv": str(QUESTIONS_RAW.relative_to(ROOT)),
        "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
        "replacement_log": str(REPLACEMENT_CSV.relative_to(ROOT)),
        "report": str(REPORT_MD.relative_to(ROOT)),
        "question_count": int(len(expanded)),
        "expanded_question_count": int((expanded["question"] != questions["question"]).sum()),
        "replacement_count": int(replacement_log["count"].sum()) if not replacement_log.empty else 0,
    }
    (EDA_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
