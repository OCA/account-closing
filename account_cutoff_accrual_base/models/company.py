# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_accrued_revenue_account_id = fields.Many2one(
        'account.account', string='Default Account for Accrued Revenues',
        domain=[('type', '<>', 'view'), ('type', '<>', 'closed')])
    default_accrued_expense_account_id = fields.Many2one(
        'account.account', string='Default Account for Accrued Expenses',
        domain=[('type', '<>', 'view'), ('type', '<>', 'closed')])
    default_accrual_revenue_journal_id = fields.Many2one(
        'account.journal', string='Default Journal for Accrued Revenues')
    default_accrual_expense_journal_id = fields.Many2one(
        'account.journal', string='Default Journal for Accrued Expenses')
