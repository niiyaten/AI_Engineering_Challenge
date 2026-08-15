from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from rag_recovery.models import Question
from rag_recovery.planner import plan_question
from rag_recovery.runner import RecoveryRunner

ROOT = Path(__file__).resolve().parents[1]


def _build_share(tmp_path: Path) -> Path:
    target = tmp_path / "共有ドライブ" / "社内管理"
    target.mkdir(parents=True)
    shutil.copy2(ROOT / "tests" / "fixtures" / "seat_map.png", target / "座席表.png")
    return tmp_path


def test_spatial_questions_are_routed_first():
    question = Question("test", 0, "FMにおいて、佐藤さんから見て右側に座っている人を教えてください。")
    assert plan_question(question)[0].route == "spatial_layout"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is required")
def test_local_ocr_spatial_layout_answers_right_and_opposite(tmp_path: Path):
    share = _build_share(tmp_path)
    runner = RecoveryRunner(share, phase="phase3")

    right, _ = runner.solve(Question("test", 0, "IMにあるFMにおいて、佐藤さんから見て右側に座っている人の名前をすべて挙げてください。"))
    opposite, trace = runner.solve(Question("test", 0, "社内管理フォルダにあるFMにおいて、井上さんの向かいに座っている方のEXTを教えてください。"))

    assert right.answered and right.answer == "鈴木"
    assert opposite.answered and opposite.answer == "7103"
    assert trace["attempts"][0]["diagnostics"].get("layout_cache_hit") is True
