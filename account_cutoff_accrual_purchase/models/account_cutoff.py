# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    order_line_model = fields.Selection(
        selection_add=[("purchase.order.line", "Purchase Orders")]
    )
