from types import SimpleNamespace
import unittest

from rag_competition.route_registry import choose_route


def analysis(*, multiple=False, relation="single_source", minimum=1):
    return SimpleNamespace(
        needs_multiple_files=multiple,
        source_requirement={"source_relation": relation, "minimum_sources": minimum},
    )


def file_record(extension):
    return SimpleNamespace(extension=extension)


class RouteRegistryTest(unittest.TestCase):
    def test_single_xlsx_filtered_question_selects_existing_table_executor(self):
        decision = choose_route(
            "対象期間の該当タスクを一覧で返してください",
            analysis(),
            [file_record(".xlsx")],
        )
        self.assertTrue(decision.route_selected)
        self.assertEqual("excel.single_source.table", decision.selected_route)
        self.assertEqual("execute_table_question", decision.executor)

    def test_two_sources_are_not_sent_to_single_source_route(self):
        decision = choose_route(
            "旧版と新版の変更点を比較してください",
            analysis(multiple=True, relation="version_comparison", minimum=2),
            [file_record(".pptx"), file_record(".pptx")],
        )
        self.assertFalse(decision.route_selected)
        self.assertIn("comparison", decision.ambiguity_reason)

    def test_coefficient_prediction_uses_the_xlsx_regression_route(self):
        decision = choose_route("regression coefficient predict id=7", analysis(), [file_record(".xlsx")])
        self.assertTrue(decision.route_selected)
        self.assertEqual("excel.regression.predict_from_coefficients", decision.selected_route)
        self.assertEqual("workbook_formula_binding", decision.structure_resolver)

    def test_notebook_axis_question_uses_replay_route_without_question_id(self):
        decision = choose_route(
            "Notebook visualization y-axis tick maximum",
            analysis(),
            [file_record(".ipynb")],
        )
        self.assertTrue(decision.route_selected)
        self.assertEqual("notebook.axis_ticks.replay", decision.selected_route)
        self.assertEqual("execute_notebook_axis_ticks", decision.executor)

    def test_unsupported_file_type_is_suppressed(self):
        decision = choose_route("該当項目を一覧で返してください", analysis(), [file_record(".png")])
        self.assertFalse(decision.route_selected)
        self.assertEqual("no_route_supports_operation_file_relation", decision.ambiguity_reason)


if __name__ == "__main__":
    unittest.main()
