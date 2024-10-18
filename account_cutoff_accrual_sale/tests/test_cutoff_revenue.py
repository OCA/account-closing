# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import Command

from .common import TestAccountCutoffAccrualSaleCommon


class TestAccountCutoffAccrualSale(TestAccountCutoffAccrualSaleCommon):
    def test_accrued_revenue_empty(self):
        """Test cutoff when there is no confirmed SO."""
        cutoff = self.revenue_cutoff
        cutoff.get_lines()
        self.assertEqual(
            len(cutoff.line_ids), 0, "There should be no SO line to process"
        )

    def test_revenue_analytic_distribution(self):
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        for line in cutoff.line_ids:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): self.price},
                "Analytic distribution is not correctly set",
            )

    def test_revenue_tax_line(self):
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff lines should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                len(line.tax_line_ids), 1, "tax lines is not correctly set"
            )
            self.assertEqual(line.tax_line_ids.cutoff_account_id, self.cutoff_account)
            self.assertEqual(line.tax_line_ids.tax_id, self.tax_sale)
            self.assertEqual(line.tax_line_ids.base, amount)
            self.assertEqual(line.tax_line_ids.amount, amount * 15 / 100)
            self.assertEqual(line.tax_line_ids.cutoff_amount, amount * 15 / 100)

    # Make tests for product with invoice policy on order

    def test_accrued_revenue_on_so_not_invoiced(self):
        """Test cutoff based on SO where product_uom_qty > qty_invoiced."""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Make invoice
        self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        self.so.invoice_ids.action_post()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund reset the SO lines qty_invoiced
        self._refund_invoice(self.so.invoice_ids)
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff lines should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_delivery_not_invoiced(self):
        """Test cutoff based on SO where product_uom_qty > qty_invoiced."""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        # 1 cutoff line for the service
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        delivered_qty = (
            cutoff.line_ids.sale_line_id._get_cutoff_accrual_delivered_quantity(cutoff)
        )
        self.assertEqual(delivered_qty, 5, "the delivery line should be delivered")
        # simulate a delivery service line added after cutoff date
        cutoff.cutoff_date -= timedelta(days=1)
        delivered_qty = (
            cutoff.line_ids.sale_line_id._get_cutoff_accrual_delivered_quantity(cutoff)
        )
        self.assertEqual(delivered_qty, 0, "the delivery line should not be delivered")
        # regenerate cutoff
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "0 cutoff line should be found")

    def test_accrued_revenue_on_so_all_invoiced(self):
        """Test cutoff based on SO where product_uom_qty = qty_invoiced."""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Make invoice
        self.so._create_invoices(final=True)
        # Validate invoice
        self.so.invoice_ids.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        # Make a refund - the refund reset qty_invoiced
        self._refund_invoice(self.so.invoice_ids)
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_draft_invoice(self):
        """Test cutoff based on SO where product_uom_qty = qty_invoiced but the.

        invoice is still in draft
        """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Make invoice
        self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        self.so.invoice_ids.action_post()
        self.assertEqual(len(cutoff.line_ids), 1, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund reset SO lines qty_invoiced
        self._refund_invoice(self.so.invoice_ids)
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff lines should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_not_invoiced_after_cutoff(self):
        """Test cutoff based on SO where product_uom_qty > qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        # Make invoice
        self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Validate invoice after cutoff
        self.so.invoice_ids.invoice_date = cutoff.cutoff_date + timedelta(days=1)
        self.so.invoice_ids.action_post()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff lines should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Make a refund after cutoff
        refund = self._refund_invoice(self.so.invoice_ids, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_all_invoiced_after_cutoff(self):
        """Test cutoff based on SO where product_uom_qty = qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Make invoice
        self.so._create_invoices(final=True)
        # Validate invoice after cutoff
        self.so.invoice_ids.invoice_date = cutoff.cutoff_date + timedelta(days=1)
        self.so.invoice_ids.action_post()
        # as there is no delivery and invoice is after cutoff, no line is generated
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Make a refund - the refund reset SO lines qty_invoiced
        refund = self._refund_invoice(self.so.invoice_ids, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_after(self):
        """Test cutoff when SO is force invoiced after cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Force invoiced after cutoff lines generated, lines should be deleted
        self.so.force_invoiced = True
        self.assertEqual(len(cutoff.line_ids), 0, "cutoff line should be deleted")
        # Remove Force invoiced, lines should be recreated
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff lines should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_before(self):
        """Test cutoff when SO is force invoiced before cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Force invoiced before cutoff lines generated, lines should be deleted
        self.so.force_invoiced = True
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
        # Remove Force invoiced, lines should be created
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_after_but_posted(self):
        """Test cutoff when SO is force invoiced after closed cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        cutoff.state = "done"
        # Force invoiced after cutoff lines generated, cutoff is posted
        self.so.force_invoiced = True
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )
        # Remove Force invoiced, nothing changes
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        amount = self.qty * self.price
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, amount, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_force_invoiced_before_but_posted(self):
        """Test cutoff when SO is force invoiced before closed cutoff"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        # Force invoiced before cutoff lines generated, lines should be deleted
        self.so.force_invoiced = True
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
        cutoff.state = "done"
        # Remove Force invoiced, lines should be created
        self.so.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")

    def test_accrued_revenue_on_so_force_invoiced_line_added(self):
        """Test cutoff when SO is force invoiced and line is added"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self.so.force_invoiced = True
        p = self.env.ref("product.expense_product")
        self.so.order_line = [
            Command.create(
                {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1,
                    "product_uom": p.uom_id.id,
                    "price_unit": self.price,
                    "tax_id": [Command.set(self.tax_sale.ids)],
                },
            )
        ]
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "0 cutoff line should be found")
        for sol in self.so.order_line:
            self.assertEqual(sol.is_cutoff_accrual_excluded, True)
