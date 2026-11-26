# Copyright 2023 Sergio Corato
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    apply_dates_all_lines = fields.Boolean(
        string="Apply Start/End Dates To All Account Move Lines", default=True
    )
