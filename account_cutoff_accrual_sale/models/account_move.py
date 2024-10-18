# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_cutoff_accrual_order_lines(self):
        """Return a list of order lines to process"""
        res = super()._get_cutoff_accrual_order_lines()
        if self.move_type in ("out_invoice", "out_refund"):
            res.append(self.invoice_line_ids.sale_line_ids)
        return res
