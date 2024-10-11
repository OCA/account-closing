# Copyright 2023 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        res = super().write(vals)
        if "force_invoiced" in vals or vals.get("invoice_status") == "to invoice":
            # As the order could be non invoiceable while a line is invoiceable
            # (see delivery module), we need to check each line when the order
            # invoice status becomes "to invoice"
            for line in self.order_line:
                line.sudo()._update_cutoff_accrual()
        return res
