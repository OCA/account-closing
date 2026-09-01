# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.exceptions import UserError

from odoo.addons.account_cutoff_accrual_order_base.tests.common import (
    TestAccountCutoffAccrualOrderCommon,
)


class TestAccountMoveLine(TestAccountCutoffAccrualOrderCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "purchase service",
                "purchase_ok": True,
                "detailed_type": "service",
                "purchase_method": "purchase",
                "standard_price": 100,
            }
        )

    def _create_purchase_order(self):
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_qty": 5,
                            "product_uom": self.product.uom_po_id.id,
                            "price_unit": 100,
                            "date_planned": fields.Date.today(),
                        }
                    )
                ],
            }
        )
        purchase_order.button_confirm()
        purchase_order.button_approve(force=True)
        return purchase_order

    def _create_purchase_invoice(self, purchase_order):
        action = purchase_order.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.write(
            {
                "invoice_date": fields.Date.today(),
                "date": fields.Date.today(),
            }
        )
        invoice.action_post()
        self.assertEqual(
            invoice.invoice_line_ids.purchase_line_id, purchase_order.order_line
        )
        return invoice

    def _create_done_cutoff_line(self, purchase_line):
        cutoff = (
            self.env["account.cutoff"]
            .with_context(default_cutoff_type="accrued_expense")
            .create(
                {
                    "cutoff_type": "accrued_expense",
                    "order_line_model": "purchase.order.line",
                    "company_id": self.company.id,
                    "cutoff_date": fields.Date.today(),
                }
            )
        )
        cutoff_line = self.env["account.cutoff.line"].create(
            {
                "parent_id": cutoff.id,
                "partner_id": self.partner.id,
                "name": purchase_line.name,
                "account_id": self.cutoff_account.id,
                "cutoff_account_id": self.cutoff_account.id,
                "currency_id": self.company.currency_id.id,
                "product_id": self.product.id,
                "price_unit": 100,
                "received_qty": 0,
                "invoiced_qty": 5,
                "purchase_line_id": purchase_line.id,
            }
        )
        cutoff.state = "done"
        return cutoff_line

    def test_cannot_change_purchase_line_when_done_cutoff_invoiced_qty_changes(self):
        """block changing the purchase line when a done cutoff would change"""
        purchase_order = self._create_purchase_order()
        invoice = self._create_purchase_invoice(purchase_order)
        self._create_done_cutoff_line(purchase_order.order_line)
        other_purchase_order = self._create_purchase_order()

        with self.assertRaisesRegex(UserError, "closed cutoff"):
            invoice.invoice_line_ids.write(
                {"purchase_line_id": other_purchase_order.order_line.id}
            )

    def test_cannot_unlink_invoice_line_when_done_cutoff_invoiced_qty_changes(self):
        """block deleting an invoice line when a done cutoff would change"""
        purchase_order = self._create_purchase_order()
        invoice = self._create_purchase_invoice(purchase_order)
        self._create_done_cutoff_line(purchase_order.order_line)
        invoice.button_draft()

        with self.assertRaisesRegex(UserError, "closed cutoff"):
            invoice.invoice_line_ids.unlink()
