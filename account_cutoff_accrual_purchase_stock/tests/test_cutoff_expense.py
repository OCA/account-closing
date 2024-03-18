# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields

from .common import TestAccountCutoffAccrualPurchaseCommon


class TestAccountCutoffAccrualPurchase(TestAccountCutoffAccrualPurchaseCommon):
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
        self.assertEqual(len(cutoff.line_ids), 0, "0 cutoff lines should be found")
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
        # - invoice is in draft, cutoff generated
        self.assertEqual(po_invoice.state, "draft", "invoice should be draft")
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Validate invoice
        po_invoice.action_post()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
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

    def test_accrued_expense_on_po_force_invoiced_after(self):
        """Test cutoff when PO is force invoiced after cutoff"""
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Force invoiced after cutoff lines generated, lines should be deleted
        self.po.force_invoiced = True
        self.assertEqual(len(cutoff.line_ids), 0, "cutoff line should deleted")
        # Remove Force invoiced, lines should be recreated
        self.po.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_force_invoiced_before(self):
        """Test cutoff when PO is force invoiced before cutoff"""
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        # Force invoiced before cutoff lines generated, lines should be deleted
        self.po.force_invoiced = True
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
        # Remove Force invoiced, lines should be created
        self.po.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_force_invoiced_after_but_posted(self):
        """Test cutoff when PO is force invoiced after closed cutoff"""
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        cutoff.state = "done"
        # Force invoiced after cutoff lines generated, cutoff is posted
        self.po.force_invoiced = True
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )
        # Remove Force invoiced, nothing changes
        self.po.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, -100 * 2, "PO line cutoff amount incorrect"
            )

    def test_accrued_expense_on_po_force_invoiced_before_but_posted(self):
        """Test cutoff when PO is force invoiced before closed cutoff"""
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        # Force invoiced before cutoff lines generated, lines should be deleted
        self.po.force_invoiced = True
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
        cutoff.state = "done"
        # Remove Force invoiced, lines should be created
        self.po.force_invoiced = False
        self.assertEqual(len(cutoff.line_ids), 0, "no cutoff line should be generated")
