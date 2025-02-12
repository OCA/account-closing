# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from .common import TestAccountCutoffAccrualSaleStockCommon


class TestAccountCutoffAccrualSaleStockOnOrder(TestAccountCutoffAccrualSaleStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Make first stock product invoicable on order
        product = cls.env.ref("product.product_delivery_01")
        product.invoice_policy = "order"
        sol = cls.so.order_line.filtered(lambda line: line.product_id == product)
        price = sol.price_unit
        sol.product_uom_qty = 2
        sol.price_unit = price

    def test_accrued_revenue_on_so_not_invoiced(self):
        """Test cutoff based on SO where qty_delivered > qty_invoiced."""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 0, "No cutoff product lines should be found"
        )
        self._do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make invoice
        invoice = self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        invoice.action_post()
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund reset the SO lines qty_invoiced
        self._refund_invoice(invoice)
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        for line in product_lines:
            self.assertEqual(line.cutoff_amount, 200, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_all_invoiced(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced."""
        cutoff = self.revenue_cutoff
        invoice = self._confirm_so_and_do_picking(2)
        # Make invoice
        invoice2 = self.so._create_invoices(final=True)
        # Validate invoice2
        invoice2.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        # Make a refund - the refund reset qty_invoiced
        self._refund_invoice(invoice)
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 1, "1 cutoff product lines should be found"
        )
        self.assertEqual(
            product_lines.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
        )

    def test_accrued_revenue_on_so_draft_invoice(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced but the.

        invoice is still in draft
        """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Make invoice
        invoice = self.so._create_invoices(final=True)
        self._do_picking(2)
        invoice2 = self.so._create_invoices(final=True)
        invoice2.action_post()
        # - invoice is in draft, no change to cutoff
        cutoff.get_lines()
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 1, "1 cutoff product lines should be found"
        )
        self.assertEqual(
            product_lines.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
        )
        # Validate invoice
        invoice.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund reset SO lines qty_invoiced
        self._refund_invoice(invoice)
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 1, "1 cutoff product lines should be found"
        )
        self.assertEqual(
            product_lines.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
        )

    def test_accrued_revenue_on_so_not_invoiced_after_cutoff(self):
        """Test cutoff based on SO where qty_delivered > qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self._do_picking(2)
        cutoff.get_lines()
        # Make invoice
        invoice = self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice after cutoff
        invoice.invoice_date = cutoff.cutoff_date + timedelta(days=1)
        invoice.action_post()
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make a refund after cutoff
        refund = self._refund_invoice(invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_all_invoiced_after_cutoff(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced.

        And make invoice after cutoff date
        We expect cutoff for the service and stock product.
        """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Make invoice for product on order
        invoice = self.so._create_invoices(final=True)
        # Validate invoice after cutoff
        invoice.invoice_date = cutoff.cutoff_date + timedelta(days=1)
        invoice.action_post()
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff lines should be found")
        self.assertEqual(cutoff.line_ids.product_id.detailed_type, "service")
        self._do_picking(2)
        # Make invoice
        invoice2 = self.so._create_invoices(final=True)
        invoice2.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        product_lines = cutoff.line_ids.filtered(
            lambda line: line.product_id.detailed_type == "product"
        )
        service_lines = cutoff.line_ids.filtered(
            lambda line: line.product_id.detailed_type == "service"
        )
        self.assertEqual(len(product_lines), 1, "1 cutoff product line should be found")
        self.assertEqual(
            product_lines.cutoff_amount, 2 * 100, "SO line cutoff amount incorrect"
        )
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 5 * 100, "SO line cutoff amount incorrect"
        )
        # Make a refund - the refund reset SO lines qty_invoiced but no change to cutoff
        refund = self._refund_invoice(invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        product_line = cutoff.line_ids.filtered(
            lambda line: line.product_id.detailed_type == "product"
        )
        self.assertEqual(len(product_line), 1, "1 cutoff product line should be found")
        self.assertEqual(
            product_line.cutoff_amount, 2 * 100, "SO line cutoff amount incorrect"
        )
        service_line = cutoff.line_ids.filtered(
            lambda line: line.product_id.detailed_type == "service"
        )
        self.assertEqual(len(service_line), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_line.cutoff_amount, 5 * 100, "SO line cutoff amount incorrect"
        )
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")

    def test_accrued_revenue_on_so_force_invoiced_after(self):
        """Test cutoff when SO is force invoiced after cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self._do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Force invoiced after cutoff lines generated, lines should be deleted
        self.so.force_invoiced = True
        self.assertEqual(len(cutoff.line_ids), 0, "cutoff lines should be deleted")
        # Remove Force invoiced, lines should be recreated
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_before(self):
        """Test cutoff when SO is force invoiced before cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self._do_picking(2)
        # Force invoiced before cutoff lines generated, lines should not be created
        self.so.force_invoiced = True
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be generated")
        # Remove Force invoiced, lines should be created
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_after_but_posted(self):
        """Test cutoff when SO is force invoiced after closed cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self._do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        cutoff.state = "done"
        # Force invoiced after cutoff lines generated, cutoff is posted
        self.so.force_invoiced = True
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Remove Force invoiced, nothing changes
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 3, "3 cutoff lines should be found")
        service_lines = self._get_service_lines(cutoff)
        product_lines = self._get_product_lines(cutoff)
        self.assertEqual(len(service_lines), 1, "1 cutoff service line should be found")
        self.assertEqual(
            service_lines.cutoff_amount, 100 * 5, "SO line cutoff amount incorrect"
        )
        self.assertEqual(
            len(product_lines), 2, "2 cutoff product lines should be found"
        )
        for line in product_lines:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_before_but_posted(self):
        """Test cutoff when SO is force invoiced before closed cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self._do_picking(2)
        # Force invoiced before cutoff lines generated, lines should be deleted
        self.so.force_invoiced = True
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
        cutoff.state = "done"
        # Remove Force invoiced, lines should be created
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
