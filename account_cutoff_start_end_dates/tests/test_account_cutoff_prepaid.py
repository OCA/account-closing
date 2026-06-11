# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_cutoff_base.tests.common import AccountCutoffCommon


class TestAccountCutoffStartEndDates(AccountCutoffCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchase_journal = cls.company_data["default_journal_purchase"]
        cls.sale_journal = cls.company_data["default_journal_sale"]

    def _create_invoice(
        self,
        move_type,
        date,
        amount,
        start_date,
        end_date,
        journal,
        account,
        tax_ids=None,
        post=True,
    ):
        invoice = self.env["account.move"].create(
            {
                "company_id": self.company.id,
                "invoice_date": date,
                "date": date,
                "partner_id": self.partner.id,
                "journal_id": journal.id,
                "move_type": move_type,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "expense/revenue",
                            "price_unit": amount,
                            "quantity": 1,
                            "account_id": account.id,
                            "start_date": start_date,
                            "end_date": end_date,
                            "tax_ids": [Command.set(tax_ids)] if tax_ids else [],
                        }
                    )
                ],
            }
        )
        if post:
            invoice.action_post()
        return invoice

    def test_compute_source_journal_ids(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        self.assertIn(self.purchase_journal, cutoff.source_journal_ids)

        cutoff.cutoff_type = "accrued_revenue"
        self.assertIn(self.sale_journal, cutoff.source_journal_ids)

    def test_compute_source_journal_ids_unknown_type(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.cutoff_type = False
        cutoff._compute_source_journal_ids()
        self.assertFalse(cutoff.source_journal_ids)

    def test_check_start_end_dates_raises_when_invalid_in_forecast(self):
        with self.assertRaisesRegex(
            ValidationError, "The start date is after the end date"
        ):
            self.env["account.cutoff"].create(
                {
                    "company_id": self.company.id,
                    "cutoff_type": "prepaid_expense",
                    "state": "forecast",
                    "start_date": "2026-06-30",
                    "end_date": "2026-06-01",
                }
            )

    def test_forecast_enable_clears_lines_and_changes_state(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.forecast_enable()
        self.assertEqual(cutoff.state, "forecast")
        self.assertFalse(cutoff.cutoff_date)

    def test_forecast_enable_raises_when_move_exists(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.move_id = self.env["account.move"].create(
            {
                "journal_id": self.cutoff_journal.id,
            }
        )
        with self.assertRaisesRegex(UserError, "linked to a journal entry"):
            cutoff.forecast_enable()

    def test_forecast_disable_clears_lines_and_changes_state(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
                "state": "forecast",
            }
        )
        cutoff.forecast_disable()
        self.assertEqual(cutoff.state, "draft")

    def test_get_lines_prepaid_expense_standard_with_mapping(self):
        self._create_invoice(
            "in_invoice",
            "2026-01-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.purchase_journal,
            self.account_expense,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-04-30",
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1)
        self.assertEqual(cutoff.line_ids.cutoff_amount, 60.0)
        # account_expense has a mapping to account_prepaid_expense
        self.assertEqual(
            cutoff.line_ids.cutoff_account_id, self.account_prepaid_expense
        )

    def test_get_lines_prepaid_revenue_without_mapping(self):
        self._create_invoice(
            "out_invoice",
            "2026-01-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.sale_journal,
            self.account_revenue,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-04-30",
                "cutoff_type": "prepaid_revenue",
            }
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1)
        self.assertEqual(cutoff.line_ids.cutoff_amount, -60.0)
        # account_revenue has NO mapping
        self.assertEqual(cutoff.line_ids.cutoff_account_id, self.account_revenue)

    def test_get_lines_prepaid_expense_start_date_after_cutoff(self):
        self._create_invoice(
            "in_invoice",
            "2026-01-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.purchase_journal,
            self.account_expense,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-01-31",
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.get_lines()
        self.assertEqual(cutoff.line_ids.cutoff_amount, 90.0)

    def test_get_lines_prepaid_expense_forecast(self):
        self._create_invoice(
            "in_invoice",
            "2026-01-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.purchase_journal,
            self.account_expense,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.forecast_enable()
        cutoff.write(
            {
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            }
        )
        cutoff.get_lines()
        self.assertEqual(cutoff.line_ids.cutoff_amount, 31.0)

    def test_get_lines_forecast_raises_when_dates_missing(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.forecast_enable()
        with self.assertRaisesRegex(UserError, "Start date and end date are required"):
            cutoff.get_lines()

    def test_get_lines_raises_when_no_source_journal(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.source_journal_ids = [Command.clear()]
        with self.assertRaisesRegex(
            UserError, "You should set at least one Source Journal"
        ):
            cutoff.get_lines()

    def test_get_lines_accrued_expense_standard(self):
        self._create_invoice(
            "in_invoice",
            "2026-05-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.purchase_journal,
            self.account_expense,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-04-30",
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.get_lines()
        self.assertEqual(cutoff.line_ids.cutoff_amount, -30.0)

    def test_get_lines_accrued_expense_end_date_before_cutoff(self):
        self._create_invoice(
            "in_invoice",
            "2026-05-15",
            90.0,
            "2026-04-01",
            "2026-04-30",
            self.purchase_journal,
            self.account_expense,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-05-05",
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.get_lines()
        self.assertEqual(cutoff.line_ids.cutoff_amount, -90.0)

    def test_get_lines_accrued_expense_with_taxes(self):
        self._create_invoice(
            "in_invoice",
            "2026-05-15",
            90.0,
            "2026-04-01",
            "2026-04-30",
            self.purchase_journal,
            self.account_expense,
            tax_ids=[self.tax.id],
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-05-05",
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.get_lines()
        self.assertTrue(cutoff.line_ids.tax_line_ids)
        self.assertEqual(len(cutoff.line_ids.tax_line_ids), 1)

    def test_get_lines_draft_posted(self):
        self._create_invoice(
            "in_invoice",
            "2026-01-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.purchase_journal,
            self.account_expense,
            post=False,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-04-30",
                "cutoff_type": "prepaid_expense",
                "source_move_state": "draft_posted",
            }
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1)

    def test_get_lines_prepaid_expense_forecast_inside(self):
        self._create_invoice(
            "in_invoice",
            "2026-01-15",
            90.0,
            "2026-05-10",
            "2026-05-20",
            self.purchase_journal,
            self.account_expense,
        )
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        cutoff.forecast_enable()
        cutoff.write(
            {
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            }
        )
        cutoff.get_lines()
        self.assertEqual(cutoff.line_ids.cutoff_amount, 90.0)

    def test_get_lines_domain_unknown_type(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2026-04-30",
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.cutoff_type = False
        cutoff.source_journal_ids = [Command.set([self.purchase_journal.id])]
        domain = cutoff._get_lines_domain()
        self.assertNotIn("start_date", str(domain))

        invoice = self._create_invoice(
            "in_invoice",
            "2026-05-15",
            90.0,
            "2026-04-01",
            "2026-06-29",
            self.purchase_journal,
            self.account_expense,
        )
        aml = invoice.line_ids.filtered(
            lambda line: line.account_id == self.account_expense
        )
        vals = cutoff._prepare_date_cutoff_line(aml, {})
        self.assertNotIn("cutoff_amount", vals)
