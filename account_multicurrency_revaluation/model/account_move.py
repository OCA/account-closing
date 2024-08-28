from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    revaluation_to_reverse = fields.Boolean(
        string="Revaluation to reverse", default=False, readonly=True
    )

    revaluation_reversed = fields.Boolean(
        string="Revaluation reversed", default=False, readonly=True
    )
