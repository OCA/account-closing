# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    revaluation_rate_type = fields.Selection(
        string="Revaluation rate type",
        selection=[
            ('monthly', 'Monthly average'),
            ('daily', 'Daily'),
        ],
        required=True,
        default='daily')
