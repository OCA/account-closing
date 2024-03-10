# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountCutoffLine(models.Model):

    _inherit = "account.cutoff.line"

    categ_id = fields.Many2one(related="product_id.categ_id", readonly=True)
