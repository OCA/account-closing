# Copyright 2023 Foodles (https://www.foodles.co/)
# @author: Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from functools import partial

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class CommonAccountCutoffBaseCAse(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None
        cls.account_cutoff = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_current"),
                ("company_id", "=", cls.env.ref("base.main_company").id),
            ],
            limit=1,
        )
        cls.account_cutoff.reconcile = True
        cls.maint_product = cls.env.ref(
            "account_invoice_start_end_dates.product_maintenance_contract_demo"
        )
        cls.miscellaneous_journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("code", "=", "MISC")], limit=1
        )
        cls.env.company.revenue_cutoff_journal_id = cls.miscellaneous_journal.id
        cls.env.company.expense_cutoff_journal_id = cls.miscellaneous_journal.id
        analytic_plan = cls.env["account.analytic.plan"].create({"name": "plan"})
        cls.analytic = cls.env["account.analytic.account"].create(
            {"name": "test", "plan_id": analytic_plan.id}
        )

    @classmethod
    def _create_invoice(cls, journal=None, move_type=None, account=None):
        return cls.env["account.move"].create(
            {
                "date": "2023-01-15",
                "invoice_date": "2023-01-15",
                "partner_id": cls.env.ref("base.res_partner_2").id,
                "journal_id": journal.id,
                "move_type": move_type,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": "Case A: 3 months starting the 7th",
                            "price_unit": 2400,
                            "quantity": 2,
                            "account_id": account.id,
                            "analytic_distribution": {cls.analytic.id: 100},
                            "start_date": "2023-01-07",
                            "end_date": "2023-03-31",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": "Case B: 3 full months",
                            "price_unit": 12,
                            "quantity": 10,
                            "account_id": account.id,
                            "start_date": "2023-01-01",
                            "end_date": "2023-03-31",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": "Case C: 2 month starting next month",
                            "price_unit": 12,
                            "quantity": 5,
                            "account_id": account.id,
                            "start_date": "2023-02-01",
                            "end_date": "2023-03-31",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": "Case D: 2 month stopping the month before",
                            "price_unit": 130,
                            "quantity": 2,
                            "account_id": account.id,
                            "start_date": "2023-01-01",
                            "end_date": "2023-02-28",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": (
                                "Case E: 1 month (22 october) leaving a blank months"
                            ),
                            "price_unit": 113.5,
                            "quantity": 1,
                            "account_id": account.id,
                            "start_date": "2022-10-01",
                            "end_date": "2022-10-15",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": (
                                "Case F: 3 months stating before invoice date "
                                "(december)"
                            ),
                            "price_unit": 777,
                            "quantity": 1,
                            "account_id": account.id,
                            "start_date": "2022-12-01",
                            "end_date": "2023-02-28",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": (
                                "Case G: 1 month (may) leaving a blank month (april)"
                            ),
                            "price_unit": 255,
                            "quantity": 1,
                            "account_id": account.id,
                            "start_date": "2023-05-01",
                            "end_date": "2023-05-31",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.env.ref("product.product_product_5").id,
                            "name": "Case H: product without date",
                            "price_unit": 215,
                            "quantity": 1,
                            "account_id": account.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.maint_product.id,
                            "name": (
                                "Case I: 3 months starting the 17th stopping the 15th"
                            ),
                            "price_unit": 2000,
                            "quantity": 1,
                            "account_id": account.id,
                            "start_date": "2023-01-17",
                            "end_date": "2023-03-15",
                        }
                    ),
                ],
            }
        )

    def assertAccountMoveLines(self, account_move, expected_lines):
        """Assert account move line values in an account move record

        :param expected_lines: list of tuple (filter_handler, dict(expected=value))
            :param filter_handler: is a filtered method that get an account move
                                    line as parameter
            :param dict(expected=value): a dict with values to test to be equals

        Usage::

            self.assertExpectedAccountMoveLines(
                invoice, [
                    (
                        lambda line: line.name == 'Expected string',
                        {"name": "Expected string"}
                    )
                ]
            )
        """
        for filter_function, expected_values in expected_lines:
            lines = account_move.line_ids.filtered(filter_function)
            if not lines:
                self.assertTrue(False, "No lines found matching filter_handler method")
            for line in lines:
                for key, expected_value in expected_values.items():
                    assert_method = self.assertEqual
                    if isinstance(expected_value, float):
                        assert_method = partial(self.assertAlmostEqual, places=2)
                    assert_method(
                        getattr(line, key),
                        expected_value,
                        msg=f"Testing {key} field on {line.name} ({len(lines)} "
                        "lines matched current filter)",
                    )


class CommonAccountInvoiceCutoffCase(CommonAccountCutoffBaseCAse):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_revenue = cls.env["account.account"].search(
            [
                (
                    "account_type",
                    "=",
                    "income",
                )
            ],
            limit=1,
        )
        cls.account_revenue.deferred_accrual_account_id = cls.account_cutoff
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        cls.invoice = cls._create_invoice(
            journal=cls.sale_journal,
            move_type="out_invoice",
            account=cls.account_revenue,
        )


class CommonAccountPurchaseInvoiceCutoffCase(CommonAccountCutoffBaseCAse):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_expense = cls.env["account.account"].search(
            [
                (
                    "account_type",
                    "=",
                    "expense",
                )
            ],
            limit=1,
        )
        cls.account_expense.deferred_accrual_account_id = cls.account_cutoff
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase")], limit=1
        )

        cls.invoice = cls._create_invoice(
            journal=cls.purchase_journal,
            move_type="in_invoice",
            account=cls.account_expense,
        )
