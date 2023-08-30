# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests.common import Form

from .common import TestAccountCutoffCutoffPickingCommon


class TestAccountCutoffCutoffExpense(TestAccountCutoffCutoffPickingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Removing all existing PO
        cls.env.cr.execute("DELETE FROM purchase_order;")
        # Create PO
        cls.tax_purchase = cls.env.company.account_purchase_tax_id
        cls.cutoff_account = cls.env["account.account"].create(
            {
                "name": "account accrued expense",
                "code": "accountAccruedExpense",
                "account_type": "asset_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.tax_purchase.account_accrued_expense_id = cls.cutoff_account
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_qty": 5,
                            "product_uom": p.uom_po_id.id,
                            "price_unit": 100,
                            "date_planned": fields.Date.to_string(
                                datetime.today() + relativedelta(days=-15)
                            ),
                            "analytic_distribution": {
                                str(cls.analytic_account.id): 100.0
                            },
                            "taxes_id": [Command.set(cls.tax_purchase.ids)],
                        },
                    )
                    for p in cls.products
                ],
            }
        )
        type_cutoff = "accrued_expense"
        cls.expense_cutoff = (
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

    def _confirm_po_and_do_picking(self, qty_done):
        self.po.button_confirm()
        self.po.button_approve(force=True)
        pick = self.po.picking_ids
        pick.action_assign()
        pick.move_line_ids.write({"qty_done": qty_done})
        pick._action_done()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties,
            [qty_done for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )

    def _create_po_invoice(self, date):
        invoice_form = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice", default_purchase_id=self.po.id
            )
        )
        invoice_form.invoice_date = date
        return invoice_form.save()

    def test_accrued_expense_empty(self):
        """Test cutoff when there is no PO."""
        cutoff = self.expense_cutoff
        cutoff.get_lines()
        self.assertEqual(
            len(cutoff.line_ids), 0, "There should be no PO line to process"
        )

    def test_expense_analytic_distribution(self):
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): 100.0},
                "Analytic distribution is not correctly set",
            )

    def test_expense_tax_line(self):
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                len(line.tax_line_ids), 1, "tax lines is not correctly set"
            )
            self.assertEqual(line.tax_line_ids.cutoff_account_id, self.cutoff_account)
            self.assertEqual(line.tax_line_ids.tax_id, self.tax_purchase)
            self.assertEqual(line.tax_line_ids.base, 200)
            self.assertEqual(line.tax_line_ids.amount, -30)
            self.assertEqual(line.tax_line_ids.cutoff_amount, -30)

    def test_accrued_expense_on_po_not_invoiced(self):
        """Test cutoff based on PO where qty_received > qty_invoiced."""
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make invoice
        po_invoice = self._create_po_invoice(fields.Date.today())
        # - invoice is in draft, no change to cutoff
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice
        po_invoice.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "SO line cutoff amount incorrect")
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice)
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_all_invoiced(self):
        """Test cutoff based on PO where qty_received = qty_invoiced."""
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        # Make invoice
        po_invoice = self._create_po_invoice(fields.Date.today())
        # Validate invoice
        po_invoice.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 0, "2 cutoff lines should be found")
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice)
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_draft_invoice(self):
        """Test cutoff based on PO where qty_received = qty_invoiced but the.

        invoice is still in draft
        """
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        # Make invoice
        po_invoice = self._create_po_invoice(fields.Date.today())
        # - invoice is in draft, no change to cutoff
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice
        po_invoice.action_post()

        self.assertEqual(len(cutoff.line_ids), 2, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice)

        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_draft_refund(self):
        """Test cutoff based on PO where qty_received = qty_invoiced but the.

        refund is still in draft
        """
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        # Make invoice for 5
        po_invoice = self._create_po_invoice(fields.Date.today())
        po_invoice.invoice_line_ids.write({"quantity": 5})
        # Validate invoice
        po_invoice.action_post()
        # Make a refund for the 3 that have not been received
        # - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice, post=False)
        refund.invoice_line_ids.write({"quantity": 3})
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 0, "No cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(line.cutoff_amount, 0, "PO line cutoff amount incorrect")

    def test_accrued_expense_on_po_not_invoiced_after_cutoff(self):
        """Test cutoff based on PO where qty_received > qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()

        # Make invoice
        po_invoice = self._create_po_invoice(fields.Date.today())
        # - invoice is in draft, no change to cutoff

        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice after cutoff
        po_invoice.date = cutoff.cutoff_date + timedelta(days=1)
        po_invoice.action_post()

        self.assertEqual(len(cutoff.line_ids), 2, "no cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice)

        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_all_invoiced_after_cutoff(self):
        """Test cutoff based on PO where qty_received = qty_invoiced.

        And make invoice after cutoff date
        """
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        # Make invoice
        po_invoice = self._create_po_invoice(fields.Date.today())
        # Validate invoice after cutoff
        po_invoice.date = cutoff.cutoff_date + timedelta(days=1)
        po_invoice.action_post()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        # Make a refund after cutoff - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice, post=False)
        refund.date = cutoff.cutoff_date + timedelta(days=1)
        refund.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Make a refund before cutoff
        # - the refund is affecting the PO lines qty_invoiced
        refund = self._refund_invoice(po_invoice)

        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2 * 2, "PO line cutoff amount incorrect"
            )
