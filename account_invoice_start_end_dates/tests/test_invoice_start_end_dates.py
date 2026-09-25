# Copyright 2016-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import time

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestInvoiceStartEndDates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.move_model = cls.env["account.move"]
        cls.partner = cls.env["res.partner"].create({"name": "Nobug Customer"})
        cls.account_revenue = cls.env["account.chart.template"]._get_demo_account(
            "income",
            "income",
            cls.env.company,
        )
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

    def test_invoice(self):
        self.move_model.create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.maint_product.id,
                            "name": "Maintenance IPBX 12 mois",
                            "price_unit": 2400,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                            "start_date": self._date("01-01"),
                            "end_date": self._date("12-31"),
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.maint_product.id,
                            "name": "Maintenance téléphones 12 mois",
                            "price_unit": 12,
                            "quantity": 10,
                            "account_id": self.account_revenue.id,
                            "start_date": self._date("01-01"),
                            "end_date": self._date("12-31"),
                        },
                    ),
                    Command.create(
                        {
                            "product_id": self.maint_product.id,
                            "name": "Maintenance Fax 6 mois",
                            "price_unit": 120.75,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                            "start_date": self._date("01-01"),
                            "end_date": self._date("06-30"),
                        },
                    ),
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_5").id,
                            "name": "HD IPBX",
                            "price_unit": 215.5,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                        },
                    ),
                ],
            }
        )

    def test_missing_date(self):
        inv = self.move_model.create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.maint_product.id,
                            "name": "Maintenance IPBX 12 mois",
                            "price_unit": 1200,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                            "start_date": False,
                            "end_date": False,
                        }
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError):
            inv.action_post()

    def test_date_order(self):
        with self.assertRaises(ValidationError):
            self.move_model.create(
                {
                    "partner_id": self.partner.id,
                    "move_type": "out_invoice",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Maintenance Odoo",
                                "price_unit": 1200,
                                "quantity": 1,
                                "account_id": self.account_revenue.id,
                                # start date before end date
                                "start_date": self._date("12-31"),
                                "end_date": self._date("01-01"),
                            }
                        )
                    ],
                }
            )

    def test_date_partial(self):
        inv = self.move_model.create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Maintenance Odoo",
                            "price_unit": 1200,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                            # start date, but no end date
                            "start_date": self._date("12-31"),
                            "end_date": False,
                        }
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError):
            inv.action_post()
        inv = self.move_model.create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Maintenance Odoo",
                            "price_unit": 1200,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                            # end date, but no start date
                            "start_date": False,
                            "end_date": self._date("12-31"),
                        }
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError):
            inv.action_post()

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
