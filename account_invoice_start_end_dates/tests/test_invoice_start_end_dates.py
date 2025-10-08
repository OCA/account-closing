# Copyright 2016-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import time

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
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
                                # start date, but no end date
                                "start_date": self._date("12-31"),
                                "end_date": False,
                            }
                        )
                    ],
                }
            )
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
                                # start date, but no end date
                                "start_date": False,
                                "end_date": self._date("12-31"),
                            }
                        )
                    ],
                }
            )
