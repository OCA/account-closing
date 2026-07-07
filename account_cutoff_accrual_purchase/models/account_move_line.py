# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_cutoff_accrual_purchase_lines(self):
        """return purchase order lines linked to purchase invoice lines"""
        return self.filtered(
            lambda line: line.move_id.move_type in ("in_invoice", "in_refund")
        ).purchase_line_id

    def _update_cutoff_accrual_purchase_lines(self, purchase_lines):
        """reuse the order line cutoff check after invoice line changes"""
        for purchase_line in purchase_lines:
            purchase_line._update_cutoff_accrual()

    def write(self, vals):
        """keep closed cutoff quantities stable when invoice lines change"""
        must_update_cutoff = bool({"purchase_line_id", "quantity"} & set(vals))
        # keep old purchase lines before the relation or quantity changes
        purchase_lines = (
            self._get_cutoff_accrual_purchase_lines()
            if must_update_cutoff
            else self.env["purchase.order.line"]
        )
        res = super().write(vals)
        if must_update_cutoff:
            # also check the new purchase lines after the write
            self._update_cutoff_accrual_purchase_lines(
                purchase_lines | self._get_cutoff_accrual_purchase_lines()
            )
        return res

    def unlink(self):
        """check closed cutoffs when invoice lines are removed"""
        purchase_lines = self._get_cutoff_accrual_purchase_lines()
        res = super().unlink()
        self._update_cutoff_accrual_purchase_lines(purchase_lines)
        return res
