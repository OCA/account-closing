from odoo.tests.common import TransactionCase

from .common import CURRENT_MODULE


class TestCurrencyRevaluationReport(TransactionCase):
    def test_wizard_empty_accounts(self):
        wizard = self.env["unrealized.report.printer"]
        wiz = wizard.create({})
        result = wiz.print_report()

        self.assertEqual(result.get("type"), "ir.actions.report")
        self.assertEqual(
            result.get("report_name"),
            f"{CURRENT_MODULE}.curr_unrealized_report",
        )
