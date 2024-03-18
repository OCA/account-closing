# Copyright 2023 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def write(self, vals):
        res = super().write(vals)
        if "force_invoiced" in vals:
            self.order_line.is_cutoff_accrual_excluded = vals["force_invoiced"]
        return res
