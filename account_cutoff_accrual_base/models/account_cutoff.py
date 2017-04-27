# -*- coding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Accrual Base module for OpenERP
#    Copyright (C) 2013 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _inherit_default_cutoff_account_id(self):
        if self.env.context is None:
            self.env.context = {}
        account_id = super(AccountCutoff,
                           self)._inherit_default_cutoff_account_id()

        type = self.env.context.get('type')
        company = self.env.user.company_id

        if type == 'accrued_expense':
            account_id = company.default_accrued_expense_account_id.id or False
        elif type == 'accrued_revenue':
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    def _get_default_journal(self, cr, uid, context=None):
        journal_id = super(account_cutoff, self)\
            ._get_default_journal(cr, uid, context=context)
        cur_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        cutoff_type = context.get('type', False)
        if cutoff_type in ['accrued_expense', 'accrued_revenue']:
            journal_id = cur_user.company_id.\
                default_accrual_journal_id.id or False
        return journal_id


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    quantity = fields.Float('Quantity',
                            digits_compute=dp.get_precision('Product UoS'),
                            readonly=True)

    price_unit = fields.Float('Unit Price',
                              digits_compute=dp.get_precision('Product Price'),
                              readonly=True,
                              help="Price per unit (discount included)")
