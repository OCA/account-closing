# -*- coding: utf-8 -*-
# Copyright 2013-2018 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class AccountCutOff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _default_cutoff_account_id(self):
        account_id = super(AccountCutOff, self)._default_cutoff_account_id()
        type = self.env.context.get('default_type')
        company = self.env.user.company_id
        if type == 'accrued_expense':
            account_id = company.default_accrued_expense_account_id.id or False
        elif type == 'accrued_revenue':
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    @api.model
    def _get_default_journal(self):
        journal = super(AccountCutOff, self)._get_default_journal()
        cutoff_type = self.env.context.get('default_type')
        company = self.env.user.company_id
        default_journal = company.default_cutoff_journal_id
        if cutoff_type == 'accrued_expense':
            journal = company.default_accrual_expense_journal_id or\
                default_journal
        elif cutoff_type == 'accrued_revenue':
            journal = company.default_accrual_revenue_journal_id or\
                default_journal
        return journal


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    quantity = fields.Float(
        string='Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True)
    price_unit = fields.Float(
        string='Unit Price',
        digits=dp.get_precision('Product Price'),
        readonly=True,
        help="Price per unit (discount included)")
