# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_prepaid_revenue_account_id = fields.Many2one(
        'account.account', string='Default Account for Prepaid Revenue',
        domain=[('deprecated', '=', False)])
    default_prepaid_expense_account_id = fields.Many2one(
        'account.account', string='Default Account for Prepaid Expense',
        domain=[('deprecated', '=', False)])
