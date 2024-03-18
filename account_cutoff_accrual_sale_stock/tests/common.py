# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.account_cutoff_accrual_sale.tests.common import (
    TestAccountCutoffAccrualSaleCommon,
)


class TestAccountCutoffAccrualSaleStockCommon(TestAccountCutoffAccrualSaleCommon):
    def _confirm_so_and_do_picking(self, qty_done):
        self.so.action_confirm()
        # Make invoice what product on order
        self.so._create_invoices(final=True)
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        # Deliver
        pick = self.so.picking_ids
        pick.action_assign()
        pick.move_line_ids.write({"qty_done": qty_done})  # receive 2/5  # deliver 2/5
        pick._action_done()
        self.assertEqual(
            self.so.invoice_status,
            "to invoice",
            'SO invoice_status should be "to invoice" after partial delivery',
        )
        qties = [sol.qty_delivered for sol in self.so.order_line]
        self.assertEqual(
            qties,
            [qty_done if p.detailed_type == "product" else 0 for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )
