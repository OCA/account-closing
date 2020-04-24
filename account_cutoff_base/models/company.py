# Copyright 2013-2016 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_cutoff_journal_id = fields.Many2one(
        "account.journal", string="Default Cut-off Journal"
    )
    default_cutoff_move_partner = fields.Boolean(
        string="Partner on Move Line by Default"
    )
