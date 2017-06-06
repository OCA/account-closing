# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    account_accrued_revenue_id = fields.Many2one(
        'account.account', string='Accrued Revenue Tax Account',
        domain=[('type', '<>', 'view'), ('type', '<>', 'closed')])
    account_accrued_expense_id = fields.Many2one(
        'account.account', string='Accrued Expense Tax Account',
        domain=[('type', '<>', 'view'), ('type', '<>', 'closed')])
