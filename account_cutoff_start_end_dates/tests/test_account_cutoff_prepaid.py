# Copyright 2014-2022 ACSONE SA/NV (http://acsone.eu)
# @author Stéphane Bidoul <stephane.bidoul@acsone.eu>
# Copyright 2016-2022 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2026 Tecnativa - Adasat Torres
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCutoffPrepaid(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.test_company_dict = cls.setup_other_company(name="Cutme Inc.")
        cls.company = cls.test_company_dict["company"]
        cls.env.user.write({"company_ids": [Command.link(cls.company.id)]})
        cls.inv_model = cls.env["account.move"]
        cls.cutoff_model = cls.env["account.cutoff"]
        cls.account_expense = cls.test_company_dict["default_account_expense"]
        cls.account_cutoff = cls.env["account.account"].create(
            {
                "account_type": "liability_current",
                "company_ids": [Command.set([cls.company.id])],
                "name": "Test cutoff",
                "code": "TC.1",
            }
        )
        cls.cutoff_journal = cls.test_company_dict["default_journal_misc"]
        cls.purchase_journal = cls.test_company_dict["default_journal_purchase"]
        cls.partner = cls.env["res.partner"].create({"name": "Odoo fanboy"})
        cls.company.write(
            {
                "default_cutoff_journal_id": cls.cutoff_journal.id,
                "default_prepaid_expense_account_id": cls.account_cutoff.id,
            }
        )

    def _date(self, date):
        """convert MM-DD to current year date YYYY-MM-DD"""
        return time.strftime("%Y-" + date)

    def _days(self, start_date, end_date):
        start_date = fields.Date.from_string(self._date(start_date))
        end_date = fields.Date.from_string(self._date(end_date))
        return (end_date - start_date).days + 1

    def _create_invoice(
        self, date, amount, start_date, end_date, move_type="in_invoice", taxes=None
    ):
        is_sale = move_type == "out_invoice"
        journal = (
            self.test_company_dict["default_journal_sale"]
            if is_sale
            else self.purchase_journal
        )
        account = (
            self.test_company_dict["default_account_revenue"]
            if is_sale
            else self.account_expense
        )
        invoice = self.inv_model.create(
            {
                "company_id": self.company.id,
                "invoice_date": self._date(date),
                "date": self._date(date),
                "partner_id": self.partner.id,
                "journal_id": journal.id,
                "move_type": move_type,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "expense",
                            "price_unit": amount,
                            "quantity": 1,
                            "account_id": account.id,
                            "tax_ids": [Command.set(taxes.ids)]
                            if taxes is not None
                            else [Command.clear()],
                            "start_date": self._date(start_date),
                            "end_date": self._date(end_date),
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        self.assertEqual(amount, invoice.amount_untaxed)
        return invoice

    def _create_cutoff(self, date):
        cutoff = self.cutoff_model.create(
            {
                "company_id": self.company.id,
                "cutoff_date": self._date(date),
                "cutoff_type": "prepaid_expense",
            }
        )
        self.assertTrue(self.purchase_journal in cutoff.source_journal_ids)
        self.assertEqual(cutoff.cutoff_journal_id, self.cutoff_journal)
        self.assertEqual(cutoff.cutoff_account_id, self.account_cutoff)
        return cutoff

    def test_with_cutoff_before_after_and_in_the_middle(self):
        """basic test with cutoff before, after and in the middle"""
        amount = self._days("04-01", "06-30")
        amount_2months = self._days("05-01", "06-30")
        # invoice to be spread of 3 months
        self._create_invoice("01-15", amount, start_date="04-01", end_date="06-30")
        # cutoff after one month of invoice period -> 2 months cutoff
        cutoff = self._create_cutoff("04-30")
        cutoff.get_lines()
        self.assertEqual(amount_2months, cutoff.total_cutoff_amount)
        # cutoff at end of invoice period -> no cutoff
        cutoff = self._create_cutoff("06-30")
        cutoff.get_lines()
        self.assertEqual(0, cutoff.total_cutoff_amount)
        # cutoff before invoice period -> full value cutoff
        cutoff = self._create_cutoff("01-31")
        cutoff.get_lines()
        self.assertEqual(amount, cutoff.total_cutoff_amount)

    def test_difference_accrual_chain(self):
        for cutoff_type, sign in (("accrued_expense", -1), ("accrued_revenue", 1)):
            invoice = self._create_invoice(
                "07-01",
                600,
                "04-01",
                "06-30",
                move_type="in_invoice" if sign == -1 else "out_invoice",
            )
            previous = self.cutoff_model
            for date, cumulative, delta in (
                ("04-30", 197.80, 197.80),
                ("05-31", 402.20, 204.40),
                ("06-30", 600, 197.80),
                ("07-01", 0, -600),
            ):
                cutoff = self.cutoff_model.create(
                    {
                        "company_id": self.company.id,
                        "cutoff_type": cutoff_type,
                        "cutoff_date": self._date(date),
                        "calculation_method": "difference",
                        "source_journal_ids": [Command.set(invoice.journal_id.ids)],
                        "cutoff_account_id": self.account_cutoff.id,
                    }
                )
                cutoff.get_lines()
                line = cutoff.line_ids.filtered_domain(
                    [("origin_move_line_id.move_id", "=", invoice.id)]
                )
                self.assertEqual(len(line), 1)
                self.assertAlmostEqual(line.pending_amount, sign * cumulative)
                self.assertAlmostEqual(line.cutoff_amount, sign * delta)
                self.assertEqual(cutoff.previous_cutoff_id, previous)
                cutoff.create_move()
                if cutoff.move_id.state == "draft":
                    cutoff.move_id.action_post()
                self.assertFalse(cutoff.move_reversal_id)
                previous = cutoff

    def test_difference_accrual_chain_with_taxes(self):
        self.company.accrual_taxes = True
        tax = self.env["account.tax"].create(
            {
                "name": "Test Tax 10%",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 10,
                "company_id": self.company.id,
                "account_accrued_expense_id": self.account_cutoff.id,
            }
        )
        invoice = self._create_invoice("07-01", 600, "04-01", "06-30", taxes=tax)
        previous = self.cutoff_model
        for date, base, base_delta, amount, tax_delta in (
            ("04-30", -197.80, -197.80, -19.78, -19.78),
            ("05-31", -402.20, -204.40, -40.22, -20.44),
            ("06-30", -600, -197.80, -60, -19.78),
            ("07-01", 0, 600, 0, 60),
        ):
            with self.subTest(date=date):
                cutoff = self.cutoff_model.create(
                    {
                        "company_id": self.company.id,
                        "cutoff_type": "accrued_expense",
                        "cutoff_date": self._date(date),
                        "calculation_method": "difference",
                        "source_journal_ids": [Command.set(invoice.journal_id.ids)],
                        "cutoff_account_id": self.account_cutoff.id,
                    }
                )
                cutoff.get_lines()
                self.assertEqual(cutoff.previous_cutoff_id, previous)
                self.assertEqual(len(cutoff.line_ids), 1)
                tax_line = cutoff.line_ids.tax_line_ids
                self.assertEqual(len(tax_line), 1)
                self.assertEqual(tax_line.tax_id, tax)
                self.assertEqual(tax_line.cutoff_account_id, self.account_cutoff)
                self.assertAlmostEqual(tax_line.pending_base, base)
                self.assertAlmostEqual(tax_line.base, base_delta)
                self.assertAlmostEqual(tax_line.pending_amount, amount)
                self.assertAlmostEqual(tax_line.pending_cutoff_amount, amount)
                self.assertAlmostEqual(tax_line.amount, tax_delta)
                self.assertAlmostEqual(tax_line.cutoff_amount, tax_delta)
                cutoff.create_move()
                if cutoff.move_id.state == "draft":
                    cutoff.move_id.action_post()
                previous = cutoff

    def test_difference_after_regular_cutoff(self):
        self._create_invoice("04-01", 600, "04-01", "06-30")
        regular = self._create_cutoff("04-30")
        regular.get_lines()
        regular.create_move()
        if regular.move_id.state == "draft":
            regular.move_id.action_post()

        cutoff = self._create_cutoff("05-31")
        cutoff.calculation_method = "difference"
        with self.assertRaises(UserError):
            cutoff._get_previous_difference_cutoff()

        reversal = regular.move_id._reverse_moves([{"date": self._date("06-01")}])
        with self.assertRaises(UserError):
            cutoff._get_previous_difference_cutoff()
        reversal.action_post()
        # Even a posted reversal is ineffective before its accounting date.
        with self.assertRaises(UserError):
            cutoff._get_previous_difference_cutoff()
        reversal.button_draft()
        # Changing the month requires a new date-based journal sequence.
        reversal.write({"name": False, "date": self._date("05-01")})
        reversal.action_post()
        cutoff.get_lines()
        self.assertFalse(cutoff.previous_cutoff_id)
        self.assertEqual(cutoff.line_ids.previous_pending_amount, 0)
        self.assertAlmostEqual(cutoff.total_cutoff_amount, 197.80)

    def test_difference_cutoff_chain(self):
        self._create_invoice("04-01", 600, "04-01", "06-30")
        previous = self.cutoff_model
        for date, pending, difference in (
            ("04-30", 402.20, 402.20),
            ("05-31", 197.80, -204.40),
            ("06-30", 0, -197.80),
        ):
            cutoff = self._create_cutoff(date)
            cutoff.calculation_method = "difference"
            cutoff.get_lines()
            self.assertEqual(cutoff.previous_cutoff_id, previous)
            self.assertEqual(len(cutoff.line_ids), 1)
            self.assertAlmostEqual(cutoff.line_ids.pending_amount, pending)
            self.assertAlmostEqual(cutoff.total_cutoff_amount, difference)
            cutoff.create_move()
            if cutoff.move_id.state == "draft":
                cutoff.move_id.action_post()
            self.assertFalse(cutoff.move_reversal_id)
            previous = cutoff

    def _check_difference_invalid_source(self, missing_date=False):
        invoice = self._create_invoice("04-01", 600, "04-01", "06-30")
        previous = self._create_cutoff("04-30")
        previous.write(
            {"calculation_method": "difference", "source_move_state": "posted"}
        )
        previous.get_lines()
        self.assertAlmostEqual(previous.line_ids.pending_amount, 402.20)
        previous.create_move()
        if previous.move_id.state == "draft":
            previous.move_id.action_post()

        invoice.button_draft()
        if missing_date:
            invoice.invoice_line_ids.start_date = False
        cutoff = self._create_cutoff("05-31")
        cutoff.write(
            {"calculation_method": "difference", "source_move_state": "posted"}
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1)
        line = cutoff.line_ids
        self.assertEqual(
            line.origin_move_line_id, previous.line_ids.origin_move_line_id
        )
        self.assertEqual(line.start_date, previous.line_ids.start_date)
        self.assertEqual(line.end_date, previous.line_ids.end_date)
        self.assertEqual(line.pending_amount, 0)
        self.assertAlmostEqual(line.previous_pending_amount, 402.20)
        self.assertAlmostEqual(line.cutoff_amount, -402.20)
        cutoff.create_move()
        if cutoff.move_id.state == "draft":
            cutoff.move_id.action_post()

        following = self._create_cutoff("06-30")
        following.write(
            {"calculation_method": "difference", "source_move_state": "posted"}
        )
        following.get_lines()
        self.assertFalse(following.line_ids)

    def test_difference_draft_source(self):
        self._check_difference_invalid_source()

    def test_difference_source_without_start_date(self):
        self._check_difference_invalid_source(missing_date=True)

    def tests_1(self):
        """generate move, and test move lines grouping"""
        # two invoices
        amount = self._days("04-01", "06-30")
        self._create_invoice("01-15", amount, start_date="04-01", end_date="06-30")
        self._create_invoice("01-16", amount, start_date="04-01", end_date="06-30")
        # cutoff before invoice period -> full value cutoff
        cutoff = self._create_cutoff("01-31")
        cutoff.get_lines()
        cutoff.create_move()
        self.assertEqual(amount * 2, cutoff.total_cutoff_amount)
        self.assertTrue(cutoff.move_id, "move not generated")
        # two invoices, but two lines (because the two cutoff lines
        # have been grouped into one line plus one counterpart)
        self.assertEqual(len(cutoff.move_id.line_ids), 2)

    def test_include_tax_lines(self):
        """Test that include_tax_lines includes tax move lines in cutoff."""
        tax = self.env["account.tax"].create(
            {
                "name": "Test Tax 10%",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 10,
                "company_id": self.company.id,
            }
        )
        amount = self._days("04-01", "06-30")
        amount_2months = self._days("05-01", "06-30")
        # Create invoice with tax
        invoice = self.inv_model.create(
            {
                "company_id": self.company.id,
                "invoice_date": self._date("01-15"),
                "date": self._date("01-15"),
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "move_type": "in_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "expense with tax",
                            "price_unit": amount,
                            "quantity": 1,
                            "account_id": self.account_expense.id,
                            "start_date": self._date("04-01"),
                            "end_date": self._date("06-30"),
                            "tax_ids": [Command.set(tax.ids)],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        # Set start_date and end_date on tax lines (not auto-propagated)
        tax_lines = invoice.line_ids.filtered(lambda line: line.display_type == "tax")
        self.assertTrue(tax_lines, "Invoice should have tax lines")
        tax_lines.write(
            {
                "start_date": self._date("04-01"),
                "end_date": self._date("06-30"),
            }
        )
        tax_line_balance = sum(tax_lines.mapped("balance"))

        # Without include_tax_lines: only product line in cutoff
        cutoff = self._create_cutoff("01-31")
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1)
        self.assertEqual(cutoff.total_cutoff_amount, amount)
        cutoff.unlink()

        # With include_tax_lines, cutoff before period: full amount + tax
        cutoff = self.cutoff_model.create(
            {
                "company_id": self.company.id,
                "cutoff_date": self._date("01-31"),
                "cutoff_type": "prepaid_expense",
                "include_tax_lines": True,
            }
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2)
        self.assertEqual(
            cutoff.total_cutoff_amount,
            amount + tax_line_balance,
        )

        # With include_tax_lines, cutoff in the middle: prorated amount + tax
        cutoff = self.cutoff_model.create(
            {
                "company_id": self.company.id,
                "cutoff_date": self._date("04-30"),
                "cutoff_type": "prepaid_expense",
                "include_tax_lines": True,
            }
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2)
        expected_tax_cutoff = self.company.currency_id.round(
            tax_line_balance * amount_2months / amount
        )
        self.assertEqual(
            cutoff.total_cutoff_amount,
            amount_2months + expected_tax_cutoff,
        )

        # With include_tax_lines, cutoff at end of period: no cutoff
        cutoff = self.cutoff_model.create(
            {
                "company_id": self.company.id,
                "cutoff_date": self._date("06-30"),
                "cutoff_type": "prepaid_expense",
                "include_tax_lines": True,
            }
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0)
        self.assertEqual(cutoff.total_cutoff_amount, 0)
