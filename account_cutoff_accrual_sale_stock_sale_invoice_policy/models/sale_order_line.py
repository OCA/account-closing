# Copyright 2025 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_cutoff_accrual_stock_invoice_policy(self):
        if self.order_id.invoice_policy != "product":
            return self.order_id.invoice_policy
        return super()._get_cutoff_accrual_stock_invoice_policy()
