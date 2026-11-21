# Copyright 2016-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    start_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)
    total_days = fields.Integer(readonly=True)
    cutoff_days = fields.Integer(
        readonly=True,
        help="In regular mode, this is the number of days after the "
        "cut-off date. In forecast mode, this is the number of days "
        "between the start date and the end date.",
    )
