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
