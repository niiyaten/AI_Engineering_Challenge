import unittest

from rag_competition.submission_format import normalize_submission_value


class SubmissionFormatTests(unittest.TestCase):
    def test_integer_like_float_is_normalized(self):
        self.assertEqual(normalize_submission_value(1200.0), {"raw_answer_value": 1200.0, "submission_answer": "1200", "normalization": "integer_like_float"})
        self.assertNotEqual(normalize_submission_value(1200.0)["submission_answer"], "120")

    def test_fractional_precision_is_preserved(self):
        self.assertEqual(normalize_submission_value("0.15002"), {"raw_answer_value": "0.15002", "submission_answer": "0.15002", "normalization": "unchanged_fractional"})

    def test_requested_decimal_precision_is_preserved(self):
        self.assertEqual(normalize_submission_value(1200.0, "小数第5位まで"), {"raw_answer_value": 1200.0, "submission_answer": "1200.0", "normalization": "unchanged_requested_precision"})

    def test_negative_and_fractional_numbers_are_not_truncated(self):
        self.assertEqual(normalize_submission_value(-1200.0)["submission_answer"], "-1200")
        self.assertEqual(normalize_submission_value(1200.5)["submission_answer"], "1200.5")

    def test_scientific_notation_is_preserved(self):
        self.assertEqual(normalize_submission_value("1.2e3"), {"raw_answer_value": "1.2e3", "submission_answer": "1.2e3", "normalization": "unchanged_scientific_notation"})


if __name__ == "__main__":
    unittest.main()
