from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .io_utils import assert_formal_input_allowed, relative_to_root, sha1_file, sha1_text, write_csv, write_jsonl
from .schemas import FileRecord, to_dict


SUPPORTED_EXTENSIONS = {
    ".docx",
    ".pptx",
    ".xlsx",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".csv",
    ".tsv",
    ".json",
    ".py",
    ".ipynb",
    ".md",
    ".txt",
}


def parse_project_parts(relative_path: Path) -> tuple[str, str, str]:
    """共有ドライブ内のパスから、領域・案件名・大分類フォルダを推定する。"""
    parts = list(relative_path.parts)
    if not parts:
        return "", "", ""
    if "プロジェクト" in parts:
        index = parts.index("プロジェクト")
        project = parts[index + 1] if len(parts) > index + 1 else ""
        major = parts[index + 2] if len(parts) > index + 2 else ""
        return "プロジェクト", project, major
    if "社内管理" in parts:
        index = parts.index("社内管理")
        major = parts[index + 1] if len(parts) > index + 1 else "社内管理"
        return "社内管理", "社内管理", major
    return parts[0], "", parts[1] if len(parts) >= 2 else ""


def infer_document_kind(file_name: str, major_folder: str) -> str:
    text = f"{major_folder} {file_name}".lower()
    rules = [
        ("contract", ["契約", "contract"]),
        ("proposal", ["提案", "proposal"]),
        ("schedule", ["計画", "スケジュール", "wbs", "schedule"]),
        ("data", ["データ", "train", "カラム", "data"]),
        ("analysis", ["分析", "analysis", "notebook", "model"]),
        ("meeting", ["会議", "議事", "meeting"]),
        ("report", ["報告", "最終報告", "report"]),
        ("management", ["社内", "用語", "座席", "決裁", "管理"]),
    ]
    for kind, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return kind
    return "unknown"


def infer_version_label(file_name: str) -> str:
    lower = file_name.lower()
    patterns = [
        r"(old)",
        r"(final)",
        r"(latest)",
        r"(v\d+)",
        r"(r\d+)",
        r"(rev\d+)",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, lower))
    return ",".join(dict.fromkeys(found))


def infer_date_hints(text: str) -> list[str]:
    dates = re.findall(r"20\d{2}[-_/年]\d{1,2}[-_/月]\d{1,2}", text)
    normalized = [date.replace("年", "-").replace("月", "-").replace("/", "-").replace("_", "-").rstrip("日") for date in dates]
    return list(dict.fromkeys(normalized))


def make_file_record(path: Path, raw_root: Path, project_root: Path) -> FileRecord:
    assert_formal_input_allowed(path, project_root)
    relative_in_raw = path.resolve().relative_to(raw_root.resolve())
    area, project, major = parse_project_parts(relative_in_raw)
    raw_rel = relative_to_root(path, project_root)
    sha1 = sha1_file(path)
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
    return FileRecord(
        file_id="file_" + sha1_text(raw_rel)[:16],
        raw_path=raw_rel,
        relative_path=relative_in_raw.as_posix(),
        file_name=path.name,
        extension=path.suffix.lower(),
        size_bytes=stat.st_size,
        modified_at=modified_at,
        sha1=sha1,
        area=area,
        project_name=project,
        major_folder=major,
        document_kind=infer_document_kind(path.name, major),
        version_label=infer_version_label(path.name),
        date_hints=infer_date_hints(path.name),
        is_temp_office_file=path.name.startswith("~$"),
    )


def build_inventory(raw_root: Path, project_root: Path, output_dir: Path) -> list[FileRecord]:
    """raw共有ドライブを再帰走査し、正式実行用のファイル台帳を作る。"""
    assert_formal_input_allowed(raw_root, project_root)
    records: list[FileRecord] = []
    for path in sorted(raw_root.rglob("*"), key=lambda p: p.as_posix().lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        record = make_file_record(path, raw_root, project_root)
        records.append(record)

    jsonl_path = output_dir / "file_records.jsonl"
    csv_path = output_dir / "file_records.csv"
    rows = [to_dict(record) for record in records]
    write_jsonl(jsonl_path, rows)
    write_csv(
        csv_path,
        rows,
        [
            "file_id",
            "raw_path",
            "relative_path",
            "file_name",
            "extension",
            "size_bytes",
            "modified_at",
            "sha1",
            "area",
            "project_name",
            "major_folder",
            "document_kind",
            "version_label",
            "date_hints",
            "is_temp_office_file",
        ],
    )
    return records
