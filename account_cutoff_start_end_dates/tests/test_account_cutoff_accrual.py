# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCutoffAccrual(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.test_company_dict = cls.setup_other_company(name="Cutme Accrual Inc.")
        cls.company = cls.test_company_dict["company"]
        cls.env.user.write({"company_ids": [Command.link(cls.company.id)]})
        cls.account_expense = cls.test_company_dict["default_account_expense"]
        cls.purchase_journal = cls.test_company_dict["default_journal_purchase"]
        cls.purchase_journal_2 = cls.env["account.journal"].create(
            {
                "name": "Other Purchases",
                "code": "OPUR",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Late supplier"})
        cls.company.write(
            {
                "default_cutoff_journal_id": cls.test_company_dict[
                    "default_journal_misc"
                ].id,
                "accrual_taxes": False,
            }
        )
        cls.cutoff_date = fields.Date.to_date("2025-12-31")

    def _create_invoice(self, amount, start_date, end_date):
        invoice = self.env["account.move"].create(
            {
                "company_id": self.company.id,
                "invoice_date": "2026-01-20",
                "date": "2026-01-20",
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "move_type": "in_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "expense",
                            "price_unit": amount,
                            "quantity": 1,
                            "account_id": self.account_expense.id,
                            "start_date": start_date,
                            "end_date": end_date,
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _create_cutoff(self, accrual_scope, source_journals=None):
        vals = {
            "company_id": self.company.id,
            "cutoff_date": self.cutoff_date,
            "cutoff_type": "accrued_expense",
            "accrual_scope": accrual_scope,
        }
        if source_journals is not None:
            vals["source_journal_ids"] = [Command.set(source_journals.ids)]
        return self.env["account.cutoff"].create(vals)

    def test_accrual_scope_lines(self):
        """Lines are split between lines entirely before and spanning the
        cut-off date"""
        # the whole period is before the cut-off date: all the 100 are accrued
        full_line = self._create_invoice(
            100, "2025-12-01", "2025-12-31"
        ).invoice_line_ids
        # the period lasts 62 days (December and January) and only the 31 days
        # of December are before the cut-off date: 124 * 31 / 62 = 62 are accrued
        partial_line = self._create_invoice(
            124, "2025-12-01", "2026-01-31"
        ).invoice_line_ids

        cutoff = self._create_cutoff("all")
        cutoff.get_lines()
        self.assertEqual(cutoff.line_ids.origin_move_line_id, full_line | partial_line)
        self.assertEqual(cutoff.total_cutoff_amount, -162)
        cutoff.unlink()

        cutoff_full = self._create_cutoff("full")
        cutoff_partial = self._create_cutoff("partial")
        cutoff_full.get_lines()
        cutoff_partial.get_lines()
        self.assertEqual(cutoff_full.line_ids.origin_move_line_id, full_line)
        self.assertEqual(cutoff_full.total_cutoff_amount, -100)
        self.assertEqual(cutoff_partial.line_ids.origin_move_line_id, partial_line)
        self.assertEqual(cutoff_partial.total_cutoff_amount, -62)

    def test_accrual_scope_overlap(self):
        """Cut-offs on the same date can't include the same lines"""
        self._create_cutoff("full")
        with self.assertRaises(ValidationError):
            self._create_cutoff("full")
        with self.assertRaises(ValidationError):
            self._create_cutoff("all")
        cutoff_partial = self._create_cutoff("partial")
        with self.assertRaises(ValidationError):
            cutoff_partial.accrual_scope = "full"
        # a different cut-off date doesn't overlap
        cutoff_partial.write({"accrual_scope": "full", "cutoff_date": "2025-11-30"})

    def test_accrual_scope_source_journals(self):
        """Cut-offs on different source journals don't overlap"""
        self._create_cutoff("partial", self.purchase_journal)
        cutoff = self._create_cutoff("partial", self.purchase_journal_2)
        with self.assertRaises(ValidationError):
            cutoff.source_journal_ids = [Command.link(self.purchase_journal.id)]
