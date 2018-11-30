# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_cutoff_journal_id = fields.Many2one(
        related='company_id.default_cutoff_journal_id',
        string='Default Cut-off Journal'
    )
