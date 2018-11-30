# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_prepaid_revenue_account_id = fields.Many2one(
        related='company_id.default_prepaid_revenue_account_id',
        string='Default Account for Prepaid Revenue',
    )
    default_prepaid_expense_account_id = fields.Many2one(
        related='company_id.default_prepaid_expense_account_id',
        string='Default Account for Prepaid Expense',
    )
