# Copyright 2013-2019 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # I can't name it default_cutoff_journal_id
    # because default_ is a special prefix
    dft_cutoff_journal_id = fields.Many2one(
        related='company_id.default_cutoff_journal_id', readonly=False)
