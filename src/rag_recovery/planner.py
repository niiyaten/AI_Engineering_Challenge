from __future__ import annotations

import re
from dataclasses import replace

from .models import QueryPlan, Question
from .normalize import nfkc, unique_nonempty

FILE_RE = re.compile(r"([^\s、。『』「」]+?\.(?:xlsx|xlsm|csv|tsv|docx|pptx|pdf|json|py|ipynb|md|png|jpe?g))", re.I)
DATE_RE = re.compile(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?")
ID_RE = re.compile(r"\b(?:MS|CP|T|A|M)\d+\b", re.I)
QUOTED_RE = re.compile(r"[「『](.*?)[」』]")

ROUTE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("spatial_layout", ("座席", "右側", "右隣", "向かい", "正面", "内線", "ext", "fm")),
    ("diff", ("比較", "差分", "変更前", "変更後", "更新内容", "最新版", "旧版", "old版", "旧版と", "最新版と")),
    ("office_format", ("太字", "下線", "イタリック", "斜体", "赤字", "文字色", "ハイライト", "コメント", "注釈", "ページですか")),
    ("chart", ("グラフ", "ヒストグラム", "可視化", "系列", "軸", "プロット", "棒グラフ", "折れ線")),
    ("join", ("紐づく", "関連するタスク", "役割", "担当者", "アクションid", "マイルストーンid", "チェックポイント", "rateが変更", "別資料")),
    ("cross_project", ("全案件", "案件のうち", "最も多い案件", "最も高い案件", "上位3", "すべての案件", "完了案件", "存在する案件", "もっとも多くの案件")),
    ("code_json", ("metrics.json", "run_summary.json", "selected_columns", "features.py", "modeling.py", "notebook", "ipynb", "max_depth", "f1")),
    ("table", ("xlsx", "csv", "シート", "セル", "行", "列", "pivot", "フィルター", "標準化", "平均", "合計", "割合", "件数", "最大", "最小", "工数", "task id", "タスクid")),
    ("document", ("docx", "pptx", "pdf", "ページ", "記載", "抜き出", "明記", "契約", "報告書", "提案書", "会議録", "調査資料")),
)



def extract_filename_hints(text: str) -> list[str]:
    hints: list[str] = []
    for raw in FILE_RE.findall(nfkc(text)):
        value = raw.strip("、。 ")
        value = re.sub(r"^(?:と|から|および|及び|ならびに)", "", value)
        # A project possessive is usually outside the actual file name.
        if "の" in value:
            suffix = value.rsplit("の", 1)[-1]
            if re.search(r"\.(?:xlsx|xlsm|csv|tsv|docx|pptx|pdf|json|py|ipynb|md|png|jpe?g)$", suffix, re.I):
                value = suffix
        hints.append(value)
    return unique_nonempty(hints)


def extract_project_hints(text: str) -> list[str]:
    value = nfkc(text)
    heads: list[str] = []
    for marker in ("の", "案件", "において", "にて"):
        if marker in value:
            head = value.split(marker, 1)[0].strip(" 、。")
            if 2 <= len(head) <= 40:
                heads.append(head)
    for alias in re.findall(r"\b[A-Z][A-Z0-9_-]{1,12}\b", value):
        heads.append(alias)
    return unique_nonempty(heads)


def detect_operations(text: str) -> list[str]:
    q = nfkc(text).lower()
    ops: list[str] = []
    rules = (
        ("extract", ("抜き出", "抽出", "答えて", "挙げて")),
        ("filter", ("該当", "条件", "のうち", "間に", "以前", "以降", "未満", "以上")),
        ("groupby", ("ごと", "別", "毎", "平均が最も", "支払月")),
        ("sum", ("合計", "総額")),
        ("mean", ("平均")),
        ("count", ("件数", "いくつ", "何個", "発行され")),
        ("nunique", ("種類", "ユニーク", "異なる")),
        ("max", ("最大", "最も高", "最も多")),
        ("min", ("最小", "最も低", "最も少")),
        ("ratio", ("割合", "%")),
        ("difference", ("差", "少なく", "多く", "変更")),
        ("rank", ("上位", "ランキング")),
        ("round", ("四捨五入", "切り上げ", "切り捨て", "小数第")),
        ("page_lookup", ("何ページ", "ページ番号", "ページですか")),
        ("style_lookup", ("太字", "下線", "イタリック", "斜体", "色", "ハイライト", "コメント")),
        ("join", ("紐づく", "関連する", "役割", "担当者", "チェックポイント", "マイルストーン")),
        ("diff", ("比較", "差分", "変更前", "変更後", "旧版", "最新版", "old")),
        ("chart", ("グラフ", "ヒストグラム", "可視化", "系列")),
        ("spatial_relation", ("座席", "右側", "右隣", "向かい", "正面", "内線", "ext")),
    )
    for name, keys in rules:
        if any(k in q for k in keys):
            ops.append(name)
    return ops or ["extract"]


def plan_question(question: Question) -> list[QueryPlan]:
    q = nfkc(question.text)
    filenames = tuple(extract_filename_hints(q))
    projects = tuple(extract_project_hints(q))
    entities = tuple(unique_nonempty([*QUOTED_RE.findall(q), *ID_RE.findall(q)]))
    dates = ["-".join((y, m.zfill(2), d.zfill(2))) for y, m, d in DATE_RE.findall(q)]
    constraints = {"dates": dates, "selected_sources": list(question.selected_sources)}
    operations = tuple(detect_operations(q))
    routes: list[str] = []
    low = q.lower()
    for route, keys in ROUTE_PATTERNS:
        if any(k.lower() in low for k in keys):
            routes.append(route)
    # Ensure highly specific executors are attempted first.
    priority = {"spatial_layout": 0, "diff": 1, "office_format": 2, "chart": 3, "join": 4, "cross_project": 5, "code_json": 6, "table": 7, "document": 8}
    routes = sorted(set(routes or ["document"]), key=lambda r: priority[r])
    if "cross_project" in routes:
        routes = [route for route in routes if route in {"spatial_layout", "cross_project"}]
    source_mode = "cross_project" if "cross_project" in routes else "multi_document" if any(r in routes for r in ("diff", "join")) else "single_document"
    return [QueryPlan(route, projects, filenames, operations, entities, constraints, source_mode) for route in routes]
