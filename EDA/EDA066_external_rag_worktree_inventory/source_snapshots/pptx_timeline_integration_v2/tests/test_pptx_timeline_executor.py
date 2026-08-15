from pathlib import Path
from types import SimpleNamespace
import json
import unittest

from rag_competition.pptx_timeline_executor import execute_pptx_timeline_lookup


def shape(index, text, left, top, width, height, kind="AUTO_SHAPE"):
    return {"shape_index": index, "text": text, "left": left, "top": top, "width": width, "height": height, "shape_type": kind}


class PptxTimelineExecutorTests(unittest.TestCase):
    def setUp(self):
        self.file = SimpleNamespace(file_id="ppt", extension=".pptx", raw_path="proposal.pptx", sha1="fixture")
        self.headers = [shape(1, "W1", 100, 40, 100, 20), shape(2, "W2", 200, 40, 100, 20), shape(3, "W3", 300, 40, 100, 20)]
        self.temp = Path(self._testMethodName + ".json")

    def tearDown(self):
        self.temp.unlink(missing_ok=True)

    def _execute(self, question, rows, markers):
        payload = {"slides": [{"slide_number": 3, "shapes": [shape(0, "スケジュール", 0, 0, 100, 20), *self.headers, *rows, *markers]}]}
        self.temp.write_text(json.dumps(payload), encoding="utf-8")
        extraction = SimpleNamespace(status="success", extracted_path=str(self.temp))
        return execute_pptx_timeline_lookup(question, [self.file], {"ppt": extraction}, Path.cwd())

    def test_activity_to_week_uses_line_marker(self):
        result = self._execute("モデルの高度化の実施予定は第何週目ですか。", [shape(4, "モデル高度化", 0, 100, 90, 40)], [shape(5, "", 200, 120, 200, 0, "LINE")])
        self.assertEqual("success", result["status"])
        self.assertEqual("第2週目", result["answer"])

    def test_week_to_activity_uses_unique_marker(self):
        rows = [shape(4, "分析", 0, 100, 90, 40), shape(5, "解釈", 0, 160, 90, 40)]
        result = self._execute("スケジュールにおいて、第3週目に実施する活動は何ですか。", rows, [shape(6, "", 200, 110, 80, 15), shape(7, "", 300, 170, 80, 15)])
        self.assertEqual("success", result["status"])
        self.assertEqual("解釈", result["answer"])

    def test_ambiguous_rows_are_suppressed(self):
        rows = [shape(4, "A", 0, 100, 90, 40), shape(5, "B", 0, 160, 90, 40)]
        result = self._execute("スケジュールにおいて、第2週目に実施する活動は何ですか。", rows, [shape(6, "", 200, 110, 80, 15), shape(7, "", 200, 170, 80, 15)])
        self.assertEqual("unsupported", result["status"])
        self.assertTrue(result["ambiguous"])

    def test_missing_timeline_is_suppressed(self):
        self.temp.write_text(json.dumps({"slides": []}), encoding="utf-8")
        extraction = SimpleNamespace(status="success", extracted_path=str(self.temp))
        result = execute_pptx_timeline_lookup("第2週目の予定は何ですか。", [self.file], {"ppt": extraction}, Path.cwd())
        self.assertEqual("timeline_slide_not_unique", result["failure_stage"])
