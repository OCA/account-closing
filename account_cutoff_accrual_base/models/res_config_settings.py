# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_accrued_revenue_account_id = fields.Many2one(
        related='company_id.default_accrued_revenue_account_id',
        string='Default Account for Accrued Revenues',
    )

    default_accrued_expense_account_id = fields.Many2one(
        related='company_id.default_accrued_expense_account_id',
        string='Default Account for Accrued Expenses',
    )

    default_accrual_revenue_journal_id = fields.Many2one(
        related='company_id.default_accrual_revenue_journal_id',
        string='Default Journal for Accrued Revenues'
    )

    default_accrual_expense_journal_id = fields.Many2one(
        related='company_id.default_accrual_expense_journal_id',
        string='Default Journal for Accrued Expenses'
    )
