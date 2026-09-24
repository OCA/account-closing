# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCutoffPicking(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.company.accrual_taxes = False
        cls.product = cls.env["product.product"].create(
            {
                "name": "Received product",
                "is_storable": True,
                "property_account_expense_id": cls.company_data[
                    "default_account_expense"
                ].id,
            }
        )
        cls.purchase = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 5,
                            "price_unit": 10,
                            "taxes_id": False,
                        }
                    )
                ],
            }
        )
        cls.purchase.button_confirm()
        receipt = cls.purchase.picking_ids
        receipt.move_ids.write({"quantity": 5, "picked": True})
        receipt.button_validate()

    def _create_cutoff(self, accrual_scope):
        return self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": fields.Date.context_today(self.purchase),
                "cutoff_type": "accrued_expense",
                "accrual_scope": accrual_scope,
            }
        )

    def test_accrual_scope(self):
        """Received goods are entirely before the cut-off date"""
        cutoff_partial = self._create_cutoff("partial")
        cutoff_partial.get_lines()
        self.assertFalse(cutoff_partial.line_ids)

        cutoff_full = self._create_cutoff("full")
        cutoff_full.get_lines()
        self.assertEqual(cutoff_full.line_ids.price_origin, self.purchase.name)
        self.assertEqual(cutoff_full.line_ids.quantity, 5)
        self.assertEqual(cutoff_full.total_cutoff_amount, -50)

        with self.assertRaises(ValidationError):
            self._create_cutoff("all")
