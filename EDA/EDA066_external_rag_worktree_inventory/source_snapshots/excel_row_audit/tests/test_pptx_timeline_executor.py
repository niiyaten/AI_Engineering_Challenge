from types import SimpleNamespace
import unittest

from rag_competition.pptx_timeline_executor import execute_pptx_timeline_lookup


def shape(index, text, left, top, width, height, kind="AUTO_SHAPE"):
    return {"shape_index": index, "text": text, "left": left, "top": top, "width": width, "height": height, "shape_type": kind}


def structure(headers, rows, markers):
    return {"slides": [{"slide_number": 3, "shapes": [shape(0, "スケジュール案", 0, 0, 100, 20), *headers, *rows, *markers]}]}


class PptxTimelineExecutorTests(unittest.TestCase):
    def setUp(self):
        self.file = SimpleNamespace(file_id="ppt", extension=".pptx", raw_path="proposal.pptx")
        self.headers = [shape(1, "W1", 100, 40, 100, 20), shape(2, "W2", 200, 40, 100, 20), shape(3, "W3", 300, 40, 100, 20)]

    def test_activity_to_first_week_uses_line_marker(self):
        rows = [shape(4, "モデル高度化\n説明性・セグメント分析", 0, 100, 90, 40)]
        markers = [shape(5, "", 200, 120, 200, 0, "LINE"), *[shape(6 + n, "", 100 + 100 * n, 100, 100, 40) for n in range(3)]]
        result = execute_pptx_timeline_lookup("提案書のモデルの高度化（説明性・セグメント分析）の実施予定は第何週目ですか。", [self.file], {"ppt": structure(self.headers, rows, markers)})
        self.assertEqual("success", result["status"])
        self.assertEqual("第2週目", result["answer"])

    def test_week_to_activity_uses_unique_rectangle_marker(self):
        rows = [shape(4, "前処理設計\n担当者", 0, 100, 90, 40), shape(5, "解釈・業務示唆整理\n担当者", 0, 160, 90, 40)]
        markers = [shape(6, "", 200, 110, 80, 15), shape(7, "", 300, 170, 80, 15)]
        result = execute_pptx_timeline_lookup("スケジュール案において、第3週目に実施する項目は何ですか。", [self.file], {"ppt": structure(self.headers, rows, markers)})
        self.assertEqual("success", result["status"])
        self.assertEqual("解釈・業務示唆整理", result["answer"])
        self.assertTrue(result["verification"]["marker_overlap_verified"])

    def test_multiple_rows_for_week_are_suppressed(self):
        rows = [shape(4, "A", 0, 100, 90, 40), shape(5, "B", 0, 160, 90, 40)]
        markers = [shape(6, "", 200, 110, 80, 15), shape(7, "", 200, 170, 80, 15)]
        result = execute_pptx_timeline_lookup("スケジュール案において、第2週目に実施する項目は何ですか。", [self.file], {"ppt": structure(self.headers, rows, markers)})
        self.assertEqual("unsupported", result["status"])

    def test_missing_schedule_slide_is_suppressed(self):
        result = execute_pptx_timeline_lookup("第2週目の予定は何ですか。", [self.file], {"ppt": {"slides": []}})
        self.assertEqual("timeline_slide_not_unique", result["failure_stage"])
