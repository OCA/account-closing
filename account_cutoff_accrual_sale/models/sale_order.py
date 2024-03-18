# Copyright 2023 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        res = super().write(vals)
        # Force inverse trigger on sale.order.line is_cutoff_accrual_excluded
        if "force_invoiced" in vals:
            self.order_line.is_cutoff_accrual_excluded = vals["force_invoiced"]
        return res
