# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    account_cutoff_line_ids = fields.One2many(
        "account.cutoff.line",
        "sale_line_id",
        string="Account Cutoff Lines",
        readonly=True,
    )

    def _get_invoice_lines(self):
        return (
            super()._get_invoice_lines().filtered(lambda l: l.move_id.state != "draft")
        )

    def _get_cutoff_quantity(self, cutoff_invoiced_qty):
        self.ensure_one()
        if self.state in ["sale", "done"] and not self.display_type:
            if self.product_id.invoice_policy == "order":
                return self.product_uom_qty - cutoff_invoiced_qty
            return self.qty_delivered - cutoff_invoiced_qty
        return 0
