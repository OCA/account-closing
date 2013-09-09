# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>

from datetime import timedelta

from odoo import Command, fields

from .common import TestAccountCutoffCutoffPickingCommon


class TestAccountCutoffCutoffRevenue(TestAccountCutoffCutoffPickingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_sale = cls.env.company.account_sale_tax_id
        cls.cutoff_account = cls.env["account.account"].create(
            {
                "name": "account accrued revenue",
                "code": "accountAccruedExpense",
                "account_type": "asset_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.tax_sale.account_accrued_revenue_id = cls.cutoff_account
        # Removing all existing SO
        cls.env.cr.execute("DELETE FROM sale_order;")
        # Create SO
        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "partner_invoice_id": cls.partner.id,
                "partner_shipping_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_uom_qty": 5,
                            "product_uom": p.uom_id.id,
                            "price_unit": 100,
                            "analytic_distribution": {
                                str(cls.analytic_account.id): 100.0
                            },
                            "tax_id": [Command.set(cls.tax_sale.ids)],
                        },
                    )
                    for p in cls.products
                ],
                "pricelist_id": cls.env.ref("product.list0").id,
            }
        )
        type_cutoff = "accrued_revenue"
        cls.revenue_cutoff = (
            cls.env["account.cutoff"]
            .with_context(default_cutoff_type=type_cutoff)
            .create(
                {
                    "cutoff_type": type_cutoff,
                    "company_id": 1,
                    "cutoff_date": fields.Date.today(),
                }
            )
        )

    def _confirm_so_and_do_picking(self, qty_done):
        self.so.action_confirm()
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
            [qty_done for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )

    def test_accrued_revenue_empty(self):
        """Test cutoff when there is no SO."""
        cutoff = self.revenue_cutoff
        cutoff.get_lines()
        self.assertEqual(
            len(cutoff.line_ids), 0, "There should be no SO line to process"
        )

    def test_revenue_analytic_distribution(self):
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): 100.0},
                "Analytic distribution is not correctly set",
            )

    def test_revenue_tax_line(self):
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                len(line.tax_line_ids), 1, "tax lines is not correctly set"
            )
            self.assertEqual(line.tax_line_ids.cutoff_account_id, self.cutoff_account)
            self.assertEqual(line.tax_line_ids.tax_id, self.tax_sale)
            self.assertEqual(line.tax_line_ids.base, 200)
            self.assertEqual(line.tax_line_ids.amount, 30)
            self.assertEqual(line.tax_line_ids.cutoff_amount, 30)

    def test_accrued_revenue_on_so_not_invoiced(self):
        """Test cutoff based on SO where qty_delivered > qty_invoiced."""
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make invoice
        self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        self.so.invoice_ids.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund reset the SO lines qty_invoiced
        self._refund_invoice(self.so.invoice_ids)
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 200, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_all_invoiced(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced."""
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        # Make invoice
        self.so._create_invoices(final=True)
        # Validate invoice
        self.so.invoice_ids.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        # Make a refund - the refund reset qty_invoiced
        self._refund_invoice(self.so.invoice_ids)
        self.assertEqual(len(cutoff.line_ids), 2, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 200, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_draft_invoice(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced but the.

        invoice is still in draft
        """
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        # Make invoice
        self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        self.so.invoice_ids.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund reset SO lines qty_invoiced
        self._refund_invoice(self.so.invoice_ids)
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 200, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_not_invoiced_after_cutoff(self):
        """Test cutoff based on SO where qty_delivered > qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        # Make invoice
        self.so._create_invoices(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice after cutoff
        self.so.invoice_ids.invoice_date = cutoff.cutoff_date + timedelta(days=1)
        self.so.invoice_ids.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make a refund after cutoff
        refund = self._refund_invoice(self.so.invoice_ids, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_all_invoiced_after_cutoff(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        # Make invoice
        self.so._create_invoices(final=True)
        # Validate invoice after cutoff
        self.so.invoice_ids.invoice_date = cutoff.cutoff_date + timedelta(days=1)
        self.so.invoice_ids.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 2 * 100, "SO line cutoff amount incorrect"
            )
        # Make a refund - the refund reset SO lines qty_invoiced
        refund = self._refund_invoice(self.so.invoice_ids, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
