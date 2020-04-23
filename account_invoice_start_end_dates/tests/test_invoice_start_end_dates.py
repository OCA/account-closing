# Copyright 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time

from odoo.tests import tagged
from odoo.tests.common import SavepointCase


@tagged("-at_install", "post_install")
class TestInvoiceStartEndDates(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inv_model = cls.env["account.move"]
        cls.account_model = cls.env["account.account"]
        cls.journal_model = cls.env["account.journal"]
        cls.account_revenue = cls.account_model.search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_revenue").id,
                )
            ],
            limit=1,
        )
        cls.sale_journal = cls.journal_model.search([("type", "=", "sale")], limit=1)
        cls.maint_product = cls.env.ref(
            "account_invoice_start_end_dates." "product_maintenance_contract_demo"
        )

    def _date(self, date):
        """ convert MM-DD to current year date YYYY-MM-DD """
        return time.strftime("%Y-" + date)

    def test_invoice_with_grouping(self):
        invoice = self.inv_model.create(
            {
                "date": self._date("01-01"),
                "partner_id": self.env.ref("base.res_partner_2").id,
                "journal_id": self.sale_journal.id,
                "type": "out_invoice",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.maint_product.id,
                            "name": "Maintenance IPBX 12 mois",
                            "price_unit": 2400,
                            "quantity": 1,
                            "account_id": self.account_revenue.id,
                            "start_date": self._date("01-01"),
                            "end_date": self._date("12-31"),
                        },
                    ),
                    (
                        0,
                        0,
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
                    (
                        0,
                        0,
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
                    (
                        0,
                        0,
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
        invoice.action_post()
