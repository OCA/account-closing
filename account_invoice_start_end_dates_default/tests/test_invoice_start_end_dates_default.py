# Copyright 2026 Lorenzo Battistini
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import time

from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestInvoiceStartEndDatesDefault(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.move_model = cls.env["account.move"]
        cls.partner = cls.env["res.partner"].create({"name": "Nobug Customer"})
        cls.account_expense = cls.env["account.chart.template"]._get_demo_account(
            "expense",
            "expense",
            cls.env.company,
        )
        cls.maint_product = cls.env["product.product"].create(
            {
                "name": "Maintenance contract",
                "type": "service",
                "must_have_dates": True,
            }
        )

    def _date(self, date):
        """convert MM-DD to current year date YYYY-MM-DD"""
        return time.strftime("%Y-" + date)

    def _create_move_without_dates(self, move_type):
        return self.move_model.create(
            {
                "partner_id": self.partner.id,
                "move_type": move_type,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.maint_product.id,
                            "name": "Maintenance",
                            "price_unit": 1200,
                            "quantity": 1,
                            "account_id": self.account_expense.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Insurance",
                            "price_unit": 600,
                            "quantity": 1,
                            "account_id": self.account_expense.id,
                            "start_date": self._date("01-01"),
                            "end_date": self._date("12-31"),
                        }
                    ),
                ],
            }
        )

    def test_bill_date_as_default_dates(self):
        self.env.company.start_end_dates_from_bill_date = True
        bill_date = fields.Date.to_date(self._date("03-15"))
        bill = self._create_move_without_dates("in_invoice")
        maint_line, insurance_line = bill.invoice_line_ids
        self.assertFalse(maint_line.start_date)
        bill.invoice_date = bill_date
        self.assertEqual(maint_line.start_date, bill_date)
        self.assertEqual(maint_line.end_date, bill_date)
        # the dates set on the line are kept
        self.assertEqual(
            insurance_line.start_date, fields.Date.to_date(self._date("01-01"))
        )
        self.assertEqual(
            insurance_line.end_date, fields.Date.to_date(self._date("12-31"))
        )
        # only the invoice lines get the bill date
        self.assertFalse((bill.line_ids - bill.invoice_line_ids).filtered("start_date"))
        # the product that must have dates gets the bill date
        bill.action_post()
        self.assertEqual(bill.state, "posted")

    def test_bill_date_as_default_dates_form(self):
        self.env.company.start_end_dates_from_bill_date = True
        bill_date = fields.Date.to_date(self._date("03-15"))
        bill_form = Form(self.move_model.with_context(default_move_type="in_invoice"))
        bill_form.partner_id = self.partner
        # line added before the bill date
        with bill_form.invoice_line_ids.new() as line_form:
            line_form.name = "Electricity"
            line_form.price_unit = 100
        bill_form.invoice_date = bill_date
        # line added after the bill date
        with bill_form.invoice_line_ids.new() as line_form:
            line_form.name = "Gas"
            line_form.price_unit = 50
        bill = bill_form.save()
        self.assertEqual(len(bill.invoice_line_ids), 2)
        for line in bill.invoice_line_ids:
            self.assertEqual(line.start_date, bill_date)
            self.assertEqual(line.end_date, bill_date)

    def test_invoice_date_as_default_dates(self):
        self.env.company.start_end_dates_from_invoice_date = True
        invoice = self._create_move_without_dates("out_invoice")
        maint_line = invoice.invoice_line_ids[0]
        self.assertFalse(maint_line.start_date)
        # the invoice date is set when posting, and the lines get it before
        # the dates of the product that must have dates are checked
        invoice.action_post()
        self.assertTrue(invoice.invoice_date)
        self.assertEqual(maint_line.start_date, invoice.invoice_date)
        self.assertEqual(maint_line.end_date, invoice.invoice_date)

    def test_default_dates_options_by_move_type(self):
        for option, move_type in (
            (False, "in_invoice"),
            ("start_end_dates_from_invoice_date", "in_invoice"),
            ("start_end_dates_from_bill_date", "out_invoice"),
        ):
            with self.subTest(option=option, move_type=move_type):
                self.env.company.write(
                    {
                        "start_end_dates_from_bill_date": False,
                        "start_end_dates_from_invoice_date": False,
                    }
                )
                if option:
                    self.env.company[option] = True
                move = self._create_move_without_dates(move_type)
                move.invoice_date = self._date("03-15")
                self.assertFalse(move.invoice_line_ids[0].start_date)

    def _create_bill_with_dates(self):
        self.env.company.start_end_dates_from_bill_date = True
        bill = self._create_move_without_dates("in_invoice")
        bill.invoice_date = self._date("03-15")
        maint_line, insurance_line = bill.invoice_line_ids
        self.assertEqual(
            maint_line.start_date, fields.Date.to_date(self._date("03-15"))
        )
        self.assertEqual(
            insurance_line.start_date, fields.Date.to_date(self._date("01-01"))
        )
        return bill

    def test_duplicate_without_default_dates(self):
        bill = self._create_bill_with_dates()
        self.env.company.start_end_dates_from_bill_date = False
        copy = bill.copy()
        self.assertFalse(copy.invoice_date)
        copy.invoice_date = self._date("04-20")
        # the dates of the original lines are not copied
        self.assertFalse(copy.invoice_line_ids.filtered("start_date"))
        self.assertFalse(copy.invoice_line_ids.filtered("end_date"))

    def test_duplicate_with_default_dates(self):
        bill = self._create_bill_with_dates()
        copy = bill.copy()
        self.assertFalse(copy.invoice_line_ids.filtered("start_date"))
        new_date = fields.Date.to_date(self._date("04-20"))
        copy.invoice_date = new_date
        # the lines of the copy get the new bill date
        self.assertEqual(len(copy.invoice_line_ids), 2)
        for line in copy.invoice_line_ids:
            self.assertEqual(line.start_date, new_date)
            self.assertEqual(line.end_date, new_date)

    def test_vendor_bill_autocomplete_default_dates(self):
        bill = self._create_bill_with_dates()
        new_date = fields.Date.to_date(self._date("04-20"))
        # The Auto-Complete field is not in the form view of the purchase
        # users when purchase is installed: call its onchange directly.
        new_bill = self.move_model.create(
            {
                "partner_id": self.partner.id,
                "move_type": "in_invoice",
                "invoice_date": new_date,
            }
        )
        new_bill.invoice_vendor_bill_id = bill
        new_bill._onchange_invoice_vendor_bill()
        self.assertEqual(len(new_bill.invoice_line_ids), 2)
        for line in new_bill.invoice_line_ids:
            self.assertEqual(line.start_date, new_date)
            self.assertEqual(line.end_date, new_date)

    def test_credit_note_keeps_dates(self):
        bill = self._create_bill_with_dates()
        bill.action_post()
        wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create(
                {
                    "journal_id": bill.journal_id.id,
                    "date": self._date("04-20"),
                    "reason": "test",
                }
            )
        )
        wizard.refund_moves()
        refund = wizard.new_move_ids
        self.assertEqual(refund.move_type, "in_refund")
        for line in bill.invoice_line_ids:
            refund_line = refund.invoice_line_ids.filtered(
                lambda rl, line=line: rl.name == line.name
            )
            self.assertEqual(len(refund_line), 1)
            self.assertEqual(refund_line.start_date, line.start_date)
            self.assertEqual(refund_line.end_date, line.end_date)
