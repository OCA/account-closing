# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_cutoff_journal_id = fields.Many2one(
        'account.journal', string='Default Cut-off Journal')
