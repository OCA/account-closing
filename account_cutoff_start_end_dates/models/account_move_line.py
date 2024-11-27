# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"
    cutoff_line_ids = fields.One2many(
        "account.cutoff.line",
        inverse_name="origin_move_line_id",
        string="Related cutoff line",
        readonly=True,
    )
