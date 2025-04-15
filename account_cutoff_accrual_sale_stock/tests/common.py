# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.account_cutoff_accrual_sale.tests.common import (
    TestAccountCutoffAccrualSaleCommon,
)


class TestAccountCutoffAccrualSaleStockCommon(TestAccountCutoffAccrualSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        for p in cls.products.filtered(
            lambda product: product.detailed_type == "product"
        ):
            cls.env["stock.quant"]._update_available_quantity(
                p, cls.stock_location, 100
            )

    def _get_service_lines(self, cutoff):
        return cutoff.line_ids.filtered(
            lambda line: line.product_id.detailed_type == "service"
        )

    def _get_product_lines(self, cutoff):
        return cutoff.line_ids.filtered(
            lambda line: line.product_id.detailed_type == "product"
        )

    def _confirm_so_and_do_picking(self, qty_done):
        self.so.action_confirm()
        if self.so.invoice_status == "to invoice":
            # Make invoice for product on order
            invoice = self.so._create_invoices(final=True)
            invoice.action_post()
            self.assertEqual(
                self.so.invoice_status,
                "no",
                'SO invoice_status should be "nothing to invoice" after confirming',
            )
        else:
            invoice = self.env["account.move"]
        self._do_picking(qty_done)
        return invoice

    def _do_picking(self, qty_done):
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
