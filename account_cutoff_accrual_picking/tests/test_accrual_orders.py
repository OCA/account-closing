# -*- coding: utf-8 -*-
# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase
from odoo import fields


class TestAccountCutoffAccrualPicking(TransactionCase):
    def setUp(self):
        super(TestAccountCutoffAccrualPicking, self).setUp()
        self.company = self.env.ref("base.main_company")
        self.accrual_journal = self.env["account.journal"].create(
            {
                "code": "cop0",
                "company_id": self.company.id,
                "name": "Accrual Journal Picking",
                "type": "general",
            }
        )
        user_type_lia = self.env.ref("account.data_account_type_current_liabilities")
        self.accrual_account = self.env["account.account"].create(
            {
                "name": "Accrual account",
                "code": "ACC480000",
                "company_id": self.company.id,
                "user_type_id": user_type_lia.id,
            }
        )
        self.company.write(
            {
                "default_accrued_revenue_account_id": self.accrual_account.id,
                "default_accrued_expense_account_id": self.accrual_account.id,
                "default_cutoff_journal_id": self.accrual_journal.id,
            }
        )

        self.partner = self.env.ref("base.res_partner_1")

        # Removing all existing SO
        self.env.cr.execute("DELETE FROM sale_order;")
        # Create SO
        self.products = [
            self.env.ref("product.product_delivery_01"),
            self.env.ref("product.product_delivery_02"),
        ]
        self.so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_uom_qty": 5,
                            "product_uom": p.uom_id.id,
                            "price_unit": 100,
                        },
                    )
                    for p in self.products
                ],
                "pricelist_id": self.env.ref("product.list0").id,
            }
        )
        type_cutoff = "accrued_revenue"
        self.revenue_cutoff = (
            self.env["account.cutoff"]
            .with_context(default_type=type_cutoff)
            .create(
                {
                    "type": type_cutoff,
                    "company_id": 1,
                    "cutoff_date": fields.Date.today(),
                }
            )
        )

        # Removing all existing PO
        self.env.cr.execute("DELETE FROM purchase_order;")
        # Create PO
        self.products = [
            self.env.ref("product.product_delivery_01"),
            self.env.ref("product.product_delivery_02"),
        ]
        self.po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_qty": 5,
                            "product_uom": p.uom_po_id.id,
                            "price_unit": 100,
                            "date_planned": fields.Date.to_string(
                                datetime.today() + relativedelta(days=-15)
                            ),
                        },
                    )
                    for p in self.products
                ],
            }
        )
        type_cutoff = "accrued_expense"
        self.expense_cutoff = (
            self.env["account.cutoff"]
            .with_context(default_type=type_cutoff)
            .create(
                {
                    "type": type_cutoff,
                    "company_id": 1,
                    "cutoff_date": fields.Date.today(),
                }
            )
        )

    def test_accrued_revenue_empty(self):
        """ Test cutoff when there is no SO """
        cutoff = self.revenue_cutoff
        cutoff.get_lines()
        self.assertEqual(
            len(cutoff.line_ids), 0, "There should be no SO line to process"
        )

    def test_accrued_revenue_on_so_not_invoiced(self):
        """ Test cutoff based on SO where qty_delivered > qty_invoiced """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        # Deliver
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # deliver 2/5
        pick.do_transfer()
        self.assertEqual(
            self.so.invoice_status,
            "to invoice",
            'SO invoice_status should be "to invoice" after partial delivery',
        )
        qties = [sol.qty_delivered for sol in self.so.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make invoice
        self.so.action_invoice_create(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        self.so.invoice_ids.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund is not affecting the SO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.so.invoice_ids.ids
        ).create({}).invoice_refund()
        refund = self.so.invoice_ids.filtered(lambda i: i.type == "out_refund")
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_all_invoiced(self):
        """ Test cutoff based on SO where qty_delivered = qty_invoiced """
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        # Deliver
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # deliver 2/5
        pick.do_transfer()
        self.assertEqual(
            self.so.invoice_status,
            "to invoice",
            'SO invoice_status should be "to invoice" after partial delivery',
        )
        qties = [sol.qty_delivered for sol in self.so.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )
        # Make invoice
        self.so.action_invoice_create(final=True)
        # Validate invoice
        self.so.invoice_ids.action_invoice_open()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        # Make a refund - the refund is not affecting the SO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.so.invoice_ids.ids
        ).create({}).invoice_refund()
        refund = self.so.invoice_ids.filtered(lambda i: i.type == "out_refund")
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_draft_invoice(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced but the
        invoice is still in draft"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        # Deliver
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # deliver 2/5
        pick.do_transfer()
        self.assertEqual(
            self.so.invoice_status,
            "to invoice",
            'SO invoice_status should be "to invoice" after partial delivery',
        )
        qties = [sol.qty_delivered for sol in self.so.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )
        # Make invoice
        self.so.action_invoice_create(final=True)
        # - invoice is in draft, no change to cutoff
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice
        self.so.invoice_ids.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund - the refund is not affecting the SO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.so.invoice_ids.ids
        ).create({}).invoice_refund()
        refund = self.so.invoice_ids.filtered(lambda i: i.type == "out_refund")
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")

    def test_accrued_revenue_on_so_not_invoiced_after_cutoff(self):
        """Test cutoff based on SO where qty_delivered > qty_invoiced.
        And make invoice after cutoff date"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        # Deliver
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # deliver 2/5
        pick.do_transfer()
        cutoff.get_lines()
        # Make invoice
        self.so.action_invoice_create(final=True)
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Validate invoice after cutoff
        self.so.invoice_ids.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        self.so.invoice_ids.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make a refund after cutoff
        # - the refund is not affecting the SO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.so.invoice_ids.ids
        ).create({}).invoice_refund()
        refund = self.so.invoice_ids.filtered(lambda i: i.type == "out_refund")
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_revenue_on_so_all_invoiced_after_cutoff(self):
        """Test cutoff based on SO where qty_delivered = qty_invoiced.
        And make invoice after cutoff date"""
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        self.assertEqual(
            self.so.invoice_status,
            "no",
            'SO invoice_status should be "nothing to invoice" after confirming',
        )
        # Deliver
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # deliver 2/5
        pick.do_transfer()
        self.assertEqual(
            self.so.invoice_status,
            "to invoice",
            'SO invoice_status should be "to invoice" after partial delivery',
        )
        qties = [sol.qty_delivered for sol in self.so.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )
        # Make invoice
        self.so.action_invoice_create(final=True)
        # Validate invoice after cutoff
        self.so.invoice_ids.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        self.so.invoice_ids.action_invoice_open()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        # Make a refund - the refund is not affecting the SO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.so.invoice_ids.ids
        ).create({}).invoice_refund()
        refund = self.so.invoice_ids.filtered(lambda i: i.type == "out_refund")
        refund.action_invoice_open()
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )

    def test_accrued_expense_empty(self):
        """ Test cutoff when there is no PO """
        cutoff = self.expense_cutoff
        cutoff.get_lines()
        self.assertEqual(
            len(cutoff.line_ids), 0, "There should be no PO line to process"
        )

    def test_accrued_expense_on_po_not_invoiced(self):
        """ Test cutoff based on PO where qty_received > qty_invoiced """
        cutoff = self.expense_cutoff
        self.po.button_confirm()
        self.po.button_approve(force=True)
        # Receive
        pick = self.po.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # receive 2/5
        pick.do_transfer()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Received quantities are wrong after partial reception",
        )
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make invoice
        invoice = self.env["account.invoice"].new(
            {"type": "in_invoice", "purchase_id": self.po.id}
        )
        invoice.purchase_order_change()
        invoice.create(invoice._convert_to_write(invoice._cache))
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice
        self.po.invoice_ids.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_all_invoiced(self):
        """ Test cutoff based on PO where qty_received = qty_invoiced """
        cutoff = self.expense_cutoff
        self.po.button_confirm()
        self.po.button_approve(force=True)
        # Receive
        pick = self.po.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # receive 2/5
        pick.do_transfer()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Received quantities are wrong after partial reception",
        )
        # Make invoice
        invoice = self.env["account.invoice"].new(
            {"type": "in_invoice", "purchase_id": self.po.id}
        )
        invoice.purchase_order_change()
        invoice.create(invoice._convert_to_write(invoice._cache))
        # Validate invoice
        self.po.invoice_ids.action_invoice_open()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_draft_invoice(self):
        """Test cutoff based on PO where qty_received = qty_invoiced but the
        invoice is still in draft"""
        cutoff = self.expense_cutoff
        self.po.button_confirm()
        self.po.button_approve(force=True)
        # Receive
        pick = self.po.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # receive 2/5
        pick.do_transfer()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Received quantities are wrong after partial reception",
        )
        # Make invoice
        invoice = self.env["account.invoice"].new(
            {"type": "in_invoice", "purchase_id": self.po.id}
        )
        invoice.purchase_order_change()
        invoice.create(invoice._convert_to_write(invoice._cache))
        # - invoice is in draft, no change to cutoff
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice
        self.po.invoice_ids.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_draft_refund(self):
        """Test cutoff based on PO where qty_received = qty_invoiced but the
        refund is still in draft"""
        cutoff = self.expense_cutoff
        self.po.button_confirm()
        self.po.button_approve(force=True)
        # Receive
        pick = self.po.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # receive 2/5
        pick.do_transfer()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties,
            [2 for p in self.products],
            "Received quantities are wrong after partial reception",
        )
        # Make invoice for 5
        invoice = self.env["account.invoice"].new(
            {"type": "in_invoice", "purchase_id": self.po.id}
        )
        invoice.purchase_order_change()
        invoice = invoice.create(invoice._convert_to_write(invoice._cache))
        invoice.invoice_line_ids.write({"quantity": 5})
        # Validate invoice
        self.po.invoice_ids.action_invoice_open()
        # Make a refund for the 3 that have not been received
        # - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.invoice_line_ids.write({"quantity": 3})
        refund.state = refund.state  # force recompute PO qty_invoiced
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")

    def test_accrued_expense_on_po_not_invoiced_after_cutoff(self):
        """Test cutoff based on PO where qty_received > qty_invoiced.
        And make invoice after cutoff date"""
        cutoff = self.expense_cutoff
        self.po.button_confirm()
        self.po.button_approve(force=True)
        # Receive
        pick = self.po.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # receive 2/5
        pick.do_transfer()
        cutoff.get_lines()
        # Make invoice
        invoice = self.env["account.invoice"].new(
            {"type": "in_invoice", "purchase_id": self.po.id}
        )
        invoice.purchase_order_change()
        invoice.create(invoice._convert_to_write(invoice._cache))
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice after cutoff
        self.po.invoice_ids.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        self.po.invoice_ids.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_all_invoiced_after_cutoff(self):
        """Test cutoff based on PO where qty_received = qty_invoiced.
        And make invoice after cutoff date"""
        cutoff = self.expense_cutoff
        self.po.button_confirm()
        self.po.button_approve(force=True)
        # Receive
        pick = self.po.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write(
            {"product_qty": 2, "qty_done": 2}
        )  # receive 2/5
        pick.do_transfer()
        # Make invoice
        invoice = self.env["account.invoice"].new(
            {"type": "in_invoice", "purchase_id": self.po.id}
        )
        invoice.purchase_order_change()
        invoice.create(invoice._convert_to_write(invoice._cache))
        # Validate invoice after cutoff
        self.po.invoice_ids.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        self.po.invoice_ids.action_invoice_open()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.date = fields.Date.to_string(
            fields.Date.from_string(cutoff.cutoff_date) + timedelta(days=1)
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        self.env["account.invoice.refund"].with_context(
            active_ids=self.po.invoice_ids.filtered(
                lambda i: i.type == "in_invoice"
            ).ids
        ).create({}).invoice_refund()
        refund = self.po.invoice_ids.filtered(
            lambda i: i.type == "in_refund" and i.state == "draft"
        )
        refund.action_invoice_open()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2 * 2, "PO line cutoff amount incorrect"
            )
