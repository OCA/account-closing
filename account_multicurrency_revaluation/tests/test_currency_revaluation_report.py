# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCurrencyRevaluationReport(TransactionCase):
    def test_wizard_empty_accounts(self):
        wizard = self.env["unrealized.report.printer"]
        wiz = wizard.create({})
        result = wiz.print_report()

        self.assertEqual(result.get("type"), "ir.actions.report")
        self.assertEqual(
            result.get("report_name"),
            "account_multicurrency_revaluation.curr_unrealized_report",
        )
