# Copyright 2023 Sergio Corato
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestInvoiceStartEndDates(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inv_model = cls.env["account.move"]
        cls.account_revenue = cls.company_data["default_account_revenue"]
        cls.sale_journal = cls.company_data["default_journal_sale"]
        product_model = cls.env["product.product"]
        cls.maint_product = product_model.create(
            {"name": "Maintenance contract", "type": "service", "must_have_dates": True}
        )
        cls.insur_product = product_model.create(
            {"name": "Insurance contract", "type": "service", "must_have_dates": True}
        )
        cls.product = product_model.create({"name": "HD IPBX", "type": "consu"})
        cls.company = cls.env.company

    @staticmethod
    def _date(date):
        """convert MM-DD to current year date YYYY-MM-DD"""
        return time.strftime("%Y-" + date)

    def _create_invoice(self):
        invoice_lines = [
            {
                "product_id": self.maint_product,
                "name": "Maintenance IPBX 12 months",
                "price_unit": 2400,
                "quantity": 1,
                "start_date": self._date("01-01"),
                "end_date": self._date("12-31"),
            },
            {
                "product_id": self.insur_product,
                "name": "Maintenance phones 12 months",
                "price_unit": 12,
                "quantity": 10,
            },
            {
                "product_id": self.maint_product,
                "name": "Maintenance Fax 6 months",
                "price_unit": 120.75,
                "quantity": 1,
                "start_date": self._date("01-01"),
                "end_date": self._date("06-30"),
            },
            {
                "product_id": self.product,
                "name": "HD IPBX",
                "price_unit": 215.5,
                "quantity": 1,
            },
        ]
        invoice_form = Form(
            self.inv_model.with_context(
                default_move_type="out_invoice",
                default_date=self._date("01-01"),
            )
        )
        invoice_form.partner_id = self.partner_a
        invoice_form.journal_id = self.sale_journal
        invoice_form.start_date = self._date("03-01")
        invoice_form.end_date = self._date("05-31")
        for invoice_line in invoice_lines:
            with invoice_form.invoice_line_ids.new() as line_form:
                line_form.product_id = invoice_line["product_id"]
                line_form.name = invoice_line["name"]
                line_form.price_unit = invoice_line["price_unit"]
                line_form.quantity = invoice_line["quantity"]
                line_form.account_id = self.account_revenue
                if invoice_line.get("start_date"):
                    line_form.start_date = invoice_line["start_date"]
                if invoice_line.get("end_date"):
                    line_form.end_date = invoice_line["end_date"]
        return invoice_form.save()

    def _test_invoice(self):
        apply_dates_all_lines = self.company.apply_dates_all_lines
        invoice = self._create_invoice()
        # add line through create() to test the create override
        invoice.write(
            {
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.insur_product.id,
                            "name": "Insurance",
                            "price_unit": 100,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                        }
                    )
                ]
            }
        )
        invoice.action_post()
        for line in invoice.line_ids.filtered(
            lambda x: x.product_id == self.maint_product
        ):
            self.assertEqual(line.start_date.strftime("%Y-%m-%d"), self._date("01-01"))
        insur_lines = invoice.line_ids.filtered(
            lambda x: x.product_id == self.insur_product
        )
        self.assertEqual(len(insur_lines), 2)
        for line in insur_lines:
            self.assertEqual(line.start_date, invoice.start_date)
            self.assertEqual(line.end_date, invoice.end_date)
        for line in invoice.line_ids.filtered(lambda x: x.product_id == self.product):
            if not apply_dates_all_lines:
                self.assertFalse(line.start_date)
                self.assertFalse(line.end_date)
            else:
                self.assertEqual(line.start_date, invoice.start_date)
                self.assertEqual(line.end_date, invoice.end_date)
        invoice.button_draft()
        insur_lines[0].end_date = self._date("04-30")
        self.assertEqual(
            insur_lines[0].end_date.strftime("%Y-%m-%d"), self._date("04-30")
        )
        invoice.end_date = self._date("04-15")
        invoice._onchange_dates()
        for line in invoice.line_ids.filtered(lambda x: x.product_id.must_have_dates):
            self.assertEqual(line.end_date.strftime("%Y-%m-%d"), self._date("04-15"))

    def test_01_invoice_without_apply_dates(self):
        self.company.apply_dates_all_lines = False
        self._test_invoice()

    def test_02_invoice_with_apply_dates(self):
        self.company.apply_dates_all_lines = True
        self._test_invoice()

    def test_03_onchange_product(self):
        self.company.apply_dates_all_lines = False
        invoice_form = Form(
            self.inv_model.with_context(default_move_type="out_invoice")
        )
        invoice_form.partner_id = self.partner_a
        invoice_form.start_date = self._date("02-01")
        invoice_form.end_date = self._date("02-28")
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.insur_product
            self.assertEqual(
                line_form.start_date.strftime("%Y-%m-%d"), self._date("02-01")
            )
            self.assertEqual(
                line_form.end_date.strftime("%Y-%m-%d"), self._date("02-28")
            )
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product
            self.assertFalse(line_form.start_date)
        invoice_form.save()

    def test_04_dates_copied_on_duplicate(self):
        self.company.apply_dates_all_lines = True
        invoice = self._create_invoice()
        new_invoice = invoice.copy()
        self.assertEqual(new_invoice.start_date, invoice.start_date)
        self.assertEqual(new_invoice.end_date, invoice.end_date)
        self.assertEqual(
            new_invoice.invoice_line_ids.mapped("start_date"),
            invoice.invoice_line_ids.mapped("start_date"),
        )
        self.assertEqual(
            new_invoice.invoice_line_ids.mapped("end_date"),
            invoice.invoice_line_ids.mapped("end_date"),
        )
