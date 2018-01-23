###############################################################################
# For copyright and license notices, see __manifest__.py file in root directory
###############################################################################


from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_accrued_revenue_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Account for Accrued Revenues',
        domain=[('deprecated', '=', False)])

    default_accrued_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Account for Accrued Expenses',
        domain=[('deprecated', '=', False)])

    default_accrual_revenue_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Journal for Accrued Revenues')

    default_accrual_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Journal for Accrued Expenses')
