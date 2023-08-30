# Copyright 2017 Camptocamp SA
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    account_cutoff_line_ids = fields.One2many(
        "account.cutoff.line",
        "purchase_line_id",
        string="Account Cutoff Lines",
        readonly=True,
    )

    def _get_invoice_lines(self):
        return (
            super()._get_invoice_lines().filtered(lambda l: l.move_id.state != "draft")
        )

    def _get_cutoff_quantity(self, cutoff_invoiced_qty):
        self.ensure_one()
        if self.order_id.state in ["purchase", "done"]:
            if self.product_id.purchase_method == "purchase":
                return self.product_qty - cutoff_invoiced_qty
            return self.qty_received - cutoff_invoiced_qty
        return 0
