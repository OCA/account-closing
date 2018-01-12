###############################################################################
# For copyright and license notices, see __manifest__.py file in root directory
###############################################################################

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    account_accrued_revenue_id = fields.Many2one(
        comodel_name='account.account',
        string='Accrued Revenue Tax Account',
        domain=[('deprecated', '=', False)]
    )
    account_accrued_expense_id = fields.Many2one(
        comodel_name='account.account',
        string='Accrued Expense Tax Account',
        domain=[('deprecated', '=', False)]
    )
