# Copyright 2019 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dft_accrued_revenue_account_id = fields.Many2one(
        related="company_id.default_accrued_revenue_account_id", readonly=False
    )

    dft_accrued_expense_account_id = fields.Many2one(
        related="company_id.default_accrued_expense_account_id", readonly=False
    )

    accrual_taxes = fields.Boolean(related="company_id.accrual_taxes", readonly=False)
