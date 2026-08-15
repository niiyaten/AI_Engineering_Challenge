from __future__ import annotations

import logging
import re
import unicodedata
import warnings
from collections.abc import Iterable
from pathlib import Path

import matplotlib

# GUIがない環境でも画像保存できるようにする。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

# =============================================================================
# パス設定
# =============================================================================

# eda001.py は「プロジェクト直下 / EDA / EDA001 / eda001.py」に置く前提。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_PATH = OUTPUT_DIR / "eda001_report.md"
LOG_PATH = OUTPUT_DIR / "eda001.log"

# zipを展開済みの場合に優先して探す場所。
# 例:
#   data/raw/share/共有ドライブ
#   data/raw/share/share/共有ドライブ
#   data/interim/share/share/共有ドライブ
DATASET_SEARCH_BASES = [
    RAW_DIR,
    INTERIM_DIR,
    DATA_DIR,
    BASE_DIR,
]

# ファイル探索時に除外するフォルダ。
# .venvを巻き込むと非常に遅くなるため、明示的に除外する。
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
}

# 質問文に含まれるキーワードから、どんな処理が必要そうかを粗く分類する。
QUESTION_PATTERNS = {
    "差分比較": ["old", "旧版", "最新版", "比較", "更新内容", "差異", "差分", "変更"],
    "Excel/表": ["xlsx", "Excel", "シート", "セル", "行", "列", "Pivot", "ピボット", "ハイライト", "表"],
    "Word/PPT書式": ["太字", "下線", "赤字", "黄色", "マーカー", "pptx", "docx", "スライド", "強調"],
    "PDF/会議録": ["pdf", "会議録", "議事録"],
    "コード/Notebook": ["py", "ipynb", "notebook", "Notebook", "コード", "modeling.py", "関数"],
    "JSON/設定": ["json", "設定", "パラメータ", "selected_columns", "metrics", "config"],
    "金額/計算": ["金額", "税込", "税抜", "差額", "合計", "平均", "小数", "丸め", "何円", "比率", "割合"],
    "日付/期間": ["日付", "期間", "開始", "終了", "何日", "月", "週", "年度", "四半期"],
    "画像/グラフ": ["png", "画像", "グラフ", "figure", "ヒストグラム", "プロット", "図", "チャート"],
    "社内用語": ["略称", "社内用語", "用語集", "正式名称"],
    "複数資料照合": ["あわせて", "それぞれ", "すべて", "複数", "各", "一覧", "抜き出"],
}


# =============================================================================
# 基本ユーティリティ
# =============================================================================


def setup() -> None:
    """出力フォルダとログ設定を準備する。"""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    logging.captureWarnings(True)
    warnings.simplefilter("always")
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )

    # 日本語フォントは環境差があるため、候補を複数指定する。
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


_HASH_U_PATTERN = re.compile(r"#U([0-9a-fA-F]{4})")


def decode_hash_u_text(text: str) -> str:
    """#U5171 のように展開された日本語パスを通常の日本語へ戻す。

    一部のunzip方法では、日本語フォルダ名が `#U5171#U6709...` のような表記で
    展開されることがある。EDAでは表示・分類しやすいように可能な範囲で復元する。
    """

    def repl(match: re.Match[str]) -> str:
        code_point = int(match.group(1), 16)
        return chr(code_point)

    decoded = _HASH_U_PATTERN.sub(repl, str(text))
    return unicodedata.normalize("NFC", decoded)


def normalize_path_text(text: str) -> str:
    """日本語ファイル名の濁点揺れを抑えるため、NFCに正規化する。"""
    return decode_hash_u_text(text)


def path_display(path: Path) -> str:
    """画面表示・CSV保存向けに、パスをスラッシュ区切りの文字列へ変換する。"""
    return normalize_path_text(path.as_posix())


def is_excluded_path(path: Path) -> bool:
    """探索対象から除外すべきフォルダ配下かどうかを判定する。"""
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def iter_files(root: Path) -> Iterable[Path]:
    """root配下のファイルを再帰的に列挙する。"""
    for path in root.rglob("*"):
        if is_excluded_path(path):
            continue
        if path.is_file() and path.name != ".extracted":
            yield path


def iter_dirs(root: Path) -> Iterable[Path]:
    """root配下のフォルダを再帰的に列挙する。"""
    if not root.exists():
        return
    for path in root.rglob("*"):
        if is_excluded_path(path):
            continue
        if path.is_dir():
            yield path


def safe_relative_to(path: Path, base: Path) -> str:
    """baseからの相対パスを返す。外側にある場合は絶対パスを返す。"""
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def df_to_markdown(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """pandasのto_markdownに頼らず、簡易Markdown表を作る。

    `to_markdown` は tabulate が必要になるため、依存を増やさない目的で自前実装する。
    """
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "該当データなし"

    cols = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(map(str, cols)) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, row in df.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if pd.isna(value):
                text = ""
            else:
                text = str(value)
            text = text.replace("\n", " ").replace("|", "\\|")
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


# =============================================================================
# データ場所の自動検出
# =============================================================================


def find_named_dirs(search_bases: list[Path], decoded_name: str) -> list[Path]:
    """指定した日本語フォルダ名に一致するフォルダを探す。"""
    hits: list[Path] = []
    seen: set[Path] = set()

    for base in search_bases:
        if not base.exists():
            continue
        for path in iter_dirs(base):
            if path in seen:
                continue
            if normalize_path_text(path.name) == decoded_name:
                hits.append(path)
                seen.add(path)
    return hits


def choose_best_path(paths: list[Path]) -> Path:
    """候補が複数ある場合、プロジェクト内のraw/interimを優先して選ぶ。"""
    if not paths:
        raise FileNotFoundError("候補パスが空です。")

    def score(path: Path) -> tuple[int, int]:
        text = path.as_posix()
        # rawに展開済みのものを最優先、次にinterim。
        if "/data/raw/" in text:
            priority = 0
        elif "/data/interim/" in text:
            priority = 1
        else:
            priority = 2
        # 階層が浅い候補を優先する。
        return (priority, len(path.parts))

    return sorted(paths, key=score)[0]


def find_drive_root() -> Path:
    """展開済みデータから `共有ドライブ` フォルダを探す。

    旧版のeda001.pyのようにzipを自動展開するのではなく、展開済みフォルダを読む。
    zipしか存在しない場合は、READMEの手順に従って手動展開してから実行する。
    """
    hits = find_named_dirs(DATASET_SEARCH_BASES, "共有ドライブ")
    if not hits:
        message = (
            "展開済みの `共有ドライブ` フォルダが見つかりません。\n"
            "share.zipを展開し、例えば `data/raw/share/共有ドライブ` または "
            "`data/raw/share/share/共有ドライブ` になるように配置してください。"
        )
        raise FileNotFoundError(message)
    drive_root = choose_best_path(hits)
    logging.info("Use drive_root: %s", drive_root)
    return drive_root


def find_questions_dir() -> Path:
    """展開済みデータから `質問回答` フォルダを探す。"""
    hits = find_named_dirs(DATASET_SEARCH_BASES, "質問回答")
    if not hits:
        message = (
            "展開済みの `質問回答` フォルダが見つかりません。\n"
            "questions_valid.csv / questions_test.csv が入っているフォルダを確認してください。"
        )
        raise FileNotFoundError(message)
    questions_dir = choose_best_path(hits)
    logging.info("Use questions_dir: %s", questions_dir)
    return questions_dir


def find_file_by_name(search_bases: list[Path], file_name: str) -> Path | None:
    """指定ファイル名を探索する。見つからない場合はNoneを返す。"""
    candidates: list[Path] = []
    for base in search_bases:
        if not base.exists():
            continue
        for path in iter_files(base):
            if normalize_path_text(path.name) == file_name:
                candidates.append(path)
    if not candidates:
        return None
    return choose_best_path(candidates)


# =============================================================================
# 共有ドライブ棚卸し
# =============================================================================


def classify_shared_drive_path(rel_path: str) -> dict[str, str]:
    """共有ドライブ内のパスから、案件名・大分類フォルダなどを推定する。"""
    parts = Path(rel_path).parts
    parts_nfc = [normalize_path_text(p) for p in parts]

    project_name = ""
    major_folder = ""
    area = ""

    if "共有ドライブ" in parts_nfc:
        idx = parts_nfc.index("共有ドライブ")
        if len(parts_nfc) > idx + 1:
            area = parts_nfc[idx + 1]

    if "プロジェクト" in parts_nfc:
        idx = parts_nfc.index("プロジェクト")
        if len(parts_nfc) > idx + 1:
            project_name = parts_nfc[idx + 1]
        if len(parts_nfc) > idx + 2:
            major_folder = parts_nfc[idx + 2]
    elif "社内管理" in parts_nfc:
        area = "社内管理"
        idx = parts_nfc.index("社内管理")
        if len(parts_nfc) > idx + 1:
            major_folder = parts_nfc[idx + 1]

    return {
        "area": area,
        "project_name": project_name,
        "major_folder": major_folder,
    }


def build_file_inventory(drive_root: Path) -> pd.DataFrame:
    """共有ドライブ配下の全ファイルを棚卸ししてDataFrame化する。"""
    rows = []

    for path in iter_files(drive_root):
        rel_actual = path.relative_to(drive_root).as_posix()
        rel_display = normalize_path_text(rel_actual)
        ext = path.suffix.lower() or "[no_ext]"
        path_info = classify_shared_drive_path(f"共有ドライブ/{rel_display}")
        try:
            size = path.stat().st_size
        except OSError:
            size = -1

        rows.append(
            {
                "relative_path": rel_display,
                "actual_relative_path": rel_actual,
                "file_name": normalize_path_text(path.name),
                "stem": normalize_path_text(path.stem),
                "extension": ext,
                "size_bytes": size,
                "size_kb": round(size / 1024, 2) if size >= 0 else None,
                "depth": len(Path(rel_display).parts),
                "area": path_info["area"],
                "project_name": path_info["project_name"],
                "major_folder": path_info["major_folder"],
                "is_temp_office_file": path.name.startswith("~$"),
                "source_path": safe_relative_to(path, BASE_DIR),
            }
        )

    if not rows:
        raise FileNotFoundError(f"共有ドライブ配下にファイルが見つかりません: {drive_root}")

    df = pd.DataFrame(rows)
    df = df.sort_values(["area", "project_name", "relative_path"]).reset_index(drop=True)
    return df


# =============================================================================
# 質問ファイル読み込み・分類
# =============================================================================


def load_questions(questions_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """valid/testの質問ファイルを読み込む。"""
    valid_path = questions_dir / "questions_valid.csv"
    test_path = questions_dir / "questions_test.csv"
    if not valid_path.exists():
        found = find_file_by_name(DATASET_SEARCH_BASES, "questions_valid.csv")
        valid_path = found if found is not None else valid_path
    if not test_path.exists():
        found = find_file_by_name(DATASET_SEARCH_BASES, "questions_test.csv")
        test_path = found if found is not None else test_path

    if not valid_path.exists():
        raise FileNotFoundError(f"questions_valid.csv が見つかりません: {questions_dir}")
    if not test_path.exists():
        raise FileNotFoundError(f"questions_test.csv が見つかりません: {questions_dir}")

    valid = pd.read_csv(valid_path, encoding="utf-8-sig")
    test = pd.read_csv(test_path, encoding="utf-8-sig")
    valid["split"] = "valid"
    test["split"] = "test"
    valid["question_file"] = safe_relative_to(valid_path, BASE_DIR)
    test["question_file"] = safe_relative_to(test_path, BASE_DIR)
    return valid, test


def add_question_features(df: pd.DataFrame) -> pd.DataFrame:
    """質問文から長さ・必要そうな処理タイプを付与する。"""
    out = df.copy()
    out["question"] = out["question"].fillna("").astype(str)
    out["question_length"] = out["question"].str.len()

    for label, patterns in QUESTION_PATTERNS.items():
        regex = "|".join(re.escape(p) for p in patterns)
        out[f"needs_{label}"] = out["question"].str.contains(regex, case=False, regex=True)

    flag_cols = [c for c in out.columns if c.startswith("needs_")]
    out["estimated_need_count"] = out[flag_cols].sum(axis=1)
    out["estimated_needs"] = out[flag_cols].apply(
        lambda row: ", ".join(c.replace("needs_", "") for c, v in row.items() if bool(v)),
        axis=1,
    )
    out["estimated_needs"] = out["estimated_needs"].replace("", "未分類")
    return out


# =============================================================================
# 集計・保存・可視化
# =============================================================================


def make_basic_tables(file_df: pd.DataFrame, valid_q: pd.DataFrame, test_q: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """EDA001で確認したい基本集計を作る。"""
    extension_counts = (
        file_df.groupby("extension", dropna=False)
        .agg(file_count=("relative_path", "count"), total_size_kb=("size_kb", "sum"))
        .reset_index()
        .sort_values("file_count", ascending=False)
    )

    project_counts = (
        file_df[file_df["project_name"].ne("")]
        .groupby("project_name", dropna=False)
        .agg(file_count=("relative_path", "count"), total_size_kb=("size_kb", "sum"))
        .reset_index()
        .sort_values("file_count", ascending=False)
    )

    major_folder_counts = (
        file_df.groupby(["area", "major_folder"], dropna=False)
        .agg(file_count=("relative_path", "count"), total_size_kb=("size_kb", "sum"))
        .reset_index()
        .sort_values(["area", "file_count"], ascending=[True, False])
    )

    questions = pd.concat([valid_q, test_q], ignore_index=True, sort=False)
    question_features = add_question_features(questions)

    need_cols = [c for c in question_features.columns if c.startswith("needs_")]
    question_type_counts = []
    for col in need_cols:
        label = col.replace("needs_", "")
        question_type_counts.append(
            {
                "estimated_need": label,
                "valid_count": int(question_features.query("split == 'valid'")[col].sum()),
                "test_count": int(question_features.query("split == 'test'")[col].sum()),
                "total_count": int(question_features[col].sum()),
            }
        )
    question_type_counts = pd.DataFrame(question_type_counts).sort_values("total_count", ascending=False)

    # validの正解は学習用に使えるため、回答文字数の傾向も見ておく。
    valid_answers = valid_q.copy()
    if "answer" in valid_answers.columns:
        valid_answers["answer"] = valid_answers["answer"].fillna("").astype(str)
        valid_answers["answer_length"] = valid_answers["answer"].str.len()

    # 最初の抽出器設計に使うため、形式ごとの推奨処理も付ける。
    extractor_priority = make_extractor_priority_table(extension_counts)

    tables = {
        "file_inventory": file_df,
        "extension_counts": extension_counts,
        "project_counts": project_counts,
        "major_folder_counts": major_folder_counts,
        "question_features": question_features,
        "question_type_counts": question_type_counts,
        "valid_answers": valid_answers,
        "extractor_priority": extractor_priority,
    }
    return tables


def make_extractor_priority_table(extension_counts: pd.DataFrame) -> pd.DataFrame:
    """拡張子ごとに、次に作る抽出器の優先度を整理する。"""
    notes = {
        ".md": ("A", "テキストとして直接読める。社内管理・規定系の確認に使いやすい。"),
        ".csv": ("A", "表データとして読み込みやすい。質問・分析結果・提出形式の確認に使う。"),
        ".json": ("A", "設定値・評価値・selected_columnsなどを構造化して抽出しやすい。"),
        ".py": ("A", "分析条件・特徴量・モデル設定をコードから抽出する対象。"),
        ".ipynb": ("A", "Notebook内のMarkdown・コード・出力をJSONとして抽出できる。"),
        ".xlsx": ("A", "セル値だけでなく、シート名・セル色・数式・フィルター情報が重要。"),
        ".docx": ("A", "本文に加えて、太字・下線・赤字・ハイライトなどの書式情報が重要。"),
        ".pptx": ("A", "スライド本文・図形テキスト・装飾・差分比較の対象。"),
        ".pdf": ("B", "テキスト抽出に加え、ページ単位・図表の見た目確認が必要。"),
        ".png": ("B", "グラフ・画像・マーカー読み取り。OCRや画像理解が必要。"),
        ".txt": ("B", "直接読めるが、件数が少なければ後回しでもよい。"),
    }

    rows = []
    for _, row in extension_counts.iterrows():
        ext = row["extension"]
        priority, note = notes.get(ext, ("C", "必要になった時点で個別対応する。"))
        rows.append(
            {
                "extension": ext,
                "file_count": int(row["file_count"]),
                "priority": priority,
                "note": note,
            }
        )
    return pd.DataFrame(rows).sort_values(["priority", "file_count"], ascending=[True, False])


def save_tables(tables: dict[str, pd.DataFrame]) -> None:
    """集計表をCSVで保存する。"""
    for name, df in tables.items():
        df.to_csv(TABLE_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")


def plot_barh(df: pd.DataFrame, x_col: str, y_col: str, title: str, out_path: Path, top_n: int = 20) -> None:
    """横棒グラフを保存する。"""
    plot_df = df.head(top_n).iloc[::-1]
    plt.figure(figsize=(10, max(4, 0.35 * len(plot_df))))
    plt.barh(plot_df[y_col].astype(str), plot_df[x_col])
    plt.title(title)
    plt.xlabel(x_col)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def make_figures(tables: dict[str, pd.DataFrame]) -> None:
    """EDAの確認用図を保存する。"""
    plot_barh(
        tables["extension_counts"],
        x_col="file_count",
        y_col="extension",
        title="拡張子別ファイル数",
        out_path=FIG_DIR / "01_extension_counts.png",
    )
    plot_barh(
        tables["project_counts"],
        x_col="file_count",
        y_col="project_name",
        title="案件別ファイル数",
        out_path=FIG_DIR / "02_project_file_counts.png",
    )
    plot_barh(
        tables["question_type_counts"],
        x_col="total_count",
        y_col="estimated_need",
        title="質問文から推定した必要処理タイプ",
        out_path=FIG_DIR / "03_question_type_counts.png",
        top_n=12,
    )

    q = tables["question_features"]
    plt.figure(figsize=(8, 5))
    for split, group in q.groupby("split"):
        plt.hist(group["question_length"], bins=20, alpha=0.6, label=split)
    plt.title("質問文の文字数分布")
    plt.xlabel("question_length")
    plt.ylabel("count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_question_length_distribution.png", dpi=150)
    plt.close()


def read_sample_submit_info() -> dict[str, int | str]:
    """展開済みsample_submitからpredictions.csvの中身を確認する。"""
    sample_path = find_file_by_name(DATASET_SEARCH_BASES, "predictions.csv")
    if sample_path is None:
        return {"sample_submit_found": 0, "sample_submit_rows": 0, "sample_submit_path": ""}
    try:
        sample_df = pd.read_csv(sample_path, header=None)
        rows = len(sample_df)
        columns = sample_df.shape[1]
    except Exception:
        rows = -1
        columns = -1
    return {
        "sample_submit_found": 1,
        "sample_submit_rows": rows,
        "sample_submit_columns": columns,
        "sample_submit_path": safe_relative_to(sample_path, BASE_DIR),
    }


# =============================================================================
# レポート出力
# =============================================================================


def write_report(tables: dict[str, pd.DataFrame], drive_root: Path, questions_dir: Path) -> None:
    """Markdown形式の簡易レポートを出力する。"""
    file_df = tables["file_inventory"]
    q = tables["question_features"]
    valid_count = int((q["split"] == "valid").sum())
    test_count = int((q["split"] == "test").sum())
    temp_count = int(file_df["is_temp_office_file"].sum())
    sample_info = read_sample_submit_info()

    top_ext = df_to_markdown(tables["extension_counts"], max_rows=10)
    top_projects = df_to_markdown(tables["project_counts"], max_rows=20)
    q_types = df_to_markdown(tables["question_type_counts"])
    extractor_priority = df_to_markdown(tables["extractor_priority"], max_rows=20)

    valid_examples_cols = [c for c in ["index", "question", "answer", "estimated_needs"] if c in q.columns]
    valid_examples = df_to_markdown(q.query("split == 'valid'")[valid_examples_cols].head(10))

    report = f"""# EDA001: 共有ドライブ全体の棚卸し

## 目的

今回のコンペは、表データ予測ではなく、共有ドライブ内の文書・表・画像・コードなどから質問に回答するAgentic RAG課題です。  
EDA001では、まず配布データの全体像を把握し、次に作る抽出器・検索器の優先順位を決めるための棚卸しを行います。

## 使用したデータ場所

| 項目 | パス |
|---|---|
| 共有ドライブ | `{safe_relative_to(drive_root, BASE_DIR)}` |
| 質問回答 | `{safe_relative_to(questions_dir, BASE_DIR)}` |
| sample_submit | `{sample_info.get('sample_submit_path', '')}` |

## 実行結果サマリ

| 項目 | 値 |
|---|---:|
| 共有ドライブ内ファイル数 | {len(file_df):,} |
| 案件数 | {file_df['project_name'].replace('', pd.NA).dropna().nunique():,} |
| 拡張子種類数 | {file_df['extension'].nunique():,} |
| Office一時ファイル候補 | {temp_count:,} |
| valid質問数 | {valid_count:,} |
| test質問数 | {test_count:,} |
| sample_submit行数 | {sample_info.get('sample_submit_rows', 0)} |

## 拡張子別ファイル数 Top10

{top_ext}

## 案件別ファイル数

{top_projects}

## 質問タイプ推定

{q_types}

## 抽出器の優先度案

{extractor_priority}

## valid質問の先頭例

{valid_examples}

## 出力ファイル

- `tables/file_inventory.csv`: 共有ドライブ内の全ファイル一覧
- `tables/extension_counts.csv`: 拡張子別ファイル数
- `tables/project_counts.csv`: 案件別ファイル数
- `tables/major_folder_counts.csv`: 大分類フォルダ別ファイル数
- `tables/question_features.csv`: valid/test質問の特徴量
- `tables/question_type_counts.csv`: 質問タイプ推定の件数
- `tables/valid_answers.csv`: valid質問と正解
- `tables/extractor_priority.csv`: 拡張子別の抽出器優先度
- `figures/01_extension_counts.png`: 拡張子別ファイル数
- `figures/02_project_file_counts.png`: 案件別ファイル数
- `figures/03_question_type_counts.png`: 質問タイプ推定
- `figures/04_question_length_distribution.png`: 質問文字数分布

## EDA001から見える次の方針

1. まず `.md`, `.csv`, `.json`, `.py`, `.ipynb` を対象に、テキスト抽出のベースラインを作る。  
   これらは比較的そのまま読めるため、RAGの初期インデックス作成に向いています。
2. 次に `.docx`, `.pptx`, `.xlsx` の抽出を作る。  
   本コンペでは太字・下線・赤字・ハイライト・セル色などの表示情報が重要です。
3. PDFと画像は後回しにしすぎない。  
   会議録PDFやグラフ画像から答える問題があるため、OCR/画像読み取りが必要になります。
4. valid 30問を手動で分類し、必要なファイル形式と抽出ロジックを対応付ける。  
   ここで作った分類をtest 100問に横展開するのが現実的です。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


# =============================================================================
# メイン処理
# =============================================================================


def main() -> None:
    setup()
    logging.info("Start EDA001")

    # zip展開は行わず、展開済みフォルダを自動検出する。
    drive_root = find_drive_root()
    questions_dir = find_questions_dir()

    valid_q, test_q = load_questions(questions_dir)
    file_df = build_file_inventory(drive_root)

    tables = make_basic_tables(file_df, valid_q, test_q)
    save_tables(tables)
    make_figures(tables)
    write_report(tables, drive_root, questions_dir)

    logging.info("Finished EDA001")
    print(f"EDA001 finished: {REPORT_PATH}")
    print(f"drive_root: {drive_root}")
    print(f"questions_dir: {questions_dir}")
    print(f"tables: {TABLE_DIR}")
    print(f"figures: {FIG_DIR}")


if __name__ == "__main__":
    main()
