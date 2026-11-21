# Copyright 2026 Lorenzo Battistini
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCutoffSpanning(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.test_company_dict = cls.setup_other_company(name="Cutme Spanning Inc.")
        cls.company = cls.test_company_dict["company"]
        cls.env.user.write({"company_ids": [Command.link(cls.company.id)]})
        cls.account_expense = cls.test_company_dict["default_account_expense"]
        cls.purchase_journal = cls.test_company_dict["default_journal_purchase"]
        cls.partner = cls.env["res.partner"].create({"name": "Late supplier"})
        cls.invoices_to_receive_account = cls._create_account(
            "Invoices to receive", "FDR1"
        )
        cls.accrued_expense_account = cls._create_account("Accrued expenses", "RAT1")
        cls.company.write(
            {
                "default_cutoff_journal_id": cls.test_company_dict[
                    "default_journal_misc"
                ].id,
                "default_accrued_expense_account_id": (
                    cls.invoices_to_receive_account.id
                ),
                "default_accrued_expense_spanning_account_id": (
                    cls.accrued_expense_account.id
                ),
                "accrual_taxes": False,
            }
        )

    @classmethod
    def _create_account(cls, name, code):
        return cls.env["account.account"].create(
            {
                "name": name,
                "code": code,
                "account_type": "liability_current",
                "company_ids": [Command.set([cls.company.id])],
            }
        )

    def _create_invoice(self, amount, start_date, end_date, taxes=None):
        line_vals = {
            "name": "expense",
            "price_unit": amount,
            "quantity": 1,
            "account_id": self.account_expense.id,
            "start_date": start_date,
            "end_date": end_date,
        }
        if taxes is not None:
            line_vals["tax_ids"] = [Command.set(taxes.ids)]
        invoice = self.env["account.move"].create(
            {
                "company_id": self.company.id,
                "invoice_date": "2026-01-20",
                "date": "2026-01-20",
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "move_type": "in_invoice",
                "invoice_line_ids": [Command.create(line_vals)],
            }
        )
        invoice.action_post()
        return invoice

    def _create_cutoff(self):
        return self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": "2025-12-31",
                "cutoff_type": "accrued_expense",
            }
        )

    def _get_counterpart_credit(self, cutoff, account):
        move_lines = cutoff.move_id.line_ids.filtered(
            lambda line: line.account_id == account
        )
        return sum(move_lines.mapped("credit"))

    def _create_invoices(self, taxes=None):
        # the whole period is before the cut-off date: all the 100 are accrued
        full_invoice = self._create_invoice(
            100, "2025-12-01", "2025-12-31", taxes=taxes
        )
        # the period lasts 62 days (December and January) and only the 31 days
        # of December are before the cut-off date: 124 * 31 / 62 = 62 are accrued
        spanning_invoice = self._create_invoice(
            124, "2025-12-01", "2026-01-31", taxes=taxes
        )
        return full_invoice, spanning_invoice

    def test_spanning_account(self):
        """The counterpart of the spanning lines uses the spanning account"""
        full_invoice, spanning_invoice = self._create_invoices()
        cutoff = self._create_cutoff()
        self.assertEqual(cutoff.cutoff_account_id, self.invoices_to_receive_account)
        self.assertEqual(
            cutoff.cutoff_account_spanning_id, self.accrued_expense_account
        )
        cutoff.get_lines()
        spanning_line = cutoff.line_ids.filtered("is_spanning")
        self.assertEqual(
            spanning_line.origin_move_line_id, spanning_invoice.invoice_line_ids
        )
        self.assertEqual(
            (cutoff.line_ids - spanning_line).origin_move_line_id,
            full_invoice.invoice_line_ids,
        )

        cutoff.create_move()
        self.assertEqual(
            self._get_counterpart_credit(cutoff, self.invoices_to_receive_account),
            100,
        )
        self.assertEqual(
            self._get_counterpart_credit(cutoff, self.accrued_expense_account), 62
        )

    def test_no_spanning_account(self):
        """Without spanning account, all the lines use the cut-off account"""
        self._create_invoices()
        cutoff = self._create_cutoff()
        cutoff.cutoff_account_spanning_id = False
        cutoff.get_lines()
        cutoff.create_move()
        self.assertEqual(
            self._get_counterpart_credit(cutoff, self.invoices_to_receive_account),
            162,
        )
        self.assertFalse(
            cutoff.move_id.line_ids.filtered(
                lambda line: line.account_id == self.accrued_expense_account
            )
        )

    def test_spanning_account_taxes(self):
        """The counterpart of the taxes follows the classification of their line"""
        tax_accrual_account = self._create_account("Accrued taxes", "TAX1")
        tax = self.env["account.tax"].create(
            {
                "name": "Test Tax 10%",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 10,
                "company_id": self.company.id,
                "account_accrued_expense_id": tax_accrual_account.id,
            }
        )
        self.company.accrual_taxes = True
        self._create_invoices(taxes=tax)
        cutoff = self._create_cutoff()
        cutoff.get_lines()
        cutoff.create_move()
        self.assertEqual(
            self._get_counterpart_credit(cutoff, self.invoices_to_receive_account),
            110,
        )
        self.assertAlmostEqual(
            self._get_counterpart_credit(cutoff, self.accrued_expense_account),
            68.2,
        )
