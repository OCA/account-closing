# Copyright 2019-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dft_prepaid_revenue_account_id = fields.Many2one(
        related="company_id.default_prepaid_revenue_account_id", readonly=False
    )
    dft_prepaid_expense_account_id = fields.Many2one(
        related="company_id.default_prepaid_expense_account_id", readonly=False
    )
